/**
 * Authoritative v1 API and WebSocket Contracts matching:
 * - shared-contracts/visit.schema.json
 * - shared-contracts/danger-alert.schema.json
 * - shared-contracts/voice-events.schema.json
 * - shared-contracts/openapi.json
 */

export type ContractSchemaVersion = 'v1';

export type ContractVisitType = 'ANC' | 'PNC' | 'Newborn' | 'Immunisation';
export type VisitLifecycleStatus = 'draft' | 'confirmed' | 'committed';
export type FollowUpActionType =
  | 'phc_referral'
  | 'vaccination_followup'
  | 'home_visit'
  | 'anc_checkup'
  | 'pnc_checkup'
  | 'hbnc_visit'
  | 'nutrition_counsel'
  | 'other';

export type FollowUpPriorityV1 = 'urgent' | 'high' | 'normal';

export interface FollowUpActionV1 {
  action_type: FollowUpActionType;
  description: string;
  due_date: string | null; // YYYY-MM-DD in Asia/Kolkata
  priority: FollowUpPriorityV1;
  source_phrase: string | null;
}

export interface VisitRecordV1 {
  schema_version: 'v1';
  visit_id: string;
  session_id: string;
  worker_id: string;
  beneficiary_id: string | null;
  beneficiary_name: string | null;
  visit_type: ContractVisitType | null;
  weight_kg: number | null;
  weight_source_text: string | null;
  vaccinations_completed: string[];
  vaccinations_due: string[];
  next_visit_date: string | null;
  next_visit_date_source_text: string | null;
  danger_signs: string[];
  danger_sign_flagged: boolean;
  follow_up_actions: FollowUpActionV1[];
  status: VisitLifecycleStatus;
  confirmed_at: string | null;
  committed_at: string | null;
  persistence_record_id: string | null;
  language: string;
  timezone: 'Asia/Kolkata';
  synthetic: boolean;
}

export type DangerSubjectV1 = 'mother' | 'newborn' | 'infant';
export type DangerCategoryV1 = 'ANC' | 'Intranatal' | 'PNC' | 'Newborn';
export type DangerMatchTypeV1 =
  | 'exact_phrase'
  | 'normalized_variant'
  | 'code_mixed_pattern'
  | 'numeric_threshold'
  | 'fuzzy_assisted';

export type DangerAlertStatusV1 = 'active' | 'acknowledged' | 'referred' | 'resolved';

export interface DangerAlertV1 {
  schema_version: 'v1';
  alert_id: string;
  session_id: string;
  visit_id: string;
  beneficiary_id: string | null;
  canonical_danger_sign_id: string;
  canonical_name: string;
  subject: DangerSubjectV1;
  category: DangerCategoryV1;
  supporting_evidence: string;
  match_type: DangerMatchTypeV1;
  source_guideline_ref: string;
  detected_at: string;
  status: DangerAlertStatusV1;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  escalation_language: string;
  referral_message: string;
  danger_sign_flagged: true;
  priority: 'urgent';
}

export interface AudioFormatV1 {
  encoding: 'pcm_s16le';
  sample_rate: 16000;
  channels: 1;
  frame_ms: 32;
  frame_samples?: 512;
  frame_bytes?: 1024;
}

export type BackendSessionStateV1 =
  | 'idle'
  | 'listening'
  | 'processing'
  | 'speaking'
  | 'danger_escalation'
  | 'read_back'
  | 'awaiting_confirmation'
  | 'committing'
  | 'committed'
  | 'closed';

export type ClarificationReasonV1 =
  | 'ambiguous_beneficiary'
  | 'missing_required'
  | 'ambiguous_value'
  | 'uncertain_danger_sign'
  | 'conflict';

export interface ClarificationCandidateV1 {
  id: string;
  label: string;
  detail?: string | null;
}

export type ErrorCodeV1 =
  | 'MISSING_CREDENTIALS'
  | 'INVALID_JSON'
  | 'STT_STREAM_ERROR'
  | 'STT_LOOP_ERROR'
  | 'STT_PROVIDER_ERROR'
  | 'TTS_STREAM_ERROR'
  | 'TURN_PROCESSING_ERROR'
  | 'SESSION_INTERNAL_ERROR'
  | 'BENEFICIARY_NOT_FOUND'
  | 'PERSISTENCE_FAILED'
  | 'INVALID_STATE_TRANSITION'
  | 'AUDIO_FORMAT_ERROR';

