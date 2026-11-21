"""Golden Evaluation Harness (1E) — Per-Field Accuracy & 100% Danger-Sign Recall.

Label: UNIT / GOLDEN-EVAL (100% synthetic multilingual, Hinglish code-mix & noisy-ASR utterances).
Requirement (MASTER.md §6):
- Report per-field extraction accuracy and danger-sign recall on every run.
- Danger-sign recall target: 100% on the golden set.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.danger_signs.detector import detect_danger_signs  # noqa: E402
from app.extraction.extractor import VisitFieldExtractor  # noqa: E402

REF_DATE = date(2026, 11, 21)


@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    language: str
    text: str
    expected_danger: bool
    expected_fields: dict[str, Any] = field(default_factory=dict)
    visit_type_context: str | None = None


GOLDEN_SET: tuple[GoldenCase, ...] = (
    # --- Routine Visits (expected_danger=False) ---
    GoldenCase(
        case_id="G01_hinglish_anc_full",
        language="hi-IN",
        text="Today I visited Lakshmi, ANC checkup completed. Weight is 52 kilo. TT injection pending hai, IFA goli regularly nahi le rahi. Next visit 25 November.",
        expected_danger=False,
        expected_fields={
            "beneficiary_id": "BEN-1042",
            "visit_type": "ANC",
            "weight_kg": 52.0,
            "vaccinations_due": ["TT"],
            "next_visit_date": "2026-11-25",
        },
    ),
    GoldenCase(
        case_id="G02_asr_noisy_hinglish_anc",
        language="hi-IN",
        text="लक्ष्मी का ANC checkup done, ववेट fifty two kilo, TT injection pending hai, next visit twenty eighth November.",
        expected_danger=False,
        expected_fields={
            "beneficiary_id": "BEN-1042",
            "visit_type": "ANC",
            "weight_kg": 52.0,
            "vaccinations_due": ["TT"],
            "next_visit_date": "2026-11-28",
        },
    ),
    GoldenCase(
        case_id="G03_newborn_grams_to_kg",
        language="kn-IN",
        text="HBNC newborn visit for Kavitha baby. Weight is 2800 gram. BCG given, OPV pending. Next visit after 7 days.",
        expected_danger=False,
        expected_fields={
            "beneficiary_id": "BEN-1044",
            "visit_type": "Newborn",
            "weight_kg": 2.8,
            "vaccinations_completed": ["BCG"],
            "vaccinations_due": ["OPV"],
            "next_visit_date": "2026-11-28",
        },
    ),
    GoldenCase(
        case_id="G04_hindi_fraction_weight_pnc",
        language="hi-IN",
        text="Kavitha Rao PNC visit completed. Weight 54 kilo. Next visit kal.",
        expected_danger=False,
        expected_fields={
            "beneficiary_id": "BEN-1043",
            "visit_type": "PNC",
            "weight_kg": 54.0,
            "next_visit_date": "2026-11-22",
        },
    ),
    GoldenCase(
        case_id="G05_immunisation_tamil_ben",
        language="ta-IN",
        text="Meena immunisation visit. Weight 6.5 kilo. Pentavalent given, MR vaccine due. Next visit 10 December.",
        expected_danger=False,
        expected_fields={
            "beneficiary_id": "BEN-1046",
            "visit_type": "Immunisation",
            "weight_kg": 6.5,
            "vaccinations_completed": ["Pentavalent"],
            "vaccinations_due": ["MR"],
            "next_visit_date": "2026-12-10",
        },
    ),
    GoldenCase(
        case_id="G06_negated_danger_safe",
        language="hi-IN",
        text="Sunita ANC checkup. Weight 56 kilo. Koi bleeding nahi hai, bukhar nahi hai, sab theek hai.",
        expected_danger=False,
        expected_fields={
            "beneficiary_id": "BEN-1045",
            "visit_type": "ANC",
            "weight_kg": 56.0,
        },
    ),
    GoldenCase(
        case_id="G07_historical_symptom_safe",
        language="hi-IN",
        text="Anita ANC visit. Pichle mahine bukhar tha ab bilkul theek hai. Weight 50 kilo.",
        expected_danger=False,
        expected_fields={
            "beneficiary_id": "BEN-1047",
            "visit_type": "ANC",
            "weight_kg": 50.0,
        },
    ),
    GoldenCase(
        case_id="G08_other_person_symptom_safe",
        language="hi-IN",
        text="Sunita ANC visit, weight 53 kilo. Padosi ke bachche ko bukhar hai, Sunita theek hai.",
        expected_danger=False,
        expected_fields={
            "beneficiary_id": "BEN-1045",
            "visit_type": "ANC",
            "weight_kg": 53.0,
        },
    ),
    # --- Danger-Sign Positive Cases (expected_danger=True — MUST hit 100% recall!) ---
    GoldenCase(
        case_id="D01_anc_bleeding_hinglish",
        language="hi-IN",
        text="Lakshmi ko pregnancy mein khoon aa raha hai, heavy bleeding ho rahi hai.",
        expected_danger=True,
        visit_type_context="ANC",
    ),
    GoldenCase(
        case_id="D02_anc_bleeding_asr_misspell",
        language="hi-IN",
        text="ANC visit Sunita, koon bah raha hai subah se.",
        expected_danger=True,
        visit_type_context="ANC",
    ),
    GoldenCase(
        case_id="D03_convulsions_hinglish",
        language="hi-IN",
        text="Mother ko fits aa rahe hain, tez jhatke aur daura pada hai.",
        expected_danger=True,
        visit_type_context="ANC",
    ),
    GoldenCase(
        case_id="D04_preeclampsia_headache_vision",
        language="hi-IN",
        text="Pregnant woman has severe headache and blurred vision, aankhon ke samne dhundhla dikh raha hai.",
        expected_danger=True,
        visit_type_context="ANC",
    ),
    GoldenCase(
        case_id="D05_high_bp_threshold",
        language="en-IN",
        text="ANC checkup Anita, BP is 150/96 mmHg with swelling on face.",
        expected_danger=True,
        visit_type_context="ANC",
    ),
    GoldenCase(
        case_id="D06_pph_excessive_bleeding",
        language="hi-IN",
        text="PNC visit Kavitha, delivery ke baad 6 pads bheeg gaye aaj, heavy postpartum bleeding.",
        expected_danger=True,
        visit_type_context="PNC",
    ),
    GoldenCase(
        case_id="D07_newborn_not_feeding_hinglish",
        language="hi-IN",
        text="Newborn baby doodh nahi pee raha hai, unable to suck since morning.",
        expected_danger=True,
        visit_type_context="Newborn",
    ),
    GoldenCase(
        case_id="D08_newborn_chest_indrawing",
        language="hi-IN",
        text="Navjat shishu mein chest indrawing ho raha hai aur tez saans chal rahi hai.",
        expected_danger=True,
        visit_type_context="Newborn",
    ),
    GoldenCase(
        case_id="D09_newborn_rr_threshold",
        language="en-IN",
        text="Newborn breathing rate is 68 breaths per minute.",
        expected_danger=True,
        visit_type_context="Newborn",
    ),
    GoldenCase(
        case_id="D10_newborn_umbilical_pus",
        language="hi-IN",
        text="Baby ke naal mein redness aur pus aa raha hai.",
        expected_danger=True,
        visit_type_context="Newborn",
    ),
    GoldenCase(
        case_id="D11_newborn_lethargy_unconscious",
        language="en-IN",
        text="Newborn is unusually lethargic and unconscious, limbs are limp.",
        expected_danger=True,
        visit_type_context="Newborn",
    ),
    GoldenCase(
        case_id="D12_newborn_vlbw_threshold",
        language="hi-IN",
        text="Newborn birth weight is 1.6 kilo, very small baby.",
        expected_danger=True,
        visit_type_context="Newborn",
    ),
    GoldenCase(
        case_id="D13_kannada_newborn_not_feeding",
        language="kn-IN",
        text="ಮಗು ಹಾಲು ಕುಡಿಯುತ್ತಿಲ್ಲ, ತುಂಬಾ ಜ್ವರ ಇದೆ.",
        expected_danger=True,
        visit_type_context="Newborn",
    ),
    GoldenCase(
        case_id="D14_tamil_anc_bleeding",
        language="ta-IN",
        text="கர்ப்பிணிக்கு ரத்தப்போக்கு உள்ளது, உடனே பார்க்க வேண்டும்.",
        expected_danger=True,
        visit_type_context="ANC",
    ),
    GoldenCase(
        case_id="D15_mixed_negation_and_positive",
        language="en-IN",
        text="No bleeding in mother, but newborn is unable to feed and feels cold to touch.",
        expected_danger=True,
        visit_type_context="Newborn",
    ),
)


def run_golden_evaluation() -> dict[str, Any]:
    extractor = VisitFieldExtractor()
    danger_tp = 0
    danger_fn = 0
    danger_fp = 0
    danger_tn = 0
    missed_danger_cases: list[str] = []
    false_positive_cases: list[str] = []

    field_correct: dict[str, int] = {}
    field_total: dict[str, int] = {}
    field_mismatches: list[str] = []

    for case in GOLDEN_SET:
        d_res = detect_danger_signs(
            case.text,
            language=case.language,
            context={"is_partial": False, "visit_type": case.visit_type_context},
        )
        if case.expected_danger:
            if d_res.danger_sign_flagged:
                danger_tp += 1
            else:
                danger_fn += 1
                missed_danger_cases.append(case.case_id)
        else:
            if d_res.danger_sign_flagged:
                danger_fp += 1
                false_positive_cases.append(case.case_id)
            else:
                danger_tn += 1

        if case.expected_fields:
            e_res = extractor.extract(
                case.text, reference_date=REF_DATE, active_language=case.language
            )
            for fname, expected_val in case.expected_fields.items():
                field_total[fname] = field_total.get(fname, 0) + 1
                actual_val = e_res.patch.get(fname)
                matched = (
                    set(actual_val) == set(expected_val)
                    if isinstance(expected_val, list) and isinstance(actual_val, list)
                    else actual_val == expected_val
                )
                if matched:
                    field_correct[fname] = field_correct.get(fname, 0) + 1
                else:
                    field_mismatches.append(
                        f"{case.case_id}.{fname}: expected={expected_val!r} got={actual_val!r}"
                    )

    recall = danger_tp / (danger_tp + danger_fn) if (danger_tp + danger_fn) else 1.0
    specificity = danger_tn / (danger_tn + danger_fp) if (danger_tn + danger_fp) else 1.0
    per_field_accuracy = {
        k: field_correct.get(k, 0) / v for k, v in sorted(field_total.items())
    }
    return {
        "total_cases": len(GOLDEN_SET),
        "danger_recall": recall,
        "danger_specificity": specificity,
        "danger_tp": danger_tp,
        "danger_fn": danger_fn,
        "danger_fp": danger_fp,
        "danger_tn": danger_tn,
        "missed_danger_cases": missed_danger_cases,
        "false_positive_cases": false_positive_cases,
        "per_field_accuracy": per_field_accuracy,
        "field_mismatches": field_mismatches,
    }


def test_golden_evaluation_100_percent_danger_recall_and_field_accuracy() -> None:
    report = run_golden_evaluation()
    print("\n=== GOLDEN EVAL REPORT (1E) ===")
    print(
        f"Danger Recall: {report['danger_recall']*100:.1f}% "
        f"(TP={report['danger_tp']}, FN={report['danger_fn']})"
    )
    print(
        f"Danger Specificity: {report['danger_specificity']*100:.1f}% "
        f"(TN={report['danger_tn']}, FP={report['danger_fp']})"
    )
    for fname, acc in report["per_field_accuracy"].items():
        print(f"  Field '{fname}' accuracy: {acc*100:.1f}%")

    assert report["danger_recall"] == 1.0, f"MISSED DANGER SIGNS: {report['missed_danger_cases']}"
    assert report["danger_specificity"] == 1.0, f"FALSE POSITIVES: {report['false_positive_cases']}"
    assert report["field_mismatches"] == [], f"Field extraction mismatches: {report['field_mismatches']}"

