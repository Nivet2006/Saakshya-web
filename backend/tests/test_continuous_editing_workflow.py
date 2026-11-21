"""Acceptance tests for Live Data Editing, Natural Corrections & Final Submission Workflow.

Covers all 9 Section 11 Acceptance Tests + contextual/ambiguous corrections + v1 schema parity.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.conversation.models import ConversationState, VisitStatus  # noqa: E402
from app.healthcare.pipeline import HealthcareSessionPipeline  # noqa: E402
from app.voice.interfaces import ChatMessage, TranscriptEvent  # noqa: E402
from app.voice.orchestration.session import VoiceSessionOrchestrator  # noqa: E402
from tests.test_contracts import validate_instance as validate_schema  # noqa: E402

CONTRACTS_DIR = REPO_ROOT / "shared-contracts"
EVENTS_SCHEMA = json.loads((CONTRACTS_DIR / "voice-events.schema.json").read_text(encoding="utf-8"))
VISIT_SCHEMA = json.loads((CONTRACTS_DIR / "visit.schema.json").read_text(encoding="utf-8"))


class _DummySTT:
    is_connected = True

    def __init__(self) -> None:
        self.q: asyncio.Queue[TranscriptEvent | None] = asyncio.Queue()

    async def connect(self) -> None:
        pass

    async def send_audio(self, pcm_chunk: bytes) -> None:
        pass

    async def events(self) -> AsyncIterator[TranscriptEvent]:
        while True:
            item = await self.q.get()
            if item is None:
                break
            yield item

    async def close(self) -> None:
        await self.q.put(None)


class _DummyTTS:
    sample_rate = 16000

    def __init__(self) -> None:
        self.spoken: list[str] = []

    async def connect(self) -> None:
        pass

    async def synthesize_stream(
        self, text: str, *, language: str | None = None, voice: str | None = None
    ) -> AsyncIterator[bytes]:
        self.spoken.append(text)
        yield b"\x01\x00" * 256

    async def cancel_active(self) -> None:
        pass

    async def close(self) -> None:
        pass


class _DummyLLM:
    provider_name = "mock"
    model_name = "mock"

    async def generate_reply(
        self,
        messages: list[ChatMessage],
        *,
        system_prompt: str,
        active_language: str,
        max_tokens: int = 160,
    ) -> str:
        return "Okay, please continue."


async def _make_session(
    session_id: str,
    *,
    beneficiary_id: str = "BEN-1044",
    review_silence_timeout_s: float = 0.0,
) -> tuple[HealthcareSessionPipeline, VoiceSessionOrchestrator, _DummyTTS, list[dict[str, Any]]]:
    emitted: list[dict[str, Any]] = []

    async def emit(ev: dict[str, Any]) -> None:
        emitted.append(ev)

    tts = _DummyTTS()
    pipeline = HealthcareSessionPipeline(
        session_id=session_id,
        worker_id="ASHA-DEMO-01",
        language="en-IN",
        beneficiary_id=beneficiary_id,
        reference_date=date(2026, 11, 21),
        continuous_editing=True,
        review_silence_timeout_s=review_silence_timeout_s,
    )
    orch = VoiceSessionOrchestrator(
        session_id=session_id,
        stt=_DummySTT(),
        tts=tts,
        llm=_DummyLLM(),
        vad=None,
        emit=emit,
        default_language="en-IN",
        on_partial_hook=pipeline.on_partial_transcript,
        on_final_hook=pipeline.on_final_transcript,
    )
    pipeline.attach_orchestrator(orch)
    await orch.start()
    await pipeline.start_session_greeting(orch)
    await orch.handle_text_input("Yes")
    await asyncio.sleep(0.03)
    return pipeline, orch, tts, emitted


@pytest.mark.asyncio
async def test_1_to_4_natural_corrections_multi_patch_and_additional_info() -> None:
    """Tests 1, 2, 3, 4: Basic correction, without NO, multiple corrections, additional vaccination."""
    pipeline, orch, tts, emitted = await _make_session("sess_edit_1_4")

    # Test 1: "Weight is 2.1 kg." -> "Actually, 2.8 kg." (and also verify 1.0 -> 2.8 when VLBW fires)
    await orch.handle_text_input("Newborn visit. Weight is 2.1 kg.")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.weight_kg == 2.1
    assert pipeline.sm.state == ConversationState.CONTINUE_CONVERSATION

    await orch.handle_text_input("Actually, 2.8 kg.")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.weight_kg == 2.8
    assert pipeline.sm.visit.visit_type.value == "Newborn"
    assert "2.8" in tts.spoken[-1]

    # Contextual correction without explicit correction cue ("3.1 kilograms.")
    await orch.handle_text_input("3.1 kilograms.")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.weight_kg == 3.1

    # Test 2: Correction without NO ("Next visit is November 28." -> "Make that December 5.")
    await orch.handle_text_input("Next visit is November 28.")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.next_visit_date == "2026-11-28"

    await orch.handle_text_input("Make that December 5.")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.next_visit_date == "2026-12-05"
    assert pipeline.sm.visit.weight_kg == 3.1  # untouched

    # Test 3: Multiple corrections in one utterance
    await orch.handle_text_input("Weight should be 2.8 and next visit December 10.")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.weight_kg == 2.8
    assert pipeline.sm.visit.next_visit_date == "2026-12-10"

    # Test 4: Additional info (add vaccinations without deleting existing fields)
    await orch.handle_text_input("BCG is pending.")
    await asyncio.sleep(0.03)
    assert "BCG" in pipeline.sm.visit.vaccinations_due

    await orch.handle_text_input("I forgot to mention that OPV is already completed.")
    await asyncio.sleep(0.03)
    assert "OPV" in pipeline.sm.visit.vaccinations_completed
    assert "BCG" in pipeline.sm.visit.vaccinations_due
    assert pipeline.sm.visit.weight_kg == 2.8
    assert pipeline.sm.visit.next_visit_date == "2026-12-10"

    # Change history tracks all updates cleanly without duplicate fields
    assert len(pipeline.sm.change_history) >= 5
    for idx, ev in enumerate(emitted):
        assert validate_schema(ev, EVENTS_SCHEMA) == [], f"Event #{idx} invalid: {ev}"
    await orch.close()


@pytest.mark.asyncio
async def test_5_summary_yes_and_final_submission() -> None:
    """Test 5: Worker finishes -> asks readback preference -> YES -> reads latest summary -> YES -> saves."""
    pipeline, orch, tts, emitted = await _make_session("sess_edit_5")

    await orch.handle_text_input("Newborn visit. Weight is 1 kg. BCG is pending. Next visit November 28.")
    await asyncio.sleep(0.03)
    await orch.handle_text_input("No, no, it is 2.8 kilograms. Change next visit to December 5.")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.weight_kg == 2.8
    assert pipeline.sm.visit.next_visit_date == "2026-12-05"

    # Worker finishes editing
    await orch.handle_text_input("That's all.")
    await asyncio.sleep(0.03)
    assert pipeline.sm.state == ConversationState.ASK_READBACK_PREFERENCE
    assert "Would you like me to read the complete visit summary aloud?" in tts.spoken[-1]

    # Worker says YES -> reads latest corrected summary + asks to submit
    await orch.handle_text_input("Yes")
    await asyncio.sleep(0.03)
    assert pipeline.sm.state == ConversationState.ASK_SUBMISSION_CONFIRMATION
    summary_spoken = tts.spoken[-1]
    assert "2.8 kg" in summary_spoken
    assert "1 kg" not in summary_spoken
    assert "5 December 2026" in summary_spoken
    assert "Would you like to submit and save this visit now?" in summary_spoken

    # Worker confirms submission
    await orch.handle_text_input("Yes")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.status == VisitStatus.CONFIRMED
    assert any(e["type"] == "persistence_requested" for e in emitted)

    await pipeline.handle_persistence_ack(
        accepted=True,
        persistence_record_id="rec_final_005",
        committed_at="2026-11-21T13:00:00Z",
    )
    await asyncio.sleep(0.03)
    assert pipeline.sm.state == ConversationState.COMMITTED
    assert "successfully saved" in tts.spoken[-1].lower()
    assert validate_schema(pipeline.current_visit_contract(), VISIT_SCHEMA) == []
    for idx, ev in enumerate(emitted):
        assert validate_schema(ev, EVENTS_SCHEMA) == [], f"Event #{idx} invalid: {ev}"
    await orch.close()


@pytest.mark.asyncio
async def test_6_summary_no_skips_readback_directly_to_submission() -> None:
    """Test 6: Worker declines summary read-back -> asks directly whether to submit (does NOT reject visit)."""
    pipeline, orch, tts, _emitted = await _make_session("sess_edit_6")

    await orch.handle_text_input("Newborn visit, weight is 2.8 kg.")
    await asyncio.sleep(0.03)
    await orch.handle_text_input("I'm done.")
    await asyncio.sleep(0.03)
    assert pipeline.sm.state == ConversationState.ASK_READBACK_PREFERENCE

    await orch.handle_text_input("No")
    await asyncio.sleep(0.03)
    assert pipeline.sm.state == ConversationState.ASK_SUBMISSION_CONFIRMATION
    assert "Would you like to submit and save this visit now?" in tts.spoken[-1]
    assert pipeline.sm.visit.weight_kg == 2.8
    assert pipeline.sm.visit.status == VisitStatus.DRAFT
    await orch.close()


@pytest.mark.asyncio
async def test_7_silence_no_response_never_auto_submits() -> None:
    """Test 7: Silence repeats question once, then retains unsubmitted draft without ever submitting."""
    pipeline, orch, tts, emitted = await _make_session(
        "sess_edit_7", review_silence_timeout_s=0.05
    )

    await orch.handle_text_input("Newborn visit, weight is 2.8 kg.")
    await asyncio.sleep(0.03)
    await orch.handle_text_input("That's all.")
    await asyncio.sleep(0.03)
    assert pipeline.sm.state == ConversationState.ASK_READBACK_PREFERENCE

    # Wait past first repeat + second silence -> retains draft
    await asyncio.sleep(0.18)
    assert pipeline.sm.visit.status == VisitStatus.DRAFT
    assert pipeline.sm.state == ConversationState.CONTINUE_CONVERSATION
    assert not any(e["type"] in ("visit_confirmed", "persistence_requested", "visit_committed") for e in emitted)
    assert "unsubmitted draft" in tts.spoken[-1].lower()
    await orch.close()


@pytest.mark.asyncio
async def test_8_correction_after_summary_invalidates_old_summary() -> None:
    """Test 8: Worker changes a field after hearing summary -> invalidates old summary & re-asks summary pref."""
    pipeline, orch, tts, _emitted = await _make_session("sess_edit_8")

    await orch.handle_text_input("Newborn visit, weight is 2.8 kg.")
    await asyncio.sleep(0.03)
    await orch.handle_text_input("That's all.")
    await asyncio.sleep(0.03)
    await orch.handle_text_input("Yes")
    await asyncio.sleep(0.03)
    assert pipeline.sm.state == ConversationState.ASK_SUBMISSION_CONFIRMATION

    # Worker corrects weight after hearing summary
    await orch.handle_text_input("Wait, change the weight to 3 kilograms.")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.weight_kg == 3.0
    assert pipeline.sm.summary_outdated is True
    assert pipeline.sm.last_read_back_text is None
    assert pipeline.sm.state == ConversationState.CONTINUE_CONVERSATION

    # Finish again -> summary preference asked again
    await orch.handle_text_input("No more changes.")
    await asyncio.sleep(0.03)
    assert pipeline.sm.state == ConversationState.ASK_READBACK_PREFERENCE
    assert "Would you like me to read the complete visit summary aloud?" in tts.spoken[-1]

    await orch.handle_text_input("Yes")
    await asyncio.sleep(0.03)
    assert "3 kg" in tts.spoken[-1]
    assert "2.8" not in tts.spoken[-1]
    await orch.close()


@pytest.mark.asyncio
async def test_9_submission_declined_keeps_unsubmitted_draft() -> None:
    """Test 9: Worker says NO to submission -> draft retained, NOT marked completed."""
    pipeline, orch, tts, emitted = await _make_session("sess_edit_9")

    await orch.handle_text_input("Newborn visit, weight is 2.8 kg.")
    await asyncio.sleep(0.03)
    await orch.handle_text_input("Finish this visit.")
    await asyncio.sleep(0.03)
    await orch.handle_text_input("No")  # skip readback
    await asyncio.sleep(0.03)
    assert pipeline.sm.state == ConversationState.ASK_SUBMISSION_CONFIRMATION

    await orch.handle_text_input("No")  # decline submission
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.status == VisitStatus.DRAFT
    assert pipeline.sm.state == ConversationState.CONTINUE_CONVERSATION
    assert not any(e["type"] in ("visit_confirmed", "visit_committed") for e in emitted)
    assert "unsubmitted draft" in tts.spoken[-1].lower()
    await orch.close()


@pytest.mark.asyncio
async def test_ambiguous_bare_number_clarification_and_visual_patch() -> None:
    """Section 3 & 4: Ambiguous bare number triggers confirmation; visual patch updates same backend draft."""
    pipeline, orch, tts, _emitted = await _make_session("sess_edit_amb")

    await orch.handle_text_input("Newborn visit, weight is 2.2 kg.")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.weight_kg == 2.2

    # Bare unitless number "2.8" asks confirmation instead of guessing
    await orch.handle_text_input("2.8")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.weight_kg == 2.2
    assert "update the previously recorded weight to 2.8 kilograms?" in tts.spoken[-1]

    await orch.handle_text_input("Yes")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.weight_kg == 2.8

    # Visual field patch updates the exact same backend draft
    await pipeline.handle_visual_patch({"weight_kg": 3.2, "next_visit_date": "2026-12-05"}, orch)
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.weight_kg == 3.2
    assert pipeline.sm.visit.next_visit_date == "2026-12-05"
    await orch.close()
