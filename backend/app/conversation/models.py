"""Typed Pydantic models and DTOs for the Phase 2 conversation state machine.

This module is intentionally decoupled from Pipecat, Gnani STT/TTS transports,
and sibling modules (`danger_signs`, `extraction`) so Agent 1 can wire 1A, 1B,
and 1C together via clean typed contracts.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


def utc_now_iso() -> str:
    """Return current UTC timestamp as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


SUPPORTED_LANGUAGES: tuple[str, ...] = ("hi-IN", "en-IN", "kn-IN", "ta-IN")

_LANGUAGE_ALIASES: dict[str, str] = {
    "hi": "hi-IN",
    "hi-in": "hi-IN",
    "hindi": "hi-IN",
    "hinglish": "hi-IN",
    "en": "en-IN",
    "en-in": "en-IN",
    "en-us": "en-IN",
    "en-gb": "en-IN",
    "english": "en-IN",
    "kn": "kn-IN",
    "kn-in": "kn-IN",
    "kannada": "kn-IN",
    "ta": "ta-IN",
    "ta-in": "ta-IN",
    "tamil": "ta-IN",
}


def normalize_language(language: str | None, *, default: str = "hi-IN") -> str:
    """Normalize a language tag to a supported BCP-47 locale."""
    if not language:
        return default
    cleaned = language.strip().lower().replace("_", "-")
    if cleaned in _LANGUAGE_ALIASES:
        return _LANGUAGE_ALIASES[cleaned]
    for supported in SUPPORTED_LANGUAGES:
        if cleaned == supported.lower():
            return supported
    return default


def detect_language_from_text(text: str | None, *, fallback: str = "hi-IN") -> str:
    """Detect the active Indic language from Unicode script ranges in transcript text."""
    if text:
        for ch in text:
            code = ord(ch)
            if 0x0B80 <= code <= 0x0BFF:
                return "ta-IN"
            if 0x0C80 <= code <= 0x0CFF:
                return "kn-IN"
            if 0x0C00 <= code <= 0x0C7F:
                return "te-IN"
            if 0x0D00 <= code <= 0x0D7F:
                return "ml-IN"
            if 0x0980 <= code <= 0x09FF:
                return "bn-IN"
            if 0x0A80 <= code <= 0x0AFF:
                return "gu-IN"
            if 0x0A00 <= code <= 0x0A7F:
                return "pa-IN"
            if 0x0900 <= code <= 0x097F:
                if fallback and fallback.lower().startswith("mr"):
                    return "mr-IN"
                return "hi-IN"
    if fallback and fallback.lower() in (
        "te-in",
        "ml-in",
        "bn-in",
        "mr-in",
        "gu-in",
        "pa-in",
    ):
        return fallback[:2].lower() + "-IN"
    return normalize_language(fallback)


class ConversationState(str, Enum):
    """States of the ASHA voice visit workflow state machine."""

    IDLE = "IDLE"
    SESSION_START = "SESSION_START"
    BENEFICIARY_GREETING = "BENEFICIARY_GREETING"
    IDENTITY_CONFIRMATION = "IDENTITY_CONFIRMATION"
    IDENTITY_CORRECTION = "IDENTITY_CORRECTION"
    BENEFICIARY_LOOKUP = "BENEFICIARY_LOOKUP"
    CANDIDATE_CONFIRMATION = "CANDIDATE_CONFIRMATION"
    GATHERING_NOTES = "GATHERING_NOTES"
    STREAMING_TRANSCRIPTION = "STREAMING_TRANSCRIPTION"
    CONTINUE_CONVERSATION = "CONTINUE_CONVERSATION"
    EXTRACTING_FIELDS = "EXTRACTING_FIELDS"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    FINAL_REVIEW_READY = "FINAL_REVIEW_READY"
    ASK_READBACK_PREFERENCE = "ASK_READBACK_PREFERENCE"
    READ_COMPLETE_SUMMARY = "READ_COMPLETE_SUMMARY"
    ASK_SUBMISSION_CONFIRMATION = "ASK_SUBMISSION_CONFIRMATION"
    READ_BACK_CONFIRMATION = "READ_BACK_CONFIRMATION"
    CORRECTION_PATCH = "CORRECTION_PATCH"
    READY_TO_CONFIRM = "READY_TO_CONFIRM"
    COMMITTED = "COMMITTED"
    DANGER_ESCALATION = "DANGER_ESCALATION"

    # Section 8 & Section 9 canonical aliases
    GATHERING_VISIT_NOTES = "GATHERING_NOTES"
    LIVE_TRANSCRIPTION = "STREAMING_TRANSCRIPTION"
    FIELD_EXTRACTION = "EXTRACTING_FIELDS"
    VISIT_DRAFT_UPDATED = "CONTINUE_CONVERSATION"
    NEW_INFORMATION = "CONTINUE_CONVERSATION"
    CORRECTION = "CORRECTION_PATCH"
    PATCH_VISIT_RECORD = "CORRECTION_PATCH"
    WORKER_INDICATES_DONE = "FINAL_REVIEW_READY"
    CLARIFICATION_IF_REQUIRED = "CLARIFICATION_REQUIRED"
    READ_BACK = "READ_BACK_CONFIRMATION"
    WORKER_CONFIRMATION = "READY_TO_CONFIRM"
    VALIDATE = "READY_TO_CONFIRM"
    SUBMIT_TO_BACKEND = "READY_TO_CONFIRM"
    SAVE_VISIT = "COMMITTED"
    VISIT_SAVED = "COMMITTED"
    PRESERVE_DRAFT = "CONTINUE_CONVERSATION"
    SESSION_CONTINUES_OR_ENDS = "COMMITTED"


