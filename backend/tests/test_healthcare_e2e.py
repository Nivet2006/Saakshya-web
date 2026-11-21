"""Integrated Phase 2 Healthcare Pipeline Tests (1A + 1B + 1C + REST + v1 Schema Parity).

Label: UNIT / INTEGRATION (mocked STT/TTS transport, real deterministic 1A/1B/1C engines,
real FastAPI app, real Draft 2020-12 JSON Schema validation against `shared-contracts/`).
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

from app.healthcare.pipeline import HealthcareSessionPipeline, session_registry  # noqa: E402
from app.main import app  # noqa: E402
from app.voice.interfaces import ChatMessage, TranscriptEvent  # noqa: E402
from app.voice.orchestration.session import VoiceSessionOrchestrator  # noqa: E402
from tests.test_contracts import validate_instance as validate_schema  # noqa: E402

CONTRACTS_DIR = REPO_ROOT / "shared-contracts"
VISIT_SCHEMA = json.loads((CONTRACTS_DIR / "visit.schema.json").read_text(encoding="utf-8"))
ALERT_SCHEMA = json.loads((CONTRACTS_DIR / "danger-alert.schema.json").read_text(encoding="utf-8"))
EVENTS_SCHEMA = json.loads((CONTRACTS_DIR / "voice-events.schema.json").read_text(encoding="utf-8"))


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
        return "Namaste, please share the visit notes."


@pytest.mark.asyncio
async def test_full_anc_visit_readback_correction_confirmation_and_schema_parity() -> None:
    """Tests the exact MASTER.md §6 workflow and validates EVERY emitted event against v1 schemas."""
    emitted: list[dict[str, Any]] = []

    async def emit(ev: dict[str, Any]) -> None:
        emitted.append(ev)

    stt = _DummySTT()
    tts = _DummyTTS()
    pipeline = HealthcareSessionPipeline(
        session_id="sess_e2e_anc",
        worker_id="ASHA-DEMO-01",
        language="en-IN",
        reference_date=date(2026, 11, 21),
    )
    orch = VoiceSessionOrchestrator(
        session_id="sess_e2e_anc",
        stt=stt,
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

    # 1. Worker dictates Hinglish ANC note
    await orch.handle_text_input(
        "Visited Lakshmi today. ANC checkup done. Weight fifty two kilo. "
        "TT injection pending hai. IFA goli regularly nahi le rahi. Next visit 25 November."
    )
    await asyncio.sleep(0.05)

    visit = pipeline.current_visit_contract()
    assert validate_schema(visit, VISIT_SCHEMA) == []
    assert visit["beneficiary_id"] == "BEN-1042"
    assert visit["visit_type"] == "ANC"
    assert visit["weight_kg"] == 52.0
    assert "TT" in visit["vaccinations_due"]
    assert visit["next_visit_date"] == "2026-11-25"
    assert visit["status"] == "draft"
    assert any(e["type"] == "read_back_started" for e in emitted)

    # 2. Worker corrects ONLY the next visit date
    await orch.handle_text_input("No, next visit is 28 November.")
    await asyncio.sleep(0.05)

    visit_after_corr = pipeline.current_visit_contract()
    assert validate_schema(visit_after_corr, VISIT_SCHEMA) == []
    assert visit_after_corr["next_visit_date"] == "2026-11-28"
    # All other fields preserved!
    assert visit_after_corr["beneficiary_id"] == "BEN-1042"
    assert visit_after_corr["weight_kg"] == 52.0
    assert "TT" in visit_after_corr["vaccinations_due"]
    assert visit_after_corr["status"] == "draft"
    assert any(e["type"] == "correction_applied" for e in emitted)

    # 3. Worker confirms explicitly -> status='confirmed' + persistence_requested
    await orch.handle_text_input("Yes")
    await asyncio.sleep(0.05)

    visit_confirmed = pipeline.current_visit_contract()
    assert validate_schema(visit_confirmed, VISIT_SCHEMA) == []
    assert visit_confirmed["status"] == "confirmed"
    assert visit_confirmed["confirmed_at"] is not None
    assert visit_confirmed["committed_at"] is None
    assert any(e["type"] == "visit_confirmed" for e in emitted)
    assert any(e["type"] == "persistence_requested" for e in emitted)

    # 4. Agent 3 acknowledges durable persistence -> status='committed'
    ack_res = await pipeline.handle_persistence_ack(
        accepted=True,
        persistence_record_id="supa_vis_e2e_1042",
        committed_at="2026-11-21T10:00:00Z",
    )
    await asyncio.sleep(0.05)
    assert ack_res["status"] == "committed"
    visit_committed = pipeline.current_visit_contract()
    assert validate_schema(visit_committed, VISIT_SCHEMA) == []
    assert visit_committed["status"] == "committed"
    assert visit_committed["persistence_record_id"] == "supa_vis_e2e_1042"
    assert any(e["type"] == "visit_committed" for e in emitted)

    # 5. Validate EVERY emitted server event against `shared-contracts/voice-events.schema.json`!
    for idx, ev in enumerate(emitted):
        errs = validate_schema(ev, EVENTS_SCHEMA)
        assert errs == [], f"Event #{idx} ({ev.get('type')}) failed v1 schema validation: {errs}"

    await orch.close()


@pytest.mark.asyncio
async def test_partial_transcript_danger_sign_interrupts_immediately_and_persists() -> None:
    """Layer 1 danger sign on a PARTIAL transcript interrupts immediately and never gets lost."""
    emitted: list[dict[str, Any]] = []

    async def emit(ev: dict[str, Any]) -> None:
        emitted.append(ev)

    stt = _DummySTT()
    tts = _DummyTTS()
    pipeline = HealthcareSessionPipeline(
        session_id="sess_e2e_danger",
        worker_id="ASHA-DEMO-01",
        language="hi-IN",
        beneficiary_id="BEN-1044",
        reference_date=date(2026, 11, 21),
    )
    orch = VoiceSessionOrchestrator(
        session_id="sess_e2e_danger",
        stt=stt,
        tts=tts,
        llm=_DummyLLM(),
        vad=None,
        emit=emit,
        default_language="hi-IN",
        on_partial_hook=pipeline.on_partial_transcript,
        on_final_hook=pipeline.on_final_transcript,
    )
    pipeline.attach_orchestrator(orch)
    await orch.start()

    # Partial transcript arrives with Newborn chest indrawing
    await stt.q.put(
        TranscriptEvent(
            event_type="partial",
            text="Baby ka chest indrawing ho raha hai",
            is_final=False,
            language_code="hi-IN",
            utterance_id="u_danger",
            seq=1,
        )
    )
    await asyncio.sleep(0.08)

    danger_events = [e for e in emitted if e["type"] == "danger_alert"]
    assert len(danger_events) >= 1
    alert = danger_events[0]["alert"]
    assert validate_schema(alert, ALERT_SCHEMA) == []
    assert alert["danger_sign_flagged"] is True
    assert alert["priority"] == "urgent"
    assert alert["beneficiary_id"] == "BEN-1044"
    assert "PHC" in alert["referral_message"] or "पीएचसी" in alert["referral_message"]
    assert tts.cancelled >= 1

    # Worker continues and records newborn weight -> danger alert MUST remain preserved!
    await orch.handle_text_input("Newborn visit, weight is 2.6 kilo.")
    await asyncio.sleep(0.08)
    visit = pipeline.current_visit_contract()
    assert validate_schema(visit, VISIT_SCHEMA) == []
    assert visit["danger_sign_flagged"] is True
    assert len(visit["danger_signs"]) >= 1
    assert visit["weight_kg"] == 2.6
    assert any(a["action_type"] == "phc_referral" and a["priority"] == "urgent" for a in visit["follow_up_actions"])

    # Every emitted event conforms to v1 voice-events schema
    for idx, ev in enumerate(emitted):
        errs = validate_schema(ev, EVENTS_SCHEMA)
        assert errs == [], f"Danger event #{idx} ({ev.get('type')}) failed v1 schema validation: {errs}"

    await orch.close()


def test_rest_phase2_endpoints_match_v1_contracts() -> None:
    """Verify live REST endpoints `/api/v1/danger-signs/check`, `/visit`, and `/persistence-ack`."""
    client = TestClient(app)

    # 1. Standalone deterministic danger check endpoint
    r = client.post(
        "/api/v1/danger-signs/check",
        json={
            "schema_version": "v1",
            "text": "Baby ka chest indrawing ho raha hai aur tez saans chal rahi hai",
            "language": "hi-IN",
            "visit_type": "Newborn",
            "beneficiary_id": "BEN-1044",
            "subject_hint": "newborn",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["danger_sign_flagged"] is True
    assert len(body["alerts"]) >= 1
    for alert in body["alerts"]:
        assert validate_schema(alert, ALERT_SCHEMA) == []

    # 2. Session visit endpoint + unconfirmed draft commit guard (409)
    r_sess = client.post(
        "/api/v1/sessions",
        json={"language": "hi-IN", "beneficiary_id": "BEN-1042", "worker_id": "ASHA-DEMO-01"},
    )
    assert r_sess.status_code == 200
    sid = r_sess.json()["session_id"]

    r_visit = client.get(f"/api/v1/sessions/{sid}/visit")
    assert r_visit.status_code == 200
    visit_body = r_visit.json()
    assert validate_schema(visit_body["visit"], VISIT_SCHEMA) == []
    assert visit_body["visit"]["status"] == "draft"

    # Attempting to persistence-ack an unconfirmed draft MUST fail with 409!
    r_ack_draft = client.post(
        f"/api/v1/sessions/{sid}/persistence-ack",
        json={
            "schema_version": "v1",
            "visit_id": visit_body["visit"]["visit_id"],
            "accepted": True,
            "persistence_record_id": "supa_should_fail",
        },
    )
    assert r_ack_draft.status_code == 409
    assert r_ack_draft.json()["code"] == "INVALID_STATE_TRANSITION"

    # 3. Unknown beneficiary returns contract ErrorResponse 404
    r_bad = client.post("/api/v1/sessions", json={"beneficiary_id": "BEN-9999"})
    assert r_bad.status_code == 404
    assert r_bad.json()["code"] == "BENEFICIARY_NOT_FOUND"
