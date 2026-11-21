'use client';

import React from 'react';
import { FieldStatusPill } from '@/components/ui/ClinicalUI';
import { BeneficiarySelector } from '@/components/voice/BeneficiarySelector';
import { LanguageSelector } from '@/components/voice/LanguageSelector';
import {
  FieldConfirmation,
  SpokenDescription,
  VisitConfirmationActions,
  VisitSuccess,
} from '@/components/voice/VisitReviewShared';
import {
  LiveTranscript,
  ProcessingIndicator,
  VoiceRecorder,
} from '@/components/voice/VoiceRecorderAndTranscript';
import type { useVoiceVisitSession } from '@/hooks/useVoiceVisitSession';
import type { Beneficiary, LanguageCode } from '@/types';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Baby,
  CalendarCheck,
  FileText,
  ShieldCheck,
  Syringe,
} from 'lucide-react';

interface AdvancedVisitViewProps {
  beneficiaries: Beneficiary[];
  recentBeneficiaryIds: string[];
  selectedBeneficiary: Beneficiary | null;
  onSelectBeneficiary: (ben: Beneficiary | null) => void;
  language: LanguageCode;
  onChangeLanguage: (lang: LanguageCode) => void;
  voice: ReturnType<typeof useVoiceVisitSession>;
  onSwitchToBasic: () => void;
  onGoHome: () => void;
}

