"""Unit and integration tests for the deterministic Rule-Based Clinical Risk Engine."""

import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.healthcare.risk_engine import (
    assess_clinical_risk,
    calculate_risk,
    extract_risk_factors,
    normalize_patient_category,
)


def test_normalize_patient_category():
    assert normalize_patient_category("pregnant") == "pregnant"
    assert normalize_patient_category("ANC") == "pregnant"
    assert normalize_patient_category("PNC") == "pregnant"
    assert normalize_patient_category("mother") == "pregnant"
    assert normalize_patient_category("child") == "child"
    assert normalize_patient_category("newborn") == "child"
    assert normalize_patient_category("Infant") == "child"
    assert normalize_patient_category("pediatric") == "child"
    assert normalize_patient_category("elder") == "elder"
    assert normalize_patient_category("elderly") == "elder"
    assert normalize_patient_category("geriatric") == "elder"
    assert normalize_patient_category("adult") == "adult"
    assert normalize_patient_category("general") == "adult"
    assert normalize_patient_category(None) == "adult"


def test_pregnant_mother_bleeding_critical():
    # Bleeding boolean
    res = assess_clinical_risk({"bleeding": True}, "pregnant")
    assert res.risk == "Critical"
    assert res.severity_rank == 3
    assert len(res.rules_matched) > 0
    assert "Active Bleeding detected" in res.rules_matched[0]
    assert calculate_risk({"bleeding": True}, "pregnant") == "Critical"

    # Spoken Indic symptom
    res_indic = assess_clinical_risk({"symptoms": ["योनि से रक्तस्राव"]}, "ANC")
    assert res_indic.risk == "Critical"


def test_pregnant_mother_high_bp_and_swelling_high():
    res = assess_clinical_risk({"highBP": True, "swelling": True}, "pregnant")
    assert res.risk == "High"
    assert res.severity_rank == 2
    assert "High Blood Pressure + Swelling detected" in res.rules_matched[0]

    # Numeric BP check (systolic >= 140)
    res_num = assess_clinical_risk({"systolicBP": 145, "swelling": True}, "PNC")
    assert res_num.risk == "High"


def test_pregnant_mother_fever_ge_4_days_medium():
    res = assess_clinical_risk({"feverDays": 4}, "pregnant")
    assert res.risk == "Medium"
    assert res.severity_rank == 1
    assert "Fever >= 4 days" in res.rules_matched[0]

    res_5 = assess_clinical_risk({"feverDays": 5}, "ANC")
    assert res_5.risk == "Medium"


def test_pregnant_mother_swelling_alone_medium():
    res = assess_clinical_risk({"swelling": True, "highBP": False}, "pregnant")
    assert res.risk == "Medium"
    assert res.severity_rank == 1
    assert "Swelling alone detected" in res.rules_matched[0]


def test_pregnant_mother_normal_low():
    res = assess_clinical_risk({"feverDays": 2, "swelling": False, "highBP": False}, "pregnant")
    assert res.risk == "Low"
    assert res.severity_rank == 0


def test_child_breathing_issue_high():
    res = assess_clinical_risk({"breathingIssue": True}, "child")
    assert res.risk == "High"
    assert res.severity_rank == 2
    assert "Breathing issue" in res.rules_matched[0]

    # Chest indrawing
    res_chest = assess_clinical_risk({"chestIndrawing": True}, "Newborn")
    assert res_chest.risk == "High"

    # Symptom list
    res_sym = assess_clinical_risk({"symptoms": ["severe chest indrawing"]}, "infant")
    assert res_sym.risk == "High"


def test_child_fever_ge_4_days_medium():
    res = assess_clinical_risk({"feverDays": 4}, "child")
    assert res.risk == "Medium"
    assert res.severity_rank == 1

    # Fever < 4 days is Low in child if no breathing issues
    res_3 = assess_clinical_risk({"feverDays": 3}, "child")
    assert res_3.risk == "Low"


def test_child_normal_low():
    res = assess_clinical_risk({}, "child")
    assert res.risk == "Low"


def test_adult_breathing_issue_high():
    res = assess_clinical_risk({"breathingIssue": True}, "adult")
    assert res.risk == "High"
    assert res.severity_rank == 2


def test_adult_fever_ge_5_days_medium():
    res = assess_clinical_risk({"feverDays": 5}, "adult")
    assert res.risk == "Medium"
    assert res.severity_rank == 1

    res_4 = assess_clinical_risk({"feverDays": 4}, "adult")
    assert res_4.risk == "Low"


def test_elderly_breathing_and_fever():
    # Breathing issue -> High
    res_breath = assess_clinical_risk({"breathingIssue": True}, "elder")
    assert res_breath.risk == "High"

    # Fever >= 3 days -> Medium for elder
    res_fever = assess_clinical_risk({"feverDays": 3}, "elderly")
    assert res_fever.risk == "Medium"


def test_api_clinical_risk_endpoint():
    client = TestClient(create_app())
    payload = {
        "schema_version": "v1",
        "patient_type": "ANC",
        "structured": {
            "bleeding": True,
            "feverDays": 2,
        },
    }
    resp = client.post("/api/v1/clinical/assess-risk", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["schema_version"] == "v1"
    assessment = data["assessment"]
    assert assessment["risk"] == "Critical"
    assert assessment["category"] == "pregnant"
    assert len(assessment["rules_matched"]) > 0
    assert "Active Bleeding detected" in assessment["rules_matched"][0]
