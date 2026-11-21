'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  ClarificationCandidateV1,
  ServerClarificationRequiredEventV1,
  VisitRecordV1,
} from '@/lib/contracts/v1';
import { saveDraftLocally } from '@/lib/offline/indexeddb-store';
import { syncManager } from '@/lib/sync/sync-manager';
import {
  BrowserVoiceClient,
  listAudioInputDevices,
  type AudioInputDeviceInfo,
} from '@/lib/voice/voice-client';
import { dataService } from '@/services/data-service';
import {
  alertV1ToUi,
  type Beneficiary,
  type CorrectionHistoryEntry,
  type DangerAlert,
  type FieldConfirmStatus,
  type LanguageCode,
  type TranscriptLine,
  type UserProfile,
  type VisitDraft,
  type VoiceInteractionState,
} from '@/types';

export interface VoiceSessionError {
  code: string;
  message: string;
  retryable: boolean;
}

export function mergeVisitV1IntoDraft(
  prev: VisitDraft | null,
  record: VisitRecordV1,
  beneficiary: Beneficiary | null,
  worker: UserProfile,
  options?: {
    missingRequiredFields?: string[];
    updatedFields?: string[];
    correctedFields?: string[];
    readBackSummary?: string;
    transcriptSummary?: string;
    attachedAlerts?: DangerAlert[];
  }
): VisitDraft {
  const now = new Date().toISOString();
  const prevStatuses = prev?.field_statuses || {};
  const nextStatuses: Record<string, FieldConfirmStatus> = { ...prevStatuses };

  const majorFields: Array<[string, unknown]> = [
    ['beneficiary_id', record.beneficiary_id],
    ['visit_type', record.visit_type],
    ['weight_kg', record.weight_kg],
    ['vaccinations_due', record.vaccinations_due.length > 0 || record.vaccinations_completed.length > 0 ? true : null],
    ['next_visit_date', record.next_visit_date],
    ['danger_signs', record.danger_sign_flagged || record.danger_signs.length > 0 ? true : 'clear'],
    ['follow_up_actions', record.follow_up_actions.length > 0 ? true : null],
  ];

  for (const [key, val] of majorFields) {
    if (options?.correctedFields?.includes(key)) {
      nextStatuses[key] = 'corrected';
    } else if (options?.missingRequiredFields?.includes(key)) {
      nextStatuses[key] = 'needs_clarification';
    } else if (val === null || val === undefined || val === '') {
      if (nextStatuses[key] !== 'confirmed') {
        nextStatuses[key] = 'missing';
      }
    } else if (nextStatuses[key] !== 'confirmed' && nextStatuses[key] !== 'corrected') {
      nextStatuses[key] = 'extracted';
    }
  }

  return {
    draft_id: record.visit_id,
    visit_id: record.visit_id,
    session_id: record.session_id,
    idempotency_key: record.visit_id,
    beneficiary_uuid: beneficiary?.id || prev?.beneficiary_uuid,
    beneficiary_id: record.beneficiary_id,
    beneficiary_name: record.beneficiary_name || beneficiary?.full_name || prev?.beneficiary_name || null,
    asha_worker_id: worker.id,
    worker_name: worker.full_name,
    phc_id: worker.phc_id,
    visit_type: record.visit_type,
    visit_date: prev?.visit_date || now,
    language: record.language,
    weight_kg: record.weight_kg,
    weight_source_text: record.weight_source_text,
    vaccinations_completed: [...record.vaccinations_completed],
    vaccinations_due: [...record.vaccinations_due],
    next_visit_date: record.next_visit_date,
    next_visit_date_source_text: record.next_visit_date_source_text,
    danger_signs: [...record.danger_signs],
    danger_sign_flagged: record.danger_sign_flagged,
    danger_alerts: options?.attachedAlerts || prev?.danger_alerts || [],
    follow_up_actions: [...record.follow_up_actions],
    missing_required_fields: options?.missingRequiredFields || prev?.missing_required_fields || [],
    updated_fields: options?.updatedFields,
    field_statuses: nextStatuses,
    raw_transcript_summary: options?.transcriptSummary ?? prev?.raw_transcript_summary,
    read_back_summary: options?.readBackSummary ?? prev?.read_back_summary,
    status: record.status,
    confirmed_at: record.confirmed_at,
    committed_at: record.committed_at,
    persistence_record_id: record.persistence_record_id,
    sync_status:
      record.status === 'committed'
        ? 'synced'
        : record.status === 'confirmed'
        ? 'pending'
        : 'draft',
    created_at: prev?.created_at || now,
    updated_at: now,
    synthetic: record.synthetic,
    v1_record: record,
  };
}

