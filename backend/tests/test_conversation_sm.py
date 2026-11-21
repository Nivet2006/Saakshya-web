"""Unit tests for Phase 2 Conversation State Machine, Read-Back & Escalation.

Covers:
- Happy path: IDLE -> GATHERING_NOTES -> EXTRACTING_FIELDS ->
  READ_BACK_CONFIRMATION -> READY_TO_CONFIRM -> confirmed ->
  persistence ack -> COMMITTED.
- Missing & ambiguous field clarification without re-asking confirmed fields.
- Single correction and repeated corrections (patches ONLY named field,
  preserves all other fields and danger flags, re-reads before confirmation).
- Explicit confirmation gate across multilingual phrases (never commits
  unconfirmed drafts; negation never falsely confirms).
- Failed persistence acknowledgement (stays out of COMMITTED, honest message,
  supports retry).
- Danger escalation interrupt from EVERY active state + partial/final
  idempotency + immutable alert preservation across resume/correction/abandon.
- Localized read-back generation across en-IN, hi-IN, kn-IN, ta-IN.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.conversation import (  # noqa: E402
    ActionType,
    ClarificationRequest,
    ConversationState,
    ConversationStateMachine,
    DangerAlertInput,
    ExtractionUpdate,
    InvalidTransitionError,
    VisitRecordState,
    VisitStatus,
    VisitType,
    classify_confirmation_intent,
    generate_read_back_text,
)


def _sample_full_extraction() -> ExtractionUpdate:
    return ExtractionUpdate(
        beneficiary_id="BEN-1042",
        beneficiary_name="Lakshmi Devi",
        visit_type=VisitType.ANC,
        weight_kg=52.5,
        vaccinations_completed=["TT-1"],
        vaccinations_due=["TT-2"],
        next_visit_date="2026-11-26",
        follow_up_actions=["Check hemoglobin at next ANC"],
    )


def _sample_danger_alert(
    canonical_id: str = "MATERNAL_SEVERE_BLEEDING",
    matched_phrase: str = "heavy bleeding",
    is_partial: bool = False,
) -> DangerAlertInput:
    return DangerAlertInput(
        canonical_id=canonical_id,
        category="maternal",
        display_name="Severe vaginal bleeding",
        matched_phrase=matched_phrase,
        guideline_reference="NHM_ASHA_MOD6_P18",
        severity="critical",
        is_partial=is_partial,
    )


# ---------------------------------------------------------------------------
# 1. Happy Path End-to-End Lifecycle
# ---------------------------------------------------------------------------


def test_happy_path_full_lifecycle() -> None:
    sm = ConversationStateMachine(session_id="sess_happy_1", language="en-IN")
    assert sm.state == ConversationState.IDLE
    assert sm.visit.status == VisitStatus.DRAFT

    # IDLE -> GATHERING_NOTES
    r_gather = sm.start_gathering()
    assert r_gather.previous_state == ConversationState.IDLE
    assert r_gather.current_state == ConversationState.GATHERING_NOTES

    # GATHERING_NOTES -> EXTRACTING_FIELDS
    r_ext_start = sm.begin_extraction()
    assert r_ext_start.current_state == ConversationState.EXTRACTING_FIELDS

    # EXTRACTING_FIELDS -> READ_BACK_CONFIRMATION
    r_rb = sm.apply_extraction(_sample_full_extraction())
    assert r_rb.previous_state == ConversationState.EXTRACTING_FIELDS
    assert r_rb.current_state == ConversationState.READ_BACK_CONFIRMATION
    assert r_rb.spoken_text is not None
    assert "Lakshmi Devi" in r_rb.spoken_text
    assert "BEN-1042" in r_rb.spoken_text
    assert "ANC" in r_rb.spoken_text
    assert "52.5 kg" in r_rb.spoken_text
    assert "TT-2" in r_rb.spoken_text
    assert "2026-11-26" in r_rb.spoken_text
    assert "Should I confirm this record?" in r_rb.spoken_text
    action_types = [a.action_type for a in r_rb.actions]
    assert ActionType.DRAFT_UPDATED in action_types
    assert ActionType.READ_BACK_STARTED in action_types
    assert ActionType.SPEAK in action_types

    # READ_BACK_CONFIRMATION -> READY_TO_CONFIRM
    r_ready = sm.on_read_back_completed()
    assert r_ready.previous_state == ConversationState.READ_BACK_CONFIRMATION
    assert r_ready.current_state == ConversationState.READY_TO_CONFIRM
    assert sm.visit.status == VisitStatus.DRAFT

    # Worker confirms -> status='confirmed', emits persistence_requested, NOT committed yet
    r_conf = sm.handle_confirmation_response("Yes, confirm")
    assert r_conf.current_state == ConversationState.READY_TO_CONFIRM
    assert sm.visit.status == VisitStatus.CONFIRMED
    assert sm.awaiting_persistence is True
    conf_types = [a.action_type for a in r_conf.actions]
    assert ActionType.WORKER_CONFIRMED in conf_types
    assert ActionType.PERSISTENCE_REQUESTED in conf_types
    assert ActionType.VISIT_COMMITTED not in conf_types

    # Persistence ack -> COMMITTED
    r_commit = sm.handle_persistence_result(accepted=True, record_id="visit_9001")
    assert r_commit.previous_state == ConversationState.READY_TO_CONFIRM
    assert r_commit.current_state == ConversationState.COMMITTED
    assert sm.visit.status == VisitStatus.COMMITTED
    assert sm.visit.record_id == "visit_9001"
    assert any(a.action_type == ActionType.VISIT_COMMITTED for a in r_commit.actions)

    # Verify exact recorded state progression
    states_visited = [ConversationState.IDLE] + [to_s for _, to_s, _ in sm.transition_history]
    assert states_visited == [
        ConversationState.IDLE,
        ConversationState.GATHERING_NOTES,
        ConversationState.EXTRACTING_FIELDS,
        ConversationState.READ_BACK_CONFIRMATION,
        ConversationState.READY_TO_CONFIRM,
        ConversationState.COMMITTED,
    ]


# ---------------------------------------------------------------------------
# 2. Missing & Ambiguous Field Clarification (Never Re-Ask Confirmed Fields)
# ---------------------------------------------------------------------------


def test_clarification_asks_only_missing_or_ambiguous_fields() -> None:
    sm = ConversationStateMachine(session_id="sess_clar_1", language="en-IN")

    # Turn 1: worker gives visit_type and weight, but beneficiary is ambiguous
    r1 = sm.apply_extraction(
        ExtractionUpdate(
            visit_type=VisitType.NEWBORN,
            weight_kg=2.9,
            clarifications=[
                ClarificationRequest(
                    field="beneficiary_id",
                    reason="ambiguous",
                    candidates=["Baby of Meena (BEN-2001)", "Baby of Meera (BEN-2002)"],
                )
            ],
        )
    )
    assert r1.current_state == ConversationState.CLARIFICATION_REQUIRED
    assert "visit_type" in sm.confirmed_fields
    assert "weight_kg" in sm.confirmed_fields
    assert len(r1.pending_clarifications) == 1
    assert r1.pending_clarifications[0].field == "beneficiary_id"
    assert r1.spoken_text is not None
    assert "BEN-2001" in r1.spoken_text
    assert "BEN-2002" in r1.spoken_text
    # Must NOT re-ask for already confirmed visit_type or weight
    assert "visit type" not in r1.spoken_text.lower()
    assert "weight" not in r1.spoken_text.lower()

    # Turn 2: worker disambiguates beneficiary -> moves straight to READ_BACK_CONFIRMATION
    r2 = sm.apply_extraction(
        ExtractionUpdate(
            beneficiary_id="BEN-2001",
            beneficiary_name="Baby of Meena",
        )
    )
    assert r2.current_state == ConversationState.READ_BACK_CONFIRMATION
    assert r2.pending_clarifications == []
    assert sm.visit.beneficiary_id == "BEN-2001"
    assert sm.visit.visit_type == VisitType.NEWBORN
    assert sm.visit.weight_kg == 2.9


def test_clarification_requires_at_least_one_clinical_observation() -> None:
    sm = ConversationStateMachine(session_id="sess_clar_2", language="en-IN")

    # Beneficiary & visit type present, but NO clinical observation yet
    r1 = sm.apply_extraction(
        ExtractionUpdate(beneficiary_id="BEN-1042", visit_type=VisitType.PNC)
    )
    assert r1.current_state == ConversationState.CLARIFICATION_REQUIRED
    assert [c.field for c in r1.pending_clarifications] == ["clinical_observation"]
    assert r1.spoken_text is not None
    assert "beneficiary" not in r1.spoken_text.lower()
    assert "visit type" not in r1.spoken_text.lower()

    # Adding just next_visit_date satisfies clinical observation requirement
    r2 = sm.apply_extraction(ExtractionUpdate(next_visit_date="2026-12-01"))
    assert r2.current_state == ConversationState.READ_BACK_CONFIRMATION


def test_ambiguous_date_clarification_blocks_read_back_until_resolved() -> None:
    sm = ConversationStateMachine(session_id="sess_clar_3", language="en-IN")

    r1 = sm.apply_extraction(
        ExtractionUpdate(
            beneficiary_id="BEN-1042",
            visit_type=VisitType.ANC,
            weight_kg=51.0,
            clarifications=[
                ClarificationRequest(
                    field="next_visit_date",
                    reason="ambiguous",
                    question="Did you mean 26 November or 3 December for the next visit?",
                )
            ],
        )
    )
    assert r1.current_state == ConversationState.CLARIFICATION_REQUIRED
    assert r1.spoken_text == "Did you mean 26 November or 3 December for the next visit?"

    r2 = sm.apply_extraction(ExtractionUpdate(next_visit_date="2026-11-26"))
    assert r2.current_state == ConversationState.READ_BACK_CONFIRMATION
    assert sm.visit.next_visit_date == "2026-11-26"


# ---------------------------------------------------------------------------
# 3. Single & Repeated Voice Corrections (CORRECTION_PATCH)
# ---------------------------------------------------------------------------


def test_single_and_repeated_corrections_preserve_all_other_fields() -> None:
    sm = ConversationStateMachine(session_id="sess_corr_1", language="en-IN")
    sm.apply_extraction(
        ExtractionUpdate(
            beneficiary_id="BEN-2001",
            beneficiary_name="Baby of Meena",
            visit_type=VisitType.NEWBORN,
            weight_kg=3.1,
            vaccinations_due=["BCG", "OPV-0"],
            next_visit_date="2026-11-26",
            follow_up_actions=["Check feeding"],
        )
    )
    sm.on_read_back_completed()
    assert sm.state == ConversationState.READY_TO_CONFIRM

    # Correction 1: inline spoken utterance "No, weight is 2.8 kilo"
    r_c1 = sm.handle_confirmation_response("No, weight is 2.8 kilo")
    assert r_c1.current_state == ConversationState.READ_BACK_CONFIRMATION
    assert r_c1.metadata["patched_fields"] == ["weight_kg"]
    assert sm.visit.weight_kg == 2.8
    # All other fields strictly preserved
    assert sm.visit.beneficiary_id == "BEN-2001"
    assert sm.visit.beneficiary_name == "Baby of Meena"
    assert sm.visit.visit_type == VisitType.NEWBORN
    assert sm.visit.vaccinations_due == ["BCG", "OPV-0"]
    assert sm.visit.next_visit_date == "2026-11-26"
    assert sm.visit.follow_up_actions == ["Check feeding"]
    assert r_c1.spoken_text is not None
    assert "2.8 kg" in r_c1.spoken_text
    assert "Should I confirm this record?" in r_c1.spoken_text
    assert any(a.action_type == ActionType.CORRECTION_APPLIED for a in r_c1.actions)
    # Must have traversed CORRECTION_PATCH -> READ_BACK_CONFIRMATION
    assert sm.transition_history[-2][1] == ConversationState.CORRECTION_PATCH
    assert sm.transition_history[-1][1] == ConversationState.READ_BACK_CONFIRMATION

    # Correction 2 (repeated, during READ_BACK_CONFIRMATION barge-in): "Nahi, next visit 28 November"
    r_c2 = sm.handle_confirmation_response("Nahi, next visit 28 November")
    assert r_c2.current_state == ConversationState.READ_BACK_CONFIRMATION
    assert sm.visit.next_visit_date == "28 November"
    assert sm.visit.weight_kg == 2.8  # First correction preserved!
    assert sm.visit.vaccinations_due == ["BCG", "OPV-0"]

    # Correction 3 (structured patch from 1C replacing vaccinations_due)
    r_c3 = sm.handle_confirmation_response(
        "No, only OPV-0 is due",
        correction_patch=ExtractionUpdate(vaccinations_due=["OPV-0"]),
    )
    assert r_c3.current_state == ConversationState.READ_BACK_CONFIRMATION
    assert sm.visit.vaccinations_due == ["OPV-0"]
    assert sm.visit.weight_kg == 2.8
    assert sm.visit.next_visit_date == "28 November"

    # Now worker explicitly confirms and persistence succeeds
    sm.on_read_back_completed()
    sm.handle_confirmation_response("Haan, theek hai")
    r_fin = sm.handle_persistence_result(accepted=True, record_id="visit_9002")
    assert r_fin.current_state == ConversationState.COMMITTED


def test_rejection_without_correction_field_asks_which_field() -> None:
    sm = ConversationStateMachine(session_id="sess_rej_1", language="hi-IN")
    sm.apply_extraction(_sample_full_extraction())
    sm.on_read_back_completed()

    r_rej = sm.handle_confirmation_response("Nahi, galat hai")
    assert r_rej.current_state == ConversationState.CLARIFICATION_REQUIRED
    assert sm.visit.status == VisitStatus.DRAFT
    assert r_rej.spoken_text is not None
    assert "कौन सी जानकारी" in r_rej.spoken_text


# ---------------------------------------------------------------------------
# 4. Explicit Confirmation Gate & Multilingual Recognition
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase",
    [
        "yes",
        "confirm",
        "correct",
        "haan",
        "haa",
        "theek hai",
        "sahi hai",
        "हाँ",
        "ठीक है",
        "houdu",
        "aama",
        "sari",
    ],
)
def test_multilingual_explicit_confirmations(phrase: str) -> None:
    assert classify_confirmation_intent(phrase) == "confirm"

    sm = ConversationStateMachine(session_id=f"sess_conf_{phrase}", language="en-IN")
    sm.apply_extraction(_sample_full_extraction())
    sm.on_read_back_completed()

    r = sm.handle_confirmation_response(phrase)
    assert sm.visit.status == VisitStatus.CONFIRMED
    assert any(a.action_type == ActionType.PERSISTENCE_REQUESTED for a in r.actions)


@pytest.mark.parametrize(
    "phrase",
    [
        "No, correct weight is 2.8",
        "Nahi, haan mat karo",
        "cancel",
        "No",
        "नहीं",
        "illa",
        "illai",
    ],
)
def test_negation_never_falsely_confirms(phrase: str) -> None:
    assert classify_confirmation_intent(phrase) == "reject"


def test_cannot_commit_unconfirmed_draft() -> None:
    sm = ConversationStateMachine(session_id="sess_gate_1", language="en-IN")
    sm.apply_extraction(_sample_full_extraction())
    sm.on_read_back_completed()
    assert sm.visit.status == VisitStatus.DRAFT

    with pytest.raises(InvalidTransitionError):
        sm.handle_persistence_result(accepted=True, record_id="visit_illegal")

    assert sm.state == ConversationState.READY_TO_CONFIRM
    assert sm.visit.status == VisitStatus.DRAFT


def test_cannot_confirm_outside_read_back_states() -> None:
    sm = ConversationStateMachine(session_id="sess_gate_2", language="en-IN")
    sm.start_gathering()

    with pytest.raises(InvalidTransitionError):
        sm.handle_confirmation_response("Yes, confirm")

    assert sm.state == ConversationState.GATHERING_NOTES
    assert sm.visit.status == VisitStatus.DRAFT


# ---------------------------------------------------------------------------
# 5. Failed Persistence Acknowledgement & Retry
# ---------------------------------------------------------------------------


def test_failed_persistence_does_not_mark_committed_and_allows_retry() -> None:
    sm = ConversationStateMachine(session_id="sess_persist_fail", language="en-IN")
    sm.apply_extraction(_sample_full_extraction())
    sm.on_read_back_completed()

    r_conf = sm.handle_confirmation_response("confirm")
    assert sm.visit.status == VisitStatus.CONFIRMED
    assert r_conf.current_state == ConversationState.READY_TO_CONFIRM

    # Persistence fails (e.g. network timeout / Supabase 503)
    r_fail = sm.handle_persistence_result(accepted=False, error="Upstream 503 timeout")
    assert r_fail.current_state == ConversationState.READY_TO_CONFIRM
    assert r_fail.current_state != ConversationState.COMMITTED
    assert sm.visit.status == VisitStatus.CONFIRMED
    assert sm.persistence_error == "Upstream 503 timeout"
    assert any(a.action_type == ActionType.PERSISTENCE_REJECTED for a in r_fail.actions)
    assert r_fail.spoken_text is not None
    assert "confirmed locally" in r_fail.spoken_text.lower()
    assert "could not be saved" in r_fail.spoken_text.lower()

    # Retry persistence -> succeeds
    r_retry = sm.retry_persistence()
    assert any(a.action_type == ActionType.PERSISTENCE_REQUESTED for a in r_retry.actions)
    r_ok = sm.handle_persistence_result(accepted=True, record_id="visit_retry_1")
    assert r_ok.current_state == ConversationState.COMMITTED
    assert sm.visit.status == VisitStatus.COMMITTED
    assert sm.visit.record_id == "visit_retry_1"


# ---------------------------------------------------------------------------
# 6. Danger Escalation from EVERY Active State + Idempotency + Preservation
# ---------------------------------------------------------------------------


def _build_sm_in_state(target: ConversationState) -> ConversationStateMachine:
    sm = ConversationStateMachine(session_id=f"sess_state_{target.value}", language="en-IN")
    if target == ConversationState.IDLE:
        return sm
    if target == ConversationState.GATHERING_NOTES:
        sm.start_gathering()
        return sm
    if target == ConversationState.EXTRACTING_FIELDS:
        sm.begin_extraction()
        return sm
    if target == ConversationState.CLARIFICATION_REQUIRED:
        sm.apply_extraction(ExtractionUpdate(beneficiary_id="BEN-1042"))
        return sm
    if target == ConversationState.READ_BACK_CONFIRMATION:
        sm.apply_extraction(_sample_full_extraction())
        return sm
    if target == ConversationState.READY_TO_CONFIRM:
        sm.apply_extraction(_sample_full_extraction())
        sm.on_read_back_completed()
        return sm
    if target == ConversationState.CORRECTION_PATCH:
        sm.apply_extraction(_sample_full_extraction())
        sm.state = ConversationState.CORRECTION_PATCH
        return sm
    if target == ConversationState.COMMITTED:
        sm.apply_extraction(_sample_full_extraction())
        sm.on_read_back_completed()
        sm.handle_confirmation_response("yes")
        sm.handle_persistence_result(accepted=True, record_id="visit_done")
        return sm
    raise AssertionError(f"Unexpected state {target}")


@pytest.mark.parametrize(
    "origin_state",
    [
        ConversationState.IDLE,
        ConversationState.GATHERING_NOTES,
        ConversationState.EXTRACTING_FIELDS,
        ConversationState.CLARIFICATION_REQUIRED,
        ConversationState.READ_BACK_CONFIRMATION,
        ConversationState.CORRECTION_PATCH,
        ConversationState.READY_TO_CONFIRM,
        ConversationState.COMMITTED,
    ],
)
def test_danger_escalation_interrupt_from_every_state(origin_state: ConversationState) -> None:
    sm = _build_sm_in_state(origin_state)
    assert sm.state == origin_state

    res = sm.handle_danger_detection(_sample_danger_alert())
    assert res.previous_state == origin_state
    assert res.current_state == ConversationState.DANGER_ESCALATION
    assert sm.return_state == origin_state
    assert res.is_urgent is True
    assert res.interrupt_speech is True
    assert sm.visit.danger_sign_flagged is True
    assert "MATERNAL_SEVERE_BLEEDING" in sm.visit.danger_signs
    assert len(sm.danger_alerts) == 1

    action_types = [a.action_type for a in res.actions]
    assert ActionType.DANGER_ALERT in action_types
    assert ActionType.SPEAK_URGENT in action_types
    assert res.spoken_text is not None
    assert "nearest PHC" in res.spoken_text


def test_danger_detection_idempotent_for_partial_then_final() -> None:
    sm = ConversationStateMachine(session_id="sess_idemp_1", language="hi-IN")
    sm.start_gathering()

    # Partial detection fires alert & urgent speech
    r_partial = sm.handle_danger_detection(
        _sample_danger_alert(
            canonical_id="NEWBORN_CONVULSIONS",
            matched_phrase="baby having fits",
            is_partial=True,
        )
    )
    assert r_partial.current_state == ConversationState.DANGER_ESCALATION
    assert r_partial.is_urgent is True
    assert len(sm.danger_alerts) == 1
    assert any(a.action_type == ActionType.DANGER_ALERT for a in r_partial.actions)

    # Final transcript triggers same canonical_id with richer detail -> deduplicated!
    r_final = sm.handle_danger_detection(
        _sample_danger_alert(
            canonical_id="NEWBORN_CONVULSIONS",
            matched_phrase="newborn baby having repeated convulsions since morning",
            is_partial=False,
        )
    )
    assert r_final.metadata["deduplicated"] is True
    assert r_final.is_urgent is False
    assert r_final.interrupt_speech is False
    assert r_final.actions == []
    assert len(sm.danger_alerts) == 1
    # Evidence enriched while keeping single alert
    assert (
        sm.danger_alerts[0].evidence
        == "newborn baby having repeated convulsions since morning"
    )
    assert len(sm.danger_alerts[0].evidence_history) == 2


def test_danger_alerts_preserved_across_resume_correction_barge_in_and_abandon() -> None:
    sm = ConversationStateMachine(session_id="sess_preserve_1", language="en-IN")
    sm.apply_extraction(_sample_full_extraction())
    sm.on_read_back_completed()

    # Danger sign interrupts READY_TO_CONFIRM
    sm.handle_danger_detection(_sample_danger_alert())
    assert sm.state == ConversationState.DANGER_ESCALATION
    assert sm.visit.danger_sign_flagged is True

    # Resume visit workflow -> re-reads record INCLUDING danger sign flag!
    r_resume = sm.resume_after_danger()
    assert r_resume.current_state == ConversationState.READ_BACK_CONFIRMATION
    assert r_resume.spoken_text is not None
    assert "Danger sign flagged" in r_resume.spoken_text
    assert sm.visit.danger_sign_flagged is True
    assert len(sm.danger_alerts) == 1

    # Barge-in & correction patch MUST NEVER clear danger_sign_flagged or alerts
    sm.handle_barge_in()
    r_patch = sm.handle_confirmation_response("No, weight is 50.0 kg")
    assert r_patch.current_state == ConversationState.READ_BACK_CONFIRMATION
    assert sm.visit.weight_kg == 50.0
    assert sm.visit.danger_sign_flagged is True
    assert "MATERNAL_SEVERE_BLEEDING" in sm.visit.danger_signs
    assert len(sm.danger_alerts) == 1

    # Even if worker abandons the visit, danger alerts remain preserved!
    r_abandon = sm.abandon_visit()
    assert r_abandon.current_state == ConversationState.IDLE
    assert sm.abandoned is True
    assert sm.visit.danger_sign_flagged is True
    assert len(sm.danger_alerts) == 1
    assert r_abandon.metadata["danger_alerts_preserved"] == 1


# ---------------------------------------------------------------------------
# 7. Localized Spoken Read-Back Generation (en-IN, hi-IN, kn-IN, ta-IN)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("lang", "expected_snippets"),
    [
        (
            "en-IN",
            [
                "Lakshmi Devi",
                "BEN-1042",
                "ANC",
                "52.5 kg",
                "TT-2",
                "2026-11-26",
                "Danger sign flagged",
                "Should I confirm this record?",
            ],
        ),
        (
            "hi-IN",
            [
                "Lakshmi Devi",
                "BEN-1042",
                "ANC",
                "52.5 किलो",
                "TT-2",
                "2026-11-26",
                "खतरे का लक्षण",
                "क्या मैं यह रिकॉर्ड कन्फर्म कर दूँ?",
            ],
        ),
        (
            "kn-IN",
            [
                "Lakshmi Devi",
                "BEN-1042",
                "ANC",
                "52.5 ಕೆಜಿ",
                "TT-2",
                "2026-11-26",
                "ಅಪಾಯದ ಲಕ್ಷಣ",
                "ಈ ದಾಖಲೆಯನ್ನು ದೃಢೀಕರಿಸಲೇ?",
            ],
        ),
        (
            "ta-IN",
            [
                "Lakshmi Devi",
                "BEN-1042",
                "ANC",
                "52.5 கிலோ",
                "TT-2",
                "2026-11-26",
                "அபாய அறிகுறி",
                "இந்தப் பதிவை உறுதிப்படுத்தலாமா?",
            ],
        ),
    ],
)
def test_localized_read_back_generation(lang: str, expected_snippets: list[str]) -> None:
    visit = VisitRecordState(
        beneficiary_id="BEN-1042",
        beneficiary_name="Lakshmi Devi",
        visit_type=VisitType.ANC,
        weight_kg=52.5,
        vaccinations_due=["TT-2"],
        follow_up_actions=["Immediate referral to nearest PHC"],
        next_visit_date="2026-11-26",
        danger_signs=["MATERNAL_SEVERE_BLEEDING"],
        danger_sign_flagged=True,
    )
    text = generate_read_back_text(visit, lang)
    for snippet in expected_snippets:
        assert snippet in text, f"Missing {snippet!r} in {lang} read-back: {text}"
