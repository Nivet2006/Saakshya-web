#!/usr/bin/env python3
"""Standalone Gnani Prisma v3.0 Live STT Pipeline Verifier.

Tests real Gnani Prisma streaming STT end-to-end without LLM, TTS, or database.
Usage:
  python scripts/test_live_stt.py              # Synthesize test audio and stream to STT
  python scripts/test_live_stt.py --wav FILE   # Stream an existing 16kHz mono WAV file
  python scripts/test_live_stt.py --mic        # Capture live microphone for 5 seconds
"""

import argparse
import asyncio
import io
import logging
import os
import sys
import time
import wave

# Ensure backend root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.config import get_settings
from app.voice.stt.gnani_prisma import GnaniPrismaSTTAdapter
from app.voice.tts.gnani_timbre import GnaniTimbreTTSAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("test_live_stt")

TEST_SENTENCE = "Hello, my name is Lakshmi. Baby weight is 2.8 kilograms."


async def run_stt_stream_verification(pcm_data: bytes, sample_rate: int = 16000) -> bool:
    """Stream raw PCM to Gnani Prisma STT and print all incoming events."""
    settings = get_settings()
    api_key = settings.gnani_api_key.get_secret_value()
    if not api_key or api_key.startswith("mock_"):
        print("\n❌ ERROR: GNANI_API_KEY is not configured in .env!")
        return False

    print("\n" + "=" * 70)
    print("STAGE 1: Connecting to Gnani Prisma v3.0 WebSocket...")
    print(f"URL: {settings.effective_stt_ws_url}")
    print(f"Model: {settings.gnani_stt_model}")
    print(f"Language: indic-auto (candidates: {settings.prisma_language_candidates})")
    print(f"Format: {settings.gnani_stt_format}")
    print("=" * 70)

    stt = GnaniPrismaSTTAdapter.from_settings(settings, language_code="indic-auto")
    t0 = time.time()
    try:
        await stt.connect()
        handshake_ms = (time.time() - t0) * 1000
        print(f"✅ WebSocket Connected in {handshake_ms:.0f}ms!")
        print(f"Server Config: {stt.connected_config}")
    except Exception as exc:
        print(f"\n❌ FAILED to connect to Gnani Prisma: {exc}")
        return False

    print("\n" + "=" * 70)
    print(f"STAGE 2: Streaming Audio ({len(pcm_data)} bytes, {len(pcm_data) / (sample_rate * 2):.2f}s)...")
    print("Cadence: 1024 bytes (512 samples) every 32ms (16kHz PCM_S16LE)")
    print("=" * 70)

    received_partials = []
    final_transcript = None
    final_lang = None
    final_latency = None

    async def event_collector():
        nonlocal final_transcript, final_lang, final_latency
        async for ev in stt.events():
            if ev.event_type == "connected":
                continue
            elif ev.event_type == "speech_start":
                print(f"  [STT Event] 🟢 Speech Start (utterance: {ev.utterance_id})")
            elif ev.event_type == "partial":
                print(f"  [STT Event] 🟡 Partial: \"{ev.text}\" (lang: {ev.language_code})")
                received_partials.append(ev.text)
            elif ev.event_type == "speech_end":
                print(f"  [STT Event] 🔵 Speech End")
            elif ev.event_type == "final":
                print(f"  [STT Event] 🟢 FINAL TRANSCRIPT: \"{ev.text}\" (lang: {ev.language_code}, latency: {ev.latency_ms}ms)")
                final_transcript = ev.text
                final_lang = ev.language_code
                final_latency = ev.latency_ms
                break
            elif ev.event_type == "error":
                print(f"  [STT Event] ❌ Error: {ev.error_message}")
                break

    listener_task = asyncio.create_task(event_collector())

    # Stream in 1024-byte frames at 32ms cadence
    frame_size = 1024
    frames_sent = 0
    stream_t0 = time.time()

    for i in range(0, len(pcm_data), frame_size):
        chunk = pcm_data[i : i + frame_size]
        if len(chunk) < frame_size:
            chunk = chunk + b"\x00" * (frame_size - len(chunk))
        await stt.send_audio(chunk)
        frames_sent += 1
        await asyncio.sleep(0.032)

    # Send trailing silence (1.2 seconds = ~38 frames) to trigger endpointing
    for _ in range(38):
        await stt.send_audio(b"\x00" * frame_size)
        frames_sent += 1
        await asyncio.sleep(0.032)

    total_stream_sec = time.time() - stream_t0
    print(f"\nSent {frames_sent} frames ({frames_sent * frame_size} bytes) in {total_stream_sec:.2f}s")

    try:
        await asyncio.wait_for(listener_task, timeout=12.0)
    except asyncio.TimeoutError:
        print("⚠️ Timed out waiting for final transcript.")

    await stt.close()

    print("\n" + "=" * 70)
    print("STAGE 3: VERIFICATION RESULTS")
    print("=" * 70)
    if final_transcript:
        print(f"✅ SUCCESS! Final Transcript Recognized:")
        print(f"   Text:     \"{final_transcript}\"")
        print(f"   Language: {final_lang}")
        print(f"   Latency:  {final_latency}ms")
        print(f"   Partials: {len(received_partials)} partial updates received")
        return True
    else:
        print("❌ FAILED: No final transcript received.")
        if received_partials:
            print(f"   (However, received partials: {received_partials})")
        return False


