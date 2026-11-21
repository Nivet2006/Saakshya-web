"""Zero-torch ONNX Silero VAD with high-pass rumble filter, hysteresis & dual-gate barge-in.

Uses `silero_vad.onnx` (bundled in `pipecat-ai`) directly via `onnxruntime` for
16 kHz / 512-sample (32 ms) PCM_S16LE frames.

Improvements for noisy household / outdoor environments & fast barge-in:
- Vectorized DC-offset removal + 85 Hz 1st-order high-pass filter before RMS/Silero
  inference to attenuate fan, AC, wind, and traffic rumble without cutting voice.
- Speech-start confirmation (`start_confirm_frames`) + silence hysteresis
  (`hangover_frames`) + pre-roll (`320 ms`) to avoid premature endpointing on natural
  pauses and prevent continuous false restarts on background TV/fan noise.
- Dual-gate barge-in: while `assistant_speaking=True`, triggers ONLY when BOTH Silero
  speech probability >= `barge_in_threshold` AND high-pass frame RMS >=
  `max(min_rms_floor, snr_multiplier * adaptive_noise_floor_rms)` are sustained for
  `barge_in_min_speech_ms`.
- Safe audio diagnostics: clipping sample count, adaptive noise floor, and SNR (dB).
"""

from __future__ import annotations

