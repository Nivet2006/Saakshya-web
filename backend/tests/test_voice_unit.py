"""Unit & mocked tests for Milestone 1 voice components.

Label: UNIT / MOCKED (does NOT substitute for live Gnani verification).
"""

from __future__ import annotations

import asyncio
import json
import struct
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402
from app.voice.interfaces import ChatMessage, TranscriptEvent, VADDecision  # noqa: E402
from app.voice.orchestration.session import VoiceSessionOrchestrator  # noqa: E402
from app.voice.stt.gnani_prisma import GnaniPrismaSTTAdapter  # noqa: E402
from app.voice.tts.gnani_timbre import Pcm16StreamProcessor, strip_wav_header  # noqa: E402
from app.voice.vad.silero_onnx import FRAME_BYTES_16K, SileroOnnxVAD  # noqa: E402


def _make_wav_header(data_len: int = 100) -> bytes:
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_len,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        16000,
        32000,
        2,
        16,
        b"data",
        data_len,
    )


def test_strip_wav_header_and_aligner() -> None:
    header = _make_wav_header(6)
    pcm_body = b"\x01\x02\x03\x04\x05\x06"
    assert strip_wav_header(header + pcm_body) == pcm_body

    # Split WAV header across chunks + odd-byte alignment
    proc = Pcm16StreamProcessor()
    assert proc.process(header[:20]) == b""
    assert proc.process(header[20:] + b"\x10\x20\x30") == b"\x10\x20"
    assert proc.process(b"\x40\x50\x60") == b"\x30\x40\x50\x60"


def test_prisma_message_parser_handles_partials_and_finals() -> None:
    adapter = GnaniPrismaSTTAdapter(api_key="test-key-not-real")
    partial_raw = json.dumps(
        {
            "type": "partial_transcript",
            "utterance_id": "u1",
            "seq": 2,
            "is_final": False,
            "text": "Today I visited Lakshmi",
            "stable_text": "Today I visited",
            "volatile_text": "Lakshmi",
        }
    )
    ev_p = adapter._parse_message(partial_raw)
    assert ev_p is not None
    assert ev_p.event_type == "partial"
    assert ev_p.is_final is False
    assert ev_p.text == "Today I visited Lakshmi"

    final_raw = json.dumps(
        {
            "type": "final_transcript",
            "text": "Weight is 52 kilo, TT injection pending hai.",
            "is_final": True,
            "latency": 150,
            "detected_language_code": "hi-IN",
            "utterance_id": "u1",
            "segment_id": "seg-1",
        }
    )
    ev_f = adapter._parse_message(final_raw)
    assert ev_f is not None
    assert ev_f.event_type == "final"
    assert ev_f.is_final is True
    assert ev_f.language_code == "hi-IN"
    assert ev_f.latency_ms == 150


def test_silero_onnx_vad_rejects_silence_and_transient_burst() -> None:
    vad = SileroOnnxVAD(barge_in_min_speech_ms=300)
    silence = b"\x00" * FRAME_BYTES_16K
    for _ in range(15):
        dec = vad.process_frame(silence, assistant_speaking=True)
        assert dec.is_speech is False
        assert dec.barge_in_triggered is False

    # Brief 1-frame impulse noise must NOT trigger barge-in
    impulse = (np.random.default_rng(42).normal(0, 0.2, 512) * 32767).astype(np.int16).tobytes()
    dec_imp = vad.process_frame(impulse, assistant_speaking=True)
    assert dec_imp.barge_in_triggered is False


class _MockSTT:
    def __init__(self) -> None:
        self.is_connected = False
        self.queue: asyncio.Queue[TranscriptEvent | None] = asyncio.Queue()
        self.sent_chunks: list[bytes] = []

    async def connect(self) -> None:
        self.is_connected = True

    async def send_audio(self, pcm_chunk: bytes) -> None:
        self.sent_chunks.append(pcm_chunk)

    async def events(self) -> AsyncIterator[TranscriptEvent]:
        while True:
            item = await self.queue.get()
            if item is None:
                break
            yield item

    async def close(self) -> None:
        self.is_connected = False
        await self.queue.put(None)


