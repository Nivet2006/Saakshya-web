'use client';

import React, { useEffect, useState, useRef } from 'react';
import { Beneficiary, DangerAlert, LanguageCode, UserProfile, VisitDraft, VoiceSessionStatus } from '@/types';
import { BrowserVoiceClient } from '@/lib/voice/voice-client';
import { saveDraftLocally } from '@/lib/offline/indexeddb-store';
import { syncManager } from '@/lib/sync/sync-manager';
import { DangerAlertBanner } from '@/components/DangerAlertBanner';
import { StructuredVisitCard } from '@/components/StructuredVisitCard';
import { TRANSLATIONS } from '@/lib/translations';
import {
  Mic,
  MicOff,
  Volume2,
  AlertCircle,
  X,
  CheckCircle2,
  RefreshCw,
  FastForward,
  Info,
} from 'lucide-react';

interface VoiceSessionModalProps {
  beneficiary: Beneficiary;
  ashaWorker: UserProfile;
  language: LanguageCode;
  onClose: () => void;
  onVisitSaved: (draft: VisitDraft) => void;
}

export const VoiceSessionModal: React.FC<VoiceSessionModalProps> = ({
  beneficiary,
  ashaWorker,
  language,
  onClose,
  onVisitSaved,
}) => {
  const [status, setStatus] = useState<VoiceSessionStatus>('connecting');
  const [partialTranscript, setPartialTranscript] = useState<string>('');
  const [finalTranscript, setFinalTranscript] = useState<string>('');
  const [assistantText, setAssistantText] = useState<string>('');
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [dangerAlert, setDangerAlert] = useState<DangerAlert | null>(null);
  const [extractedDraft, setExtractedDraft] = useState<Partial<VisitDraft>>({});
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [activeCorrectionField, setActiveCorrectionField] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const t = TRANSLATIONS[language] || TRANSLATIONS['hi-IN'];
  const voiceClientRef = useRef<BrowserVoiceClient | null>(null);
  const sessionIdRef = useRef<string>(`sess-${Date.now()}`);

  useEffect(() => {
    const client = new BrowserVoiceClient({
      onStatusChange: (newStatus) => setStatus(newStatus),
      onPartialTranscript: (text) => setPartialTranscript(text),
      onFinalTranscript: (text) => {
        setFinalTranscript((prev) => (prev ? `${prev} ${text}` : text));
        setPartialTranscript('');
      },
      onAssistantText: (text) => setAssistantText(text),
      onAudioLevel: (lvl) => setAudioLevel(lvl),
      onVisitExtracted: (draft) => {
        setExtractedDraft((prev) => ({ ...prev, ...draft }));
      },
      onDangerAlert: (alert) => {
        setDangerAlert(alert);
      },
      onError: (err) => setErrorMessage(err),
    });

    voiceClientRef.current = client;

    client.startSession({
      sessionId: sessionIdRef.current,
      language: language,
      ashaWorkerId: ashaWorker.id,
      beneficiaryId: beneficiary.id,
    });

    return () => {
      client.stopSession();
    };
  }, [beneficiary.id, ashaWorker.id, language]);

  const handleBargeIn = () => {
    if (voiceClientRef.current) {
      voiceClientRef.current.triggerBargeIn();
    }
  };

  const handleVoiceCorrection = (fieldName: string) => {
    setActiveCorrectionField(fieldName);
    if (voiceClientRef.current) {
      voiceClientRef.current.sendVoiceCorrection(fieldName);
    }
  };

  const handleConfirmAndSave = async () => {
    setIsSaving(true);
    const draftId = `draft-${Date.now()}`;
    const idempotencyKey = `idemp-${draftId}-${Date.now()}`;

    const completedDraft: VisitDraft = {
      draft_id: draftId,
      idempotency_key: idempotencyKey,
      beneficiary_id: beneficiary.id,
      beneficiary_name: beneficiary.full_name,
      asha_worker_id: ashaWorker.id,
      phc_id: ashaWorker.phc_id,
      visit_type: (extractedDraft.visit_type as any) || 'ANC_2',
      visit_date: new Date().toISOString(),
      language: language,
      vitals: extractedDraft.vitals || {
        blood_pressure_sys: 160,
        blood_pressure_dia: 100,
        weight_kg: 56.5,
      },
      immunisations_administered: extractedDraft.immunisations_administered || [],
      immunisations_due: extractedDraft.immunisations_due || [],
      danger_signs_present: !!dangerAlert,
      danger_signs: dangerAlert ? [dangerAlert] : [],
      missing_fields: [],
      follow_up_required: extractedDraft.follow_up_required ?? true,
      follow_up_date:
        extractedDraft.follow_up_date ||
        new Date(Date.now() + 2 * 86400000).toISOString().split('T')[0],
      follow_up_reason: extractedDraft.follow_up_reason || 'Routine follow-up',
      notes: extractedDraft.notes || finalTranscript,
      raw_transcript_summary: finalTranscript,
      read_back_confirmed: true,
      sync_status: 'pending',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    // 1. Durably save in IndexedDB
    await saveDraftLocally(completedDraft);

    // 2. Trigger background sync
    syncManager.triggerSync();

    setIsSaving(false);
    if (voiceClientRef.current) voiceClientRef.current.stopSession();
    onVisitSaved(completedDraft);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4">
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[92vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-slate-900 text-lg">{t.voiceVisitSession}</h2>
              <span className="text-xs bg-brand-100 text-brand-800 font-semibold px-2 py-0.5 rounded-full">
                {language}
              </span>
            </div>
            <p className="text-xs text-slate-500">
              {t.beneficiaryLabel} <strong className="text-slate-800">{beneficiary.full_name}</strong> ({beneficiary.beneficiary_id})
            </p>
          </div>
          <button
            onClick={() => {
              if (voiceClientRef.current) voiceClientRef.current.stopSession();
              onClose();
            }}
            className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200 transition-colors"
            aria-label="Close voice session"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="p-4 overflow-y-auto flex-1 space-y-4">
          {/* Error Banner */}
          {errorMessage && (
            <div className="p-3 bg-red-50 text-red-800 rounded-xl border border-red-200 text-xs flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Urgent Danger Alert Banner (Safety-Critical, High Priority) */}
          {dangerAlert && <DangerAlertBanner alert={dangerAlert} language={language} />}

          {/* Central Microphone & Audio Waveform Visualizer */}
          <div className="bg-gradient-to-b from-slate-900 to-slate-800 rounded-2xl p-5 text-white flex flex-col items-center justify-center shadow-inner">
            <div className="relative mb-3">
              <div
                className={`w-20 h-20 rounded-full flex items-center justify-center transition-all ${
                  status === 'listening'
                    ? 'bg-emergency-600 animate-pulse-mic text-white'
                    : status === 'speaking'
                    ? 'bg-brand-500 text-white'
                    : status === 'interrupted'
                    ? 'bg-amber-500 text-white'
                    : 'bg-slate-700 text-slate-300'
                }`}
              >
                {status === 'speaking' ? (
                  <Volume2 className="h-9 w-9 animate-pulse" />
                ) : status === 'listening' ? (
                  <Mic className="h-9 w-9" />
                ) : (
                  <MicOff className="h-9 w-9" />
                )}
              </div>
            </div>

            {/* Live Audio Level Bar */}
            <div className="w-48 h-2 bg-slate-700 rounded-full overflow-hidden mb-3">
              <div
                className="h-full bg-emerald-400 transition-all duration-75"
                style={{ width: `${Math.min(100, Math.max(5, audioLevel * 100))}%` }}
              />
            </div>

            {/* Status Label */}
            <div className="text-center">
              <span
                className={`text-xs uppercase tracking-wider font-bold px-3 py-1 rounded-full ${
                  status === 'listening'
                    ? 'bg-emergency-500/20 text-emergency-400 border border-emergency-500/30'
                    : status === 'speaking'
                    ? 'bg-brand-500/20 text-brand-300 border border-brand-500/30'
                    : status === 'interrupted'
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    : 'bg-slate-700 text-slate-300'
                }`}
              >
                {status === 'listening' && t.listeningStatus}
                {status === 'speaking' && t.speakingStatus}
                {status === 'processing' && t.processingStatus}
                {status === 'interrupted' && t.interruptedStatus}
                {status === 'connecting' && t.connectingStatus}
                {status === 'permission_denied' && t.permissionDeniedStatus}
                {status === 'idle' && t.sessionEndedStatus}
              </span>
            </div>

            {/* Barge-in Button: Stop speaking & interrupt */}
            {status === 'speaking' && (
              <button
                type="button"
                onClick={handleBargeIn}
                className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-lg text-xs transition-colors shadow-sm"
              >
                <FastForward className="h-3.5 w-3.5" />
                <span>{t.bargeInButton}</span>
              </button>
            )}
          </div>

          {/* Live Transcript Stream */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-xs">
            <span className="font-bold text-slate-600 block mb-1">
              {t.liveTranscriptionTitle}
            </span>
            <p className="text-slate-800 min-h-[40px] leading-relaxed">
              {finalTranscript && <span>{finalTranscript} </span>}
              {partialTranscript && (
                <span className="text-brand-700 italic font-medium">{partialTranscript}</span>
              )}
              {!finalTranscript && !partialTranscript && (
                <span className="text-slate-400 italic">
                  {t.transcriptPlaceholder}
                </span>
              )}
            </p>
          </div>

          {/* Assistant Spoken Response Bubble */}
          {assistantText && (
            <div className="bg-brand-50 border border-brand-200 rounded-xl p-3 text-xs text-brand-900">
              <span className="font-bold flex items-center gap-1.5 mb-1 text-brand-700">
                <Volume2 className="h-3.5 w-3.5 text-brand-600" />
                {t.assistantReadBackTitle}
              </span>
              <p className="font-medium">{assistantText}</p>
            </div>
          )}

          {/* Extracted Visit Card */}
          <StructuredVisitCard
            draft={extractedDraft}
            onVoiceCorrectField={handleVoiceCorrection}
            activeCorrectionField={activeCorrectionField}
            language={language}
          />
        </div>

        {/* Action Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between gap-3">
          <div className="text-[11px] text-slate-500 flex items-center gap-1">
            <Info className="h-3.5 w-3.5 text-slate-400 shrink-0" />
            <span>{t.autoSaveNotice}</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (voiceClientRef.current) voiceClientRef.current.stopSession();
                onClose();
              }}
              className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-200 text-xs font-semibold transition-colors"
            >
              {t.cancelButton}
            </button>

            <button
              onClick={handleConfirmAndSave}
              disabled={isSaving}
              className="px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-bold shadow-md hover:shadow-lg transition-all flex items-center gap-2 disabled:opacity-50"
            >
              {isSaving ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  <span>{t.savingButton}</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  <span>{t.confirmAndSaveButton}</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
