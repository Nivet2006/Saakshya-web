"""Replaceable provider protocols and canonical voice pipeline event models."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass(slots=True)
class TranscriptEvent:
    """Normalized STT event emitted by any streaming STT adapter."""

    event_type: Literal["connected", "speech_start", "partial", "speech_end", "final", "error"]
    text: str = ""
    is_final: bool = False
    language_code: str | None = None
    utterance_id: str | None = None
    segment_id: str | None = None
    seq: int | None = None
    latency_ms: int | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VADDecision:
    """Per-frame output from local VAD + barge-in detector."""

    speech_prob: float
    frame_rms: float
    noise_floor_rms: float
    is_speech: bool
    barge_in_triggered: bool = False
    pre_roll_pcm: bytes = b""


@dataclass(slots=True)
class ChatMessage:
    """Minimal provider-agnostic conversation message."""

    role: Literal["system", "user", "assistant"]
    content: str


class StreamingSTTAdapter(Protocol):
    """Protocol for streaming Speech-to-Text providers (e.g. Gnani Prisma v3.0)."""

    @property
    def is_connected(self) -> bool: ...

    async def connect(self) -> None: ...

    async def send_audio(self, pcm_chunk: bytes) -> None: ...

    def events(self) -> AsyncIterator[TranscriptEvent]: ...

    async def close(self) -> None: ...


class StreamingTTSAdapter(Protocol):
    """Protocol for interruptible streaming Text-to-Speech providers (e.g. Gnani Timbre v3.0)."""

    @property
    def sample_rate(self) -> int: ...

    async def connect(self) -> None: ...

    def synthesize_stream(
        self,
        text: str,
        *,
        language: str | None = None,
        voice: str | None = None,
    ) -> AsyncIterator[bytes]: ...

    async def cancel_active(self) -> None:
        """Immediately stop in-flight synthesis so no stale audio continues."""
        ...

    async def close(self) -> None: ...


class LLMAdapter(Protocol):
    """Protocol for replaceable conversational LLM providers."""

    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    async def generate_reply(
        self,
        messages: list[ChatMessage],
        *,
        system_prompt: str,
        active_language: str,
        max_tokens: int = 160,
    ) -> str: ...


class VADDetector(Protocol):
    """Protocol for frame-level local VAD + dual-gate barge-in detector."""

    def reset(self) -> None: ...

    def process_frame(self, pcm_frame: bytes, *, assistant_speaking: bool) -> VADDecision: ...