class VisitStatus(str, Enum):
    """Lifecycle status distinguishing draft, worker-confirmed, and durably committed."""

    DRAFT = "draft"
    CONFIRMED = "confirmed"
    COMMITTED = "committed"


class VisitType(str, Enum):
    """Supported ASHA home-visit types."""

    ANC = "ANC"
    PNC = "PNC"
    NEWBORN = "Newborn"
    IMMUNISATION = "Immunisation"


_VISIT_TYPE_ALIASES: dict[str, VisitType] = {
    "anc": VisitType.ANC,
    "antenatal": VisitType.ANC,
    "pnc": VisitType.PNC,
    "postnatal": VisitType.PNC,
    "newborn": VisitType.NEWBORN,
    "hbnc": VisitType.NEWBORN,
    "neonatal": VisitType.NEWBORN,
    "immunisation": VisitType.IMMUNISATION,
    "immunization": VisitType.IMMUNISATION,
    "vaccination": VisitType.IMMUNISATION,
}


def coerce_visit_type(value: Any) -> VisitType | None:
    """Normalize string or enum values to canonical VisitType."""
    if value is None:
        return None
    if isinstance(value, VisitType):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        key = cleaned.lower()
        if key in _VISIT_TYPE_ALIASES:
            return _VISIT_TYPE_ALIASES[key]
    raise ValueError(
        f"Unsupported visit_type {value!r}; expected one of: ANC, PNC, Newborn, Immunisation."
    )


class ActionType(str, Enum):
    """Structured side-effect actions emitted by the state machine."""

    STATE_CHANGED = "state_changed"
    SPEAK = "speak"
    SPEAK_URGENT = "speak_urgent"
    DANGER_ALERT = "danger_alert"
    DRAFT_UPDATED = "draft_updated"
    CLARIFICATION_PROMPT = "clarification_prompt"
    READ_BACK_STARTED = "read_back_started"
    CORRECTION_APPLIED = "correction_applied"
    WORKER_CONFIRMED = "worker_confirmed"
    PERSISTENCE_REQUESTED = "persistence_requested"
    PERSISTENCE_REJECTED = "persistence_rejected"
    VISIT_COMMITTED = "visit_committed"


class ClarificationRequest(BaseModel):
    """Describes a missing or ambiguous field requiring worker clarification."""

    field: str
    reason: str = "missing"
    question: str | None = None
    candidates: list[str] = Field(default_factory=list)


class DangerAlertInput(BaseModel):
    """Protocol-compatible DTO passed from the deterministic danger-sign engine (1A)."""

    alert_id: str | None = None
    canonical_id: str
    category: str = ""
    display_name: str = ""
    matched_phrase: str = ""
    guideline_reference: str = ""
    severity: str = "critical"
    confidence: float = 1.0
    is_partial: bool = False
    escalation_message: str | None = None
    language: str | None = None

    @field_validator("canonical_id")
    @classmethod
    def _normalize_canonical_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("canonical_id must be non-empty")
        return cleaned.upper()


