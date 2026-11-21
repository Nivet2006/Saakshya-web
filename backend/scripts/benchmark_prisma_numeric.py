#!/usr/bin/env python3
"""Live Gnani Prisma v3.0 Numeric & Entity Accuracy Benchmark (Transcribe vs Code-Mix).

Synthesizes realistic ASHA speech recordings via Gnani Timbre v3.0 across:
- Clean English & Hinglish code-mixed utterances
- Naturally spoken decimals ("two point eight", "fifty two point five")
- Grams & kilograms ("2800 grams", "three kilo two hundred grams")
- Dates ("28 November", "after 7 days")
- Spoken Beneficiary IDs ("BEN 1044", "B E N 1056")
- Regional phrasing (Hindi, Kannada, Tamil)
- Repeated numerical corrections ("weight 2.6 kilo, no, 2.8 kilo")
- Noisy recordings (synthetic 14 dB SNR street/household background noise)

Runs the EXACT SAME audio recordings through live Gnani Prisma v3.0 in both:
  1. `format="transcribe"` (ITN enabled, contextual keywords + speaker_names + previous_text + topic)
  2. `format="codemix"` (same audio & context, format="codemix")

Reports all 7 Section G metrics side-by-side without claiming any unmeasured results.
"""

from __future__ import annotations

import asyncio
import io
import json
import sys
import time
import wave
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from gnani.stt import GnaniSTTClient  # noqa: E402

from app.core.config import build_contextual_stt_options, get_settings  # noqa: E402
from app.extraction.extractor import VisitFieldExtractor  # noqa: E402
from app.extraction.metrics import NumericEvalCase, evaluate_transcripts  # noqa: E402
from app.extraction.secondary_recognition import (  # noqa: E402
    GnaniRestSecondaryRecognizer,
    assess_numeric_uncertainty,
    compare_numeric_interpretations,
)
from app.voice.stt.gnani_prisma import GnaniPrismaSTTAdapter  # noqa: E402
from app.voice.tts.gnani_timbre import GnaniTimbreTTSAdapter  # noqa: E402

REF_DATE = date(2026, 11, 21)


@dataclass(frozen=True)
class BenchmarkSpeechCase:
    eval_case: NumericEvalCase
    tts_voice: str = "Avinash"
    add_noise_snr_db: float | None = None
    noise_profile: str = "broadband"  # "broadband" | "street_babble" | "clipped_low_gain"
    beneficiary_name: str | None = None
    previous_text: str | None = None