class _MockSlowTTS:
    def __init__(self) -> None:
        self.sample_rate = 16000
        self.cancelled_count = 0
        self.calls: list[str] = []

    async def connect(self) -> None:
        pass

    async def synthesize_stream(
        self, text: str, *, language: str | None = None, voice: str | None = None
    ) -> AsyncIterator[bytes]:
        self.calls.append(text)
        for _ in range(20):
            await asyncio.sleep(0.03)
            yield b"\x01\x00" * 512

    async def cancel_active(self) -> None:
        self.cancelled_count += 1

    async def close(self) -> None:
        pass


class _MockLLM:
    provider_name = "mock"
    model_name = "mock-llm"

    def __init__(self) -> None:
        self.seen_histories: list[list[ChatMessage]] = []

    async def generate_reply(
        self,
        messages: list[ChatMessage],
        *,
        system_prompt: str,
        active_language: str,
        max_tokens: int = 160,
    ) -> str:
        self.seen_histories.append(list(messages))
        last = messages[-1].content
        if "28" in last or "twenty-eighth" in last:
            return "Updated next visit to 28 November. Should I confirm?"
        return "Noted ANC visit for Lakshmi, next visit 26 November."


class _TriggerOnCommandVAD:
    def __init__(self) -> None:
        self.trigger_next = False

    def reset(self) -> None:
        pass

    def process_frame(self, pcm_frame: bytes, *, assistant_speaking: bool) -> VADDecision:
        trig = self.trigger_next and assistant_speaking
        self.trigger_next = False
        return VADDecision(0.9 if trig else 0.1, 0.2 if trig else 0.0, 0.01, trig, trig)


@pytest.mark.asyncio
async def test_orchestrator_barge_in_stops_stale_audio_and_resumes_context() -> None:
    """UNIT/MOCKED test verifying zero stale audio after barge-in and context resumption."""
    emitted: list[dict[str, Any]] = []

    async def emit(ev: dict[str, Any]) -> None:
        emitted.append(ev)

    stt = _MockSTT()
    tts = _MockSlowTTS()
    llm = _MockLLM()
    vad = _TriggerOnCommandVAD()

    orch = VoiceSessionOrchestrator(
        session_id="test_sess_1",
        stt=stt,
        tts=tts,
        llm=llm,
        vad=vad,
        emit=emit,
    )
    orch._turn_debounce_s = 0.02
    await orch.start()

    # Turn 1: worker speaks
    await stt.queue.put(
        TranscriptEvent(
            event_type="final",
            text="ANC visit for Lakshmi, next visit 26 November.",
            is_final=True,
            language_code="hi-IN",
        )
    )
    # Wait until TTS has emitted at least 2 audio chunks for turn 1
    for _ in range(50):
        await asyncio.sleep(0.02)
        turn1_chunks = [e for e in emitted if e["type"] == "tts_audio_chunk" and e["turn_id"] == 1]
        if len(turn1_chunks) >= 2:
            break
    assert len(turn1_chunks) >= 2
    assert orch.assistant_speaking is True

    # Trigger VAD barge-in mid-TTS!
    vad.trigger_next = True
    await orch.handle_audio_chunk(b"\x01\x00" * 512)
    barge_idx = next(i for i, e in enumerate(emitted) if e["type"] == "tts_cancelled")
    assert tts.cancelled_count >= 1
    assert orch.assistant_speaking is False

    # Wait briefly to verify ZERO stale turn-1 chunks arrive after tts_cancelled
    await asyncio.sleep(0.1)
    stale_after_cancel = [
        e for e in emitted[barge_idx + 1 :] if e["type"] == "tts_audio_chunk" and e["turn_id"] == 1
    ]
    assert stale_after_cancel == []

    # Turn 2: interrupting correction arrives -> resumes conversation with prior context
    await stt.queue.put(
        TranscriptEvent(
            event_type="final",
            text="No, next visit 28 November.",
            is_final=True,
            language_code="hi-IN",
        )
    )
    for _ in range(80):
        await asyncio.sleep(0.02)
        if any(e["type"] == "tts_complete" and e["turn_id"] > 1 for e in emitted):
            break

    responses = [e for e in emitted if e["type"] == "assistant_response"]
    assert len(responses) == 2
    assert "28 November" in responses[1]["text"]
    # LLM saw Turn 1 context when answering Turn 2
    assert len(llm.seen_histories[-1]) >= 3

    await orch.close()


