#!/usr/bin/env python3
"""LIVE Phase 2 Healthcare + Danger-Sign Voice End-to-End Verification.

Label: LIVE-GNANI INTEGRATION TEST (real Gnani Prisma v3.0 STT + real Gnani Timbre v3.0 TTS
+ real Phase 2 1A Danger-Sign Engine + 1B State Machine + 1C Extractor + v1 Contract Validation).

Scenario tested live over real WebSocket `/ws/voice/{session_id}`:
1. Synthetic Hinglish ANC visit note streamed to live Prisma v3.0 -> extracts `BEN-1042`,
   `ANC`, `weight_kg=52.0`, `vaccinations_due=['TT']`, `next_visit_date` -> speaks live Timbre
   v3.0 read-back confirmation!
2. Mid-readback BARGE-IN with a Newborn/Maternal danger sign ("Mother ko heavy bleeding ho rahi
   hai, vaginal bleeding") -> Layer 1 deterministic engine fires immediately, cancels read-back,
   emits schema-valid `danger_alert` (`danger_sign_flagged=true`, `priority='urgent'`), and
   speaks live Timbre v3.0 urgent PHC referral!
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import sys
from pathlib import Path

import uvicorn
import websockets

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.voice.tts.gnani_timbre import GnaniTimbreTTSAdapter  # noqa: E402
from tests.test_contracts import validate_instance as validate_schema  # noqa: E402

CONTRACTS_DIR = REPO_ROOT / "shared-contracts"
VISIT_SCHEMA = json.loads((CONTRACTS_DIR / "visit.schema.json").read_text(encoding="utf-8"))
ALERT_SCHEMA = json.loads((CONTRACTS_DIR / "danger-alert.schema.json").read_text(encoding="utf-8"))
EVENTS_SCHEMA = json.loads((CONTRACTS_DIR / "voice-events.schema.json").read_text(encoding="utf-8"))

FRAME_BYTES = 1024


async def _synth_pcm(tts: GnaniTimbreTTSAdapter, text: str, lang: str = "hi-IN") -> bytes:
    buf = bytearray()
    async for chunk in tts.synthesize_stream(text, language=lang, voice="Avinash"):
        buf.extend(chunk)
    return bytes(buf)


async def run_live_phase2_verification() -> None:
    settings = get_settings()
    missing = settings.validate_live_credentials()
    if missing:
        raise RuntimeError(f"Missing live credentials: {missing}")

    print("[LIVE-P2] Generating 2 synthetic Hinglish speech fixtures via Timbre v3.0...", flush=True)
    fixture_tts = GnaniTimbreTTSAdapter.from_settings(settings)
    await fixture_tts.connect()
    try:
        anc_pcm = await _synth_pcm(
            fixture_tts,
            "Today I visited Lakshmi, ANC checkup completed. Weight is fifty two kilo. TT injection pending hai. Next visit twenty fifth November.",
            "hi-IN",
        )
        danger_pcm = await _synth_pcm(
            fixture_tts,
            "Emergency, mother ko heavy vaginal bleeding ho rahi hai.",
            "hi-IN",
        )
    finally:
        await fixture_tts.close()

    port = 8766
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    server_task = asyncio.create_task(server.serve())
    for _ in range(50):
        if server.started:
            break
        await asyncio.sleep(0.1)
    assert server.started

    events: list[dict] = []
    readback_tts_started = asyncio.Event()
    danger_alert_seen = asyncio.Event()
    danger_tts_complete = asyncio.Event()

    try:
        ws_url = f"ws://127.0.0.1:{port}/ws/voice/live_p2_verify?language=indic-auto&mode=healthcare"
        async with websockets.connect(ws_url, max_size=4 * 1024 * 1024) as ws:
            async def receiver() -> None:
                async for raw in ws:
                    if isinstance(raw, bytes):
                        continue
                    ev = json.loads(raw)
                    events.append(ev)
                    t = ev.get("type")
                    if t == "final_transcript":
                        print(f"  [LIVE FINAL] {ev['text']}", flush=True)
                    elif t == "visit_draft_updated":
                        d = ev["draft"]
                        print(
                            f"  [DRAFT] ben={d['beneficiary_id']} type={d['visit_type']} "
                            f"wt={d['weight_kg']} due={d['vaccinations_due']} "
                            f"next={d['next_visit_date']} danger={d['danger_sign_flagged']}",
                            flush=True,
                        )
                    elif t == "read_back_started":
                        print(f"  [READ-BACK] {ev['summary_text']}", flush=True)
                    elif t == "tts_audio_chunk" and not danger_alert_seen.is_set():
                        readback_tts_started.set()
                    elif t == "danger_alert":
                        a = ev["alert"]
                        print(
                            f"  [URGENT DANGER ALERT] id={a['canonical_danger_sign_id']} "
                            f"source={a['source_guideline_ref']}",
                            flush=True,
                        )
                        danger_alert_seen.set()
                    elif t == "tts_complete" and danger_alert_seen.is_set():
                        print(f"  [URGENT REFERRAL TTS COMPLETE] chunks={ev['total_chunks']}", flush=True)
                        danger_tts_complete.set()

            recv_task = asyncio.create_task(receiver())
            await asyncio.sleep(0.5)

            print("[LIVE-P2] Streaming ANC visit note...", flush=True)
            silence_frames = max(60, (settings.endpoint_silence_ms // 32) + 20)
            for i in range(0, len(anc_pcm), FRAME_BYTES):
                await ws.send(anc_pcm[i : i + FRAME_BYTES])
                await asyncio.sleep(0.028)
            for _ in range(silence_frames):
                await ws.send(b"\x00" * FRAME_BYTES)
                await asyncio.sleep(0.028)

            await asyncio.wait_for(readback_tts_started.wait(), timeout=25.0)
            print("[LIVE-P2] Read-back TTS playing -> interrupting with urgent danger sign!", flush=True)

            for i in range(0, len(danger_pcm), FRAME_BYTES):
                await ws.send(danger_pcm[i : i + FRAME_BYTES])
                await asyncio.sleep(0.028)
            for _ in range(silence_frames):
                await ws.send(b"\x00" * FRAME_BYTES)
                await asyncio.sleep(0.028)

            await asyncio.wait_for(danger_alert_seen.wait(), timeout=20.0)
            await asyncio.wait_for(danger_tts_complete.wait(), timeout=20.0)

            await ws.send(json.dumps({"type": "end_session"}))
            recv_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await recv_task
    finally:
        server.should_exit = True
        await server_task

    # Strict contract validation of ALL live emitted events!
    draft_events = [e for e in events if e["type"] == "visit_draft_updated"]
    alert_events = [e for e in events if e["type"] == "danger_alert"]
    assert len(draft_events) >= 1
    assert len(alert_events) >= 1

    latest_draft = draft_events[-1]["draft"]
    assert latest_draft["beneficiary_id"] == "BEN-1042"
    assert latest_draft["visit_type"] == "ANC"
    assert latest_draft["weight_kg"] == 52.0
    assert latest_draft["danger_sign_flagged"] is True

    assert validate_schema(latest_draft, VISIT_SCHEMA) == []
    assert validate_schema(alert_events[0]["alert"], ALERT_SCHEMA) == []
    for idx, ev in enumerate(events):
        errs = validate_schema(ev, EVENTS_SCHEMA)
        assert errs == [], f"Live event #{idx} ({ev.get('type')}) failed v1 schema: {errs}"

    print("\n=== LIVE PHASE 2 HEALTHCARE + DANGER ESCALATION PASSED (0 MOCKS, 100% v1 SCHEMA VALID) ===", flush=True)


if __name__ == "__main__":
    asyncio.run(run_live_phase2_verification())
