"""Pydantic v2 data models for the deterministic danger-sign engine.

All canonical danger signs and thresholds are grounded strictly in
``docs/DANGER_SIGN_GUIDELINES.md`` (NHM / MoHFW / NHSRC official guidance).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SubjectType = Literal["mother", "newborn", "infant"]
CategoryType = Literal["ANC", "Intranatal", "PNC", "Newborn"]
MatchType = Literal["exact", "alias", "normalized", "fuzzy", "threshold"]


class DangerMatch(BaseModel):
    """A single verified or uncertain danger-sign match."""

    model_config = ConfigDict(extra="forbid")

    canonical_id: str
    canonical_name: str
    subject: SubjectType
    category: CategoryType
    matched_phrase: str
    evidence_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    match_type: MatchType
    source_doc: str
    source_section: str
    requires_clarification: bool = False


class DetectionResult(BaseModel):
    """Structured output of deterministic danger-sign detection."""

    model_config = ConfigDict(extra="forbid")

    danger_sign_flagged: bool
    escalation_required: bool
    matches: list[DangerMatch] = Field(default_factory=list)
    uncertain_matches: list[DangerMatch] = Field(default_factory=list)
    suppressed_context_matches: list[dict[str, str]] = Field(default_factory=list)
    active_language: str = "hi-IN"
    referral_message: str | None = None
    is_partial: bool = False


class DangerSignEntry(BaseModel):
    """Immutable catalog specification for an officially cited danger sign."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    canonical_id: str
    canonical_name: str
    subject: SubjectType
    category: CategoryType
    source_doc: str
    source_section: str
    exact_phrases: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    fuzzy_targets: tuple[str, ...] = ()
    uncertain_phrases: tuple[str, ...] = ()
    intrinsic_negative_phrases: tuple[str, ...] = ()
    # Catastrophic signs (e.g., vaginal bleeding in pregnancy, convulsions,
    # apnea/no cry, chest indrawing) cannot be downgraded by mild/hedging cues.
    allow_hedge_downgrade: bool = False
    # Optional semantic group used to disambiguate mother vs newborn / ANC vs PNC
    # when the same symptom occurs across phases (e.g., bleeding, convulsions, fever).
    disambiguation_group: str | None = None
