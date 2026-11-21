#!/usr/bin/env python3
"""Minimal local CLI audio test harness for Milestone 1 voice loop verification.

Capabilities:
- List and select audio input/output devices (`--list-devices`, `--input-device`, `--output-device`)
- Automatic cross-platform audio driver fallback (Windows WASAPI/DirectSound/MME,
  sample-rate resampling, stereo-to-mono downmix, and graceful headless playback fallback)
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
from typing import Any

import numpy as np
import websockets

SAMPLE_RATE = 16000
FRAME_SAMPLES = 512  # 32 ms @ 16 kHz
FRAME_BYTES = FRAME_SAMPLES * 2

# Ordered Windows Host API preference for low-latency / reliable PortAudio streams.
_WINDOWS_HOSTAPI_PRIORITY: tuple[str, ...] = (
    "windows wasapi",
    "windows directsound",
    "mme",
)


def ensure_utf8_stdio() -> None:
    """Ensure stdout/stderr use UTF-8 on Windows so Indic scripts never raise UnicodeEncodeError."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            with contextlib.suppress(Exception):
                reconfigure(encoding="utf-8", errors="replace")


def resample_pcm16(pcm: bytes, src_rate: int, dst_rate: int) -> bytes:
    """Linearly resample 16-bit mono PCM bytes from `src_rate` to `dst_rate`."""
    if not pcm or src_rate == dst_rate or src_rate <= 0 or dst_rate <= 0:
        return pcm
    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    if samples.size == 0:
        return pcm
    new_len = max(1, int(round(samples.size * dst_rate / src_rate)))
    if samples.size == 1:
        resampled = np.repeat(samples, new_len)
    else:
        resampled = np.interp(
            np.linspace(0, samples.size - 1, new_len),
            np.arange(samples.size),
            samples,
        )
    return np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()


def downmix_to_mono_int16(samples: np.ndarray, channels: int) -> np.ndarray:
    """Downmix multi-channel int16 audio array `[frames, channels]` to mono 1-D int16."""
    if channels <= 1:
        return samples.reshape(-1).astype(np.int16, copy=False)
    arr = samples.reshape(-1, channels).astype(np.int32)
    return np.clip(arr.mean(axis=1), -32768, 32767).astype(np.int16)


def _hostapi_rank(hostapi_name: str) -> int:
    name_low = hostapi_name.lower()
    for idx, prefix in enumerate(_WINDOWS_HOSTAPI_PRIORITY):
        if prefix in name_low:
            return idx
    if "wdm-ks" in name_low:
        return 99  # WDM-KS frequently rejects shared-mode sample rates on Windows
    return 10


def _candidate_audio_configs(
    sd: Any,
    *,
    device: int | None,
    is_input: bool,
) -> list[tuple[int | None, int, int, int]]:
    """Build ordered `(device_idx, samplerate, channels, blocksize)` candidates for PortAudio."""
    try:
        devices = list(sd.query_devices())
    except Exception:
        return [(device, SAMPLE_RATE, 1, FRAME_SAMPLES), (device, SAMPLE_RATE, 1, 0)]

    try:
        hostapis = list(sd.query_hostapis())
    except Exception:
        hostapis = []

    channel_key = "max_input_channels" if is_input else "max_output_channels"
    default_pair = getattr(sd.default, "device", (None, None))
    default_idx = default_pair[0] if is_input else default_pair[1]

    def _device_hostapi_name(dev: dict[str, Any]) -> str:
        idx = dev.get("hostapi")
        if isinstance(idx, int) and 0 <= idx < len(hostapis):
            return str(hostapis[idx].get("name", ""))
        return ""

    # Determine ordered list of device indices to try
    ordered_indices: list[int | None] = []
    if device is not None:
        ordered_indices.append(device)
    else:
        if isinstance(default_idx, int) and 0 <= default_idx < len(devices):
            ordered_indices.append(default_idx)
        else:
            ordered_indices.append(None)

        other_idxs = [
            idx
            for idx, dev in enumerate(devices)
            if int(dev.get(channel_key, 0)) > 0 and idx != default_idx
        ]
        other_idxs.sort(key=lambda i: _hostapi_rank(_device_hostapi_name(devices[i])))
        ordered_indices.extend(other_idxs)

    candidates: list[tuple[int | None, int, int, int]] = []
    seen: set[tuple[int | None, int, int, int]] = set()

    def _add(dev_idx: int | None, sr: int, ch: int, blk: int) -> None:
        key = (dev_idx, sr, ch, blk)
        if key not in seen and sr > 0 and ch > 0:
            seen.add(key)
            candidates.append(key)

    for dev_idx in ordered_indices:
        dev_info = (
            devices[dev_idx]
            if isinstance(dev_idx, int) and 0 <= dev_idx < len(devices)
            else {}
        )
        max_ch = int(dev_info.get(channel_key, 2)) if dev_info else 2
        if dev_info and max_ch <= 0 and device is None:
            continue

        default_sr = int(round(float(dev_info.get("default_samplerate") or 48000)))
        sample_rates = [SAMPLE_RATE]
        for sr in (default_sr, 48000, 44100):
            if sr > 0 and sr not in sample_rates:
                sample_rates.append(sr)

        channels_to_try = [1]
        if max_ch >= 2:
            channels_to_try.append(2)

        for ch in channels_to_try:
            for sr in sample_rates:
                blk = FRAME_SAMPLES if sr == SAMPLE_RATE else 0
                _add(dev_idx, sr, ch, blk)
                if blk != 0:
                    _add(dev_idx, sr, ch, 0)

    return candidates or [(device, SAMPLE_RATE, 1, FRAME_SAMPLES)]


