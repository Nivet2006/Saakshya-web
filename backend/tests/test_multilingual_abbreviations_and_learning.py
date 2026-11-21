"""Tests for language switching, regional/medical abbreviations, worker learning, and structured conversion."""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

from app.conversation.models import detect_language_switch_command
from app.extraction.abbreviations import normalize_healthcare_abbreviations
from app.extraction.extractor import VisitFieldExtractor
from app.healthcare.pipeline import HealthcareSessionPipeline
from app.services.worker_memory import WorkerCorrectionMemory
from app.voice.interfaces import TranscriptEvent
from app.voice.orchestration.session import VoiceSessionOrchestrator
from tests.test_healthcare_e2e import _DummyLLM, _DummySTT, _DummyTTS


def test_explicit_spoken_language_switching() -> None:
    assert detect_language_switch_command("Please speak in Tamil") == "ta-IN"
    assert detect_language_switch_command("Switch to Kannada") == "kn-IN"
    assert detect_language_switch_command("Hindi mein baat karo") == "hi-IN"
    assert detect_language_switch_command("Telugu lo matladu") == "te-IN"
    assert detect_language_switch_command("English please") == "en-IN"
    assert detect_language_switch_command("தமிழில் பேசு") == "ta-IN"
    # Normal clinical note mentioning a language should NOT trigger a switch
    assert detect_language_switch_command("Patient weight is 52 kg") is None


def test_healthcare_abbreviation_normalization_and_extraction() -> None:
    raw = (
        "a.n.c checkup for Lakshmi Devi. b.p 120/80, h.b 10.5, "
        "sp o 2 98%, p.r 84, r.r 20, r.b.s 110, e.b.f started, k.m.c started, "
        "o.r.s and zinc given, e.d.d 2026-12-15."
    )
    norm = normalize_healthcare_abbreviations(raw)
    assert "ANC" in norm
    assert "BP" in norm
    assert "Hb" in norm
    assert "SpO2" in norm
    assert "ORS" in norm
    assert "KMC" in norm

    extractor = VisitFieldExtractor()
    res = extractor.extract(raw, reference_date=date(2026, 11, 22))
    assert res.patch["visit_type"] == "ANC"
    assert res.patch["beneficiary_id"] == "BEN-1042"
    obs_by_key = {o.key: o for o in res.observations}
    assert obs_by_key["blood_pressure"].value == "120/80"
    assert obs_by_key["hemoglobin_g_dl"].value == 10.5
    assert obs_by_key["spo2_pct"].value == 98.0
    assert obs_by_key["pulse_rate_bpm"].value == 84.0
    assert obs_by_key["respiratory_rate"].value == 20.0
    assert obs_by_key["blood_sugar_mg_dl"].value == 110.0
    assert "ors_zinc_therapy" in obs_by_key
    assert "newborn_care_note" in obs_by_key
    assert "edd_date" in obs_by_key


def test_regional_words_across_indic_languages() -> None:
    extractor = VisitFieldExtractor()
    # Telugu ANC + fever temperature
    te = extractor.extract("గర్భిణీ విజిట్ జ్వరం 100.4", reference_date=date(2026, 11, 22))
    assert te.patch["visit_type"] == "ANC"
    assert any(o.key == "temperature" and o.value == 100.4 for o in te.observations)

    # Malayalam Newborn + height
    ml = extractor.extract("നവജാതശിശു ഉയരം 51 cm", reference_date=date(2026, 11, 22))
    assert ml.patch["visit_type"] == "Newborn"
    assert any(o.key == "height_cm" and o.value == 51.0 for o in ml.observations)

    # Marathi Immunisation
    mr = extractor.extract("लसीकरण भेट ओपीव्ही", reference_date=date(2026, 11, 22))
    assert mr.patch["visit_type"] == "Immunisation"


def test_worker_correction_memory_learns_and_applies(tmp_path: Path) -> None:
    store_path = tmp_path / "worker_corr.json"
    mem = WorkerCorrectionMemory(storage_path=store_path)
    mem.record_correction(
        "ASHA-42",
        wrong_phrase="eye fa",
        corrected_phrase="IFA",
        field_name="clinical_note",
    )
    mem.record_correction(
        "ASHA-42",
        wrong_phrase="amc",
        corrected_phrase="ANC",
        field_name="visit_type",
    )

    # Reload from disk to verify persistence
    mem2 = WorkerCorrectionMemory(storage_path=store_path)
    updated, applied = mem2.apply_learned_corrections(
        "ASHA-42", "amc visit taking eye fa tablets regularly"
    )
    assert "ANC visit" in updated
    assert "IFA tablets" in updated
    assert len(applied) == 2
    assert "IFA" in mem2.get_worker_bias_keywords("ASHA-42")


def test_pipeline_language_switch_and_worker_learning_e2e(tmp_path: Path) -> None:
    async def _run() -> None:
        events: list[dict] = []

        async def _emit(ev: dict) -> None:
            events.append(ev)

        mem = WorkerCorrectionMemory(storage_path=tmp_path / "mem.json")
        pipeline = HealthcareSessionPipeline(
            session_id="sess-lang-learn",
            worker_id="ASHA-99",
            language="hi-IN",
            beneficiary_id="BEN-1042",
            worker_memory=mem,
        )
        orch = VoiceSessionOrchestrator(
            session_id="sess-lang-learn",
            stt=_DummySTT(),
            tts=_DummyTTS(),
            llm=_DummyLLM(),
            vad=None,
            emit=_emit,
            default_language="hi-IN",
            language_locked=True,
        )
        pipeline.attach_orchestrator(orch)

        # Confirm beneficiary identity
        await pipeline.on_final_transcript(
            TranscriptEvent(event_type="final", text="Yes"), orch
        )

        # Spoken language switch to Tamil
        handled = await pipeline.on_final_transcript(
            TranscriptEvent(event_type="final", text="Please speak in Tamil"), orch
        )
        assert handled is True
        assert pipeline.language == "ta-IN"
        assert orch.active_language == "ta-IN"
        assert any(e["type"] == "language_switched" and e["language"] == "ta-IN" for e in events)

        # Worker speaks a correction: "not amc, ANC"
        await pipeline.on_final_transcript(
            TranscriptEvent(event_type="final", text="not amc, ANC"), orch
        )
        summary = mem.get_worker_summary("ASHA-99")
        assert len(summary["phrase_corrections"]) == 1
        assert summary["phrase_corrections"][0]["corrected_phrase"] == "ANC"

        # Subsequent utterance with ASR error "amc" is auto-normalized to ANC structured record
        await pipeline.on_final_transcript(
            TranscriptEvent(event_type="final", text="amc checkup b.p 110/70 spo2 99"), orch
        )
        contract = pipeline.current_visit_contract()
        assert contract["visit_type"] == "ANC"

        await orch.close()

    asyncio.run(_run())