export function useVoiceVisitSession(params: {
  worker: UserProfile;
  language: LanguageCode;
  selectedBeneficiary: Beneficiary | null;
  onDataCommitted: (savedVisit: VisitDraft) => void;
}) {
  const { worker, language, selectedBeneficiary, onDataCommitted } = params;

  const [interactionState, setInteractionState] = useState<VoiceInteractionState>('idle');
  const [isConnected, setIsConnected] = useState(false);
  const [handsFree, setHandsFree] = useState(true);
  const [pttPressed, setPttPressed] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [waveformBands, setWaveformBands] = useState<number[]>(() => new Array(16).fill(0));
  const [sessionId, setSessionId] = useState<string>('');
  const [durationSeconds, setDurationSeconds] = useState(0);

  const [inputDevices, setInputDevices] = useState<AudioInputDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('default');

  const [partialStable, setPartialStable] = useState('');
  const [partialVolatile, setPartialVolatile] = useState('');
  const [transcriptHistory, setTranscriptHistory] = useState<TranscriptLine[]>([]);
  const [assistantText, setAssistantText] = useState('');
  const [isTtsPlaying, setIsTtsPlaying] = useState(false);
  const [isTtsPaused, setIsTtsPaused] = useState(false);

  const [visitDraft, setVisitDraft] = useState<VisitDraft | null>(null);
  const [dangerAlerts, setDangerAlerts] = useState<DangerAlert[]>([]);
  const [clarification, setClarification] = useState<ServerClarificationRequiredEventV1 | null>(
    null
  );
  const [correctionHistory, setCorrectionHistory] = useState<CorrectionHistoryEntry[]>([]);
  const [isCorrectingMode, setIsCorrectingMode] = useState(false);
  const [targetCorrectionField, setTargetCorrectionField] = useState<string | null>(null);
  const [requiresReReadBack, setRequiresReReadBack] = useState(false);
  const [error, setError] = useState<VoiceSessionError | null>(null);
  const [committedResult, setCommittedResult] = useState<VisitDraft | null>(null);
  const [isPersistencePending, setIsPersistencePending] = useState(false);

  const clientRef = useRef<BrowserVoiceClient | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const draftRef = useRef<VisitDraft | null>(null);
  const alertsRef = useRef<DangerAlert[]>([]);
  const finalLinesRef = useRef<string[]>([]);

  useEffect(() => {
    draftRef.current = visitDraft;
  }, [visitDraft]);

  useEffect(() => {
    alertsRef.current = dangerAlerts;
  }, [dangerAlerts]);

  useEffect(() => {
    listAudioInputDevices().then(setInputDevices);
  }, []);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      clientRef.current?.stopSession();
    };
  }, []);

  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const resetSessionState = useCallback(() => {
    stopTimer();
    clientRef.current?.stopSession();
    clientRef.current = null;
    setInteractionState('idle');
    setIsConnected(false);
    setAudioLevel(0);
    setWaveformBands(new Array(16).fill(0));
    setDurationSeconds(0);
    setSessionId('');
    setPartialStable('');
    setPartialVolatile('');
    setTranscriptHistory([]);
    setAssistantText('');
    setIsTtsPlaying(false);
    setIsTtsPaused(false);
    setVisitDraft(null);
    setDangerAlerts([]);
    setClarification(null);
    setCorrectionHistory([]);
    setIsCorrectingMode(false);
    setTargetCorrectionField(null);
    setRequiresReReadBack(false);
    setError(null);
    setCommittedResult(null);
    setIsPersistencePending(false);
    finalLinesRef.current = [];
  }, []);

  const startVoiceSession = useCallback(async () => {
    setError(null);
    setCommittedResult(null);
    setClarification(null);
    finalLinesRef.current = [];
    setTranscriptHistory([]);
    setPartialStable('');
    setPartialVolatile('');
    setDurationSeconds(0);

    const client = new BrowserVoiceClient({
      onStateChange: (nextState) => {
        setInteractionState(nextState);
      },
      onConnectionChange: (connected, reconnecting) => {
        setIsConnected(connected);
        if (reconnecting) setInteractionState('reconnecting');
      },
      onSessionReady: (ev) => {
        setSessionId(ev.session_id);
        listAudioInputDevices().then(setInputDevices);
      },
      onAudioLevel: (lvl, bands) => {
        setAudioLevel(lvl);
        if (bands) setWaveformBands(bands);
      },
      onPartialTranscript: (ev) => {
        const stable = ev.stable_text || ev.text || '';
        const volatile = ev.volatile_text || '';
        setPartialStable(stable);
        setPartialVolatile(volatile);

        const liveText = [finalLinesRef.current.join(' '), stable, volatile]
          .map((s) => s.trim())
          .filter(Boolean)
          .join(' ');
        if (liveText) {
          setVisitDraft((prev) => {
            if (prev) {
              return { ...prev, raw_transcript_summary: liveText };
            }
            const now = new Date().toISOString();
            const draftId = `draft-${Date.now()}`;
            return {
              draft_id: draftId,
              visit_id: draftId,
              session_id: sessionId || draftId,
              idempotency_key: draftId,
              beneficiary_uuid: selectedBeneficiary?.id,
              beneficiary_id: selectedBeneficiary?.beneficiary_id || null,
              beneficiary_name: selectedBeneficiary?.full_name || null,
              asha_worker_id: worker.id,
              worker_name: worker.full_name,
              phc_id: worker.phc_id,
              visit_type: null,
              visit_date: now,
              language: ev.language || language,
              weight_kg: null,
              weight_source_text: null,
              vaccinations_completed: [],
              vaccinations_due: [],
              next_visit_date: null,
              next_visit_date_source_text: null,
              danger_signs: [],
              danger_sign_flagged: false,
              danger_alerts: alertsRef.current,
              follow_up_actions: [],
              missing_required_fields: selectedBeneficiary ? ['visit_type'] : ['beneficiary_id', 'visit_type'],
              field_statuses: {
                beneficiary_id: selectedBeneficiary ? 'extracted' : 'needs_clarification',
                visit_type: 'needs_clarification',
                weight_kg: 'missing',
                vaccinations_due: 'missing',
                next_visit_date: 'missing',
                danger_signs: 'extracted',
                follow_up_actions: 'missing',
              },
              raw_transcript_summary: liveText,
              status: 'draft',
              confirmed_at: null,
              committed_at: null,
              persistence_record_id: null,
              sync_status: 'draft',
              created_at: now,
              updated_at: now,
              synthetic: true,
            };
          });
        }
      },
      onFinalTranscript: (ev) => {
        setPartialStable('');
        setPartialVolatile('');
        finalLinesRef.current.push(ev.text);
        const fullTranscript = finalLinesRef.current.join(' ').trim();
        setTranscriptHistory((prev) => [
          ...prev,
          {
            id: `final-${Date.now()}-${prev.length}`,
            role: 'asha',
            text: ev.text,
            language: ev.language,
            timestamp: ev.timestamp,
            is_final: true,
            latency_ms: ev.latency_ms,
          },
        ]);
        if (fullTranscript) {
          setVisitDraft((prev) =>
            prev ? { ...prev, raw_transcript_summary: fullTranscript } : prev
          );
        }
      },
      onAssistantResponse: (text, _turnId, isDangerEscalation, respLang) => {
        setAssistantText(text);
        setTranscriptHistory((prev) => [
          ...prev,
          {
            id: `asst-${Date.now()}-${prev.length}`,
            role: isDangerEscalation ? 'danger' : 'assistant',
            text,
            language: respLang,
            timestamp: new Date().toISOString(),
            is_danger_escalation: isDangerEscalation,
          },
        ]);
      },
      onTtsPlaybackChange: (playing, paused) => {
        setIsTtsPlaying(playing);
        setIsTtsPaused(paused);
      },
      onBargeIn: () => {
        setIsTtsPlaying(false);
        setIsTtsPaused(false);
      },
      onVisitDraftUpdated: (ev) => {
        setClarification(null);
        const merged = mergeVisitV1IntoDraft(draftRef.current, ev.draft, selectedBeneficiary, worker, {
          missingRequiredFields: ev.missing_required_fields,
          updatedFields: ev.updated_fields,
          transcriptSummary: finalLinesRef.current.join(' '),
          attachedAlerts: alertsRef.current,
        });
        setVisitDraft(merged);
        saveDraftLocally(merged).catch(() => {});
      },
      onClarificationRequired: (ev) => {
        setClarification(ev);
      },
      onReadBackStarted: (ev) => {
        setRequiresReReadBack(false);
        setIsCorrectingMode(false);
        setTargetCorrectionField(null);
        const merged = mergeVisitV1IntoDraft(draftRef.current, ev.draft, selectedBeneficiary, worker, {
          readBackSummary: ev.summary_text,
          transcriptSummary: finalLinesRef.current.join(' '),
          attachedAlerts: alertsRef.current,
        });
        setVisitDraft(merged);
        saveDraftLocally(merged).catch(() => {});
      },
      onCorrectionApplied: (ev) => {
        setRequiresReReadBack(true);
        setIsCorrectingMode(false);
        setTargetCorrectionField(null);
        setCorrectionHistory((prev) => [
          ...prev,
          {
            timestamp: ev.timestamp,
            corrected_fields: ev.corrected_fields,
            previous_values: ev.previous_values,
            new_values: ev.new_values,
            preserved_fields: ev.preserved_fields,
          },
        ]);
        const merged = mergeVisitV1IntoDraft(draftRef.current, ev.draft, selectedBeneficiary, worker, {
          correctedFields: ev.corrected_fields,
          transcriptSummary: finalLinesRef.current.join(' '),
          attachedAlerts: alertsRef.current,
        });
        setVisitDraft(merged);
        saveDraftLocally(merged).catch(() => {});
      },
      onVisitConfirmed: (ev) => {
        const merged = mergeVisitV1IntoDraft(draftRef.current, ev.visit, selectedBeneficiary, worker, {
          transcriptSummary: finalLinesRef.current.join(' '),
          attachedAlerts: alertsRef.current,
        });
        setVisitDraft(merged);
        saveDraftLocally(merged).catch(() => {});
      },
      onPersistenceRequested: async (ev) => {
        setIsPersistencePending(true);
        const uiAlerts = ev.danger_alerts.map((a) =>
          alertV1ToUi(a, {
            beneficiary_name: ev.visit.beneficiary_name || selectedBeneficiary?.full_name,
            asha_worker_id: worker.id,
            asha_worker_name: worker.full_name,
            phc_id: worker.phc_id,
          })
        );
        const toPersist = mergeVisitV1IntoDraft(draftRef.current, ev.visit, selectedBeneficiary, worker, {
          transcriptSummary: finalLinesRef.current.join(' '),
          attachedAlerts: uiAlerts,
        });
        const res = await syncManager.persistConfirmedVisitNow(toPersist, ev.correlation_id);
        clientRef.current?.sendPersistenceAck({
          visitId: ev.visit_id,
          correlationId: ev.correlation_id,
          accepted: res.accepted,
          persistenceRecordId: res.persistenceRecordId,
          committedAt: res.committedAt,
          errorCode: res.accepted ? null : 'PERSISTENCE_FAILED',
          errorMessage: res.errorMessage ?? null,
        });
        if (!res.accepted) {
          setIsPersistencePending(false);
          setError({
            code: 'PERSISTENCE_FAILED',
            message: res.errorMessage || 'Database persistence failed. Draft kept safely locally.',
            retryable: true,
          });
        }
      },
      onVisitCommitted: (ev) => {
        setIsPersistencePending(false);
        const committed = mergeVisitV1IntoDraft(draftRef.current, ev.visit, selectedBeneficiary, worker, {
          transcriptSummary: finalLinesRef.current.join(' '),
          attachedAlerts: alertsRef.current,
        });
        setVisitDraft(committed);
        setCommittedResult(committed);
        saveDraftLocally(committed).catch(() => {});
        dataService.recordCommittedVisit(committed);
        stopTimer();
        onDataCommitted(committed);
      },
      onPersistenceRejected: (ev) => {
        setIsPersistencePending(false);
        setError({
          code: ev.code,
          message: ev.reason,
          retryable: ev.retryable,
        });
      },
      onDangerAlert: (ev) => {
        const uiAlert = alertV1ToUi(ev.alert, {
          beneficiary_name:
            draftRef.current?.beneficiary_name || selectedBeneficiary?.full_name || undefined,
          asha_worker_id: worker.id,
          asha_worker_name: worker.full_name,
          phc_id: worker.phc_id,
        });
        dataService.registerDangerAlert(uiAlert, worker);
        setDangerAlerts((prev) => {
          if (prev.some((a) => a.alert_id === uiAlert.alert_id)) return prev;
          return [uiAlert, ...prev];
        });
        setVisitDraft((prev) =>
          prev
            ? {
                ...prev,
                danger_sign_flagged: true,
                danger_signs: Array.from(
                  new Set([...prev.danger_signs, uiAlert.canonical_danger_sign_id])
                ),
                danger_alerts: [
                  uiAlert,
                  ...prev.danger_alerts.filter((a) => a.alert_id !== uiAlert.alert_id),
                ],
              }
            : prev
        );
      },
      onError: (code, message, retryable) => {
        setError({ code, message, retryable });
      },
    });

    clientRef.current = client;
    const createdSessionId = await client.startSession({
      language,
      workerId: worker.worker_code,
      beneficiaryId: selectedBeneficiary?.beneficiary_id ?? null,
      deviceId: selectedDeviceId,
      handsFree,
    });

    if (createdSessionId) {
      setSessionId(createdSessionId);
      stopTimer();
      timerRef.current = setInterval(() => {
        setDurationSeconds((s) => s + 1);
      }, 1000);
    }
  }, [worker, language, selectedBeneficiary, selectedDeviceId, handsFree, onDataCommitted]);

  const stopRecordingSession = useCallback(() => {
    stopTimer();
    clientRef.current?.stopSession();
    setIsConnected(false);
    setAudioLevel(0);
    setWaveformBands(new Array(16).fill(0));
  }, []);

  const toggleHandsFree = useCallback((nextHandsFree: boolean) => {
    setHandsFree(nextHandsFree);
    setPttPressed(false);
    clientRef.current?.setMicTransmissionActive(nextHandsFree);
  }, []);

  const handlePttDown = useCallback(() => {
    setPttPressed(true);
    clientRef.current?.setMicTransmissionActive(true);
  }, []);

  const handlePttUp = useCallback(() => {
    setPttPressed(false);
    if (!handsFree) {
      clientRef.current?.setMicTransmissionActive(false);
    }
  }, [handsFree]);

  const triggerBargeIn = useCallback(() => {
    clientRef.current?.triggerBargeIn('user_tap');
  }, []);

  const pauseReadBack = useCallback(() => {
    clientRef.current?.pausePlayback();
  }, []);

  const resumeReadBack = useCallback(() => {
    clientRef.current?.resumePlayback();
  }, []);

  const sendClarificationSelection = useCallback((candidate: ClarificationCandidateV1) => {
    setClarification(null);
    clientRef.current?.sendTextInput(candidate.id);
  }, []);

  const startVoiceCorrection = useCallback((fieldKey?: string) => {
    setIsCorrectingMode(true);
    setTargetCorrectionField(fieldKey || null);
    if (clientRef.current) {
      clientRef.current.triggerBargeIn('voice_correction_tap');
      clientRef.current.setMicTransmissionActive(true);
    }
  }, []);

  const submitVoiceTextInput = useCallback((text: string) => {
    if (!text.trim()) return false;
    return clientRef.current?.sendTextInput(text.trim(), language) ?? false;
  }, [language]);

  const confirmAndSaveVisit = useCallback(async () => {
    const current = draftRef.current;
    if (!current) return;

    // If live WebSocket session is active, follow official Agent 1 confirm_visit -> persistence_requested -> persistence_ack flow
    if (clientRef.current?.isConnected()) {
      setIsPersistencePending(true);
      clientRef.current.sendConfirmVisit(current.visit_id, true);
      return;
    }

    // Explicit offline confirmation flow when backend socket dropped after extraction
    const confirmedDraft: VisitDraft = {
      ...current,
      status: 'confirmed',
      confirmed_at: new Date().toISOString(),
      sync_status: navigator.onLine ? 'pending' : 'pending',
    };
    setVisitDraft(confirmedDraft);
    await saveDraftLocally(confirmedDraft);

    if (navigator.onLine) {
      setIsPersistencePending(true);
      const res = await syncManager.persistConfirmedVisitNow(confirmedDraft);
      setIsPersistencePending(false);
      if (res.accepted && res.committedAt) {
        const done: VisitDraft = {
          ...confirmedDraft,
          status: 'committed',
          committed_at: res.committedAt,
          persistence_record_id: res.persistenceRecordId,
          sync_status: 'synced',
        };
        setCommittedResult(done);
        onDataCommitted(done);
        return;
      }
    }

    // Queued offline safely for reconnect sync
    setCommittedResult(confirmedDraft);
    onDataCommitted(confirmedDraft);
  }, [onDataCommitted]);

  const patchFieldStatus = useCallback((fieldKey: string, status: FieldConfirmStatus) => {
    setVisitDraft((prev) => {
      if (!prev) return prev;
      const updated = {
        ...prev,
        field_statuses: {
          ...(prev.field_statuses || {}),
          [fieldKey]: status,
        },
      };
      saveDraftLocally(updated).catch(() => {});
      return updated;
    });
  }, []);

  const acknowledgeDangerAlert = useCallback(
    (alertId: string) => {
      const updated = dataService.updateDangerAlertStatus(alertId, 'acknowledged', worker);
      if (updated) {
        setDangerAlerts((prev) => prev.map((a) => (a.alert_id === alertId ? updated : a)));
      }
    },
    [worker]
  );

  return {
    interactionState,
    isConnected,
    handsFree,
    pttPressed,
    audioLevel,
    waveformBands,
    sessionId,
    durationSeconds,
    inputDevices,
    selectedDeviceId,
    setSelectedDeviceId,
    partialStable,
    partialVolatile,
    transcriptHistory,
    assistantText,
    isTtsPlaying,
    isTtsPaused,
    visitDraft,
    dangerAlerts,
    clarification,
    correctionHistory,
    isCorrectingMode,
    targetCorrectionField,
    requiresReReadBack,
    error,
    setError,
    committedResult,
    isPersistencePending,
    startVoiceSession,
    stopRecordingSession,
    resetSessionState,
    toggleHandsFree,
    handlePttDown,
    handlePttUp,
    triggerBargeIn,
    pauseReadBack,
    resumeReadBack,
    sendClarificationSelection,
    startVoiceCorrection,
    submitVoiceTextInput,
    confirmAndSaveVisit,
    patchFieldStatus,
    acknowledgeDangerAlert,
  };
}