BENCHMARK_CASES: tuple[BenchmarkSpeechCase, ...] = (
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B01_newborn_decimal_en",
            language="en-IN",
            category="decimal",
            spoken_text="Baby of Kavitha Rao newborn visit. Weight is two point eight kilograms. Beneficiary ID B E N one zero four four.",
            expected_weight_kg=Decimal("2.8"),
            expected_unit_kind="kg",
            expected_has_decimal=True,
            expected_beneficiary_id="BEN-1044",
        ),
        tts_voice="Avinash",
        beneficiary_name="Baby of Kavitha Rao",
        previous_text="Namaste! Are you visiting Baby of Kavitha Rao today?",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B02_anc_decimal_hinglish",
            language="hi-IN",
            category="codemix",
            spoken_text="Today I visited Lakshmi Devi, ANC checkup completed. Weight is fifty two point five kilo, next visit twenty eighth November.",
            expected_weight_kg=Decimal("52.5"),
            expected_unit_kind="kg",
            expected_has_decimal=True,
            expected_next_visit_date="2026-11-28",
            expected_beneficiary_id="BEN-1042",
        ),
        tts_voice="Shivani",
        beneficiary_name="Lakshmi Devi",
        previous_text="Namaste! Are you visiting Lakshmi Devi today?",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B03_grams_to_kg_en",
            language="en-IN",
            category="clean",
            spoken_text="Newborn HBNC visit, weight is two thousand eight hundred grams. Next visit after seven days.",
            expected_weight_kg=Decimal("2.8"),
            expected_unit_kind="g",
            expected_has_decimal=True,
            expected_next_visit_date="2026-11-28",
        ),
        tts_voice="Devansh",
        beneficiary_name="Baby of Kavitha Rao",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B04_compound_kg_grams",
            language="en-IN",
            category="decimal",
            spoken_text="Meena Selvam immunisation visit. Weight is three kilo two hundred grams. Next visit fifth December.",
            expected_weight_kg=Decimal("3.2"),
            expected_unit_kind="compound_kg_g",
            expected_has_decimal=True,
            expected_next_visit_date="2026-12-05",
            expected_beneficiary_id="BEN-1046",
        ),
        tts_voice="Lakshmi",
        beneficiary_name="Meena Selvam",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B05_noisy_decimal_14db",
            language="en-IN",
            category="noisy",
            spoken_text="Anitha Sharma ANC checkup, weight is fifty four point two kilograms, beneficiary ID B E N one zero five six.",
            expected_weight_kg=Decimal("54.2"),
            expected_unit_kind="kg",
            expected_has_decimal=True,
            expected_beneficiary_id="BEN-1056",
        ),
        tts_voice="Avinash",
        add_noise_snr_db=14.0,
        beneficiary_name="Anitha Sharma",
        previous_text="Please tell me the beneficiary details and weight.",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B06_noisy_hinglish_14db",
            language="hi-IN",
            category="noisy",
            spoken_text="Sunita Kumari ANC visit, वजन पचास किलो, next visit twenty fifth November.",
            expected_weight_kg=Decimal("50"),
            expected_unit_kind="kg",
            expected_has_decimal=False,
            expected_next_visit_date="2026-11-25",
            expected_beneficiary_id="BEN-1045",
        ),
        tts_voice="Shivani",
        add_noise_snr_db=14.0,
        beneficiary_name="Sunita Kumari",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B07_repeated_correction",
            language="en-IN",
            category="correction",
            spoken_text="Newborn weight is two point six kilo, no, two point eight kilo.",
            expected_weight_kg=Decimal("2.8"),
            expected_unit_kind="kg",
            expected_has_decimal=True,
        ),
        tts_voice="Avinash",
        beneficiary_name="Baby of Kavitha Rao",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B08_hindi_decimal",
            language="hi-IN",
            category="regional",
            spoken_text="नवजात शिशु का वजन दो दशमलव आठ किलो है, अगला विजिट अट्ठाईस नवंबर।",
            expected_weight_kg=Decimal("2.8"),
            expected_unit_kind="kg",
            expected_has_decimal=True,
            expected_next_visit_date="2026-11-28",
        ),
        tts_voice="Shivani",
        beneficiary_name="Baby of Kavitha Rao",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B09_kannada_maternal_regional",
            language="kn-IN",
            category="regional",
            spoken_text="ಕವಿತಾ ರಾವ್, ಬಾಣಂತಿ ಭೇಟಿ, ತೂಕ ಐವತ್ತೆರಡು ಪಾಯಿಂಟ್ ಎಂಟು ಕೆಜಿ.",
            expected_weight_kg=Decimal("52.8"),
            expected_unit_kind="kg",
            expected_has_decimal=True,
            expected_beneficiary_id="BEN-1043",
        ),
        tts_voice="Lakshmi",
        beneficiary_name="Kavitha Rao",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B10_tamil_regional",
            language="ta-IN",
            category="regional",
            spoken_text="மீனா செல்வம் பார்வை, எடை ஆறு புள்ளி ஐந்து கிலோ.",
            expected_weight_kg=Decimal("6.5"),
            expected_unit_kind="kg",
            expected_has_decimal=True,
            expected_beneficiary_id="BEN-1046",
        ),
        tts_voice="Lakshmi",
        beneficiary_name="Meena Selvam",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B11_kannada_newborn_decimal",
            language="kn-IN",
            category="regional",
            spoken_text="ಬೇಬಿ ಆಫ್ ಕವಿತಾ ರಾವ್, ನವಜಾತ ಶಿಶು, ತೂಕ ಎರಡು ಪಾಯಿಂಟ್ ಎಂಟು ಕೆಜಿ.",
            expected_weight_kg=Decimal("2.8"),
            expected_unit_kind="kg",
            expected_has_decimal=True,
            expected_beneficiary_id="BEN-1044",
        ),
        tts_voice="Lakshmi",
        beneficiary_name="Baby of Kavitha Rao",
    ),
    # --- Hard / adversarial cases (low-SNR non-stationary noise, code-mixed numerals, conflicts) ---
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B12_hinglish_do_point_aath",
            language="hi-IN",
            category="codemix",
            spoken_text="Baby weight do point aath kilo hai, next visit do December.",
            expected_weight_kg=Decimal("2.8"),
            expected_unit_kind="kg",
            expected_has_decimal=True,
            expected_next_visit_date="2026-12-02",
        ),
        tts_voice="Shivani",
        beneficiary_name="Baby of Kavitha Rao",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B13_marathi_adhich_kilo",
            language="mr-IN",
            category="regional",
            spoken_text="नवजात बाळाचे वजन अडीच किलो आहे.",
            expected_weight_kg=Decimal("2.5"),
            expected_unit_kind="kg",
            expected_has_decimal=True,
        ),
        tts_voice="Shivani",
        beneficiary_name="Baby of Kavitha Rao",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B14_kannada_compound_kg_g",
            language="kn-IN",
            category="regional",
            spoken_text="ಮಗುವಿನ ತೂಕ ಮೂರು ಕೆಜಿ ಇನ್ನೂರು ಗ್ರಾಂ.",
            expected_weight_kg=Decimal("3.2"),
            expected_unit_kind="compound_kg_g",
            expected_has_decimal=True,
        ),
        tts_voice="Lakshmi",
        beneficiary_name="Baby of Kavitha Rao",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B15_street_noise_8db",
            language="en-IN",
            category="noisy",
            spoken_text="Sunita Devi ANC visit, weight is fifty six point five kg, HB eleven point four, next visit first December.",
            expected_weight_kg=Decimal("56.5"),
            expected_unit_kind="kg",
            expected_has_decimal=True,
            expected_next_visit_date="2026-12-01",
            expected_observations={"hemoglobin_g_dl": Decimal("11.4")},
        ),
        tts_voice="Avinash",
        add_noise_snr_db=8.0,
        noise_profile="street_babble",
        beneficiary_name="Sunita Devi",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B16_low_gain_babble_9db",
            language="hi-IN",
            category="noisy",
            spoken_text="नवजात वजन तीन किलो दो सौ ग्राम, लाभार्थी आईडी बी ई एन एक शून्य चार चार.",
            expected_weight_kg=Decimal("3.2"),
            expected_unit_kind="compound_kg_g",
            expected_has_decimal=True,
            expected_beneficiary_id="BEN-1044",
        ),
        tts_voice="Shivani",
        add_noise_snr_db=9.0,
        noise_profile="clipped_low_gain",
        beneficiary_name="Baby of Kavitha Rao",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B17_stream_paused_correction",
            language="en-IN",
            category="correction",
            spoken_text="Newborn weight is two point six kilograms, no, weight is two point eight kilograms.",
            expected_weight_kg=Decimal("2.8"),
            expected_unit_kind="kg",
            expected_has_decimal=True,
        ),
        tts_voice="Avinash",
        beneficiary_name="Baby of Kavitha Rao",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B18_adversarial_unitless_2800",
            language="en-IN",
            category="adversarial",
            spoken_text="Baby weight is two thousand eight hundred.",
            expected_weight_kg=None,
            expect_clarification_instead_of_confirm=True,
        ),
        tts_voice="Devansh",
        beneficiary_name="Baby of Kavitha Rao",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B19_adversarial_conflict_26_or_28",
            language="en-IN",
            category="adversarial",
            spoken_text="Baby weight was two point six or two point eight kilo.",
            expected_weight_kg=None,
            expect_clarification_instead_of_confirm=True,
        ),
        tts_voice="Avinash",
        beneficiary_name="Baby of Kavitha Rao",
    ),
    BenchmarkSpeechCase(
        eval_case=NumericEvalCase(
            case_id="B20_codemix_date_id_ben1042",
            language="hi-IN",
            category="codemix",
            spoken_text="Lakshmi Devi ANC checkup, next visit ten days baad, beneficiary ID BEN one zero four two.",
            expected_next_visit_date="2026-12-01",
            expected_beneficiary_id="BEN-1042",
        ),
        tts_voice="Shivani",
        beneficiary_name="Lakshmi Devi",
    ),
)