async def generate_synthetic_audio(sentence: str) -> bytes:
    """Use Gnani Timbre TTS to synthesize 16kHz PCM audio for verification."""
    settings = get_settings()
    tts = GnaniTimbreTTSAdapter.from_settings(settings)
    await tts.connect()
    pcm_chunks = []
    print(f"Synthesizing test sentence: \"{sentence}\"")
    async for chunk in tts.synthesize_stream(sentence, language="en-IN"):
        pcm_chunks.append(chunk)
    await tts.close()
    return b"".join(pcm_chunks)


def read_wav_file(path: str) -> bytes:
    with wave.open(path, "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

        if sampwidth != 2:
            raise ValueError(f"WAV must be 16-bit PCM, got {sampwidth * 8}-bit")
        if framerate != 16000:
            print(f"⚠️ Warning: WAV sample rate is {framerate}Hz, expected 16000Hz.")
        if n_channels > 1:
            print("Downmixing stereo to mono...")
            import numpy as np
            arr = np.frombuffer(frames, dtype=np.int16).reshape(-1, n_channels)
            mono = arr.mean(axis=1).astype(np.int16)
            return mono.tobytes()
        return frames


def capture_mic_audio(duration_sec: float = 5.0) -> bytes:
    try:
        import sounddevice as sd
    except ImportError:
        print("sounddevice not installed. Cannot capture mic.")
        return b""
    print(f"\n🎤 Recording {duration_sec} seconds from your microphone... Speak now!")
    audio = sd.rec(int(duration_sec * 16000), samplerate=16000, channels=1, dtype="int16")
    sd.wait()
    print("Recording finished!")
    return audio.tobytes()


async def main():
    parser = argparse.ArgumentParser(description="Gnani Prisma v3.0 STT Verifier")
    parser.add_argument("--wav", type=str, help="Path to a 16kHz mono PCM WAV file")
    parser.add_argument("--mic", action="store_true", help="Record 5s from system microphone")
    parser.add_argument("--text", type=str, default=TEST_SENTENCE, help="Synthetic test text")
    args = parser.parse_args()

    if args.wav:
        print(f"Loading WAV file: {args.wav}")
        pcm_data = read_wav_file(args.wav)
    elif args.mic:
        pcm_data = capture_mic_audio(5.0)
        if not pcm_data:
            sys.exit(1)
    else:
        print("Generating synthetic speech via Gnani Timbre TTS...")
        pcm_data = await generate_synthetic_audio(args.text)

    success = await run_stt_stream_verification(pcm_data)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
