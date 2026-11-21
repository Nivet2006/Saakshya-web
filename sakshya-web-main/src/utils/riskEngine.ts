/**
 * Rule-Based Clinical Risk Engine (utils/riskEngine.ts / utils/riskEngine.js)
 *
 * Grounded in National Health Mission (NHM), MoHFW, HBNC & IMNCI protocols.
 * Unlike black-box LLM systems, this engine is 100% deterministic, explainable,
 * auditable, and categorized by patient lifecycle:
 *
 * 1. Pregnant Mother (ANC / PNC):
 *    - Bleeding -> Critical (Obstetric hemorrhage emergency)
 *    - High BP + Swelling -> High (Pre-eclampsia / Eclampsia risk)
 *    - Fever >= 4 days -> Medium (Prolonged maternal pyrexia / sepsis risk)
 *    - Swelling alone -> Medium (Maternal edema surveillance)
 * 2. Child (Newborn / Infant):
 *    - Breathing issue / Severe chest indrawing -> High (Acute respiratory distress / Severe pneumonia)
 *    - Fever >= 4 days -> Medium (Persistent pediatric fever / Sepsis evaluation)
 * 3. Adult & Elderly:
 *    - Breathing issue -> High (Acute cardiac / respiratory distress)
 *    - Fever >= 5 days (>= 3 days for elderly) -> Medium (Prolonged infectious fever)
 */

export type RiskLevel = 'Critical' | 'High' | 'Medium' | 'Low';

export type PatientCategory = 'pregnant' | 'child' | 'elder' | 'adult';

export interface StructuredClinicalData {
  feverDays?: number | string | null;
  highBP?: boolean;
  swelling?: boolean;
  bleeding?: boolean;
  breathingIssue?: boolean;
  chestIndrawing?: boolean;
  symptoms?: string[];
  systolicBP?: number | null;
  diastolicBP?: number | null;
  temperatureF?: number | null;
  [key: string]: unknown;
}

export interface ClinicalRiskFactors {
  hasBleeding: boolean;
  hasHighBP: boolean;
  hasSwelling: boolean;
  hasBreathingIssue: boolean;
  feverDays: number | null;
  detectedSymptoms: string[];
}

export interface ClinicalRiskAssessment {
  risk: RiskLevel;
  severityRank: number; // 3 = Critical, 2 = High, 1 = Medium, 0 = Low
  category: PatientCategory;
  rulesMatched: string[];
  rationale: string[];
  recommendedAction: string;
  isDeterministic: true;
  factors: ClinicalRiskFactors;
}

/**
 * Normalizes raw patient type / category string to canonical enum:
 * 'pregnant' | 'child' | 'elder' | 'adult'
 */
export function normalizePatientCategory(rawType?: string | null): PatientCategory {
  if (!rawType || typeof rawType !== 'string') {
    return 'adult';
  }
  const clean = rawType.trim().toLowerCase();

  if (
    clean === 'pregnant' ||
    clean === 'pregnancy' ||
    clean === 'anc' ||
    clean === 'pnc' ||
    clean === 'mother' ||
    clean === 'maternal'
  ) {
    return 'pregnant';
  }

  if (
    clean === 'child' ||
    clean === 'newborn' ||
    clean === 'infant' ||
    clean === 'pediatric' ||
    clean === 'baby' ||
    clean === 'toddler' ||
    clean === 'immunisation' ||
    clean === 'immunization'
  ) {
    return 'child';
  }

  if (
    clean === 'elder' ||
    clean === 'elderly' ||
    clean === 'senior' ||
    clean === 'geriatric'
  ) {
    return 'elder';
  }

  return 'adult';
}

/**
 * Parses and extracts normalized clinical factors from structured visit data.
 */
