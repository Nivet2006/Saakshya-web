"""Live Gnani Timbre v3.0 Interruptible Realtime WebSocket TTS adapter.

Verified against `wss://api.vachana.ai/api/v1/tts` (2026-11-21):
- Auth header: `X-API-Key-ID`
- Model: `timbre-v3.0`, Voice: `Shivani` (multilingual across all 10 Indian languages + English)
- Output: 16kHz, 16-bit signed LE mono PCM (`linear_pcm` in `wav` container; 44-byte RIFF header stripped)
- Cancellation: Closing the active WebSocket on barge-in immediately aborts server-side synthesis
  so zero stale audio frames are produced or delivered.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
import struct
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from app.core.config import DEFAULT_GNANI_TTS_WS_URL, Settings
from app.core.logging import log_event, safe_text_preview

logger = logging.getLogger(__name__)

_WAV_HEADER_SIZE = 44

SUPPORTED_TTS_LANGUAGES = frozenset(
    {
        "auto",
        "hi-IN",
        "en-IN",
        "ta-IN",
        "te-IN",
        "kn-IN",
        "ml-IN",
        "mr-IN",
        "bn-IN",
        "gu-IN",
        "pa-IN",
    }
)


def strip_wav_header(data: bytes) -> bytes:
    """Strip RIFF/WAVE header if present, returning raw PCM bytes."""
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return data
    offset = 12
    while offset + 8 <= len(data):
        chunk_id = data[offset : offset + 4]
        chunk_size = struct.unpack_from("<I", data, offset + 4)[0]
        if chunk_id == b"data":
            start = offset + 8
            return data[start : start + chunk_size] if chunk_size else data[start:]
        offset += 8 + chunk_size
    return b"" if len(data) <= _WAV_HEADER_SIZE else data[_WAV_HEADER_SIZE:]


class Pcm16StreamProcessor:
    """Strips an initial (possibly split) WAV header and aligns raw 16-bit PCM frames."""

    def __init__(self) -> None:
        self._wav_pending = b""
        self._remainder = b""

    def reset(self) -> None:
        self._wav_pending = b""
        self._remainder = b""

    def process(self, chunk: bytes) -> bytes:
        if not chunk:
            return b""
        if self._wav_pending or (len(chunk) >= 4 and chunk[:4] == b"RIFF"):
            buf = self._wav_pending + chunk
            self._wav_pending = b""
            if buf[:4] == b"RIFF" and len(buf) < _WAV_HEADER_SIZE:
                self._wav_pending = buf
                return b""
            pcm = strip_wav_header(buf)
        else:
            pcm = chunk

        if not pcm:
            return b""
        combined = self._remainder + pcm
        aligned_len = len(combined) - (len(combined) % 2)
        self._remainder = combined[aligned_len:]
        return combined[:aligned_len]


class GnaniTimbreTTSAdapter:
    """Interruptible async WebSocket client for Gnani Timbre v3.0 TTS."""

    def __init__(
        self,
        *,
        api_key: str,
        ws_url: str = DEFAULT_GNANI_TTS_WS_URL,
        model: str = "timbre-v3.0",
        default_voice: str = "Shivani",
        default_language: str = "hi-IN",
        sample_rate: int = 16000,
        open_timeout: float = 20.0,
        chunk_timeout: float = 20.0,
    ) -> None:
        if not api_key:
            raise ValueError("GNANI_API_KEY is required for GnaniTimbreTTSAdapter")
        self._api_key = api_key
        self._ws_url = ws_url or DEFAULT_GNANI_TTS_WS_URL
        self._model = model or "timbre-v3.0"
        self._default_voice = default_voice or "Shivani"
        self._default_language = default_language or "hi-IN"
        self._sample_rate = sample_rate
        self._open_timeout = open_timeout
        self._chunk_timeout = chunk_timeout

        self._ws: Any = None
        self._ws_lock = asyncio.Lock()
        self._generation = 0
        self._closed = False

    @classmethod
    def from_settings(cls, settings: Settings) -> GnaniTimbreTTSAdapter:
        return cls(
            api_key=settings.gnani_api_key.get_secret_value(),
            ws_url=settings.effective_tts_ws_url,
            model=settings.gnani_tts_model or "timbre-v3.0",
            default_voice=settings.gnani_tts_voice or "Shivani",
            default_language=settings.default_language or "hi-IN",
            sample_rate=settings.audio_sample_rate,
        )

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def _is_ws_open(self, ws: Any) -> bool:
        if ws is None:
            return False
        state = getattr(ws, "state", None)
        state_name = getattr(state, "name", None)
        if isinstance(state_name, str):
            return state_name.upper() == "OPEN"
        return not bool(getattr(ws, "closed", False))

    async def connect(self) -> None:
        """Eagerly open a persistent WebSocket to Gnani Timbre v3.0."""
        async with self._ws_lock:
            if self._is_ws_open(self._ws):
                return
            await self._open_fresh_socket()

    async def _open_fresh_socket(self) -> Any:
        request_id = f"asha_tts_{uuid.uuid4().hex[:12]}"
        headers = {
            "X-API-Key-ID": self._api_key,
            "Content-Type": "application/json",
            "X-API-Request-ID": request_id,
        }
        ws = await websockets.connect(
            self._ws_url,
            additional_headers=headers,
            open_timeout=self._open_timeout,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
        )
        self._ws = ws
        log_event(logger, "tts_connected", request_id=request_id, model=self._model)
        return ws

    async def cancel_active(self, *, warm_reconnect: bool = True) -> None:
        """Abort any in-flight synthesis immediately by closing the WebSocket."""
        self._generation += 1
        ws = self._ws
        self._ws = None
        if ws is not None:
            with contextlib.suppress(Exception):
                await ws.close()
        log_event(logger, "tts_cancelled_upstream", generation=self._generation)
        if warm_reconnect and not self._closed:
            asyncio.create_task(self._warm_reconnect_background())

    async def _warm_reconnect_background(self) -> None:
        with contextlib.suppress(Exception):
            if not self._closed:
                await self.connect()

    async def close(self) -> None:
        self._closed = True
        await self.cancel_active(warm_reconnect=False)

    def _normalize_language(self, language: str | None) -> str:
        lang = (language or self._default_language or "hi-IN").strip()
        return lang if lang in SUPPORTED_TTS_LANGUAGES else "auto"

    async def synthesize_stream(
        self,
        text: str,
        *,
        language: str | None = None,
        voice: str | None = None,
    ) -> AsyncIterator[bytes]:
        """Stream aligned raw PCM_S16LE chunks for `text`. Safe to cancel mid-stream."""
        cleaned = text.strip()
        if not cleaned:
            return

        my_gen = self._generation
        request_id = f"asha_tts_{uuid.uuid4().hex[:12]}"
        payload = {
            "text": cleaned,
            "voice": voice or self._default_voice,
            "model": self._model,
            "language": self._normalize_language(language),
            "audio_config": {
                "sample_rate": self._sample_rate,
                "encoding": "linear_pcm",
                "num_channels": 1,
                "sample_width": 2,
                "container": "wav",
            },
        }

        async with self._ws_lock:
            if not self._is_ws_open(self._ws):
                await self._open_fresh_socket()
            ws = self._ws

        if ws is None or my_gen != self._generation:
            return

        processor = Pcm16StreamProcessor()
        t0 = time.perf_counter()
        ttfb_ms: int | None = None
        total_bytes = 0

        try:
            try:
                await ws.send(json.dumps(payload))
            except ConnectionClosed:
                if my_gen != self._generation:
                    return
                async with self._ws_lock:
                    ws = await self._open_fresh_socket()
                await ws.send(json.dumps(payload))

            while my_gen == self._generation:
                msg = await asyncio.wait_for(ws.recv(), timeout=self._chunk_timeout)
                if my_gen != self._generation:
                    break

                if isinstance(msg, bytes):
                    pcm = processor.process(msg)
                    if pcm:
                        if ttfb_ms is None:
                            ttfb_ms = int((time.perf_counter() - t0) * 1000)
                        total_bytes += len(pcm)
                        yield pcm
                    continue

                data = json.loads(msg)
                msg_type = data.get("type", "")

                if msg_type == "audio":
                    b64 = _extract_audio_b64(data)
                    if b64:
                        pcm = processor.process(base64.b64decode(b64))
                        if pcm:
                            if ttfb_ms is None:
                                ttfb_ms = int((time.perf_counter() - t0) * 1000)
                            total_bytes += len(pcm)
                            yield pcm

                elif msg_type == "complete":
                    # Gnani sends two `complete` messages: first with dict `data` (last chunk),
                    # second with only `"message": "Streaming completed"`.
                    if isinstance(data.get("data"), dict):
                        b64 = _extract_audio_b64(data)
                        if b64:
                            pcm = processor.process(base64.b64decode(b64))
                            if pcm:
                                if ttfb_ms is None:
                                    ttfb_ms = int((time.perf_counter() - t0) * 1000)
                                total_bytes += len(pcm)
                                yield pcm
                        with contextlib.suppress(Exception):
                            await asyncio.wait_for(ws.recv(), timeout=0.08)
                        break
                    break

                elif msg_type == "error":
                    err_msg = data.get("message", "Unknown Gnani TTS error")
                    logger.error("tts_stream_error request_id=%s error=%s", request_id, err_msg)
                    raise RuntimeError(f"Gnani TTS error: {err_msg}")

            log_event(
                logger,
                "tts_complete",
                request_id=request_id,
                ttfb_ms=ttfb_ms,
                total_ms=int((time.perf_counter() - t0) * 1000),
                bytes=total_bytes,
                preview=safe_text_preview(cleaned),
            )
        except asyncio.CancelledError:
            # Close the socket so upstream server stops streaming the cancelled turn
            await self.cancel_active()
            raise
        except ConnectionClosed:
            if my_gen == self._generation:
                logger.warning("tts_ws_closed_mid_stream request_id=%s", request_id)
                if self._ws is ws:
                    self._ws = None
        except Exception:
            if self._ws is ws:
                self._ws = None
                with contextlib.suppress(Exception):
                    await ws.close()
            raise


def _extract_audio_b64(payload: dict[str, Any]) -> str:
    nested = payload.get("data")
    if isinstance(nested, dict) and nested.get("audio"):
        return str(nested["audio"])
    return str(payload.get("audio", ""))

