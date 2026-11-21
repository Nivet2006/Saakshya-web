export type LanguageCode = 'hi-IN' | 'kn-IN' | 'ta-IN' | 'en-IN';

export type UserRole = 'ASHA_WORKER' | 'PHC_SUPERVISOR' | 'ADMIN';

export interface UserProfile {
  id: string;
  auth_user_id?: string;
  role: UserRole;
  full_name: string;
  phone_number?: string;
  phc_id: string;
  phc_name?: string;
  assigned_area?: string;
  preferred_language: LanguageCode;
  is_active: boolean;
}

export interface Facility {
  id: string;
  code: string;
  name: string;
  facility_type: 'PHC' | 'CHC' | 'SUB_CENTRE' | 'DISTRICT_HOSPITAL' | 'FRU';
  district: string;
  state: string;
  pincode?: string;
  contact_phone?: string;
  emergency_transport_phone: string;
}

export type BeneficiaryCategory = 
  | 'PREGNANT_WOMAN'
  | 'INFANT'
  | 'CHILD'
  | 'LACTATING_MOTHER'
  | 'GENERAL_ADULT';

export interface Beneficiary {
  id: string;
  beneficiary_id: string; // e.g. BEN-1042
  full_name: string;
  age_years: number;
  gender: 'FEMALE' | 'MALE' | 'OTHER';
  category: BeneficiaryCategory;
  village: string;
  household_head?: string;
  phone_number?: string;
  rch_id?: string;
  lmp_date?: string;
  edd_date?: string;
  high_risk_status: boolean;
  high_risk_reasons: string[];
  assigned_asha_id?: string;
  phc_id: string;
  created_at: string;
  updated_at: string;
}

export interface Vitals {
  weight_kg?: number | null;
  blood_pressure_sys?: number | null;
  blood_pressure_dia?: number | null;
  temperature_f?: number | null;
  hemoglobin_g_dl?: number | null;
  fetal_heart_rate_bpm?: number | null;
}

export type VisitType =
  | 'ANC_1' | 'ANC_2' | 'ANC_3' | 'ANC_4'
  | 'PNC_DAY_1' | 'PNC_DAY_3' | 'PNC_DAY_7' | 'PNC_DAY_14' | 'PNC_DAY_28'
  | 'IMMUNISATION' | 'CHILD_GROWTH' | 'GENERAL_CHECKUP';

export type DangerSeverity = 'CRITICAL' | 'HIGH' | 'MODERATE';

export type DangerCategory =
  | 'severe_pre_eclampsia_eclampsia'
  | 'antepartum_hemorrhage'
  | 'postpartum_hemorrhage'
  | 'neonatal_hypothermia_sepsis'
  | 'severe_acute_malnutrition'
  | 'respiratory_distress'
  | 'severe_anemia'
  | 'prolonged_obstructed_labor'
  | 'other_medical_emergency';

export interface DangerAlert {
  id?: string;
  alert_id: string;
  session_id?: string;
  visit_id?: string;
  beneficiary_id: string;
  beneficiary_name?: string;
  asha_worker_id?: string;
  asha_worker_name?: string;
  phc_id: string;
  severity: DangerSeverity;
  category: DangerCategory | string;
  symptom_evidence: string;
  referral_instruction: string;
  referral_facility_type: 'PHC' | 'CHC' | 'DH' | 'FRU';
  referral_status: 'PENDING_TRANSPORT' | 'EN_ROUTE' | 'ARRIVED_AT_FACILITY' | 'RESOLVED' | 'FOLLOW_UP_SCHEDULED';
  supervisor_acknowledged: boolean;
  acknowledged_by?: string;
  acknowledged_at?: string;
  detected_at: string;
}

export type SyncStatus = 'draft' | 'pending' | 'syncing' | 'synced' | 'failed' | 'conflict';

export interface VisitDraft {
  draft_id: string;
  idempotency_key: string;
  beneficiary_id: string;
  beneficiary_name: string;
  asha_worker_id: string;
  phc_id: string;
  visit_type: VisitType;
  visit_date: string;
  language: LanguageCode;
  vitals: Vitals;
  immunisations_administered: string[];
  immunisations_due: string[];
  ifa_tablets_given?: number | null;
  danger_signs_present: boolean;
  danger_signs: DangerAlert[];
  missing_fields: string[];
  follow_up_required: boolean;
  follow_up_date?: string | null;
  follow_up_reason?: string | null;
  notes?: string | null;
  raw_transcript_summary?: string;
  read_back_confirmed: boolean;
  sync_status: SyncStatus;
  last_sync_error?: string;
  created_at: string;
  updated_at: string;
}

export interface FollowUpTask {
  id: string;
  beneficiary_id: string;
  beneficiary_name?: string;
  asha_worker_id: string;
  phc_id: string;
  due_date: string;
  task_type: string;
  priority: 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';
  status: 'PENDING' | 'COMPLETED' | 'OVERDUE' | 'CANCELLED';
  completed_at?: string;
  notes?: string;
  created_at: string;
}

export interface ImmunisationScheduleItem {
  id: string;
  beneficiary_id: string;
  beneficiary_name?: string;
  vaccine_name: string;
  dose_number: number;
  due_date: string;
  administered_date?: string;
  administered_by?: string;
  batch_number?: string;
  status: 'DUE' | 'OVERDUE' | 'GIVEN' | 'MISSED';
}

export type VoiceSessionStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'listening'
  | 'processing'
  | 'speaking'
  | 'interrupted'
  | 'permission_denied'
  | 'disconnected'
  | 'error';
