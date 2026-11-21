import { DangerAlert, LanguageCode, VisitDraft } from '@/types';

export type ClientEventType =
  | 'session_start'
  | 'audio_chunk'
  | 'barge_in'
  | 'voice_correction'
  | 'confirm_visit'
  | 'session_end';

export type ServerEventType =
  | 'session_ready'
  | 'stt_partial'
  | 'stt_final'
  | 'assistant_text'
  | 'tts_audio_chunk'
  | 'tts_complete'
  | 'interrupted'
  | 'visit_extracted'
  | 'danger_alert'
  | 'error';

export interface ClientSessionStartMessage {
  type: 'session_start';
  session_id: string;
  asha_worker_id: string;
  beneficiary_id?: string;
  language: LanguageCode;
  audio_format?: string;
}

export interface ClientBargeInMessage {
  type: 'barge_in';
  session_id: string;
  interrupted_at_ms: number;
  reason?: string;
}

export interface ClientVoiceCorrectionMessage {
  type: 'voice_correction';
  session_id: string;
  field_name: string;
  target_value?: string;
}

export interface ClientConfirmVisitMessage {
  type: 'confirm_visit';
  session_id: string;
  draft_id: string;
}

export type ClientWebSocketMessage =
  | ClientSessionStartMessage
  | ClientBargeInMessage
  | ClientVoiceCorrectionMessage
  | ClientConfirmVisitMessage
  | { type: 'session_end'; session_id: string };

export interface ServerSTTPartialMessage {
  type: 'stt_partial';
  session_id: string;
  text: string;
  is_final: false;
}

export interface ServerSTTFinalMessage {
  type: 'stt_final';
  session_id: string;
  text: string;
  is_final: true;
  language?: string;
}

export interface ServerAssistantTextMessage {
  type: 'assistant_text';
  session_id: string;
  text: string;
  state: 'speaking' | 'clarifying' | 'reading_back' | 'danger_warning';
}

export interface ServerTTSAudioChunkMessage {
  type: 'tts_audio_chunk';
  session_id: string;
  chunk_index: number;
  audio_base64: string;
  codec?: 'wav' | 'mp3' | 'pcm';
}

export interface ServerInterruptedMessage {
  type: 'interrupted';
  session_id: string;
  active_stream_cancelled?: boolean;
}

export interface ServerVisitExtractedMessage {
  type: 'visit_extracted';
  session_id: string;
  draft: Partial<VisitDraft>;
}

export interface ServerDangerAlertMessage {
  type: 'danger_alert';
  session_id: string;
  alert: DangerAlert;
}

export interface ServerErrorMessage {
  type: 'error';
  session_id?: string;
  code: string;
  message: string;
  retryable: boolean;
}

export type ServerWebSocketMessage =
  | { type: 'session_ready'; session_id: string }
  | ServerSTTPartialMessage
  | ServerSTTFinalMessage
  | ServerAssistantTextMessage
  | ServerTTSAudioChunkMessage
  | { type: 'tts_complete'; session_id: string }
  | ServerInterruptedMessage
  | ServerVisitExtractedMessage
  | ServerDangerAlertMessage
  | ServerErrorMessage;
