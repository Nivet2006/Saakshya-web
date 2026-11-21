"""Instrumentation and evaluation metrics for numeric, unit, date, and ID accuracy.

Measures separately (Section G):
- Numeric exact-match accuracy
- Decimal accuracy
- Unit recognition accuracy
- Date accuracy
- Beneficiary ID accuracy
- Numeric omission rate
- Incorrect numeric confirmation rate
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.extraction.extractor import VisitFieldExtractor
from app.extraction.numbers import find_weight_candidates, normalize_numeric_text


@dataclass(frozen=True)
class NumericEvalCase:
    """Single test case for numeric / entity recognition & extraction evaluation."""

    case_id: str
    language: str
    spoken_text: str
    category: str = "clean"  # "clean" | "noisy" | "codemix" | "regional" | "decimal" | "correction"
    expected_weight_kg: Decimal | None = None
    expected_unit_kind: str | None = None  # "kg" | "g" | "compound_kg_g" | "unitless"
    expected_has_decimal: bool = False
    expected_next_visit_date: str | None = None
    expected_beneficiary_id: str | None = None
    expected_observations: dict[str, Any] = field(default_factory=dict)
    expect_clarification_instead_of_confirm: bool = False
    visit_type_hint: str | None = None


@dataclass
class NumericEvalReport:
    """Aggregated evaluation metrics across a corpus of utterances or ASR transcripts."""

    mode_label: str
    total_cases: int
    numeric_exact_match_accuracy: float
    decimal_accuracy: float
    unit_recognition_accuracy: float
    date_accuracy: float
    beneficiary_id_accuracy: float
    numeric_omission_rate: float
    incorrect_numeric_confirmation_rate: float
    counts: dict[str, int] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode_label": self.mode_label,
            "total_cases": self.total_cases,
            "numeric_exact_match_accuracy": round(self.numeric_exact_match_accuracy, 4),
            "decimal_accuracy": round(self.decimal_accuracy, 4),
            "unit_recognition_accuracy": round(self.unit_recognition_accuracy, 4),
            "date_accuracy": round(self.date_accuracy, 4),
            "beneficiary_id_accuracy": round(self.beneficiary_id_accuracy, 4),
            "numeric_omission_rate": round(self.numeric_omission_rate, 4),
            "incorrect_numeric_confirmation_rate": round(self.incorrect_numeric_confirmation_rate, 4),
            "counts": dict(self.counts),
            "failures": list(self.failures),
        }


def _to_decimal(val: Any) -> Decimal | None:
    if val is None or isinstance(val, bool):
        return None
    try:
        return Decimal(str(val)).quantize(Decimal("0.001"))
    except (InvalidOperation, ValueError):
        return None


def evaluate_transcripts(
    cases: list[NumericEvalCase],
    transcripts_by_id: dict[str, str],
    *,
    mode_label: str,
    reference_date: date = date(2026, 11, 21),
    extractor: VisitFieldExtractor | None = None,
) -> NumericEvalReport:
    """Evaluate extraction accuracy across a map of `case_id -> transcript`."""
    ext = extractor or VisitFieldExtractor()

    num_total = 0
    num_exact = 0
    num_omitted = 0
    num_incorrect_confirmed = 0

    dec_total = 0
    dec_exact = 0

    unit_total = 0
    unit_correct = 0

    date_total = 0
    date_correct = 0

    ben_total = 0
    ben_correct = 0

    failures: list[str] = []

    for case in cases:
        transcript = transcripts_by_id.get(case.case_id, "")
        res = ext.extract(
            transcript,
            reference_date=reference_date,
            active_language=case.language,
        )

        # 1. Numeric exact-match, decimal, omission, & incorrect confirmation
        if case.expected_weight_kg is not None:
            num_total += 1
            expected_w = case.expected_weight_kg.quantize(Decimal("0.001"))
            actual_w = _to_decimal(res.patch.get("weight_kg"))
            has_weight_clar = any(c.field_name == "weight_kg" for c in res.clarifications)

            if actual_w == expected_w:
                num_exact += 1
            else:
                if actual_w is None and not has_weight_clar:
                    num_omitted += 1
                elif actual_w is not None and not has_weight_clar:
                    # Wrong numeric value accepted as confirmed without asking clarification!
                    num_incorrect_confirmed += 1
                failures.append(
                    f"{case.case_id} [weight]: expected={expected_w} got={actual_w} "
                    f"clar={has_weight_clar} transcript={transcript!r}"
                )

            if case.expected_has_decimal:
                dec_total += 1
                if actual_w == expected_w:
                    dec_exact += 1

            if case.expected_unit_kind is not None:
                unit_total += 1
                norm_t = normalize_numeric_text(transcript)
                wcands = find_weight_candidates(norm_t)
                matched_unit = any(
                    c.unit_kind == case.expected_unit_kind
                    and c.value_kg.quantize(Decimal("0.001")) == expected_w
                    for c in wcands
                )
                if matched_unit or (actual_w == expected_w and case.expected_unit_kind == "unitless"):
                    unit_correct += 1
                else:
                    failures.append(
                        f"{case.case_id} [unit]: expected={case.expected_unit_kind} "
                        f"cands={[(c.unit_kind, str(c.value_kg)) for c in wcands]}"
                    )

        # Numeric observations (e.g. temperature, hemoglobin, blood_pressure)
        for obs_key, expected_obs_val in case.expected_observations.items():
            num_total += 1
            matched_obs = next((o for o in res.observations if o.key == obs_key), None)
            actual_val = matched_obs.value if matched_obs else None
            if isinstance(expected_obs_val, Decimal):
                act_dec = _to_decimal(actual_val)
                if act_dec == expected_obs_val.quantize(Decimal("0.001")):
                    num_exact += 1
                else:
                    if act_dec is None:
                        num_omitted += 1
                    elif matched_obs and matched_obs.status == "confirmed":
                        num_incorrect_confirmed += 1
                    failures.append(
                        f"{case.case_id} [{obs_key}]: expected={expected_obs_val} got={actual_val}"
                    )
                if case.expected_has_decimal:
                    dec_total += 1
                    if act_dec == expected_obs_val.quantize(Decimal("0.001")):
                        dec_exact += 1
            else:
                if str(actual_val) == str(expected_obs_val):
                    num_exact += 1
                else:
                    if actual_val is None:
                        num_omitted += 1
                    elif matched_obs and matched_obs.status == "confirmed":
                        num_incorrect_confirmed += 1
                    failures.append(
                        f"{case.case_id} [{obs_key}]: expected={expected_obs_val!r} got={actual_val!r}"
                    )

        # 2. Ambiguous / adversarial numeric cases that MUST NOT be confirmed silently
        if case.expect_clarification_instead_of_confirm:
            num_total += 1
            if "weight_kg" in res.patch:
                num_incorrect_confirmed += 1
                failures.append(
                    f"{case.case_id} [unsafe_confirm]: silently accepted weight_kg={res.patch['weight_kg']}"
                )
            else:
                num_exact += 1

        # 3. Date accuracy
        if case.expected_next_visit_date is not None:
            date_total += 1
            actual_d = res.patch.get("next_visit_date")
            if actual_d == case.expected_next_visit_date:
                date_correct += 1
            else:
                failures.append(
                    f"{case.case_id} [date]: expected={case.expected_next_visit_date} got={actual_d} transcript={transcript!r}"
                )

        # 4. Beneficiary ID accuracy
        if case.expected_beneficiary_id is not None:
            ben_total += 1
            actual_bid = res.patch.get("beneficiary_id")
            if actual_bid == case.expected_beneficiary_id:
                ben_correct += 1
            else:
                failures.append(
                    f"{case.case_id} [ben_id]: expected={case.expected_beneficiary_id} got={actual_bid} transcript={transcript!r}"
                )

    return NumericEvalReport(
        mode_label=mode_label,
        total_cases=len(cases),
        numeric_exact_match_accuracy=(num_exact / num_total) if num_total else 1.0,
        decimal_accuracy=(dec_exact / dec_total) if dec_total else 1.0,
        unit_recognition_accuracy=(unit_correct / unit_total) if unit_total else 1.0,
        date_accuracy=(date_correct / date_total) if date_total else 1.0,
        beneficiary_id_accuracy=(ben_correct / ben_total) if ben_total else 1.0,
        numeric_omission_rate=(num_omitted / num_total) if num_total else 0.0,
        incorrect_numeric_confirmation_rate=(num_incorrect_confirmed / num_total) if num_total else 0.0,
        counts={
            "numeric_total": num_total,
            "numeric_exact": num_exact,
            "numeric_omitted": num_omitted,
            "numeric_incorrect_confirmed": num_incorrect_confirmed,
            "decimal_total": dec_total,
            "decimal_exact": dec_exact,
            "unit_total": unit_total,
            "unit_correct": unit_correct,
            "date_total": date_total,
            "date_correct": date_correct,
            "beneficiary_id_total": ben_total,
            "beneficiary_id_correct": ben_correct,
        },
        failures=failures,
    )

