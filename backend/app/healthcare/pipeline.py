"""Central Phase 2 Healthcare Integration Pipeline (1A + 1B + 1C -> v1 Contracts).

Wires:
- Layer 1 Deterministic Danger-Sign Engine (1A) on EVERY partial & final transcript
- Healthcare Visit Field Extractor & Validator (1C) on final transcripts
- Conversation State Machine, Read-Back, Correction & Confirmation Gate (1B)
- Contract-validated `v1` JSON serialization for `visit.schema.json`,
  `danger-alert.schema.json`, and `voice-events.schema.json`
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime, timezone, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from decimal import Decimal

from app.conversation.models import (
    ActionType,
    ClarificationRequest,
    ConversationState,
    DangerAlertInput,
    DangerAlertRecord,
    ExtractionUpdate,
    TransitionResult,
    VisitRecordState,
    VisitStatus,
    detect_language_from_text,
    normalize_language,
)
from app.conversation.state_machine import (
    ConversationStateMachine,
    InvalidTransitionError,
    classify_confirmation_intent,
    format_unambiguous_spoken_date,
    is_completion_intent,
)
from app.core.config import build_contextual_stt_options, get_settings
from app.core.logging import log_event
from app.danger_signs.detector import detect_danger_signs, get_referral_message
from app.danger_signs.models import DangerMatch, DetectionResult
from app.extraction.extractor import VisitFieldExtractor
from app.extraction.models import DynamicObservation, FieldClarification, FollowUpAction, VisitDraft
from app.extraction.numbers import format_decimal_clean
from app.extraction.secondary_recognition import (
    IMPORTANT_CONFIRMABLE_FIELDS,
    NUMERIC_OBSERVATION_KEYS,
    SecondarySpeechRecognizer,
    assess_numeric_uncertainty,
    compare_numeric_interpretations,
)
from app.services.beneficiaries import SyntheticBeneficiaryDirectory
from app.voice.interfaces import TranscriptEvent
from app.voice.orchestration.session import VoiceSessionOrchestrator

logger = logging.getLogger(__name__)
try:
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30))

_MATCH_TYPE_TO_CONTRACT: dict[str, str] = {
    "exact": "exact_phrase",
    "alias": "code_mixed_pattern",
    "normalized": "normalized_variant",
    "threshold": "numeric_threshold",
    "fuzzy": "fuzzy_assisted",
}

_STATE_TO_WS_SESSION_STATE: dict[ConversationState, str] = {
    ConversationState.IDLE: "idle",
    ConversationState.SESSION_START: "idle",
    ConversationState.BENEFICIARY_GREETING: "speaking",
    ConversationState.IDENTITY_CONFIRMATION: "listening",
    ConversationState.IDENTITY_CORRECTION: "listening",
    ConversationState.BENEFICIARY_LOOKUP: "processing",
    ConversationState.CANDIDATE_CONFIRMATION: "listening",
    ConversationState.GATHERING_NOTES: "listening",
    ConversationState.STREAMING_TRANSCRIPTION: "listening",
    ConversationState.CONTINUE_CONVERSATION: "listening",
    ConversationState.EXTRACTING_FIELDS: "processing",
    ConversationState.CLARIFICATION_REQUIRED: "speaking",
    ConversationState.FINAL_REVIEW_READY: "awaiting_confirmation",
    ConversationState.ASK_READBACK_PREFERENCE: "awaiting_confirmation",
    ConversationState.READ_COMPLETE_SUMMARY: "read_back",
    ConversationState.ASK_SUBMISSION_CONFIRMATION: "awaiting_confirmation",
    ConversationState.READ_BACK_CONFIRMATION: "speaking",
    ConversationState.CORRECTION_PATCH: "processing",
    ConversationState.READY_TO_CONFIRM: "listening",
    ConversationState.COMMITTED: "committed",
    ConversationState.DANGER_ESCALATION: "danger_escalation",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _map_follow_up_action_type(action_type: str, visit_type: str | None) -> str:
    if action_type == "vaccination":
        return "vaccination_followup"
    if action_type == "ifa_adherence":
        return "nutrition_counsel"
    if action_type == "danger_referral":
        return "phc_referral"
    if action_type == "weight_monitoring":
        return "hbnc_visit" if visit_type == "Newborn" else "home_visit"
    if action_type == "routine_visit":
        if visit_type == "ANC":
            return "anc_checkup"
        if visit_type == "PNC":
            return "pnc_checkup"
        if visit_type == "Newborn":
            return "hbnc_visit"
        return "home_visit"
    return "other"


def format_danger_alert_contract(
    *,
    alert_id: str,
    session_id: str,
    visit_id: str,
    beneficiary_id: str | None,
    match: DangerMatch,
    language: str,
    referral_message: str,
    detected_at: str | None = None,
    status: str = "active",
    acknowledged_by: str | None = None,
    acknowledged_at: str | None = None,
) -> dict[str, Any]:
    """Serialize a 1A DangerMatch into a strict `danger-alert.schema.json` v1 dict."""
    evidence = (match.evidence_text or match.matched_phrase or match.canonical_name).strip()[:200]
    return {
        "schema_version": "v1",
        "alert_id": alert_id,
        "session_id": session_id,
        "visit_id": visit_id,
        "beneficiary_id": beneficiary_id,
        "canonical_danger_sign_id": match.canonical_id,
        "canonical_name": match.canonical_name,
        "subject": match.subject,
        "category": match.category,
        "supporting_evidence": evidence,
        "match_type": _MATCH_TYPE_TO_CONTRACT.get(match.match_type, "code_mixed_pattern"),
        "source_guideline_ref": f"{match.source_doc} ({match.source_section})",
        "detected_at": detected_at or utc_now_iso(),
        "status": status,
        "acknowledged_by": acknowledged_by,
        "acknowledged_at": acknowledged_at,
        "escalation_language": normalize_language(language),
        "referral_message": referral_message,
        "danger_sign_flagged": True,
        "priority": "urgent",
    }


def format_visit_contract(
    *,
    visit_state: VisitRecordState,
    session_id: str,
    worker_id: str,
    language: str,
    weight_source_text: str | None = None,
    next_visit_date_source_text: str | None = None,
    structured_follow_ups: list[dict[str, Any]] | None = None,
    confirmed_at: str | None = None,
    committed_at: str | None = None,
) -> dict[str, Any]:
    """Serialize VisitRecordState into a strict `visit.schema.json` v1 dict."""
    vtype_str = visit_state.visit_type.value if visit_state.visit_type else None
    follow_ups = list(structured_follow_ups or [])
    if not follow_ups and visit_state.follow_up_actions:
        follow_ups = [
            {
                "action_type": "other",
                "description": desc,
                "due_date": visit_state.next_visit_date,
                "priority": "normal",
                "source_phrase": None,
            }
            for desc in visit_state.follow_up_actions
        ]

    # Ensure urgent PHC referral follow-up exists if danger_sign_flagged is True
    if visit_state.danger_sign_flagged and not any(
        f.get("action_type") == "phc_referral" for f in follow_ups
    ):
        today_ist = datetime.now(IST).date().isoformat()
        follow_ups.insert(
            0,
            {
                "action_type": "phc_referral",
                "description": "Immediate referral to nearest PHC for detected danger sign",
                "due_date": today_ist,
                "priority": "urgent",
                "source_phrase": (visit_state.danger_signs[0] if visit_state.danger_signs else None),
            },
        )

    payload: dict[str, Any] = {
        "schema_version": "v1",
        "visit_id": visit_state.visit_draft_id,
        "session_id": session_id,
        "worker_id": worker_id,
        "beneficiary_id": visit_state.beneficiary_id,
        "beneficiary_name": visit_state.beneficiary_name,
        "visit_type": vtype_str,
        "weight_kg": visit_state.weight_kg,
        "weight_source_text": weight_source_text,
        "vaccinations_completed": list(visit_state.vaccinations_completed),
        "vaccinations_due": list(visit_state.vaccinations_due),
        "next_visit_date": visit_state.next_visit_date,
        "next_visit_date_source_text": next_visit_date_source_text,
        "danger_signs": list(visit_state.danger_signs),
        "danger_sign_flagged": bool(visit_state.danger_sign_flagged),
        "follow_up_actions": follow_ups,
        "status": visit_state.status.value,
        "confirmed_at": confirmed_at,
        "committed_at": committed_at,
        "persistence_record_id": visit_state.record_id,
        "language": normalize_language(language),
        "timezone": "Asia/Kolkata",
        "synthetic": True,
    }
    if visit_state.observations:
        serialized_obs = []
        for idx, o in enumerate(visit_state.observations):
            if o.get("key") is None:
                continue
            val = o.get("value")
            if isinstance(val, bool):
                vtype = "boolean"
            elif isinstance(val, (int, float)):
                vtype = "number"
            else:
                vtype = "text"
            obs_status = str(o.get("status", "confirmed"))
            if obs_status not in {"needs_confirmation", "confirmed", "corrected", "uncertain", "removed"}:
                obs_status = "confirmed"
            serialized_obs.append(
                {
                    "id": str(o.get("id") or f"obs_{o.get('key')}_{idx}"),
                    "key": str(o.get("key", "")),
                    "label": str(o.get("label", o.get("key", ""))),
                    "value": val,
                    "value_type": vtype,
                    "unit": o.get("unit"),
                    "source_text": o.get("source_text"),
                    "turn_id": o.get("turn_id"),
                    "confidence": o.get("confidence"),
                    "extraction_stage": "uncertain" if obs_status in {"needs_confirmation", "uncertain"} else "normalized",
                    "status": obs_status,
                }
            )
        if serialized_obs:
            payload["observations"] = serialized_obs
    if visit_state.events:
        serialized_events = []
        for idx, e in enumerate(visit_state.events):
            if not e.get("name"):
                continue
            ev_obj: dict[str, Any] = {
                "id": str(e.get("id") or f"evt_{str(e.get('event_type', 'immunisation')).lower()}_{str(e.get('name', '')).lower().replace(' ', '_')}_{idx}"),
                "event_type": str(e.get("event_type", "immunisation")),
                "name": str(e.get("name", "")),
                "status": str(e.get("status", "due")),
                "date": e.get("date"),
                "source_text": e.get("source_text"),
                "turn_id": e.get("turn_id"),
                "confirmation_status": "confirmed",
            }
            if e.get("notes"):
                ev_obj["attributes"] = {"notes": str(e["notes"])}
            serialized_events.append(ev_obj)
        if serialized_events:
            payload["events"] = serialized_events
    return payload


class HealthcareSessionPipeline:
    """Per-session coordinator integrating 1A (Danger Signs), 1B (State Machine), and 1C (Extraction)."""

    def __init__(
        self,
        *,
        session_id: str,
        worker_id: str = "ASHA-DEMO-01",
        language: str = "hi-IN",
        beneficiary_id: str | None = None,
        directory: SyntheticBeneficiaryDirectory | None = None,
        reference_date: date | None = None,
        continuous_editing: bool = False,
        review_silence_timeout_s: float = 12.0,
        secondary_recognizer: SecondarySpeechRecognizer | None = None,
        confirm_important_numbers: bool = False,
    ) -> None:
        self.session_id = session_id
        self.worker_id = worker_id
        self.language = normalize_language(language)
        self._directory = directory or SyntheticBeneficiaryDirectory()
        self._extractor = VisitFieldExtractor(beneficiary_directory=self._directory)
        self._reference_date = reference_date
        self.continuous_editing = continuous_editing
        self.review_silence_timeout_s = review_silence_timeout_s
        self._secondary_recognizer = secondary_recognizer
        self.confirm_important_numbers = confirm_important_numbers

        ben_name: str | None = None
        if beneficiary_id:
            ben = self._directory.get_by_id(beneficiary_id)
            if ben is not None:
                beneficiary_id = ben.beneficiary_id
                ben_name = ben.full_name

        self.sm = ConversationStateMachine(
            session_id=session_id,
            language=self.language,
            beneficiary_id=beneficiary_id,
            beneficiary_name=ben_name,
        )
        self.sm.start_gathering()

        self._weight_source_text: str | None = None
        self._next_visit_date_source_text: str | None = None
        self._structured_follow_ups: list[dict[str, Any]] = []
        self._confirmed_at: str | None = None
        self._committed_at: str | None = None
        self._contract_alerts: dict[str, dict[str, Any]] = {}
        self._orchestrator: VoiceSessionOrchestrator | None = None
        self._last_stt_beneficiary_id: str | None = beneficiary_id
        self._stt_reconnect_task: asyncio.Task[None] | None = None
        # Typed pending confirmation queue keyed by field name (weight_kg, next_visit_date,
        # beneficiary_id, temperature, blood_pressure, hemoglobin_g_dl)
        self._pending_numeric_confirmations: dict[str, dict[str, Any]] = {}
        self._pending_source_texts: dict[str, str | None] = {}
        self._pending_obs_candidates: dict[str, dict[str, Any]] = {}
        self._pending_beneficiary_names: dict[str, str] = {}
        self._pending_follow_up_actions: dict[str, list[FollowUpAction]] = {}
        self._awaiting_numeric_repeat_field: str | None = None
        self._silence_task: asyncio.Task[None] | None = None

    def set_secondary_recognizer(self, recognizer: SecondarySpeechRecognizer | None) -> None:
        self._secondary_recognizer = recognizer

    async def _reconnect_stt_safely(self, stt: Any) -> None:
        try:
            await stt.reconnect_with_context()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log_event(
                logger,
                "stt_context_reconnect_failed",
                session=self.session_id,
                reason=str(exc)[:120],
            )

    def _sync_stt_context_from_visit(self, orchestrator: VoiceSessionOrchestrator) -> None:
        """Keep STT speaker_names & keywords synced to the active beneficiary without overloading."""
        stt = getattr(orchestrator, "_stt", None)
        update_ctx = getattr(stt, "update_context", None)
        if not callable(update_ctx):
            return
        ctx = build_contextual_stt_options(
            beneficiary_name=self.sm.visit.beneficiary_name,
            beneficiary_id=self.sm.visit.beneficiary_id,
        )
        update_ctx(
            speaker_names=ctx["speaker_names"],
            keywords=ctx["keywords"],
        )
        # Reopen live Prisma WS on beneficiary change so handshake headers
        # (`x-speaker-names`, `x-keywords`, `x-previous-text`) actually refresh.
        new_bid = self.sm.visit.beneficiary_id
        if new_bid and new_bid != self._last_stt_beneficiary_id:
            self._last_stt_beneficiary_id = new_bid
            reconnect_fn = getattr(stt, "reconnect_with_context", None)
            if callable(reconnect_fn) and getattr(stt, "is_connected", False):
                if self._stt_reconnect_task is not None and not self._stt_reconnect_task.done():
                    self._stt_reconnect_task.cancel()
                self._stt_reconnect_task = asyncio.create_task(
                    self._reconnect_stt_safely(stt),
                    name=f"stt-ctx-reconnect-{self.session_id}",
                )

    def _is_baby_context(self) -> bool:
        vtype = self.sm.visit.visit_type.value if self.sm.visit.visit_type else None
        if vtype == "Newborn":
            return True
        if self.sm.visit.beneficiary_id:
            ben = self._directory.get_by_id(self.sm.visit.beneficiary_id)
            if ben and ben.category in {"newborn", "infant"}:
                return True
        return False

    def _format_numeric_confirmation_prompt(
        self,
        field_name: str,
        value: Any,
        *,
        language: str,
        unit: str | None = None,
    ) -> str:
        lang = normalize_language(language)
        if field_name == "weight_kg":
            val_s = format_decimal_clean(Decimal(str(value)))
            is_baby = self._is_baby_context()
            if lang == "hi-IN":
                subject = "बच्चे का वज़न" if is_baby else "वज़न"
                return f"मैंने {subject} {val_s} किलोग्राम सुना है। क्या यह सही है?"
            if lang == "kn-IN":
                subject = "ಮಗುವಿನ ತೂಕ" if is_baby else "ತೂಕ"
                return f"{subject} {val_s} ಕಿಲೋಗ್ರಾಂ ಎಂದು ಕೇಳಿಸಿದೆ. ಇದು ಸರಿಯೇ?"
            if lang == "ta-IN":
                subject = "குழந்தையின் எடை" if is_baby else "எடை"
                return f"{subject} {val_s} கிலோகிராம் என்று கேட்டது. இது சரியா?"
            subject = "the baby's weight" if is_baby else "the weight"
            return f"I heard {subject} as {val_s} kilograms. Is that correct?"
        if field_name == "next_visit_date":
            spoken_date = format_unambiguous_spoken_date(str(value)) or str(value)
            if lang == "hi-IN":
                return f"मैंने अगली विज़िट की तारीख {spoken_date} सुनी है। क्या यह सही है?"
            if lang == "kn-IN":
                return f"ಮುಂದಿನ ಭೇಟಿಯ ದಿನಾಂಕ {spoken_date} ಎಂದು ಕೇಳಿಸಿದೆ. ಇದು ಸರಿಯೇ?"
            if lang == "ta-IN":
                return f"அடுத்த வருகை தேதி {spoken_date} என்று கேட்டது. இது சரியா?"
            return f"I heard the next visit date as {spoken_date}. Is that correct?"
        if field_name == "beneficiary_id":
            bid = str(value).strip().upper()
            if lang == "hi-IN":
                return f"मैंने लाभार्थी आईडी {bid} सुनी है। क्या यह सही है?"
            if lang == "kn-IN":
                return f"ಫಲಾನುಭವಿ ಐಡಿ {bid} ಎಂದು ಕೇಳಿಸಿದೆ. ಇದು ಸರಿಯೇ?"
            if lang == "ta-IN":
                return f"பயனாளி ஐடி {bid} என்று கேட்டது. இது சரியா?"
            return f"I heard the beneficiary ID as {bid}. Is that correct?"
        if field_name == "temperature":
            u = unit or "°F"
            val_s = format_decimal_clean(Decimal(str(value)))
            if lang == "hi-IN":
                return f"मैंने तापमान {val_s} {u} सुना है। क्या यह सही है?"
            if lang == "kn-IN":
                return f"ತಾಪಮಾನ {val_s} {u} ಎಂದು ಕೇಳಿಸಿದೆ. ಇದು ಸರಿಯೇ?"
            if lang == "ta-IN":
                return f"வெப்பநிலை {val_s} {u} என்று கேட்டது. இது சரியா?"
            return f"I heard the temperature as {val_s} {u}. Is that correct?"
        if field_name == "blood_pressure":
            u = unit or "mmHg"
            if lang == "hi-IN":
                return f"मैंने ब्लड प्रेशर {value} {u} सुना है। क्या यह सही है?"
            if lang == "kn-IN":
                return f"ರಕ್ತದೊತ್ತಡ {value} {u} ಎಂದು ಕೇಳಿಸಿದೆ. ಇದು ಸರಿಯೇ?"
            if lang == "ta-IN":
                return f"ரத்த அழுத்தம் {value} {u} என்று கேட்டது. இது சரியா?"
            return f"I heard the blood pressure as {value} {u}. Is that correct?"
        if field_name == "hemoglobin_g_dl":
            u = unit or "g/dL"
            val_s = format_decimal_clean(Decimal(str(value)))
            if lang == "hi-IN":
                return f"मैंने हीमोग्लोबिन {val_s} {u} सुना है। क्या यह सही है?"
            if lang == "kn-IN":
                return f"ಹಿಮೋಗ್ಲೋಬಿನ್ {val_s} {u} ಎಂದು ಕೇಳಿಸಿದೆ. ಇದು ಸರಿಯೇ?"
            if lang == "ta-IN":
                return f"ஹீமோகுளோபின் {val_s} {u} என்று கேட்டது. இது சரியா?"
            return f"I heard the hemoglobin as {val_s} {u}. Is that correct?"
        return f"I heard {field_name} as {value}. Is that correct?"

    def _format_repeat_numeric_prompt(self, field_name: str, *, language: str) -> str:
        lang = normalize_language(language)
        if field_name == "weight_kg":
            if lang == "hi-IN":
                return "ठीक है, कृपया सही वज़न दोबारा बोलें।"
            if lang == "kn-IN":
                return "ಸರಿ, ದಯವಿಟ್ಟು ಸರಿಯಾದ ತೂಕವನ್ನು ಮತ್ತೆ ಹೇಳಿ."
            if lang == "ta-IN":
                return "சரி, தயவுசெய்து சரியான எடையை மீண்டும் சொல்லுங்கள்."
            return "Okay, please repeat the weight."
        if field_name == "next_visit_date":
            if lang == "hi-IN":
                return "ठीक है, कृपया अगली विज़िट की सही तारीख दोबारा बोलें।"
            if lang == "kn-IN":
                return "ಸರಿ, ದಯವಿಟ್ಟು ಮುಂದಿನ ಭೇಟಿಯ ಸರಿಯಾದ ದಿನಾಂಕವನ್ನು ಮತ್ತೆ ಹೇಳಿ."
            if lang == "ta-IN":
                return "சரி, தயவுசெய்து அடுத்த வருகையின் சரியான தேதியை மீண்டும் சொல்லுங்கள்."
            return "Okay, please repeat the next visit date."
        if field_name == "beneficiary_id":
            if lang == "hi-IN":
                return "ठीक है, कृपया सही लाभार्थी आईडी दोबारा बोलें।"
            if lang == "kn-IN":
                return "ಸರಿ, ದಯವಿಟ್ಟು ಸರಿಯಾದ ಫಲಾನುಭವಿ ಐಡಿಯನ್ನು ಮತ್ತೆ ಹೇಳಿ."
            if lang == "ta-IN":
                return "சரி, தயவுசெய்து சரியான பயனாளி ஐடியை மீண்டும் சொல்லுங்கள்."
            return "Okay, please repeat the beneficiary ID."
        if field_name == "temperature":
            if lang == "hi-IN":
                return "ठीक है, कृपया सही तापमान दोबारा बोलें।"
            if lang == "kn-IN":
                return "ಸರಿ, ದಯವಿಟ್ಟು ಸರಿಯಾದ ತಾಪಮಾನವನ್ನು ಮತ್ತೆ ಹೇಳಿ."
            if lang == "ta-IN":
                return "சரி, தயவுசெய்து சரியான வெப்பநிலையை மீண்டும் சொல்லுங்கள்."
            return "Okay, please repeat the temperature."
        if field_name == "blood_pressure":
            if lang == "hi-IN":
                return "ठीक है, कृपया सही ब्लड प्रेशर दोबारा बोलें।"
            if lang == "kn-IN":
                return "ಸರಿ, ದಯವಿಟ್ಟು ಸರಿಯಾದ ರಕ್ತದೊತ್ತಡವನ್ನು ಮತ್ತೆ ಹೇಳಿ."
            if lang == "ta-IN":
                return "சரி, தயவுசெய்து சரியான ரத்த அழுத்தத்தை மீண்டும் சொல்லுங்கள்."
            return "Okay, please repeat the blood pressure."
        if field_name == "hemoglobin_g_dl":
            if lang == "hi-IN":
                return "ठीक है, कृपया सही हीमोग्लोबिन मान दोबारा बोलें।"
            if lang == "kn-IN":
                return "ಸರಿ, ದಯವಿಟ್ಟು ಸರಿಯಾದ ಹಿಮೋಗ್ಲೋಬಿನ್ ಮೌಲ್ಯವನ್ನು ಮತ್ತೆ ಹೇಳಿ."
            if lang == "ta-IN":
                return "சரி, தயவுசெய்து சரியான ஹீமோகுளோபின் அளவை மீண்டும் சொல்லுங்கள்."
            return "Okay, please repeat the hemoglobin value."
        if lang == "hi-IN":
            return "ठीक है, कृपया सही मान दोबारा बोलें।"
        return f"Okay, please repeat the {field_name}."

    def attach_orchestrator(self, orchestrator: VoiceSessionOrchestrator) -> None:
        self._orchestrator = orchestrator

    def _cancel_silence_timer(self) -> None:
        if self._silence_task is not None and not self._silence_task.done():
            self._silence_task.cancel()
        self._silence_task = None

    def _schedule_silence_timer_if_needed(self, orchestrator: VoiceSessionOrchestrator) -> None:
        self._cancel_silence_timer()
        if self.review_silence_timeout_s <= 0:
            return
        if self.sm.state not in (
            ConversationState.ASK_READBACK_PREFERENCE,
            ConversationState.ASK_SUBMISSION_CONFIRMATION,
        ):
            return

        async def _timer() -> None:
            try:
                await asyncio.sleep(self.review_silence_timeout_s)
                if self.sm.state in (
                    ConversationState.ASK_READBACK_PREFERENCE,
                    ConversationState.ASK_SUBMISSION_CONFIRMATION,
                ):
                    await self.handle_silence_timeout(orchestrator)
            except asyncio.CancelledError:
                return

        self._silence_task = asyncio.create_task(
            _timer(), name=f"review-silence-{self.session_id}"
        )

    async def start_session_greeting(self, orchestrator: VoiceSessionOrchestrator) -> None:
        """Initiate Section 1 personalized spoken greeting and enter voice identity verification."""
        self.continuous_editing = True
        transition = self.sm.start_beneficiary_greeting(language=self.language)
        orchestrator.telemetry.steps.session_started = True
        orchestrator.telemetry.steps.beneficiary_identified = bool(self.sm.visit.beneficiary_id)
        orchestrator.telemetry.steps.identity_voice_confirmed = False
        await self._dispatch_transition(transition, orchestrator, is_greeting=True)

    def current_visit_contract(self) -> dict[str, Any]:
        return format_visit_contract(
            visit_state=self.sm.visit,
            session_id=self.session_id,
            worker_id=self.worker_id,
            language=self.sm.active_language,
            weight_source_text=self._weight_source_text,
            next_visit_date_source_text=self._next_visit_date_source_text,
            structured_follow_ups=self._structured_follow_ups,
            confirmed_at=self._confirmed_at,
            committed_at=self._committed_at,
        )

    def current_alerts_contract(self) -> list[dict[str, Any]]:
        # Keep beneficiary_id synced on alerts if resolved later in the visit
        ben_id = self.sm.visit.beneficiary_id
        out: list[dict[str, Any]] = []
        for alert in self._contract_alerts.values():
            if ben_id and alert["beneficiary_id"] is None:
                alert["beneficiary_id"] = ben_id
            out.append(dict(alert))
        return out

    def _build_draft_snapshot_for_extractor(self) -> VisitDraft:
        v = self.sm.visit
        return VisitDraft(
            visit_id=v.visit_draft_id,
            beneficiary_id=v.beneficiary_id,
            beneficiary_name=v.beneficiary_name,
            visit_type=v.visit_type.value if v.visit_type else None,
            weight_kg=v.weight_kg,
            weight_source_text=self._weight_source_text,
            vaccinations_completed=list(v.vaccinations_completed),
            vaccinations_due=list(v.vaccinations_due),
            next_visit_date=v.next_visit_date,
            next_visit_date_source_text=self._next_visit_date_source_text,
            danger_signs=list(v.danger_signs),
            danger_sign_flagged=v.danger_sign_flagged,
            status=v.status.value,
            confirmed_fields=sorted(self.sm.confirmed_fields),
        )

    def _run_danger_check(self, text: str, *, language: str, is_partial: bool) -> DetectionResult:
        vtype = self.sm.visit.visit_type.value if self.sm.visit.visit_type else None
        subject: str | None = None
        if vtype == "Newborn":
            subject = "newborn"
        elif vtype in ("ANC", "PNC"):
            subject = "mother"
        return detect_danger_signs(
            text,
            language=language,
            context={"is_partial": is_partial, "visit_type": vtype, "subject": subject},
        )

    async def on_partial_transcript(
        self, event: TranscriptEvent, orchestrator: VoiceSessionOrchestrator
    ) -> bool:
        """Layer 1 Danger-Sign Engine + live non-mutating field autofeed on EVERY partial transcript."""
        settings = get_settings()
        self._cancel_silence_timer()
        raw_lang = event.language_code or orchestrator.active_language or self.language
        lang = detect_language_from_text(event.text, fallback=raw_lang)
        self.sm.set_language(lang)
        self.language = lang
        orchestrator.active_language = lang

        if settings.danger_sign_partial_matching:
            result = self._run_danger_check(event.text, language=lang, is_partial=True)
            if result.danger_sign_flagged and result.matches:
                await self._trigger_danger_escalation(result, orchestrator, is_partial=True)
                return True

        # Live autofeed: extract structured fields from partial speech without mutating state machine
        partial_text = (event.text or "").strip()
        if len(partial_text) >= 4 and partial_text != getattr(self, "_last_partial_preview_text", None):
            self._last_partial_preview_text = partial_text
            existing_draft = self._build_draft_snapshot_for_extractor()
            preview = self._extractor.extract(
                partial_text,
                reference_date=self._reference_date,
                active_language=lang,
                existing_draft=existing_draft,
            )
            if preview.patch:
                preview_contract = self.current_visit_contract()
                updated_fields: list[str] = []
                for key in (
                    "beneficiary_id",
                    "beneficiary_name",
                    "visit_type",
                    "weight_kg",
                    "vaccinations_completed",
                    "vaccinations_due",
                    "next_visit_date",
                ):
                    if key in preview.patch and preview.patch[key] not in (None, []):
                        preview_contract[key] = preview.patch[key]
                        updated_fields.append(key)
                if "follow_up_actions" in preview.patch and preview.patch["follow_up_actions"]:
                    preview_contract["follow_up_actions"] = [
                        {
                            "action_type": _map_follow_up_action_type(a.action_type, preview_contract.get("visit_type")),
                            "description": a.description,
                            "due_date": a.due_date,
                            "priority": a.priority,
                            "source_phrase": a.source_phrase,
                        }
                        for a in preview.patch["follow_up_actions"]
                    ]
                    updated_fields.append("follow_up_actions")
                if updated_fields:
                    await orchestrator.emit_event(
                        "visit_draft_updated",
                        visit_id=self.sm.visit.visit_draft_id,
                        draft=preview_contract,
                        updated_fields=updated_fields,
                        missing_required_fields=self._missing_required_fields(),
                    )
        return False

    async def on_final_transcript(
        self, event: TranscriptEvent, orchestrator: VoiceSessionOrchestrator
    ) -> bool:
        """Process a final transcript through 1A (Danger) -> 1C (Extraction) -> 1B (State Machine)."""
        self._cancel_silence_timer()
        raw_lang = event.language_code or orchestrator.active_language or self.language
        lang = detect_language_from_text(event.text, fallback=raw_lang)
        self.sm.set_language(lang)
        self.language = lang
        orchestrator.active_language = lang

        # 1. Layer 1 Deterministic Danger-Sign Check (ALWAYS runs first; NEVER suppressed)
        danger_res = self._run_danger_check(event.text, language=lang, is_partial=False)
        danger_fired = False
        if danger_res.danger_sign_flagged and danger_res.matches:
            danger_fired = await self._trigger_danger_escalation(
                danger_res, orchestrator, is_partial=False
            )

        # If we were in DANGER_ESCALATION and worker continues speaking visit notes, resume workflow
        if self.sm.state == ConversationState.DANGER_ESCALATION and not danger_fired:
            self.sm.resume_after_danger()

        # 1b. Voice-Based Beneficiary Identity Verification & Lookup (Sections 1 & 2)
        if not danger_fired and self.sm.state in (
            ConversationState.IDENTITY_CONFIRMATION,
            ConversationState.CANDIDATE_CONFIRMATION,
        ):
            intent = classify_confirmation_intent(event.text)
            if intent == "confirm":
                transition = self.sm.handle_identity_confirmation_response(
                    event.text, language=lang
                )
                orchestrator.telemetry.steps.beneficiary_identified = True
                orchestrator.telemetry.steps.identity_voice_confirmed = True
                self._sync_stt_context_from_visit(orchestrator)
                await self._dispatch_transition(transition, orchestrator)
                return True

            if intent == "reject":
                rejected_id = self.sm.candidate_beneficiary_id
                rej_transition = self.sm.handle_identity_confirmation_response(
                    "no", language=lang
                )
                # Check if worker also spoke the replacement name/ID in the same utterance
                matches, spoken_id = self._directory.resolve_spoken_identity(
                    event.text, exclude_beneficiary_id=rejected_id
                )
                if matches or spoken_id is not None:
                    lookup_trans = self.sm.apply_beneficiary_lookup_result(
                        [(b.beneficiary_id, b.full_name) for b in matches],
                        language=lang,
                    )
                    if len(matches) == 1:
                        orchestrator.telemetry.steps.beneficiary_identified = True
                        self._sync_stt_context_from_visit(orchestrator)
                    await self._dispatch_transition(lookup_trans, orchestrator)
                    return True
                await self._dispatch_transition(rej_transition, orchestrator)
                return True

            # Unclear response: check if worker directly spoke a different beneficiary name/ID
            matches, spoken_id = self._directory.resolve_spoken_identity(
                event.text, exclude_beneficiary_id=self.sm.candidate_beneficiary_id
            )
            if matches or spoken_id is not None:
                lookup_trans = self.sm.apply_beneficiary_lookup_result(
                    [(b.beneficiary_id, b.full_name) for b in matches],
                    language=lang,
                )
                if len(matches) == 1:
                    orchestrator.telemetry.steps.beneficiary_identified = True
                await self._dispatch_transition(lookup_trans, orchestrator)
                return True

            unclear_trans = self.sm.handle_identity_confirmation_response(
                event.text, language=lang
            )
            await self._dispatch_transition(unclear_trans, orchestrator)
            return True

        if not danger_fired and self.sm.state in (
            ConversationState.IDENTITY_CORRECTION,
            ConversationState.BENEFICIARY_LOOKUP,
        ):
            matches, _spoken_id = self._directory.resolve_spoken_identity(event.text)
            lookup_trans = self.sm.apply_beneficiary_lookup_result(
                [(b.beneficiary_id, b.full_name) for b in matches],
                language=lang,
            )
            if len(matches) == 1:
                orchestrator.telemetry.steps.beneficiary_identified = True
            await self._dispatch_transition(lookup_trans, orchestrator)
            return True

        # 2. Extract structured healthcare visit fields (1C)
        existing_draft = self._build_draft_snapshot_for_extractor()
        extraction = self._extractor.extract(
            event.text,
            reference_date=self._reference_date,
            active_language=lang,
            existing_draft=existing_draft,
        )

        # 2a-bis. If worker rejected a confirmation and repeated a bare value (e.g. "101.2",
        # "120 by 80", "11.4", "2.8"), re-extract with the awaited field cue if needed.
        if self._awaiting_numeric_repeat_field:
            awaited = self._awaiting_numeric_repeat_field
            has_awaited = awaited in extraction.patch or any(
                o.key == awaited for o in extraction.observations
            )
            if (
                not has_awaited
                and not extraction.patch
                and not extraction.observations
                and classify_confirmation_intent(event.text) not in {"confirm", "reject"}
            ):
                cue_map = {
                    "weight_kg": "weight",
                    "next_visit_date": "next visit",
                    "beneficiary_id": "beneficiary id",
                    "temperature": "temp",
                    "blood_pressure": "bp",
                    "hemoglobin_g_dl": "hb",
                }
                cue = cue_map.get(awaited)
                if cue:
                    retry_ext = self._extractor.extract(
                        f"{cue} {event.text}",
                        reference_date=self._reference_date,
                        active_language=lang,
                        existing_draft=existing_draft,
                    )
                    if awaited in retry_ext.patch or any(
                        o.key == awaited for o in retry_ext.observations
                    ):
                        extraction = retry_ext
                        extraction.detected_correction = True

        # 2b. Optional secondary recognition (Section E): ONLY when a critical number is uncertain/inconsistent
        utterance_pcm = event.metadata.get("utterance_pcm")
        uncertainty = assess_numeric_uncertainty(
            event.text,
            extraction,
            stt_confidence=event.confidence,
        )
        if (
            uncertainty.should_recheck
            and isinstance(utterance_pcm, (bytes, bytearray))
            and len(utterance_pcm) > 0
            and self._secondary_recognizer is not None
        ):
            orchestrator.telemetry.secondary_recognition_runs += 1
            stt_obj = getattr(orchestrator, "_stt", None)
            ctx_snap = (
                stt_obj.context_snapshot()
                if stt_obj is not None and hasattr(stt_obj, "context_snapshot")
                else {}
            )
            try:
                sec_res = await self._secondary_recognizer.recognize_segment(
                    bytes(utterance_pcm),
                    sample_rate=int(event.metadata.get("sample_rate") or 16000),
                    language_code=str(ctx_snap.get("language_code") or "indic-auto"),
                    language_candidates=ctx_snap.get("language_candidates"),
                    keywords=ctx_snap.get("keywords"),
                    speaker_names=ctx_snap.get("speaker_names"),
                    previous_text=ctx_snap.get("previous_text"),
                    topic=ctx_snap.get("topic"),
                )
                sec_text = str(sec_res.get("transcript", "")).strip()
                if sec_text:
                    comparison = compare_numeric_interpretations(
                        extraction,
                        sec_text,
                        extractor=self._extractor,
                        reference_date=self._reference_date,
                        active_language=lang,
                        existing_draft=existing_draft,
                    )
                    if comparison.has_disagreement:
                        orchestrator.telemetry.secondary_recognition_conflicts += 1
                        disagreed_set = set(comparison.disagreed_fields)
                        for df in comparison.disagreed_fields:
                            extraction.patch.pop(df, None)
                            if df == "weight_kg":
                                extraction.patch.pop("weight_source_text", None)
                            elif df == "next_visit_date":
                                extraction.patch.pop("next_visit_date_source_text", None)
                            elif df == "beneficiary_id":
                                extraction.patch.pop("beneficiary_name", None)
                        # Remove disagreed numeric DynamicObservations so unconfirmed vitals don't commit
                        if disagreed_set & set(NUMERIC_OBSERVATION_KEYS):
                            extraction.observations = [
                                o for o in extraction.observations if o.key not in disagreed_set
                            ]
                            for obs_key in NUMERIC_OBSERVATION_KEYS:
                                if (
                                    obs_key in disagreed_set
                                    and len(comparison.candidate_values.get(obs_key, [])) == 1
                                    and comparison.candidate_observations.get(obs_key)
                                ):
                                    cand_obs = comparison.candidate_observations[obs_key][0]
                                    self._pending_obs_candidates[obs_key] = cand_obs.model_dump(mode="json")
                                    self._pending_source_texts[obs_key] = cand_obs.source_text or sec_text
                        # Replace clarifications on disagreed fields with comparison clarifications
                        extraction.clarifications = [
                            c for c in extraction.clarifications if c.field_name not in disagreed_set
                        ] + comparison.clarifications
                        # If secondary recovered a single candidate weight when primary omitted it,
                        # stage it as a needs_confirmation observation for mandatory worker confirmation.
                        if "weight_kg" in disagreed_set and len(comparison.candidate_values.get("weight_kg", [])) == 1:
                            cand_val = float(comparison.candidate_values["weight_kg"][0])
                            if not any(o.key == "weight_kg" for o in extraction.observations):
                                extraction.observations.append(
                                    DynamicObservation(
                                        key="weight_kg",
                                        label="Weight (Needs Confirmation)",
                                        value=cand_val,
                                        unit="kg",
                                        category="measurement",
                                        status="needs_confirmation",
                                        source_text=sec_text,
                                    )
                                )
            except Exception as exc:
                log_event(
                    logger,
                    "secondary_stt_skipped",
                    session=self.session_id,
                    reason=str(exc)[:120],
                )

        # 2c. Mandatory inline numeric confirmation when configured OR when awaiting repeat/uncertain
        existing_clar_fields = {c.field_name for c in extraction.clarifications}
        in_readback_or_submit = self.sm.state in (
            ConversationState.READ_BACK_CONFIRMATION,
            ConversationState.READY_TO_CONFIRM,
            ConversationState.ASK_READBACK_PREFERENCE,
            ConversationState.ASK_SUBMISSION_CONFIRMATION,
        )
        if self.confirm_important_numbers and not in_readback_or_submit:
            if (
                "weight_kg" in extraction.patch
                and "weight_kg" not in existing_clar_fields
                and self._awaiting_numeric_repeat_field != "weight_kg"
            ):
                cand_w = extraction.patch.pop("weight_kg")
                cand_src = extraction.patch.pop("weight_source_text", None)
                self._pending_source_texts["weight_kg"] = cand_src
                prompt_text = self._format_numeric_confirmation_prompt(
                    "weight_kg", cand_w, language=lang
                )
                extraction.clarifications.append(
                    FieldClarification(
                        field_name="weight_kg",
                        reason="ambiguous_value",
                        prompt_hint=prompt_text,
                        candidates=[format_decimal_clean(Decimal(str(cand_w)))],
                    )
                )
                extraction.observations.append(
                    DynamicObservation(
                        key="weight_kg",
                        label="Weight (Needs Confirmation)",
                        value=cand_w,
                        unit="kg",
                        category="measurement",
                        status="needs_confirmation",
                        source_text=cand_src or event.text,
                    )
                )

            if (
                "next_visit_date" in extraction.patch
                and "next_visit_date" not in existing_clar_fields
                and self._awaiting_numeric_repeat_field != "next_visit_date"
            ):
                cand_date = str(extraction.patch.pop("next_visit_date"))
                cand_src = extraction.patch.pop("next_visit_date_source_text", None)
                self._pending_source_texts["next_visit_date"] = cand_src
                if "follow_up_actions" in extraction.patch:
                    all_acts: list[FollowUpAction] = list(extraction.patch["follow_up_actions"])
                    held = [a for a in all_acts if a.due_date == cand_date]
                    kept = [a for a in all_acts if a.due_date != cand_date]
                    if held:
                        self._pending_follow_up_actions["next_visit_date"] = held
                    if kept:
                        extraction.patch["follow_up_actions"] = kept
                    else:
                        extraction.patch.pop("follow_up_actions", None)
                prompt_text = self._format_numeric_confirmation_prompt(
                    "next_visit_date", cand_date, language=lang
                )
                extraction.clarifications.append(
                    FieldClarification(
                        field_name="next_visit_date",
                        reason="ambiguous_value",
                        prompt_hint=prompt_text,
                        candidates=[cand_date],
                    )
                )

            if (
                "beneficiary_id" in extraction.patch
                and extraction.patch["beneficiary_id"] != self.sm.visit.beneficiary_id
                and "beneficiary_id" not in existing_clar_fields
                and self._awaiting_numeric_repeat_field != "beneficiary_id"
            ):
                cand_bid = str(extraction.patch.pop("beneficiary_id"))
                cand_bname = extraction.patch.pop("beneficiary_name", None)
                if cand_bname:
                    self._pending_beneficiary_names[cand_bid] = str(cand_bname)
                prompt_text = self._format_numeric_confirmation_prompt(
                    "beneficiary_id", cand_bid, language=lang
                )
                extraction.clarifications.append(
                    FieldClarification(
                        field_name="beneficiary_id",
                        reason="ambiguous_value",
                        prompt_hint=prompt_text,
                        candidates=[cand_bid],
                    )
                )

            gated_obs: list[DynamicObservation] = []
            for obs in extraction.observations:
                if (
                    obs.key in NUMERIC_OBSERVATION_KEYS
                    and obs.key not in existing_clar_fields
                    and self._awaiting_numeric_repeat_field != obs.key
                ):
                    self._pending_obs_candidates[obs.key] = obs.model_dump(mode="json")
                    self._pending_source_texts[obs.key] = obs.source_text or event.text
                    prompt_text = self._format_numeric_confirmation_prompt(
                        obs.key, obs.value, unit=obs.unit, language=lang
                    )
                    extraction.clarifications.append(
                        FieldClarification(
                            field_name=obs.key,
                            reason="ambiguous_value",
                            prompt_hint=prompt_text,
                            candidates=[str(obs.value)],
                        )
                    )
                else:
                    gated_obs.append(obs)
            extraction.observations = gated_obs

        # Ensure any uncertain numeric observation with a pending clarification is not silently saved
        clar_obs_keys = {
            c.field_name for c in extraction.clarifications if c.field_name in NUMERIC_OBSERVATION_KEYS
        }
        if clar_obs_keys:
            kept_obs: list[DynamicObservation] = []
            for obs in extraction.observations:
                if obs.key in clar_obs_keys:
                    self._pending_obs_candidates.setdefault(obs.key, obs.model_dump(mode="json"))
                else:
                    kept_obs.append(obs)
            extraction.observations = kept_obs

        if self._awaiting_numeric_repeat_field and (
            self._awaiting_numeric_repeat_field in extraction.patch
            or any(o.key == self._awaiting_numeric_repeat_field for o in extraction.observations)
        ):
            self._awaiting_numeric_repeat_field = None
            extraction.detected_correction = True

        # Preserve source provenance phrases and structured follow-ups for v1 contract
        if "weight_source_text" in extraction.patch:
            self._weight_source_text = extraction.patch["weight_source_text"]
        if "next_visit_date_source_text" in extraction.patch:
            self._next_visit_date_source_text = extraction.patch["next_visit_date_source_text"]

        extracted_followups: list[FollowUpAction] = extraction.patch.get("follow_up_actions", [])
        if extracted_followups:
            vtype_hint = extraction.patch.get("visit_type") or (
                self.sm.visit.visit_type.value if self.sm.visit.visit_type else None
            )
            for act in extracted_followups:
                mapped_type = _map_follow_up_action_type(act.action_type, vtype_hint)
                # Replace prior scheduled routine home visit follow-up when a new date is given
                if act.action_type == "routine_visit" and act.due_date:
                    self._structured_follow_ups = [
                        f
                        for f in self._structured_follow_ups
                        if not (
                            f.get("action_type") == mapped_type
                            and str(f.get("description", "")).startswith("Conduct")
                        )
                    ]
                if not any(
                    f.get("description") == act.description and f.get("due_date") == act.due_date
                    for f in self._structured_follow_ups
                ):
                    self._structured_follow_ups.append(
                        {
                            "action_type": mapped_type,
                            "description": act.description,
                            "due_date": act.due_date,
                            "priority": act.priority,
                            "source_phrase": act.source_phrase,
                        }
                    )

        # Build 1B ExtractionUpdate DTO
        sm_clarifications = [
            ClarificationRequest(
                field=c.field_name,
                reason=c.reason,
                question=c.prompt_hint,
                candidates=list(c.candidates),
            )
            for c in extraction.clarifications
        ]
        # Surface any conservative uncertain danger-sign matches as clarifications
        for um in danger_res.uncertain_matches:
            sm_clarifications.append(
                ClarificationRequest(
                    field="danger_signs",
                    reason="uncertain_danger_sign",
                    question=(
                        f"You mentioned '{um.matched_phrase}'. "
                        f"Is this severe or ongoing right now? Please clarify so I can check for danger signs."
                    ),
                )
            )

        update_kwargs: dict[str, Any] = {}
        explicit_fields: set[str] = set()
        for key in (
            "beneficiary_id",
            "beneficiary_name",
            "visit_type",
            "weight_kg",
            "vaccinations_completed",
            "vaccinations_due",
            "next_visit_date",
        ):
            if key in extraction.patch:
                update_kwargs[key] = extraction.patch[key]
                explicit_fields.add(key)

        if extracted_followups:
            update_kwargs["follow_up_actions"] = [a.description for a in extracted_followups]
            explicit_fields.add("follow_up_actions")

        obs_dicts = [o.model_dump(mode="json") for o in extraction.observations]
        if obs_dicts:
            update_kwargs["observations"] = obs_dicts
            explicit_fields.add("observations")

        event_dicts = [e.model_dump(mode="json") for e in extraction.events]
        if event_dicts:
            update_kwargs["events"] = event_dicts
            explicit_fields.add("events")

        rm_obs = set(extraction.remove_observation_keys)
        rm_ev = set(extraction.remove_event_names)
        trace_dict = extraction.trace.model_dump(mode="json") if extraction.trace else None

        update = ExtractionUpdate(
            **update_kwargs,
            remove_observation_keys=rm_obs,
            remove_event_names=rm_ev,
            trace=trace_dict,
            clarifications=sm_clarifications,
            explicit_fields=explicit_fields if explicit_fields else None,
            detected_language=lang,
        )

        # 3. Route into Conversation State Machine (1B)
        if danger_fired:
            # Record any extracted fields silently into the draft without interrupting urgent referral speech
            if explicit_fields or rm_obs or rm_ev:
                self.sm._apply_update_fields(
                    update, is_patch=bool(rm_obs or rm_ev), merge_lists=True
                )
                await orchestrator.emit_event(
                    "visit_draft_updated",
                    visit_id=self.sm.visit.visit_draft_id,
                    draft=self.current_visit_contract(),
                    updated_fields=sorted(explicit_fields),
                    missing_required_fields=self._missing_required_fields(),
                )
            return True

        if self.sm.state in (
            ConversationState.READ_BACK_CONFIRMATION,
            ConversationState.READY_TO_CONFIRM,
        ):
            patch_arg = update if explicit_fields else None
            # Handle explicit confirmation or correction
            transition = self.sm.handle_confirmation_response(
                event.text,
                correction_patch=patch_arg,
            )
            if patch_arg is not None:
                orchestrator.telemetry.correction_count += 1
            if self.sm.visit.status == VisitStatus.CONFIRMED:
                orchestrator.telemetry.steps.worker_confirmed = True
            await self._dispatch_transition(transition, orchestrator)
            return True

        # Section 6–8: Readback preference & Submission confirmation states
        if self.sm.state == ConversationState.ASK_READBACK_PREFERENCE:
            patch_arg = update if explicit_fields else None
            transition = self.sm.handle_readback_preference_response(
                event.text, correction_patch=patch_arg, language=lang
            )
            if transition.metadata.get("is_correction"):
                orchestrator.telemetry.correction_count += 1
            if self.sm.state == ConversationState.ASK_SUBMISSION_CONFIRMATION:
                orchestrator.telemetry.steps.read_back_completed = True
            await self._dispatch_transition(transition, orchestrator)
            return True

        if self.sm.state == ConversationState.ASK_SUBMISSION_CONFIRMATION:
            patch_arg = update if explicit_fields else None
            transition = self.sm.handle_submission_confirmation_response(
                event.text, correction_patch=patch_arg, language=lang
            )
            if transition.metadata.get("is_correction"):
                orchestrator.telemetry.correction_count += 1
            if self.sm.visit.status == VisitStatus.CONFIRMED:
                orchestrator.telemetry.steps.worker_confirmed = True
            await self._dispatch_transition(transition, orchestrator)
            return True

        # Clear any stale pending confirmation if the worker directly spoke a new value
        for f_cleared in list(explicit_fields) + [o.key for o in extraction.observations]:
            self._pending_numeric_confirmations.pop(f_cleared, None)

        # Pending confirmation of an ambiguous or uncertain numeric value (Section F)
        if self._pending_numeric_confirmations and not explicit_fields:
            amb_intent = classify_confirmation_intent(event.text)
            if amb_intent == "confirm":
                pending_field = next(iter(self._pending_numeric_confirmations))
                entry = self._pending_numeric_confirmations.pop(pending_field)
                pending: ExtractionUpdate = entry["patch"]
                src_text = entry.get("source_text")
                if pending_field == "weight_kg" and src_text:
                    self._weight_source_text = src_text
                elif pending_field == "next_visit_date" and src_text:
                    self._next_visit_date_source_text = src_text
                if pending_field == "next_visit_date":
                    for act in self._pending_follow_up_actions.pop("next_visit_date", []):
                        self._structured_follow_ups.append(
                            {
                                "action_type": _map_follow_up_action_type(
                                    act.action_type,
                                    self.sm.visit.visit_type.value if self.sm.visit.visit_type else None,
                                ),
                                "description": act.description,
                                "due_date": act.due_date,
                                "priority": act.priority,
                                "source_phrase": act.source_phrase,
                            }
                        )
                self.sm.pending_clarifications = [
                    c for c in self.sm.pending_clarifications if c.field != pending_field
                ]
                orchestrator.telemetry.numeric_confirmations_accepted += 1
                orchestrator.telemetry.correction_count += 1
                transition = self.sm.apply_continuous_update(
                    pending,
                    is_correction=True,
                    merge_lists=(pending_field in NUMERIC_OBSERVATION_KEYS),
                    language=lang,
                )
                if pending_field == "beneficiary_id" and self.sm.visit.beneficiary_id:
                    orchestrator.telemetry.steps.beneficiary_identified = True
                    orchestrator.telemetry.steps.identity_voice_confirmed = True
                    self._sync_stt_context_from_visit(orchestrator)
                await self._dispatch_transition(transition, orchestrator)
                if self._pending_numeric_confirmations:
                    next_field = next(iter(self._pending_numeric_confirmations))
                    next_hint = self._pending_numeric_confirmations[next_field].get("prompt_hint")
                    if next_hint:
                        orchestrator.telemetry.numeric_confirmations_requested += 1
                        await orchestrator.emit_event(
                            "clarification_required",
                            visit_id=self.sm.visit.visit_draft_id,
                            field=next_field,
                            reason="ambiguous_value",
                            prompt_text=next_hint,
                            language=lang,
                        )
                        await orchestrator.speak_direct(next_hint, language=lang)
                return True
            if amb_intent == "reject":
                rejected_field = next(iter(self._pending_numeric_confirmations))
                self._pending_numeric_confirmations.pop(rejected_field, None)
                self._pending_source_texts.pop(rejected_field, None)
                self._pending_obs_candidates.pop(rejected_field, None)
                self._pending_follow_up_actions.pop(rejected_field, None)
                self._awaiting_numeric_repeat_field = rejected_field
                self.sm.pending_clarifications = []
                orchestrator.telemetry.numeric_confirmations_rejected += 1
                repeat_prompt = self._format_repeat_numeric_prompt(rejected_field, language=lang)
                await orchestrator.emit_event(
                    "clarification_required",
                    visit_id=self.sm.visit.visit_draft_id,
                    field=rejected_field,
                    reason="ambiguous_value",
                    prompt_text=repeat_prompt,
                    language=lang,
                )
                await orchestrator.speak_direct(repeat_prompt, language=lang)
                return True

        # Continuous editing workflow (Basic Mode live conversation, Sections 1–9)
        if self.continuous_editing:
            done_intent = is_completion_intent(event.text)
            if explicit_fields or sm_clarifications or rm_obs or rm_ev:
                orchestrator.telemetry.steps.visit_notes_captured = True
                # Capture pending ambiguous/uncertain numeric candidates for YES/NO spoken confirmation
                for c in sm_clarifications:
                    if (
                        c.field in IMPORTANT_CONFIRMABLE_FIELDS
                        and c.reason in {"ambiguous_value", "conflict"}
                        and c.candidates
                    ):
                        if len(c.candidates) == 1:
                            cand_raw = c.candidates[0]
                            patch_obj: ExtractionUpdate | None = None
                            if c.field == "weight_kg":
                                try:
                                    patch_obj = ExtractionUpdate(
                                        weight_kg=float(cand_raw),
                                        explicit_fields={"weight_kg"},
                                        detected_language=lang,
                                    )
                                except ValueError:
                                    patch_obj = None
                            elif c.field == "next_visit_date":
                                patch_obj = ExtractionUpdate(
                                    next_visit_date=str(cand_raw),
                                    explicit_fields={"next_visit_date"},
                                    detected_language=lang,
                                )
                            elif c.field == "beneficiary_id":
                                bid = str(cand_raw).strip().upper()
                                bname = self._pending_beneficiary_names.pop(bid, None)
                                if not bname:
                                    ben = self._directory.get_by_id(bid)
                                    bname = ben.full_name if ben else None
                                exp_set = {"beneficiary_id"} | ({"beneficiary_name"} if bname else set())
                                patch_obj = ExtractionUpdate(
                                    beneficiary_id=bid,
                                    beneficiary_name=bname,
                                    explicit_fields=exp_set,
                                    detected_language=lang,
                                )
                            elif c.field in NUMERIC_OBSERVATION_KEYS:
                                obs_dict = self._pending_obs_candidates.pop(c.field, None)
                                if obs_dict is None:
                                    unit_defaults = {
                                        "temperature": "°F",
                                        "blood_pressure": "mmHg",
                                        "hemoglobin_g_dl": "g/dL",
                                    }
                                    label_defaults = {
                                        "temperature": "Temperature",
                                        "blood_pressure": "Blood Pressure",
                                        "hemoglobin_g_dl": "Hemoglobin (Hb)",
                                    }
                                    val_parsed: Any = cand_raw
                                    if c.field in {"temperature", "hemoglobin_g_dl"}:
                                        try:
                                            val_parsed = float(cand_raw)
                                        except ValueError:
                                            val_parsed = cand_raw
                                    obs_dict = DynamicObservation(
                                        key=c.field,
                                        label=label_defaults[c.field],
                                        value=val_parsed,
                                        unit=unit_defaults[c.field],
                                        category="measurement",
                                        status="confirmed",
                                        source_text=self._pending_source_texts.get(c.field) or event.text,
                                    ).model_dump(mode="json")
                                else:
                                    obs_dict["status"] = "confirmed"
                                patch_obj = ExtractionUpdate(
                                    observations=[obs_dict],
                                    explicit_fields={"observations"},
                                    detected_language=lang,
                                )
                            if patch_obj is not None:
                                self._pending_numeric_confirmations[c.field] = {
                                    "patch": patch_obj,
                                    "source_text": self._pending_source_texts.pop(c.field, None),
                                    "prompt_hint": c.question,
                                }
                                orchestrator.telemetry.numeric_confirmations_requested += 1
                        elif c.reason == "conflict":
                            # Conflicting values: ask worker to repeat/choose without staging either
                            self._awaiting_numeric_repeat_field = c.field
                            orchestrator.telemetry.numeric_confirmations_requested += 1
                if (extraction.detected_correction and explicit_fields) or rm_obs or rm_ev:
                    orchestrator.telemetry.correction_count += 1
                transition = self.sm.apply_continuous_update(
                    update,
                    is_correction=bool(extraction.detected_correction or rm_obs or rm_ev),
                    merge_lists=True,
                    language=lang,
                )
                if self.sm.visit.beneficiary_id:
                    orchestrator.telemetry.steps.beneficiary_identified = True
                    self._sync_stt_context_from_visit(orchestrator)
                    if self.sm.identity_verified:
                        orchestrator.telemetry.steps.identity_voice_confirmed = True
                orchestrator.telemetry.steps.clarifications_resolved = (
                    len(self.sm.pending_clarifications) == 0
                )
                if not self._missing_required_fields():
                    orchestrator.telemetry.steps.required_fields_extracted = True
                await self._dispatch_transition(transition, orchestrator)
                if done_intent and not self.sm.pending_clarifications:
                    done_trans = self.sm.indicate_worker_done(language=lang)
                    await self._dispatch_transition(done_trans, orchestrator)
                return True

            if done_intent:
                done_trans = self.sm.indicate_worker_done(language=lang)
                await self._dispatch_transition(done_trans, orchestrator)
                return True

            return False

        # Legacy single-shot path (when continuous_editing=False)
        # If worker gave an explicit correction while gathering/clarifying
        if extraction.detected_correction and explicit_fields:
            orchestrator.telemetry.correction_count += 1
            transition = self.sm.apply_correction_patch(update)
            await self._dispatch_transition(transition, orchestrator)
            return True

        # If nothing clinical/structured was extracted at all (e.g. greeting or general chitchat)
        if not explicit_fields and not sm_clarifications:
            # Let Milestone 1 LLM handle conversational greeting naturally unless awaiting confirmation
            return False

        orchestrator.telemetry.steps.visit_notes_captured = True
        transition = self.sm.apply_extraction(update)
        if self.sm.visit.beneficiary_id:
            orchestrator.telemetry.steps.beneficiary_identified = True
            if self.sm.identity_verified:
                orchestrator.telemetry.steps.identity_voice_confirmed = True
        orchestrator.telemetry.steps.clarifications_resolved = (
            len(self.sm.pending_clarifications) == 0
        )
        if not self._missing_required_fields():
            orchestrator.telemetry.steps.required_fields_extracted = True
        if self.sm.state in (
            ConversationState.READ_BACK_CONFIRMATION,
            ConversationState.READY_TO_CONFIRM,
        ):
            orchestrator.telemetry.steps.read_back_completed = True
        await self._dispatch_transition(transition, orchestrator)
        return True

    async def handle_finish_review_command(
        self, orchestrator: VoiceSessionOrchestrator
    ) -> None:
        """Handle explicit UI/WS request to finish note collection and enter final review."""
        self._cancel_silence_timer()
        transition = self.sm.indicate_worker_done(language=self.language)
        await self._dispatch_transition(transition, orchestrator)

    async def handle_silence_timeout(
        self, orchestrator: VoiceSessionOrchestrator
    ) -> None:
        """Handle silence timeout during readback preference or submission confirmation."""
        transition = self.sm.handle_silence_timeout()
        if transition.actions or transition.spoken_text:
            await self._dispatch_transition(transition, orchestrator)

    async def handle_visual_patch(
        self, fields: dict[str, Any], orchestrator: VoiceSessionOrchestrator
    ) -> None:
        """Apply visual UI field edits onto the exact same backend VisitRecordState."""
        self._cancel_silence_timer()
        kwargs: dict[str, Any] = {}
        explicit: set[str] = set()
        clear_fields: set[str] = set()

        if "beneficiary_id" in fields:
            bid = fields["beneficiary_id"]
            if bid:
                ben = self._directory.get_by_id(str(bid))
                if ben is not None:
                    kwargs["beneficiary_id"] = ben.beneficiary_id
                    kwargs["beneficiary_name"] = ben.full_name
                    explicit.update({"beneficiary_id", "beneficiary_name"})
        if "visit_type" in fields:
            if fields["visit_type"]:
                kwargs["visit_type"] = fields["visit_type"]
                explicit.add("visit_type")
            else:
                clear_fields.add("visit_type")
        if "weight_kg" in fields:
            if fields["weight_kg"] is not None and fields["weight_kg"] != "":
                kwargs["weight_kg"] = float(fields["weight_kg"])
                explicit.add("weight_kg")
            else:
                clear_fields.add("weight_kg")
        if "next_visit_date" in fields:
            if fields["next_visit_date"]:
                kwargs["next_visit_date"] = str(fields["next_visit_date"])
                explicit.add("next_visit_date")
            else:
                clear_fields.add("next_visit_date")
        if "vaccinations_completed" in fields and isinstance(fields["vaccinations_completed"], list):
            kwargs["vaccinations_completed"] = [str(x) for x in fields["vaccinations_completed"] if str(x).strip()]
            explicit.add("vaccinations_completed")
        if "vaccinations_due" in fields and isinstance(fields["vaccinations_due"], list):
            kwargs["vaccinations_due"] = [str(x) for x in fields["vaccinations_due"] if str(x).strip()]
            explicit.add("vaccinations_due")
        if "observations" in fields and isinstance(fields["observations"], list):
            kwargs["observations"] = [dict(x) for x in fields["observations"] if isinstance(x, dict)]
            explicit.add("observations")
        if "events" in fields and isinstance(fields["events"], list):
            kwargs["events"] = [dict(x) for x in fields["events"] if isinstance(x, dict)]
            explicit.add("events")

        if not explicit and not clear_fields:
            return

        update = ExtractionUpdate(
            **kwargs,
            explicit_fields=explicit if explicit else None,
            clear_fields=clear_fields,
            detected_language=self.language,
        )
        orchestrator.telemetry.correction_count += 1
        transition = self.sm.apply_continuous_update(
            update, is_correction=True, merge_lists=False, language=self.language
        )
        await self._dispatch_transition(transition, orchestrator)

    async def handle_remove_item(
        self,
        *,
        observation_key: str | None = None,
        event_name: str | None = None,
        orchestrator: VoiceSessionOrchestrator,
    ) -> None:
        """Handle explicit removal of a dynamic observation or repeatable event."""
        self._cancel_silence_timer()
        rm_obs = {observation_key} if observation_key else set()
        rm_ev = {event_name} if event_name else set()
        if not rm_obs and not rm_ev:
            return
        update = ExtractionUpdate(
            remove_observation_keys=rm_obs,
            remove_event_names=rm_ev,
            detected_language=self.language,
        )
        orchestrator.telemetry.correction_count += 1
        transition = self.sm.apply_continuous_update(
            update, is_correction=True, merge_lists=True, language=self.language
        )
        await self._dispatch_transition(transition, orchestrator)

    async def handle_explicit_confirm_command(
        self, confirmed: bool, orchestrator: VoiceSessionOrchestrator
    ) -> None:
        """Handle client `confirm_visit` WS command."""
        self._cancel_silence_timer()
        utterance = "yes confirm" if confirmed else "no"
        if self.sm.state == ConversationState.ASK_READBACK_PREFERENCE:
            transition = self.sm.handle_readback_preference_response(utterance, language=self.language)
            await self._dispatch_transition(transition, orchestrator)
            return
        if self.sm.state == ConversationState.ASK_SUBMISSION_CONFIRMATION:
            transition = self.sm.handle_submission_confirmation_response(utterance, language=self.language)
            if self.sm.visit.status == VisitStatus.CONFIRMED:
                orchestrator.telemetry.steps.worker_confirmed = True
            await self._dispatch_transition(transition, orchestrator)
            return
        if self.sm.state in (
            ConversationState.CONTINUE_CONVERSATION,
            ConversationState.GATHERING_NOTES,
            ConversationState.FINAL_REVIEW_READY,
        ):
            if confirmed:
                # Direct UI "Accept & Save" from review screen validates and submits
                self.sm.state = ConversationState.ASK_SUBMISSION_CONFIRMATION
                transition = self.sm.handle_submission_confirmation_response("yes", language=self.language)
                if self.sm.visit.status == VisitStatus.CONFIRMED:
                    orchestrator.telemetry.steps.worker_confirmed = True
                await self._dispatch_transition(transition, orchestrator)
                return
            done_trans = self.sm.indicate_worker_done(language=self.language)
            await self._dispatch_transition(done_trans, orchestrator)
            return

        if self.sm.state not in (
            ConversationState.READ_BACK_CONFIRMATION,
            ConversationState.READY_TO_CONFIRM,
        ):
            if confirmed:
                await orchestrator.emit_event(
                    "error",
                    code="INVALID_STATE_TRANSITION",
                    message="Visit record must complete read-back before confirmation.",
                    retryable=False,
                )
                return
        transition = self.sm.handle_confirmation_response(utterance)
        await self._dispatch_transition(transition, orchestrator)

    async def handle_persistence_ack(
        self,
        *,
        accepted: bool,
        persistence_record_id: str | None = None,
        committed_at: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        emit_ws: bool = True,
    ) -> dict[str, Any]:
        """Process Agent 3 persistence acknowledgement (HTTP or WS)."""
        if self.sm.visit.status != VisitStatus.CONFIRMED and accepted:
            raise InvalidTransitionError(
                f"Cannot commit visit '{self.sm.visit.visit_draft_id}' while status is "
                f"'{self.sm.visit.status.value}'. Explicit worker confirmation is required first."
            )

        transition = self.sm.handle_persistence_result(
            accepted=accepted,
            record_id=persistence_record_id,
            error=error_message,
        )
        if accepted:
            self._committed_at = committed_at or utc_now_iso()
            if self._orchestrator is not None:
                self._orchestrator.telemetry.steps.worker_confirmed = True
                self._orchestrator.telemetry.steps.visit_persisted = True

        if emit_ws and self._orchestrator is not None:
            await self._dispatch_transition(
                transition,
                self._orchestrator,
                error_code=error_code,
            )

        return {
            "schema_version": "v1",
            "session_id": self.session_id,
            "visit_id": self.sm.visit.visit_draft_id,
            "status": self.sm.visit.status.value,
            "persistence_record_id": self.sm.visit.record_id,
            "committed_at": self._committed_at,
        }

    async def _trigger_danger_escalation(
        self,
        detection: DetectionResult,
        orchestrator: VoiceSessionOrchestrator,
        *,
        is_partial: bool,
    ) -> bool:
        """Interrupt active speech immediately, emit v1 `danger_alert`, speak urgent PHC referral."""
        lang = normalize_language(detection.active_language or self.language)
        referral_msg = detection.referral_message or get_referral_message(lang)
        emitted_new_urgent = False

        for match in detection.matches:
            already_seen = match.canonical_id in self._contract_alerts
            alert_id = (
                self._contract_alerts[match.canonical_id]["alert_id"]
                if already_seen
                else f"alrt_{uuid.uuid4().hex[:12]}"
            )
            contract_alert = format_danger_alert_contract(
                alert_id=alert_id,
                session_id=self.session_id,
                visit_id=self.sm.visit.visit_draft_id,
                beneficiary_id=self.sm.visit.beneficiary_id,
                match=match,
                language=lang,
                referral_message=referral_msg,
                detected_at=(
                    self._contract_alerts[match.canonical_id]["detected_at"]
                    if already_seen
                    else utc_now_iso()
                ),
            )
            self._contract_alerts[match.canonical_id] = contract_alert

            sm_input = DangerAlertInput(
                alert_id=alert_id,
                canonical_id=match.canonical_id,
                category=match.category,
                display_name=match.canonical_name,
                matched_phrase=match.evidence_text or match.matched_phrase,
                guideline_reference=f"{match.source_doc} ({match.source_section})",
                confidence=match.confidence,
                is_partial=is_partial,
                escalation_message=referral_msg,
                language=lang,
            )
            self.sm.handle_danger_detection(sm_input)

            if not already_seen:
                emitted_new_urgent = True
                log_event(
                    logger,
                    "danger_sign_escalated",
                    session=self.session_id,
                    canonical_id=match.canonical_id,
                    is_partial=is_partial,
                )
                await orchestrator.emit_event(
                    "danger_alert",
                    priority="urgent",
                    danger_sign_flagged=True,
                    interrupts_speech=True,
                    alert=contract_alert,
                )

        if emitted_new_urgent:
            await orchestrator.emit_event(
                "visit_draft_updated",
                visit_id=self.sm.visit.visit_draft_id,
                draft=self.current_visit_contract(),
                updated_fields=["danger_signs", "danger_sign_flagged", "follow_up_actions"],
                missing_required_fields=self._missing_required_fields(),
            )
            await orchestrator.speak_urgent(referral_msg, language=lang)
        return emitted_new_urgent

    def _missing_required_fields(self) -> list[str]:
        missing: list[str] = []
        if self.sm.visit.beneficiary_id is None or not self.sm.identity_verified:
            missing.append("beneficiary_id")
        if self.sm.visit.visit_type is None:
            missing.append("visit_type")
        if not self.sm.visit.has_clinical_observation():
            missing.append("clinical_observation")
        return missing

    def _normalize_clarification_reason(self, field: str, reason: str) -> str:
        r = (reason or "").lower()
        if r in ("ambiguous_beneficiary", "missing_required", "ambiguous_value", "uncertain_danger_sign", "conflict"):
            return r
        if field == "beneficiary_id" and "ambig" in r:
            return "ambiguous_beneficiary"
        if "missing" in r:
            return "missing_required"
        if "conflict" in r:
            return "conflict"
        if "danger" in r:
            return "uncertain_danger_sign"
        return "ambiguous_value"

    async def _dispatch_transition(
        self,
        transition: TransitionResult,
        orchestrator: VoiceSessionOrchestrator,
        *,
        error_code: str | None = None,
        is_greeting: bool = False,
    ) -> None:
        """Emit strict v1 contract WebSocket events & trigger TTS for a 1B TransitionResult."""
        visit_id = self.sm.visit.visit_draft_id
        lang = normalize_language(transition.spoken_language)
        next_turn_id = max(1, orchestrator.active_turn_id + 1)

        for action in transition.actions:
            atype = action.action_type
            payload = action.payload

            if atype == ActionType.DRAFT_UPDATED:
                updated_fields = list(
                    payload.get("updated_fields") or payload.get("changed_fields") or []
                )
                await orchestrator.emit_event(
                    "visit_draft_updated",
                    visit_id=visit_id,
                    draft=self.current_visit_contract(),
                    updated_fields=updated_fields,
                    missing_required_fields=self._missing_required_fields(),
                )

            elif atype == ActionType.CLARIFICATION_PROMPT:
                raw_clars = payload.get("clarifications", [])
                first = raw_clars[0] if raw_clars else {"field": "visit_notes", "reason": "missing_required"}
                field_name = str(first.get("field", "visit_notes"))
                candidates = []
                for c in first.get("candidates") or []:
                    c_str = str(c)
                    cid = c_str.split(":", 1)[0].strip() if ":" in c_str else c_str
                    candidates.append({"id": cid, "label": c_str, "detail": None})
                ev_kwargs: dict[str, Any] = {
                    "visit_id": visit_id,
                    "field": field_name,
                    "reason": self._normalize_clarification_reason(field_name, str(first.get("reason", ""))),
                    "prompt_text": transition.spoken_text or first.get("question") or f"Please clarify {field_name}.",
                    "language": lang,
                }
                if candidates:
                    ev_kwargs["candidates"] = candidates
                await orchestrator.emit_event("clarification_required", **ev_kwargs)

            elif atype == ActionType.CORRECTION_APPLIED:
                corrected = list(payload.get("patched_fields") or payload.get("corrected_fields") or [])
                if not corrected:
                    corrected = ["visit_record"]
                draft_dict = self.current_visit_contract()
                preserved = [
                    k
                    for k in ("beneficiary_id", "visit_type", "weight_kg", "vaccinations_due", "next_visit_date", "danger_sign_flagged")
                    if k not in corrected and draft_dict.get(k) not in (None, [], False)
                ]
                await orchestrator.emit_event(
                    "correction_applied",
                    visit_id=visit_id,
                    corrected_fields=corrected,
                    previous_values=dict(payload.get("previous_values", {})),
                    new_values={k: draft_dict.get(k) for k in corrected if k in draft_dict},
                    preserved_fields=preserved,
                    requires_re_read_back=True,
                    draft=draft_dict,
                )

            elif atype == ActionType.READ_BACK_STARTED:
                summary = payload.get("read_back_text") or transition.spoken_text or "Visit summary."
                await orchestrator.emit_event(
                    "read_back_started",
                    visit_id=visit_id,
                    turn_id=next_turn_id,
                    summary_text=summary,
                    language=lang,
                    draft=self.current_visit_contract(),
                )

            elif atype == ActionType.WORKER_CONFIRMED:
                self._confirmed_at = utc_now_iso()
                await orchestrator.emit_event(
                    "visit_confirmed",
                    visit_id=visit_id,
                    confirmed_at=self._confirmed_at,
                    visit=self.current_visit_contract(),
                )

            elif atype == ActionType.PERSISTENCE_REQUESTED:
                corr_id = f"corr_{uuid.uuid4().hex[:10]}"
                await orchestrator.emit_event(
                    "persistence_requested",
                    correlation_id=corr_id,
                    visit_id=visit_id,
                    visit=self.current_visit_contract(),
                    danger_alerts=self.current_alerts_contract(),
                )

            elif atype == ActionType.VISIT_COMMITTED:
                await orchestrator.emit_event(
                    "visit_committed",
                    visit_id=visit_id,
                    visit=self.current_visit_contract(),
                    persistence_record_id=self.sm.visit.record_id or "persisted",
                    committed_at=self._committed_at or utc_now_iso(),
                )

            elif atype == ActionType.PERSISTENCE_REJECTED:
                await orchestrator.emit_event(
                    "persistence_rejected",
                    visit_id=visit_id,
                    code=error_code or "PERSISTENCE_FAILED",
                    reason=payload.get("error") or "Persistence layer rejected visit write.",
                    retryable=True,
                )

        if transition.spoken_text:
            if transition.is_urgent or transition.interrupt_speech:
                await orchestrator.speak_urgent(
                    transition.spoken_text, language=transition.spoken_language
                )
            else:
                await orchestrator.speak_direct(
                    transition.spoken_text,
                    language=transition.spoken_language,
                    is_greeting=is_greeting,
                )
            if transition.current_state == ConversationState.READ_BACK_CONFIRMATION:
                self.sm.on_read_back_completed()
                orchestrator.telemetry.steps.read_back_completed = True

        # Emit v1 `clarification_required` prompts for readback preference & submission confirmation
        # so the frontend stays strictly backend-driven without breaking shared-contracts/v1 schemas.
        if transition.current_state == ConversationState.ASK_READBACK_PREFERENCE:
            await orchestrator.emit_event(
                "clarification_required",
                visit_id=visit_id,
                field="readback_preference",
                reason="missing_required",
                prompt_text=transition.spoken_text or "Would you like me to read the complete visit summary aloud?",
                language=lang,
                candidates=[
                    {"id": "yes", "label": "Yes, Read Summary Aloud", "detail": None},
                    {"id": "no", "label": "No, Skip Summary", "detail": None},
                ],
            )
            self._schedule_silence_timer_if_needed(orchestrator)
        elif transition.current_state == ConversationState.ASK_SUBMISSION_CONFIRMATION:
            await orchestrator.emit_event(
                "clarification_required",
                visit_id=visit_id,
                field="submission_confirmation",
                reason="missing_required",
                prompt_text=transition.spoken_text or "Would you like to submit and save this visit now?",
                language=lang,
                candidates=[
                    {"id": "yes", "label": "Yes, Submit & Save", "detail": None},
                    {"id": "no", "label": "No, Keep as Draft", "detail": None},
                ],
            )
            self._schedule_silence_timer_if_needed(orchestrator)


class SessionRegistry:
    """In-memory active session registry linking REST control plane & live WS pipelines."""

    def __init__(self) -> None:
        self._meta: dict[str, dict[str, Any]] = {}
        self._pipelines: dict[str, HealthcareSessionPipeline] = {}

    def create_session(
        self,
        *,
        session_id: str,
        language: str,
        beneficiary_id: str | None,
        worker_id: str,
        created_at: str,
    ) -> HealthcareSessionPipeline:
        self._meta[session_id] = {
            "session_id": session_id,
            "language": language,
            "beneficiary_id": beneficiary_id,
            "worker_id": worker_id,
            "created_at": created_at,
        }
        pipeline = HealthcareSessionPipeline(
            session_id=session_id,
            worker_id=worker_id,
            language=language if language != "indic-auto" else get_settings().default_language,
            beneficiary_id=beneficiary_id,
        )
        self._pipelines[session_id] = pipeline
        return pipeline

    def get_metadata(self, session_id: str) -> dict[str, Any] | None:
        return self._meta.get(session_id)

    def get_or_create_pipeline(
        self,
        session_id: str,
        *,
        language: str = "hi-IN",
        beneficiary_id: str | None = None,
        worker_id: str = "ASHA-DEMO-01",
    ) -> HealthcareSessionPipeline:
        if session_id in self._pipelines:
            return self._pipelines[session_id]
        meta = self._meta.get(session_id, {})
        return self.create_session(
            session_id=session_id,
            language=meta.get("language", language),
            beneficiary_id=meta.get("beneficiary_id", beneficiary_id),
            worker_id=meta.get("worker_id", worker_id),
            created_at=meta.get("created_at", utc_now_iso()),
        )

    def get_pipeline(self, session_id: str) -> HealthcareSessionPipeline | None:
        return self._pipelines.get(session_id)


session_registry = SessionRegistry()
