#!/usr/bin/env python3
"""Minimal local CLI audio test harness for Milestone 1 voice loop verification.

Capabilities:
- List and select audio input/output devices (`--list-devices`, `--input-device`, `--output-device`)
- Stream live microphone audio (16kHz PCM_S16LE) over `/ws/voice/{session_id}`
- Play streaming Gnani Timbre v3.0 PCM audio with instant buffer flush on `tts_cancelled` / `barge_in`
- Display live partial and final transcripts, assistant responses, and session state
- Replay recorded WAV files (`--wav path/to/file.wav`) for repeatable testing
- Test manual barge-in (`--barge-in-wav` or pressing Enter during live mic mode)
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import collections
import contextlib
import json
import sys
import threading
import uuid
import wave
from pathlib import Path

import numpy as np
import websockets

SAMPLE_RATE = 16000
FRAME_SAMPLES = 512  # 32 ms @ 16 kHz
FRAME_BYTES = FRAME_SAMPLES * 2


class InterruptibleSpeaker:
    """Thread-safe 16kHz PCM_S16LE speaker player with instant flush on barge-in."""

    def __init__(self, *, device: int | None = None, enabled: bool = True) -> None:
        self._device = device
        self._enabled = enabled
        self._lock = threading.Lock()
        self._queue: collections.deque[bytes] = collections.deque()
        self._current_buf = b""
        self._active_turn_id: int = -1
        self._stream = None

    def start(self) -> None:
        if not self._enabled:
            return
        import sounddevice as sd

        def callback(outdata: np.ndarray, frames: int, _time, _status) -> None:
            needed = frames * 2
            out = bytearray()
            with self._lock:
                while len(out) < needed:
                    if not self._current_buf:
                        if not self._queue:
                            break
                        self._current_buf = self._queue.popleft()
                    take = min(needed - len(out), len(self._current_buf))
                    out.extend(self._current_buf[:take])
                    self._current_buf = self._current_buf[take:]
            if len(out) < needed:
                out.extend(b"\x00" * (needed - len(out)))
            outdata[:] = np.frombuffer(bytes(out), dtype=np.int16).reshape(-1, 1)

        self._stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=FRAME_SAMPLES,
            device=self._device,
            callback=callback,
        )
        self._stream.start()

    def set_turn(self, turn_id: int) -> None:
        with self._lock:
            self._active_turn_id = turn_id

    def enqueue(self, turn_id: int, pcm: bytes) -> None:
        if not self._enabled:
            return
        with self._lock:
            if turn_id < self._active_turn_id:
                return  # Drop stale audio from cancelled turn
            self._active_turn_id = turn_id
            self._queue.append(pcm)

    def flush(self, *, min_next_turn_id: int | None = None) -> int:
        with self._lock:
            dropped = len(self._queue)
            self._queue.clear()
            self._current_buf = b""
            if min_next_turn_id is not None:
                self._active_turn_id = max(self._active_turn_id, min_next_turn_id)
            return dropped

    def stop(self) -> None:
        if self._stream is not None:
            with contextlib.suppress(Exception):
                self._stream.stop()
                self._stream.close()
            self._stream = None


def list_audio_devices() -> None:
    import sounddevice as sd

    print("Available audio devices:")
    for idx, dev in enumerate(sd.query_devices()):
        print(
            f"  [{idx}] {dev['name']} "
            f"(in={dev['max_input_channels']}, out={dev['max_output_channels']}, "
            f"default_sr={int(dev['default_samplerate'])} Hz)"
        )
    print(f"Default (input, output): {sd.default.device}")


def read_wav_pcm16_16k(wav_path: Path) -> bytes:
    with wave.open(str(wav_path), "rb") as wf:
        if wf.getsampwidth() != 2 or wf.getnchannels() != 1:
            raise ValueError("WAV must be 16-bit mono PCM")
        sr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    if sr == SAMPLE_RATE:
        return raw
    # Linear resample to 16kHz if needed
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    new_len = int(round(len(samples) * SAMPLE_RATE / sr))
    resampled = np.interp(
        np.linspace(0, len(samples) - 1, new_len),
        np.arange(len(samples)),
        samples,
    )
    return np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()


async def run_client(args: argparse.Namespace) -> None:
    session_id = args.session_id or f"cli_{uuid.uuid4().hex[:8]}"
    url = f"{args.server.rstrip('/')}/ws/voice/{session_id}?language={args.language}"
    speaker = InterruptibleSpeaker(device=args.output_device, enabled=not args.no_playback)
    speaker.start()

    print(f"[CLI] Connecting to {url} ...")
    try:
        async with websockets.connect(url, max_size=4 * 1024 * 1024) as ws:
            print("[CLI] Connected! Waiting for session_ready...")
            tts_started_ev = asyncio.Event()
            tts_done_ev = asyncio.Event()

            async def receiver() -> None:
                async for raw in ws:
                    if isinstance(raw, bytes):
                        continue
                    ev = json.loads(raw)
                    t = ev.get("type")
                    if t == "session_ready":
                        print(
                            f"[READY] lang={ev.get('language')} stt={ev.get('stt_provider')} "
                            f"tts={ev.get('tts_provider')} llm={ev.get('llm_model')}"
                        )
                    elif t == "session_state":
                        print(f"[STATE] {ev.get('state')} (turn={ev.get('turn_id')})")
                    elif t == "partial_transcript":
                        print(f"\r[PARTIAL] {ev.get('text', '')}    ", end="", flush=True)
                    elif t == "final_transcript":
                        print(
                            f"\n[FINAL] ({ev.get('language')}, {ev.get('latency_ms')}ms): "
                            f"{ev.get('text', '')}"
                        )
                    elif t == "assistant_response":
                        print(f"[ASSISTANT turn={ev.get('turn_id')}]: {ev.get('text', '')}")
                    elif t == "tts_start":
                        tts_done_ev.clear()
                        tts_started_ev.set()
                        speaker.set_turn(int(ev.get("turn_id", 0)))
                    elif t == "tts_audio_chunk":
                        pcm = base64.b64decode(ev.get("audio_base64", ""))
                        speaker.enqueue(int(ev.get("turn_id", 0)), pcm)
                    elif t == "tts_complete":
                        print(
                            f"[TTS DONE] turn={ev.get('turn_id')} "
                            f"chunks={ev.get('total_chunks')} bytes={ev.get('total_bytes')}"
                        )
                        tts_done_ev.set()
                    elif t in ("barge_in", "tts_cancelled"):
                        dropped = speaker.flush(
                            min_next_turn_id=int(ev.get("new_turn_id", ev.get("cancelled_turn_id", 0)) + 1)
                        )
                        print(f"\n[BARGE-IN/{t}] flushed {dropped} queued audio chunks -> {ev}")
                    elif t == "error":
                        print(f"\n[ERROR] {ev.get('code')}: {ev.get('message')}")

            recv_task = asyncio.create_task(receiver())

            if args.wav:
                pcm = read_wav_pcm16_16k(Path(args.wav))
                print(f"[CLI] Streaming WAV ({len(pcm)/32000:.2f}s): {args.wav}")
                for i in range(0, len(pcm), FRAME_BYTES):
                    await ws.send(pcm[i : i + FRAME_BYTES])
                    await asyncio.sleep(0.030)
                # Trailing silence so Prisma endpointing fires
                for _ in range(35):
                    await ws.send(b"\x00" * FRAME_BYTES)
                    await asyncio.sleep(0.030)

                if args.barge_in_wav:
                    print("[CLI] Waiting for assistant TTS to begin, then streaming barge-in WAV...")
                    await asyncio.wait_for(tts_started_ev.wait(), timeout=20.0)
                    await asyncio.sleep(0.35)
                    barge_pcm = read_wav_pcm16_16k(Path(args.barge_in_wav))
                    for i in range(0, len(barge_pcm), FRAME_BYTES):
                        await ws.send(barge_pcm[i : i + FRAME_BYTES])
                        await asyncio.sleep(0.030)
                    for _ in range(35):
                        await ws.send(b"\x00" * FRAME_BYTES)
                        await asyncio.sleep(0.030)

                await asyncio.sleep(args.wait_after)
                await ws.send(json.dumps({"type": "end_session"}))
                recv_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await recv_task
            else:
                import sounddevice as sd

                loop = asyncio.get_running_loop()
                mic_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=100)

                def mic_callback(indata: np.ndarray, _frames: int, _time, _status) -> None:
                    data = indata.tobytes()
                    with contextlib.suppress(asyncio.QueueFull):
                        loop.call_soon_threadsafe(mic_queue.put_nowait, data)

                print(
                    "[CLI] Live microphone streaming started. Speak naturally! "
                    "Press Ctrl+C to exit."
                )
                with sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype="int16",
                    blocksize=FRAME_SAMPLES,
                    device=args.input_device,
                    callback=mic_callback,
                ):
                    try:
                        while True:
                            chunk = await mic_queue.get()
                            await ws.send(chunk)
                    except (KeyboardInterrupt, asyncio.CancelledError):
                        pass
                await ws.send(json.dumps({"type": "end_session"}))
                recv_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await recv_task
    finally:
        speaker.stop()
        print("\n[CLI] Session closed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="ASHA Voice Backend — Milestone 1 CLI Test Harness")
    parser.add_argument("--list-devices", action="store_true", help="List audio input/output devices")
    parser.add_argument("--server", default="ws://127.0.0.1:8000", help="Backend WS base URL")
    parser.add_argument("--session-id", default=None, help="Optional explicit session ID")
    parser.add_argument("--language", default="indic-auto", help="STT language (default: indic-auto)")
    parser.add_argument("--input-device", type=int, default=None, help="Microphone device index")
    parser.add_argument("--output-device", type=int, default=None, help="Speaker device index")
    parser.add_argument("--wav", default=None, help="Stream a 16-bit mono WAV file instead of live mic")
    parser.add_argument("--barge-in-wav", default=None, help="Optional second WAV to stream mid-TTS to test barge-in")
    parser.add_argument("--no-playback", action="store_true", help="Disable speaker output (headless test)")
    parser.add_argument("--wait-after", type=float, default=10.0, help="Seconds to wait after WAV stream")
    args = parser.parse_args()

    if args.list_devices:
        list_audio_devices()
        return

    try:
        asyncio.run(run_client(args))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()

