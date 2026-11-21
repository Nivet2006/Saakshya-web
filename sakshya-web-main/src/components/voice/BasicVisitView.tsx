'use client';

import React from 'react';
import { BeneficiarySelector } from '@/components/voice/BeneficiarySelector';
import { LanguageSelector } from '@/components/voice/LanguageSelector';
import {
  VisitConfirmationActions,
  VisitSuccess,
  VisitSummaryCard,
} from '@/components/voice/VisitReviewShared';
import {
  LiveTranscript,
  ProcessingIndicator,
  VoiceRecorder,
} from '@/components/voice/VoiceRecorderAndTranscript';
import { useVoiceVisitSession } from '@/hooks/useVoiceVisitSession';
import { HealthWave } from '@/components/animations/HealthWave';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type { Beneficiary, LanguageCode } from '@/types';
import { AlertCircle, CheckCircle2, Clock, ShieldCheck, Volume2 } from 'lucide-react';

interface BasicVisitViewProps {
  beneficiaries: Beneficiary[];
  recentBeneficiaryIds: string[];
  selectedBeneficiary: Beneficiary | null;
  onSelectBeneficiary: (ben: Beneficiary | null) => void;
  onAddBeneficiary?: (input: {
    full_name: string;
    category: Beneficiary['category'];
    age_years: number;
    village: string;
    household_head?: string;
    phone_number?: string;
    edd_date?: string;
    high_risk_status: boolean;
    preferred_language: LanguageCode;
  }) => Promise<Beneficiary>;
  language: LanguageCode;
  onChangeLanguage: (lang: LanguageCode) => void;
  voice: ReturnType<typeof useVoiceVisitSession>;
  onGoHome: () => void;
}