class DangerAlertRecord(BaseModel):
    """Immutable per-session danger alert record aligned with cross-agent contracts."""

    alert_id: str
    session_id: str
    visit_draft_id: str
    beneficiary_id: str | None = None
    canonical_id: str
    category: str = ""
    display_name: str = ""
    evidence: str = ""
    evidence_history: list[str] = Field(default_factory=list)
    guideline_reference: str = ""
    severity: str = "critical"
    detected_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    status: str = "active"
    acknowledged: bool = False
    escalation_language: str = "hi-IN"
    danger_sign_flagged: bool = True


class VisitRecordState(BaseModel):
    """Canonical structured visit record maintained across the voice workflow."""

    visit_draft_id: str = Field(
        default_factory=lambda: f"draft_{uuid.uuid4().hex[:12]}"
    )
    record_id: str | None = None
    beneficiary_id: str | None = None
    beneficiary_name: str | None = None
    visit_type: VisitType | None = None
    weight_kg: float | None = None
    vaccinations_completed: list[str] = Field(default_factory=list)
    vaccinations_due: list[str] = Field(default_factory=list)
    next_visit_date: str | None = None
    danger_signs: list[str] = Field(default_factory=list)
    danger_sign_flagged: bool = False
    follow_up_actions: list[str] = Field(default_factory=list)
    status: VisitStatus = VisitStatus.DRAFT
    updated_at: str = Field(default_factory=utc_now_iso)

    @field_validator("visit_type", mode="before")
    @classmethod
    def _validate_visit_type(cls, value: Any) -> VisitType | None:
        return coerce_visit_type(value)

    @field_validator("weight_kg")
    @classmethod
    def _validate_weight(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value <= 0 or value > 250:
            raise ValueError("weight_kg must be between 0 and 250 kg")
        return round(float(value), 2)

    def has_clinical_observation(self) -> bool:
        """Return True if at least one clinical observation or danger flag is recorded."""
        return (
            self.weight_kg is not None
            or len(self.vaccinations_due) > 0
            or len(self.vaccinations_completed) > 0
            or self.next_visit_date is not None
            or self.danger_sign_flagged
        )

    def to_contract_payload(self) -> dict[str, Any]:
        """Serialize canonical fields for WebSocket events and persistence handoff."""
        return self.model_dump(mode="json")


class ExtractionUpdate(BaseModel):
    """Protocol-compatible DTO passed from the healthcare extraction layer (1C)."""

    beneficiary_id: str | None = None
    beneficiary_name: str | None = None
    visit_type: VisitType | None = None
    weight_kg: float | None = None
    vaccinations_completed: list[str] | None = None
    vaccinations_due: list[str] | None = None
    next_visit_date: str | None = None
    follow_up_actions: list[str] | None = None
    clarifications: list[ClarificationRequest] = Field(default_factory=list)
    explicit_fields: set[str] | None = None
    clear_fields: set[str] = Field(default_factory=set)
    detected_language: str | None = None

    @field_validator("visit_type", mode="before")
    @classmethod
    def _validate_visit_type(cls, value: Any) -> VisitType | None:
        return coerce_visit_type(value)

    @field_validator("weight_kg")
    @classmethod
    def _validate_weight(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value <= 0 or value > 250:
            raise ValueError("weight_kg must be between 0 and 250 kg")
        return round(float(value), 2)

    def specified_fields(self) -> set[str]:
        """Return the set of visit fields present in this update/patch."""
        patchable = (
            "beneficiary_id",
            "beneficiary_name",
            "visit_type",
            "weight_kg",
            "vaccinations_completed",
            "vaccinations_due",
            "next_visit_date",
            "follow_up_actions",
        )
        if self.explicit_fields is not None:
            return {f for f in self.explicit_fields if f in patchable}
        return {f for f in patchable if getattr(self, f) is not None}


class StateMachineAction(BaseModel):
    """Typed action emitted by the state machine for orchestration/transport layers."""

    action_type: ActionType
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: str = "normal"


class TransitionResult(BaseModel):
    """Outcome of a state machine event or transition."""

    previous_state: ConversationState
    current_state: ConversationState
    spoken_text: str | None = None
    spoken_language: str
    is_urgent: bool = False
    interrupt_speech: bool = False
    actions: list[StateMachineAction] = Field(default_factory=list)
    visit_record: VisitRecordState
    danger_alerts: list[DangerAlertRecord] = Field(default_factory=list)
    pending_clarifications: list[ClarificationRequest] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