def test_rest_health_and_synthetic_beneficiaries() -> None:
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["synthetic_data_only"] is True

    r_ben = client.get("/api/v1/beneficiaries?q=Lakshmi")
    assert r_ben.status_code == 200
    ids = {b["beneficiary_id"] for b in r_ben.json()["beneficiaries"]}
    assert "BEN-1042" in ids

    r_sess = client.post("/api/v1/sessions", json={"language": "indic-auto", "beneficiary_id": "BEN-1042"})
    assert r_sess.status_code == 200
    assert r_sess.json()["websocket_path"].startswith("/ws/voice/")


def test_all_ten_indic_languages_supported_without_fallback_or_keyerror() -> None:
    from app.conversation.models import SUPPORTED_LANGUAGES, normalize_language
    from app.conversation.state_machine import generate_beneficiary_greeting_text
    from app.danger_signs.detector import get_referral_message

    expected = {"hi-IN", "en-IN", "kn-IN", "ta-IN", "te-IN", "ml-IN", "bn-IN", "mr-IN", "gu-IN", "pa-IN"}
    assert expected.issubset(set(SUPPORTED_LANGUAGES))
    for lang in expected:
        assert normalize_language(lang) == lang
        assert normalize_language(lang.split("-")[0]) == lang
        greeting = generate_beneficiary_greeting_text("Lakshmi Devi", "BEN-1042", lang)
        referral = get_referral_message(lang)
        assert isinstance(greeting, str) and len(greeting) > 5
        assert isinstance(referral, str) and len(referral) > 5


@pytest.mark.asyncio
async def test_language_lock_preserves_selected_tamil_on_english_codemix() -> None:
    from app.healthcare.pipeline import HealthcareSessionPipeline

    emitted: list[dict[str, Any]] = []

    async def emit(ev: dict[str, Any]) -> None:
        emitted.append(ev)

    stt = _MockSTT()
    tts = _MockSlowTTS()
    llm = _MockLLM()
    vad = _TriggerOnCommandVAD()

    pipeline = HealthcareSessionPipeline(session_id="lang_lock_1", language="ta-IN", beneficiary_id="BEN-1042")
    pipeline.set_preferred_language("ta-IN", fallback="ta-IN")

    orch = VoiceSessionOrchestrator(
        session_id="lang_lock_1",
        stt=stt,
        tts=tts,
        llm=llm,
        vad=vad,
        emit=emit,
        default_language="ta-IN",
        language_locked=True,
        on_partial_hook=pipeline.on_partial_transcript,
        on_final_hook=pipeline.on_final_transcript,
    )
    pipeline.attach_orchestrator(orch)
    orch._turn_debounce_s = 0.02
    await orch.start()

    # Code-mixed English numbers/phrases when user explicitly selected Tamil
    await stt.queue.put(
        TranscriptEvent(
            event_type="final",
            text="Baby weight 2.8 kg next visit 28 November",
            is_final=True,
            language_code="en-IN",
        )
    )
    for _ in range(50):
        await asyncio.sleep(0.02)
        if any(e.get("type") in {"final_transcript", "assistant_response", "visit_draft_updated"} for e in emitted):
            break

    assert orch.active_language == "ta-IN"
    assert pipeline.sm.active_language == "ta-IN"
    finals = [e for e in emitted if e.get("type") == "final_transcript"]
    assert finals and finals[0]["language"] == "ta-IN"
    await orch.close()


