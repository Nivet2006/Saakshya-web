"""Comprehensive tests for Sections A-G: Gnani config, dedicated numeric/entity parsers,
optional secondary recognition, mandatory spoken confirmation, and accuracy metrics.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings, build_contextual_stt_options  # noqa: E402
from app.extraction.extractor import VisitFieldExtractor  # noqa: E402
from app.extraction.metrics import NumericEvalCase, evaluate_transcripts  # noqa: E402
from app.extraction.numbers import (  # noqa: E402
    decimal_to_float,
    find_weight_candidates,
    format_decimal_clean,
    parse_decimal_phrase,
    resolve_beneficiary_id_mention,
)
from app.extraction.secondary_recognition import (  # noqa: E402
    assess_numeric_uncertainty,
    compare_numeric_interpretations,
)
from app.healthcare.pipeline import HealthcareSessionPipeline  # noqa: E402
from app.voice.interfaces import ChatMessage, TranscriptEvent  # noqa: E402
from app.voice.orchestration.session import VoiceSessionOrchestrator  # noqa: E402
from app.voice.stt.gnani_prisma import GnaniPrismaSTTAdapter  # noqa: E402

REF_DATE = date(2026, 11, 21)


# ---------------------------------------------------------------------------
# Section A & D: Outgoing Gnani Prisma v3.0 configuration & context headers
# ---------------------------------------------------------------------------


def test_gnani_adapter_outgoing_headers_and_context_not_overloaded() -> None:
    settings = Settings(
        GNANI_API_KEY="test-key-not-real",
        GNANI_STT_MODEL="prisma-v3.0",
        AUDIO_SAMPLE_RATE=16000,
    )
    assert settings.gnani_stt_format == "transcribe"

    ctx = build_contextual_stt_options(
        beneficiary_name="Baby of Kavitha Rao",
        beneficiary_id="BEN-1044",
        previous_text="Namaste! Are you visiting Baby of Kavitha Rao today?",
    )
    adapter = GnaniPrismaSTTAdapter.from_settings(
        settings,
        language_code="indic-auto",
        keywords=ctx["keywords"],
        speaker_names=ctx["speaker_names"],
        previous_text=ctx["previous_text"],
        topic=ctx["topic"],
    )
    headers = adapter.build_headers("req_test_1")

    assert headers["x-model"] == "prisma-v3.0"
    assert headers["x-format"] == "transcribe"
    assert headers["lang_code"] == "indic-auto"
    assert headers["x-language-candidates"] == ",".join(settings.prisma_language_candidates)
    assert set(headers["x-language-candidates"].split(",")) == {"hi-IN", "en-IN", "kn-IN", "ta-IN"}
    assert headers["x-sample-rate"] == "16000"
    assert headers["x-partials"] == "true"

    kw = json.loads(headers["x-keywords"])
    assert "Baby of Kavitha Rao" in kw
    assert "Kavitha Rao" in kw
    assert "BEN-1044" in kw
    # Must NOT overload with unrelated beneficiaries when a beneficiary is selected
    assert "Anitha Sharma" not in kw
    assert "Meena Selvam" not in kw
    assert len(kw) < 80

    sp = json.loads(headers["x-speaker-names"])
    assert sp == ["Baby of Kavitha Rao", "Kavitha Rao"]
    assert headers["x-previous-text"] == "Namaste! Are you visiting Baby of Kavitha Rao today?"
    assert "ASHA community health" in headers["x-topic"]

    diag = adapter.inspect_connection_config()
    assert diag["outgoing_headers"]["x-api-key-id"] == "***"
    assert diag["output_format"] == "transcribe"


# ---------------------------------------------------------------------------
# Section C: Dedicated multilingual, mixed-language & exact Decimal parsers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("phrase", "expected_decimal"),
    [
        ("2.8", "2.8"),
        ("2 . 8", "2.8"),
        ("two point eight", "2.8"),
        ("point five", "0.5"),
        ("two point zero eight", "2.08"),
        ("two point eighty five", "2.85"),
        ("fifty two point five", "52.5"),
        ("छियालीस", "46"),
        ("बयालीस", "42"),
        ("अड़तीस", "38"),
        ("पैंतालीस", "45"),
        ("tirpan dashamlav do", "53.2"),
        ("दो दशमलव आठ", "2.8"),
        ("दो पॉइंट आठ", "2.8"),
        ("साढ़े तीन", "3.5"),
        ("सवा तीन", "3.25"),
        ("पौने तीन", "2.75"),
        ("ಎರಡು ಪಾಯಿಂಟ್ ಎಂಟು", "2.8"),
        ("eradu point entu", "2.8"),
        ("ಐವತ್ತೆರಡು", "52"),
        ("aivatteradu", "52"),
        ("ಒಂದೂವರೆ", "1.5"),
        ("ಎರಡೂವರೆ", "2.5"),
        ("ಇಪ್ಪತ್ತೆಂಟು", "28"),
        ("இரண்டு புள்ளி எட்டு", "2.8"),
        ("irandu pulli ettu", "2.8"),
        ("ஐம்பத்து இரண்டு", "52"),
        ("ஒன்றரை", "1.5"),
        ("teen point five", "3.5"),
        ("two thousand आठ सौ", "2800"),
    ],
)
def test_exact_decimal_multilingual_number_parsing(phrase: str, expected_decimal: str) -> None:
    parsed = parse_decimal_phrase(phrase)
    assert parsed is not None
    assert parsed == Decimal(expected_decimal)


@pytest.mark.parametrize(
    ("utterance", "expected_kg", "expected_unit"),
    [
        ("weight is 2.8 kg", Decimal("2.8"), "kg"),
        ("baby weight 2,800 grams", Decimal("2.8"), "g"),
        ("weight two kilo पाँच सौ gram", Decimal("2.5"), "compound_kg_g"),
        ("weight 3 kg 50 gm", Decimal("3.05"), "compound_kg_g"),
        ("weight 750 grams", Decimal("0.75"), "g"),
        ("ತೂಕ ಎರಡು ಪಾಯಿಂಟ್ ಎಂಟು ಕೆಜಿ", Decimal("2.8"), "kg"),
        ("ತೂಕ ಎರಡು ಕೆಜಿ ಎಂಟು ನೂರು ಗ್ರಾಂ", Decimal("2.8"), "compound_kg_g"),
        ("எடை இரண்டு புள்ளி எட்டு கிலோ", Decimal("2.8"), "kg"),
        ("वजन 2 किलो 800 ग्राम", Decimal("2.8"), "compound_kg_g"),
    ],
)
def test_weight_unit_and_mixed_language_exact_decimal(
    utterance: str, expected_kg: Decimal, expected_unit: str
) -> None:
    cands = find_weight_candidates(utterance)
    assert len(cands) >= 1
    assert cands[-1].value_kg.quantize(Decimal("0.001")) == expected_kg.quantize(Decimal("0.001"))
    assert cands[-1].unit_kind == expected_unit


def test_beneficiary_id_asr_artifacts_and_multilingual_digits() -> None:
    cases = [
        ("Beneficiary ID BE. N 1044", "BEN-1044"),
        ("B.E.N. 1056", "BEN-1056"),
        ("BEN ten forty four", "BEN-1044"),
        ("BEN ಒಂದು ಸೊನ್ನೆ ನಾಲ್ಕು ನಾಲ್ಕು", "BEN-1044"),
        ("BEN ஒன்று பூஜ்ஜியம் நான்கு இரண்டு", "BEN-1042"),
        ("बीईएन १०४५", "BEN-1045"),
        ("BEN 1042 nahi BEN 1044", "BEN-1044"),
    ]
    for text, expected in cases:
        bid, _src, _corr, conflicts = resolve_beneficiary_id_mention(text)
        assert conflicts == []
        assert bid == expected, f"Failed for {text!r}: got {bid}"


def test_repeated_corrections_vs_conflicts_in_single_utterance() -> None:
    ext = VisitFieldExtractor()

    # Repeated numeric correction in same utterance -> selects corrected value
    r_corr = ext.extract("Newborn visit, weight is 2.6 kilo, no, 2.8 kilo.", reference_date=REF_DATE)
    assert r_corr.patch["weight_kg"] == 2.8
    assert r_corr.detected_correction is True

    # Repeated date correction in same utterance -> selects corrected date
    r_date_corr = ext.extract("Next visit 25 November, actually 28 November.", reference_date=REF_DATE)
    assert r_date_corr.patch["next_visit_date"] == "2026-11-28"
    assert r_date_corr.detected_correction is True

    # Conflicting values with NO correction bridge -> asks clarification, never guesses!
    r_conf = ext.extract("Weight is 2.6 or 2.8 kilo.", reference_date=REF_DATE)
    assert "weight_kg" not in r_conf.patch
    assert any(c.field_name == "weight_kg" and c.reason == "conflict" for c in r_conf.clarifications)

    # Unitless 2800 for newborn -> clarifies grams vs kg instead of silently storing 2800 kg
    r_unit = ext.extract("Kavitha newborn weight is 2800.", reference_date=REF_DATE)
    assert "weight_kg" not in r_unit.patch
    assert any("2800 grams" in c.prompt_hint for c in r_unit.clarifications)

    # Kannada & Tamil dates
    r_kn_d = ext.extract("ಮುಂದಿನ ಭೇಟಿ ನಾಳೆ", reference_date=REF_DATE)
    assert r_kn_d.patch["next_visit_date"] == "2026-11-22"
    r_ta_d = ext.extract("அடுத்த பார்வை 28 நவம்பர்", reference_date=REF_DATE)
    assert r_ta_d.patch["next_visit_date"] == "2026-11-28"


# ---------------------------------------------------------------------------
# Section E: Optional secondary recognition triggers & conservative comparison
# ---------------------------------------------------------------------------


def test_secondary_recognition_trigger_and_no_blind_majority() -> None:
    ext = VisitFieldExtractor()

    # Clean utterance MUST NOT trigger expensive secondary recognition
    clean_res = ext.extract("Newborn visit, weight is 2.8 kg.", reference_date=REF_DATE)
    assert assess_numeric_uncertainty("Newborn visit, weight is 2.8 kg.", clean_res).should_recheck is False

    # Low confidence or unparsed numeric cue or conflict MUST trigger
    assert assess_numeric_uncertainty(
        "Newborn visit, weight is 2.8 kg.", clean_res, stt_confidence=0.45
    ).should_recheck is True
    unparsed_res = ext.extract("baby weight some garbled noise kilo", reference_date=REF_DATE)
    assert assess_numeric_uncertainty(
        "baby weight some garbled noise kilo", unparsed_res
    ).should_recheck is True

    # Disagreement between primary and secondary NEVER blindly picks a winner
    p_res = ext.extract("Newborn visit, weight is 2.8 kg.", reference_date=REF_DATE)
    comp = compare_numeric_interpretations(
        p_res,
        "Newborn visit, weight is 3.8 kg.",
        extractor=ext,
        reference_date=REF_DATE,
    )
    assert comp.has_disagreement is True
    assert "weight_kg" in comp.disagreed_fields
    assert set(comp.candidate_values["weight_kg"]) == {"2.8", "3.8"}
    assert any(c.field_name == "weight_kg" and c.reason == "conflict" for c in comp.clarifications)


# ---------------------------------------------------------------------------
# Section F: Mandatory spoken confirmation flow
# ---------------------------------------------------------------------------


class _DummySTT:
    is_connected = True

    def __init__(self) -> None:
        self.q: asyncio.Queue[TranscriptEvent | None] = asyncio.Queue()

    async def connect(self) -> None:
        pass

    async def send_audio(self, pcm_chunk: bytes) -> None:
        pass

    async def events(self) -> AsyncIterator[TranscriptEvent]:
        while True:
            item = await self.q.get()
            if item is None:
                break
            yield item

    async def close(self) -> None:
        await self.q.put(None)


class _DummyTTS:
    sample_rate = 16000

    def __init__(self) -> None:
        self.spoken: list[str] = []

    async def connect(self) -> None:
        pass

    async def synthesize_stream(
        self, text: str, *, language: str | None = None, voice: str | None = None
    ) -> AsyncIterator[bytes]:
        self.spoken.append(text)
        yield b"\x01\x00" * 256

    async def cancel_active(self) -> None:
        pass

    async def close(self) -> None:
        pass


class _DummyLLM:
    provider_name = "mock"
    model_name = "mock"

    async def generate_reply(
        self,
        messages: list[ChatMessage],
        *,
        system_prompt: str,
        active_language: str,
        max_tokens: int = 160,
    ) -> str:
        return "Okay."


class _MockSecondaryRecognizer:
    def __init__(self, transcript: str) -> None:
        self.transcript = transcript
        self.calls = 0

    async def recognize_segment(self, pcm_bytes: bytes, **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        return {"transcript": self.transcript}


@pytest.mark.asyncio
async def test_mandatory_spoken_confirmation_yes_and_no_repeat() -> None:
    emitted: list[dict[str, Any]] = []

    async def emit(ev: dict[str, Any]) -> None:
        emitted.append(ev)

    stt = _DummySTT()
    tts = _DummyTTS()
    sec = _MockSecondaryRecognizer("Newborn visit, weight is 2.8 kg.")
    pipeline = HealthcareSessionPipeline(
        session_id="sess_secf",
        worker_id="ASHA-DEMO-01",
        language="en-IN",
        beneficiary_id="BEN-1044",
        reference_date=REF_DATE,
        continuous_editing=True,
        secondary_recognizer=sec,
        confirm_important_numbers=True,
    )
    orch = VoiceSessionOrchestrator(
        session_id="sess_secf",
        stt=stt,
        tts=tts,
        llm=_DummyLLM(),
        vad=None,
        emit=emit,
        default_language="en-IN",
        on_partial_hook=pipeline.on_partial_transcript,
        on_final_hook=pipeline.on_final_transcript,
    )
    pipeline.attach_orchestrator(orch)
    await orch.start()
    await pipeline.start_session_greeting(orch)
    await orch.handle_text_input("Yes")
    await asyncio.sleep(0.03)

    # 1. Worker speaks baby weight -> asks mandatory spoken confirmation!
    await orch.handle_text_input("Newborn visit. Baby weight is 2.8 kilograms.")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.weight_kg is None  # NOT silently confirmed yet
    assert "I heard the baby's weight as 2.8 kilograms. Is that correct?" in tts.spoken[-1]
    assert sec.calls == 0  # Clean utterance did NOT trigger duplicate recognition!

    # 2. Worker says NO -> asks to repeat, does NOT store unconfirmed 2.8
    await orch.handle_text_input("No")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.weight_kg is None
    assert "repeat the weight" in tts.spoken[-1].lower()

    # 3. Worker repeats corrected value 2.9 kg -> updates observation cleanly
    await orch.handle_text_input("2.9 kilograms")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.weight_kg == 2.9

    # 4. Now simulate low-confidence audio utterance triggering secondary recognition disagreement
    await stt.q.put(
        TranscriptEvent(
            event_type="final",
            text="Weight is 3.8 kilograms",
            is_final=True,
            language_code="en-IN",
            confidence=0.40,
            metadata={"utterance_pcm": b"\x01\x00" * 1600, "sample_rate": 16000},
        )
    )
    await asyncio.sleep(0.05)
    assert sec.calls == 1
    # Never silently replaced 2.9 with 3.8 or 2.8!
    assert pipeline.sm.visit.weight_kg == 2.9
    assert "conflicting weights" in tts.spoken[-1].lower()

    await orch.close()


# ---------------------------------------------------------------------------
# Section G: Evaluation metrics computation
# ---------------------------------------------------------------------------


def test_metrics_report_measures_all_seven_dimensions() -> None:
    cases = [
        NumericEvalCase(
            case_id="C1",
            language="en-IN",
            spoken_text="Baby of Kavitha Rao newborn visit weight 2.8 kg next visit 28 November BEN-1044",
            expected_weight_kg=Decimal("2.8"),
            expected_unit_kind="kg",
            expected_has_decimal=True,
            expected_next_visit_date="2026-11-28",
            expected_beneficiary_id="BEN-1044",
        ),
        NumericEvalCase(
            case_id="C2",
            language="hi-IN",
            spoken_text="वजन 2800 ग्राम अगला विजिट 7 दिन बाद",
            expected_weight_kg=Decimal("2.8"),
            expected_unit_kind="g",
            expected_has_decimal=True,
            expected_next_visit_date="2026-11-28",
        ),
    ]
    report = evaluate_transcripts(
        cases,
        {c.case_id: c.spoken_text for c in cases},
        mode_label="unit_test_clean",
        reference_date=REF_DATE,
    )
    assert report.numeric_exact_match_accuracy == 1.0
    assert report.decimal_accuracy == 1.0
    assert report.unit_recognition_accuracy == 1.0
    assert report.date_accuracy == 1.0
    assert report.beneficiary_id_accuracy == 1.0
    assert report.numeric_omission_rate == 0.0
    assert report.incorrect_numeric_confirmation_rate == 0.0


# ---------------------------------------------------------------------------
# Follow-up Improvements: Indic compounds, ambiguous dates, ring buffer PCM,
# multi-field numeric confirmation, and WS context reconnect
# ---------------------------------------------------------------------------


def test_indic_systematic_compounds_and_half_idioms_and_dmy_mdy_flag() -> None:
    from app.extraction.dates import find_date_candidates
    from app.extraction.numbers import parse_decimal_phrase

    ext = VisitFieldExtractor()
    assert parse_decimal_phrase("ಇಪ್ಪತ್ತೆರಡು") == Decimal("22")
    assert parse_decimal_phrase("ನಲವತ್ತೆಂಟು") == Decimal("48")
    assert parse_decimal_phrase("முப்பத்தைந்து") == Decimal("35")
    assert parse_decimal_phrase("do aur aadha") == Decimal("2.5")
    assert parse_decimal_phrase("ಮೂರು ಮತ್ತು ಅರ್ಧ") == Decimal("3.5")

    res = ext.extract("वजन दो और आधा किलो", reference_date=REF_DATE, active_language="hi-IN")
    assert res.patch.get("weight_kg") == 2.5

    cands_ambig = find_date_candidates("next visit on 05/07/2026", reference_date=REF_DATE)
    assert cands_ambig and cands_ambig[0].ambiguous_dmy_mdy is True
    cands_unambig = find_date_candidates("next visit on 25/11/2026", reference_date=REF_DATE)
    assert cands_unambig and cands_unambig[0].ambiguous_dmy_mdy is False


@pytest.mark.asyncio
async def test_session_utterance_keyed_pcm_preserves_overlapping_segments_without_vad() -> None:
    emitted: list[dict[str, Any]] = []
    final_events: list[TranscriptEvent] = []

    async def emit(ev: dict[str, Any]) -> None:
        emitted.append(ev)

    async def on_final(ev: TranscriptEvent, _orch: VoiceSessionOrchestrator) -> bool:
        final_events.append(ev)
        return True

    stt = _DummySTT()
    tts = _DummyTTS()
    orch = VoiceSessionOrchestrator(
        session_id="sess_pcm_ring",
        stt=stt,
        tts=tts,
        llm=_DummyLLM(),
        vad=None,
        emit=emit,
        default_language="en-IN",
        on_final_hook=on_final,
    )
    await orch.start()

    # Stream tagged PCM chunks (>0.5s per utterance so pre-roll doesn't cross segments)
    await orch.handle_audio_chunk(b"\x01\x01" * 1600)  # pre-roll 1
    await stt.q.put(TranscriptEvent(event_type="speech_start", utterance_id="utt-1"))
    await asyncio.sleep(0.01)
    await orch.handle_audio_chunk(b"\x02\x02" * 6400)  # utt-1 body
    await orch.handle_audio_chunk(b"\x00\x00" * 9000)  # 0.56s tail silence before utt-2 starts

    # Overlapping speech_start for utt-2 (BEFORE utt-1 ends/finalizes) MUST NOT wipe utt-1 audio!
    await stt.q.put(TranscriptEvent(event_type="speech_start", utterance_id="utt-2"))
    await asyncio.sleep(0.01)
    await orch.handle_audio_chunk(b"\x03\x03" * 9000)  # utt-2 body (>0.5s)

    await stt.q.put(TranscriptEvent(event_type="speech_end", utterance_id="utt-1"))
    await stt.q.put(
        TranscriptEvent(event_type="final", utterance_id="utt-1", text="weight 2.8 kg", is_final=True)
    )
    await asyncio.sleep(0.02)

    await orch.handle_audio_chunk(b"\x04\x04" * 3200)  # utt-2 tail
    await stt.q.put(TranscriptEvent(event_type="speech_end", utterance_id="utt-2"))
    await stt.q.put(
        TranscriptEvent(event_type="final", utterance_id="utt-2", text="temp 100 F", is_final=True)
    )
    await asyncio.sleep(0.02)

    assert len(final_events) == 2
    pcm_1 = final_events[0].metadata.get("utterance_pcm", b"")
    pcm_2 = final_events[1].metadata.get("utterance_pcm", b"")
    assert b"\x02\x02" * 100 in pcm_1
    assert b"\x04\x04" not in pcm_1
    assert b"\x04\x04" * 100 in pcm_2
    assert b"\x02\x02" not in pcm_2
    await orch.close()


@pytest.mark.asyncio
async def test_multi_field_mandatory_confirmation_and_secondary_vital_conflict() -> None:
    emitted: list[dict[str, Any]] = []

    async def emit(ev: dict[str, Any]) -> None:
        emitted.append(ev)

    stt = _DummySTT()
    tts = _DummyTTS()
    sec = _MockSecondaryRecognizer("Temperature is 99.1 F.")
    pipeline = HealthcareSessionPipeline(
        session_id="sess_multinum",
        worker_id="ASHA-DEMO-01",
        language="en-IN",
        beneficiary_id="BEN-1044",
        reference_date=REF_DATE,
        continuous_editing=True,
        secondary_recognizer=sec,
        confirm_important_numbers=True,
    )
    orch = VoiceSessionOrchestrator(
        session_id="sess_multinum",
        stt=stt,
        tts=tts,
        llm=_DummyLLM(),
        vad=None,
        emit=emit,
        default_language="en-IN",
        on_partial_hook=pipeline.on_partial_transcript,
        on_final_hook=pipeline.on_final_transcript,
    )
    pipeline.attach_orchestrator(orch)
    await orch.start()
    await pipeline.start_session_greeting(orch)
    await orch.handle_text_input("Yes")
    await asyncio.sleep(0.03)

    # 1. Next visit date gated -> YES confirms it
    await orch.handle_text_input("Next visit on 28 November 2026")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.next_visit_date is None
    assert "next visit date" in tts.spoken[-1].lower() and "correct?" in tts.spoken[-1].lower()
    await orch.handle_text_input("Yes")
    await asyncio.sleep(0.03)
    assert pipeline.sm.visit.next_visit_date == "2026-11-28"

    # 2. Non-danger temperature gated -> NO rejects -> bare number repeat "98.6" updates observation!
    await orch.handle_text_input("Temp 98.4 F")
    await asyncio.sleep(0.03)
    assert not any(o.get("key") == "temperature" for o in pipeline.sm.visit.observations)
    assert "temperature" in tts.spoken[-1].lower()
    await orch.handle_text_input("No")
    await asyncio.sleep(0.03)
    assert "repeat the temperature" in tts.spoken[-1].lower()
    await orch.handle_text_input("98.6")
    await asyncio.sleep(0.03)
    temp_obs = [o for o in pipeline.sm.visit.observations if o.get("key") == "temperature"]
    assert len(temp_obs) == 1 and float(temp_obs[0]["value"]) == 98.6

    # 3. Hemoglobin & BP gated -> confirm cleanly
    await orch.handle_text_input("Hb 11.2 g/dL")
    await asyncio.sleep(0.03)
    assert not any(o.get("key") == "hemoglobin_g_dl" for o in pipeline.sm.visit.observations)
    await orch.handle_text_input("Yes")
    await asyncio.sleep(0.03)
    hb_obs = [o for o in pipeline.sm.visit.observations if o.get("key") == "hemoglobin_g_dl"]
    assert len(hb_obs) == 1 and float(hb_obs[0]["value"]) == 11.2

    # 4. Secondary vital disagreement (98.8 vs 99.1) does NOT overwrite 98.6 silently!
    await stt.q.put(
        TranscriptEvent(
            event_type="final",
            text="Temp 98.8 F",
            is_final=True,
            language_code="en-IN",
            confidence=0.45,
            metadata={"utterance_pcm": b"\x05\x05" * 1600, "sample_rate": 16000},
        )
    )
    await asyncio.sleep(0.05)
    assert sec.calls == 1
    temp_obs_after = [o for o in pipeline.sm.visit.observations if o.get("key") == "temperature"]
    assert float(temp_obs_after[0]["value"]) == 98.6
    assert "conflicting temperature" in tts.spoken[-1].lower()

    await orch.close()


@pytest.mark.asyncio
async def test_gnani_prisma_reconnect_with_context_refreshes_headers() -> None:
    from app.voice.stt.gnani_prisma import GnaniPrismaSTTAdapter

    adapter = GnaniPrismaSTTAdapter(
        api_key="test-key",
        ws_url="wss://example.invalid/stt/v3/stream",
        language_code="indic-auto",
        language_candidates=["hi-IN", "kn-IN"],
        speaker_names=["Kavitha"],
        keywords=["ASHA", "HBNC"],
    )
    connect_calls: list[dict[str, str]] = []
    close_calls = 0

    async def fake_close_only() -> None:
        nonlocal close_calls
        close_calls += 1

    async def fake_connect() -> None:
        connect_calls.append(adapter.build_headers("req-test"))

    adapter._close_socket_only = fake_close_only  # type: ignore[method-assign]
    adapter.connect = fake_connect  # type: ignore[method-assign]

    adapter.update_context(speaker_names=["Lakshmi Devi", "Savitri"], keywords=["IFA", "DPT"])
    await adapter.reconnect_with_context()
    assert close_calls == 1
    assert len(connect_calls) == 1
    assert "Lakshmi Devi" in connect_calls[0]["x-speaker-names"]
    assert "IFA" in connect_calls[0]["x-keywords"]
    assert adapter._closed is False