// ---------- REST API DTOs (openapi.json v1) ----------

export interface HealthResponseV1 {
  status: 'ok' | 'degraded';
  service: string;
  schema_version: 'v1';
  stt_model: string;
  tts_model: string;
  llm_provider: string;
  llm_model: string;
  live_credentials_configured: boolean;
  missing_env_vars: string[];
  synthetic_data_only: boolean;
}

export interface CreateSessionRequestV1 {
  language?: string;
  beneficiary_id?: string | null;
  worker_id?: string;
}

export interface CreateSessionResponseV1 {
  schema_version: 'v1';
  session_id: string;
  websocket_path: string;
  language: string;
  beneficiary_id: string | null;
  created_at: string;
  audio_format: AudioFormatV1;
}

export interface BackendBeneficiarySummaryV1 {
  beneficiary_id: string;
  full_name: string;
  category: 'pregnant_woman' | 'postnatal_mother' | 'newborn' | 'infant';
  village: string;
  preferred_language: string;
}

export interface BeneficiaryListResponseV1 {
  schema_version: 'v1';
  synthetic_data_only: boolean;
  beneficiaries: BackendBeneficiarySummaryV1[];
}

export interface SessionVisitResponseV1 {
  schema_version: 'v1';
  session_id: string;
  conversation_state?: BackendSessionStateV1;
  visit: VisitRecordV1;
  danger_alerts: DangerAlertV1[];
}

export interface PersistenceAckRequestV1 {
  schema_version: 'v1';
  visit_id: string;
  correlation_id: string;
  accepted: boolean;
  persistence_record_id?: string | null;
  committed_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
}

export interface PersistenceAckResponseV1 {
  schema_version: 'v1';
  session_id: string;
  visit_id: string;
  status: 'confirmed' | 'committed';
  persistence_record_id: string | null;
  committed_at: string | null;
}

export interface DangerSignCheckRequestV1 {
  schema_version: 'v1';
  text: string;
  language?: string;
  visit_type?: ContractVisitType | null;
  beneficiary_id?: string | null;
  subject_hint?: DangerSubjectV1 | null;
}

export interface SuppressedDangerMatchV1 {
  canonical_danger_sign_id: string;
  reason: 'negated' | 'historical' | 'other_person';
  phrase: string;
}

export interface DangerSignCheckResponseV1 {
  schema_version: 'v1';
  danger_sign_flagged: boolean;
  requires_clarification: boolean;
  clarification_prompt: string | null;
  alerts: DangerAlertV1[];
  suppressed_matches: SuppressedDangerMatchV1[];
}

export interface ApiErrorResponseV1 {
  schema_version: 'v1';
  code: ErrorCodeV1;
  message: string;
  retryable: boolean;
  detail?: string | null;
}

// ---------- WebSocket Client -> Server Events (voice-events.schema.json) ----------

export interface ClientAudioChunkEventV1 {
  schema_version?: 'v1';
  type: 'audio_chunk';
  audio_base64: string;
  seq?: number;
  encoding?: 'pcm_s16le';
  sample_rate?: 16000;
  channels?: 1;
}

export interface ClientBargeInEventV1 {
  schema_version?: 'v1';
  type: 'barge_in';
  reason?: string;
  client_timestamp?: string;
}

export interface ClientTextInputEventV1 {
  schema_version?: 'v1';
  type: 'text_input';
  text: string;
  language?: string;
}

export interface ClientSetLanguageEventV1 {
  schema_version?: 'v1';
  type: 'set_language';
  language: string;
}

export interface ClientConfirmVisitEventV1 {
  schema_version?: 'v1';
  type: 'confirm_visit';
  visit_id: string;
  confirmed: boolean;
  worker_id?: string;
  confirmation_method?: 'voice' | 'ui_button';
}

export interface ClientPersistenceAckEventV1 {
  schema_version?: 'v1';
  type: 'persistence_ack';
  visit_id: string;
  correlation_id: string;
  accepted: boolean;
  persistence_record_id?: string | null;
  committed_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
}

