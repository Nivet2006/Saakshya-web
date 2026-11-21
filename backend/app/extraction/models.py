"""Typed Pydantic v2 models for ASHA home-visit field extraction and validation."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

VisitType = Literal["ANC", "PNC", "Newborn", "Immunisation"]
FollowUpActionType = Literal[
    "vaccination",
    "ifa_adherence",
    "weight_monitoring",
    "danger_referral",
    "routine_visit",
    "other",
]
FollowUpPriority = Literal["normal", "high", "urgent"]
VisitStatus = Literal["draft", "confirmed", "committed"]


def _validate_iso_date(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) != 10:
        raise ValueError(f"Expected ISO-8601 YYYY-MM-DD date, got {value!r}")
    date.fromisoformat(value)
    return value


class FollowUpAction(BaseModel):
    """Grounded follow-up action derived from explicit utterance evidence."""

    action_type: FollowUpActionType
    description: str
    due_date: str | None = None
    priority: FollowUpPriority = "normal"
    source_phrase: str | None = None

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, value: str | None) -> str | None:
        return _validate_iso_date(value)


class FieldClarification(BaseModel):
    """Clarification request emitted whenever an extracted value is ambiguous or implausible."""

    field_name: str
    reason: str
    prompt_hint: str
    candidates: list[str] = Field(default_factory=list)


class VisitDraft(BaseModel):
    """Structured draft record for a single ASHA home visit."""

    visit_id: str
    beneficiary_id: str | None = None
    beneficiary_name: str | None = None
    visit_type: VisitType | None = None
    weight_kg: float | None = None
    weight_source_text: str | None = None
    vaccinations_completed: list[str] = Field(default_factory=list)
    vaccinations_due: list[str] = Field(default_factory=list)
    next_visit_date: str | None = None
    next_visit_date_source_text: str | None = None
    danger_signs: list[str] = Field(default_factory=list)
    danger_sign_flagged: bool = False
    follow_up_actions: list[FollowUpAction] = Field(default_factory=list)
    status: VisitStatus = "draft"
    confirmed_fields: list[str] = Field(default_factory=list)
    clarifications_needed: list[FieldClarification] = Field(default_factory=list)

    @field_validator("next_visit_date")
    @classmethod
    def validate_next_visit_date(cls, value: str | None) -> str | None:
        return _validate_iso_date(value)

    @field_validator("weight_kg")
    @classmethod
    def validate_weight_kg(cls, value: float | None) -> float | None:
        if value is not None and value <= 0:
            raise ValueError("weight_kg must be positive when provided")
        return value


class ExtractionResult(BaseModel):
    """Incremental extraction patch from a single worker utterance."""

    patch: dict[str, Any] = Field(default_factory=dict)
    clarifications: list[FieldClarification] = Field(default_factory=list)
    detected_correction: bool = False
    corrected_fields: list[str] = Field(default_factory=list)
    provenance: dict[str, str] = Field(default_factory=dict)
