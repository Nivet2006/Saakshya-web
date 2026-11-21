"""Unit tests for Windows/cross-platform audio driver fallback, UTF-8 stdio, and launcher helpers."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import cli_client  # noqa: E402
from app.core.logging import ensure_utf8_stdio  # noqa: E402


class _FakePortAudioError(RuntimeError):
    pass


class _FakeStream:
    def __init__(self, *, samplerate: int, channels: int, device: int | None, callback) -> None:
        self.samplerate = samplerate
        self.channels = channels
        self.device = device
        self.callback = callback
        self.started = False
        self.stopped = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


def test_ensure_utf8_stdio_safe_on_indic_text() -> None:
    ensure_utf8_stdio()
    cli_client.ensure_utf8_stdio()
    assert "नमस्ते" and "ಕನ್ನಡ" and "தமிழ்"


def test_resample_pcm16_roundtrip_and_passthrough() -> None:
    src = np.arange(0, 1600, dtype=np.int16).tobytes()
    assert cli_client.resample_pcm16(src, 16000, 16000) == src
    assert cli_client.resample_pcm16(b"", 48000, 16000) == b""

    up = cli_client.resample_pcm16(src, 16000, 48000)
    assert len(up) == len(src) * 3

    down = cli_client.resample_pcm16(up, 48000, 16000)
    assert len(down) == len(src)


def test_downmix_to_mono_int16() -> None:
    stereo = np.array([[1000, 3000], [-2000, -4000]], dtype=np.int16)
    mono = cli_client.downmix_to_mono_int16(stereo, 2)
    assert mono.dtype == np.int16
    assert list(mono) == [2000, -3000]


def test_candidate_audio_configs_prioritizes_windows_hostapis() -> None:
    fake_sd = SimpleNamespace(
        default=SimpleNamespace(device=(0, 0)),
        query_hostapis=lambda: [
            {"name": "Windows WDM-KS"},
            {"name": "MME"},
            {"name": "Windows WASAPI"},
        ],
        query_devices=lambda: [
            {
                "name": "WDM Mic",
                "hostapi": 0,
                "max_input_channels": 2,
                "max_output_channels": 0,
                "default_samplerate": 48000.0,
            },
            {
                "name": "MME Mic",
                "hostapi": 1,
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 44100.0,
            },
            {
                "name": "WASAPI Mic",
                "hostapi": 2,
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 48000.0,
            },
        ],
    )
    configs = cli_client._candidate_audio_configs(fake_sd, device=None, is_input=True)
    # Default device (0) is tried first, then WASAPI (2) before MME (1) and WDM-KS
    seen_devs = []
    for dev_idx, *_ in configs:
        if dev_idx not in seen_devs:
            seen_devs.append(dev_idx)
    assert seen_devs == [0, 2, 1]


def test_speaker_falls_back_to_48k_stereo_and_resamples(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[tuple[int | None, int, int, int]] = []

    def fake_output_stream(**kwargs):
        attempts.append(
            (kwargs["device"], kwargs["samplerate"], kwargs["channels"], kwargs["blocksize"])
        )
        if kwargs["samplerate"] != 48000 or kwargs["channels"] != 2:
            raise _FakePortAudioError("Invalid sample rate / channels on Windows WASAPI")
        return _FakeStream(
            samplerate=kwargs["samplerate"],
            channels=kwargs["channels"],
            device=kwargs["device"],
            callback=kwargs["callback"],
        )

    fake_sd = SimpleNamespace(
        default=SimpleNamespace(device=(0, 0)),
        query_hostapis=lambda: [{"name": "Windows WASAPI"}],
        query_devices=lambda: [
            {
                "name": "Realtek Speakers",
                "hostapi": 0,
                "max_input_channels": 0,
                "max_output_channels": 2,
                "default_samplerate": 48000.0,
            }
        ],
        OutputStream=fake_output_stream,
    )
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)

    speaker = cli_client.InterruptibleSpeaker(enabled=True)
    speaker.start()
    try:
        assert speaker._enabled is True
        assert speaker._output_rate == 48000
        assert speaker._output_channels == 2
        assert len(attempts) >= 2

        # Enqueue 16 kHz mono PCM (512 samples = 1024 bytes) -> resampled 3x to 48 kHz (3072 bytes)
        pcm_16k = np.ones(512, dtype=np.int16).tobytes()
        speaker.enqueue(0, pcm_16k)
        assert len(speaker._queue) == 1
        assert len(speaker._queue[0]) == 1024 * 3

        # Verify stereo callback expansion does not raise
        out_buf = np.zeros((1536, 2), dtype=np.int16)
        speaker._stream.callback(out_buf, 1536, None, None)
        assert int(out_buf[0, 0]) == 1
        assert int(out_buf[0, 1]) == 1
    finally:
        speaker.stop()


def test_speaker_disables_gracefully_when_no_driver_works(monkeypatch: pytest.MonkeyPatch) -> None:
    def always_fail(**_kwargs):
        raise _FakePortAudioError("No audio device available")

    fake_sd = SimpleNamespace(
        default=SimpleNamespace(device=(-1, -1)),
        query_hostapis=lambda: [],
        query_devices=lambda: [],
        OutputStream=always_fail,
    )
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)

    speaker = cli_client.InterruptibleSpeaker(enabled=True)
    speaker.start()
    assert speaker._enabled is False
    assert speaker._stream is None


@pytest.mark.asyncio
async def test_input_stream_falls_back_to_48k_stereo_and_downmixes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_input_stream(**kwargs):
        if kwargs["samplerate"] != 48000 or kwargs["channels"] != 2:
            raise _FakePortAudioError("Only 48kHz stereo supported")
        return _FakeStream(
            samplerate=kwargs["samplerate"],
            channels=kwargs["channels"],
            device=kwargs["device"],
            callback=kwargs["callback"],
        )

    fake_sd = SimpleNamespace(
        default=SimpleNamespace(device=(0, 0)),
        query_hostapis=lambda: [{"name": "Windows WASAPI"}],
        query_devices=lambda: [
            {
                "name": "USB Stereo Mic",
                "hostapi": 0,
                "max_input_channels": 2,
                "max_output_channels": 0,
                "default_samplerate": 48000.0,
            }
        ],
        InputStream=fake_input_stream,
    )
    loop = asyncio.get_running_loop()
    mic_q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=10)

    stream, sr, ch = cli_client.open_input_stream_with_fallback(
        fake_sd, device=None, loop=loop, mic_queue=mic_q
    )
    try:
        assert sr == 48000
        assert ch == 2

        # Simulate 48 kHz stereo callback (1536 frames -> 512 frames @ 16 kHz mono = 1024 bytes)
        indata = np.full((1536, 2), 500, dtype=np.int16)
        stream.callback(indata, 1536, None, None)
        await asyncio.sleep(0.01)
        chunk = mic_q.get_nowait()
        assert len(chunk) == 1024
        arr = np.frombuffer(chunk, dtype=np.int16)
        assert int(arr[0]) == 500
    finally:
        stream.stop()
        stream.close()

