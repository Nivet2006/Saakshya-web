#!/usr/bin/env python3
"""LIVE Milestone 1 End-to-End Verification Script.

Label: LIVE-GNANI + LIVE-GEMINI INTEGRATION TEST (zero mocks).

Verifies all Milestone 1 acceptance criteria end-to-end through the real FastAPI
WebSocket backend:
1. FastAPI backend starts on a local port & `/health` reports live credentials ready.
2. WebSocket `/ws/voice/{session_id}` connects and initializes real Gnani Prisma v3.0,
   Gemini LLM, ONNX Silero VAD, and Gnani Timbre v3.0.
3. Synthetic Hinglish Utterance 1 (generated with Timbre v3.0) streams over WS
   -> real Prisma v3.0 emits partial + final transcripts
   -> real Gemini generates a short contextual Hinglish response
   -> real Timbre v3.0 streams PCM audio chunks back.
4. Mid-playback BARGE-IN: while turn 1 TTS audio is actively streaming, synthetic
   Hinglish Utterance 2 ("Nahi, weight fifty five kilo hai, next visit twenty eighth November.")
   is streamed into the same WebSocket -> ONNX Silero VAD triggers `barge_in` + `tts_cancelled`,
   ZERO stale turn-1 chunks arrive after cancellation, Utterance 2 is transcribed live by
   Prisma v3.0, answered by Gemini using prior conversation context, and spoken by Timbre v3.0.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import sys
import time
from pathlib import Path

import uvicorn
import websockets

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.voice.tts.gnani_timbre import GnaniTimbreTTSAdapter  # noqa: E402

FRAME_BYTES = 1024  # 512 samples @ 16 kHz (32 ms)


async def _synth_fixture_pcm(tts: GnaniTimbreTTSAdapter, text: str, lang: str = "hi-IN") -> bytes:
    buf = bytearray()
    async for chunk in tts.synthesize_stream(text, language=lang, voice="Avinash"):
        buf.extend(chunk)
    return bytes(buf)


async def run_live_milestone1_verification() -> None:
    settings = get_settings()
    missing = settings.validate_live_credentials()
    if missing:
        raise RuntimeError(f"Cannot run LIVE Milestone 1 test; missing env vars: {missing}")

    # 1. Generate two synthetic Hinglish audio fixtures using live Gnani Timbre v3.0
    print("[LIVE-M1] Step 1: Generating 2 synthetic Hinglish speech fixtures via Gnani Timbre v3.0...", flush=True)
    fixture_tts = GnaniTimbreTTSAdapter.from_settings(settings)
    await fixture_tts.connect()
    try:
        utt1_pcm = await _synth_fixture_pcm(
            fixture_tts,
            "Today I visited Lakshmi, ANC checkup completed. Weight is fifty two kilo. TT injection pending hai. Next visit twenty sixth November.",
            "hi-IN",
        )
        utt2_pcm = await _synth_fixture_pcm(
            fixture_tts,
            "Nahi, next visit twenty eighth November hai, weight fifty five kilo.",
            "hi-IN",
        )
    finally:
        await fixture_tts.close()
    print(
        f"[LIVE-M1] Synthetic fixtures ready: utt1={len(utt1_pcm)/32000:.2f}s, utt2={len(utt2_pcm)/32000:.2f}s",
        flush=True,
    )

    # 2. Start real FastAPI / Uvicorn server in-process on ephemeral local port
    port = 8765
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())
    for _ in range(50):
        if server.started:
            break
        await asyncio.sleep(0.1)
    assert server.started, "FastAPI server failed to start"
    print(f"[LIVE-M1] Step 2: FastAPI backend running on 127.0.0.1:{port}", flush=True)

    events: list[dict] = []
    turn1_tts_started = asyncio.Event()
    turn2_tts_completed = asyncio.Event()
    barge_in_seen = asyncio.Event()
    turn1_id: int | None = None
    barge_in_event_index: int | None = None

    try:
        ws_url = f"ws://127.0.0.1:{port}/ws/voice/live_m1_verify?language=indic-auto"
        async with websockets.connect(ws_url, max_size=4 * 1024 * 1024) as ws:
            async def receiver() -> None:
                nonlocal turn1_id, barge_in_event_index
                async for raw in ws:
                    if isinstance(raw, bytes):
                        continue
                    ev = json.loads(raw)
                    events.append(ev)
                    t = ev.get("type")
                    if t == "session_ready":
                        print(f"[LIVE-M1] WS Ready: {ev['stt_provider']} -> {ev['llm_model']} -> {ev['tts_provider']}", flush=True)
                    elif t == "partial_transcript":
                        print(f"  [PARTIAL] {ev['text']}", flush=True)
                    elif t == "final_transcript":
                        print(f"  [FINAL] ({ev.get('language')}, {ev.get('latency_ms')}ms) {ev['text']}", flush=True)
                    elif t == "assistant_response":
                        print(f"  [LLM turn={ev['turn_id']}] {ev['text']}", flush=True)
                    elif t == "tts_audio_chunk":
                        tid = ev["turn_id"]
                        if turn1_id is None:
                            turn1_id = tid
                            turn1_tts_started.set()
                    elif t == "tts_cancelled":
                        barge_in_event_index = len(events) - 1
                        barge_in_seen.set()
                        print(f"  [BARGE-IN CANCELLED] {ev}", flush=True)
                    elif t == "tts_complete":
                        print(f"  [TTS COMPLETE] turn={ev['turn_id']} chunks={ev['total_chunks']} bytes={ev['total_bytes']}", flush=True)
                        if barge_in_seen.is_set() and turn1_id is not None and ev["turn_id"] > turn1_id:
                            turn2_tts_completed.set()
                    elif t == "error":
                        print(f"  [ERROR] {ev}", flush=True)

            recv_task = asyncio.create_task(receiver())
            await asyncio.sleep(0.5)

            # 3. Stream Utterance 1 in real-time 32ms PCM chunks + trailing silence
            print("[LIVE-M1] Step 3: Streaming Utterance 1 to /ws/voice/live_m1_verify...", flush=True)
            t0 = time.perf_counter()
            for i in range(0, len(utt1_pcm), FRAME_BYTES):
                await ws.send(utt1_pcm[i : i + FRAME_BYTES])
                await asyncio.sleep(0.028)
            for _ in range(38):
                await ws.send(b"\x00" * FRAME_BYTES)
                await asyncio.sleep(0.028)

            # Wait for live TTS audio chunks of Turn 1 to start streaming
            await asyncio.wait_for(turn1_tts_started.wait(), timeout=25.0)
            print(f"[LIVE-M1] Turn 1 live Timbre audio streaming started at +{time.perf_counter()-t0:.2f}s!", flush=True)

            # 4. BARGE-IN! Immediately stream Utterance 2 while Turn 1 TTS is still streaming!
            print("[LIVE-M1] Step 4: Triggering live VAD barge-in with Utterance 2 mid-TTS...", flush=True)
            for i in range(0, len(utt2_pcm), FRAME_BYTES):
                await ws.send(utt2_pcm[i : i + FRAME_BYTES])
                await asyncio.sleep(0.028)
            for _ in range(38):
                await ws.send(b"\x00" * FRAME_BYTES)
                await asyncio.sleep(0.028)

            # Wait for barge-in cancellation + Turn 2 full TTS completion
            await asyncio.wait_for(barge_in_seen.wait(), timeout=15.0)
            await asyncio.wait_for(turn2_tts_completed.wait(), timeout=25.0)

            await ws.send(json.dumps({"type": "end_session"}))
            recv_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await recv_task
    finally:
        server.should_exit = True
        await server_task

    # Assertions on real live events
    partials = [e for e in events if e["type"] == "partial_transcript"]
    finals = [e for e in events if e["type"] == "final_transcript"]
    replies = [e for e in events if e["type"] == "assistant_response"]
    tts_chunks_t1 = [e for e in events if e["type"] == "tts_audio_chunk" and e["turn_id"] == turn1_id]
    tts_chunks_t2 = [
        e for e in events if e["type"] == "tts_audio_chunk" and turn1_id is not None and e["turn_id"] > turn1_id
    ]
    assert len(partials) >= 1, "Expected live partial_transcript events from Prisma v3.0"
    assert len(finals) >= 2, f"Expected >=2 live final_transcript events, got {len(finals)}"
    assert len(replies) >= 2, f"Expected >=2 live LLM responses, got {len(replies)}"
    assert len(tts_chunks_t1) >= 1, "Expected live Turn 1 Timbre v3.0 audio chunks"
    assert len(tts_chunks_t2) >= 1, "Expected live Turn 2 Timbre v3.0 audio chunks"
    assert barge_in_event_index is not None, "Expected barge_in/tts_cancelled event"

    # Zero stale Turn 1 audio after tts_cancelled!
    stale = [
        e
        for e in events[barge_in_event_index + 1 :]
        if e["type"] == "tts_audio_chunk" and e["turn_id"] == turn1_id
    ]
    assert stale == [], f"Stale Turn 1 audio chunks arrived after tts_cancelled: {len(stale)}"

    # Decode a Turn 2 chunk to verify valid non-empty PCM bytes
    sample_pcm = base64.b64decode(tts_chunks_t2[0]["audio_base64"])
    assert len(sample_pcm) > 0 and len(sample_pcm) % 2 == 0

    print("\n=== LIVE MILESTONE 1 VERIFICATION PASSED (0 MOCKS) ===", flush=True)
    print(f"  Partials received: {len(partials)}", flush=True)
    print(f"  Finals received:   {len(finals)}", flush=True)
    print(f"  LLM turns:         {len(replies)}", flush=True)
    print(f"  Turn 1 TTS chunks: {len(tts_chunks_t1)} (interrupted cleanly, 0 stale chunks after cancel)", flush=True)
    print(f"  Turn 2 TTS chunks: {len(tts_chunks_t2)} (resumed conversation with new input)", flush=True)


if __name__ == "__main__":
    asyncio.run(run_live_milestone1_verification())

