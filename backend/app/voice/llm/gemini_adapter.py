"""Replaceable Gemini (with optional Groq fallback) async LLM adapter.

Verified live (2026-11-21):
- `gemini-3.1-flash-lite` with `thinking_budget=0` responds in ~1.5s for short Hinglish turns.
- `gemini-3.5-flash-lite` (default config) serves as an automatic in-provider fallback.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from google import genai
from google.genai import types

from app.core.config import Settings
from app.core.logging import log_event, safe_text_preview
from app.voice.interfaces import ChatMessage

logger = logging.getLogger(__name__)

MILESTONE1_SYSTEM_PROMPT = """You are Sakshi, a fast, helpful voice assistant for Indian ASHA community health workers recording home-visit notes.

Rules:
1. Reply in the SAME language/style as the ASHA worker (Hindi/Hinglish, Kannada, Tamil, Telugu, or Indian English).
2. Keep every reply VERY SHORT (1-2 brief sentences, under 28 words) because it will be spoken aloud via TTS.
3. Acknowledge the visit details the worker mentioned and ask only ONE concise clarifying or follow-up question if needed.
4. NEVER diagnose, prescribe medicine, or recommend home remedies/treatments. If a serious symptom/danger sign is mentioned, immediately instruct the worker to refer the mother or newborn to the nearest Primary Health Centre (PHC) immediately — never invent a PHC name, address, or phone number.
5. Never invent beneficiary IDs, weights, dates, or vaccination statuses that the worker did not state.
6. Write numbers and dates clearly so TTS speaks them naturally. Do not use markdown, bullet points, or emojis."""


_LANG_DISPLAY = {
    "hi-IN": "Hindi (hi-IN, Devanagari script)",
    "en-IN": "Indian English (en-IN)",
    "kn-IN": "Kannada (kn-IN, Kannada script)",
    "ta-IN": "Tamil (ta-IN, Tamil script)",
    "te-IN": "Telugu (te-IN, Telugu script)",
    "ml-IN": "Malayalam (ml-IN, Malayalam script)",
    "bn-IN": "Bengali (bn-IN, Bengali script)",
    "mr-IN": "Marathi (mr-IN, Devanagari script)",
    "gu-IN": "Gujarati (gu-IN, Gujarati script)",
    "pa-IN": "Punjabi (pa-IN, Gurmukhi script)",
}


def _language_instruction(active_language: str) -> str:
    label = _LANG_DISPLAY.get(active_language, active_language)
    return (
        f"\nActive worker language: {label}. "
        f"Respond in {label} cleanly so Gnani Timbre TTS speaks it naturally."
    )


class GeminiLLMAdapter:
    """Async Gemini LLM adapter with zero-thinking low-latency config and fallback."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-3.1-flash-lite",
        fallback_models: tuple[str, ...] = ("gemini-3.5-flash-lite",),
        timeout_ms: int = 12_000,
    ) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiLLMAdapter")
        self._model = model
        self._fallback_models = tuple(m for m in fallback_models if m and m != model)
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout_ms),
        )

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    def _build_contents(self, messages: list[ChatMessage]) -> list[types.Content]:
        contents: list[types.Content] = []
        for msg in messages:
            if msg.role == "system":
                continue
            role = "model" if msg.role == "assistant" else "user"
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg.content)])
            )
        return contents

    def _build_config(
        self,
        *,
        model: str,
        system_prompt: str,
        active_language: str,
        max_tokens: int,
    ) -> types.GenerateContentConfig:
        lang_hint = _language_instruction(active_language)
        kwargs: dict[str, Any] = {
            "system_instruction": system_prompt + lang_hint,
            "max_output_tokens": max_tokens,
            "temperature": 0.3,
        }
        # `gemini-3.1-flash-lite` supports thinking_budget=0 for lowest voice latency;
        # `gemini-3.5-flash-lite` rejects thinking_budget=0, so omit for 3.5-flash-lite.
        if "3.1-flash-lite" in model:
            kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        return types.GenerateContentConfig(**kwargs)

    async def generate_reply(
        self,
        messages: list[ChatMessage],
        *,
        system_prompt: str = MILESTONE1_SYSTEM_PROMPT,
        active_language: str = "hi-IN",
        max_tokens: int = 160,
    ) -> str:
        """Generate a short contextual voice reply, falling back on transient errors."""
        contents = self._build_contents(messages)
        if not contents:
            return "नमस्ते, कृपया विजिट की जानकारी बताइए।"

        models_to_try = (self._model, *self._fallback_models)
        last_exc: Exception | None = None

        for candidate in models_to_try:
            t0 = time.perf_counter()
            cfg = self._build_config(
                model=candidate,
                system_prompt=system_prompt,
                active_language=active_language,
                max_tokens=max_tokens,
            )
            try:
                resp = await self._client.aio.models.generate_content(
                    model=candidate,
                    contents=contents,
                    config=cfg,
                )
                text = (resp.text or "").strip()
                if text:
                    log_event(
                        logger,
                        "llm_reply",
                        provider="gemini",
                        model=candidate,
                        latency_ms=int((time.perf_counter() - t0) * 1000),
                        preview=safe_text_preview(text),
                    )
                    return text
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "llm_attempt_failed provider=gemini model=%s err=%s",
                    candidate,
                    str(exc)[:160],
                )

        raise RuntimeError(f"All Gemini LLM models failed: {last_exc}")


class GroqLLMAdapter:
    """Optional Groq async LLM adapter (used when LLM_PROVIDER=groq or as fallback)."""

    def __init__(self, *, api_key: str, model: str = "llama-3.1-8b-instant") -> None:
        if not api_key:
            raise ValueError("GROQ_API_KEY is required for GroqLLMAdapter")
        from groq import AsyncGroq

        self._client = AsyncGroq(api_key=api_key, timeout=12.0)
        self._model = model

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate_reply(
        self,
        messages: list[ChatMessage],
        *,
        system_prompt: str = MILESTONE1_SYSTEM_PROMPT,
        active_language: str = "hi-IN",
        max_tokens: int = 160,
    ) -> str:
        t0 = time.perf_counter()
        payload = [{"role": "system", "content": f"{system_prompt}{_language_instruction(active_language)}"}]
        payload.extend({"role": m.role, "content": m.content} for m in messages if m.role != "system")
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=payload,  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=0.3,
        )
        text = (resp.choices[0].message.content or "").strip()
        log_event(
            logger,
            "llm_reply",
            provider="groq",
            model=self._model,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            preview=safe_text_preview(text),
        )
        return text


def build_llm_adapter(settings: Settings) -> GeminiLLMAdapter | GroqLLMAdapter:
    """Instantiate the configured primary LLM adapter from root `.env`."""
    provider = settings.llm_provider.lower()
    if provider == "groq":
        return GroqLLMAdapter(
            api_key=settings.groq_api_key.get_secret_value(),
            model=settings.effective_llm_model,
        )
    return GeminiLLMAdapter(
        api_key=settings.gemini_api_key.get_secret_value(),
        model=settings.effective_llm_model,
    )

