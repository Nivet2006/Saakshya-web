"""Comprehensive remediation verification suite:
1. Multilingual & code-mixed numeric parsing + preservation of unusual values.
2. Multi-stage UtteranceExtractionTrace provenance.
3. Dynamic extensible observations, repeatable immunisation events, in-place updates & removals.
4. Synthetic noisy-environment VAD / high-pass filtering / pause hysteresis / clipping telemetry.
5. Immediate full-duplex barge-in with stale-turn suppression.
"""

from __future__ import annotations

import math
import struct
from datetime import date

import pytest

from app.core.config import Settings
from app.extraction.extractor import VisitFieldExtractor
from app.healthcare.pipeline import HealthcareSessionPipeline
from app.voice.interfaces import TranscriptEvent
from app.voice.orchestration.session import VoiceSessionOrchestrator
from app.voice.vad.silero_onnx import SileroOnnxVAD

# ---------------------------------------------------------------------------
# 1. Multilingual numeric normalization & multi-stage trace
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("utterance", "expected_kg"),
    [
        ("One kilogram", 1.0),
        ("Two point eight kilo", 2.8),
        ("2 kilo 800 grams", 2.8),
        ("ಎರಡು ಪಾಯಿಂಟ್ ಎಂಟು ಕಿಲೋ", 2.8),
        ("ಎರಡು ಕಿಲೋ ಎಂಟು ನೂರು ಗ್ರಾಂ", 2.8),
        ("ढाई किलो", 2.5),
        ("Weight is two point five", 2.5),
        ("Weight is three kilo", 3.0),
        ("Weight should be 2.8", 2.8),
    ],
)
def test_multilingual_numeric_weight_extraction(utterance: str, expected_kg: float) -> None:
    extractor = VisitFieldExtractor()
    res = extractor.extract(utterance, reference_date=date(2026, 11, 21))
    assert res.patch.get("weight_kg") == pytest.approx(expected_kg)
    assert res.trace is not None
    assert res.trace.raw_transcript == utterance
    assert len(res.trace.extracted_numbers) >= 1
    assert res.trace.extracted_numbers[0]["value"] == pytest.approx(expected_kg)


def test_spoken_date_twenty_eight_november_and_compound_update() -> None:
    extractor = VisitFieldExtractor()
    res_date = extractor.extract("Next visit Twenty-eight November", reference_date=date(2026, 11, 21))
    assert res_date.patch.get("next_visit_date") == "2026-11-28"

    res_combo = extractor.extract(
        "Weight should be 2.8 and next visit December 10.",
        reference_date=date(2026, 11, 21),
    )
    assert res_combo.patch.get("weight_kg") == pytest.approx(2.8)
    assert res_combo.patch.get("next_visit_date") == "2026-12-10"


def test_unusual_weight_preserved_as_needs_confirmation_never_discarded() -> None:
    extractor = VisitFieldExtractor()
    res = extractor.extract("Newborn weight is 48 kilo", reference_date=date(2026, 11, 21))
    # Scalar field stays unpatched until clarified, while unusual observation + clarification preserve the spoken value
    assert "weight_kg" not in res.patch
    assert any(
        c.field_name == "weight_kg" and any(x in c.candidates for x in ("48", "48.0"))
        for c in res.clarifications
    )
    assert any(
        o.key == "weight_kg" and o.value == pytest.approx(48.0) and o.status == "needs_confirmation"
        for o in res.observations
    )
    assert res.trace is not None
    assert any(
        n.get("field") == "weight_kg" and n.get("status") == "needs_confirmation"
        for n in res.trace.extracted_numbers
    )


# ---------------------------------------------------------------------------
# 2. Dynamic observations, repeatable events & removals
# ---------------------------------------------------------------------------