class InterruptibleSpeaker:
    """Thread-safe PCM_S16LE speaker player with auto driver fallback and instant flush."""

    def __init__(self, *, device: int | None = None, enabled: bool = True) -> None:
        self._device = device
        self._enabled = enabled
        self._lock = threading.Lock()
        self._queue: collections.deque[bytes] = collections.deque()
        self._current_buf = b""
        self._active_turn_id: int = -1
        self._stream = None
        self._output_rate = SAMPLE_RATE
        self._output_channels = 1

    def start(self) -> None:
        if not self._enabled:
            return
        try:
            import sounddevice as sd
        except Exception as exc:
            print(
                f"[CLI][WARN] Speaker output disabled (sounddevice/PortAudio unavailable: {exc}).",
                file=sys.stderr,
            )
            self._enabled = False
            return

        last_err: Exception | None = None
        for dev_idx, sr, ch, blk in _candidate_audio_configs(
            sd, device=self._device, is_input=False
        ):
            self._output_rate = sr
            self._output_channels = ch

            def callback(
                outdata: np.ndarray,
                frames: int,
                _time,
                _status,
                *,
                _ch: int = ch,
            ) -> None:
                needed = frames * 2  # mono bytes at output_rate
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
                mono = np.frombuffer(bytes(out), dtype=np.int16)
                if _ch == 1:
                    outdata[:] = mono.reshape(-1, 1)
                else:
                    outdata[:] = np.repeat(mono[:, None], _ch, axis=1)

            stream = None
            try:
                stream = sd.OutputStream(
                    samplerate=sr,
                    channels=ch,
                    dtype="int16",
                    blocksize=blk,
                    device=dev_idx,
                    callback=callback,
                )
                stream.start()
                self._stream = stream
                if sr != SAMPLE_RATE or ch != 1 or dev_idx != self._device:
                    print(
                        f"[CLI] Speaker opened with driver fallback "
                        f"(device={dev_idx}, rate={sr}Hz, ch={ch})"
                    )
                return
            except Exception as exc:
                last_err = exc
                if stream is not None:
                    with contextlib.suppress(Exception):
                        stream.close()

        print(
            f"[CLI][WARN] Could not open any speaker output device ({last_err}). "
            "Continuing with speaker playback disabled.",
            file=sys.stderr,
        )
        self._enabled = False

    def set_turn(self, turn_id: int) -> None:
        with self._lock:
            self._active_turn_id = turn_id

    def enqueue(self, turn_id: int, pcm: bytes) -> None:
        if not self._enabled or not pcm:
            return
        play_pcm = (
            resample_pcm16(pcm, SAMPLE_RATE, self._output_rate)
            if self._output_rate != SAMPLE_RATE
            else pcm
        )
        with self._lock:
            if turn_id < self._active_turn_id:
                return  # Drop stale audio from cancelled turn
            self._active_turn_id = turn_id
            self._queue.append(play_pcm)

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


