"""REST endpoints matching `shared-contracts/openapi.json` (v1)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.conversation.state_machine import InvalidTransitionError
from app.core.config import get_settings
from app.danger_signs.detector import detect_danger_signs, get_referral_message
from app.healthcare.pipeline import format_danger_alert_contract, session_registry
from app.services.beneficiaries import SyntheticBeneficiaryDirectory

router = APIRouter()
_directory = SyntheticBeneficiaryDirectory()


def _error_response(
    status_code: int, code: str, message: str, *, retryable: bool = False, detail: str | None = None
) -> JSONResponse:
    body: dict[str, Any] = {
        "schema_version": "v1",
        "code": code,
        "message": message,
        "retryable": retryable,
    }
    if detail is not None:
        body["detail"] = detail
    return JSONResponse(status_code=status_code, content=body)


class CreateSessionRequest(BaseModel):
    language: str = Field(
        default="indic-auto",
        description="Preferred BCP-47 language code (e.g. hi-IN, kn-IN, ta-IN, en-IN) or 'indic-auto'.",
    )
    beneficiary_id: str | None = Field(
        default=None,
        description="Optional synthetic beneficiary ID (e.g. BEN-1042).",
    )
    worker_id: str = Field(
        default="ASHA-DEMO-01",
        description="Synthetic ASHA worker identifier.",
    )


class CreateSessionResponse(BaseModel):
    schema_version: str = "v1"
    session_id: str
    websocket_path: str
    language: str
    beneficiary_id: str | None
    created_at: str
    audio_format: dict[str, Any]


class PersistenceAckRequest(BaseModel):
    schema_version: str = "v1"
    visit_id: str
    correlation_id: str | None = None
    accepted: bool
    persistence_record_id: str | None = None
    committed_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class DangerSignCheckRequest(BaseModel):
    schema_version: str = "v1"
    text: str = Field(min_length=1)
    language: str = Field(default="hi-IN")
    visit_type: str | None = None
    beneficiary_id: str | None = None
    subject_hint: str | None = None


@router.get("/health")
async def health_check() -> dict[str, Any]:
    settings = get_settings()
    missing = settings.validate_live_credentials()
    return {
        "status": "ok",
        "service": "asha-voice-backend",
        "schema_version": "v1",
        "stt_model": settings.gnani_stt_model,
        "tts_model": settings.gnani_tts_model,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.effective_llm_model,
        "live_credentials_configured": len(missing) == 0,
        "missing_env_vars": missing,
        "synthetic_data_only": settings.synthetic_data_only,
    }


@router.post("/api/v1/sessions", response_model=CreateSessionResponse)
async def create_session(req: CreateSessionRequest) -> Any:
    settings = get_settings()
    if req.beneficiary_id and _directory.get_by_id(req.beneficiary_id) is None:
        return _error_response(
            404,
            "BENEFICIARY_NOT_FOUND",
            f"Synthetic beneficiary '{req.beneficiary_id}' not found.",
            retryable=False,
        )

    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    session_registry.create_session(
        session_id=session_id,
        language=req.language,
        beneficiary_id=req.beneficiary_id,
        worker_id=req.worker_id,
        created_at=created_at,
    )

    return CreateSessionResponse(
        session_id=session_id,
        websocket_path=f"/ws/voice/{session_id}",
        language=req.language,
        beneficiary_id=req.beneficiary_id,
        created_at=created_at,
        audio_format={
            "encoding": "pcm_s16le",
            "sample_rate": settings.audio_sample_rate,
            "channels": 1,
            "frame_ms": 32,
        },
    )


@router.get("/api/v1/beneficiaries")
async def list_beneficiaries(q: str | None = None) -> dict[str, Any]:
    items = _directory.search_by_name(q) if q else _directory.list_all()
    return {
        "schema_version": "v1",
        "synthetic_data_only": True,
        "beneficiaries": [
            {
                "beneficiary_id": b.beneficiary_id,
                "full_name": b.full_name,
                "category": b.category,
                "village": b.village,
                "preferred_language": b.preferred_language,
            }
            for b in items
        ],
    }


@router.get("/api/v1/sessions/{session_id}/visit")
async def get_session_visit(session_id: str) -> Any:
    pipeline = session_registry.get_pipeline(session_id)
    if pipeline is None:
        return _error_response(
            404,
            "INVALID_STATE_TRANSITION",
            f"Session '{session_id}' not found.",
            retryable=False,
        )
    return {
        "schema_version": "v1",
        "session_id": session_id,
        "conversation_state": pipeline.sm.state.value,
        "visit": pipeline.current_visit_contract(),
        "danger_alerts": pipeline.current_alerts_contract(),
    }


@router.post("/api/v1/sessions/{session_id}/persistence-ack")
async def acknowledge_visit_persistence(session_id: str, req: PersistenceAckRequest) -> Any:
    pipeline = session_registry.get_pipeline(session_id)
    if pipeline is None:
        return _error_response(
            404,
            "INVALID_STATE_TRANSITION",
            f"Session '{session_id}' not found.",
            retryable=False,
        )
    try:
        result = await pipeline.handle_persistence_ack(
            accepted=req.accepted,
            persistence_record_id=req.persistence_record_id,
            committed_at=req.committed_at,
            error_code=req.error_code,
            error_message=req.error_message,
            emit_ws=True,
        )
    except InvalidTransitionError as exc:
        return _error_response(409, "INVALID_STATE_TRANSITION", str(exc), retryable=False)

    if not req.accepted:
        return _error_response(
            422,
            req.error_code or "PERSISTENCE_FAILED",
            req.error_message or "Persistence layer rejected visit record write.",
            retryable=True,
        )
    return result


@router.post("/api/v1/danger-signs/check")
async def check_danger_signs(req: DangerSignCheckRequest) -> dict[str, Any]:
    res = detect_danger_signs(
        req.text,
        language=req.language,
        context={
            "is_partial": False,
            "visit_type": req.visit_type,
            "subject": req.subject_hint,
        },
    )
    referral = res.referral_message or get_referral_message(req.language)
    alerts = [
        format_danger_alert_contract(
            alert_id=f"alrt_{uuid.uuid4().hex[:12]}",
            session_id="standalone_check",
            visit_id="standalone_visit",
            beneficiary_id=req.beneficiary_id,
            match=m,
            language=req.language,
            referral_message=referral,
        )
        for m in res.matches
    ]
    clar_prompt: str | None = None
    if res.uncertain_matches:
        phrases = ", ".join(m.matched_phrase for m in res.uncertain_matches)
        clar_prompt = (
            f"Uncertain symptom mentioned ({phrases}). "
            "Please clarify severity and whether it is currently ongoing."
        )
    return {
        "schema_version": "v1",
        "danger_sign_flagged": res.danger_sign_flagged,
        "requires_clarification": len(res.uncertain_matches) > 0,
        "clarification_prompt": clar_prompt,
        "alerts": alerts,
        "suppressed_matches": list(res.suppressed_context_matches),
    }


def get_session_metadata(session_id: str) -> dict[str, Any] | None:
    return session_registry.get_metadata(session_id)