def test_dynamic_observations_repeatable_events_and_removals() -> None:
    extractor = VisitFieldExtractor()
    draft = extractor.extract(
        "Visit for Baby of Kavitha Rao, newborn visit.",
        reference_date=date(2026, 11, 21),
    )
    visit_draft = extractor.apply_to_draft(
        extractor.apply_to_draft.__globals__["VisitDraft"](visit_id="v-dyn-1")
        if "VisitDraft" in extractor.apply_to_draft.__globals__
        else __import__("app.extraction.models", fromlist=["VisitDraft"]).VisitDraft(visit_id="v-dyn-1"),
        draft,
    )

    obs_res = extractor.extract(
        "Length is 50 cm, temperature 37.2 C, Hb is 11.5, breastfeeding well. BCG given, OPV and Pentavalent due.",
        reference_date=date(2026, 11, 21),
        existing_draft=visit_draft,
    )
    visit_draft = extractor.apply_to_draft(visit_draft, obs_res)

    obs_keys = {o.key for o in visit_draft.observations}
    assert {"height_cm", "temperature", "hemoglobin_g_dl", "feeding_status"} <= obs_keys

    events_by_name = {e.name: e for e in visit_draft.events}
    assert events_by_name["BCG"].status == "completed"
    assert events_by_name["OPV"].status == "due"
    assert events_by_name["Pentavalent"].status == "due"

    # Update OPV status in-place without duplicating events
    upd_res = extractor.extract(
        "Actually, OPV was also given.",
        reference_date=date(2026, 11, 21),
        existing_draft=visit_draft,
    )
    visit_draft = extractor.apply_to_draft(visit_draft, upd_res, correction_mode=True)
    opv_events = [e for e in visit_draft.events if e.name == "OPV"]
    assert len(opv_events) == 1
    assert opv_events[0].status == "completed"

    # Remove feeding observation cleanly
    rm_res = extractor.extract(
        "Remove that feeding observation",
        reference_date=date(2026, 11, 21),
        existing_draft=visit_draft,
    )
    visit_draft = extractor.apply_to_draft(visit_draft, rm_res, correction_mode=True)
    assert all(o.key != "feeding_status" for o in visit_draft.observations)


def test_routine_visit_followup_deduplicated_on_date_edit() -> None:
    extractor = VisitFieldExtractor()
    from app.extraction.models import VisitDraft

    d = VisitDraft(visit_id="v-dedup-1", visit_type="Newborn")
    r1 = extractor.extract("Weight is 2.8 kg and next visit December 5.", reference_date=date(2026, 11, 21))
    d = extractor.apply_to_draft(d, r1)
    r2 = extractor.extract("Next visit December 10.", reference_date=date(2026, 11, 21), existing_draft=d)
    d = extractor.apply_to_draft(d, r2)

    routine = [a for a in d.follow_up_actions if a.action_type == "routine_visit"]
    assert len(routine) == 1
    assert routine[0].due_date == "2026-12-10"


# ---------------------------------------------------------------------------
# 3. Synthetic noisy environment audio & Silero VAD verification
# ---------------------------------------------------------------------------


def _pcm_frame(samples_f32: list[float]) -> bytes:
    ints = [max(-32768, min(32767, int(round(s * 32767.0)))) for s in samples_f32]
    return struct.pack(f"<{len(ints)}h", *ints)


def _sine_frame(freq_hz: float, amp: float, sample_idx_start: int, sr: int = 16000) -> bytes:
    samples = [
        amp * math.sin(2.0 * math.pi * freq_hz * ((sample_idx_start + i) / sr))
        for i in range(512)
    ]
    return _pcm_frame(samples)


def test_vad_filters_55hz_fan_rumble_and_counts_clipping_and_hysteresis() -> None:
    vad = SileroOnnxVAD(speech_threshold=0.55, start_confirm_frames=2, hangover_frames=12)

    # 1. Sustained 55 Hz low-frequency fan/motor hum at 0.14 amplitude should be suppressed by 85 Hz HPF
    fan_speech_hits = 0
    for f_idx in range(25):
        frame = _sine_frame(55.0, 0.14, f_idx * 512)
        dec = vad.process_frame(frame, assistant_speaking=False)
        if dec.is_speech:
            fan_speech_hits += 1
    assert fan_speech_hits == 0

    # 2. Single-frame 300 Hz transient impulse must NOT trigger speech start (needs 2 consecutive frames)
    vad.reset()
    imp = _sine_frame(350.0, 0.45, 0)
    dec1 = vad.process_frame(imp, assistant_speaking=False)
    dec_quiet = vad.process_frame(b"\x00" * 1024, assistant_speaking=False)
    assert not dec1.speech_started
    assert not dec_quiet.is_speech

    # 3. Sustained speech + clipping detection
    vad.reset()
    clipped_frame = _pcm_frame([1.2 if (i % 2 == 0) else -1.2 for i in range(512)])
    dec_clip = vad.process_frame(clipped_frame, assistant_speaking=False)
    assert dec_clip.clipped_samples == 512
    diag = vad.diagnostics()
    assert diag["total_clipped_samples"] == 512
    assert diag["total_frames"] > 0


def test_default_endpoint_silence_tolerate_long_natural_pauses() -> None:
    s = Settings(_env_file=None)
    assert s.endpoint_silence_ms >= 1300
    assert s.barge_in_vad_threshold >= 0.65