def open_input_stream_with_fallback(
    sd: Any,
    *,
    device: int | None,
    loop: asyncio.AbstractEventLoop,
    mic_queue: asyncio.Queue[bytes],
) -> tuple[Any, int, int]:
    """Open microphone InputStream with automatic Windows/macOS driver & rate fallback."""
    last_err: Exception | None = None
    for dev_idx, sr, ch, blk in _candidate_audio_configs(sd, device=device, is_input=True):

        def mic_callback(
            indata: np.ndarray,
            _frames: int,
            _time,
            _status,
            *,
            _sr: int = sr,
            _ch: int = ch,
        ) -> None:
            mono = downmix_to_mono_int16(indata, _ch)
            data = mono.tobytes()
            if _sr != SAMPLE_RATE:
                data = resample_pcm16(data, _sr, SAMPLE_RATE)
            with contextlib.suppress(asyncio.QueueFull):
                loop.call_soon_threadsafe(mic_queue.put_nowait, data)

        stream = None
        try:
            stream = sd.InputStream(
                samplerate=sr,
                channels=ch,
                dtype="int16",
                blocksize=blk,
                device=dev_idx,
                callback=mic_callback,
            )
            stream.start()
            return stream, sr, ch
        except Exception as exc:
            last_err = exc
            if stream is not None:
                with contextlib.suppress(Exception):
                    stream.close()

    raise RuntimeError(
        f"Could not open any microphone input device ({last_err}). "
        "On Windows, verify Settings -> Privacy & security -> Microphone is enabled, "
        "check `--list-devices`, or test with `--wav <path>`."
    )


def list_audio_devices() -> None:
    try:
        import sounddevice as sd
    except Exception as exc:
        print(
            f"[CLI][ERROR] sounddevice/PortAudio failed to initialize: {exc}",
            file=sys.stderr,
        )
        return

    try:
        hostapis = list(sd.query_hostapis())
    except Exception:
        hostapis = []

    print("Available audio devices:")
    for idx, dev in enumerate(sd.query_devices()):
        api_idx = dev.get("hostapi")
        api_name = (
            hostapis[api_idx]["name"]
            if isinstance(api_idx, int) and 0 <= api_idx < len(hostapis)
            else "unknown"
        )
        print(
            f"  [{idx}] {dev['name']} [{api_name}] "
            f"(in={dev['max_input_channels']}, out={dev['max_output_channels']}, "
            f"default_sr={int(dev['default_samplerate'])} Hz)"
        )
    print(f"Default (input, output): {sd.default.device}")


def read_wav_pcm16_16k(wav_path: Path) -> bytes:
    with wave.open(str(wav_path), "rb") as wf:
        if wf.getsampwidth() != 2 or wf.getnchannels() not in (1, 2):
            raise ValueError("WAV must be 16-bit mono or stereo PCM")
        channels = wf.getnchannels()
        sr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    if channels == 2:
        mono = downmix_to_mono_int16(np.frombuffer(raw, dtype=np.int16), 2)
        raw = mono.tobytes()
    return resample_pcm16(raw, sr, SAMPLE_RATE)


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
                mic_stream, actual_sr, actual_ch = open_input_stream_with_fallback(
                    sd,
                    device=args.input_device,
                    loop=loop,
                    mic_queue=mic_queue,
                )
                print(
                    f"[CLI] Live microphone streaming started (rate={actual_sr}Hz, ch={actual_ch}). "
                    "Speak naturally! Press Ctrl+C to exit."
                )
                try:
                    while True:
                        chunk = await mic_queue.get()
                        await ws.send(chunk)
                except (KeyboardInterrupt, asyncio.CancelledError):
                    pass
                finally:
                    with contextlib.suppress(Exception):
                        mic_stream.stop()
                        mic_stream.close()
                with contextlib.suppress(Exception):
                    await ws.send(json.dumps({"type": "end_session"}))
                recv_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await recv_task
    finally:
        speaker.stop()
        print("\n[CLI] Session closed.")


def main() -> None:
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description="ASHA Voice Backend — Milestone 1 CLI Test Harness")
    parser.add_argument("--list-devices", action="store_true", help="List audio input/output devices")
    parser.add_argument("--server", default="ws://127.0.0.1:8000", help="Backend WS base URL")
    parser.add_argument("--session-id", default=None, help="Optional explicit session ID")
    parser.add_argument("--language", default="indic-auto", help="STT language (default: indic-auto)")
    parser.add_argument("--input-device", type=int, default=None, help="Microphone device index")
    parser.add_argument("--output-device", type=int, default=None, help="Speaker device index")
    parser.add_argument("--wav", default=None, help="Stream a 16-bit mono/stereo WAV file instead of live mic")
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