export interface ClientPingEventV1 {
  schema_version?: 'v1';
  type: 'ping';
  client_timestamp?: string;
}

export interface ClientEndSessionEventV1 {
  schema_version?: 'v1';
  type: 'end_session';
  reason?: string;
}

export interface ClientPatchFieldsEventV1 {
  schema_version?: 'v1';
  type: 'patch_fields';
  fields: Record<string, unknown>;
}

export interface ClientFinishNotesEventV1 {
  schema_version?: 'v1';
  type: 'finish_notes';
}

export type ClientWebSocketEventV1 =
  | ClientAudioChunkEventV1
  | ClientBargeInEventV1
  | ClientTextInputEventV1
  | ClientSetLanguageEventV1
  | ClientConfirmVisitEventV1
  | ClientPersistenceAckEventV1
  | ClientPingEventV1
  | ClientEndSessionEventV1
  | ClientPatchFieldsEventV1
  | ClientFinishNotesEventV1;

// ---------- WebSocket Server -> Client Events (voice-events.schema.json) ----------

export interface ServerSessionReadyEventV1 {
  schema_version: 'v1';
  type: 'session_ready';
  session_id: string;
  timestamp: string;
  language: string;
  audio_format: AudioFormatV1;
  visit_id?: string;
  supported_languages?: string[];
  stt_provider?: string;
  tts_provider?: string;
  llm_provider?: string;
  llm_model?: string;
}

export interface ServerSessionStateEventV1 {
  schema_version: 'v1';
  type: 'session_state';
  session_id: string;
  timestamp: string;
  state: BackendSessionStateV1;
  turn_id: number;
}

export interface ServerSpeechStartEventV1 {
  schema_version: 'v1';
  type: 'speech_start';
  session_id: string;
  timestamp: string;
  utterance_id: string | null;
}

export interface ServerSpeechEndEventV1 {
  schema_version: 'v1';
  type: 'speech_end';
  session_id: string;
  timestamp: string;
  utterance_id: string | null;
}

export interface ServerPartialTranscriptEventV1 {
  schema_version: 'v1';
  type: 'partial_transcript';
  session_id: string;
  timestamp: string;
  text: string;
  stable_text: string;
  volatile_text: string;
  language: string;
  utterance_id?: string | null;
  seq?: number | null;
  is_final: false;
}

export interface ServerFinalTranscriptEventV1 {
  schema_version: 'v1';
  type: 'final_transcript';
  session_id: string;
  timestamp: string;
  text: string;
  language: string;
  utterance_id?: string | null;
  segment_id?: string | null;
  latency_ms?: number | null;
  is_final: true;
}

export interface ServerAssistantResponseEventV1 {
  schema_version: 'v1';
  type: 'assistant_response';
  session_id: string;
  timestamp: string;
  turn_id: number;
  text: string;
  language: string;
  is_danger_escalation: boolean;
}

export interface ServerTtsStartEventV1 {
  schema_version: 'v1';
  type: 'tts_start';
  session_id: string;
  timestamp: string;
  turn_id: number;
  sample_rate: 16000;
  encoding: 'pcm_s16le';
  channels: 1;
}

export interface ServerTtsAudioChunkEventV1 {
  schema_version: 'v1';
  type: 'tts_audio_chunk';
  session_id: string;
  timestamp: string;
  turn_id: number;
  seq: number;
  audio_base64: string;
  sample_rate: 16000;
}

export interface ServerTtsCompleteEventV1 {
  schema_version: 'v1';
  type: 'tts_complete';
  session_id: string;
  timestamp: string;
  turn_id: number;
  total_chunks: number;
  total_bytes: number;
}

export interface ServerBargeInEventV1 {
  schema_version: 'v1';
  type: 'barge_in';
  session_id: string;
  timestamp: string;
  cancelled_turn_id: number;
  new_turn_id: number;
  trigger: 'vad' | 'client' | 'danger_sign' | 'supersede';
}

export interface ServerTtsCancelledEventV1 {
  schema_version: 'v1';
  type: 'tts_cancelled';
  session_id: string;
  timestamp: string;
  cancelled_turn_id: number;
  reason: string;
}