# ---------------------------------------------------------------------------
# 4. Immediate barge-in & dynamic pipeline WS events
# ---------------------------------------------------------------------------


class _DummySTT:
    async def connect(self, language: str, sample_rate: int = 16000) -> None:
        return None

    async def send_audio(self, pcm_frame: bytes) -> None:
        return None

    async def end_utterance(self) -> None:
        return None

    async def receive_transcripts(self):
        if False:
            yield None

    async def close(self) -> None:
        return None


class _DummyLLM:
    async def stream_reply(self, prompt: str, history, language: str):
        yield "Ok."


class _SlowTTS:
    sample_rate: int = 16000

    def __init__(self) -> None:
        self.cancelled = False

    async def synthesize_stream(self, text: str, language: str, voice: str = "Shivani"):
        for seq in range(1, 20):
            if self.cancelled:
                break
            yield b"\x01\x00" * 256
            await __import__("asyncio").sleep(0.01)

    async def cancel_active(self) -> None:
        self.cancelled = True

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_immediate_barge_in_advances_turn_before_slow_tts_cancel_and_removes_items() -> None:
    emitted: list[dict] = []

    async def _send(ev: dict) -> None:
        emitted.append(ev)

    pipeline = HealthcareSessionPipeline(
        session_id="sess_rem_1",
        beneficiary_id="BEN-1044",
        continuous_editing=True,
    )
    tts = _SlowTTS()
    orch = VoiceSessionOrchestrator(
        session_id="sess_rem_1",
        stt=_DummySTT(),
        tts=tts,
        llm=_DummyLLM(),
        vad=SileroOnnxVAD(),
        emit=_send,
        on_final_hook=pipeline.on_final_transcript,
    )
    orch.active_turn_id = 3
    orch.assistant_speaking = True
    await orch.interrupt(trigger="client")

    assert orch.active_turn_id == 4
    assert tts.cancelled is True
    barge_evs = [e for e in emitted if e.get("type") == "barge_in"]
    cancel_evs = [e for e in emitted if e.get("type") == "tts_cancelled"]
    assert barge_evs and barge_evs[0]["cancelled_turn_id"] == 3 and barge_evs[0]["new_turn_id"] == 4
    assert cancel_evs and cancel_evs[0]["cancelled_turn_id"] == 3

    # Verify pipeline dynamic observation + removal via handle_remove_item
    pipeline.sm.start_beneficiary_greeting(language="en-IN")
    await orch.handle_text_input("Yes")
    await orch.handle_text_input("Newborn visit, length 50 cm, breastfeeding well, BCG given, OPV due.")
    contract = pipeline.current_visit_contract()
    assert any(o["key"] == "feeding_status" for o in contract.get("observations", []))
    assert any(e["name"] == "OPV" for e in contract.get("events", []))

    await pipeline.handle_remove_item(observation_key="feeding_status", orchestrator=orch)
    await pipeline.handle_remove_item(event_name="OPV", orchestrator=orch)
    contract_after = pipeline.current_visit_contract()
    assert all(o["key"] != "feeding_status" for o in contract_after.get("observations", []))
    assert all(e["name"] != "OPV" for e in contract_after.get("events", []))


def test_synthetic_noisy_environment_corpus_metrics() -> None:
    """Verify VAD noise rejection, SNR estimation, pause tolerance & barge-in false-trigger immunity."""
    scenarios = [
        ("quiet_silence", 0.0, 0.0, False),
        ("ceiling_fan_60hz_hum", 60.0, 0.12, False),
        ("outdoor_wind_rumble_45hz", 45.0, 0.16, False),
        ("street_traffic_50hz_rumble", 50.0, 0.14, False),
    ]
    for name, freq, amp, _expect_speech in scenarios:
        vad = SileroOnnxVAD(speech_threshold=0.6, barge_in_threshold=0.70, start_confirm_frames=2)
        barge_hits = 0
        speech_hits = 0
        for f_idx in range(30):
            frame = b"\x00" * 1024 if amp == 0.0 else _sine_frame(freq, amp, f_idx * 512)
            dec = vad.process_frame(frame, assistant_speaking=True)
            if dec.is_speech:
                speech_hits += 1
            if dec.barge_in_triggered:
                barge_hits += 1
        assert speech_hits == 0, f"{name} false speech triggers: {speech_hits}"
        assert barge_hits == 0, f"{name} false barge-in triggers during TTS: {barge_hits}"

    # Verify natural 800 ms pause (~25 frames) tolerances via endpointing config > 800ms
    s = Settings(_env_file=None)
    assert 800 < s.endpoint_silence_ms <= 2000
    assert vad._min_rms_floor >= 0.015