def _degrade_pcm(
    pcm: bytes,
    *,
    snr_db: float,
    profile: str = "broadband",
    seed: int = 42,
    sample_rate: int = 16000,
) -> bytes:
    """Apply realistic household/street noise and mic degradation to 16-bit PCM."""
    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float64)
    n = len(samples)
    if n == 0:
        return pcm
    rng = np.random.default_rng(seed)

    if profile == "clipped_low_gain":
        # Low-gain field microphone + fan hum + occasional sharp spike clipping
        samples = samples * 0.22
        spike_idx = rng.integers(0, max(1, n - 400), size=max(1, n // 16000))
        for idx in spike_idx:
            samples[idx : idx + 250] += rng.choice([-18000.0, 18000.0])

    sig_power = float(np.mean(samples ** 2)) + 1e-9
    noise_power = sig_power / (10.0 ** (snr_db / 10.0))

    if profile == "street_babble":
        # Non-stationary modulated street + multi-speaker chatter + 100Hz fan/traffic rumble
        t = np.arange(n, dtype=np.float64) / float(sample_rate)
        env = 0.5 + 0.5 * np.sin(2.0 * np.pi * 2.3 * t + rng.uniform(0, 3.14))
        white = rng.normal(0.0, 1.0, size=n)
        # Simple 5-tap moving average shapes speech-band babble + low rumble
        babble = np.convolve(white, np.array([0.15, 0.22, 0.26, 0.22, 0.15]), mode="same") * env
        rumble = 0.45 * np.sin(2.0 * np.pi * 110.0 * t) + 0.35 * np.sin(2.0 * np.pi * 220.0 * t)
        noise = babble + rumble
        noise *= np.sqrt(noise_power / (float(np.mean(noise ** 2)) + 1e-9))
    else:
        noise = rng.normal(0.0, np.sqrt(noise_power), size=n)

    mixed = np.clip(samples + noise, -32768.0, 32767.0).astype(np.int16)
    return mixed.tobytes()


def _pcm_to_wav(pcm: bytes, sample_rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return buf.getvalue()


async def _transcribe_streaming_ws(
    pcm: bytes,
    *,
    settings: Any,
    ctx: dict[str, Any],
    output_format: str = "transcribe",
) -> tuple[str, list[str], float]:
    """Stream PCM chunks over live Gnani Prisma WebSocket and collect final transcripts."""
    t0 = time.perf_counter()
    adapter = GnaniPrismaSTTAdapter(
        api_key=settings.gnani_api_key.get_secret_value(),
        ws_url=settings.gnani_stt_ws_url,
        language_code="indic-auto",
        output_format=output_format,
        model=settings.gnani_stt_model,
        sample_rate=16000,
        enable_partials=True,
        language_candidates=settings.prisma_language_candidates,
        keywords=ctx["keywords"],
        speaker_names=ctx["speaker_names"],
        previous_text=ctx["previous_text"],
        topic=ctx["topic"],
        min_silence_ms=min(settings.endpoint_silence_ms, 900),
    )
    finals: list[str] = []
    done = asyncio.Event()

    async def _reader() -> None:
        async for ev in adapter.events():
            if ev.event_type == "final" and ev.text.strip():
                finals.append(ev.text.strip())
                done.set()

    await adapter.connect()
    reader_task = asyncio.create_task(_reader())
    try:
        frame_bytes = 1024  # 32 ms @ 16kHz mono s16le
        for offset in range(0, len(pcm), frame_bytes):
            await adapter.send_audio(pcm[offset : offset + frame_bytes])
            await asyncio.sleep(0.020)
        # Wait up to 3.5s after audio while streaming trailing silence frames
        silence = b"\x00" * frame_bytes
        for _ in range(55):
            if done.is_set():
                # Drain brief pause for any split second segment
                await asyncio.sleep(0.35)
                break
            await adapter.send_audio(silence)
            await asyncio.sleep(0.032)
        if not done.is_set():
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(done.wait(), timeout=2.5)
    finally:
        await adapter.close()
        reader_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await reader_task
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return " ".join(finals).strip(), finals, elapsed_ms


async def _run_ws_context_ab_check(
    rest_client: GnaniSTTClient,
    settings: Any,
    pcm_by_id: dict[str, bytes],
) -> dict[str, Any]:
    """Compare WS vs REST proper-noun/entity recognition with & without contextual headers."""
    probe_id = "B04_compound_kg_grams"
    pcm = pcm_by_id.get(probe_id)
    if not pcm:
        return {}
    wav = _pcm_to_wav(pcm)
    results: dict[str, Any] = {}
    for label, with_ctx in (("without_context", False), ("with_context", True)):
        ctx = (
            build_contextual_stt_options(
                beneficiary_name="Meena Selvam",
                beneficiary_id="BEN-1046",
                previous_text="Visiting Meena Selvam for immunisation and weight check.",
            )
            if with_ctx
            else {
                "keywords": [],
                "speaker_names": [],
                "previous_text": "",
                "topic": "",
            }
        )
        rest_res = rest_client.transcribe_bytes(
            wav,
            filename=f"{probe_id}_{label}.wav",
            language_code="indic-auto",
            model="prisma-v3.0",
            format="transcribe",
            language_candidates=settings.prisma_language_candidates,
            keywords=ctx["keywords"] or None,
            speaker_names=ctx["speaker_names"] or None,
            previous_text=ctx["previous_text"] or None,
            topic=ctx["topic"] or None,
        )
        ws_txt, _, ws_ms = await _transcribe_streaming_ws(
            pcm, settings=settings, ctx=ctx, output_format="transcribe"
        )
        results[label] = {
            "rest_transcript": str(rest_res.get("transcript", "")).strip(),
            "ws_transcript": ws_txt,
            "ws_latency_ms": round(ws_ms, 1),
        }
    return results


async def run_live_benchmark(*, include_ws: bool = True) -> dict[str, Any]:
    settings = get_settings()
    missing = settings.validate_live_credentials()
    if missing:
        raise RuntimeError(f"Missing required env vars for live benchmark: {missing}")

    print(
        f"[BENCH] Synthesizing {len(BENCHMARK_CASES)} synthetic ASHA speech fixtures via Gnani Timbre v3.0...",
        flush=True,
    )
    tts = GnaniTimbreTTSAdapter.from_settings(settings)
    await tts.connect()
    pcm_fixtures: dict[str, bytes] = {}
    wav_fixtures: dict[str, bytes] = {}
    try:
        for idx, bcase in enumerate(BENCHMARK_CASES):
            ec = bcase.eval_case
            buf = bytearray()
            async for chunk in tts.synthesize_stream(
                ec.spoken_text, language=ec.language, voice=bcase.tts_voice
            ):
                buf.extend(chunk)
            pcm = bytes(buf)
            if bcase.add_noise_snr_db is not None:
                pcm = _degrade_pcm(
                    pcm,
                    snr_db=bcase.add_noise_snr_db,
                    profile=bcase.noise_profile,
                    seed=100 + idx,
                )
            pcm_fixtures[ec.case_id] = pcm
            wav_fixtures[ec.case_id] = _pcm_to_wav(pcm)
    finally:
        await tts.close()

    rest_client = GnaniSTTClient(api_key=settings.gnani_api_key.get_secret_value(), timeout=30)
    transcripts_by_mode: dict[str, dict[str, str]] = {"transcribe": {}, "codemix": {}}
    if include_ws:
        transcripts_by_mode["ws_transcribe"] = {}
    ws_split_segments: dict[str, list[str]] = {}
    rest_latencies_ms: dict[str, list[float]] = {"transcribe": [], "codemix": [], "ws_transcribe": []}

    for fmt in ("transcribe", "codemix"):
        print(f"[BENCH] Evaluating live Gnani Prisma v3.0 REST in format={fmt!r}...", flush=True)
        for bcase in BENCHMARK_CASES:
            ec = bcase.eval_case
            ctx = build_contextual_stt_options(
                beneficiary_name=bcase.beneficiary_name,
                beneficiary_id=ec.expected_beneficiary_id,
                previous_text=bcase.previous_text,
            )
            t0 = time.perf_counter()
            res = rest_client.transcribe_bytes(
                wav_fixtures[ec.case_id],
                filename=f"{ec.case_id}.wav",
                language_code="indic-auto",
                model="prisma-v3.0",
                format=fmt,
                language_candidates=settings.prisma_language_candidates,
                keywords=ctx["keywords"],
                speaker_names=ctx["speaker_names"] or None,
                previous_text=ctx["previous_text"] or None,
                topic=ctx["topic"],
            )
            rest_latencies_ms[fmt].append((time.perf_counter() - t0) * 1000.0)
            transcript = str(res.get("transcript", "")).strip()
            transcripts_by_mode[fmt][ec.case_id] = transcript
            print(
                f"  [{fmt}] {ec.case_id} ({res.get('detected_language_code')}): {transcript}",
                flush=True,
            )

    if include_ws:
        print("[BENCH] Evaluating live Gnani Prisma v3.0 Streaming WS in format='transcribe'...", flush=True)
        for bcase in BENCHMARK_CASES:
            ec = bcase.eval_case
            ctx = build_contextual_stt_options(
                beneficiary_name=bcase.beneficiary_name,
                beneficiary_id=ec.expected_beneficiary_id,
                previous_text=bcase.previous_text,
            )
            ws_txt, ws_parts, ws_ms = await _transcribe_streaming_ws(
                pcm_fixtures[ec.case_id], settings=settings, ctx=ctx, output_format="transcribe"
            )
            transcripts_by_mode["ws_transcribe"][ec.case_id] = ws_txt
            ws_split_segments[ec.case_id] = ws_parts
            rest_latencies_ms["ws_transcribe"].append(ws_ms)
            print(
                f"  [ws_transcribe] {ec.case_id} ({len(ws_parts)} segs, {ws_ms:.0f}ms): {ws_txt}",
                flush=True,
            )

    # Measure secondary recognition triggers, disagreements & latency overhead
    ext = VisitFieldExtractor()
    sec_rec = GnaniRestSecondaryRecognizer(
        api_key=settings.gnani_api_key.get_secret_value(),
        secondary_format=settings.gnani_stt_secondary_format,
        model=settings.gnani_stt_model,
    )
    secondary_stats: dict[str, Any] = {
        "triggered_cases": [],
        "disagreed_cases": [],
        "latencies_ms": [],
    }
    for bcase in BENCHMARK_CASES:
        ec = bcase.eval_case
        prim_txt = transcripts_by_mode["transcribe"][ec.case_id]
        prim_ext = ext.extract(prim_txt, reference_date=REF_DATE, active_language=ec.language)
        uncert = assess_numeric_uncertainty(prim_txt, prim_ext)
        if uncert.should_recheck:
            ctx = build_contextual_stt_options(
                beneficiary_name=bcase.beneficiary_name,
                beneficiary_id=ec.expected_beneficiary_id,
                previous_text=bcase.previous_text,
            )
            t0 = time.perf_counter()
            sec_res = await sec_rec.recognize_segment(
                pcm_fixtures[ec.case_id],
                sample_rate=16000,
                language_code="indic-auto",
                language_candidates=settings.prisma_language_candidates,
                keywords=ctx["keywords"],
                speaker_names=ctx["speaker_names"],
                previous_text=ctx["previous_text"],
                topic=ctx["topic"],
            )
            sec_ms = (time.perf_counter() - t0) * 1000.0
            sec_txt = str(sec_res.get("transcript", "")).strip()
            comp = compare_numeric_interpretations(
                prim_ext, sec_txt, extractor=ext, reference_date=REF_DATE, active_language=ec.language
            )
            secondary_stats["triggered_cases"].append(
                {"case_id": ec.case_id, "reasons": list(uncert.reasons), "latency_ms": round(sec_ms, 1)}
            )
            secondary_stats["latencies_ms"].append(round(sec_ms, 1))
            if comp.has_disagreement:
                secondary_stats["disagreed_cases"].append(
                    {"case_id": ec.case_id, "fields": comp.disagreed_fields, "candidates": comp.candidate_values}
                )

    eval_cases = [b.eval_case for b in BENCHMARK_CASES]
    reports: dict[str, Any] = {}
    for mode_key in transcripts_by_mode:
        reports[mode_key] = evaluate_transcripts(
            eval_cases,
            transcripts_by_mode[mode_key],
            mode_label=f"prisma-v3.0_{mode_key}",
            reference_date=REF_DATE,
        )

    # Per-language breakdown on primary transcribe mode
    per_language: dict[str, dict[str, Any]] = {}
    for lang in sorted({b.eval_case.language for b in BENCHMARK_CASES}):
        lang_cases = [b.eval_case for b in BENCHMARK_CASES if b.eval_case.language == lang]
        rep = evaluate_transcripts(
            lang_cases,
            transcripts_by_mode["transcribe"],
            mode_label=f"transcribe_{lang}",
            reference_date=REF_DATE,
        )
        per_language[lang] = rep.to_dict()

    ws_context_ab = await _run_ws_context_ab_check(rest_client, settings, pcm_fixtures)

    summary = {
        mode_key: rep.to_dict() for mode_key, rep in reports.items()
    }
    summary["per_language_transcribe"] = per_language
    summary["secondary_recognition"] = secondary_stats
    summary["ws_split_segments"] = {k: v for k, v in ws_split_segments.items() if len(v) > 1}
    summary["ws_context_ab_check"] = ws_context_ab
    summary["avg_latency_ms"] = {
        k: round(sum(v) / len(v), 1) if v else 0.0 for k, v in rest_latencies_ms.items()
    }
    summary["transcripts"] = transcripts_by_mode

    print("\n=== LIVE PRISMA V3.0 BENCHMARK SUMMARY ===", flush=True)
    for label, rep in reports.items():
        print(
            f"\nMode: {label} (avg latency {summary['avg_latency_ms'].get(label, 0.0)} ms)\n"
            f"  Numeric exact-match accuracy:          {rep.numeric_exact_match_accuracy*100:.1f}%\n"
            f"  Decimal accuracy:                      {rep.decimal_accuracy*100:.1f}%\n"
            f"  Unit recognition accuracy:             {rep.unit_recognition_accuracy*100:.1f}%\n"
            f"  Date accuracy:                         {rep.date_accuracy*100:.1f}%\n"
            f"  Beneficiary ID accuracy:               {rep.beneficiary_id_accuracy*100:.1f}%\n"
            f"  Numeric omission rate:                 {rep.numeric_omission_rate*100:.1f}%\n"
            f"  Incorrect numeric confirmation rate:   {rep.incorrect_numeric_confirmation_rate*100:.1f}%\n"
            f"  Counts: {rep.counts}\n"
            f"  Failures: {rep.failures}",
            flush=True,
        )
    print("\n--- Per-language breakdown (REST transcribe) ---", flush=True)
    for lang, d in per_language.items():
        print(
            f"  {lang} (n={d['total_cases']}): exact={d['numeric_exact_match_accuracy']*100:.1f}%, "
            f"dec={d['decimal_accuracy']*100:.1f}%, unit={d['unit_recognition_accuracy']*100:.1f}%, "
            f"date={d['date_accuracy']*100:.1f}%, id={d['beneficiary_id_accuracy']*100:.1f}%, "
            f"omission={d['numeric_omission_rate']*100:.1f}%, bad_confirm={d['incorrect_numeric_confirmation_rate']*100:.1f}%",
            flush=True,
        )
    print(f"\n--- Secondary Recognition Overhead ---\n  {secondary_stats}", flush=True)
    print(f"\n--- WS Context Header A/B Check ---\n  {ws_context_ab}", flush=True)
    return summary


if __name__ == "__main__":
    import contextlib

    result = asyncio.run(run_live_benchmark(include_ws="--no-ws" not in sys.argv))
    if "--json-out" in sys.argv:
        idx = sys.argv.index("--json-out")
        if idx + 1 < len(sys.argv):
            out_path = Path(sys.argv[idx + 1])
            out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

