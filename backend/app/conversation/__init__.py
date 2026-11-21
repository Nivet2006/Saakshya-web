"""Phase 2 Conversation State Machine, Read-Back & Confirmation package."""

from app.conversation.models import (
    SUPPORTED_LANGUAGES,
    ActionType,
    ClarificationRequest,
    ConversationState,
    DangerAlertInput,
    DangerAlertRecord,
    ExtractionUpdate,
    StateMachineAction,
    TransitionResult,
    VisitRecordState,
    VisitStatus,
    VisitType,
    normalize_language,
)
from app.conversation.state_machine import (
    ConversationStateMachine,
    InvalidTransitionError,
    classify_confirmation_intent,
    extract_fallback_correction_patch,
    generate_clarification_text,
    generate_read_back_text,
    generate_urgent_referral_text,
)

__all__ = [
    "ActionType",
    "ClarificationRequest",
    "ConversationState",
    "ConversationStateMachine",
    "DangerAlertInput",
    "DangerAlertRecord",
    "ExtractionUpdate",
    "InvalidTransitionError",
    "SUPPORTED_LANGUAGES",
    "StateMachineAction",
    "TransitionResult",
    "VisitRecordState",
    "VisitStatus",
    "VisitType",
    "classify_confirmation_intent",
    "extract_fallback_correction_patch",
    "generate_clarification_text",
    "generate_read_back_text",
    "generate_urgent_referral_text",
    "normalize_language",
]
