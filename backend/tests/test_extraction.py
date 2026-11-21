"""Unit tests for deterministic multilingual ASHA visit field extraction & validation.

All beneficiary names, IDs, and visit utterances are 100% synthetic.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.extraction import (  # noqa: E402
    ExtractionResult,
    FieldClarification,
    FollowUpAction,
    VisitDraft,
    VisitFieldExtractor,
)
from app.services.beneficiaries import SyntheticBeneficiaryDirectory  # noqa: E402

REF_DATE = date(2026, 11, 21)  # Saturday


@pytest.fixture
def extractor() -> VisitFieldExtractor:
    return VisitFieldExtractor(
        beneficiary_directory=SyntheticBeneficiaryDirectory(),
        timezone_name="Asia/Kolkata",
    )


# ---------------------------------------------------------------------------
# 1. Model validation tests
# ---------------------------------------------------------------------------


def test_models_validate_iso_dates_and_positive_weight() -> None:
    draft = VisitDraft(
        visit_id="visit-001",
        beneficiary_id="BEN-1042",
        visit_type="ANC",
        weight_kg=52.0,
        next_visit_date="2026-11-25",
    )
    assert draft.status == "draft"
    assert draft.danger_sign_flagged is False
    assert draft.danger_signs == []

    with pytest.raises(ValidationError):
        VisitDraft(visit_id="visit-002", next_visit_date="2026-02-31")

    with pytest.raises(ValidationError):
        VisitDraft(visit_id="visit-003", next_visit_date="tomorrow")

    with pytest.raises(ValidationError):
        VisitDraft(visit_id="visit-004", weight_kg=-3.0)

    with pytest.raises(ValidationError):
        FollowUpAction(
            action_type="routine_visit",
            description="Follow up",
            due_date="31/11/2026",
        )


# ---------------------------------------------------------------------------
# 2. Beneficiary resolution & disambiguation tests
# ---------------------------------------------------------------------------


def test_beneficiary_resolution_by_id_and_unknown_id(extractor: VisitFieldExtractor) -> None:
    res = extractor.extract("BEN-1042 ANC visit weight 52 kilo", reference_date=REF_DATE)
    assert res.patch["beneficiary_id"] == "BEN-1042"
    assert res.patch["beneficiary_name"] == "Lakshmi Devi"
    assert res.clarifications == []

    res_spaced = extractor.extract("B E N 1045 checkup", reference_date=REF_DATE)
    assert res_spaced.patch["beneficiary_id"] == "BEN-1045"
    assert res_spaced.patch["beneficiary_name"] == "Sunita Kumari"

    res_unknown = extractor.extract("BEN-9999 ANC visit", reference_date=REF_DATE)
    assert "beneficiary_id" not in res_unknown.patch
    assert any(c.field_name == "beneficiary_id" for c in res_unknown.clarifications)


def test_beneficiary_resolution_multilingual_aliases(extractor: VisitFieldExtractor) -> None:
    cases = [
        ("सुनीता का वजन 55 किलो", "BEN-1045", "Sunita Kumari"),
        ("மீனா immunisation visit", "BEN-1046", "Meena Selvam"),
        ("अनीता का ANC विजिट", "BEN-1047", "Anita Devi"),
        ("ಕವಿತಾ PNC visit", "BEN-1043", "Kavitha Rao"),
        ("लक्ष्मी का ANC विजिट", "BEN-1042", "Lakshmi Devi"),
        ("Lakshmi Narayanan PNC visit", "BEN-1048", "Lakshmi Narayanan"),
        ("Baby of Kavitha Rao weight 2.8 kilo", "BEN-1044", "Baby of Kavitha Rao"),
        ("Kavitha newborn weight 2.8 kilo", "BEN-1044", "Baby of Kavitha Rao"),
        ("Kavitha ka newborn visit weight 3 kilo", "BEN-1044", "Baby of Kavitha Rao"),
    ]
    for utterance, expected_id, expected_name in cases:
        res = extractor.extract(utterance, reference_date=REF_DATE)
        assert res.patch.get("beneficiary_id") == expected_id, f"Failed for: {utterance}"
        assert res.patch.get("beneficiary_name") == expected_name, f"Failed for: {utterance}"


def test_beneficiary_ambiguity_and_disambiguation(extractor: VisitFieldExtractor) -> None:
    # Bare "Lakshmi" matches both BEN-1042 (Lakshmi Devi) and BEN-1048 (Lakshmi Narayanan)
    ambig = extractor.extract("Lakshmi ka weight 52 kilo", reference_date=REF_DATE)
    assert "beneficiary_id" not in ambig.patch
    assert ambig.patch["weight_kg"] == 52.0
    ben_clars = [c for c in ambig.clarifications if c.field_name == "beneficiary_id"]
    assert len(ben_clars) == 1
    assert any("BEN-1042" in cand for cand in ben_clars[0].candidates)
    assert any("BEN-1048" in cand for cand in ben_clars[0].candidates)

    # Disambiguated by ANC visit type -> BEN-1042 (pregnant_woman)
    anc = extractor.extract("Lakshmi ka ANC visit hai, weight 52 kilo", reference_date=REF_DATE)
    assert anc.patch["beneficiary_id"] == "BEN-1042"
    assert anc.patch["beneficiary_name"] == "Lakshmi Devi"

    # Disambiguated by PNC visit type -> BEN-1048 (postnatal_mother)
    pnc = extractor.extract("Lakshmi ka PNC visit hai", reference_date=REF_DATE)
    assert pnc.patch["beneficiary_id"] == "BEN-1048"
    assert pnc.patch["beneficiary_name"] == "Lakshmi Narayanan"

    # Disambiguated by village mention
    rampur = extractor.extract("Lakshmi from Rampur weight 51 kilo", reference_date=REF_DATE)
    assert rampur.patch["beneficiary_id"] == "BEN-1042"

    kaveri = extractor.extract("Lakshmi from Kaveri weight 49 kilo", reference_date=REF_DATE)
    assert kaveri.patch["beneficiary_id"] == "BEN-1048"

    # Disambiguated via existing_draft visit_type
    existing = VisitDraft(visit_id="v-1", visit_type="ANC")
    from_draft = extractor.extract("Lakshmi", reference_date=REF_DATE, existing_draft=existing)
    assert from_draft.patch["beneficiary_id"] == "BEN-1042"

    # Unknown name must NEVER fabricate an ID
    unknown_name = extractor.extract("Priya ka checkup hua", reference_date=REF_DATE)
    assert "beneficiary_id" not in unknown_name.patch


# ---------------------------------------------------------------------------
# 3. Visit type extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("utterance", "expected"),
    [
        ("Sunita antenatal checkup", "ANC"),
        ("Garbhavati checkup done", "ANC"),
        ("गर्भवती जांच हुई", "ANC"),
        ("Pregnancy checkup for Anita", "ANC"),
        ("Kavitha postnatal checkup", "PNC"),
        ("Delivery ke baad visit", "PNC"),
        ("Prasav ke baad checkup", "PNC"),
        ("HBNC home visit", "Newborn"),
        ("Navjat shishu ka weight 2.9 kilo", "Newborn"),
        ("Newborn checkup", "Newborn"),
        ("Meena ka tikakaran visit", "Immunisation"),
        ("Immunization session for Meena", "Immunisation"),
        ("Vaccine visit completed", "Immunisation"),
        ("ANC visit, TT pending", "ANC"),  # vaccine mention must not override ANC
        ("Not ANC, it is PNC", "PNC"),
    ],
)
def test_visit_type_extraction(
    extractor: VisitFieldExtractor, utterance: str, expected: str
) -> None:
    res = extractor.extract(utterance, reference_date=REF_DATE)
    assert res.patch.get("visit_type") == expected


def test_conflicting_visit_types_emit_clarification(extractor: VisitFieldExtractor) -> None:
    res = extractor.extract("ANC and PNC visit today", reference_date=REF_DATE)
    assert "visit_type" not in res.patch
    assert any(c.field_name == "visit_type" for c in res.clarifications)


# ---------------------------------------------------------------------------
# 4. Weight normalization & physiological validation tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("utterance", "expected_kg"),
    [
        ("weight fifty two kilo", 52.0),
        ("ववेट fifty two kilo", 52.0),  # real Gnani Prisma ASR artifact
        ("weight is 2.8 kilo", 2.8),
        ("weight 2800 gram", 2.8),
        ("baby weight 2800g", 2.8),
        ("weight 3 kilo 200 gram", 3.2),
        ("weight three kilo two hundred grams", 3.2),
        ("वजन ढाई किलो है", 2.5),
        ("dhai kilo weight", 2.5),
        ("वजन साढ़े तीन किलो", 3.5),
        ("sadhe teen kilo", 3.5),
        ("सवा तीन किलो", 3.25),
        ("पौने तीन किलो", 2.75),
        ("डेढ़ किलो", 1.5),
        ("two point eight kilo", 2.8),
        ("दो दशमलव आठ किलो", 2.8),
        ("three and a half kilo", 3.5),
        ("वजन ५२ किलो", 52.0),
        ("BCG given and 2.8 kilo", 2.8),
        ("weight 52", 52.0),
        ("वजन 48.5", 48.5),
    ],
)
def test_weight_normalization(
    extractor: VisitFieldExtractor, utterance: str, expected_kg: float
) -> None:
    res = extractor.extract(utterance, reference_date=REF_DATE)
    assert res.patch.get("weight_kg") == pytest.approx(expected_kg)
    assert res.patch.get("weight_source_text")
    assert "weight_kg" in res.provenance


def test_weight_physiological_bounds_validation(extractor: VisitFieldExtractor) -> None:
    # Globally implausible
    res_high = extractor.extract("weight 520 kilo", reference_date=REF_DATE)
    assert "weight_kg" not in res_high.patch
    assert any(c.field_name == "weight_kg" for c in res_high.clarifications)

    res_low = extractor.extract("weight 0.1 kilo", reference_date=REF_DATE)
    assert "weight_kg" not in res_low.patch
    assert any(c.field_name == "weight_kg" for c in res_low.clarifications)

    # Implausible for newborn (>15 kg)
    res_nb = extractor.extract("Kavitha newborn weight 52 kilo", reference_date=REF_DATE)
    assert "weight_kg" not in res_nb.patch
    assert any(c.field_name == "weight_kg" for c in res_nb.clarifications)

    # Implausible for adult ANC (<25 kg)
    res_anc = extractor.extract("Lakshmi Devi ANC visit weight 2.8 kilo", reference_date=REF_DATE)
    assert "weight_kg" not in res_anc.patch
    assert any(c.field_name == "weight_kg" for c in res_anc.clarifications)

    # Non-weight numbers must NOT be extracted as weight
    res_no_wt = extractor.extract(
        "BEN-1042 ANC visit next visit 25 November after 7 days", reference_date=REF_DATE
    )
    assert "weight_kg" not in res_no_wt.patch


# ---------------------------------------------------------------------------
# 5. Vaccination extraction tests (completed vs due)
# ---------------------------------------------------------------------------


def test_vaccinations_completed_vs_due(extractor: VisitFieldExtractor) -> None:
    res = extractor.extract(
        "BCG and OPV given, Pentavalent is pending, Rotavirus nahi laga",
        reference_date=REF_DATE,
    )
    assert res.patch["vaccinations_completed"] == ["BCG", "OPV"]
    assert res.patch["vaccinations_due"] == ["Pentavalent", "Rotavirus"]

    res_hi = extractor.extract(
        "TT ho gaya, Td baaki hai, PCV lag gaya, IPV not given",
        reference_date=REF_DATE,
    )
    assert res_hi.patch["vaccinations_completed"] == ["TT", "PCV"]
    assert res_hi.patch["vaccinations_due"] == ["Td", "IPV"]

    res_more = extractor.extract(
        "Measles de diya, Hepatitis B and DPT remaining",
        reference_date=REF_DATE,
    )
    assert res_more.patch["vaccinations_completed"] == ["MR"]
    assert res_more.patch["vaccinations_due"] == ["Hepatitis B", "DPT"]


def test_vaccination_without_status_does_not_guess(extractor: VisitFieldExtractor) -> None:
    res = extractor.extract("We talked about BCG today", reference_date=REF_DATE)
    assert "vaccinations_completed" not in res.patch
    assert "vaccinations_due" not in res.patch
    assert any(c.field_name == "vaccinations_due" for c in res.clarifications)

    # Guard against false positives on ordinary English words
    res_fp = extractor.extract("Mr. Sharma said she is feeling better", reference_date=REF_DATE)
    assert "vaccinations_completed" not in res_fp.patch
    assert "vaccinations_due" not in res_fp.patch


# ---------------------------------------------------------------------------
# 6. Next visit date parsing & ambiguity tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("utterance", "expected_iso"),
    [
        ("next visit 25 November", "2026-11-25"),
        ("next visit twenty eighth November", "2026-11-28"),
        ("next visit 28 Nov", "2026-11-28"),
        ("next visit 28/11/2026", "2026-11-28"),
        ("next visit 2026-11-28", "2026-11-28"),
        ("अगला विजिट 28 नवंबर", "2026-11-28"),
        ("next visit 5 January", "2027-01-05"),  # rolls forward past REF_DATE
        ("next visit tomorrow", "2026-11-22"),
        ("agla visit kal hai", "2026-11-22"),
        ("next visit parso", "2026-11-23"),
        ("next visit next Monday", "2026-11-23"),
        ("agla visit agle somwar", "2026-11-23"),
        ("next visit next week", "2026-11-28"),
        ("agla visit agle hafte", "2026-11-28"),
        ("next visit after 7 days", "2026-11-28"),
        ("7 din baad aana hai", "2026-11-28"),
        ("सात दिन बाद आना है", "2026-11-28"),
        ("after 2 weeks", "2026-12-05"),
    ],
)
def test_next_visit_date_parsing(
    extractor: VisitFieldExtractor, utterance: str, expected_iso: str
) -> None:
    res = extractor.extract(utterance, reference_date=REF_DATE)
    assert res.patch.get("next_visit_date") == expected_iso
    assert res.patch.get("next_visit_date_source_text")
    assert "next_visit_date" in res.provenance


def test_ambiguous_invalid_and_past_dates(extractor: VisitFieldExtractor) -> None:
    for utterance in (
        "next visit some day next month",
        "agla visit agle mahine kisi din",
        "next visit 31 February",
        "next visit 31/02/2026",
    ):
        res = extractor.extract(utterance, reference_date=REF_DATE)
        assert "next_visit_date" not in res.patch, f"Unexpected date for: {utterance}"
        assert any(
            c.field_name == "next_visit_date" for c in res.clarifications
        ), f"Expected clarification for: {utterance}"

    # Past symptom onset "kal se" must NOT be treated as tomorrow's next visit
    past = extractor.extract("kal se bukhar hai", reference_date=REF_DATE)
    assert "next_visit_date" not in past.patch

    # Hindi "sat kilo" (7 kg) must NOT trigger Saturday
    sat_wt = extractor.extract("weight sat kilo", reference_date=REF_DATE)
    assert sat_wt.patch["weight_kg"] == 7.0
    assert "next_visit_date" not in sat_wt.patch


# ---------------------------------------------------------------------------
# 7. Grounded follow-up actions tests
# ---------------------------------------------------------------------------


def test_follow_up_actions_grounded(extractor: VisitFieldExtractor) -> None:
    res = extractor.extract(
        "Lakshmi ka ANC visit hai, IFA goli regularly nahi le rahi, TT due hai, next visit 25 November",
        reference_date=REF_DATE,
    )
    actions: list[FollowUpAction] = res.patch["follow_up_actions"]
    action_types = {a.action_type for a in actions}
    assert "vaccination" in action_types
    assert "ifa_adherence" in action_types
    assert "routine_visit" in action_types
    for action in actions:
        assert action.due_date == "2026-11-25"

    # Positive IFA adherence must NOT emit an ifa_adherence non-adherence action
    pos = extractor.extract(
        "Sunita ANC visit, IFA goli regularly le rahi hai, weight 54 kilo",
        reference_date=REF_DATE,
    )
    pos_actions: list[FollowUpAction] = pos.patch.get("follow_up_actions", [])
    assert not any(a.action_type == "ifa_adherence" for a in pos_actions)

    # Explicit weight monitoring cue
    wm = extractor.extract("Recheck weight next week", reference_date=REF_DATE)
    wm_types = {a.action_type for a in wm.patch["follow_up_actions"]}
    assert "weight_monitoring" in wm_types
    assert "routine_visit" in wm_types


# ---------------------------------------------------------------------------
# 8. Voice correction patch detection & apply_to_draft safety tests
# ---------------------------------------------------------------------------


def test_single_field_correction_preserves_other_fields_and_danger_signs(
    extractor: VisitFieldExtractor,
) -> None:
    initial_draft = VisitDraft(
        visit_id="visit-100",
        beneficiary_id="BEN-1044",
        beneficiary_name="Baby of Kavitha Rao",
        visit_type="Newborn",
        weight_kg=3.2,
        weight_source_text="3.2 kilo",
        vaccinations_completed=["BCG"],
        vaccinations_due=["OPV"],
        next_visit_date="2026-11-28",
        next_visit_date_source_text="28 November",
        danger_signs=["fast_breathing"],
        danger_sign_flagged=True,
        follow_up_actions=[
            FollowUpAction(
                action_type="danger_referral",
                description="Refer immediately to nearest PHC",
                priority="urgent",
            ),
            FollowUpAction(
                action_type="vaccination",
                description="Schedule and administer due vaccination(s): OPV",
                due_date="2026-11-28",
                priority="high",
            ),
        ],
        status="confirmed",
        confirmed_fields=["beneficiary_id", "visit_type", "weight_kg"],
    )

    corr = extractor.extract(
        "No, weight is 2.8 kilo",
        reference_date=REF_DATE,
        existing_draft=initial_draft,
    )
    assert corr.detected_correction is True
    assert corr.corrected_fields == ["weight_kg"]
    assert set(corr.patch.keys()) == {"weight_kg", "weight_source_text"}
    assert corr.patch["weight_kg"] == 2.8

    updated = extractor.apply_to_draft(initial_draft, corr, correction_mode=True)
    # Input draft must not be mutated
    assert initial_draft.weight_kg == 3.2

    # Only weight changed; all other accepted fields preserved
    assert updated.weight_kg == 2.8
    assert updated.beneficiary_id == "BEN-1044"
    assert updated.beneficiary_name == "Baby of Kavitha Rao"
    assert updated.visit_type == "Newborn"
    assert updated.vaccinations_completed == ["BCG"]
    assert updated.vaccinations_due == ["OPV"]
    assert updated.next_visit_date == "2026-11-28"

    # Danger signs and referral action MUST be preserved unconditionally
    assert updated.danger_sign_flagged is True
    assert updated.danger_signs == ["fast_breathing"]
    assert any(a.action_type == "danger_referral" for a in updated.follow_up_actions)

    # Confirmed status resets to draft and corrected field removed from confirmed_fields
    assert updated.status == "draft"
    assert "weight_kg" not in updated.confirmed_fields
    assert "beneficiary_id" in updated.confirmed_fields


def test_hindi_correction_and_non_correction_negations(extractor: VisitFieldExtractor) -> None:
    corr_hi = extractor.extract("नहीं, वजन 54 किलो है", reference_date=REF_DATE)
    assert corr_hi.detected_correction is True
    assert corr_hi.corrected_fields == ["weight_kg"]
    assert corr_hi.patch["weight_kg"] == 54.0

    corr_hinglish = extractor.extract(
        "Galat hai, next visit 28 November hai", reference_date=REF_DATE
    )
    assert corr_hinglish.detected_correction is True
    assert corr_hinglish.corrected_fields == ["next_visit_date"]
    assert corr_hinglish.patch["next_visit_date"] == "2026-11-28"

    # Standalone action correction reports follow_up_actions
    corr_ifa = extractor.extract(
        "Actually she is not taking IFA tablets", reference_date=REF_DATE
    )
    assert corr_ifa.detected_correction is True
    assert corr_ifa.corrected_fields == ["follow_up_actions"]

    # Ordinary negative clinical/vaccine facts must NOT be flagged as corrections
    non_corr_ifa = extractor.extract("IFA goli regularly nahi le rahi", reference_date=REF_DATE)
    assert non_corr_ifa.detected_correction is False

    non_corr_vax = extractor.extract("BCG nahi laga", reference_date=REF_DATE)
    assert non_corr_vax.detected_correction is False

    non_corr_symp = extractor.extract("No fever, weight 52 kilo", reference_date=REF_DATE)
    assert non_corr_symp.detected_correction is False


def test_apply_to_draft_protects_confirmed_fields_and_clears_resolved_clarifications(
    extractor: VisitFieldExtractor,
) -> None:
    draft = VisitDraft(
        visit_id="visit-200",
        beneficiary_id="BEN-1042",
        beneficiary_name="Lakshmi Devi",
        visit_type="ANC",
        weight_kg=52.0,
        danger_signs=["convulsions"],
        danger_sign_flagged=True,
        confirmed_fields=["weight_kg"],
    )

    # Attempting to overwrite confirmed weight with None or non-correction value must fail
    null_patch = ExtractionResult(
        patch={"weight_kg": None, "danger_sign_flagged": False, "danger_signs": []},
        clarifications=[],
    )
    safe = extractor.apply_to_draft(draft, null_patch, correction_mode=False)
    assert safe.weight_kg == 52.0
    assert safe.danger_sign_flagged is True
    assert safe.danger_signs == ["convulsions"]

    non_corr_overwrite = ExtractionResult(patch={"weight_kg": 55.0}, clarifications=[])
    protected = extractor.apply_to_draft(draft, non_corr_overwrite, correction_mode=False)
    assert protected.weight_kg == 52.0

    # Multi-turn ambiguity resolution clears beneficiary clarification
    turn1 = extractor.extract("Lakshmi ka weight 52 kilo", reference_date=REF_DATE)
    d1 = extractor.apply_to_draft(VisitDraft(visit_id="visit-201"), turn1)
    assert d1.beneficiary_id is None
    assert any(c.field_name == "beneficiary_id" for c in d1.clarifications_needed)

    turn2 = extractor.extract("Lakshmi Devi ANC visit", reference_date=REF_DATE, existing_draft=d1)
    d2 = extractor.apply_to_draft(d1, turn2)
    assert d2.beneficiary_id == "BEN-1042"
    assert d2.weight_kg == 52.0
    assert not any(c.field_name == "beneficiary_id" for c in d2.clarifications_needed)


def test_vaccine_correction_moves_from_due_to_completed(extractor: VisitFieldExtractor) -> None:
    draft = VisitDraft(
        visit_id="visit-300",
        beneficiary_id="BEN-1046",
        beneficiary_name="Meena Selvam",
        visit_type="Immunisation",
        vaccinations_due=["Pentavalent", "OPV"],
    )
    corr = extractor.extract(
        "Actually Pentavalent is given", reference_date=REF_DATE, existing_draft=draft
    )
    assert corr.detected_correction is True
    updated = extractor.apply_to_draft(draft, corr, correction_mode=True)
    assert "Pentavalent" in updated.vaccinations_completed
    assert "Pentavalent" not in updated.vaccinations_due
    assert updated.vaccinations_due == ["OPV"]


# ---------------------------------------------------------------------------
# 9. Full end-to-end realistic code-mixed utterances
# ---------------------------------------------------------------------------


def test_end_to_end_hinglish_anc_note_with_prisma_asr_artifact(
    extractor: VisitFieldExtractor,
) -> None:
    utterance = (
        "Lakshmi ka ANC visit hai, ववेट fifty two kilo, "
        "IFA goli regularly nahi le rahi, TT due hai, next visit 25 November"
    )
    res = extractor.extract(utterance, reference_date=REF_DATE, active_language="hi-IN")
    draft = extractor.apply_to_draft(VisitDraft(visit_id="visit-anc-1"), res)

    assert draft.beneficiary_id == "BEN-1042"
    assert draft.beneficiary_name == "Lakshmi Devi"
    assert draft.visit_type == "ANC"
    assert draft.weight_kg == 52.0
    assert draft.vaccinations_due == ["TT"]
    assert draft.next_visit_date == "2026-11-25"
    assert draft.clarifications_needed == []
    action_types = {a.action_type for a in draft.follow_up_actions}
    assert action_types == {"vaccination", "ifa_adherence", "routine_visit"}


def test_end_to_end_newborn_hbnc_note(extractor: VisitFieldExtractor) -> None:
    utterance = (
        "Kavitha newborn HBNC visit, weight 2800g, "
        "BCG and OPV given, Pentavalent pending, next visit after 7 days"
    )
    res = extractor.extract(utterance, reference_date=REF_DATE, active_language="kn-IN")
    draft = extractor.apply_to_draft(VisitDraft(visit_id="visit-nb-1"), res)

    assert draft.beneficiary_id == "BEN-1044"
    assert draft.beneficiary_name == "Baby of Kavitha Rao"
    assert draft.visit_type == "Newborn"
    assert draft.weight_kg == 2.8
    assert draft.vaccinations_completed == ["BCG", "OPV"]
    assert draft.vaccinations_due == ["Pentavalent"]
    assert draft.next_visit_date == "2026-11-28"
    assert draft.clarifications_needed == []