export const BasicVisitView: React.FC<BasicVisitViewProps> = ({
  beneficiaries,
  recentBeneficiaryIds,
  selectedBeneficiary,
  onSelectBeneficiary,
  onAddBeneficiary,
  language,
  onChangeLanguage,
  voice,
  onGoHome,
}) => {
  const { ui } = useTranslation(language);
  if (voice.committedResult) {
    return (
      <VisitSuccess
        savedVisit={voice.committedResult}
        onStartAnother={() => {
          voice.resetSessionState();
          onSelectBeneficiary(null);
        }}
        onGoHome={onGoHome}
      />
    );
  }

  return (
    <div className="space-y-5">
      {/* Step 1: Beneficiary Identification */}
      <BeneficiarySelector
        beneficiaries={beneficiaries}
        selectedBeneficiary={selectedBeneficiary}
        recentBeneficiaryIds={recentBeneficiaryIds}
        onSelect={onSelectBeneficiary}
        onAddBeneficiary={onAddBeneficiary}
        currentLanguage={language}
        ambiguousCandidates={
          voice.clarification?.reason === 'ambiguous_beneficiary'
            ? voice.clarification.candidates
            : undefined
        }
        onSelectCandidate={(cand) => voice.sendClarificationSelection(cand)}
        disabled={voice.isConnected}
      />

      {/* Step 2: Language Selection */}
      <LanguageSelector
        selectedLanguage={language}
        onChange={onChangeLanguage}
      />

      {/* Voice Beneficiary Verification & Live TTFA Performance Status */}
      {(voice.isConnected || voice.identityVerificationStatus !== 'idle') && (
        <section
          aria-label="Beneficiary Identity Verification and Voice Performance"
          className={`rounded-xl border-2 p-4 shadow-sm transition-colors ${
            voice.identityVerificationStatus === 'verified'
              ? 'bg-emerald-50/80 border-emerald-400 text-emerald-950'
              : voice.identityVerificationStatus === 'correcting'
              ? 'bg-amber-50/90 border-amber-400 text-amber-950'
              : 'bg-sky-50/90 border-sky-400 text-sky-950'
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              {voice.identityVerificationStatus === 'verified' ? (
                <ShieldCheck className="h-5 w-5 text-emerald-700 shrink-0" aria-hidden="true" />
              ) : voice.identityVerificationStatus === 'correcting' ? (
                <AlertCircle className="h-5 w-5 text-amber-700 shrink-0" aria-hidden="true" />
              ) : (
                <Volume2 className="h-5 w-5 text-sky-700 shrink-0" aria-hidden="true" />
              )}
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs sm:text-sm font-bold">
                    {voice.identityVerificationStatus === 'verified'
                      ? ui.identityVerifiedVoice
                      : voice.identityVerificationStatus === 'candidate_confirmation'
                      ? ui.identityCandidatePrompt
                      : voice.identityVerificationStatus === 'correcting'
                      ? ui.identityCorrectionPrompt
                      : ui.identityCheckPrompt}
                  </span>
                  {(voice.visitDraft?.beneficiary_id || selectedBeneficiary?.beneficiary_id) && (
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-white/90 border border-current/20">
                      {voice.visitDraft?.beneficiary_name || selectedBeneficiary?.full_name} (
                      {voice.visitDraft?.beneficiary_id || selectedBeneficiary?.beneficiary_id})
                    </span>
                  )}
                </div>
                {(voice.verificationPrompt || voice.assistantText) && (
                  <p className="text-xs mt-1 font-medium opacity-90">
                    {voice.verificationPrompt || voice.assistantText}
                  </p>
                )}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div className="hidden sm:block overflow-hidden py-0.5">
                <HealthWave width={150} height={24} color="#0D9488" opacity={0.7} />
              </div>
              {voice.latencyMetrics && (
                <div
                  className="inline-flex items-center gap-2 px-2.5 py-1 rounded-lg bg-white/90 border border-slate-200 text-[11px] font-mono text-slate-700"
                  title="End-of-speech to First Audible Assistant Audio (TTFA)"
                >
                  <Clock className="h-3.5 w-3.5 text-clinical-primary shrink-0" aria-hidden="true" />
                  <span>
                    {voice.latencyMetrics.lastTtfaMs !== null
                      ? `TTFA: ${voice.latencyMetrics.lastTtfaMs}ms (P50: ${voice.latencyMetrics.p50TtfaMs ?? '-'}ms · P95: ${voice.latencyMetrics.p95TtfaMs ?? '-'}ms)`
                      : voice.latencyMetrics.greetingLatencyMs !== null
                      ? `Greeting: ${voice.latencyMetrics.greetingLatencyMs}ms`
                      : 'Measuring TTFA...'}
                  </span>
                </div>
              )}
              {voice.audioDiagnostics && (
                <div
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/90 border border-slate-200 text-[11px] font-mono text-slate-600"
                  title="Web Audio capture pipeline & barge-in diagnostics"
                >
                  <span>
                    {voice.audioDiagnostics.usedAudioWorklet ? 'Worklet' : 'ScriptProc'} ·{' '}
                    {voice.audioDiagnostics.captureSampleRate}Hz→16kHz · Stale:{' '}
                    {voice.audioDiagnostics.staleChunksDiscarded}
                  </span>
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Step 3: Simple Voice Capture + Live Transcription */}
      <VoiceRecorder
        interactionState={voice.interactionState}
        isConnected={voice.isConnected}
        handsFree={voice.handsFree}
        pttPressed={voice.pttPressed}
        audioLevel={voice.audioLevel}
        waveformBands={voice.waveformBands}
        durationSeconds={voice.durationSeconds}
        language={language}
        inputDevices={voice.inputDevices}
        selectedDeviceId={voice.selectedDeviceId}
        isCorrectingMode={voice.isCorrectingMode}
        targetCorrectionField={voice.targetCorrectionField}
        onSelectDevice={voice.setSelectedDeviceId}
        onToggleHandsFree={voice.toggleHandsFree}
        onStartRecording={voice.startVoiceSession}
        onStopRecording={voice.stopRecordingSession}
        onPttDown={voice.handlePttDown}
        onPttUp={voice.handlePttUp}
        onBargeIn={voice.triggerBargeIn}
        onSendTextUtterance={voice.submitVoiceTextInput}
      />

      {(voice.transcriptHistory.length > 0 || voice.partialStable || voice.partialVolatile) && (
        <LiveTranscript
          history={voice.transcriptHistory}
          partialStable={voice.partialStable}
          partialVolatile={voice.partialVolatile}
          language={language}
        />
      )}

      {/* Step 4: Processing Indicator */}
      <ProcessingIndicator active={voice.interactionState === 'processing'} />

      {/* Step 5: Here's what I understood from your visit */}
      {voice.visitDraft && (
        <>
          <VisitSummaryCard
            draft={voice.visitDraft}
            isTtsPlaying={voice.isTtsPlaying}
            isTtsPaused={voice.isTtsPaused}
            requiresReReadBack={voice.requiresReReadBack}
            summaryOutdated={voice.summaryOutdated}
            activeCorrectionField={voice.targetCorrectionField}
            onPausePlayback={voice.pauseReadBack}
            onResumePlayback={voice.resumeReadBack}
            onVoiceCorrectField={(fieldKey) => voice.startVoiceCorrection(fieldKey)}
            onVisualPatchFields={voice.patchFieldsVisually}
            onRemoveObservation={voice.removeObservationVisually}
            onRemoveEvent={voice.removeEventVisually}
            onSpeakToMakeChanges={voice.speakToMakeChanges}
          />

          {/* Summary Readback Preference & Final Submission Workflow Controls */}
          {voice.reviewPhase === 'ask_readback' && (
            <section
              aria-label="Summary Playback Preference"
              className="bg-sky-50 border-2 border-sky-400 rounded-2xl p-4 sm:p-5 shadow-sm space-y-3"
            >
              <p className="text-sm font-bold text-sky-950">
                {ui.readbackPrefPrompt}
              </p>
              <div className="flex flex-wrap gap-2.5">
                <button
                  type="button"
                  onClick={() => voice.respondReadbackPreference(true)}
                  className="px-4 py-2.5 rounded-xl bg-clinical-primary hover:bg-clinical-primary-dark text-white text-xs sm:text-sm font-bold"
                >
                  {ui.yesReadSummaryBtn}
                </button>
                <button
                  type="button"
                  onClick={() => voice.respondReadbackPreference(false)}
                  className="px-4 py-2.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-300 text-slate-800 text-xs sm:text-sm font-bold"
                >
                  {ui.noSkipSubmissionBtn}
                </button>
                <button
                  type="button"
                  onClick={voice.speakToMakeChanges}
                  className="px-4 py-2.5 rounded-xl bg-amber-100 hover:bg-amber-200 border border-amber-400 text-amber-950 text-xs sm:text-sm font-bold"
                >
                  {ui.speakMoreChangesBtn}
                </button>
              </div>
            </section>
          )}

          {voice.reviewPhase === 'editing' && voice.isConnected && (
            <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-50 border border-slate-200 rounded-xl p-3.5">
              <span className="text-xs font-semibold text-slate-700">
                {ui.finishNotesAndReviewPrompt}
              </span>
              <button
                type="button"
                onClick={voice.finishNotesAndReview}
                className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold"
              >
                {ui.finishAndReviewBtn}
              </button>
            </div>
          )}

          {voice.reviewPhase === 'draft_retained' && (
            <div
              role="status"
              className="p-3.5 rounded-xl bg-amber-50 border border-amber-300 text-xs font-semibold text-amber-950"
            >
              {ui.draftRetainedNotice}
            </div>
          )}

          {/* Step 6: Confirmation & Final Submission Actions */}
          <VisitConfirmationActions
            draft={voice.visitDraft}
            isSaving={voice.isPersistencePending}
            requiresReReadBack={voice.requiresReReadBack}
            onAcceptAndSave={voice.confirmAndSaveVisit}
            onRejectAndCorrect={voice.speakToMakeChanges}
            onDiscardAndRerecord={voice.resetSessionState}
          />
        </>
      )}
    </div>
  );
};

