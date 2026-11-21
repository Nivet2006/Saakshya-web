"""Deterministic multilingual & code-mixed healthcare visit field extractor.

Extracts structured ASHA home-visit fields from Indic + English code-mixed ASR
transcripts without guessing missing facts, fabricating beneficiary IDs, or
performing clinical diagnosis / danger-sign classification.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.extraction.dates import (
    AMBIGUOUS_DATE_RE,
    find_date_candidates,
    resolve_date_candidates,
)
from app.extraction.models import (
    DynamicEvent,
    DynamicObservation,
    ExtractionResult,
    FieldClarification,
    FollowUpAction,
    UtteranceExtractionTrace,
    VisitDraft,
    VisitType,
)
from app.extraction.numbers import (
    INDIC_CHAR_CLASS,
    INDIC_DIGIT_TRANS,
    LB,
    QTY_PHRASE,
    RB,
    decimal_to_float,
    find_weight_candidates,
    format_decimal_clean,
    normalize_numeric_text,
    parse_decimal_phrase,
    resolve_beneficiary_id_mention,
    resolve_repeated_candidates,
)
from app.services.beneficiaries import (
    SyntheticBeneficiary,
    SyntheticBeneficiaryDirectory,
)

_INDIC_DIGIT_TRANS = INDIC_DIGIT_TRANS
_INDIC_CHAR_CLASS = INDIC_CHAR_CLASS
_LB = LB
_RB = RB
_QTY_PHRASE = QTY_PHRASE


def _normalize_text(text: str) -> str:
    """Normalize Unicode NFC, Indic numerals to ASCII digits, spaced decimals, and whitespace."""
    return normalize_numeric_text(text)


def _wb_pattern(phrase: str) -> str:
    """Build a token-bounded regex pattern safe for Latin and Indic scripts."""
    escaped = re.escape(phrase)
    escaped = escaped.replace(r"\ ", r"\s+")
    return rf"{_LB}{escaped}{_RB}"


def _parse_number_phrase(phrase: str) -> float | None:
    """Backward-compatible wrapper returning float from exact Decimal parser."""
    dec = parse_decimal_phrase(phrase)
    return decimal_to_float(dec) if dec is not None else None


# ---------------------------------------------------------------------------
# Visit type patterns
# ---------------------------------------------------------------------------

_VISIT_TYPE_PATTERNS: dict[VisitType, tuple[re.Pattern[str], ...]] = {
    "ANC": tuple(
        re.compile(_wb_pattern(p), re.IGNORECASE)
        for p in (
            "anc",
            "a.n.c",
            "antenatal",
            "ante-natal",
            "ante natal",
            "pregnancy checkup",
            "pregnancy visit",
            "pregnant visit",
            "pregnant checkup",
            "garbhavati",
            "garbhwati",
            "garbhavastha",
            "गर्भवती",
            "गर्भावस्था",
            "एएनसी",
            "प्रसव पूर्व",
            "गर्भ जांच",
            "ಗರ್ಭಿಣಿ",
            "கர்ப்பிணி",
        )
    ),
    "PNC": tuple(
        re.compile(_wb_pattern(p), re.IGNORECASE)
        for p in (
            "pnc",
            "p.n.c",
            "postnatal",
            "post-natal",
            "post natal",
            "postpartum",
            "post partum",
            "after delivery",
            "delivery ke baad",
            "prasav ke baad",
            "prasavottar",
            "जच्चा",
            "प्रसव के बाद",
            "डिलीवरी के बाद",
            "पीएनसी",
            "प्रसवोत्तर",
            "ಬಾಣಂತಿ",
            "பிரசவத்திற்கு பிறகு",
        )
    ),
    "Newborn": tuple(
        re.compile(_wb_pattern(p), re.IGNORECASE)
        for p in (
            "newborn",
            "new born",
            "hbnc",
            "h.b.n.c",
            "neonate",
            "neonatal",
            "navjat",
            "navjaat",
            "shishu",
            "baby checkup",
            "baby visit",
            "baby weight",
            "नवजात",
            "शिशु",
            "एचबीएनसी",
            "ನವಜಾತ",
            "பிறந்த குழந்தை",
        )
    ),
    "Immunisation": tuple(
        re.compile(_wb_pattern(p), re.IGNORECASE)
        for p in (
            "immunisation",
            "immunization",
            "tikakaran",
            "teekakaran",
            "vaccine visit",
            "vaccination visit",
            "tika visit",
            "टीकाकरण",
            "टीका विजिट",
            "ಲಸಿಕೆ",
            "தடுப்பூசி",
        )
    ),
}

_SECONDARY_NEWBORN_PATTERN = re.compile(_wb_pattern("baby"), re.IGNORECASE)
_SECONDARY_IMMUNISATION_PATTERN = re.compile(
    rf"{_LB}(?:vaccination|vaccines?){_RB}", re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Vaccination patterns
# ---------------------------------------------------------------------------

_VACCINE_SPECS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Hepatitis B", ("hepatitis b", "hep b", "hep-b", "hepb", "हेपेटाइटिस बी")),
    (
        "Pentavalent",
        (
            "pentavalent",
            "penta-1",
            "penta-2",
            "penta-3",
            "penta 1",
            "penta 2",
            "penta 3",
            "penta1",
            "penta2",
            "penta3",
            "penta",
            "पेंटावैलेंट",
            "पेंटा",
        ),
    ),
    ("Rotavirus", ("rotavirus", "rota virus", "rota", "rvv", "रोटावायरस", "रोटा")),
    (
        "OPV",
        (
            "opv-0",
            "opv-1",
            "opv-2",
            "opv-3",
            "opv 0",
            "opv 1",
            "opv 2",
            "opv 3",
            "opv0",
            "opv1",
            "opv2",
            "opv3",
            "opv",
            "o.p.v",
            "polio drops",
            "polio",
            "ओपीवी",
            "पोलियो",
        ),
    ),
    ("BCG", ("bcg", "b.c.g", "बीसीजी")),
    ("PCV", ("pcv-1", "pcv-2", "pcv booster", "pcv", "p.c.v", "pneumococcal", "पीसीवी")),
    ("IPV", ("fipv", "ipv-1", "ipv-2", "ipv", "i.p.v", "आईपीवी")),
    ("DPT", ("dpt booster", "dpt-1", "dpt-2", "dpt", "d.p.t", "डीपीटी")),
    (
        "MR",
        (
            "measles rubella",
            "measles-rubella",
            "measles",
            "mr-1",
            "mr-2",
            "mr 1",
            "mr 2",
            "mr1",
            "mr2",
            "mr",
            "m.r",
            "खसरा",
            "एमआर",
        ),
    ),
    (
        "Td",
        (
            "td booster",
            "td-1",
            "td-2",
            "td 1",
            "td 2",
            "td1",
            "td2",
            "td",
            "t.d",
            "टीडी",
        ),
    ),
    (
        "TT",
        (
            "tt booster",
            "tt-1",
            "tt-2",
            "tt 1",
            "tt 2",
            "tt1",
            "tt2",
            "tt",
            "t.t",
            "tetanus",
            "टीटी",
            "टी.टी",
            "टिटनेस",
        ),
    ),
)

_COMPILED_VACCINES: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...] = tuple(
    (name, tuple(re.compile(_wb_pattern(p), re.IGNORECASE) for p in aliases))
    for name, aliases in _VACCINE_SPECS
)

_VACCINE_DUE_CUES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(_wb_pattern(p), re.IGNORECASE)
    for p in (
        "not yet given",
        "not given",
        "not done",
        "not completed",
        "not received",
        "not taken",
        "not administered",
        "to be given",
        "still due",
        "pending",
        "overdue",
        "due",
        "remaining",
        "missed",
        "upcoming",
        "scheduled",
        "baaki",
        "baki",
        "bakaya",
        "nahi laga",
        "nahin laga",
        "nahi lagi",
        "nahin lagi",
        "nahi diya",
        "nahin diya",
        "nahi hua",
        "nahin hua",
        "nahi hui",
        "nahin hui",
        "abhi nahi",
        "dena hai",
        "lagna hai",
        "lagwana hai",
        "बाकी",
        "बकाया",
        "नहीं लगा",
        "नहीं लगी",
        "नहीं दिया",
        "नहीं हुआ",
        "नहीं हुई",
        "अभी नहीं",
        "देना है",
        "लगना है",
        "लगवाना है",
        "ಬಾಕಿ",
        "ಕೊಟ್ಟಿಲ್ಲ",
        "ಹಾಕಬೇಕು",
        "ಕೊಡಬೇಕು",
        "பாக்கி",
        "போடவில்லை",
        "போடணும்",
        "கொடுக்கணும்",
        "போட வேண்டும்",
        "நிலுவை",
    )
)

_VACCINE_COMPLETED_CUES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(_wb_pattern(p), re.IGNORECASE)
    for p in (
        "given",
        "done",
        "completed",
        "administered",
        "received",
        "taken",
        "finished",
        "vaccinated",
        "lag gaya",
        "lag gayi",
        "lag gai",
        "laga diya",
        "lag chuka",
        "lag chuki",
        "de diya",
        "de di",
        "ho gaya",
        "ho gayi",
        "ho gai",
        "mil gaya",
        "mil gayi",
        "போட்டாச்சு",
        "போட்டுவிட்டேன்",
        "கொடுத்தாச்சு",
        "போட்டேன்",
        "ಹಾಕಿದೆ",
        "ಕೊಟ್ಟಿದೆ",
        "ಲಸಿಕೆ ಹಾಕಲಾಗಿದೆ",
        "लग गया",
        "लग गई",
        "लगा दिया",
        "दे दिया",
        "हो गया",
        "हो गई",
        "मिल गया",
        "ಕೊಟ್ಟಿದೆ",
        "ಹಾಕಿದೆ",
        "போட்டாச்சு",
        "கொடுத்தாச்சு",
    )
)

# ---------------------------------------------------------------------------
# Follow-up action cues
# ---------------------------------------------------------------------------

_IFA_NON_ADHERENCE_RE = re.compile(
    rf"(?:"
    rf"{_LB}(?:ifa|iron|calcium|आयरन|आईएफए|कैल्शियम)[^,.;।]{{0,45}}"
    rf"(?:nahi\s+le|nahin\s+le|nahi\s+kha|nahin\s+kha|not\s+taking|not\s+regular|irregular|missed|skipped|chhoot|chhut|नहीं\s+ले|नहीं\s+खा|छूट\s+गई){_RB}|"
    rf"{_LB}(?:not\s+taking|missed|skipped|irregular(?:\s+with)?)\s+(?:the\s+)?"
    rf"(?:ifa|iron|calcium)(?:\s+(?:tablets?|pills?|goli))?{_RB}"
    rf")",
    re.IGNORECASE,
)

_WEIGHT_MONITOR_RE = re.compile(
    rf"{_LB}(?:recheck\s+weight|monitor\s+weight|weight\s+monitoring|weight\s+check\s+karna|vajan\s+dobara|wajan\s+dobara|वजन\s+दोबारा){_RB}",
    re.IGNORECASE,
)

_FOLLOWUP_VISIT_CUE_RE = re.compile(
    rf"{_LB}(?:next\s+visit|follow[\s\-]?up(?:\s+visit)?|agla\s+visit|agli\s+visit|अगला\s+विजिट|अगली\s+विजिट|dobara\s+aana|दोबारा\s+आना){_RB}",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Voice correction intent cues
# ---------------------------------------------------------------------------

_CORRECTION_COMMA_RE = re.compile(
    rf"{_LB}(?:no|nahi|nahin|नहीं|नही)(?:\s*[,.:!।\-]\s*(?:no|nahi|nahin|नहीं|नही))*\s*[,.:!।\-]",
    re.IGNORECASE,
)
_CORRECTION_START_RE = re.compile(
    r"^\s*(?:no|nope|nahi|nahin|sorry|wait|actually|correction|नहीं|नही|गलत|माफ\s+कीजिए)\s+"
    r"(?!(?:fever|bleeding|headache|swelling|danger|problem|issue|symptom|symptoms|"
    r"bukhar|dard|sujan|dikkat|takleef|complication|complications)\b)",
    re.IGNORECASE,
)
_CORRECTION_INLINE_RE = re.compile(
    rf"{_LB}(?:galat|गलत|गलती\s+से|wrong|incorrect|incorrectly|mistake|actually|correction|correct\s+that|"
    rf"the\s+correct\s+(?:weight|date|next\s+visit|visit|beneficiary|value)|"
    rf"(?:it|weight|date|next\s+visit)\s+should\s+be|should\s+be|"
    rf"make\s+(?:it|that)|"
    rf"change\s+(?:it|the|weight|visit|date|next\s+visit|beneficiary|vaccine|vaccination)|"
    rf"update\s+(?:it|the|weight|visit|date|next\s+visit|beneficiary|vaccine|vaccination)|"
    rf"i\s+meant|i\s+said\s+that\s+incorrectly|i\s+forgot\s+to\s+(?:mention|add)|forgot\s+to\s+(?:mention|add)|"
    rf"that\s+was\s+(?:the\s+)?birth\s+weight|today'?s\s+weight|previous\s+(?:date|weight)\s+was\s+wrong|"
    rf"instead|badal\s+do|badlo|sahi\s+karo|theek\s+karo|बदलो|बदल\s+दो|बदलें|सही\s+करें|दरअसल|आज\s+का\s+वजन|"
    rf"ತಪ್ಪಾಗಿದೆ|ಬದಲಾಯಿಸಿ|ನಿಜವಾಗಿ|தவறு|மாற்று|உண்மையில்){_RB}",
    re.IGNORECASE,
)

# Category <-> VisitType compatibility for disambiguation
_VISIT_TYPE_CATEGORIES: dict[VisitType, frozenset[str]] = {
    "ANC": frozenset({"pregnant_woman"}),
    "PNC": frozenset({"postnatal_mother"}),
    "Newborn": frozenset({"newborn"}),
    "Immunisation": frozenset({"infant", "newborn", "pregnant_woman"}),
}


class VisitFieldExtractor:
    """Deterministic extractor & validator for structured ASHA home-visit drafts."""

    def __init__(
        self,
        beneficiary_directory: SyntheticBeneficiaryDirectory | None = None,
        timezone_name: str = "Asia/Kolkata",
    ) -> None:
        self._directory = beneficiary_directory or SyntheticBeneficiaryDirectory()
        self._timezone_name = timezone_name

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(
        self,
        text: str,
        *,
        reference_date: date | None = None,
        active_language: str = "hi-IN",
        existing_draft: VisitDraft | None = None,
    ) -> ExtractionResult:
        """Extract only fields grounded in `text`; never guess missing facts."""
        _ = active_language  # Retained for interface parity and future locale hints
        normalized = _normalize_text(text)
        if not normalized:
            return ExtractionResult()

        try:
            tz = ZoneInfo(self._timezone_name)
        except Exception:
            tz = timezone(timedelta(hours=5, minutes=30))
        ref_date = reference_date or datetime.now(tz).date()

        patch: dict[str, Any] = {}
        clarifications: list[FieldClarification] = []
        provenance: dict[str, str] = {}

        # 1. Correction intent detection
        detected_correction = self._detect_correction(normalized)

        # 2. Visit type (extracted early so it can help disambiguate beneficiary & weight bounds)
        visit_type, vt_source, vt_clar = self._extract_visit_type(normalized)
        if visit_type is not None:
            patch["visit_type"] = visit_type
            if vt_source:
                provenance["visit_type"] = vt_source
        if vt_clar is not None:
            clarifications.append(vt_clar)

        effective_visit_type: VisitType | None = visit_type or (
            existing_draft.visit_type if existing_draft else None
        )

        # 3. Beneficiary resolution against SyntheticBeneficiaryDirectory
        ben, ben_source, ben_clar, ben_inline_corr = self._extract_beneficiary(
            normalized, effective_visit_type=effective_visit_type
        )
        if ben_inline_corr:
            detected_correction = True
        if ben is not None:
            patch["beneficiary_id"] = ben.beneficiary_id
            patch["beneficiary_name"] = ben.full_name
            if ben_source:
                provenance["beneficiary_id"] = ben_source
                provenance["beneficiary_name"] = ben_source
        if ben_clar is not None:
            clarifications.append(ben_clar)

        effective_ben: SyntheticBeneficiary | None = ben
        if effective_ben is None and existing_draft and existing_draft.beneficiary_id:
            effective_ben = self._directory.get_by_id(existing_draft.beneficiary_id)

        # 4. Weight normalization & physiological bounds validation (exact Decimal)
        weight_kg, weight_source, weight_clar, unusual_weight, wt_inline_corr, weight_unit_kind = self._extract_weight(
            normalized,
            effective_visit_type=effective_visit_type,
            effective_beneficiary=effective_ben,
        )
        if wt_inline_corr:
            detected_correction = True
        extracted_numbers: list[dict[str, Any]] = []
        if weight_kg is not None:
            patch["weight_kg"] = weight_kg
            if weight_source:
                patch["weight_source_text"] = weight_source
                provenance["weight_kg"] = weight_source
            extracted_numbers.append(
                {
                    "field": "weight_kg",
                    "value": weight_kg,
                    "normalized_decimal": format_decimal_clean(Decimal(str(weight_kg))),
                    "unit": "kg",
                    "source_unit": weight_unit_kind,
                    "source_text": weight_source or "",
                    "status": "draft",
                }
            )
        elif unusual_weight is not None:
            u_val, u_src = unusual_weight
            extracted_numbers.append(
                {
                    "field": "weight_kg",
                    "value": u_val,
                    "normalized_decimal": format_decimal_clean(Decimal(str(u_val))),
                    "unit": "kg",
                    "source_unit": weight_unit_kind,
                    "source_text": u_src,
                    "status": "needs_confirmation",
                }
            )
        if weight_clar is not None:
            clarifications.append(weight_clar)

        # 5. Vaccinations (completed vs due)
        v_completed, v_due, v_prov, v_clars = self._extract_vaccinations(normalized)
        if v_completed:
            patch["vaccinations_completed"] = v_completed
            if "vaccinations_completed" in v_prov:
                provenance["vaccinations_completed"] = v_prov["vaccinations_completed"]
        if v_due:
            patch["vaccinations_due"] = v_due
            if "vaccinations_due" in v_prov:
                provenance["vaccinations_due"] = v_prov["vaccinations_due"]
        clarifications.extend(v_clars)

        # 6. Next visit date (ISO YYYY-MM-DD)
        next_date, date_source, date_clar, date_inline_corr = self._extract_next_visit_date(
            normalized, reference_date=ref_date
        )
        if date_inline_corr:
            detected_correction = True
        if next_date is not None:
            patch["next_visit_date"] = next_date
            if date_source:
                patch["next_visit_date_source_text"] = date_source
                provenance["next_visit_date"] = date_source
        if date_clar is not None:
            clarifications.append(date_clar)

        # 6b. Bare numeric weight correction fallback (e.g. "No, it is fifty-three." or "No, it is 3.2." or "Actually, 2.8.")
        if (
            weight_kg is None
            and weight_clar is None
            and detected_correction
            and next_date is None
            and date_clar is None
            and not v_completed
            and not v_due
            and ben is None
            and visit_type is None
        ):
            m_bare = re.search(
                rf"(?:it\s+should\s+be|should\s+be|make\s+(?:it|that)|it\s+is|is|hai|है|actually|correction|meant|no[, ]+|nahi[, ]+|नहीं[, ]+)\s*(?P<qty>{_LB}{_QTY_PHRASE}{_RB})",
                normalized,
                re.IGNORECASE,
            )
            if m_bare:
                bare_dec = parse_decimal_phrase(m_bare.group("qty"))
                if bare_dec is not None:
                    bare_val = decimal_to_float(bare_dec, places=3)
                    min_kg, max_kg, _ctx = self._weight_bounds(
                        effective_visit_type=effective_visit_type,
                        effective_beneficiary=effective_ben,
                        text=normalized,
                    )
                    if min_kg <= bare_val <= max_kg:
                        weight_kg = bare_val
                        weight_source = m_bare.group("qty").strip()
                        patch["weight_kg"] = weight_kg
                        patch["weight_source_text"] = weight_source
                        provenance["weight_kg"] = weight_source
                        extracted_numbers.append(
                            {
                                "field": "weight_kg",
                                "value": weight_kg,
                                "normalized_decimal": format_decimal_clean(bare_dec),
                                "unit": "kg",
                                "source_unit": "unitless",
                                "source_text": weight_source,
                                "status": "draft",
                            }
                        )

        # 7. Grounded follow-up actions
        actions = self._derive_follow_up_actions(
            normalized,
            vaccinations_due=v_due,
            next_visit_date=next_date,
            date_source=date_source,
        )
        if actions:
            patch["follow_up_actions"] = actions

        # 7b. Dynamic observations, repeatable events & explicit removals
        dynamic_observations, obs_numbers = self._extract_dynamic_observations(
            normalized,
            unusual_weight=unusual_weight,
            has_structured_fields=bool(patch),
        )
        extracted_numbers.extend(obs_numbers)
        dynamic_events = self._build_dynamic_events(
            v_completed=v_completed,
            v_due=v_due,
            v_prov=v_prov,
            next_date=next_date,
        )
        remove_obs_keys, remove_event_names = self._extract_removals(
            normalized, existing_draft=existing_draft
        )

        # Identify corrected fields when correction intent OR contextual replacement is detected
        if not detected_correction and existing_draft is not None:
            word_count = len(normalized.split())
            if (
                "weight_kg" in patch
                and existing_draft.weight_kg is not None
                and patch["weight_kg"] != existing_draft.weight_kg
                and word_count <= 8
            ):
                detected_correction = True
            elif (
                "next_visit_date" in patch
                and existing_draft.next_visit_date is not None
                and patch["next_visit_date"] != existing_draft.next_visit_date
                and word_count <= 10
            ):
                detected_correction = True

        # Ambiguous standalone bare number without unit when weight already exists (Section 3)
        if (
            weight_kg is None
            and weight_clar is None
            and next_date is None
            and date_clar is None
            and not v_completed
            and not v_due
            and ben is None
            and visit_type is None
            and existing_draft is not None
            and existing_draft.weight_kg is not None
            and len(normalized.split()) <= 3
        ):
            bare_dec = parse_decimal_phrase(normalized)
            if bare_dec is not None:
                bare_only = decimal_to_float(bare_dec, places=3)
                min_kg, max_kg, _ctx = self._weight_bounds(
                    effective_visit_type=effective_visit_type,
                    effective_beneficiary=effective_ben,
                    text=normalized,
                )
                if min_kg <= bare_only <= max_kg and bare_only != existing_draft.weight_kg:
                    val_str = format_decimal_clean(bare_dec)
                    clarifications.append(
                        FieldClarification(
                            field_name="weight_kg",
                            reason="ambiguous_value",
                            prompt_hint=(
                                f"Do you want me to update the previously recorded weight "
                                f"to {val_str} kilograms?"
                            ),
                            candidates=[val_str],
                        )
                    )

        corrected_fields: list[str] = []
        if detected_correction:
            for key in (
                "beneficiary_id",
                "visit_type",
                "weight_kg",
                "vaccinations_completed",
                "vaccinations_due",
                "next_visit_date",
            ):
                if key in patch:
                    corrected_fields.append(key)
            # Only list follow_up_actions as a corrected field when an explicit
            # standalone action (e.g. ifa_adherence / weight_monitoring) was mentioned,
            # not merely a derived routine_visit/vaccination action from date/vaccine fields.
            if any(
                a.action_type in {"ifa_adherence", "weight_monitoring", "other"}
                for a in actions
            ):
                corrected_fields.append("follow_up_actions")
            non_sup_obs = [o for o in dynamic_observations if o.key != "supplement_adherence"]
            if non_sup_obs or (dynamic_observations and "follow_up_actions" not in corrected_fields):
                corrected_fields.append("observations")
            if dynamic_events and "vaccinations_completed" not in corrected_fields and "vaccinations_due" not in corrected_fields:
                corrected_fields.append("events")

        extraction_status = "no_entities"
        if clarifications:
            extraction_status = "clarification_needed"
        elif detected_correction or remove_obs_keys or remove_event_names:
            extraction_status = "corrected"
        elif patch or dynamic_observations or dynamic_events:
            extraction_status = "extracted"

        trace = UtteranceExtractionTrace(
            raw_transcript=text,
            finalized_transcript=text,
            normalized_transcript=normalized,
            detected_entities={
                "fields": {
                    k: (
                        [a.model_dump() for a in v]
                        if k == "follow_up_actions"
                        else v
                    )
                    for k, v in patch.items()
                },
                "observations": [o.model_dump() for o in dynamic_observations],
                "events": [e.model_dump() for e in dynamic_events],
                "removals": {
                    "observation_keys": remove_obs_keys,
                    "event_names": remove_event_names,
                },
            },
            extracted_numbers=extracted_numbers,
            source_phrases=dict(provenance),
            extraction_status=extraction_status,
        )

        return ExtractionResult(
            patch=patch,
            clarifications=clarifications,
            detected_correction=detected_correction,
            corrected_fields=corrected_fields,
            provenance=provenance,
            observations=dynamic_observations,
            events=dynamic_events,
            remove_observation_keys=remove_obs_keys,
            remove_event_names=remove_event_names,
            trace=trace,
        )

    def apply_to_draft(
        self,
        draft: VisitDraft,
        result: ExtractionResult,
        *,
        correction_mode: bool = False,
    ) -> VisitDraft:
        """Apply an `ExtractionResult` patch onto `draft`, returning a new `VisitDraft`.

        Safety guarantees:
        - Preserves all unmentioned fields during corrections.
        - NEVER clears `danger_sign_flagged` or removes existing `danger_signs`.
        - NEVER silently overwrites confirmed fields with null or uncertain values.
        - Clears `status="confirmed"` back to `"draft"` if a confirmed field is modified.
        """
        updated = draft.model_copy(deep=True)
        is_correction = correction_mode or result.detected_correction
        confirmed_set = set(updated.confirmed_fields)
        changed_confirmed = False

        # Protect safety-critical danger-sign fields unconditionally
        preserved_danger_flag = updated.danger_sign_flagged
        preserved_danger_signs = list(updated.danger_signs)

        patch = result.patch

        # Scalar fields
        scalar_pairs: tuple[tuple[str, str | None], ...] = (
            ("beneficiary_id", "beneficiary_name"),
            ("visit_type", None),
            ("weight_kg", "weight_source_text"),
            ("next_visit_date", "next_visit_date_source_text"),
        )
        for field_name, companion_field in scalar_pairs:
            if field_name not in patch:
                continue
            new_val = patch[field_name]
            if new_val is None:
                # Never overwrite an existing or confirmed field with null
                continue
            current_val = getattr(updated, field_name)
            if field_name in confirmed_set and not is_correction:
                # Never silently overwrite a confirmed field outside correction mode
                continue
            setattr(updated, field_name, new_val)
            if companion_field and companion_field in patch and patch[companion_field] is not None:
                setattr(updated, companion_field, patch[companion_field])
            if field_name in confirmed_set and new_val != current_val:
                confirmed_set.discard(field_name)
                changed_confirmed = True

        # Vaccinations completed
        if "vaccinations_completed" in patch and patch["vaccinations_completed"]:
            new_completed: list[str] = list(patch["vaccinations_completed"])
            if "vaccinations_completed" not in confirmed_set or is_correction:
                merged_completed = _dedupe_preserve_order(
                    updated.vaccinations_completed + new_completed
                )
                if (
                    "vaccinations_completed" in confirmed_set
                    and merged_completed != updated.vaccinations_completed
                ):
                    confirmed_set.discard("vaccinations_completed")
                    changed_confirmed = True
                updated.vaccinations_completed = merged_completed
                # If a vaccine is now completed, remove it from vaccinations_due
                completed_lower = {v.lower() for v in new_completed}
                updated.vaccinations_due = [
                    v for v in updated.vaccinations_due if v.lower() not in completed_lower
                ]

        # Vaccinations due
        if "vaccinations_due" in patch and patch["vaccinations_due"]:
            new_due: list[str] = list(patch["vaccinations_due"])
            if "vaccinations_due" not in confirmed_set or is_correction:
                merged_due = _dedupe_preserve_order(updated.vaccinations_due + new_due)
                if "vaccinations_due" in confirmed_set and merged_due != updated.vaccinations_due:
                    confirmed_set.discard("vaccinations_due")
                    changed_confirmed = True
                updated.vaccinations_due = merged_due
                if is_correction:
                    due_lower = {v.lower() for v in new_due}
                    updated.vaccinations_completed = [
                        v
                        for v in updated.vaccinations_completed
                        if v.lower() not in due_lower
                    ]

        # Follow-up actions: merge without dropping existing grounded/danger actions
        if "follow_up_actions" in patch and patch["follow_up_actions"]:
            incoming_actions = [
                a if isinstance(a, FollowUpAction) else FollowUpAction.model_validate(a)
                for a in patch["follow_up_actions"]
            ]
            existing_actions = list(updated.follow_up_actions)
            for inc in incoming_actions:
                # Whenever next_visit_date is set or updated, keep a single current routine_visit action
                if inc.action_type == "routine_visit" and inc.due_date:
                    existing_actions = [
                        a for a in existing_actions if a.action_type != "routine_visit"
                    ]
                if not any(
                    a.action_type == inc.action_type
                    and a.description == inc.description
                    and a.due_date == inc.due_date
                    for a in existing_actions
                ):
                    existing_actions.append(inc)
            updated.follow_up_actions = existing_actions

        # Dynamic observations: upsert by normalized key, remove explicit deletions
        if result.remove_observation_keys:
            rm_obs = {k.strip().lower() for k in result.remove_observation_keys}
            updated.observations = [
                o for o in updated.observations if o.key.strip().lower() not in rm_obs
            ]
        for obs in result.observations:
            replaced = False
            for idx, existing_obs in enumerate(updated.observations):
                if existing_obs.key.lower() == obs.key.lower():
                    updated.observations[idx] = obs
                    replaced = True
                    break
            if not replaced:
                updated.observations.append(obs)
        # If weight_kg was confirmed cleanly via scalar patch, clear any stale needs_confirmation weight observation
        if "weight_kg" in patch and patch["weight_kg"] is not None:
            updated.observations = [
                o for o in updated.observations if o.key.lower() != "weight_kg"
            ]

        # Repeatable events (immunisation etc.): upsert in-place by (event_type, name.lower())
        if result.remove_event_names:
            rm_ev = {n.strip().lower() for n in result.remove_event_names}
            updated.events = [
                e for e in updated.events if e.name.strip().lower() not in rm_ev
            ]
            # Also reflect removal in legacy vaccine arrays
            updated.vaccinations_completed = [
                v for v in updated.vaccinations_completed if v.strip().lower() not in rm_ev
            ]
            updated.vaccinations_due = [
                v for v in updated.vaccinations_due if v.strip().lower() not in rm_ev
            ]
        for ev in result.events:
            replaced = False
            for idx, existing_ev in enumerate(updated.events):
                if (
                    existing_ev.event_type.lower() == ev.event_type.lower()
                    and existing_ev.name.lower() == ev.name.lower()
                ):
                    updated.events[idx] = ev
                    replaced = True
                    break
            if not replaced:
                updated.events.append(ev)

        if result.trace is not None:
            updated.utterance_traces.append(result.trace)

        # Update clarifications: clear resolved fields, upsert newly emitted clarifications
        resolved_fields = {k for k, v in patch.items() if v is not None and v != []}
        clar_by_field: dict[str, FieldClarification] = {
            c.field_name: c
            for c in updated.clarifications_needed
            if c.field_name not in resolved_fields
        }
        for new_clar in result.clarifications:
            if new_clar.field_name not in resolved_fields:
                clar_by_field[new_clar.field_name] = new_clar
        updated.clarifications_needed = list(clar_by_field.values())

        # Reflect confirmation / draft status update
        updated.confirmed_fields = [f for f in updated.confirmed_fields if f in confirmed_set]
        if changed_confirmed and updated.status == "confirmed":
            updated.status = "draft"

        # Restore safety-critical danger-sign invariants unconditionally
        updated.danger_sign_flagged = preserved_danger_flag or updated.danger_sign_flagged
        updated.danger_signs = _dedupe_preserve_order(
            preserved_danger_signs + list(updated.danger_signs)
        )

        return updated

    # ------------------------------------------------------------------
    # Private extractors
    # ------------------------------------------------------------------

    def _detect_correction(self, text: str) -> bool:
        if _CORRECTION_COMMA_RE.search(text):
            return True
        if _CORRECTION_START_RE.search(text):
            return True
        return bool(_CORRECTION_INLINE_RE.search(text))

    def _extract_visit_type(
        self, text: str
    ) -> tuple[VisitType | None, str | None, FieldClarification | None]:
        matched_types: dict[VisitType, str] = {}
        negated_types: set[VisitType] = set()

        for vtype, patterns in _VISIT_TYPE_PATTERNS.items():
            for pat in patterns:
                m = pat.search(text)
                if m:
                    # Check immediate negation before/after match (e.g. "not ANC", "ANC nahi")
                    before = text[max(0, m.start() - 18) : m.start()].lower()
                    after = text[m.end() : min(len(text), m.end() + 18)].lower()
                    if re.search(r"\b(?:not|no|nahi|nahin|नहीं)\s*$", before) or re.match(
                        r"^\s*(?:nahi|nahin|नहीं)\b", after
                    ):
                        negated_types.add(vtype)
                        continue
                    matched_types[vtype] = m.group(0)
                    break

        # Secondary cues only if no primary visit type matched
        if not matched_types:
            m_baby = _SECONDARY_NEWBORN_PATTERN.search(text)
            if m_baby:
                matched_types["Newborn"] = m_baby.group(0)
            else:
                m_imm = _SECONDARY_IMMUNISATION_PATTERN.search(text)
                if m_imm:
                    matched_types["Immunisation"] = m_imm.group(0)

        if not matched_types:
            return None, None, None

        if len(matched_types) == 1:
            vtype, src = next(iter(matched_types.items()))
            return vtype, src, None

        # If Immunisation + another primary type co-occur, check whether Immunisation was
        # explicitly framed as the visit type ("immunisation visit") vs incidental mention.
        if "Immunisation" in matched_types and len(matched_types) == 2:
            imm_src = matched_types["Immunisation"].lower()
            other_type = next(k for k in matched_types if k != "Immunisation")
            if "visit" in imm_src or "tikakaran" in imm_src or "टीकाकरण" in imm_src:
                return "Immunisation", matched_types["Immunisation"], None
            return other_type, matched_types[other_type], None

        # Genuine conflict between multiple visit types (e.g. "ANC and PNC")
        candidates = list(matched_types.keys())
        return (
            None,
            None,
            FieldClarification(
                field_name="visit_type",
                reason=f"Multiple visit types mentioned in utterance: {', '.join(candidates)}.",
                prompt_hint="Please confirm whether this visit is "
                + " or ".join(candidates)
                + ".",
                candidates=candidates,
            ),
        )

    def _extract_beneficiary(
        self,
        text: str,
        *,
        effective_visit_type: VisitType | None = None,
    ) -> tuple[SyntheticBeneficiary | None, str | None, FieldClarification | None, bool]:
        # 1. Explicit beneficiary ID lookup (handles BEN-1042, BE. N 1044, spoken digits, repeated corrections)
        spoken_id, id_src, id_corr, id_conflicts = resolve_beneficiary_id_mention(text)
        if id_conflicts:
            return (
                None,
                None,
                FieldClarification(
                    field_name="beneficiary_id",
                    reason="conflict",
                    prompt_hint=f"I heard multiple beneficiary IDs ({' or '.join(id_conflicts)}). Which beneficiary ID is correct?",
                    candidates=id_conflicts,
                ),
                False,
            )
        if spoken_id:
            found = self._directory.get_by_id(spoken_id)
            if found is not None:
                return found, id_src or spoken_id, None, id_corr
            if re.search(r"\b(?:b[\s.]*e[\s.]*n|id)\b", text, re.IGNORECASE):
                return (
                    None,
                    None,
                    FieldClarification(
                        field_name="beneficiary_id",
                        reason=f"Beneficiary ID {spoken_id} was not found in the synthetic directory.",
                        prompt_hint=f"I could not find {spoken_id} in the beneficiary list. Please repeat the beneficiary's name or ID.",
                        candidates=[],
                    ),
                    id_corr,
                )

        all_bens = self._directory.list_all()
        text_lower = text.lower()

        # 2. Exact full-name matches (prefer longest match, e.g., "Baby of Kavitha Rao" > "Kavitha Rao")
        full_matches: list[tuple[int, SyntheticBeneficiary, str]] = []
        for ben in all_bens:
            pat = re.compile(_wb_pattern(ben.full_name), re.IGNORECASE)
            m = pat.search(text)
            if m:
                full_matches.append((len(ben.full_name), ben, m.group(0)))
        if full_matches:
            max_len = max(item[0] for item in full_matches)
            top = [(b, s) for length, b, s in full_matches if length == max_len]
            if len(top) == 1:
                return top[0][0], top[0][1], None, False
            res_b, res_s, res_c = self._resolve_or_clarify_candidates(
                [b for b, _ in top],
                source_text=top[0][1],
                text_lower=text_lower,
                effective_visit_type=effective_visit_type,
            )
            return res_b, res_s, res_c, False

        # 3. Multi-word alias matches (e.g., "lakshmi narayanan", "kavitha baby", "kavitha newborn")
        multi_matches: list[tuple[int, SyntheticBeneficiary, str]] = []
        for ben in all_bens:
            for alias in ben.aliases:
                if " " not in alias.strip():
                    continue
                m = re.search(_wb_pattern(alias), text, re.IGNORECASE)
                if m:
                    multi_matches.append((len(alias), ben, m.group(0)))
                    break
        if multi_matches:
            max_len = max(item[0] for item in multi_matches)
            top_bens: list[SyntheticBeneficiary] = []
            top_src = ""
            seen_ids: set[str] = set()
            for length, b, s in multi_matches:
                if length == max_len and b.beneficiary_id not in seen_ids:
                    seen_ids.add(b.beneficiary_id)
                    top_bens.append(b)
                    top_src = top_src or s
            if len(top_bens) == 1:
                return top_bens[0], top_src, None, False
            res_b, res_s, res_c = self._resolve_or_clarify_candidates(
                top_bens,
                source_text=top_src,
                text_lower=text_lower,
                effective_visit_type=effective_visit_type,
            )
            return res_b, res_s, res_c, False

        # 4. Single-word alias & first-name matches across ALL beneficiaries
        candidates: list[SyntheticBeneficiary] = []
        seen_ids = set()
        matched_term = ""

        # Collect single-word triggers per beneficiary
        for ben in all_bens:
            tokens_to_check: list[str] = []
            for alias in ben.aliases:
                alias_s = alias.strip()
                if alias_s and " " not in alias_s:
                    tokens_to_check.append(alias_s)
            name_parts = ben.full_name.split()
            # Include first name token for regular person names (skip "Baby of ...")
            if name_parts and name_parts[0].lower() != "baby":
                first_tok = name_parts[0]
                if first_tok.lower() not in {t.lower() for t in tokens_to_check}:
                    tokens_to_check.append(first_tok)

            for tok in tokens_to_check:
                m = re.search(_wb_pattern(tok), text, re.IGNORECASE)
                if m:
                    if ben.beneficiary_id not in seen_ids:
                        seen_ids.add(ben.beneficiary_id)
                        candidates.append(ben)
                        matched_term = matched_term or m.group(0)
                    break

        # Special handling for newborn/baby of a matched mother (e.g., "Kavitha ka newborn visit" -> BEN-1044)
        if candidates and (
            effective_visit_type == "Newborn"
            or re.search(
                rf"{_LB}(?:baby|newborn|navjat|navjaat|shishu|bachcha|bacha|नवजात|शिशु){_RB}",
                text,
                re.IGNORECASE,
            )
        ):
            baby_matches: list[SyntheticBeneficiary] = []
            for ben in all_bens:
                if ben.category == "newborn" and ben.full_name.lower().startswith("baby of "):
                    mother_name = ben.full_name[8:].strip().lower()
                    for cand in candidates:
                        if cand.full_name.lower() == mother_name or (
                            cand.full_name.split()[0].lower() in mother_name
                        ):
                            baby_matches.append(ben)
                            break
            if len(baby_matches) == 1:
                return baby_matches[0], matched_term, None, False

        if not candidates:
            return None, None, None, False

        if len(candidates) == 1:
            return candidates[0], matched_term, None, False

        res_b, res_s, res_c = self._resolve_or_clarify_candidates(
            candidates,
            source_text=matched_term,
            text_lower=text_lower,
            effective_visit_type=effective_visit_type,
        )
        return res_b, res_s, res_c, False

    def _resolve_or_clarify_candidates(
        self,
        candidates: list[SyntheticBeneficiary],
        *,
        source_text: str,
        text_lower: str,
        effective_visit_type: VisitType | None,
    ) -> tuple[SyntheticBeneficiary | None, str | None, FieldClarification | None]:
        remaining = list(candidates)

        # Disambiguate by village / ward mention
        village_hits: list[SyntheticBeneficiary] = []
        for ben in remaining:
            village_tokens = [
                tok
                for tok in re.findall(r"[a-z0-9]+", ben.village.lower())
                if tok not in {"demo", "ward"} and len(tok) >= 3
            ]
            if any(re.search(_wb_pattern(vt), text_lower) for vt in village_tokens):
                village_hits.append(ben)
        if len(village_hits) == 1:
            return village_hits[0], source_text, None
        if village_hits:
            remaining = village_hits

        # Disambiguate by surname / second name token
        surname_hits: list[SyntheticBeneficiary] = []
        for ben in remaining:
            parts = ben.full_name.lower().split()
            if len(parts) >= 2 and any(
                re.search(_wb_pattern(p), text_lower) for p in parts[1:] if len(p) >= 2
            ):
                surname_hits.append(ben)
        if len(surname_hits) == 1:
            return surname_hits[0], source_text, None
        if surname_hits:
            remaining = surname_hits

        # Disambiguate by visit type <-> beneficiary category
        if effective_visit_type is not None:
            allowed_cats = _VISIT_TYPE_CATEGORIES.get(effective_visit_type, frozenset())
            cat_hits = [b for b in remaining if b.category in allowed_cats]
            if len(cat_hits) == 1:
                return cat_hits[0], source_text, None
            if cat_hits:
                remaining = cat_hits

        # Still ambiguous -> emit FieldClarification and NEVER fabricate an ID
        candidate_labels = [
            f"{b.beneficiary_id}: {b.full_name} ({b.village})" for b in remaining
        ]
        short_options = " or ".join(f"{b.full_name} ({b.beneficiary_id})" for b in remaining)
        return (
            None,
            None,
            FieldClarification(
                field_name="beneficiary_id",
                reason=f"Multiple beneficiaries match '{source_text}'.",
                prompt_hint=f"Multiple records match {source_text}. Did you mean {short_options}?",
                candidates=candidate_labels,
            ),
        )

    def _extract_weight(
        self,
        text: str,
        *,
        effective_visit_type: VisitType | None,
        effective_beneficiary: SyntheticBeneficiary | None,
    ) -> tuple[float | None, str | None, FieldClarification | None, tuple[float, str] | None, bool, str | None]:
        candidates = find_weight_candidates(text)
        if not candidates:
            return None, None, None, None, False, None

        selected, inline_corr, conflicts = resolve_repeated_candidates(text, candidates)
        if conflicts:
            cand_strs = [format_decimal_clean(c.value_kg) for c in conflicts]
            return (
                None,
                None,
                FieldClarification(
                    field_name="weight_kg",
                    reason="conflict",
                    prompt_hint=(
                        f"I heard conflicting weights ({' or '.join(cand_strs)} kilograms). "
                        "Which weight is correct?"
                    ),
                    candidates=cand_strs,
                ),
                None,
                False,
                None,
            )

        assert selected is not None
        source_text = re.sub(
            r"(?:[\s,]+(?:and|aur|और))+$", "", selected.source_text.strip(), flags=re.IGNORECASE
        )
        weight_kg = decimal_to_float(selected.value_kg, places=3)
        weight_str = format_decimal_clean(selected.value_kg)

        # Physiological bounds validation: retain unusual value cleanly as uncertain/needs_confirmation
        min_kg, max_kg, context_label = self._weight_bounds(
            effective_visit_type=effective_visit_type,
            effective_beneficiary=effective_beneficiary,
            text=text,
        )
        if weight_kg < min_kg or weight_kg > max_kg:
            # Special unit-clarification hint for unitless newborn gram figures (e.g. "weight is 2800")
            if (
                not selected.has_explicit_unit
                and context_label == "newborn/infant"
                and 400 <= weight_kg <= 9999
            ):
                kg_from_g = format_decimal_clean(selected.value_kg / Decimal("1000"))
                hint = (
                    f"I heard {source_text}. Did you mean {int(weight_kg)} grams "
                    f"({kg_from_g} kilograms)? Is that correct?"
                )
            else:
                hint = (
                    f"I heard {source_text} ({weight_str} kg), which seems unusual for a "
                    f"{context_label} record. Should I keep {weight_str} kg or would you like to correct it?"
                )
            return (
                None,
                None,
                FieldClarification(
                    field_name="weight_kg",
                    reason="ambiguous_value",
                    prompt_hint=hint,
                    candidates=[weight_str],
                ),
                (weight_kg, source_text or f"{weight_str} kg"),
                inline_corr,
                selected.unit_kind,
            )

        return weight_kg, source_text, None, None, inline_corr, selected.unit_kind

    def _weight_bounds(
        self,
        *,
        effective_visit_type: VisitType | None,
        effective_beneficiary: SyntheticBeneficiary | None,
        text: str,
    ) -> tuple[float, float, str]:
        if effective_visit_type == "Newborn" or (
            effective_beneficiary is not None
            and effective_beneficiary.category in {"newborn", "infant"}
        ):
            return 0.4, 15.0, "newborn/infant"

        if effective_visit_type in {"ANC", "PNC"} or (
            effective_beneficiary is not None
            and effective_beneficiary.category in {"pregnant_woman", "postnatal_mother"}
        ):
            return 25.0, 150.0, "adult maternal"

        if re.search(
            rf"{_LB}(?:newborn|navjat|shishu|baby|नवजात|शिशु){_RB}", text, re.IGNORECASE
        ):
            return 0.4, 15.0, "newborn/infant"

        return 0.4, 150.0, "human"

    def _extract_vaccinations(
        self, text: str
    ) -> tuple[list[str], list[str], dict[str, str], list[FieldClarification]]:
        completed: list[str] = []
        due: list[str] = []
        completed_sources: list[str] = []
        due_sources: list[str] = []
        clarifications: list[FieldClarification] = []

        # Split on major clause separators first
        raw_clauses = re.split(
            r"[,;.\n।]+|\b(?:but|lekin|par|magar|whereas|while)\b|(?:लेकिन|मगर|परंतु)",
            text,
            flags=re.IGNORECASE,
        )

        # Further split on "and" / "aur" / "और" ONLY when both sides carry their own status cue
        clauses: list[str] = []
        for rc in raw_clauses:
            rc = rc.strip()
            if not rc:
                continue
            conj_parts = re.split(r"\b(?:and|aur)\b|और", rc, flags=re.IGNORECASE)
            if len(conj_parts) > 1 and all(
                self._clause_has_vaccine_cue(part) for part in conj_parts
            ):
                clauses.extend(p.strip() for p in conj_parts if p.strip())
            else:
                clauses.append(rc)

        for clause in clauses:
            found_vaccines = self._find_vaccines_in_clause(clause)
            if not found_vaccines:
                continue

            cues = self._find_vaccine_cues_in_clause(clause)
            if not cues:
                # Never invent vaccination status if not stated
                for vname, _span in found_vaccines:
                    clarifications.append(
                        FieldClarification(
                            field_name="vaccinations_due",
                            reason=f"Vaccination '{vname}' was mentioned without completed or pending status.",
                            prompt_hint=f"Has {vname} already been given, or is it still pending?",
                            candidates=[f"{vname} completed", f"{vname} due"],
                        )
                    )
                continue

            for vname, (v_start, v_end) in found_vaccines:
                status = self._assign_nearest_cue(v_start, v_end, cues)
                if status == "completed":
                    if vname not in completed:
                        completed.append(vname)
                    completed_sources.append(clause)
                elif status == "due":
                    if vname not in due:
                        due.append(vname)
                    due_sources.append(clause)

        provenance: dict[str, str] = {}
        if completed_sources:
            provenance["vaccinations_completed"] = "; ".join(
                _dedupe_preserve_order(completed_sources)
            )
        if due_sources:
            provenance["vaccinations_due"] = "; ".join(_dedupe_preserve_order(due_sources))

        return completed, due, provenance, clarifications

    def _clause_has_vaccine_cue(self, clause: str) -> bool:
        return bool(self._find_vaccine_cues_in_clause(clause))

    def _find_vaccines_in_clause(self, clause: str) -> list[tuple[str, tuple[int, int]]]:
        matches: list[tuple[str, tuple[int, int]]] = []
        occupied_spans: list[tuple[int, int]] = []

        for canonical, patterns in _COMPILED_VACCINES:
            for pat in patterns:
                for m in pat.finditer(clause):
                    span = (m.start(), m.end())
                    # Skip honorific "Mr." followed by a person's name
                    if canonical == "MR" and re.match(
                        r"mr\.\s+[a-z]", clause[m.start() : m.end() + 10], re.IGNORECASE
                    ):
                        continue
                    if any(not (span[1] <= s or span[0] >= e) for s, e in occupied_spans):
                        continue
                    occupied_spans.append(span)
                    matches.append((canonical, span))
                    break
        matches.sort(key=lambda item: item[1][0])
        return matches

    def _find_vaccine_cues_in_clause(
        self, clause: str
    ) -> list[tuple[str, tuple[int, int]]]:
        cues: list[tuple[str, tuple[int, int]]] = []
        occupied: list[tuple[int, int]] = []

        # Match DUE cues first so negated completions ("not given", "nahi laga") are masked
        for pat in _VACCINE_DUE_CUES:
            for m in pat.finditer(clause):
                span = (m.start(), m.end())
                if any(not (span[1] <= s or span[0] >= e) for s, e in occupied):
                    continue
                occupied.append(span)
                cues.append(("due", span))

        for pat in _VACCINE_COMPLETED_CUES:
            for m in pat.finditer(clause):
                span = (m.start(), m.end())
                if any(not (span[1] <= s or span[0] >= e) for s, e in occupied):
                    continue
                occupied.append(span)
                cues.append(("completed", span))

        cues.sort(key=lambda item: item[1][0])
        return cues

    def _assign_nearest_cue(
        self,
        v_start: int,
        v_end: int,
        cues: list[tuple[str, tuple[int, int]]],
    ) -> str:
        # Prefer the closest cue AFTER the vaccine mention (typical EN/HI word order),
        # falling back to the closest cue BEFORE it (e.g., "pending Pentavalent").
        after = [(c_start - v_end, status) for status, (c_start, _c_end) in cues if c_start >= v_end]
        if after:
            after.sort(key=lambda item: item[0])
            return after[0][1]
        before = [(v_start - c_end, status) for status, (_c_start, c_end) in cues if c_end <= v_start]
        if before:
            before.sort(key=lambda item: item[0])
            return before[0][1]
        return cues[0][0]

    def _extract_next_visit_date(
        self,
        text: str,
        *,
        reference_date: date,
    ) -> tuple[str | None, str | None, FieldClarification | None, bool]:
        candidates = find_date_candidates(text, reference_date=reference_date)
        if not candidates:
            m_ambig = AMBIGUOUS_DATE_RE.search(text)
            if m_ambig:
                return (
                    None,
                    None,
                    FieldClarification(
                        field_name="next_visit_date",
                        reason=f"Next visit date '{m_ambig.group(0)}' is too ambiguous to convert to a calendar date.",
                        prompt_hint="Please specify an exact date or number of days for the next visit.",
                        candidates=[],
                    ),
                    False,
                )
            return None, None, None, False

        selected, inline_corr, conflicts = resolve_date_candidates(text, candidates)
        if conflicts:
            cand_strs = [c.iso_date for c in conflicts if c.iso_date]
            return (
                None,
                None,
                FieldClarification(
                    field_name="next_visit_date",
                    reason="conflict",
                    prompt_hint=(
                        f"I heard multiple dates ({' or '.join(cand_strs)}). "
                        "Which next visit date is correct?"
                    ),
                    candidates=cand_strs,
                ),
                False,
            )

        assert selected is not None
        if selected.invalid_calendar_date or selected.iso_date is None:
            return None, None, self._invalid_date_clarification(selected.source_text), inline_corr

        return selected.iso_date, selected.source_text, None, inline_corr

    def _parse_day_token(self, raw_day: str) -> int | None:
        cleaned = raw_day.strip().lower()
        m_num = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?", cleaned)
        if m_num:
            return int(m_num.group(1))
        val = _parse_int_tokens(cleaned.replace("-", " ").split())
        if val is not None and 1 <= val <= 31:
            return val
        return None

    def _parse_count_token(self, raw_count: str | None) -> int | None:
        if not raw_count:
            return None
        cleaned = raw_count.strip().lower()
        if cleaned in {"a", "an"}:
            return 1
        if cleaned.isdigit():
            return int(cleaned)
        return _parse_int_tokens(cleaned.replace("-", " ").split())

    def _invalid_date_clarification(self, raw_text: str) -> FieldClarification:
        return FieldClarification(
            field_name="next_visit_date",
            reason=f"'{raw_text}' is not a valid calendar date.",
            prompt_hint=f"The date '{raw_text}' is not valid. Please confirm the correct next visit date.",
            candidates=[],
        )

    def _derive_follow_up_actions(
        self,
        text: str,
        *,
        vaccinations_due: list[str],
        next_visit_date: str | None,
        date_source: str | None,
    ) -> list[FollowUpAction]:
        actions: list[FollowUpAction] = []

        # 1. Pending/due vaccinations
        if vaccinations_due:
            vaccines_str = ", ".join(vaccinations_due)
            actions.append(
                FollowUpAction(
                    action_type="vaccination",
                    description=f"Schedule and administer due vaccination(s): {vaccines_str}",
                    due_date=next_visit_date,
                    priority="high",
                    source_phrase=vaccines_str,
                )
            )

        # 2. IFA / calcium non-adherence
        m_ifa = _IFA_NON_ADHERENCE_RE.search(text)
        if m_ifa:
            actions.append(
                FollowUpAction(
                    action_type="ifa_adherence",
                    description="Follow up and counsel beneficiary on regular IFA/calcium adherence",
                    due_date=next_visit_date,
                    priority="high",
                    source_phrase=m_ifa.group(0).strip(),
                )
            )

        # 3. Explicit weight monitoring
        m_wm = _WEIGHT_MONITOR_RE.search(text)
        if m_wm:
            actions.append(
                FollowUpAction(
                    action_type="weight_monitoring",
                    description="Recheck and monitor beneficiary weight at follow-up",
                    due_date=next_visit_date,
                    priority="normal",
                    source_phrase=m_wm.group(0).strip(),
                )
            )

        # 4. Routine follow-up visit when explicitly requested or scheduled
        m_fv = _FOLLOWUP_VISIT_CUE_RE.search(text)
        if next_visit_date is not None or m_fv is not None:
            desc = (
                f"Conduct scheduled follow-up home visit on {next_visit_date}"
                if next_visit_date
                else "Conduct follow-up home visit"
            )
            actions.append(
                FollowUpAction(
                    action_type="routine_visit",
                    description=desc,
                    due_date=next_visit_date,
                    priority="normal",
                    source_phrase=date_source or (m_fv.group(0).strip() if m_fv else None),
                )
            )

        return actions

    def _extract_dynamic_observations(
        self,
        text: str,
        *,
        unusual_weight: tuple[float, str] | None,
        has_structured_fields: bool,
    ) -> tuple[list[DynamicObservation], list[dict[str, Any]]]:
        """Extract extensible measurements, feeding/care status, counselling & uncaptured clinical notes."""
        observations: list[DynamicObservation] = []
        numbers: list[dict[str, Any]] = []
        covered_spans: list[tuple[int, int]] = []

        if unusual_weight is not None:
            u_val, u_src = unusual_weight
            observations.append(
                DynamicObservation(
                    key="weight_kg",
                    label="Weight (Needs Confirmation)",
                    value=u_val,
                    unit="kg",
                    category="measurement",
                    status="needs_confirmation",
                    source_text=u_src,
                )
            )

        # 1. Height / length in cm
        m_len = re.search(
            rf"{_LB}(?:height|length|lambai|लंबाई|ಎತ್ತರ|ಉದ್ದ|உயரம்)\s*(?:is|hai|है|=|:|was)?\s*(?P<qty>{_QTY_PHRASE})\s*(?:cm|centimeter|centimeters|सेमी)?{_RB}",
            text,
            re.IGNORECASE,
        )
        if m_len:
            dec_val = parse_decimal_phrase(m_len.group("qty"))
            if dec_val is not None and Decimal("20") <= dec_val <= Decimal("220"):
                val_r = decimal_to_float(dec_val, places=2)
                observations.append(
                    DynamicObservation(
                        key="height_cm",
                        label="Height / Length",
                        value=val_r,
                        unit="cm",
                        category="measurement",
                        status="confirmed",
                        source_text=m_len.group(0).strip(),
                    )
                )
                numbers.append({"field": "height_cm", "value": val_r, "normalized_decimal": format_decimal_clean(dec_val), "unit": "cm", "source_text": m_len.group(0).strip(), "status": "confirmed"})
                covered_spans.append(m_len.span())

        # 2. MUAC in cm
        m_muac = re.search(
            rf"{_LB}(?:muac|mid[\s-]*upper[\s-]*arm)\s*(?:is|=|:)?\s*(?P<qty>{_QTY_PHRASE})\s*(?:cm|सेमी)?{_RB}",
            text,
            re.IGNORECASE,
        )
        if m_muac:
            dec_val = parse_decimal_phrase(m_muac.group("qty"))
            if dec_val is not None and Decimal("5") <= dec_val <= Decimal("45"):
                val_r = decimal_to_float(dec_val, places=2)
                observations.append(
                    DynamicObservation(
                        key="muac_cm",
                        label="MUAC",
                        value=val_r,
                        unit="cm",
                        category="measurement",
                        status="confirmed",
                        source_text=m_muac.group(0).strip(),
                    )
                )
                numbers.append({"field": "muac_cm", "value": val_r, "normalized_decimal": format_decimal_clean(dec_val), "unit": "cm", "source_text": m_muac.group(0).strip(), "status": "confirmed"})
                covered_spans.append(m_muac.span())

        # 3. Temperature (supports digits and spoken decimal phrases like "99 point 8")
        m_temp = re.search(
            rf"{_LB}(?:temp|temperature|tapman|तापमान|ಜ್ವರ|ತಾಪಮಾನ|வெப்பநிலை)\s*(?:is|hai|है|=|:)?\s*(?P<qty>{_QTY_PHRASE})\s*(?P<unit>°?\s*[cf]|celsius|fahrenheit|degree|degrees)?{_RB}",
            text,
            re.IGNORECASE,
        )
        if m_temp:
            dec_t = parse_decimal_phrase(m_temp.group("qty"))
            if dec_t is not None and Decimal("30") <= dec_t <= Decimal("110"):
                tval = decimal_to_float(dec_t, places=1)
                raw_u = (m_temp.group("unit") or "").strip().lower()
                unit = "°C" if ("c" in raw_u or tval < 45) else "°F"
                observations.append(
                    DynamicObservation(
                        key="temperature",
                        label="Temperature",
                        value=tval,
                        unit=unit,
                        category="measurement",
                        status="confirmed",
                        source_text=m_temp.group(0).strip(),
                    )
                )
                numbers.append({"field": "temperature", "value": tval, "normalized_decimal": format_decimal_clean(dec_t), "unit": unit, "source_text": m_temp.group(0).strip(), "status": "confirmed"})
                covered_spans.append(m_temp.span())

        # 4. Blood pressure (e.g. "BP 110/70", "BP is 120 by 80")
        m_bp = re.search(
            rf"{_LB}(?:bp|b\.p\.|blood\s+pressure|रक्तचाप)\s*(?:is|hai|है|=|:)?\s*(?P<sys>\d{{2,3}})\s*(?:/|by|over)\s*(?P<dia>\d{{2,3}}){_RB}",
            text,
            re.IGNORECASE,
        )
        if m_bp:
            bp_str = f"{m_bp.group('sys')}/{m_bp.group('dia')}"
            observations.append(
                DynamicObservation(
                    key="blood_pressure",
                    label="Blood Pressure",
                    value=bp_str,
                    unit="mmHg",
                    category="measurement",
                    status="confirmed",
                    source_text=m_bp.group(0).strip(),
                )
            )
            numbers.append({"field": "blood_pressure", "value": bp_str, "unit": "mmHg", "source_text": m_bp.group(0).strip(), "status": "confirmed"})
            covered_spans.append(m_bp.span())

        # 5. Hemoglobin (Hb)
        m_hb = re.search(
            rf"{_LB}(?:hb|h\.b\.|hemoglobin|haemoglobin|हीमोग्लोबिन)\s*(?:is|hai|है|=|:)?\s*(?P<qty>{_QTY_PHRASE})\s*(?:g/dl|gm%|grams?)?{_RB}",
            text,
            re.IGNORECASE,
        )
        if m_hb:
            dec_hb = parse_decimal_phrase(m_hb.group("qty"))
            if dec_hb is not None and Decimal("2.0") <= dec_hb <= Decimal("22.0"):
                hb_r = decimal_to_float(dec_hb, places=1)
                observations.append(
                    DynamicObservation(
                        key="hemoglobin_g_dl",
                        label="Hemoglobin (Hb)",
                        value=hb_r,
                        unit="g/dL",
                        category="measurement",
                        status="confirmed",
                        source_text=m_hb.group(0).strip(),
                    )
                )
                numbers.append({"field": "hemoglobin_g_dl", "value": hb_r, "normalized_decimal": format_decimal_clean(dec_hb), "unit": "g/dL", "source_text": m_hb.group(0).strip(), "status": "confirmed"})
                covered_spans.append(m_hb.span())

        # 6. Feeding / breastfeeding status
        m_feed = re.search(
            r"(?:exclusive(?:ly)?\s+breastfeeding|breastfeeding\s+(?:well|poorly|not\s+well|started|regularly|ok|good|fine)|not\s+(?:feeding|breastfeeding)(?:\s+well)?|poor\s+feeding|feeding\s+(?:well|poorly|fine|ok|normal)|स्तनपान\s+(?:ठीक|अच्छा|नहीं)|दूध\s+(?:ठीक\s+से\s+)?पी\s+रहा)",
            text,
            re.IGNORECASE,
        )
        if m_feed:
            observations.append(
                DynamicObservation(
                    key="feeding_status",
                    label="Feeding / Breastfeeding",
                    value=m_feed.group(0).strip(),
                    category="feeding",
                    status="confirmed",
                    source_text=m_feed.group(0).strip(),
                )
            )
            covered_spans.append(m_feed.span())

        # 7. IFA / Calcium supplement adherence
        m_supp = re.search(
            r"(?:taking\s+(?:ifa|iron|calcium)(?:\s+tablets?)?(?:\s+regularly)?|not\s+taking\s+(?:ifa|iron|calcium)(?:\s+tablets?)?|ifa\s+(?:completed|started|skipped|missed|adherence)|calcium\s+(?:started|taken|regular)|आयरन\s+की\s+गोली\s+(?:ले\s+रही|नहीं\s+ले\s+रही))",
            text,
            re.IGNORECASE,
        )
        if m_supp:
            observations.append(
                DynamicObservation(
                    key="supplement_adherence",
                    label="IFA / Calcium Supplements",
                    value=m_supp.group(0).strip(),
                    category="supplements",
                    status="confirmed",
                    source_text=m_supp.group(0).strip(),
                )
            )
            covered_spans.append(m_supp.span())

        # 8. Umbilical cord / hygiene / skin-to-skin care
        m_care = re.search(
            r"(?:umbilical\s+cord\s+[^,.]+|cord\s+(?:is\s+)?(?:clean|dry|healthy)|skin[\s-]+to[\s-]+skin\s+care[^,.]*|kangaroo\s+mother\s+care[^,.]*)",
            text,
            re.IGNORECASE,
        )
        if m_care:
            observations.append(
                DynamicObservation(
                    key="newborn_care_note",
                    label="Newborn Care",
                    value=m_care.group(0).strip(),
                    category="newborn_care",
                    status="confirmed",
                    source_text=m_care.group(0).strip(),
                )
            )
            covered_spans.append(m_care.span())

        # 9. Counselling given
        m_coun = re.search(
            r"(?:counsel+ed\s+(?:on|about)\s+[^,.]+|advised\s+(?:on|for|about)\s+[^,.]+|परिवार\s+को\s+[^।,.]+\s+सलाह\s+दी)",
            text,
            re.IGNORECASE,
        )
        if m_coun:
            observations.append(
                DynamicObservation(
                    key="counselling_topic",
                    label="Counselling Given",
                    value=m_coun.group(0).strip(),
                    category="counselling",
                    status="confirmed",
                    source_text=m_coun.group(0).strip(),
                )
            )
            covered_spans.append(m_coun.span())

        # 10. Arbitrary spoken detail catch-all: if worker spoke a rich clinical sentence without
        # triggering only conversational acks ("yes", "no", "ok", "confirm") and no dynamic obs matched,
        # keep the detail preserved as a clinical_note so spoken info is never silently dropped.
        stripped = text.strip()
        words = stripped.split()
        is_ack_or_removal = bool(
            re.fullmatch(
                r"(?:yes|yeah|yep|no|nope|ok|okay|done|confirm|save|submit|cancel|read back|skip|hello|hi|haan|जी|हाँ|नहीं)\W*",
                stripped,
                re.IGNORECASE,
            )
            or re.search(r"\b(?:remove|delete|clear|drop|हटा|मिटा)\b", stripped, re.IGNORECASE)
        )
        if (
            not observations
            and not has_structured_fields
            and not is_ack_or_removal
            and len(words) >= 4
        ):
            observations.append(
                DynamicObservation(
                    key="clinical_note",
                    label="Additional Clinical Note",
                    value=stripped,
                    category="clinical_note",
                    status="confirmed",
                    source_text=stripped,
                )
            )

        return observations, numbers

    def _build_dynamic_events(
        self,
        *,
        v_completed: list[str],
        v_due: list[str],
        v_prov: dict[str, str],
        next_date: str | None,
    ) -> list[DynamicEvent]:
        """Build repeatable per-item immunisation events cleanly."""
        events: list[DynamicEvent] = []
        for vac in v_completed:
            events.append(
                DynamicEvent(
                    event_type="immunisation",
                    name=vac,
                    status="completed",
                    date=None,
                    source_text=v_prov.get("vaccinations_completed"),
                )
            )
        completed_lower = {v.lower() for v in v_completed}
        for vac in v_due:
            if vac.lower() in completed_lower:
                continue
            events.append(
                DynamicEvent(
                    event_type="immunisation",
                    name=vac,
                    status="due",
                    date=next_date,
                    source_text=v_prov.get("vaccinations_due"),
                )
            )
        return events

    def _extract_removals(
        self,
        text: str,
        *,
        existing_draft: VisitDraft | None,
    ) -> tuple[list[str], list[str]]:
        """Detect explicit spoken removal/deletion requests for dynamic observations or events."""
        m_rm = re.search(
            r"\b(?:remove|delete|clear|drop)\s+(?:that\s+|the\s+)?(?P<target>[a-z0-9\s\-_/]{2,40})",
            text,
            re.IGNORECASE,
        )
        if not m_rm:
            return [], []
        target = m_rm.group("target").strip().lower()
        obs_keys: list[str] = []
        event_names: list[str] = []

        # Map common spoken labels to dynamic observation keys
        obs_aliases = {
            "feeding": "feeding_status",
            "breastfeeding": "feeding_status",
            "height": "height_cm",
            "length": "height_cm",
            "muac": "muac_cm",
            "temp": "temperature",
            "temperature": "temperature",
            "bp": "blood_pressure",
            "blood pressure": "blood_pressure",
            "hb": "hemoglobin_g_dl",
            "hemoglobin": "hemoglobin_g_dl",
            "supplement": "supplement_adherence",
            "ifa": "supplement_adherence",
            "calcium": "supplement_adherence",
            "cord": "newborn_care_note",
            "counselling": "counselling_topic",
            "counseling": "counselling_topic",
            "note": "clinical_note",
            "clinical note": "clinical_note",
        }
        for alias, key in obs_aliases.items():
            if alias in target:
                obs_keys.append(key)

        if existing_draft is not None:
            for obs in existing_draft.observations:
                if obs.key.lower() in target or obs.label.lower() in target:
                    if obs.key not in obs_keys:
                        obs_keys.append(obs.key)
            for ev in existing_draft.events:
                if ev.name.lower() in target:
                    if ev.name not in event_names:
                        event_names.append(ev.name)
            for vac in list(existing_draft.vaccinations_due) + list(existing_draft.vaccinations_completed):
                if vac.lower() in target and vac not in event_names:
                    event_names.append(vac)

        # Also check canonical vaccine mentions directly
        for canon in ("BCG", "OPV", "Hepatitis B", "Pentavalent", "Rota", "PCV", "IPV", "MR", "DPT", "TT", "Td"):
            if re.search(rf"\b{re.escape(canon.lower())}\b", target):
                if canon not in event_names:
                    event_names.append(canon)

        return obs_keys, event_names


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