import logging
import math
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
        barge_in_threshold: float = 0.70,
        barge_in_min_speech_ms: int = 192,
        min_rms_floor: float = 0.015,
        snr_multiplier: float = 2.2,
        pre_roll_ms: int = 320,
        start_confirm_frames: int = 2,
        hangover_frames: int = 12,
        highpass_hz: float = 85.0,
    ) -> None:
        if sample_rate != 16000:
            raise ValueError("SileroOnnxVAD currently supports 16000 Hz frames")
        self._sample_rate = sample_rate
        self._speech_threshold = speech_threshold
        self._barge_in_threshold = max(barge_in_threshold, speech_threshold)
        self._barge_in_frames_needed = max(2, round(barge_in_min_speech_ms / 32.0))
        self._min_rms_floor = min_rms_floor
        self._snr_multiplier = snr_multiplier
        self._start_confirm_frames = max(1, start_confirm_frames)
        self._hangover_frames = max(1, hangover_frames)

        # 1st-order high-pass RC coefficient: alpha = RC / (RC + dt)
        if highpass_hz > 0:
            rc = 1.0 / (2.0 * math.pi * highpass_hz)
            dt = 1.0 / float(sample_rate)
            self._hp_alpha = rc / (rc + dt)
        else:
            self._hp_alpha = 0.0

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
        self._hp_prev_x: float = 0.0
        self._hp_prev_y: float = 0.0
        self._in_speech: bool = False
        self._speech_onset_streak: int = 0
        self._silence_hangover_count: int = 0
        self.total_frames: int = 0
        self.total_clipped_samples: int = 0
        self.speech_segments_started: int = 0
        self.speech_segments_ended: int = 0
        self.reset()

    def reset(self) -> None:
        """Reset Silero recurrent state, filter state, and hysteresis counters."""
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, CONTEXT_SAMPLES_16K), dtype=np.float32)
        self._barge_in_streak = 0
        self._barge_in_dips = 0
        self._hp_prev_x = 0.0
        self._hp_prev_y = 0.0
        self._in_speech = False
        self._speech_onset_streak = 0
        self._silence_hangover_count = 0
        self._pre_roll.clear()
        self._remainder = b""

    def reset_barge_in_streak(self) -> None:
        self._barge_in_streak = 0
        self._barge_in_dips = 0

    def _apply_highpass(self, samples: np.ndarray) -> np.ndarray:
        """Attenuate sub-85Hz rumble (fan/wind/AC/traffic) without distorting speech."""
        if self._hp_alpha <= 0.0 or samples.size == 0:
            return samples
        a = self._hp_alpha
        out = np.empty_like(samples)
        prev_x = self._hp_prev_x
        prev_y = self._hp_prev_y
        for i in range(samples.size):
            x = float(samples[i])
            y = a * (prev_y + x - prev_x)
            out[i] = y
            prev_x = x
            prev_y = y
        self._hp_prev_x = prev_x
        self._hp_prev_y = prev_y
        return out

    def diagnostics(self) -> dict[str, Any]:
        nf_db = 20.0 * math.log10(max(self._noise_floor_rms, 1e-6))
        return {
            "total_frames": self.total_frames,
            "total_clipped_samples": self.total_clipped_samples,
            "noise_floor_rms": round(self._noise_floor_rms, 6),
            "noise_floor_dbfs": round(nf_db, 2),
            "in_speech": self._in_speech,
            "speech_segments_started": self.speech_segments_started,
            "speech_segments_ended": self.speech_segments_ended,
        }

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
        any_started = False
        any_ended = False
        clipped_sum = 0
        while offset + FRAME_BYTES_16K <= len(buf):
            chunk = buf[offset : offset + FRAME_BYTES_16K]
            offset += FRAME_BYTES_16K
            last_decision = self._process_512_frame(chunk, assistant_speaking=assistant_speaking)
            any_started = any_started or last_decision.speech_started
            any_ended = any_ended or last_decision.speech_ended
            clipped_sum += last_decision.clipped_samples
            if last_decision.barge_in_triggered:
                self._remainder = buf[offset:]
                last_decision.speech_started = any_started
                last_decision.speech_ended = any_ended
                last_decision.clipped_samples = clipped_sum
                return last_decision

        self._remainder = buf[offset:]
        last_decision.speech_started = any_started
        last_decision.speech_ended = any_ended
        last_decision.clipped_samples = clipped_sum
        return last_decision

    def _process_512_frame(self, chunk: bytes, *, assistant_speaking: bool) -> VADDecision:
        self.total_frames += 1
        raw_i16 = np.frombuffer(chunk, dtype=np.int16)
        clipped = int(np.count_nonzero((raw_i16 >= 32760) | (raw_i16 <= -32760)))
        self.total_clipped_samples += clipped

        raw_samples = raw_i16.astype(np.float32) / 32768.0
        filtered = self._apply_highpass(raw_samples)
        frame_rms = float(np.sqrt(np.mean(filtered * filtered)))
        prob = self._infer_prob(filtered)

        self._pre_roll.append(chunk)

        # Update adaptive noise floor only during confident non-speech frames
        if prob < 0.35 and not self._in_speech:
            alpha = 0.05 if not assistant_speaking else 0.015
            self._noise_floor_rms = (1.0 - alpha) * self._noise_floor_rms + alpha * frame_rms

        snr_db = 20.0 * math.log10(max(frame_rms, 1e-6) / max(self._noise_floor_rms, 1e-6))
        rms_speech_gate = max(self._min_rms_floor * 0.65, 1.5 * self._noise_floor_rms)
        raw_speech = prob >= self._speech_threshold and frame_rms >= rms_speech_gate

        speech_started = False
        speech_ended = False
        if not self._in_speech:
            if raw_speech:
                self._speech_onset_streak += 1
                if self._speech_onset_streak >= self._start_confirm_frames:
                    self._in_speech = True
                    self._silence_hangover_count = 0
                    self.speech_segments_started += 1
                    speech_started = True
            else:
                self._speech_onset_streak = 0
        else:
            if raw_speech or prob >= (self._speech_threshold * 0.75):
                self._silence_hangover_count = 0
            else:
                self._silence_hangover_count += 1
                if self._silence_hangover_count >= self._hangover_frames:
                    self._in_speech = False
                    self._speech_onset_streak = 0
                    self._silence_hangover_count = 0
                    self.speech_segments_ended += 1
                    speech_ended = True

        is_speech = self._in_speech or raw_speech
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
            speech_started=speech_started,
            speech_ended=speech_ended,
            clipped_samples=clipped,
            snr_db=round(snr_db, 2),
        )