export interface ServerVisitDraftUpdatedEventV1 {
  schema_version: 'v1';
  type: 'visit_draft_updated';
  session_id: string;
  timestamp: string;
  visit_id: string;
  updated_fields: string[];
  missing_required_fields: string[];
  draft: VisitRecordV1;
}

export interface ServerClarificationRequiredEventV1 {
  schema_version: 'v1';
  type: 'clarification_required';
  session_id: string;
  timestamp: string;
  visit_id: string;
  field: string;
  reason: ClarificationReasonV1;
  prompt_text: string;
  language: string;
  candidates?: ClarificationCandidateV1[];
}

export interface ServerReadBackStartedEventV1 {
  schema_version: 'v1';
  type: 'read_back_started';
  session_id: string;
  timestamp: string;
  visit_id: string;
  turn_id: number;
  summary_text: string;
  language: string;
  draft: VisitRecordV1;
}

export interface ServerCorrectionAppliedEventV1 {
  schema_version: 'v1';
  type: 'correction_applied';
  session_id: string;
  timestamp: string;
  visit_id: string;
  corrected_fields: string[];
  previous_values: Record<string, unknown>;
  new_values: Record<string, unknown>;
  preserved_fields: string[];
  requires_re_read_back: true;
  draft: VisitRecordV1;
}

export interface ServerVisitConfirmedEventV1 {
  schema_version: 'v1';
  type: 'visit_confirmed';
  session_id: string;
  timestamp: string;
  visit_id: string;
  confirmed_at: string;
  confirmation_utterance?: string | null;
  visit: VisitRecordV1;
}

export interface ServerPersistenceRequestedEventV1 {
  schema_version: 'v1';
  type: 'persistence_requested';
  session_id: string;
  timestamp: string;
  correlation_id: string;
  visit_id: string;
  visit: VisitRecordV1;
  danger_alerts: DangerAlertV1[];
}

export interface ServerVisitCommittedEventV1 {
  schema_version: 'v1';
  type: 'visit_committed';
  session_id: string;
  timestamp: string;
  visit_id: string;
  persistence_record_id: string;
  committed_at: string;
  correlation_id?: string | null;
  visit: VisitRecordV1;
}

export interface ServerPersistenceRejectedEventV1 {
  schema_version: 'v1';
  type: 'persistence_rejected';
  session_id: string;
  timestamp: string;
  visit_id: string;
  correlation_id?: string | null;
  code: ErrorCodeV1;
  reason: string;
  retryable: boolean;
}

export interface ServerDangerAlertEventV1 {
  schema_version: 'v1';
  type: 'danger_alert';
  session_id: string;
  timestamp: string;
  priority: 'urgent';
  danger_sign_flagged: true;
  interrupts_speech: boolean;
  alert: DangerAlertV1;
}

export interface ServerErrorEventV1 {
  schema_version: 'v1';
  type: 'error';
  session_id: string;
  timestamp?: string;
  code: ErrorCodeV1;
  message: string;
  retryable: boolean;
  turn_id?: number | null;
}

export interface ServerPongEventV1 {
  schema_version: 'v1';
  type: 'pong';
  session_id: string;
  timestamp: string;
  client_timestamp?: string | null;
}

export type ServerWebSocketEventV1 =
  | ServerSessionReadyEventV1
  | ServerSessionStateEventV1
  | ServerSpeechStartEventV1
  | ServerSpeechEndEventV1
  | ServerPartialTranscriptEventV1
  | ServerFinalTranscriptEventV1
  | ServerAssistantResponseEventV1
  | ServerTtsStartEventV1
  | ServerTtsAudioChunkEventV1
  | ServerTtsCompleteEventV1
  | ServerBargeInEventV1
  | ServerTtsCancelledEventV1
  | ServerVisitDraftUpdatedEventV1
  | ServerClarificationRequiredEventV1
  | ServerReadBackStartedEventV1
  | ServerCorrectionAppliedEventV1
  | ServerVisitConfirmedEventV1
  | ServerPersistenceRequestedEventV1
  | ServerVisitCommittedEventV1
  | ServerPersistenceRejectedEventV1
  | ServerDangerAlertEventV1
  | ServerErrorEventV1
  | ServerPongEventV1;