export function extractRiskFactors(structured: StructuredClinicalData = {}): ClinicalRiskFactors {
  const {
    feverDays = null,
    highBP = false,
    swelling = false,
    bleeding = false,
    breathingIssue = false,
    chestIndrawing = false,
    symptoms = [],
    systolicBP = null,
    diastolicBP = null,
  } = structured;

  const rawSymptoms = Array.isArray(symptoms) ? symptoms : [];
  const symptomLower = rawSymptoms.map((s) => String(s).toLowerCase().trim());
  const matchesAny = (targets: string[]): boolean =>
    symptomLower.some((s) => targets.some((t) => s.includes(t)));

  // Numeric BP check (>= 140 systolic or >= 90 diastolic per NHM guidelines)
  const isBPElevated =
    Boolean(highBP) ||
    matchesAny(['high bp', 'bp high', 'hypertension', 'उच्च रक्तचाप', 'रक्तचाप ज्यादा', 'रक्तदाब']) ||
    (typeof systolicBP === 'number' && systolicBP >= 140) ||
    (typeof diastolicBP === 'number' && diastolicBP >= 90);

  const hasSwelling =
    Boolean(swelling) ||
    matchesAny(['swelling', 'edema', 'oedema', 'सूजन', 'सोज़िश', 'सुज', 'सूज']);

  const hasBleeding =
    Boolean(bleeding) ||
    matchesAny([
      'bleeding',
      'vaginal bleeding',
      'pv bleeding',
      'per vaginum bleeding',
      'antepartum hemorrhage',
      'postpartum hemorrhage',
      'रक्तस्राव',
      'खून आना',
      'ब्लीडिंग',
    ]);

  const hasBreathingIssue =
    Boolean(breathingIssue) ||
    Boolean(chestIndrawing) ||
    matchesAny([
      'breathing issue',
      'breathing problem',
      'shortness of breath',
      'difficulty breathing',
      'chest indrawing',
      'severe chest indrawing',
      'rapid breathing',
      'stridor',
      'सांस फूलना',
      'सांस लेने में दिक्कत',
      'श्वास घेण्यास त्रास',
      'धाप लागणे',
    ]);

  let parsedFeverDays: number | null = null;
  if (feverDays !== null && feverDays !== undefined) {
    const num = Number(feverDays);
    if (!Number.isNaN(num) && num >= 0) {
      parsedFeverDays = num;
    }
  }

  return {
    hasBleeding,
    hasHighBP: isBPElevated,
    hasSwelling,
    hasBreathingIssue,
    feverDays: parsedFeverDays,
    detectedSymptoms: rawSymptoms,
  };
}

/**
 * Evaluates the full deterministic, explainable clinical risk assessment.
 */
