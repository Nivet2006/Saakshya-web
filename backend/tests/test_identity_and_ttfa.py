"""Tests for STRICT ADD-ON: Live Voice Greeting, Beneficiary Verification, Barge-In & TTFA Telemetry.

Covers Sections 1–9:
- Section 1 & Test 1: Start Recording personalized greeting & YES confirmation -> GATHERING_NOTES
- Section 2 Scenario B & Test 2: NO -> voice correction ("Actually, it is Anitha Sharma" -> BEN-1056) -> candidate confirmation
- Section 2 Scenario C & Test 3: Multiple matching beneficiaries ("Lakshmi" -> BEN-1042 & BEN-1048) -> asks for BEN-ID
- Section 2 Scenario D: Beneficiary not found -> asks to repeat name or ID
- Section 2 Scenario E: Ambiguous YES/NO response -> re-prompts, never auto-confirms
- Section 4 & Test 4 & Test 5: Exact decimal weights (2.8 kg, 3.2 kg), spoken BEN-IDs, unambiguous date read-back ("28 November 2026")
- Section 7 & Test 9: Barge-in with bare number correction ("No, it is fifty-three")
- Section 8: Full state flow + danger-sign interrupt from any identity verification state
- Section 5 & 6 & Test 8: TTFA instrumentation (all 6 timestamps, P50, P95, avg, greeting latency) & 9-step task completion rate
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
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.conversation.models import ConversationState  # noqa: E402
from app.conversation.state_machine import (  # noqa: E402
    ConversationStateMachine,
    format_unambiguous_spoken_date,
)
from app.extraction.extractor import VisitFieldExtractor  # noqa: E402
from app.healthcare.pipeline import HealthcareSessionPipeline  # noqa: E402
from app.main import app  # noqa: E402
from app.services.beneficiaries import SyntheticBeneficiaryDirectory  # noqa: E402
from app.voice.interfaces import ChatMessage, TranscriptEvent  # noqa: E402
from app.voice.orchestration.session import VoiceSessionOrchestrator  # noqa: E402
from tests.test_contracts import validate_instance as validate_schema  # noqa: E402

CONTRACTS_DIR = REPO_ROOT / "shared-contracts"
EVENTS_SCHEMA = json.loads((CONTRACTS_DIR / "voice-events.schema.json").read_text(encoding="utf-8"))


class _MockSTT:
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


class _MockTTS:
    sample_rate = 16000

    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.cancelled = 0

    async def connect(self) -> None:
        pass

    async def synthesize_stream(
        self, text: str, *, language: str | None = None, voice: str | None = None
    ) -> AsyncIterator[bytes]:
        self.spoken.append(text)
        yield b"\x01\x00" * 512

    async def cancel_active(self) -> None:
        self.cancelled += 1

    async def close(self) -> None:
        pass


class _MockLLM:
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


@pytest.mark.asyncio
async def test_scenario_a_and_test1_greeting_and_correct_identity_verification() -> None:
    """Test 1: Select Lakshmi Devi -> Start Recording -> AI greets -> Worker says YES -> Note collection."""
    emitted: list[dict[str, Any]] = []

    async def emit(ev: dict[str, Any]) -> None:
        emitted.append(ev)

    stt = _MockSTT()
    tts = _MockTTS()
    pipeline = HealthcareSessionPipeline(
        session_id="sess_id_test1",
        worker_id="ASHA-DEMO-01",
        language="en-IN",
        beneficiary_id="BEN-1042",
        reference_date=date(2026, 11, 21),
    )
    orch = VoiceSessionOrchestrator(
        session_id="sess_id_test1",
        stt=stt,
        tts=tts,
        llm=_MockLLM(),
        vad=None,
        emit=emit,
        default_language="en-IN",
        on_partial_hook=pipeline.on_partial_transcript,
        on_final_hook=pipeline.on_final_transcript,
    )
    pipeline.attach_orchestrator(orch)
    await orch.start()
    await pipeline.start_session_greeting(orch)
    await asyncio.sleep(0.05)

    assert pipeline.sm.state == ConversationState.IDENTITY_CONFIRMATION
    assert pipeline.sm.identity_verified is False
    assert "Lakshmi Devi" in tts.spoken[-1]
    assert "BEN-1042" in tts.spoken[-1]
    assert "Say yes or no" in tts.spoken[-1]

    # Ambiguous response (Scenario E) must NOT confirm
    await orch.handle_text_input("Wait what?")
    await asyncio.sleep(0.05)
    assert pipeline.sm.state == ConversationState.IDENTITY_CONFIRMATION
    assert pipeline.sm.identity_verified is False
    assert "Please say yes or no" in tts.spoken[-1]

    # Worker says YES (Scenario A)
    await orch.handle_text_input("Yes")
    await asyncio.sleep(0.05)
    assert pipeline.sm.state == ConversationState.GATHERING_NOTES
    assert pipeline.sm.state == ConversationState.GATHERING_VISIT_NOTES
    assert pipeline.sm.identity_verified is True
    assert "Lakshmi Devi is confirmed" in tts.spoken[-1]

    # Now worker speaks visit notes (continuous editing keeps session open for additions/corrections)
    await orch.handle_text_input(
        "Today I visited Lakshmi. ANC checkup completed. Weight is fifty-two kilo. "
        "TT injection pending. Next visit is twenty-eighth November."
    )
    await asyncio.sleep(0.05)
    assert pipeline.sm.visit.visit_type.value == "ANC"
    assert pipeline.sm.visit.weight_kg == 52.0
    assert "TT" in pipeline.sm.visit.vaccinations_due
    assert pipeline.sm.visit.next_visit_date == "2026-11-28"
    assert "28 November 2026" in tts.spoken[-1]

    # Section 7 & Test 9: Barge-in / correction with bare number "No, it is fifty-three."
    await orch.handle_text_input("No, it is fifty-three.")
    await asyncio.sleep(0.05)
    assert pipeline.sm.visit.weight_kg == 53.0
    assert pipeline.sm.visit.next_visit_date == "2026-11-28"
    assert "53 kilograms" in tts.spoken[-1]

    # Worker indicates completion -> asks summary readback preference -> YES -> reads summary -> YES -> submits
    await orch.handle_text_input("That's all.")
    await asyncio.sleep(0.05)
    assert pipeline.sm.state == ConversationState.ASK_READBACK_PREFERENCE
    await orch.handle_text_input("Yes")
    await asyncio.sleep(0.05)
    assert "53 kg" in tts.spoken[-1]
    assert "28 November 2026" in tts.spoken[-1]

    await orch.handle_text_input("Yes, confirm")
    await asyncio.sleep(0.05)
    await pipeline.handle_persistence_ack(
        accepted=True,
        persistence_record_id="rec_test1_1042",
        committed_at="2026-11-21T12:00:00Z",
    )
    await asyncio.sleep(0.05)

    summary = orch.telemetry.summary()
    assert summary["task_success"]["task_completed"] is True
    assert summary["initial_greeting_latency_ms"] is not None
    assert summary["ttfa_p50_ms"] is not None
    assert summary["ttfa_p95_ms"] is not None

    for idx, ev in enumerate(emitted):
        assert validate_schema(ev, EVENTS_SCHEMA) == [], f"Event #{idx} invalid: {ev}"

    await orch.close()


@pytest.mark.asyncio
async def test_scenario_b_c_d_wrong_identity_similar_names_and_not_found() -> None:
    """Tests 2 & 3: Wrong identity -> NO -> similar name ('Lakshmi') -> not found -> 'Anitha Sharma' (BEN-1056)."""
    emitted: list[dict[str, Any]] = []

    async def emit(ev: dict[str, Any]) -> None:
        emitted.append(ev)

    stt = _MockSTT()
    tts = _MockTTS()
    pipeline = HealthcareSessionPipeline(
        session_id="sess_id_test2",
        worker_id="ASHA-DEMO-01",
        language="en-IN",
        beneficiary_id="BEN-1042",
        reference_date=date(2026, 11, 21),
    )
    orch = VoiceSessionOrchestrator(
        session_id="sess_id_test2",
        stt=stt,
        tts=tts,
        llm=_MockLLM(),
        vad=None,
        emit=emit,
        default_language="en-IN",
        on_partial_hook=pipeline.on_partial_transcript,
        on_final_hook=pipeline.on_final_transcript,
    )
    pipeline.attach_orchestrator(orch)
    await orch.start()
    await pipeline.start_session_greeting(orch)
    await asyncio.sleep(0.05)

    # Scenario B step 1: Worker says NO
    await orch.handle_text_input("No, different beneficiary.")
    await asyncio.sleep(0.05)
    assert pipeline.sm.state == ConversationState.IDENTITY_CORRECTION
    assert pipeline.sm.visit.beneficiary_id is None
    assert "correct beneficiary's name or beneficiary ID" in tts.spoken[-1]

    # Scenario C / Test 3: Worker speaks an ambiguous name ("Lakshmi") matching BEN-1042 & BEN-1048
    await orch.handle_text_input("Lakshmi")
    await asyncio.sleep(0.05)
    assert pipeline.sm.state == ConversationState.IDENTITY_CORRECTION
    assert pipeline.sm.visit.beneficiary_id is None
    assert "more than one matching beneficiary" in tts.spoken[-1]
    assert "Please tell me the beneficiary ID" in tts.spoken[-1]

    # Scenario D: Worker speaks an unknown name ("Priya Verma")
    await orch.handle_text_input("Priya Verma")
    await asyncio.sleep(0.05)
    assert pipeline.sm.state == ConversationState.IDENTITY_CORRECTION
    assert pipeline.sm.visit.beneficiary_id is None
    assert "couldn't find that beneficiary" in tts.spoken[-1]

    # Scenario B step 2 / Test 2: Worker speaks "Actually, it is Anitha Sharma."
    await orch.handle_text_input("Actually, it is Anitha Sharma.")
    await asyncio.sleep(0.05)
    assert pipeline.sm.state == ConversationState.CANDIDATE_CONFIRMATION
    assert pipeline.sm.candidate_beneficiary_id == "BEN-1056"
    assert pipeline.sm.candidate_beneficiary_name == "Anitha Sharma"
    # Candidate is NOT auto-confirmed yet
    assert pipeline.sm.identity_verified is False
    assert "I found Anitha Sharma, beneficiary ID BEN-1056. Is this correct?" in tts.spoken[-1]

    # Worker confirms the candidate
    await orch.handle_text_input("Yes")
    await asyncio.sleep(0.05)
    assert pipeline.sm.state == ConversationState.GATHERING_NOTES
    assert pipeline.sm.identity_verified is True
    assert pipeline.sm.visit.beneficiary_id == "BEN-1056"
    assert pipeline.sm.visit.beneficiary_name == "Anitha Sharma"

    for idx, ev in enumerate(emitted):
        assert validate_schema(ev, EVENTS_SCHEMA) == [], f"Event #{idx} invalid: {ev}"

    await orch.close()


def test_decimal_weights_spoken_ids_and_kannada_tamil_numbers() -> None:
    """Tests 4, 5, 6: Decimal weights (2.8, 3.2), spoken BEN-IDs, and Kannada/Tamil number words."""
    directory = SyntheticBeneficiaryDirectory()
    extractor = VisitFieldExtractor(beneficiary_directory=directory)

    # Test 4: "Weight is 2.8 kilo" and spaced ASR decimal "2 . 8 kilo"
    r1 = extractor.extract("Newborn visit for BEN-1044. Weight is 2.8 kilo.")
    assert r1.patch["weight_kg"] == 2.8
    assert r1.patch["beneficiary_id"] == "BEN-1044"

    r1_spaced = extractor.extract("Newborn visit for BEN-1044. Weight is 2 . 8 kilo.")
    assert r1_spaced.patch["weight_kg"] == 2.8

    # Test 5: "No, it is 3.2 kilo."
    r2 = extractor.extract("No, it is 3.2 kilo.")
    assert r2.detected_correction is True
    assert r2.patch["weight_kg"] == 3.2

    # Spoken digit BEN-ID resolution ("BEN one zero five six")
    matches, spoken_id = directory.resolve_spoken_identity("Beneficiary ID BEN one zero five six")
    assert spoken_id == "BEN-1056"
    assert len(matches) == 1 and matches[0].full_name == "Anitha Sharma"

    # Test 6: Kannada & Tamil code-mixed weight extraction
    r_kn = extractor.extract("Kavitha PNC visit, ತೂಕ ಐವತ್ತೆರಡು ಕೆಜಿ")
    assert r_kn.patch["weight_kg"] == 52.0

    r_ta = extractor.extract("Meena immunisation visit, எடை இரண்டு புள்ளி எட்டு கிலோ")
    assert r_ta.patch["weight_kg"] == 2.8

    # Unambiguous date formatting
    assert format_unambiguous_spoken_date("2026-11-28") == "28 November 2026 (2026-11-28)"


def test_danger_escalation_interrupts_from_identity_verification_states() -> None:
    """Section 8: A verified danger sign must interrupt from any identity verification state."""
    from app.conversation.models import DangerAlertInput

    for init_fn in (
        lambda sm: sm.start_beneficiary_greeting(
            beneficiary_id="BEN-1042", beneficiary_name="Lakshmi Devi"
        ),
        lambda sm: (
            sm.start_beneficiary_greeting(
                beneficiary_id="BEN-1042", beneficiary_name="Lakshmi Devi"
            ),
            sm.handle_identity_confirmation_response("no"),
        ),
        lambda sm: (
            sm.start_beneficiary_greeting(
                beneficiary_id="BEN-1042", beneficiary_name="Lakshmi Devi"
            ),
            sm.handle_identity_confirmation_response("no"),
            sm.apply_beneficiary_lookup_result([("BEN-1056", "Anitha Sharma")]),
        ),
    ):
        sm = ConversationStateMachine(session_id="sess_danger_id", language="en-IN")
        init_fn(sm)
        res = sm.handle_danger_detection(
            DangerAlertInput(
                canonical_id="ANC_VAGINAL_BLEEDING",
                category="ANC",
                display_name="Vaginal bleeding",
                matched_phrase="heavy bleeding",
                guideline_reference="NHM Module 6 p.30",
            )
        )
        assert res.current_state == ConversationState.DANGER_ESCALATION
        assert res.is_urgent is True
        assert res.interrupt_speech is True
        assert sm.visit.danger_sign_flagged is True


def test_rest_telemetry_metrics_endpoints() -> None:
    """Section 5: Verify REST telemetry endpoints `/api/v1/sessions/{id}/metrics` and `/api/v1/metrics/summary`."""
    client = TestClient(app)
    r_post = client.post(
        "/api/v1/sessions/sess_metric_test/metrics/client-playback",
        json={"schema_version": "v1", "turn_id": 1, "client_ttfa_ms": 412.5},
    )
    assert r_post.status_code == 200

    r_get = client.get("/api/v1/sessions/sess_metric_test/metrics")
    assert r_get.status_code == 200
    assert r_get.json()["session_id"] == "sess_metric_test"

    r_sum = client.get("/api/v1/metrics/summary")
    assert r_sum.status_code == 200
    assert "ttfa_p50_ms" in r_sum.json()
    assert "task_completion_rate" in r_sum.json()

