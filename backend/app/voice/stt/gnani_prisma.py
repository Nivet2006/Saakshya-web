"""Live Gnani Prisma v3.0 Realtime Streaming STT WebSocket adapter.

Verified against `wss://api.vachana.ai/stt/v3/stream` (2026-11-21):
- Auth header: `x-api-key-id`
- Model header: `x-model: prisma-v3.0`
- Language headers: `lang_code: indic-auto` (or BCP-47) + `x-language-candidates`
- Output style: `x-format: codemix` (preserves English medical terms in Latin script)
- Partials: `x-partials: true` -> emits `partial_transcript` + `final_transcript`
- Keywords: `x-keywords` (ASCII-escaped JSON array, <= 200 items)
- Audio input: raw binary PCM_S16LE mono frames (512 samples = 1024 bytes @ 16kHz)
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from collections.abc import AsyncIterator, Sequence
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from app.core.config import ASHA_DOMAIN_KEYWORDS, DEFAULT_GNANI_STT_WS_URL, Settings
from app.core.logging import log_event, safe_text_preview
from app.voice.interfaces import TranscriptEvent

logger = logging.getLogger(__name__)


class GnaniPrismaSTTAdapter:
    """Async WebSocket client for Gnani Prisma v3.0 streaming STT."""

    def __init__(
        self,
        *,
        api_key: str,
        ws_url: str = DEFAULT_GNANI_STT_WS_URL,
        model: str = "prisma-v3.0",
        language_code: str = "indic-auto",
        language_candidates: Sequence[str] | None = None,
        output_format: str = "codemix",
        sample_rate: int = 16000,
        enable_partials: bool = True,
        keywords: Sequence[str] | None = ASHA_DOMAIN_KEYWORDS,
        vad_threshold: float | None = None,
        min_silence_ms: int | None = None,
        min_speech_ms: int | None = None,
        idle_timeout_sec: int = 180,
        open_timeout: float = 20.0,
    ) -> None:
        if not api_key:
            raise ValueError("GNANI_API_KEY is required for GnaniPrismaSTTAdapter")
        self._api_key = api_key
        self._ws_url = ws_url or DEFAULT_GNANI_STT_WS_URL
        self._model = model or "prisma-v3.0"
        self._language_code = language_code
        self._language_candidates = list(language_candidates or [])
        self._output_format = output_format
        self._sample_rate = sample_rate
        self._enable_partials = enable_partials
        self._keywords = list(keywords or [])[:200]
        self._vad_threshold = vad_threshold
        self._min_silence_ms = min_silence_ms
        self._min_speech_ms = min_speech_ms
        self._idle_timeout_sec = idle_timeout_sec
        self._open_timeout = open_timeout

        self._ws: Any = None
        self._recv_task: asyncio.Task[None] | None = None
        self._events: asyncio.Queue[TranscriptEvent | None] = asyncio.Queue()
        self._closed = False
        self._connect_lock = asyncio.Lock()
        self._request_id: str = ""
        self._connected_config: dict[str, Any] = {}

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        language_code: str | None = None,
    ) -> GnaniPrismaSTTAdapter:
        """Build an adapter from root `.env` Settings."""
        lang = language_code or "indic-auto"
        candidates = settings.prisma_language_candidates if lang == "indic-auto" else None
        return cls(
            api_key=settings.gnani_api_key.get_secret_value(),
            ws_url=settings.effective_stt_ws_url,
            model=settings.gnani_stt_model or "prisma-v3.0",
            language_code=lang,
            language_candidates=candidates,
            output_format=settings.gnani_stt_format or "codemix",
            sample_rate=settings.audio_sample_rate,
            enable_partials=settings.gnani_stt_enable_partials,
            min_silence_ms=min(max(settings.endpoint_silence_ms, 100), 2000),
        )

    @property
    def is_connected(self) -> bool:
        if self._ws is None:
            return False
        state = getattr(self._ws, "state", None)
        state_name = getattr(state, "name", None)
        if isinstance(state_name, str):
            return state_name.upper() == "OPEN"
        return not bool(getattr(self._ws, "closed", False))

    @property
    def connected_config(self) -> dict[str, Any]:
        return dict(self._connected_config)

    def build_headers(self, request_id: str) -> dict[str, str]:
        """Construct verified Prisma v3.0 WebSocket upgrade headers."""
        headers: dict[str, str] = {
            "x-api-key-id": self._api_key,
            "x-model": self._model,
            "lang_code": self._language_code,
            "x-sample-rate": str(self._sample_rate),
            "x-api-request-id": request_id,
        }
        if self._output_format:
            headers["x-format"] = self._output_format
        if self._enable_partials:
            headers["x-partials"] = "true"
        if self._language_code == "indic-auto" and len(self._language_candidates) >= 2:
            headers["x-language-candidates"] = ",".join(self._language_candidates[:4])
        if self._keywords and self._model.lower() == "prisma-v3.0":
            headers["x-keywords"] = json.dumps(self._keywords, ensure_ascii=True)
        if self._vad_threshold is not None:
            headers["x-vad-threshold"] = str(self._vad_threshold)
        if self._min_silence_ms is not None:
            headers["x-min-silence-ms"] = str(self._min_silence_ms)
        if self._min_speech_ms is not None:
            headers["x-min-speech-ms"] = str(self._min_speech_ms)
        if self._idle_timeout_sec is not None:
            headers["x-idle-timeout-sec"] = str(self._idle_timeout_sec)
        return headers

    async def connect(self) -> None:
        """Open the Prisma v3.0 WebSocket and await the `connected` handshake event."""
        async with self._connect_lock:
            if self.is_connected:
                return
            self._closed = False
            self._request_id = f"asha_stt_{uuid.uuid4().hex[:12]}"
            headers = self.build_headers(self._request_id)

            ws = await websockets.connect(
                self._ws_url,
                additional_headers=headers,
                open_timeout=self._open_timeout,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
            )
            try:
                first_raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
            except Exception:
                await ws.close()
                raise

            first_event = self._parse_message(first_raw)
            if first_event is None or first_event.event_type == "error":
                await ws.close()
                err = first_event.error_message if first_event else "Unexpected handshake"
                raise ConnectionError(f"Gnani Prisma handshake failed: {err}")

            self._ws = ws
            self._connected_config = first_event.metadata.get("config", {})
            log_event(
                logger,
                "stt_connected",
                request_id=self._request_id,
                model=self._model,
                partials=self._connected_config.get("partials_enabled", False),
                lang=self._language_code,
            )
            await self._events.put(first_event)
            self._recv_task = asyncio.create_task(
                self._receive_loop(ws),
                name=f"gnani-prisma-recv-{self._request_id}",
            )

    async def send_audio(self, pcm_chunk: bytes) -> None:
        """Send raw PCM_S16LE audio chunk; auto-reconnect once if socket dropped."""
        if self._closed or not pcm_chunk:
            return
        if not self.is_connected:
            await self.connect()
        ws = self._ws
        if ws is None:
            return
        try:
            await ws.send(pcm_chunk)
        except ConnectionClosed:
            if self._closed:
                return
            logger.warning("stt_send_reconnect request_id=%s", self._request_id)
            await self._close_socket_only()
            await self.connect()
            if self._ws is not None:
                await self._ws.send(pcm_chunk)

    async def events(self) -> AsyncIterator[TranscriptEvent]:
        """Yield normalized TranscriptEvents until the adapter is closed."""
        while True:
            event = await self._events.get()
            if event is None:
                break
            yield event

    async def close(self) -> None:
        """Gracefully shut down the WebSocket and signal the event iterator to finish."""
        self._closed = True
        await self._close_socket_only()
        await self._events.put(None)

    async def _close_socket_only(self) -> None:
        if self._recv_task is not None and not self._recv_task.done():
            self._recv_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._recv_task
        self._recv_task = None
        if self._ws is not None:
            with contextlib.suppress(Exception):
                await self._ws.close()
            self._ws = None

    async def _receive_loop(self, ws: Any) -> None:
        try:
            async for raw_msg in ws:
                if isinstance(raw_msg, bytes):
                    continue
                event = self._parse_message(raw_msg)
                if event is not None:
                    await self._events.put(event)
        except asyncio.CancelledError:
            raise
        except ConnectionClosed as exc:
            if not self._closed:
                logger.warning(
                    "stt_ws_closed request_id=%s code=%s",
                    self._request_id,
                    getattr(exc, "code", None),
                )
        except Exception as exc:
            if not self._closed:
                logger.error("stt_recv_error request_id=%s err=%s", self._request_id, exc)
                await self._events.put(
                    TranscriptEvent(event_type="error", error_message=str(exc))
                )
        finally:
            if self._ws is ws:
                self._ws = None
            with contextlib.suppress(Exception):
                await ws.close()

    def _parse_message(self, raw_msg: str | bytes) -> TranscriptEvent | None:
        if isinstance(raw_msg, bytes):
            return None
        try:
            payload: dict[str, Any] = json.loads(raw_msg)
        except json.JSONDecodeError as exc:
            return TranscriptEvent(event_type="error", error_message=f"Invalid JSON: {exc}")

        msg_type = str(payload.get("type", "")).lower()

        if msg_type == "connected":
            return TranscriptEvent(
                event_type="connected",
                metadata={
                    "message": payload.get("message", ""),
                    "config": payload.get("config", {}),
                    "request_id": payload.get("request_id", self._request_id),
                },
            )

        if msg_type in ("speech_start", "vad_start"):
            return TranscriptEvent(
                event_type="speech_start",
                utterance_id=payload.get("utterance_id"),
                metadata={"t_ms": payload.get("t_ms")},
            )

        if msg_type in ("speech_end", "vad_end"):
            return TranscriptEvent(
                event_type="speech_end",
                utterance_id=payload.get("utterance_id"),
                metadata={"audio_ms": payload.get("audio_ms"), "t_ms": payload.get("t_ms")},
            )

        if msg_type == "partial_transcript":
            text = str(payload.get("text", "")).strip()
            if not text:
                return None
            return TranscriptEvent(
                event_type="partial",
                text=text,
                is_final=False,
                language_code=payload.get("detected_language_code"),
                utterance_id=payload.get("utterance_id"),
                seq=payload.get("seq"),
                metadata={
                    "stable_text": payload.get("stable_text", ""),
                    "volatile_text": payload.get("volatile_text", ""),
                },
            )

        if msg_type in ("final_transcript", "transcript"):
            text = str(payload.get("text", "")).strip()
            if not text:
                return None
            is_final = bool(payload.get("is_final", True))
            log_event(
                logger,
                "stt_transcript",
                final=is_final,
                lang=payload.get("detected_language_code"),
                latency_ms=payload.get("latency"),
                preview=safe_text_preview(text),
            )
            return TranscriptEvent(
                event_type="final" if is_final else "partial",
                text=text,
                is_final=is_final,
                language_code=payload.get("detected_language_code"),
                utterance_id=payload.get("utterance_id"),
                segment_id=payload.get("segment_id"),
                latency_ms=payload.get("latency"),
                metadata={
                    "audio_duration_ms": payload.get("audio_duration_ms"),
                    "segment_index": payload.get("segment_index"),
                },
            )

        if msg_type == "error":
            return TranscriptEvent(
                event_type="error",
                error_message=str(payload.get("message", "Unknown Gnani STT error")),
            )

        # Ignore informational `processing` or `settings_updated` notifications
        return None