export function assessClinicalRisk(
  structured: StructuredClinicalData = {},
  patientTypeRaw: string = 'general'
): ClinicalRiskAssessment {
  const category = normalizePatientCategory(patientTypeRaw);
  const factors = extractRiskFactors(structured);
  const { hasBleeding, hasHighBP, hasSwelling, hasBreathingIssue, feverDays } = factors;

  const rulesMatched: string[] = [];
  const rationale: string[] = [];
  let risk: RiskLevel = 'Low';
  let severityRank = 0;
  let recommendedAction =
    'Continue routine ASHA community register tracking and regular maternal/child checkup.';

  // 1. PREGNANT MOTHER (ANC / PNC)
  if (category === 'pregnant') {
    if (hasBleeding) {
      risk = 'Critical';
      severityRank = 3;
      rulesMatched.push('Pregnant Mother: Active Bleeding detected -> Immediate Emergency Escalation');
      rationale.push(
        'Vaginal bleeding during pregnancy or postpartum is an obstetric emergency (antepartum/postpartum hemorrhage). Official NHM/MOD6 guidelines require immediate emergency transfer.'
      );
      recommendedAction =
        'IMMEDIATE EMERGENCY: Dispatch 108 ambulance for direct transfer to First Referral Unit (FRU) / District Hospital. Alert Medical Officer immediately.';
    } else if (hasHighBP && hasSwelling) {
      risk = 'High';
      severityRank = 2;
      rulesMatched.push('Pregnant Mother: High Blood Pressure + Swelling detected -> Pre-eclampsia Risk');
      rationale.push(
        'Co-occurrence of gestational hypertension and peripheral/facial edema is a classic indicator of severe pre-eclampsia requiring urgent clinical intervention.'
      );
      recommendedAction =
        'URGENT CLINICAL REVIEW: Refer to Primary Health Centre (PHC) Medical Officer within 24 hours for urine protein analysis and antihypertensive management.';
    } else if (feverDays !== null && feverDays >= 4) {
      risk = 'Medium';
      severityRank = 1;
      rulesMatched.push(`Pregnant Mother: Fever >= 4 days (${feverDays} days) -> Prolonged Pyrexia Risk`);
      rationale.push(
        'Prolonged fever in maternal care poses high risks of chorioamnionitis, systemic infection, or malaria requiring prompt diagnostic workup.'
      );
      recommendedAction =
        'SCHEDULE REVIEW: Refer to PHC within 48 hours for blood smear, malaria RDT, and infection workup. Advise fluid intake and rest.';
    } else if (hasSwelling) {
      risk = 'Medium';
      severityRank = 1;
      rulesMatched.push('Pregnant Mother: Swelling alone detected -> Gestational Edema Surveillance');
      rationale.push(
        'Pedal or facial edema without verified hypertension requires close surveillance to detect emerging pre-eclampsia or maternal anemia early.'
      );
      recommendedAction =
        'ACTIVE MONITORING: Schedule ASHA home follow-up within 48 hours. Measure blood pressure and advise salt reduction and foot elevation.';
    }
  }

  // 2. CHILD (NEWBORN / INFANT)
  else if (category === 'child') {
    if (hasBreathingIssue) {
      risk = 'High';
      severityRank = 2;
      rulesMatched.push('Child / Newborn: Breathing issue / Severe chest indrawing -> Acute Respiratory Distress');
      rationale.push(
        'Fast breathing or lower chest wall indrawing in infants is an official IMNCI / HBNC red flag for severe pneumonia or sepsis.'
      );
      recommendedAction =
        'URGENT ESCALATION: Immediate referral to PHC or Special Newborn Care Unit (SNCU). Keep child warm with Kangaroo Mother Care (KMC) during transport.';
    } else if (feverDays !== null && feverDays >= 4) {
      risk = 'Medium';
      severityRank = 1;
      rulesMatched.push(`Child: Fever >= 4 days (${feverDays} days) -> Persistent Pediatric Pyrexia`);
      rationale.push(
        'Fever lasting 4 or more days in infants warrants pediatric evaluation to rule out focal bacterial infection, UTI, or severe malaria.'
      );
      recommendedAction =
        'CLINICAL EVALUATION: Refer to ANM/PHC for examination and malaria testing within 24 hours. Ensure frequent breastfeeding or ORS.';
    } else if (hasBleeding) {
      risk = 'High';
      severityRank = 2;
      rulesMatched.push('Child / Newborn: Bleeding detected -> Pediatric Emergency');
      rationale.push(
        'Umbilical stump bleeding or gastrointestinal bleeding in a newborn is a critical sign of vitamin K deficiency or hemorrhagic disease.'
      );
      recommendedAction =
        'URGENT ESCALATION: Refer immediately to PHC / Child Care Centre.';
    }
  }

  // 3. ELDERLY
  else if (category === 'elder') {
    if (hasBreathingIssue) {
      risk = 'High';
      severityRank = 2;
      rulesMatched.push('Elderly: Breathing issue detected -> Cardiorespiratory Distress Risk');
      rationale.push(
        'Dyspnea or sudden shortness of breath in the elderly presents acute risks of myocardial infarction, pulmonary edema, or COPD exacerbation.'
      );
      recommendedAction =
        'URGENT CLINICAL REVIEW: Transfer to PHC/CHC emergency facility. Maintain comfortable upright sitting posture.';
    } else if (hasBleeding) {
      risk = 'High';
      severityRank = 2;
      rulesMatched.push('Elderly: Bleeding detected -> Acute Hemorrhagic Concern');
      rationale.push('Active blood loss in elderly patients requires prompt hospital evaluation.');
      recommendedAction = 'URGENT ESCALATION: Refer to PHC for stabilization and hemorrhage evaluation.';
    } else if (feverDays !== null && feverDays >= 3) {
      risk = 'Medium';
      severityRank = 1;
      rulesMatched.push(`Elderly: Fever >= 3 days (${feverDays} days) -> Persistent Geriatric Infection`);
      rationale.push(
        'Elderly patients deteriorate rapidly with untreated bacterial infections or pneumonia.'
      );
      recommendedAction =
        'CLINICAL REVIEW: Medical officer assessment and laboratory blood screening at PHC within 24-48 hours.';
    }
  }

  // 4. ADULT & GENERAL
  else {
    if (hasBreathingIssue) {
      risk = 'High';
      severityRank = 2;
      rulesMatched.push('Adult: Breathing issue detected -> Acute Respiratory / Cardiac Compromise');
      rationale.push(
        'Severe shortness of breath or respiratory distress in adults warrants emergency clinical triage.'
      );
      recommendedAction =
        'URGENT CLINICAL REVIEW: Refer to nearest PHC/CHC for oxygenation and vital evaluation.';
    } else if (hasBleeding) {
      risk = 'High';
      severityRank = 2;
      rulesMatched.push('Adult: Bleeding detected -> Acute Hemorrhage');
      rationale.push('Uncontrolled or unexplained bleeding requires clinical assessment.');
      recommendedAction = 'URGENT ESCALATION: Urgent referral to medical officer.';
    } else if (feverDays !== null && feverDays >= 5) {
      risk = 'Medium';
      severityRank = 1;
      rulesMatched.push(`Adult: Fever >= 5 days (${feverDays} days) -> Prolonged Adult Pyrexia`);
      rationale.push(
        'Persistent fever beyond 5 days exceeds normal self-limiting viral trajectory; rule out dengue, typhoid, or malaria.'
      );
      recommendedAction =
        'CLINICAL WORKUP: Refer to PHC for diagnostic screening (malaria, typhoid, complete blood count).';
    }
  }

  return {
    risk,
    severityRank,
    category,
    rulesMatched,
    rationale,
    recommendedAction,
    isDeterministic: true,
    factors,
  };
}

