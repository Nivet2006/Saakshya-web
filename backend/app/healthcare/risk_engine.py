"""Rule-Based Clinical Risk Engine (Python / FastAPI / Healthcare Layer).

Grounded in National Health Mission (NHM), MoHFW, HBNC & IMNCI protocols.
Unlike black-box LLM systems, this engine is 100% deterministic, explainable,
auditable, and categorized by patient lifecycle:

1. Pregnant Mother (ANC / PNC):
   - Bleeding -> Critical (Obstetric hemorrhage emergency)
   - High BP + Swelling -> High (Pre-eclampsia / Eclampsia risk)
   - Fever >= 4 days -> Medium (Prolonged maternal pyrexia / sepsis risk)
   - Swelling alone -> Medium (Maternal edema surveillance)
2. Child (Newborn / Infant):
   - Breathing issue / Severe chest indrawing -> High (Acute respiratory distress / Severe pneumonia)
   - Fever >= 4 days -> Medium (Persistent pediatric fever / Sepsis evaluation)
3. Adult & Elderly:
   - Breathing issue -> High (Acute cardiac / respiratory distress)
   - Fever >= 5 days (>= 3 days for elderly) -> Medium (Prolonged infectious fever)
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


RiskLevel = Literal["Critical", "High", "Medium", "Low"]
PatientCategory = Literal["pregnant", "child", "elder", "adult"]


class ClinicalRiskFactors(BaseModel):
    model_config = ConfigDict(extra="forbid")

    has_bleeding: bool = False
    has_high_bp: bool = False
    has_swelling: bool = False
    has_breathing_issue: bool = False
    fever_days: int | None = None
    detected_symptoms: list[str] = Field(default_factory=list)


class ClinicalRiskAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk: RiskLevel
    severity_rank: int = Field(description="3=Critical, 2=High, 1=Medium, 0=Low")
    category: PatientCategory
    rules_matched: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    recommended_action: str
    is_deterministic: bool = True
    factors: ClinicalRiskFactors


def normalize_patient_category(raw_type: str | None) -> PatientCategory:
    if not raw_type or not isinstance(raw_type, str):
        return "adult"

    clean = raw_type.strip().lower()

    if clean in ("pregnant", "pregnancy", "anc", "pnc", "mother", "maternal"):
        return "pregnant"

    if clean in (
        "child",
        "newborn",
        "infant",
        "pediatric",
        "baby",
        "toddler",
        "immunisation",
        "immunization",
    ):
        return "child"

    if clean in ("elder", "elderly", "senior", "geriatric"):
        return "elder"

    return "adult"


def extract_risk_factors(structured: dict[str, Any] | None = None) -> ClinicalRiskFactors:
    if not structured:
        return ClinicalRiskFactors()

    fever_days_raw = structured.get("fever_days") or structured.get("feverDays")
    high_bp_raw = structured.get("high_bp") or structured.get("highBP", False)
    swelling_raw = structured.get("swelling", False)
    bleeding_raw = structured.get("bleeding", False)
    breathing_raw = structured.get("breathing_issue") or structured.get("breathingIssue", False)
    chest_indrawing = structured.get("chest_indrawing") or structured.get("chestIndrawing", False)

    systolic_bp = structured.get("systolic_bp") or structured.get("systolicBP")
    diastolic_bp = structured.get("diastolic_bp") or structured.get("diastolicBP")

    raw_symptoms = structured.get("symptoms", [])
    if isinstance(raw_symptoms, (list, tuple, set)):
        symptom_list = [str(s) for s in raw_symptoms]
        symptom_lower = [s.lower().strip() for s in symptom_list]
    else:
        symptom_list = []
        symptom_lower = []

    def _matches_any(targets: tuple[str, ...]) -> bool:
        return any(any(t in s for t in targets) for s in symptom_lower)

    # High BP evaluation
    is_bp_elevated = (
        bool(high_bp_raw)
        or _matches_any(("high bp", "bp high", "hypertension", "उच्च रक्तचाप", "रक्तचाप ज्यादा", "रक्तदाब जास्त"))
    )
    if not is_bp_elevated and systolic_bp is not None:
        try:
            if float(systolic_bp) >= 140.0:
                is_bp_elevated = True
        except (ValueError, TypeError):
            pass
    if not is_bp_elevated and diastolic_bp is not None:
        try:
            if float(diastolic_bp) >= 90.0:
                is_bp_elevated = True
        except (ValueError, TypeError):
            pass

    # Swelling
    has_swelling = (
        bool(swelling_raw)
        or _matches_any(("swelling", "edema", "oedema", "सूजन", "सोज़िश", "सुज", "सूज"))
    )

    # Bleeding
    has_bleeding = (
        bool(bleeding_raw)
        or _matches_any((
            "bleeding",
            "vaginal bleeding",
            "pv bleeding",
            "per vaginum bleeding",
            "antepartum hemorrhage",
            "postpartum hemorrhage",
            "रक्तस्राव",
            "खून आना",
            "ब्लीडिंग",
            "रक्तदाब",
        ))
    )

    # Breathing
    has_breathing_issue = (
        bool(breathing_raw)
        or bool(chest_indrawing)
        or _matches_any((
            "breathing issue",
            "breathing problem",
            "shortness of breath",
            "difficulty breathing",
            "chest indrawing",
            "severe chest indrawing",
            "rapid breathing",
            "stridor",
            "सांस फूलना",
            "सांस लेने में दिक्कत",
            "सांस की तकलीफ",
            "श्वास घेण्यास त्रास",
            "धाप लागणे",
        ))
    )

    # Fever days
    parsed_fever_days: int | None = None
    if fever_days_raw is not None:
        try:
            val = int(fever_days_raw)
            if val >= 0:
                parsed_fever_days = val
        except (ValueError, TypeError):
            pass

    return ClinicalRiskFactors(
        has_bleeding=has_bleeding,
        has_high_bp=is_bp_elevated,
        has_swelling=has_swelling,
        has_breathing_issue=has_breathing_issue,
        fever_days=parsed_fever_days,
        detected_symptoms=symptom_list,
    )


def assess_clinical_risk(
    structured: dict[str, Any] | None = None,
    patient_type_raw: str = "general",
) -> ClinicalRiskAssessment:
    """Evaluates the full deterministic, explainable clinical risk assessment."""
    category = normalize_patient_category(patient_type_raw)
    factors = extract_risk_factors(structured)

    rules_matched: list[str] = []
    rationale: list[str] = []
    risk: RiskLevel = "Low"
    severity_rank = 0
    recommended_action = (
        "Continue routine ASHA community register tracking and regular checkup."
    )

    # 1. PREGNANT MOTHER (ANC / PNC)
    if category == "pregnant":
        if factors.has_bleeding:
            risk = "Critical"
            severity_rank = 3
            rules_matched.append("Pregnant Mother: Active Bleeding detected -> Immediate Emergency Escalation")
            rationale.append(
                "Vaginal bleeding during pregnancy or postpartum is an obstetric emergency (antepartum/postpartum hemorrhage). Official NHM/MOD6 guidelines require immediate emergency transfer."
            )
            recommended_action = (
                "IMMEDIATE EMERGENCY: Dispatch 108 ambulance for direct transfer to First Referral Unit (FRU) / District Hospital. Alert Medical Officer immediately."
            )
        elif factors.has_high_bp and factors.has_swelling:
            risk = "High"
            severity_rank = 2
            rules_matched.append("Pregnant Mother: High Blood Pressure + Swelling detected -> Pre-eclampsia Risk")
            rationale.append(
                "Co-occurrence of gestational hypertension and peripheral/facial edema is a classic indicator of severe pre-eclampsia requiring urgent clinical intervention."
            )
            recommended_action = (
                "URGENT CLINICAL REVIEW: Refer to Primary Health Centre (PHC) Medical Officer within 24 hours for urine protein analysis and antihypertensive management."
            )
        elif factors.fever_days is not None and factors.fever_days >= 4:
            risk = "Medium"
            severity_rank = 1
            rules_matched.append(f"Pregnant Mother: Fever >= 4 days ({factors.fever_days} days) -> Prolonged Pyrexia Risk")
            rationale.append(
                "Prolonged fever in maternal care poses high risks of chorioamnionitis, systemic infection, or malaria requiring prompt diagnostic workup."
            )
            recommended_action = (
                "SCHEDULE REVIEW: Refer to PHC within 48 hours for blood smear, malaria RDT, and infection workup. Advise fluid intake and rest."
            )
        elif factors.has_swelling:
            risk = "Medium"
            severity_rank = 1
            rules_matched.append("Pregnant Mother: Swelling alone detected -> Gestational Edema Surveillance")
            rationale.append(
                "Pedal or facial edema without verified hypertension requires close surveillance to detect emerging pre-eclampsia or maternal anemia early."
            )
            recommended_action = (
                "ACTIVE MONITORING: Schedule ASHA home follow-up within 48 hours. Measure blood pressure and advise salt reduction and foot elevation."
            )

    # 2. CHILD (NEWBORN / INFANT)
    elif category == "child":
        if factors.has_breathing_issue:
            risk = "High"
            severity_rank = 2
            rules_matched.append("Child / Newborn: Breathing issue / Severe chest indrawing -> Acute Respiratory Distress")
            rationale.append(
                "Fast breathing or lower chest wall indrawing in infants is an official IMNCI / HBNC red flag for severe pneumonia or sepsis."
            )
            recommended_action = (
                "URGENT ESCALATION: Immediate referral to PHC or Special Newborn Care Unit (SNCU). Keep child warm with Kangaroo Mother Care (KMC) during transport."
            )
        elif factors.fever_days is not None and factors.fever_days >= 4:
            risk = "Medium"
            severity_rank = 1
            rules_matched.append(f"Child: Fever >= 4 days ({factors.fever_days} days) -> Persistent Pediatric Pyrexia")
            rationale.append(
                "Fever lasting 4 or more days in infants warrants pediatric evaluation to rule out focal bacterial infection, UTI, or severe malaria."
            )
            recommended_action = (
                "CLINICAL EVALUATION: Refer to ANM/PHC for examination and malaria testing within 24 hours. Ensure frequent breastfeeding or ORS."
            )
        elif factors.has_bleeding:
            risk = "High"
            severity_rank = 2
            rules_matched.append("Child / Newborn: Bleeding detected -> Pediatric Emergency")
            rationale.append(
                "Umbilical stump bleeding or gastrointestinal bleeding in a newborn is a critical sign of vitamin K deficiency or hemorrhagic disease."
            )
            recommended_action = "URGENT ESCALATION: Refer immediately to PHC / Child Care Centre."

    # 3. ELDERLY
    elif category == "elder":
        if factors.has_breathing_issue:
            risk = "High"
            severity_rank = 2
            rules_matched.append("Elderly: Breathing issue detected -> Cardiorespiratory Distress Risk")
            rationale.append(
                "Dyspnea or sudden shortness of breath in the elderly presents acute risks of myocardial infarction, pulmonary edema, or COPD exacerbation."
            )
            recommended_action = (
                "URGENT CLINICAL REVIEW: Transfer to PHC/CHC emergency facility. Maintain comfortable upright sitting posture."
            )
        elif factors.has_bleeding:
            risk = "High"
            severity_rank = 2
            rules_matched.append("Elderly: Bleeding detected -> Acute Hemorrhagic Concern")
            rationale.append("Active blood loss in elderly patients requires prompt hospital evaluation.")
            recommended_action = "URGENT ESCALATION: Refer to PHC for stabilization and hemorrhage evaluation."
        elif factors.fever_days is not None and factors.fever_days >= 3:
            risk = "Medium"
            severity_rank = 1
            rules_matched.append(f"Elderly: Fever >= 3 days ({factors.fever_days} days) -> Persistent Geriatric Infection")
            rationale.append("Elderly patients deteriorate rapidly with untreated bacterial infections or pneumonia.")
            recommended_action = (
                "CLINICAL REVIEW: Medical officer assessment and laboratory blood screening at PHC within 24-48 hours."
            )

    # 4. ADULT & GENERAL
    else:
        if factors.has_breathing_issue:
            risk = "High"
            severity_rank = 2
            rules_matched.append("Adult: Breathing issue detected -> Acute Respiratory / Cardiac Compromise")
            rationale.append("Severe shortness of breath or respiratory distress in adults warrants emergency clinical triage.")
            recommended_action = (
                "URGENT CLINICAL REVIEW: Refer to nearest PHC/CHC for oxygenation and vital evaluation."
            )
        elif factors.has_bleeding:
            risk = "High"
            severity_rank = 2
            rules_matched.append("Adult: Bleeding detected -> Acute Hemorrhage")
            rationale.append("Uncontrolled or unexplained bleeding requires clinical assessment.")
            recommended_action = "URGENT ESCALATION: Urgent referral to medical officer."
        elif factors.fever_days is not None and factors.fever_days >= 5:
            risk = "Medium"
            severity_rank = 1
            rules_matched.append(f"Adult: Fever >= 5 days ({factors.fever_days} days) -> Prolonged Adult Pyrexia")
            rationale.append(
                "Persistent fever beyond 5 days exceeds normal self-limiting viral trajectory; rule out dengue, typhoid, or malaria."
            )
            recommended_action = (
                "CLINICAL WORKUP: Refer to PHC for diagnostic screening (malaria, typhoid, complete blood count)."
            )

    return ClinicalRiskAssessment(
        risk=risk,
        severity_rank=severity_rank,
        category=category,
        rules_matched=rules_matched,
        rationale=rationale,
        recommended_action=recommended_action,
        is_deterministic=True,
        factors=factors,
    )


def calculate_risk(
    structured: dict[str, Any] | None = None,
    patient_type_raw: str = "general",
) -> RiskLevel:
    """Standard AASHA risk calculation interface (100% backward & forward compatible)."""
    return assess_clinical_risk(structured, patient_type_raw).risk