export const AdvancedVisitView: React.FC<AdvancedVisitViewProps> = ({
  beneficiaries,
  recentBeneficiaryIds,
  selectedBeneficiary,
  onSelectBeneficiary,
  language,
  onChangeLanguage,
  voice,
  onSwitchToBasic,
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

  const draft = voice.visitDraft;
  const statuses = draft?.field_statuses || {};
  const hasUnresolved = Object.values(statuses).some((s) => s === 'needs_clarification');

  const isMaternal =
    draft?.visit_type === 'ANC' ||
    draft?.visit_type === 'PNC' ||
    selectedBeneficiary?.category === 'PREGNANT_WOMAN' ||
    selectedBeneficiary?.category === 'LACTATING_MOTHER';

  const isNewborn =
    draft?.visit_type === 'Newborn' || selectedBeneficiary?.category === 'INFANT';

  return (
    <div className="space-y-5">
      {/* Top Voice Controls Grid for Tablet / Desktop */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        <div className="lg:col-span-5 space-y-4">
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
          <LanguageSelector
            selectedLanguage={language}
            onChange={onChangeLanguage}
            disabled={voice.isConnected}
          />
        </div>

        <div className="lg:col-span-7 space-y-4">
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
          <ProcessingIndicator active={voice.interactionState === 'processing'} />
        </div>
      </div>

      {/* Section 7a: Live Full Transcription */}
      <LiveTranscript
        history={voice.transcriptHistory}
        partialStable={voice.partialStable}
        partialVolatile={voice.partialVolatile}
        language={language}
      />

      {/* Detailed Multi-Section Clinical Review Cards */}
      {draft && (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <h2 className="text-lg font-bold text-clinical-text">
              Detailed Healthcare Record &amp; Field Confirmation
            </h2>
            <button
              type="button"
              onClick={onSwitchToBasic}
              className="inline-flex items-center gap-1.5 text-xs font-bold text-clinical-primary hover:underline"
            >
              <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Return to Basic Mode</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Section 1 — Beneficiary Information */}
            <section className="bg-white border border-clinical-border-subtle rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-clinical-text flex items-center gap-2">
                  <Activity className="h-4 w-4 text-clinical-primary" aria-hidden="true" />
                  <span>Section 1 · Beneficiary &amp; Visit Info</span>
                </h3>
                <FieldStatusPill status={statuses.beneficiary_id || 'extracted'} compact />
              </div>
              <dl className="grid grid-cols-2 gap-y-2 text-xs">
                <dt className="text-slate-500">Beneficiary ID</dt>
                <dd className="font-mono font-bold text-clinical-text">
                  {draft.beneficiary_id || 'Unresolved'}
                </dd>
                <dt className="text-slate-500">Beneficiary Name</dt>
                <dd className="font-bold text-clinical-text">
                  {draft.beneficiary_name || 'Not identified'}
                </dd>
                <dt className="text-slate-500">Visit Date</dt>
                <dd className="tabular-nums text-clinical-text">
                  {new Date(draft.visit_date).toLocaleDateString()}
                </dd>
                <dt className="text-slate-500">Visit Type</dt>
                <dd className="font-bold text-clinical-text">
                  {draft.visit_type || 'Needs Clarification'}
                </dd>
              </dl>
              <FieldConfirmation
                fieldKey="visit_type"
                label="Visit Type"
                currentStatus={statuses.visit_type || 'extracted'}
                onUpdateStatus={voice.patchFieldStatus}
                onVoiceCorrect={(k) => voice.startVoiceCorrection(k)}
              />
            </section>

            {/* Section 2 or 3 — Maternal OR Newborn Care Info */}
            {isMaternal && (
              <section className="bg-white border border-clinical-border-subtle rounded-xl p-4 shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-bold text-clinical-text flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-clinical-primary" aria-hidden="true" />
                    <span>Section 2 · Maternal / ANC-PNC Info</span>
                  </h3>
                  <FieldStatusPill status={statuses.weight_kg || 'extracted'} compact />
                </div>
                <dl className="grid grid-cols-2 gap-y-2 text-xs">
                  <dt className="text-slate-500">Classification</dt>
                  <dd className="font-bold text-clinical-text">{draft.visit_type || 'Pending'}</dd>
                  <dt className="text-slate-500">Measured Weight</dt>
                  <dd className="font-bold tabular-nums text-clinical-text">
                    {draft.weight_kg !== null ? `${draft.weight_kg} kg` : 'Not recorded'}
                  </dd>
                  <dt className="text-slate-500">Spoken Phrase</dt>
                  <dd className="text-slate-600">{draft.weight_source_text || '—'}</dd>
                  {selectedBeneficiary?.edd_date && (
                    <>
                      <dt className="text-slate-500">Directory EDD</dt>
                      <dd className="tabular-nums font-semibold text-clinical-text">
                        {selectedBeneficiary.edd_date}
                      </dd>
                    </>
                  )}
                </dl>
                <FieldConfirmation
                  fieldKey="weight_kg"
                  label="Weight"
                  currentStatus={statuses.weight_kg || 'extracted'}
                  onUpdateStatus={voice.patchFieldStatus}
                  onVoiceCorrect={(k) => voice.startVoiceCorrection(k)}
                />
              </section>
            )}

            {isNewborn && (
              <section className="bg-white border border-clinical-border-subtle rounded-xl p-4 shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-bold text-clinical-text flex items-center gap-2">
                    <Baby className="h-4 w-4 text-clinical-secondary" aria-hidden="true" />
                    <span>Section 3 · Newborn / HBNC Details</span>
                  </h3>
                  <FieldStatusPill status={statuses.weight_kg || 'extracted'} compact />
                </div>
                <dl className="grid grid-cols-2 gap-y-2 text-xs">
                  <dt className="text-slate-500">Newborn Weight</dt>
                  <dd className="font-bold tabular-nums text-clinical-text">
                    {draft.weight_kg !== null ? `${draft.weight_kg} kg` : 'Not recorded'}
                  </dd>
                  <dt className="text-slate-500">Source Speech</dt>
                  <dd className="text-slate-600">{draft.weight_source_text || '—'}</dd>
                  <dt className="text-slate-500">Danger Flagged</dt>
                  <dd
                    className={`font-bold ${
                      draft.danger_sign_flagged ? 'text-clinical-danger' : 'text-emerald-700'
                    }`}
                  >
                    {draft.danger_sign_flagged ? 'Yes — Urgent PHC Referral' : 'None flagged'}
                  </dd>
                </dl>
                <FieldConfirmation
                  fieldKey="weight_kg"
                  label="Newborn Weight"
                  currentStatus={statuses.weight_kg || 'extracted'}
                  onUpdateStatus={voice.patchFieldStatus}
                  onVoiceCorrect={(k) => voice.startVoiceCorrection(k)}
                />
              </section>
            )}

            {/* Section 4 — Immunisation */}
            <section className="bg-white border border-clinical-border-subtle rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-clinical-text flex items-center gap-2">
                  <Syringe className="h-4 w-4 text-clinical-primary" aria-hidden="true" />
                  <span>Section 4 · Immunisation Ledger</span>
                </h3>
                <FieldStatusPill status={statuses.vaccinations_due || 'extracted'} compact />
              </div>
              <div className="space-y-2 text-xs">
                <div>
                  <span className="font-semibold text-slate-500 block">Vaccinations Completed:</span>
                  {draft.vaccinations_completed.length > 0 ? (
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {draft.vaccinations_completed.map((v) => (
                        <span
                          key={v}
                          className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold"
                        >
                          {v}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-slate-500 italic">None reported as completed</span>
                  )}
                </div>
                <div>
                  <span className="font-semibold text-slate-500 block">Vaccinations Due / Pending:</span>
                  {draft.vaccinations_due.length > 0 ? (
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {draft.vaccinations_due.map((v) => (
                        <span
                          key={v}
                          className="px-2 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-300 font-semibold"
                        >
                          {v}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-slate-500 italic">None identified</span>
                  )}
                </div>
              </div>
              <FieldConfirmation
                fieldKey="vaccinations_due"
                label="Vaccinations"
                currentStatus={statuses.vaccinations_due || 'extracted'}
                onUpdateStatus={voice.patchFieldStatus}
                onVoiceCorrect={(k) => voice.startVoiceCorrection(k)}
              />
            </section>

            {/* Section 5 — Danger Signs (Read-only backend authority) */}
            <section className="bg-white border border-clinical-border-subtle rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-clinical-text flex items-center gap-2">
                  <AlertTriangle
                    className={`h-4 w-4 ${
                      draft.danger_sign_flagged ? 'text-clinical-danger' : 'text-slate-400'
                    }`}
                    aria-hidden="true"
                  />
                  <span>Section 5 · Deterministic Danger Screening</span>
                </h3>
                <span
                  className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                    draft.danger_sign_flagged
                      ? 'bg-red-100 text-red-800'
                      : 'bg-emerald-50 text-emerald-800'
                  }`}
                >
                  {draft.danger_sign_flagged ? 'FLAGGED' : 'Clear in speech'}
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Evaluated exclusively by Agent 1&rsquo;s NHM/MoHFW deterministic clinical engine.
                Frontend never overrides or hides safety alerts.
              </p>
              {draft.danger_signs.length > 0 && (
                <ul className="mt-2 space-y-1 text-xs font-bold text-red-900">
                  {draft.danger_signs.map((s) => (
                    <li key={s}>• {s}</li>
                  ))}
                </ul>
              )}
            </section>

            {/* Section 6 — Follow-up Actions */}
            <section className="bg-white border border-clinical-border-subtle rounded-xl p-4 shadow-sm md:col-span-2">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-clinical-text flex items-center gap-2">
                  <CalendarCheck className="h-4 w-4 text-clinical-primary" aria-hidden="true" />
                  <span>Section 6 · Follow-Up Actions &amp; Next Visit</span>
                </h3>
                <span className="text-xs font-bold tabular-nums text-clinical-primary">
                  Next Visit: {draft.next_visit_date || 'Not scheduled'}
                </span>
              </div>
              {draft.follow_up_actions.length > 0 ? (
                <ul className="space-y-2">
                  {draft.follow_up_actions.map((act, i) => (
                    <li
                      key={`${act.action_type}-${i}`}
                      className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-wrap items-center justify-between gap-2 text-xs"
                    >
                      <div>
                        <span className="font-bold text-clinical-text">{act.description}</span>
                        {act.source_phrase && (
                          <span className="block text-[11px] text-slate-500">
                            Trigger: &ldquo;{act.source_phrase}&rdquo;
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[11px] text-slate-600">
                          {act.due_date || 'Immediate'}
                        </span>
                        <span
                          className={`uppercase text-[10px] font-bold px-2 py-0.5 rounded ${
                            act.priority === 'urgent'
                              ? 'bg-red-100 text-red-800'
                              : act.priority === 'high'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-slate-200 text-slate-700'
                          }`}
                        >
                          {act.priority}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-500 italic">No structured follow-up actions yet.</p>
              )}
              <FieldConfirmation
                fieldKey="next_visit_date"
                label="Next Visit Date"
                currentStatus={statuses.next_visit_date || 'extracted'}
                onUpdateStatus={voice.patchFieldStatus}
                onVoiceCorrect={(k) => voice.startVoiceCorrection(k)}
              />
            </section>
          </div>

          {/* Section 7b — Spoken Read-back & Correction Audit Log */}
          <section className="bg-white border border-clinical-border-subtle rounded-xl p-4 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-clinical-text flex items-center gap-2">
              <FileText className="h-4 w-4 text-clinical-primary" aria-hidden="true" />
              <span>Section 7 · Read-Back &amp; Voice Correction Audit</span>
            </h3>
            <SpokenDescription
              transcriptSummary={draft.raw_transcript_summary}
              readBackSummary={draft.read_back_summary}
              isTtsPlaying={voice.isTtsPlaying}
              isTtsPaused={voice.isTtsPaused}
              requiresReReadBack={voice.requiresReReadBack}
              onPausePlayback={voice.pauseReadBack}
              onResumePlayback={voice.resumeReadBack}
            />
            {voice.correctionHistory.length > 0 && (
              <div className="p-3 rounded-lg bg-indigo-50/70 border border-indigo-200 text-xs space-y-1.5">
                <p className="font-bold text-indigo-950">Applied Voice Corrections (Other Fields Preserved):</p>
                {voice.correctionHistory.map((c, idx) => (
                  <p key={idx} className="text-indigo-900">
                    Updated <strong>{c.corrected_fields.join(', ')}</strong>:{' '}
                    <code>{JSON.stringify(c.previous_values)}</code> →{' '}
                    <code>{JSON.stringify(c.new_values)}</code> (preserved:{' '}
                    {c.preserved_fields.join(', ')})
                  </p>
                ))}
              </div>
            )}
          </section>

          {/* Section 8 — Final Detailed Confirmation Actions */}
          <VisitConfirmationActions
            draft={draft}
            isSaving={voice.isPersistencePending}
            requiresReReadBack={voice.requiresReReadBack}
            hasUnresolvedClarifications={hasUnresolved}
            onAcceptAndSave={voice.confirmAndSaveVisit}
            onRejectAndCorrect={() => voice.startVoiceCorrection()}
            onDiscardAndRerecord={voice.resetSessionState}
          />
        </div>
      )}
    </div>
  );
};

