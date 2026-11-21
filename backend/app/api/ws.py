"""Full-duplex WebSocket endpoint `/ws/voice/{session_id}` with Phase 2 Healthcare Pipeline."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.routes import get_session_metadata
from app.conversation.state_machine import InvalidTransitionError
from app.core.config import build_contextual_stt_options, get_settings
from app.core.logging import log_event
from app.extraction.secondary_recognition import GnaniRestSecondaryRecognizer
from app.healthcare.pipeline import session_registry
from app.services.beneficiaries import SyntheticBeneficiaryDirectory
from app.voice.llm.gemini_adapter import build_llm_adapter
from app.voice.orchestration.session import VoiceSessionOrchestrator
from app.voice.stt.gnani_prisma import GnaniPrismaSTTAdapter
from app.voice.tts.gnani_timbre import GnaniTimbreTTSAdapter
from app.voice.vad.silero_onnx import SileroOnnxVAD

logger = logging.getLogger(__name__)
ws_router = APIRouter()


@ws_router.websocket("/ws/voice/{session_id}")
async def voice_session_ws(
    websocket: WebSocket,
    session_id: str,
    language: str | None = None,
    disable_vad: bool = False,
    mode: str = "healthcare",
    greet: bool = False,
) -> None:
    """Real-time full-duplex audio + structured event WebSocket for a voice session.

    Query params:
    - `language`: BCP-47 code or `indic-auto` (default)
    - `disable_vad`: disable local ONNX Silero VAD (default False)
    - `mode`: `healthcare` (full 1A+1B+1C pipeline, default) or `voice_only` (Milestone 1 LLM loop)
    """
    await websocket.accept()
    settings = get_settings()
    missing = settings.validate_live_credentials()
    if missing:
        await websocket.send_json(
            {
                "schema_version": "v1",
                "type": "error",
                "session_id": session_id,
                "code": "MISSING_CREDENTIALS",
                "message": f"Missing required environment variables: {', '.join(missing)}",
                "retryable": False,
            }
        )
        await websocket.close(code=1011)
        return

    meta = get_session_metadata(session_id) or {}
    stt_lang = language or meta.get("language") or "indic-auto"
    ben_id = meta.get("beneficiary_id")
    ben_obj = SyntheticBeneficiaryDirectory().get_by_id(ben_id) if ben_id else None

    if stt_lang != "indic-auto":
        tts_default_lang = stt_lang
    elif ben_obj and ben_obj.preferred_language:
        tts_default_lang = ben_obj.preferred_language
    else:
        tts_default_lang = settings.default_language

    send_lock = asyncio.Lock()

    async def safe_emit(payload: dict[str, Any]) -> None:
        async with send_lock:
            try:
                await websocket.send_json(payload)
            except Exception:
                pass

    stt_ctx = build_contextual_stt_options(
        beneficiary_name=ben_obj.full_name if ben_obj else None,
        beneficiary_id=ben_obj.beneficiary_id if ben_obj else ben_id,
    )

    stt = GnaniPrismaSTTAdapter.from_settings(
        settings,
        language_code=stt_lang,
        keywords=stt_ctx["keywords"],
        speaker_names=stt_ctx["speaker_names"],
        previous_text=stt_ctx["previous_text"],
        topic=stt_ctx["topic"],
    )
    tts = GnaniTimbreTTSAdapter.from_settings(settings)
    llm = build_llm_adapter(settings)
    secondary_recognizer = (
        GnaniRestSecondaryRecognizer(
            api_key=settings.gnani_api_key.get_secret_value(),
            secondary_format=settings.gnani_stt_secondary_format,
            model=settings.gnani_stt_model or "prisma-v3.0",
        )
        if settings.gnani_stt_secondary_enabled and settings.gnani_api_key.get_secret_value().strip()
        else None
    )
    vad = (
        None
        if disable_vad
        else SileroOnnxVAD(
            sample_rate=settings.audio_sample_rate,
            speech_threshold=settings.vad_threshold,
            barge_in_threshold=settings.barge_in_vad_threshold,
            barge_in_min_speech_ms=settings.barge_in_min_speech_ms,
        )
    )

    pipeline = (
        session_registry.get_or_create_pipeline(
            session_id,
            language=tts_default_lang,
            beneficiary_id=meta.get("beneficiary_id"),
            worker_id=meta.get("worker_id", "ASHA-DEMO-01"),
        )
        if mode != "voice_only"
        else None
    )
    if pipeline is not None:
        pipeline.set_preferred_language(stt_lang, fallback=tts_default_lang)
        if secondary_recognizer is not None:
            pipeline.set_secondary_recognizer(secondary_recognizer)
        pipeline.confirm_important_numbers = settings.mandatory_numeric_confirmation

    orchestrator = VoiceSessionOrchestrator(
        session_id=session_id,
        stt=stt,
        tts=tts,
        llm=llm,
        vad=vad,
        emit=safe_emit,
        default_language=tts_default_lang,
        language_locked=(stt_lang != "indic-auto"),
        tts_voice=settings.gnani_tts_voice,
        on_partial_hook=pipeline.on_partial_transcript if pipeline else None,
        on_final_hook=pipeline.on_final_transcript if pipeline else None,
    )
    if pipeline is not None:
        pipeline.attach_orchestrator(orchestrator)

    try:
        log_event(
            logger,
            "ws_session_accepted",
            session=session_id,
            stt_lang=stt_lang,
            mode=mode,
        )
        await orchestrator.start()
        if greet and pipeline is not None:
            await pipeline.start_session_greeting(orchestrator)

        while True:
            message = await websocket.receive()
            msg_type = message.get("type")
            if msg_type == "websocket.disconnect":
                break

            raw_bytes = message.get("bytes")
            if raw_bytes is not None:
                await orchestrator.handle_audio_chunk(raw_bytes)
                continue

            raw_text = message.get("text")
            if raw_text is None:
                continue

            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                await safe_emit(
                    {
                        "schema_version": "v1",
                        "type": "error",
                        "session_id": session_id,
                        "code": "INVALID_JSON",
                        "message": "Client sent malformed JSON frame.",
                        "retryable": True,
                    }
                )
                continue

            ev_type = str(data.get("type", "")).lower()
            if ev_type == "audio_chunk":
                b64 = data.get("audio_base64", "")
                if b64:
                    await orchestrator.handle_audio_chunk(base64.b64decode(b64))
            elif ev_type == "barge_in":
                await orchestrator.interrupt(trigger=str(data.get("reason", "client")))
                if pipeline is not None:
                    pipeline.sm.handle_barge_in()
            elif ev_type == "text_input":
                await orchestrator.handle_text_input(str(data.get("text", "")))
            elif ev_type == "set_language":
                new_lang = str(data.get("language", "")).strip()
                if new_lang:
                    is_auto = new_lang == "indic-auto"
                    eff_lang = settings.default_language if is_auto else new_lang
                    orchestrator.active_language = eff_lang
                    orchestrator.language_locked = not is_auto
                    if pipeline is not None:
                        pipeline.set_preferred_language(new_lang, fallback=eff_lang)
                    try:
                        await stt.update_stream_settings(language_code=new_lang)
                    except Exception as exc:
                        logger.warning("stt_set_language_failed err=%s", exc)
            elif ev_type == "confirm_visit" and pipeline is not None:
                await pipeline.handle_explicit_confirm_command(
                    bool(data.get("confirmed", False)), orchestrator
                )
            elif ev_type == "patch_fields" and pipeline is not None:
                fields = data.get("fields")
                if isinstance(fields, dict):
                    await pipeline.handle_visual_patch(fields, orchestrator)
            elif ev_type == "remove_observation" and pipeline is not None:
                key = str(data.get("key", "")).strip()
                if key:
                    await pipeline.handle_remove_item(observation_key=key, orchestrator=orchestrator)
            elif ev_type == "remove_event" and pipeline is not None:
                name = str(data.get("name", "")).strip()
                if name:
                    await pipeline.handle_remove_item(event_name=name, orchestrator=orchestrator)
            elif ev_type in ("finish_notes", "request_review") and pipeline is not None:
                await pipeline.handle_finish_review_command(orchestrator)
            elif ev_type == "silence_timeout" and pipeline is not None:
                await pipeline.handle_silence_timeout(orchestrator)
            elif ev_type == "persistence_ack" and pipeline is not None:
                try:
                    await pipeline.handle_persistence_ack(
                        accepted=bool(data.get("accepted", False)),
                        persistence_record_id=data.get("persistence_record_id"),
                        committed_at=data.get("committed_at"),
                        error_code=data.get("error_code"),
                        error_message=data.get("error_message"),
                        emit_ws=True,
                    )
                except InvalidTransitionError as exc:
                    await orchestrator.emit_event(
                        "error",
                        code="INVALID_STATE_TRANSITION",
                        message=str(exc),
                        retryable=False,
                    )
            elif ev_type == "ping":
                await orchestrator.emit_event("pong")
            elif ev_type == "end_session":
                break

    except WebSocketDisconnect:
        log_event(logger, "ws_client_disconnected", session=session_id)
    except Exception as exc:
        logger.exception("ws_session_unhandled_error session=%s", session_id)
        await safe_emit(
            {
                "schema_version": "v1",
                "type": "error",
                "session_id": session_id,
                "code": "SESSION_INTERNAL_ERROR",
                "message": str(exc),
                "retryable": True,
            }
        )
    finally:
        await orchestrator.close()
