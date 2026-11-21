"""Zero-torch ONNX Silero VAD with adaptive noise-floor dual-gate barge-in detector.

Uses `silero_vad.onnx` (bundled in `pipecat-ai`) directly via `onnxruntime` for
16 kHz / 512-sample (32 ms) PCM_S16LE frames.

Dual-gate barge-in prevents household/street noise bursts from constantly cutting
off the assistant: while `assistant_speaking=True`, barge-in triggers ONLY when
BOTH Silero speech probability >= `barge_in_threshold` AND frame RMS >=
`max(min_rms_floor, snr_multiplier * adaptive_noise_floor_rms)` are sustained
for `barge_in_min_speech_ms` (allowing at most 1 brief frame dip).
"""

from __future__ import annotations

import logging
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np

try:
    import onnxruntime as ort
except ImportError as exc:
    import sys as _sys

    if _sys.platform == "win32":
        raise ImportError(
            "Failed to load onnxruntime on Windows. Install the Microsoft Visual C++ "
            "Redistributable (x64): https://aka.ms/vs/17/release/vc_redist.x64.exe "
            f"(original error: {exc})"
        ) from exc
    raise

from app.voice.interfaces import VADDecision

logger = logging.getLogger(__name__)

FRAME_SAMPLES_16K = 512
FRAME_BYTES_16K = FRAME_SAMPLES_16K * 2  # 1024 bytes = 32 ms @ 16kHz
CONTEXT_SAMPLES_16K = 64


def locate_silero_onnx() -> Path:
    """Locate the bundled `silero_vad.onnx` model file."""
    import pipecat.audio.vad as vad_pkg

    pkg_dir = Path(vad_pkg.__file__).resolve().parent
    candidate = pkg_dir / "data" / "silero_vad.onnx"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"silero_vad.onnx not found at {candidate}")


class SileroOnnxVAD:
    """Noise-resilient ONNX Silero VAD + sustained-speech dual-gate barge-in."""

    def __init__(
        self,
        *,
        model_path: Path | None = None,
        sample_rate: int = 16000,
        speech_threshold: float = 0.6,
        barge_in_threshold: float = 0.72,
        barge_in_min_speech_ms: int = 300,
        min_rms_floor: float = 0.015,
        snr_multiplier: float = 2.2,
        pre_roll_ms: int = 320,
    ) -> None:
        if sample_rate != 16000:
            raise ValueError("SileroOnnxVAD currently supports 16000 Hz frames")
        self._sample_rate = sample_rate
        self._speech_threshold = speech_threshold
        self._barge_in_threshold = max(barge_in_threshold, speech_threshold)
        self._barge_in_frames_needed = max(2, round(barge_in_min_speech_ms / 32.0))
        self._min_rms_floor = min_rms_floor
        self._snr_multiplier = snr_multiplier

        path = model_path or locate_silero_onnx()
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        self._session = ort.InferenceSession(
            str(path),
            sess_options=opts,
            providers=["CPUExecutionProvider"],
        )
        self._input_names = {inp.name for inp in self._session.get_inputs()}

        pre_roll_frames = max(1, round(pre_roll_ms / 32.0))
        self._pre_roll: deque[bytes] = deque(maxlen=pre_roll_frames)
        self._remainder = b""
        self._state: np.ndarray
        self._context: np.ndarray
        self._noise_floor_rms: float = 0.005
        self._barge_in_streak: int = 0
        self._barge_in_dips: int = 0
        self.reset()

    def reset(self) -> None:
        """Reset Silero recurrent state and barge-in counters."""
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, CONTEXT_SAMPLES_16K), dtype=np.float32)
        self._barge_in_streak = 0
        self._barge_in_dips = 0
        self._pre_roll.clear()
        self._remainder = b""

    def reset_barge_in_streak(self) -> None:
        self._barge_in_streak = 0
        self._barge_in_dips = 0

    def _infer_prob(self, samples_f32: np.ndarray) -> float:
        """Run one 512-sample frame through Silero ONNX (v5/v6 state+context format)."""
        x = samples_f32.reshape(1, FRAME_SAMPLES_16K)
        if "state" in self._input_names:
            x_with_ctx = np.concatenate([self._context, x], axis=1)
            ort_inputs: dict[str, Any] = {
                "input": x_with_ctx,
                "state": self._state,
                "sr": np.array(self._sample_rate, dtype=np.int64),
            }
            out, new_state = self._session.run(None, ort_inputs)
            self._state = new_state
            self._context = x_with_ctx[:, -CONTEXT_SAMPLES_16K:]
            return float(np.squeeze(out))
        # Legacy Silero v4 fallback (`h`/`c`)
        ort_inputs = {
            "input": x,
            "sr": np.array(self._sample_rate, dtype=np.int64),
            "h": self._state[:1],
            "c": self._state[1:],
        }
        out, h, c = self._session.run(None, ort_inputs)
        self._state = np.concatenate([h, c], axis=0)
        return float(np.squeeze(out))

    def process_frame(self, pcm_frame: bytes, *, assistant_speaking: bool) -> VADDecision:
        """Evaluate arbitrary-sized PCM_S16LE bytes in 512-sample (32 ms) slices."""
        buf = self._remainder + pcm_frame
        last_decision = VADDecision(
            speech_prob=0.0,
            frame_rms=0.0,
            noise_floor_rms=self._noise_floor_rms,
            is_speech=False,
            barge_in_triggered=False,
        )

        offset = 0
        while offset + FRAME_BYTES_16K <= len(buf):
            chunk = buf[offset : offset + FRAME_BYTES_16K]
            offset += FRAME_BYTES_16K
            last_decision = self._process_512_frame(chunk, assistant_speaking=assistant_speaking)
            if last_decision.barge_in_triggered:
                self._remainder = buf[offset:]
                return last_decision

        self._remainder = buf[offset:]
        return last_decision

    def _process_512_frame(self, chunk: bytes, *, assistant_speaking: bool) -> VADDecision:
        samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
        frame_rms = float(np.sqrt(np.mean(samples * samples)))
        prob = self._infer_prob(samples)

        self._pre_roll.append(chunk)

        # Update adaptive noise floor only during non-speech frames when idle
        if prob < 0.35:
            alpha = 0.05 if not assistant_speaking else 0.02
            self._noise_floor_rms = (1.0 - alpha) * self._noise_floor_rms + alpha * frame_rms

        is_speech = prob >= self._speech_threshold
        barge_in_triggered = False
        pre_roll_pcm = b""

        if assistant_speaking:
            rms_gate = max(self._min_rms_floor, self._snr_multiplier * self._noise_floor_rms)
            if prob >= self._barge_in_threshold and frame_rms >= rms_gate:
                self._barge_in_streak += 1
                self._barge_in_dips = 0
            elif self._barge_in_streak > 0 and self._barge_in_dips == 0 and prob >= 0.5:
                # Tolerate 1 brief inter-syllable dip without losing barge-in momentum
                self._barge_in_dips += 1
            else:
                self._barge_in_streak = 0
                self._barge_in_dips = 0

            if self._barge_in_streak >= self._barge_in_frames_needed:
                barge_in_triggered = True
                pre_roll_pcm = b"".join(self._pre_roll)
                self._barge_in_streak = 0
                self._barge_in_dips = 0
        else:
            self._barge_in_streak = 0
            self._barge_in_dips = 0

        return VADDecision(
            speech_prob=prob,
            frame_rms=frame_rms,
            noise_floor_rms=self._noise_floor_rms,
            is_speech=is_speech,
            barge_in_triggered=barge_in_triggered,
            pre_roll_pcm=pre_roll_pcm,
        )

