"""Optional secondary recognition for uncertain or inconsistent numeric utterances (Section E).

Runs ONLY when a critical numerical value (weight, date, beneficiary ID, or vital) is:
- out of physiological / calendar bounds,
- ambiguous or missing units,
- conflicting within the utterance,
- low-confidence from primary STT, or
- unparsed despite containing numeric/unit cues.

Never runs on clean, unambiguous utterances, and never silently overwrites one number
with another: disagreements or uncertainties are always surfaced to the ASHA worker
for explicit spoken confirmation.
"""

from __future__ import annotations

import asyncio
import io
import logging
import re
import wave
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Protocol

from gnani.stt import GnaniSTTClient

from app.core.logging import log_event
from app.extraction.extractor import VisitFieldExtractor
from app.extraction.models import (
    DynamicObservation,
    ExtractionResult,
    FieldClarification,
    VisitDraft,
)
from app.extraction.numbers import (
    GRAM_UNIT_RE,
    KG_UNIT_RE,
    LB,
    RB,
    WEIGHT_CUE_RE,
    format_decimal_clean,
)

logger = logging.getLogger(__name__)

NUMERIC_OBSERVATION_KEYS: tuple[str, ...] = (
    "temperature",
    "blood_pressure",
    "hemoglobin_g_dl",
)
IMPORTANT_CONFIRMABLE_FIELDS: tuple[str, ...] = (
    "weight_kg",
    "next_visit_date",
    "beneficiary_id",
    *NUMERIC_OBSERVATION_KEYS,
)

_NUMERIC_CUE_RE = re.compile(
    rf"(?:\d|{LB}(?:{WEIGHT_CUE_RE}|{KG_UNIT_RE}|{GRAM_UNIT_RE}|next\s+visit|agla\s+visit|ben|id|temp|temperature|tapman|तापमान|ಜ್ವರ|ತಾಪಮಾನ|வெப்பநிலை|bp|blood\s*pressure|hb|h\.b\.|hemoglobin|haemoglobin|हीमोग्लोबिन){RB})",
    re.IGNORECASE,
)


