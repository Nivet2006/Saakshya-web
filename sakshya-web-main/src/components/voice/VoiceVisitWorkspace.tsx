'use client';

import React, { useEffect, useState } from 'react';
import { DangerAlertBanner } from '@/components/DangerAlertBanner';
import { ErrorBanner } from '@/components/ui/ClinicalUI';
import { AdvancedVisitView } from '@/components/voice/AdvancedVisitView';
import { AudioDiagnosticsPanel } from '@/components/voice/AudioDiagnosticsPanel';
import { BasicVisitView } from '@/components/voice/BasicVisitView';
import { ModeSelector } from '@/components/voice/ModeSelector';
import { useVoiceVisitSession } from '@/hooks/useVoiceVisitSession';
import type { AshaExperienceMode, Beneficiary, LanguageCode, UserProfile, VisitDraft } from '@/types';

interface VoiceVisitWorkspaceProps {
  worker: UserProfile;
  beneficiaries: Beneficiary[];
  recentVisits: VisitDraft[];
  selectedBeneficiary: Beneficiary | null;
  onSelectBeneficiary: (ben: Beneficiary | null) => void;
  language: LanguageCode;
  onChangeLanguage: (lang: LanguageCode) => void;
  onVisitCommitted: (visit: VisitDraft) => void;
  onGoHome: () => void;
}

const MODE_STORAGE_KEY = 'sakshya_asha_experience_mode';

export const VoiceVisitWorkspace: React.FC<VoiceVisitWorkspaceProps> = ({
  worker,
  beneficiaries,
  recentVisits,
  selectedBeneficiary,
  onSelectBeneficiary,
  language,
  onChangeLanguage,
  onVisitCommitted,
  onGoHome,
}) => {
  // Default experience MUST be Basic Mode
  const [mode, setMode] = useState<AshaExperienceMode>('basic');

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(MODE_STORAGE_KEY);
      if (saved === 'advanced' || saved === 'basic') {
        setMode(saved);
      }
    }
  }, []);

  const handleModeChange = (next: AshaExperienceMode) => {
    setMode(next);
    if (typeof window !== 'undefined') {
      localStorage.setItem(MODE_STORAGE_KEY, next);
    }
  };

  const voice = useVoiceVisitSession({
    worker,
    language,
    selectedBeneficiary,
    beneficiaries,
    onSelectBeneficiary,
    onDataCommitted: onVisitCommitted,
  });

  const recentIds = Array.from(
    new Set(
      recentVisits
        .map((v) => v.beneficiary_id)
        .filter((id): id is string => typeof id === 'string' && id.length > 0)
    )
  );

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-clinical-text">
          Record Household Voice Visit
        </h1>
        <p className="text-xs sm:text-sm text-clinical-text-secondary mt-0.5">
          Connected to Agent 1 Voice Pipeline · Switch anytime between Basic and Advanced views
          without losing visit data.
        </p>
      </div>

      {/* Mode Switcher: Basic (Default) vs Advanced */}
      <ModeSelector mode={mode} onChange={handleModeChange} />

      {/* Developer Diagnostic Panel & Live Mic Loopback Test */}
      <AudioDiagnosticsPanel
        diagnostics={voice.audioDiagnostics}
        audioLevel={voice.audioLevel}
        waveformBands={voice.waveformBands}
        isConnected={voice.isConnected}
        sessionId={voice.sessionId}
        inputDevices={voice.inputDevices}
        selectedDeviceId={voice.selectedDeviceId}
        onSelectDevice={voice.setSelectedDeviceId}
        onSendTextUtterance={voice.submitVoiceTextInput}
        language={language}
      />

      {/* Urgent Danger Sign Alerts ALWAYS Override Normal Flow & Stay Visible */}
      {voice.dangerAlerts.length > 0 && (
        <div className="space-y-3" aria-label="Urgent Danger Sign Alerts">
          {voice.dangerAlerts.map((alert) => (
            <DangerAlertBanner
              key={alert.alert_id}
              alert={alert}
              language={language}
              onAcknowledge={(id) => voice.acknowledgeDangerAlert(id)}
            />
          ))}
        </div>
      )}

      {/* Session Error Recovery Banner */}
      {voice.error && (
        <ErrorBanner
          title={`Voice Session Issue (${voice.error.code})`}
          message={voice.error.message}
          onRetry={voice.error.retryable ? voice.startVoiceSession : undefined}
          retryLabel="Reconnect Session"
          onDismiss={() => voice.setError(null)}
        />
      )}

      {/* Basic Mode (Default) vs Advanced Mode sharing the EXACT same underlying VisitDraft & VoiceSession */}
      {mode === 'basic' ? (
        <BasicVisitView
          beneficiaries={beneficiaries}
          recentBeneficiaryIds={recentIds}
          selectedBeneficiary={selectedBeneficiary}
          onSelectBeneficiary={onSelectBeneficiary}
          language={language}
          onChangeLanguage={onChangeLanguage}
          voice={voice}
          onGoHome={onGoHome}
        />
      ) : (
        <AdvancedVisitView
          beneficiaries={beneficiaries}
          recentBeneficiaryIds={recentIds}
          selectedBeneficiary={selectedBeneficiary}
          onSelectBeneficiary={onSelectBeneficiary}
          language={language}
          onChangeLanguage={onChangeLanguage}
          voice={voice}
          onSwitchToBasic={() => handleModeChange('basic')}
          onGoHome={onGoHome}
        />
      )}
    </div>
  );
};

