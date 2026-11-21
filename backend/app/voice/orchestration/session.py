"""Asyncio Voice Session Orchestrator.

Coordinates:
    Client audio -> ONNX Silero VAD (dual-gate barge-in) -> Gnani Prisma v3.0 STT
    -> [Phase 2 Danger-Sign / State Machine hook] -> LLM -> Gnani Timbre v3.0 TTS
    -> Client audio chunks (tagged with monotonic `turn_id`).

Zero-stale-audio barge-in guarantee:
- Every assistant turn is tagged with a monotonically increasing `turn_id`.
- On barge-in (VAD sustained speech during assistant TTS, client `barge_in`, or
  high-priority danger escalation), `active_turn_id` increments immediately, the
  in-flight LLM/TTS task is cancelled, `tts.cancel_active()` resets the upstream
  Timbre WebSocket, and `barge_in` + `tts_cancelled` events are emitted so the
  client flushes its local playback buffer immediately.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from app.conversation.models import detect_language_from_text
from app.core.logging import log_event, safe_text_preview
from app.core.telemetry import SessionTelemetryTracker, telemetry_registry
from app.voice.interfaces import (
    ChatMessage,
    LLMAdapter,
    StreamingSTTAdapter,
    StreamingTTSAdapter,
    TranscriptEvent,
    VADDetector,
)
from app.voice.llm.gemini_adapter import MILESTONE1_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

EmitCallback = Callable[[dict[str, Any]], Awaitable[None]]
TranscriptHook = Callable[[TranscriptEvent, "VoiceSessionOrchestrator"], Awaitable[bool]]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class VoiceSessionOrchestrator:
    """Manages one full-duplex, interruptible voice conversation session."""

    def __init__(
        self,
        *,
        session_id: str | None = None,
        stt: StreamingSTTAdapter,
        tts: StreamingTTSAdapter,
        llm: LLMAdapter,
        vad: VADDetector | None,
        emit: EmitCallback,
        default_language: str = "hi-IN",
        language_locked: bool = False,
        tts_voice: str = "Shivani",
        system_prompt: str = MILESTONE1_SYSTEM_PROMPT,
        on_partial_hook: TranscriptHook | None = None,
        on_final_hook: TranscriptHook | None = None,
        context_provider: Callable[[], str] | None = None,
    ) -> None:
        self.session_id = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        self._stt = stt
        self._tts = tts
        self._llm = llm
        self._vad = vad
        self._emit = emit
        self.active_language = default_language
        self.language_locked = language_locked
        self.tts_voice = tts_voice
        self._system_prompt = system_prompt
        self._on_partial_hook = on_partial_hook
        self._on_final_hook = on_final_hook
        self._context_provider = context_provider

        self.history: list[ChatMessage] = []
        self.active_turn_id: int = 0
        self.assistant_speaking: bool = False
        self.state: str = "idle"

        self._stt_loop_task: asyncio.Task[None] | None = None
        self._response_task: asyncio.Task[None] | None = None
        self._turn_lock = asyncio.Lock()
        self._closed = False
        self._pending_utterance_parts: list[str] = []
        self._debounce_task: asyncio.Task[None] | None = None
        self._turn_debounce_s: float = 0.06
        self.telemetry: SessionTelemetryTracker = telemetry_registry.get_or_create(self.session_id)
        self.audio_frames_received: int = 0
        self.audio_bytes_received: int = 0
        self.vad_clipped_samples: int = 0
        self.last_snr_db: float = 0.0
        # Bounded in-memory rolling PCM ring buffer (never persisted to disk) +
        # per-utterance byte ranges keyed by utterance_id for accurate secondary ASR.
        self._pcm_bytes_per_ms: int = (16000 * 2) // 1000  # 32 bytes/ms @ 16kHz mono s16le
        self._pcm_ring_max_bytes: int = 45 * 16000 * 2  # 45s rolling window
        self._pcm_ring: bytearray = bytearray()
        self._pcm_ring_start_offset: int = 0
        self._session_audio_bytes_total: int = 0
        self._last_final_offset: int = 0
        self._utterance_start_offsets: dict[str, int] = {}
        self._completed_utterance_pcm: dict[str, bytes] = {}
        self._active_local_utterance_start: int | None = None

    def _envelope(self, event_type: str, **payload: Any) -> dict[str, Any]:
        return {
            "schema_version": "v1",
            "type": event_type,
            "session_id": self.session_id,
            "timestamp": utc_now_iso(),
            **payload,
        }

    async def emit_event(self, event_type: str, **payload: Any) -> None:
        if self._closed and event_type not in ("session_state", "error"):
            return
        await self._emit(self._envelope(event_type, **payload))

    async def _set_state(self, new_state: str) -> None:
        if self.state == new_state:
            return
        self.state = new_state
        await self.emit_event("session_state", state=new_state, turn_id=self.active_turn_id)

    async def start(self) -> None:
        """Connect STT & TTS upstreams and start the STT event reader loop."""
        await asyncio.gather(self._stt.connect(), self._tts.connect())
        self._stt_loop_task = asyncio.create_task(
            self._stt_event_loop(), name=f"stt-loop-{self.session_id}"
        )
        await self.emit_event(
            "session_ready",
            language=self.active_language,
            audio_format={
                "encoding": "pcm_s16le",
                "sample_rate": self._tts.sample_rate,
                "channels": 1,
                "frame_ms": 32,
            },
            stt_provider=type(self._stt).__name__,
            tts_provider=type(self._tts).__name__,
            llm_provider=self._llm.provider_name,
            llm_model=self._llm.model_name,
        )
        await self._set_state("listening")

    async def handle_audio_chunk(self, pcm_bytes: bytes) -> None:
        """Process incoming 16kHz PCM_S16LE audio from client mic/WAV."""
        if self._closed or not pcm_bytes:
            return
        self.audio_frames_received += 1
        self.audio_bytes_received += len(pcm_bytes)

        chunk_start_offset = self._session_audio_bytes_total

        # Append incoming PCM to bounded timestamp-indexed rolling ring buffer BEFORE VAD/STT
        self._pcm_ring.extend(pcm_bytes)
        self._session_audio_bytes_total += len(pcm_bytes)
        if len(self._pcm_ring) > self._pcm_ring_max_bytes:
            excess = len(self._pcm_ring) - self._pcm_ring_max_bytes
            del self._pcm_ring[:excess]
            self._pcm_ring_start_offset += excess

        # 1. Local VAD + dual-gate barge-in detection while assistant is speaking
        if self._vad is not None:
            decision = self._vad.process_frame(
                pcm_bytes, assistant_speaking=self.assistant_speaking
            )
            self.vad_clipped_samples += decision.clipped_samples
            self.last_snr_db = decision.snr_db
            if decision.speech_started:
                self.telemetry.mark_speech_start()
                pre_roll_len = len(decision.pre_roll_pcm) if decision.pre_roll_pcm else 0
                self._active_local_utterance_start = max(
                    self._pcm_ring_start_offset, chunk_start_offset - pre_roll_len
                )
            if decision.speech_ended:
                self.telemetry.mark_speech_end()
            if decision.barge_in_triggered:
                await self.interrupt(trigger="vad")

        # 2. Stream audio continuously into Gnani Prisma v3.0
        try:
            await self._stt.send_audio(pcm_bytes)
        except Exception as exc:
            logger.error("session_stt_send_error session=%s err=%s", self.session_id, exc)
            await self.emit_event(
                "error",
                code="STT_STREAM_ERROR",
                message=f"Failed to stream audio to STT: {exc}",
                retryable=True,
            )

        if self.audio_frames_received == 1 or self.audio_frames_received % 25 == 0:
            import numpy as np
            arr = np.frombuffer(pcm_bytes, dtype=np.int16)
            rms_val = float(np.sqrt(np.mean(arr.astype(np.float32) ** 2))) if len(arr) > 0 else 0.0
            log_event(
                logger,
                "audio_frame_rx",
                session=self.session_id,
                frames=self.audio_frames_received,
                bytes=self.audio_bytes_received,
                rms=round(rms_val, 1),
                stt_connected=self._stt.is_connected,
            )
            await self.emit_event(
                "server_audio_stats",
                frames_received=self.audio_frames_received,
                bytes_received=self.audio_bytes_received,
                rms=round(rms_val, 1),
                stt_connected=self._stt.is_connected,
            )

    async def handle_text_input(self, text: str) -> None:
        """Accept direct text utterance (for testing/fallback) through the same pipeline."""
        cleaned = text.strip()
        if not cleaned or self._closed:
            return
        if self.assistant_speaking or (
            self._response_task is not None and not self._response_task.done()
        ):
            await self.interrupt(trigger="client")

        detected_lang = detect_language_from_text(cleaned, fallback=self.active_language)
        self.active_language = detected_lang
        ev = TranscriptEvent(
            event_type="final",
            text=cleaned,
            is_final=True,
            language_code=detected_lang,
            utterance_id=f"txt_{uuid.uuid4().hex[:8]}",
            latency_ms=0.0,
        )
        self.telemetry.mark_transcript_finalized(stt_latency_ms=0.0)
        await self.emit_event(
            "final_transcript",
            text=ev.text,
            language=ev.language_code,
            utterance_id=ev.utterance_id,
            is_final=True,
        )
        await self._handle_final_transcript(ev)

    async def interrupt(self, *, trigger: str = "client") -> int:
        """Cancel active assistant generation & TTS immediately so zero stale audio plays."""
        cancelled_turn = self.active_turn_id
        self.active_turn_id += 1
        was_active = self.assistant_speaking or (
            self._response_task is not None and not self._response_task.done()
        )
        self.assistant_speaking = False

        if self._debounce_task is not None and not self._debounce_task.done():
            self._debounce_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._debounce_task
            self._debounce_task = None

        if self._response_task is not None and not self._response_task.done():
            self._response_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._response_task
        self._response_task = None

        if was_active or trigger in ("client", "vad", "danger_sign"):
            self.telemetry.barge_in_count += 1
            log_event(
                logger,
                "barge_in",
                session=self.session_id,
                trigger=trigger,
                cancelled_turn=cancelled_turn,
                new_turn=self.active_turn_id,
            )
            await self.emit_event(
                "barge_in",
                cancelled_turn_id=cancelled_turn,
                new_turn_id=self.active_turn_id,
                trigger=trigger,
            )
            await self.emit_event(
                "tts_cancelled",
                cancelled_turn_id=cancelled_turn,
                reason=trigger,
            )

        await self._tts.cancel_active()

        if not self._closed:
            await self._set_state("listening")
        return self.active_turn_id

    async def speak_urgent(self, text: str, *, language: str | None = None) -> None:
        """Interrupt any current speech and immediately speak a high-priority message."""
        turn_id = await self.interrupt(trigger="danger_sign")
        lang = language or self.active_language
        self.telemetry.start_turn(turn_id, is_greeting=False)
        self.telemetry.mark_llm_first_token(turn_id)
        await self._set_state("danger_escalation")
        self._response_task = asyncio.create_task(
            self._speak_text_turn(
                turn_id=turn_id,
                reply_text=text,
                language=lang,
                is_danger_escalation=True,
            ),
            name=f"urgent-tts-{self.session_id}-{turn_id}",
        )

    async def speak_direct(
        self,
        text: str,
        *,
        language: str | None = None,
        is_greeting: bool = False,
    ) -> None:
        """Speak a pre-generated assistant reply (used by Phase 2 state machine)."""
        if self._response_task is not None and not self._response_task.done():
            await self.interrupt(trigger="supersede")
        self.active_turn_id += 1
        turn_id = self.active_turn_id
        lang = language or self.active_language
        self.telemetry.start_turn(turn_id, is_greeting=is_greeting)
        self.telemetry.mark_llm_first_token(turn_id)
        self.history.append(ChatMessage(role="assistant", content=text))
        self._response_task = asyncio.create_task(
            self._speak_text_turn(
                turn_id=turn_id,
                reply_text=text,
                language=lang,
                is_danger_escalation=False,
            ),
            name=f"direct-tts-{self.session_id}-{turn_id}",
        )

    async def close(self) -> None:
        """Cleanly cancel tasks and close upstream STT/TTS connections."""
        if self._closed:
            return
        self._closed = True
        self.active_turn_id += 1
        self.assistant_speaking = False

        for task in (self._debounce_task, self._response_task, self._stt_loop_task):
            if task is not None and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        await asyncio.gather(
            self._stt.close(),
            self._tts.close(),
            return_exceptions=True,
        )
        self._pcm_ring.clear()
        self._utterance_start_offsets.clear()
        self._completed_utterance_pcm.clear()
        self.state = "closed"
        log_event(logger, "session_closed", session=self.session_id)

    # -- Internal STT & Turn Processing -------------------------------------

    async def _stt_event_loop(self) -> None:
        try:
            async for event in self._stt.events():
                if self._closed:
                    break
                await self._dispatch_stt_event(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("stt_event_loop_error session=%s err=%s", self.session_id, exc)
            await self.emit_event(
                "error",
                code="STT_LOOP_ERROR",
                message=str(exc),
                retryable=True,
            )

    def _slice_pcm_ring(self, start_offset: int, end_offset: int) -> bytes:
        """Extract PCM bytes in [start_offset, end_offset] from the rolling ring buffer."""
        if not self._pcm_ring or end_offset <= start_offset:
            return b""
        ring_end = self._pcm_ring_start_offset + len(self._pcm_ring)
        clamped_start = max(self._pcm_ring_start_offset, start_offset)
        clamped_end = min(ring_end, end_offset)
        if clamped_end <= clamped_start:
            return b""
        rel_start = clamped_start - self._pcm_ring_start_offset
        rel_end = clamped_end - self._pcm_ring_start_offset
        return bytes(self._pcm_ring[rel_start:rel_end])

    async def _dispatch_stt_event(self, event: TranscriptEvent) -> None:
        if event.event_type == "connected":
            return

        if event.event_type == "speech_start":
            self.telemetry.mark_speech_start()
            uid = event.utterance_id or "_active"
            # Prefer local VAD start if within recent 2s; otherwise preserve 0.5s pre-roll
            default_start = max(
                self._pcm_ring_start_offset,
                self._session_audio_bytes_total - 16000,
            )
            if (
                self._vad is not None
                and self._active_local_utterance_start is not None
                and (self._session_audio_bytes_total - self._active_local_utterance_start) <= 64000
            ):
                start_off = self._active_local_utterance_start
            else:
                start_off = max(default_start, self._last_final_offset)
            self._utterance_start_offsets[uid] = start_off
            if len(self._utterance_start_offsets) > 12:
                oldest = next(iter(self._utterance_start_offsets))
                self._utterance_start_offsets.pop(oldest, None)
            await self.emit_event("speech_start", utterance_id=event.utterance_id)
            return

        if event.event_type == "speech_end":
            self.telemetry.mark_speech_end()
            uid = event.utterance_id or "_active"
            end_off = self._session_audio_bytes_total
            start_off = self._utterance_start_offsets.get(uid)
            if start_off is None:
                audio_ms = event.metadata.get("audio_ms")
                if isinstance(audio_ms, (int, float)) and audio_ms > 0:
                    start_off = max(
                        self._pcm_ring_start_offset,
                        end_off - int(audio_ms * self._pcm_bytes_per_ms) - 9600,
                    )
                else:
                    start_off = max(self._pcm_ring_start_offset, self._last_final_offset)
            sliced = self._slice_pcm_ring(start_off, end_off)
            if sliced:
                self._completed_utterance_pcm[uid] = sliced
                if len(self._completed_utterance_pcm) > 8:
                    oldest = next(iter(self._completed_utterance_pcm))
                    self._completed_utterance_pcm.pop(oldest, None)
            await self.emit_event("speech_end", utterance_id=event.utterance_id)
            return

        if event.event_type == "error":
            await self.emit_event(
                "error",
                code="STT_PROVIDER_ERROR",
                message=event.error_message or "Unknown STT error",
                retryable=True,
            )
            return

        if self.language_locked:
            # Keep the worker's explicitly selected response language across English/ASCII code-mix.
            # Only switch if the utterance contains a distinct Indic Unicode script.
            if event.text and any(0x0900 <= ord(ch) <= 0x0D7F for ch in event.text):
                detected = detect_language_from_text(event.text, fallback=self.active_language)
                if detected and detected != "en-IN":
                    self.active_language = detected
        else:
            if event.language_code and event.language_code not in ("auto", "indic-auto"):
                self.active_language = event.language_code
            if event.text:
                detected = detect_language_from_text(
                    event.text,
                    fallback=event.language_code or self.active_language,
                )
                if detected:
                    self.active_language = detected

        if event.event_type == "partial":
            self.telemetry.mark_speech_start()
            # If user is clearly speaking words while TTS is playing (even if local VAD missed it),
            # trigger barge-in when partial text has >= 2 words.
            if self.assistant_speaking and len(event.text.split()) >= 2:
                await self.interrupt(trigger="vad")

            await self.emit_event(
                "partial_transcript",
                text=event.text,
                stable_text=event.metadata.get("stable_text", ""),
                volatile_text=event.metadata.get("volatile_text", ""),
                language=(
                    self.active_language
                    if self.language_locked
                    else (event.language_code or self.active_language)
                ),
                utterance_id=event.utterance_id,
                seq=event.seq,
                is_final=False,
            )
            if self._on_partial_hook is not None:
                await self._on_partial_hook(event, self)
            return

        if event.event_type == "final":
            self.telemetry.mark_transcript_finalized(stt_latency_ms=event.latency_ms)
            uid = event.utterance_id or "_active"
            utterance_pcm = self._completed_utterance_pcm.pop(uid, None)
            start_off = self._utterance_start_offsets.pop(uid, None)
            if utterance_pcm is None:
                if uid != "_active":
                    utterance_pcm = self._completed_utterance_pcm.pop("_active", None)
                if start_off is None and uid != "_active":
                    start_off = self._utterance_start_offsets.pop("_active", None)
            end_off = self._session_audio_bytes_total
            if utterance_pcm is None:
                if start_off is not None:
                    utterance_pcm = self._slice_pcm_ring(start_off, end_off)
                elif isinstance(event.metadata.get("audio_duration_ms"), (int, float)):
                    dur_ms = float(event.metadata["audio_duration_ms"])
                    dur_start = max(
                        self._pcm_ring_start_offset,
                        end_off - int(dur_ms * self._pcm_bytes_per_ms) - 9600,
                    )
                    utterance_pcm = self._slice_pcm_ring(dur_start, end_off)
                elif self._active_local_utterance_start is not None:
                    utterance_pcm = self._slice_pcm_ring(self._active_local_utterance_start, end_off)
                else:
                    utterance_pcm = self._slice_pcm_ring(self._last_final_offset, end_off)
            self._last_final_offset = end_off
            self._active_local_utterance_start = None
            if utterance_pcm:
                event.metadata.setdefault("utterance_pcm", utterance_pcm)
                event.metadata.setdefault("sample_rate", self._tts.sample_rate)
            append_ctx = getattr(self._stt, "append_previous_context", None)
            if callable(append_ctx) and event.text:
                append_ctx(event.text)
            await self.emit_event(
                "final_transcript",
                text=event.text,
                language=(
                    self.active_language
                    if self.language_locked
                    else (event.language_code or self.active_language)
                ),
                utterance_id=event.utterance_id,
                segment_id=event.segment_id,
                latency_ms=event.latency_ms,
                is_final=True,
            )
            await self._handle_final_transcript(event)

    async def _handle_final_transcript(self, event: TranscriptEvent) -> None:
        # Phase 2 hook (e.g. Danger-Sign + State Machine) can intercept and handle the turn
        if self._on_final_hook is not None:
            handled = await self._on_final_hook(event, self)
            if handled:
                return

        # Coalesce rapid back-to-back final segments (e.g. brief mid-sentence pause)
        self._pending_utterance_parts.append(event.text)
        if self._debounce_task is not None and not self._debounce_task.done():
            self._debounce_task.cancel()
        self._debounce_task = asyncio.create_task(
            self._flush_pending_utterance(), name=f"debounce-{self.session_id}"
        )

    async def _flush_pending_utterance(self) -> None:
        try:
            await asyncio.sleep(self._turn_debounce_s)
        except asyncio.CancelledError:
            return

        combined = " ".join(self._pending_utterance_parts).strip()
        self._pending_utterance_parts.clear()
        if not combined or self._closed:
            return

        # Cancel any stale in-flight response before starting the new turn
        if self._response_task is not None and not self._response_task.done():
            await self.interrupt(trigger="vad")

        self.active_turn_id += 1
        turn_id = self.active_turn_id
        self.telemetry.start_turn(turn_id, is_greeting=False)
        self.history.append(ChatMessage(role="user", content=combined))
        # Keep conversation window bounded for low-latency LLM turns
        if len(self.history) > 16:
            self.history = self.history[-16:]

        self._response_task = asyncio.create_task(
            self._run_llm_and_tts_turn(turn_id=turn_id, language=self.active_language),
            name=f"turn-{self.session_id}-{turn_id}",
        )

    async def _run_llm_and_tts_turn(self, *, turn_id: int, language: str) -> None:
        try:
            await self._set_state("processing")
            prompt = self._system_prompt
            if callable(self._context_provider):
                extra_ctx = (self._context_provider() or "").strip()
                if extra_ctx:
                    prompt = f"{self._system_prompt}\n\n{extra_ctx}"
            reply_text = await self._llm.generate_reply(
                list(self.history),
                system_prompt=prompt,
                active_language=language,
            )
            if turn_id != self.active_turn_id or self._closed:
                return

            self.telemetry.mark_llm_first_token(turn_id)
            self.history.append(ChatMessage(role="assistant", content=reply_text))
            await self._speak_text_turn(
                turn_id=turn_id,
                reply_text=reply_text,
                language=language,
                is_danger_escalation=False,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("turn_error session=%s turn=%s err=%s", self.session_id, turn_id, exc)
            await self.emit_event(
                "error",
                code="TURN_PROCESSING_ERROR",
                message=f"Could not complete voice turn: {exc}",
                retryable=True,
            )
            if turn_id == self.active_turn_id and not self._closed:
                await self._set_state("listening")

    async def _speak_text_turn(
        self,
        *,
        turn_id: int,
        reply_text: str,
        language: str,
        is_danger_escalation: bool,
    ) -> None:
        if turn_id != self.active_turn_id or self._closed:
            return

        await self.emit_event(
            "assistant_response",
            turn_id=turn_id,
            text=reply_text,
            language=language,
            is_danger_escalation=is_danger_escalation,
        )
        await self.emit_event(
            "tts_start",
            turn_id=turn_id,
            sample_rate=self._tts.sample_rate,
            encoding="pcm_s16le",
            channels=1,
        )

        self.assistant_speaking = True
        if not is_danger_escalation:
            await self._set_state("speaking")

        seq = 0
        total_bytes = 0
        try:
            async for pcm_chunk in self._tts.synthesize_stream(
                reply_text,
                language=language,
                voice=self.tts_voice,
            ):
                if turn_id != self.active_turn_id or self._closed:
                    break
                seq += 1
                if seq == 1:
                    self.telemetry.mark_tts_first_chunk(turn_id)
                total_bytes += len(pcm_chunk)
                await self.emit_event(
                    "tts_audio_chunk",
                    turn_id=turn_id,
                    seq=seq,
                    audio_base64=base64.b64encode(pcm_chunk).decode("ascii"),
                    sample_rate=self._tts.sample_rate,
                )

            if turn_id == self.active_turn_id and not self._closed:
                await self.emit_event(
                    "tts_complete",
                    turn_id=turn_id,
                    total_chunks=seq,
                    total_bytes=total_bytes,
                )
        except asyncio.CancelledError:
            log_event(
                logger,
                "tts_turn_cancelled",
                session=self.session_id,
                turn=turn_id,
                chunks_sent=seq,
                preview=safe_text_preview(reply_text),
            )
            raise
        finally:
            if turn_id == self.active_turn_id:
                self.assistant_speaking = False
                if not self._closed:
                    await self._set_state("listening")

