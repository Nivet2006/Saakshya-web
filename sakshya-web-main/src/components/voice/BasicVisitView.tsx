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
import type { Beneficiary, LanguageCode } from '@/types';

interface BasicVisitViewProps {
  beneficiaries: Beneficiary[];
  recentBeneficiaryIds: string[];
  selectedBeneficiary: Beneficiary | null;
  onSelectBeneficiary: (ben: Beneficiary | null) => void;
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
  language,
  onChangeLanguage,
  voice,
  onGoHome,
}) => {
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
        disabled={voice.isConnected}
      />

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
            activeCorrectionField={voice.targetCorrectionField}
            onPausePlayback={voice.pauseReadBack}
            onResumePlayback={voice.resumeReadBack}
            onVoiceCorrectField={(fieldKey) => voice.startVoiceCorrection(fieldKey)}
          />

          {/* Step 6: Confirmation Actions */}
          <VisitConfirmationActions
            draft={voice.visitDraft}
            isSaving={voice.isPersistencePending}
            requiresReReadBack={voice.requiresReReadBack}
            onAcceptAndSave={voice.confirmAndSaveVisit}
            onRejectAndCorrect={() => voice.startVoiceCorrection()}
            onDiscardAndRerecord={voice.resetSessionState}
          />
        </>
      )}
    </div>
  );
};