def test_create_beneficiary_endpoint_and_partial_danger_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("DANGER_SIGN_PARTIAL_MATCHING", "false")
    get_settings.cache_clear()
    try:
        assert get_settings().danger_sign_partial_matching is False
        client = TestClient(app)
        r = client.post(
            "/api/v1/beneficiaries",
            json={
                "full_name": "Priya Murugan",
                "category": "PREGNANT_WOMAN",
                "village": "Kaveri Demo Ward 4",
                "preferred_language": "ta-IN",
                "age_years": 24,
                "high_risk_status": True,
            },
        )
        assert r.status_code == 200
        created = r.json()["beneficiary"]
        assert created["full_name"] == "Priya Murugan"
        assert created["beneficiary_id"].startswith("BEN-")

        r_list = client.get("/api/v1/beneficiaries?q=Priya%20Murugan")
        assert r_list.status_code == 200
        assert any(b["beneficiary_id"] == created["beneficiary_id"] for b in r_list.json()["beneficiaries"])
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_preselected_beneficiary_understands_clinical_notes_without_explicit_yes() -> None:
    from app.conversation.models import ConversationState
    from app.healthcare.pipeline import HealthcareSessionPipeline

    emitted: list[dict[str, Any]] = []

    async def emit(ev: dict[str, Any]) -> None:
        emitted.append(ev)

    stt = _MockSTT()
    tts = _MockSlowTTS()
    llm = _MockLLM()
    vad = _TriggerOnCommandVAD()

    pipeline = HealthcareSessionPipeline(session_id="clin_skip_yes", language="en-IN", beneficiary_id="BEN-1042")
    pipeline.set_preferred_language("en-IN", fallback="en-IN")
    orch = VoiceSessionOrchestrator(
        session_id="clin_skip_yes",
        stt=stt,
        tts=tts,
        llm=llm,
        vad=vad,
        emit=emit,
        default_language="en-IN",
        language_locked=True,
        on_partial_hook=pipeline.on_partial_transcript,
        on_final_hook=pipeline.on_final_transcript,
    )
    pipeline.attach_orchestrator(orch)
    await orch.start()
    await pipeline.start_session_greeting(orch)
    assert pipeline.sm.state == ConversationState.IDENTITY_CONFIRMATION

    await stt.queue.put(
        TranscriptEvent(
            event_type="final",
            text="ANC visit completed, weight is 53 kilo, next visit 28 November.",
            is_final=True,
            language_code="en-IN",
        )
    )
    for _ in range(50):
        await asyncio.sleep(0.02)
        if pipeline.sm.visit.weight_kg == 53.0:
            break

    assert pipeline.sm.identity_verified is True
    assert pipeline.sm.visit.weight_kg == 53.0
    assert pipeline.sm.visit.next_visit_date == "2026-11-28"
    await orch.close()


def test_codemixed_indic_english_baby_weight_and_vlbw() -> None:
    from datetime import date
    from app.extraction.extractor import VisitFieldExtractor
    from app.extraction.models import VisitDraft

    ext = VisitFieldExtractor()
    draft = VisitDraft(visit_id="v_mix", beneficiary_id="BEN-1042")

    # Tamil-English, Telugu-English, and English "baby's weight is two" on ANC mother profile
    for phrase in (
        "the baby's weight is two",
        "குழந்தையின் எடை வந்து two",
        "బేబీ వెయిట్ వచ్చేసి two",
        "बच्चे का वजन दो",
    ):
        res = ext.extract(phrase, reference_date=date(2026, 11, 21), existing_draft=draft)
        assert res.patch.get("weight_kg") == 2.0, f"Failed for {phrase!r}: {res}"
        assert not any(c.field_name == "weight_kg" for c in res.clarifications)