/**
 * Standard AASHA risk calculation interface (100% backward & forward compatible).
 *
 * @param structured - Object containing symptoms, feverDays, highBP, swelling, bleeding, breathingIssue
 * @param patientTypeRaw - Patient category ('pregnant', 'child', 'elder', 'general', 'ANC', 'PNC', etc.)
 * @returns RiskLevel - 'Critical' | 'High' | 'Medium' | 'Low'
 */
export function calculateRisk(
  structured: StructuredClinicalData = {},
  patientTypeRaw: string = 'general'
): RiskLevel {
  return assessClinicalRisk(structured, patientTypeRaw).risk;
}

/**
 * Styling helper for Tailwind CSS badge and container colors based on RiskLevel.
 */
export function getRiskColorClasses(risk: RiskLevel): {
  badgeBg: string;
  badgeText: string;
  badgeBorder: string;
  cardBorder: string;
  bgLight: string;
  dotColor: string;
} {
  switch (risk) {
    case 'Critical':
      return {
        badgeBg: 'bg-red-600',
        badgeText: 'text-white',
        badgeBorder: 'border-red-700',
        cardBorder: 'border-red-500 ring-2 ring-red-500/30',
        bgLight: 'bg-red-50',
        dotColor: 'bg-red-600 animate-ping',
      };
    case 'High':
      return {
        badgeBg: 'bg-orange-500',
        badgeText: 'text-white',
        badgeBorder: 'border-orange-600',
        cardBorder: 'border-orange-400',
        bgLight: 'bg-orange-50',
        dotColor: 'bg-orange-500',
      };
    case 'Medium':
      return {
        badgeBg: 'bg-amber-500',
        badgeText: 'text-white',
        badgeBorder: 'border-amber-600',
        cardBorder: 'border-amber-400',
        bgLight: 'bg-amber-50',
        dotColor: 'bg-amber-500',
      };
    case 'Low':
    default:
      return {
        badgeBg: 'bg-emerald-600',
        badgeText: 'text-white',
        badgeBorder: 'border-emerald-700',
        cardBorder: 'border-emerald-300',
        bgLight: 'bg-emerald-50',
        dotColor: 'bg-emerald-500',
      };
  }
}

export default calculateRisk;
