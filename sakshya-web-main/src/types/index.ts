import type {
  ContractVisitType,
  DangerAlertV1,
  DynamicEventV1,
  DynamicObservationV1,
  FollowUpActionV1,
  VisitRecordV1,
} from '@/lib/contracts/v1';

export type PrismaLanguageCode =
  | 'indic-auto'
  | 'hi-IN'
  | 'kn-IN'
  | 'ta-IN'
  | 'te-IN'
  | 'ml-IN'
  | 'bn-IN'
  | 'mr-IN'
  | 'gu-IN'
  | 'pa-IN'
  | 'en-IN';

export type LanguageCode = PrismaLanguageCode | string;

export type AshaExperienceMode = 'basic' | 'advanced';

export type UserRole = 'ASHA_WORKER' | 'PHC_SUPERVISOR' | 'ADMIN';

export interface UserProfile {
  id: string;
  worker_code: string; // Matches Agent 1 worker_id (e.g. ASHA-DEMO-01)
  auth_user_id?: string;
  role: UserRole;
  full_name: string;
  phone_number?: string;
  phc_id: string;
  phc_name?: string;
  assigned_area?: string;
  preferred_language: LanguageCode;
  is_active: boolean;
  last_active_at?: string;
  is_online?: boolean;
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
  id: string; // UUID in Supabase
  beneficiary_id: string; // BEN-1042 (matches Agent 1 backend)
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
  preferred_language?: LanguageCode;
  created_at: string;
  updated_at: string;
}

export type FieldConfirmStatus =
  | 'extracted'
  | 'needs_clarification'
  | 'corrected'
  | 'confirmed'
  | 'missing';

export interface CorrectionHistoryEntry {
  timestamp: string;
  corrected_fields: string[];
  previous_values: Record<string, unknown>;
  new_values: Record<string, unknown>;
  preserved_fields: string[];
}

export type SyncStatus = 'draft' | 'pending' | 'syncing' | 'synced' | 'failed' | 'conflict';

export interface DangerAlert {
  id?: string;
  alert_id: string;
  session_id?: string;
  visit_id?: string;
  beneficiary_id: string | null;
  beneficiary_name?: string;
  asha_worker_id?: string;
  asha_worker_name?: string;
  phc_id: string;
  canonical_danger_sign_id: string;
  canonical_name: string;
  subject: 'mother' | 'newborn' | 'infant';
  category: string;
  supporting_evidence: string;
  match_type?: string;
  source_guideline_ref: string;
  referral_message: string;
  escalation_language: string;
  status: 'active' | 'acknowledged' | 'referred' | 'resolved';
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  detected_at: string;
  priority: 'urgent';
  danger_sign_flagged: true;
  referral_facility_type?: 'PHC' | 'CHC' | 'DH' | 'FRU' | 'SNCU';
  referral_notes?: string;
}

export interface VisitDraft {
  draft_id: string;
  visit_id: string; // Canonical Agent 1 visit_id (idempotency key)
  session_id: string;
  idempotency_key: string;
  beneficiary_uuid?: string;
  beneficiary_id: string | null;
  beneficiary_name: string | null;
  asha_worker_id: string;
  worker_name?: string;
  phc_id: string;
  visit_type: ContractVisitType | null;
  visit_date: string;
  language: LanguageCode;
  weight_kg: number | null;
  weight_source_text: string | null;
  vaccinations_completed: string[];
  vaccinations_due: string[];
  next_visit_date: string | null;
  next_visit_date_source_text: string | null;
  danger_signs: string[];
  danger_sign_flagged: boolean;
  danger_alerts: DangerAlert[];
  follow_up_actions: FollowUpActionV1[];
  observations?: DynamicObservationV1[];
  events?: DynamicEventV1[];
  missing_required_fields: string[];
  updated_fields?: string[];
  field_statuses?: Record<string, FieldConfirmStatus>;
  raw_transcript_summary?: string;
  read_back_summary?: string;
  status: 'draft' | 'confirmed' | 'committed';
  confirmed_at: string | null;
  committed_at: string | null;
  persistence_record_id: string | null;
  sync_status: SyncStatus;
  last_sync_error?: string;
  created_at: string;
  updated_at: string;
  synthetic: boolean;
  // Raw v1 contract snapshot when received from Agent 1
  v1_record?: VisitRecordV1;
}

export interface FollowUpTask {
  id: string;
  beneficiary_uuid?: string;
  beneficiary_id: string;
  beneficiary_name?: string;
  asha_worker_id: string;
  phc_id: string;
  due_date: string;
  task_type: string;
  action_type?: string;
  priority: 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';
  status: 'PENDING' | 'COMPLETED' | 'OVERDUE' | 'CANCELLED';
  completed_at?: string;
  notes?: string;
  created_at: string;
}

export interface ImmunisationScheduleItem {
  id: string;
  beneficiary_uuid?: string;
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

export interface AuditLogEntry {
  id: string;
  actor_name: string;
  actor_role: UserRole;
  action_type: string;
  entity_type: string;
  entity_id: string;
  summary: string;
  created_at: string;
}

/**
 * 11 explicit UI voice interaction states mapped deterministically
 * from Agent 1 WebSocket events + browser mic hardware status.
 */
export type VoiceInteractionState =
  | 'idle'
  | 'connecting'
  | 'listening'
  | 'processing'
  | 'transcribing'
  | 'responding'
  | 'speaking'
  | 'interrupted'
  | 'reconnecting'
  | 'error'
  | 'completed';

export interface TranscriptLine {
  id: string;
  role: 'asha' | 'assistant' | 'system' | 'danger';
  text: string;
  language?: string;
  timestamp: string;
  is_final?: boolean;
  is_danger_escalation?: boolean;
  latency_ms?: number | null;
}

export function alertV1ToUi(
  a: DangerAlertV1,
  extras?: { beneficiary_name?: string; asha_worker_id?: string; asha_worker_name?: string; phc_id?: string }
): DangerAlert {
  return {
    alert_id: a.alert_id,
    session_id: a.session_id,
    visit_id: a.visit_id,
    beneficiary_id: a.beneficiary_id,
    beneficiary_name: extras?.beneficiary_name,
    asha_worker_id: extras?.asha_worker_id,
    asha_worker_name: extras?.asha_worker_name,
    phc_id: extras?.phc_id || 'a0000000-0000-0000-0000-000000000001',
    canonical_danger_sign_id: a.canonical_danger_sign_id,
    canonical_name: a.canonical_name,
    subject: a.subject,
    category: a.category,
    supporting_evidence: a.supporting_evidence,
    match_type: a.match_type,
    source_guideline_ref: a.source_guideline_ref,
    referral_message: a.referral_message,
    escalation_language: a.escalation_language,
    status: a.status,
    acknowledged_by: a.acknowledged_by,
    acknowledged_at: a.acknowledged_at,
    detected_at: a.detected_at,
    priority: a.priority,
    danger_sign_flagged: true,
    referral_facility_type: a.subject === 'newborn' ? 'SNCU' : 'PHC',
  };
}