def pcm16_to_wav_bytes(pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
    """Wrap raw mono 16-bit PCM bytes in a WAV container in memory."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_bytes)
    return buf.getvalue()


@dataclass(frozen=True)
class UncertaintyAssessment:
    """Result of checking whether an utterance needs secondary recognition."""

    should_recheck: bool
    reasons: tuple[str, ...] = ()


def assess_numeric_uncertainty(
    text: str,
    extraction: ExtractionResult,
    *,
    stt_confidence: float | None = None,
    confidence_threshold: float = 0.65,
) -> UncertaintyAssessment:
    """Determine whether secondary recognition should re-evaluate the utterance audio."""
    reasons: list[str] = []

    # 1. Explicit numeric / date / ID / vital clarifications emitted by primary extractor
    for c in extraction.clarifications:
        if c.field_name in IMPORTANT_CONFIRMABLE_FIELDS:
            reasons.append(f"clarification:{c.field_name}")

    # 2. Needs-confirmation observations (e.g. out-of-bounds weight)
    for obs in extraction.observations:
        if obs.status in {"uncertain", "needs_confirmation"}:
            reasons.append(f"obs_uncertain:{obs.key}")

    # 3. Low STT confidence when numeric entities were extracted
    has_numeric_obs = any(o.key in NUMERIC_OBSERVATION_KEYS for o in extraction.observations)
    has_numeric = bool(
        "weight_kg" in extraction.patch
        or "next_visit_date" in extraction.patch
        or "beneficiary_id" in extraction.patch
        or has_numeric_obs
        or (extraction.trace and extraction.trace.extracted_numbers)
    )
    if stt_confidence is not None and stt_confidence < confidence_threshold and has_numeric:
        reasons.append(f"low_stt_confidence:{stt_confidence:.2f}")

    # 4. Utterance contains explicit numeric/weight/ID/vital cues yet nothing parsed
    if (
        not has_numeric
        and not reasons
        and _NUMERIC_CUE_RE.search(text or "")
        and re.search(
            rf"{LB}(?:weight|wajan|vajan|वजन|ತೂಕ|எடை|kilo|kg|gram|ben|id|temp|temperature|tapman|तापमान|ಜ್ವರ|ತಾಪಮಾನ|வெப்பநிலை|bp|blood\s*pressure|hb|h\.b\.|hemoglobin|haemoglobin|हीमोग्लोबिन){RB}",
            text or "",
            re.IGNORECASE,
        )
    ):
        reasons.append("unparsed_numeric_cue")

    return UncertaintyAssessment(
        should_recheck=len(reasons) > 0,
        reasons=tuple(dict.fromkeys(reasons)),
    )


class SecondarySpeechRecognizer(Protocol):
    """Protocol for optional secondary utterance re-evaluation."""

    async def recognize_segment(
        self,
        pcm_bytes: bytes,
        *,
        sample_rate: int = 16000,
        language_code: str = "indic-auto",
        language_candidates: list[str] | None = None,
        keywords: list[str] | None = None,
        speaker_names: list[str] | None = None,
        previous_text: str | None = None,
        topic: str | None = None,
    ) -> dict[str, Any]: ...


class GnaniRestSecondaryRecognizer:
    """Secondary recognizer using Gnani Prisma v3.0 REST API (`format='codemix'` or `'verbatim'`)."""

    def __init__(
        self,
        *,
        api_key: str,
        secondary_format: str = "codemix",
        model: str = "prisma-v3.0",
        timeout_sec: float = 5.0,
    ) -> None:
        if not api_key:
            raise ValueError("GNANI_API_KEY is required for GnaniRestSecondaryRecognizer")
        self._client = GnaniSTTClient(api_key=api_key, timeout=int(max(timeout_sec, 2.0)))
        self._format = secondary_format
        self._model = model
        self._timeout_sec = timeout_sec

    async def recognize_segment(
        self,
        pcm_bytes: bytes,
        *,
        sample_rate: int = 16000,
        language_code: str = "indic-auto",
        language_candidates: list[str] | None = None,
        keywords: list[str] | None = None,
        speaker_names: list[str] | None = None,
        previous_text: str | None = None,
        topic: str | None = None,
    ) -> dict[str, Any]:
        if not pcm_bytes:
            return {"transcript": "", "format": self._format}
        wav_bytes = pcm16_to_wav_bytes(pcm_bytes, sample_rate=sample_rate)
        cands = language_candidates if language_code == "indic-auto" else None

        def _call() -> dict[str, Any]:
            return self._client.transcribe_bytes(
                wav_bytes,
                filename="utterance.wav",
                language_code=language_code,
                model=self._model,
                format=self._format,
                language_candidates=cands,
                keywords=(keywords or [])[:200] or None,
                speaker_names=(speaker_names or [])[:4] or None,
                previous_text=previous_text[-600:] if previous_text else None,
                topic=topic[:1600] if topic else None,
            )

        res = await asyncio.wait_for(asyncio.to_thread(_call), timeout=self._timeout_sec)
        log_event(
            logger,
            "secondary_stt_complete",
            model=self._model,
            format=self._format,
            detected_lang=res.get("detected_language_code"),
        )
        return res


@dataclass
class SecondaryComparisonResult:
    """Comparison between primary and secondary numeric/entity interpretations."""

    secondary_transcript: str
    secondary_extraction: ExtractionResult
    has_disagreement: bool
    disagreed_fields: list[str] = field(default_factory=list)
    candidate_values: dict[str, list[str]] = field(default_factory=dict)
    candidate_observations: dict[str, list[DynamicObservation]] = field(default_factory=dict)
    clarifications: list[FieldClarification] = field(default_factory=list)


def _norm_obs_value(obs: DynamicObservation | None) -> str | None:
    if obs is None or obs.value is None:
        return None
    if obs.key in {"temperature", "hemoglobin_g_dl"}:
        try:
            return format_decimal_clean(Decimal(str(obs.value)))
        except Exception:
            return str(obs.value).strip()
    return str(obs.value).strip()


def compare_numeric_interpretations(
    primary: ExtractionResult,
    secondary_transcript: str,
    *,
    extractor: VisitFieldExtractor,
    reference_date: date | None = None,
    active_language: str = "hi-IN",
    existing_draft: VisitDraft | None = None,
) -> SecondaryComparisonResult:
    """Compare primary vs secondary interpretations WITHOUT blindly picking a winner."""
    secondary_ext = extractor.extract(
        secondary_transcript,
        reference_date=reference_date,
        active_language=active_language,
        existing_draft=existing_draft,
    )

    disagreed: list[str] = []
    candidate_values: dict[str, list[str]] = {}
    candidate_observations: dict[str, list[DynamicObservation]] = {}
    clarifications: list[FieldClarification] = []

    for field_name in ("weight_kg", "next_visit_date", "beneficiary_id"):
        p_val = primary.patch.get(field_name)
        s_val = secondary_ext.patch.get(field_name)

        if field_name == "weight_kg":
            p_norm = format_decimal_clean(Decimal(str(p_val))) if p_val is not None else None
            s_norm = format_decimal_clean(Decimal(str(s_val))) if s_val is not None else None
        else:
            p_norm = str(p_val) if p_val is not None else None
            s_norm = str(s_val) if s_val is not None else None

        if p_norm != s_norm and (p_norm is not None or s_norm is not None):
            disagreed.append(field_name)
            vals = [v for v in (p_norm, s_norm) if v is not None]
            # Also collect candidate values from clarifications
            for cl in list(primary.clarifications) + list(secondary_ext.clarifications):
                if cl.field_name == field_name:
                    for c in cl.candidates:
                        if c not in vals:
                            vals.append(c)
            candidate_values[field_name] = vals
            if field_name == "weight_kg":
                if len(vals) == 1:
                    hint = f"I heard the weight as {vals[0]} kilograms. Is that correct?"
                else:
                    hint = (
                        f"I heard conflicting weights ({' or '.join(vals)} kilograms). "
                        "Which weight is correct?"
                    )
            elif field_name == "next_visit_date":
                hint = (
                    f"I heard the next visit date as {' or '.join(vals)}. "
                    "Please confirm the exact date."
                )
            else:
                hint = (
                    f"I heard beneficiary ID {' or '.join(vals)}. "
                    "Please confirm the correct beneficiary ID."
                )
            clarifications.append(
                FieldClarification(
                    field_name=field_name,
                    reason="conflict" if len(vals) > 1 else "ambiguous_value",
                    prompt_hint=hint,
                    candidates=vals,
                )
            )

    for obs_key in NUMERIC_OBSERVATION_KEYS:
        p_obs = next((o for o in primary.observations if o.key == obs_key), None)
        s_obs = next((o for o in secondary_ext.observations if o.key == obs_key), None)
        p_norm = _norm_obs_value(p_obs)
        s_norm = _norm_obs_value(s_obs)
        if p_norm != s_norm and (p_norm is not None or s_norm is not None):
            disagreed.append(obs_key)
            vals = [v for v in (p_norm, s_norm) if v is not None]
            candidate_values[obs_key] = vals
            candidate_observations[obs_key] = [o for o in (p_obs, s_obs) if o is not None]
            label_map = {
                "temperature": "temperature",
                "blood_pressure": "blood pressure",
                "hemoglobin_g_dl": "hemoglobin",
            }
            unit_s = ""
            ref_obs = p_obs or s_obs
            if ref_obs and ref_obs.unit:
                unit_s = f" {ref_obs.unit}"
            lbl = label_map.get(obs_key, obs_key)
            if len(vals) == 1:
                hint = f"I heard {lbl} as {vals[0]}{unit_s}. Is that correct?"
            else:
                hint = (
                    f"I heard conflicting {lbl} values ({' or '.join(vals)}{unit_s}). "
                    f"Which {lbl} is correct?"
                )
            clarifications.append(
                FieldClarification(
                    field_name=obs_key,
                    reason="conflict" if len(vals) > 1 else "ambiguous_value",
                    prompt_hint=hint,
                    candidates=vals,
                )
            )

    return SecondaryComparisonResult(
        secondary_transcript=secondary_transcript,
        secondary_extraction=secondary_ext,
        has_disagreement=len(disagreed) > 0,
        disagreed_fields=disagreed,
        candidate_values=candidate_values,
        candidate_observations=candidate_observations,
        clarifications=clarifications,
    )

