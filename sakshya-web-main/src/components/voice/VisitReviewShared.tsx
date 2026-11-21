'use client';

import React, { useState } from 'react';
import { FieldStatusPill, NativeConfirmDialog } from '@/components/ui/ClinicalUI';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type { FieldConfirmStatus, VisitDraft } from '@/types';
import {
  AlertTriangle,
  Calendar,
  Check,
  CheckCircle2,
  Edit3,
  HelpCircle,
  Mic,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  Volume2,
  X,
} from 'lucide-react';

export const SpokenDescription: React.FC<{
  transcriptSummary?: string;
  readBackSummary?: string;
  isTtsPlaying: boolean;
  isTtsPaused: boolean;
  requiresReReadBack?: boolean;
  onPausePlayback: () => void;
  onResumePlayback: () => void;
}> = ({
  transcriptSummary,
  readBackSummary,
  isTtsPlaying,
  isTtsPaused,
  requiresReReadBack,
  onPausePlayback,
  onResumePlayback,
}) => {
  const { ui } = useTranslation();
  return (
    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
          {ui.spokenDescriptionHeading}
        </span>

        {isTtsPlaying && (
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-clinical-primary">
              <Volume2 className="h-3.5 w-3.5" aria-hidden="true" />
              <span>{isTtsPaused ? 'Read-back Paused' : 'Timbre Reading Aloud'}</span>
            </span>
            <button
              type="button"
              onClick={isTtsPaused ? onResumePlayback : onPausePlayback}
              className="compact-chip inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white border border-slate-300 text-xs font-bold text-slate-800 hover:bg-slate-100"
            >
              {isTtsPaused ? (
                <>
                  <Play className="h-3 w-3" aria-hidden="true" />
                  <span>Resume</span>
                </>
              ) : (
                <>
                  <Pause className="h-3 w-3" aria-hidden="true" />
                  <span>Pause</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {transcriptSummary ? (
        <p className="text-sm text-clinical-text leading-relaxed bg-white p-3 rounded-lg border border-slate-200">
          &ldquo;{transcriptSummary}&rdquo;
        </p>
      ) : (
        <p className="text-xs text-slate-500 italic">No spoken description finalized yet.</p>
      )}

      {readBackSummary && (
        <div className="p-3 rounded-lg bg-teal-50/80 border border-teal-200 text-xs text-teal-950">
          <span className="font-bold block mb-1 text-clinical-primary-dark">
            Assistant Spoken Summary:
          </span>
          <p className="leading-relaxed">{readBackSummary}</p>
        </div>
      )}

      {requiresReReadBack && (
        <div
          role="status"
          className="p-2.5 rounded-lg bg-amber-50 border border-amber-300 text-xs text-amber-900 font-semibold"
        >
          Field updated — assistant will re-read the corrected summary before saving.
        </div>
      )}
    </div>
  );
};

export const VoiceCorrectionControl: React.FC<{
  fieldKey: string;
  fieldLabel: string;
  isActiveTarget?: boolean;
  onTriggerVoiceCorrection: (fieldKey: string) => void;
}> = ({ fieldKey, fieldLabel, isActiveTarget, onTriggerVoiceCorrection }) => (
  <button
    type="button"
    onClick={() => onTriggerVoiceCorrection(fieldKey)}
    aria-label={`Correct ${fieldLabel} by voice`}
    className={`compact-chip inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold border transition-colors ${
      isActiveTarget
        ? 'bg-indigo-600 text-white border-indigo-700'
        : 'bg-white text-clinical-secondary border-slate-300 hover:bg-sky-50'
    }`}
  >
    <Mic className="h-3 w-3" aria-hidden="true" />
    <span>Correct</span>
  </button>
);

export const CapturedField: React.FC<{
  fieldKey: string;
  label: string;
  value: string | null;
  rawEditValue?: string;
  editType?: 'text' | 'number' | 'date' | 'visit_type';
  sourcePhrase?: string | null;
  status: FieldConfirmStatus;
  onVoiceCorrect?: (fieldKey: string) => void;
  onVisualSave?: (fieldKey: string, nextValue: string) => void;
  activeCorrectionField?: string | null;
}> = ({
  fieldKey,
  label,
  value,
  rawEditValue,
  editType = 'text',
  sourcePhrase,
  status,
  onVoiceCorrect,
  onVisualSave,
  activeCorrectionField,
}) => {
  const [editing, setEditing] = useState(false);
  const [editDraft, setEditDraft] = useState(rawEditValue ?? '');
  const isMissing = value === null || value === '';
  const needsAttn = status === 'needs_clarification' || isMissing;
  const isModified = status === 'corrected';

  const startEdit = () => {
    setEditDraft(rawEditValue ?? (value || ''));
    setEditing(true);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    onVisualSave?.(fieldKey, editDraft);
    setEditing(false);
  };

  return (
    <div
      className={`p-3 rounded-xl border transition-colors flex flex-col gap-2 ${
        activeCorrectionField === fieldKey
          ? 'bg-indigo-50 border-indigo-400 ring-2 ring-indigo-200'
          : isModified
          ? 'bg-sky-50/60 border-sky-300'
          : needsAttn
          ? 'bg-amber-50/70 border-dashed border-amber-400'
          : 'bg-white border-slate-200'
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-clinical-text-secondary">{label}</span>
            <FieldStatusPill
              status={isMissing && status !== 'needs_clarification' ? 'missing' : status}
              compact
            />
            {isModified && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-sky-100 text-sky-900">
                Updated
              </span>
            )}
          </div>
          <p
            className={`mt-1 text-sm font-bold tabular-nums ${
              isMissing ? 'text-amber-800 italic font-semibold' : 'text-clinical-text'
            }`}
          >
            {isMissing ? 'Not identified — needs confirmation' : value}
          </p>
          {sourcePhrase && (
            <p className="text-[11px] text-slate-500 mt-0.5">From speech: &ldquo;{sourcePhrase}&rdquo;</p>
          )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {onVisualSave && !editing && (
            <button
              type="button"
              onClick={startEdit}
              aria-label={`Edit ${label}`}
              className="compact-chip inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold border bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
            >
              <Edit3 className="h-3 w-3" aria-hidden="true" />
              <span>Edit</span>
            </button>
          )}
          {onVoiceCorrect && (
            <VoiceCorrectionControl
              fieldKey={fieldKey}
              fieldLabel={label}
              isActiveTarget={activeCorrectionField === fieldKey}
              onTriggerVoiceCorrection={onVoiceCorrect}
            />
          )}
        </div>
      </div>

      {editing && onVisualSave && (
        <form onSubmit={handleSave} className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200">
          {editType === 'visit_type' ? (
            <select
              value={editDraft}
              onChange={(e) => setEditDraft(e.target.value)}
              className="flex-1 min-w-[140px] px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs bg-white"
            >
              <option value="">Select visit type</option>
              <option value="ANC">ANC</option>
              <option value="PNC">PNC</option>
              <option value="Newborn">Newborn</option>
              <option value="Immunisation">Immunisation</option>
            </select>
          ) : (
            <input
              type={editType === 'number' ? 'number' : editType === 'date' ? 'date' : 'text'}
              step={editType === 'number' ? '0.1' : undefined}
              value={editDraft}
              onChange={(e) => setEditDraft(e.target.value)}
              className="flex-1 min-w-[140px] px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs bg-white"
            />
          )}
          <button
            type="submit"
            className="px-3 py-1.5 rounded-lg bg-clinical-primary text-white text-xs font-bold"
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => setEditing(false)}
            className="px-2.5 py-1.5 rounded-lg border border-slate-300 text-slate-600 text-xs font-semibold"
          >
            Cancel
          </button>
        </form>
      )}
    </div>
  );
};

export const FieldConfirmation: React.FC<{
  fieldKey: string;
  label: string;
  currentStatus: FieldConfirmStatus;
  onUpdateStatus: (fieldKey: string, status: FieldConfirmStatus) => void;
  onVoiceCorrect: (fieldKey: string) => void;
}> = ({ fieldKey, label, currentStatus, onUpdateStatus, onVoiceCorrect }) => (
  <div className="flex flex-wrap items-center gap-1.5 mt-2 pt-2 border-t border-slate-100">
    <button
      type="button"
      onClick={() => onUpdateStatus(fieldKey, 'confirmed')}
      className={`compact-chip inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold border ${
        currentStatus === 'confirmed'
          ? 'bg-emerald-600 text-white border-emerald-700'
          : 'bg-white text-emerald-800 border-emerald-300 hover:bg-emerald-50'
      }`}
    >
      <Check className="h-3 w-3" aria-hidden="true" />
      <span>Confirm {label}</span>
    </button>
    <button
      type="button"
      onClick={() => onVoiceCorrect(fieldKey)}
      className="compact-chip inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-white text-sky-800 border border-sky-300 hover:bg-sky-50"
    >
      <Mic className="h-3 w-3" aria-hidden="true" />
      <span>Correct by Voice</span>
    </button>
    <button
      type="button"
      onClick={() => onUpdateStatus(fieldKey, 'needs_clarification')}
      className={`compact-chip inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold border ${
        currentStatus === 'needs_clarification'
          ? 'bg-amber-600 text-white border-amber-700'
          : 'bg-white text-amber-800 border-amber-300 hover:bg-amber-50'
      }`}
    >
      <HelpCircle className="h-3 w-3" aria-hidden="true" />
      <span>Needs Clarification</span>
    </button>
  </div>
);

export const VisitSummaryCard: React.FC<{
  draft: VisitDraft;
  isTtsPlaying: boolean;
  isTtsPaused: boolean;
  requiresReReadBack?: boolean;
  summaryOutdated?: boolean;
  activeCorrectionField?: string | null;
  onPausePlayback: () => void;
  onResumePlayback: () => void;
  onVoiceCorrectField?: (fieldKey: string) => void;
  onVisualPatchFields?: (fields: Record<string, unknown>) => void;
  onRemoveObservation?: (key: string) => void;
  onRemoveEvent?: (name: string) => void;
  onSpeakToMakeChanges?: () => void;
}> = ({
  draft,
  isTtsPlaying,
  isTtsPaused,
  requiresReReadBack,
  summaryOutdated,
  activeCorrectionField,
  onPausePlayback,
  onResumePlayback,
  onVoiceCorrectField,
  onVisualPatchFields,
  onRemoveObservation,
  onRemoveEvent,
  onSpeakToMakeChanges,
}) => {
  const statuses = draft.field_statuses || {};
  const [addingNote, setAddingNote] = useState(false);
  const [newObsLabel, setNewObsLabel] = useState('');
  const [newObsValue, setNewObsValue] = useState('');

  const vaccineText =
    draft.vaccinations_due.length > 0 || draft.vaccinations_completed.length > 0
      ? [
          draft.vaccinations_completed.length > 0
            ? `Completed: ${draft.vaccinations_completed.join(', ')}`
            : '',
          draft.vaccinations_due.length > 0 ? `Due: ${draft.vaccinations_due.join(', ')}` : '',
        ]
          .filter(Boolean)
          .join(' · ')
      : null;

  const followUpText =
    draft.follow_up_actions.length > 0
      ? draft.follow_up_actions.map((a) => a.description).join('; ')
      : null;

  const handleFieldVisualSave = (fieldKey: string, nextValue: string) => {
    if (!onVisualPatchFields) return;
    if (fieldKey === 'weight_kg') {
      const parsed = parseFloat(nextValue);
      onVisualPatchFields({ weight_kg: Number.isFinite(parsed) && parsed > 0 ? parsed : null });
    } else if (fieldKey === 'next_visit_date') {
      onVisualPatchFields({ next_visit_date: nextValue.trim() || null });
    } else if (fieldKey === 'visit_type') {
      onVisualPatchFields({ visit_type: nextValue.trim() || null });
    } else if (fieldKey === 'beneficiary_id') {
      onVisualPatchFields({ beneficiary_id: nextValue.trim().toUpperCase() || null });
    } else if (fieldKey === 'vaccinations_due') {
      const items = nextValue
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      onVisualPatchFields({ vaccinations_due: items });
    }
  };

  return (
    <section
      aria-labelledby="review-card-heading"
      className="bg-white border-2 border-clinical-primary/30 rounded-2xl p-4 sm:p-6 shadow-sm space-y-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-200">
        <div>
          <h2 id="review-card-heading" className="text-base sm:text-lg font-bold text-clinical-text">
            Here&rsquo;s what I understood from your visit
          </h2>
          <p className="text-xs text-clinical-text-secondary">
            Editable until final submission · Speak or tap Edit on any field.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {onSpeakToMakeChanges && draft.status === 'draft' && (
            <button
              type="button"
              onClick={onSpeakToMakeChanges}
              className="compact-chip inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-sky-50 hover:bg-sky-100 border border-sky-300 text-sky-900 text-xs font-bold"
            >
              <Mic className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Speak to make changes</span>
            </button>
          )}
          <span
            className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${
              draft.status === 'committed'
                ? 'bg-emerald-100 text-emerald-900'
                : draft.status === 'confirmed'
                ? 'bg-sky-100 text-sky-900'
                : 'bg-amber-100 text-amber-900'
            }`}
          >
            {draft.status === 'draft' ? 'Unsubmitted Draft' : draft.status}
          </span>
        </div>
      </div>

      {/* Section A: Spoken Description */}
      <SpokenDescription
        transcriptSummary={draft.raw_transcript_summary}
        readBackSummary={summaryOutdated ? undefined : draft.read_back_summary}
        isTtsPlaying={isTtsPlaying}
        isTtsPaused={isTtsPaused}
        requiresReReadBack={requiresReReadBack || summaryOutdated}
        onPausePlayback={onPausePlayback}
        onResumePlayback={onResumePlayback}
      />

      {/* Section B: Captured Information */}
      <div className="space-y-2.5">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-600 block">
          B. Captured Information
        </span>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
          <CapturedField
            fieldKey="beneficiary_id"
            label="Beneficiary"
            value={
              draft.beneficiary_name && draft.beneficiary_id
                ? `${draft.beneficiary_name} (${draft.beneficiary_id})`
                : draft.beneficiary_id || draft.beneficiary_name
            }
            rawEditValue={draft.beneficiary_id || ''}
            status={statuses.beneficiary_id || (draft.beneficiary_id ? 'extracted' : 'needs_clarification')}
            onVoiceCorrect={onVoiceCorrectField}
            onVisualSave={onVisualPatchFields ? handleFieldVisualSave : undefined}
            activeCorrectionField={activeCorrectionField}
          />
          <CapturedField
            fieldKey="visit_type"
            label="Visit Type"
            value={draft.visit_type}
            rawEditValue={draft.visit_type || ''}
            editType="visit_type"
            status={statuses.visit_type || (draft.visit_type ? 'extracted' : 'needs_clarification')}
            onVoiceCorrect={onVoiceCorrectField}
            onVisualSave={onVisualPatchFields ? handleFieldVisualSave : undefined}
            activeCorrectionField={activeCorrectionField}
          />
          {(draft.weight_kg !== null || statuses.weight_kg === 'needs_clarification') && (
            <CapturedField
              fieldKey="weight_kg"
              label="Weight"
              value={draft.weight_kg !== null ? `${draft.weight_kg} kg` : null}
              rawEditValue={draft.weight_kg !== null ? String(draft.weight_kg) : ''}
              editType="number"
              sourcePhrase={draft.weight_source_text}
              status={statuses.weight_kg || (draft.weight_kg !== null ? 'extracted' : 'missing')}
              onVoiceCorrect={onVoiceCorrectField}
              onVisualSave={onVisualPatchFields ? handleFieldVisualSave : undefined}
              activeCorrectionField={activeCorrectionField}
            />
          )}
          {(vaccineText !== null || statuses.vaccinations_due === 'needs_clarification') && !(draft.events && draft.events.length > 0) && (
            <CapturedField
              fieldKey="vaccinations_due"
              label="Vaccinations / Immunisation"
              value={vaccineText}
              rawEditValue={draft.vaccinations_due.join(', ')}
              status={statuses.vaccinations_due || (vaccineText ? 'extracted' : 'missing')}
              onVoiceCorrect={onVoiceCorrectField}
              onVisualSave={onVisualPatchFields ? handleFieldVisualSave : undefined}
              activeCorrectionField={activeCorrectionField}
            />
          )}
          {(draft.next_visit_date !== null || statuses.next_visit_date === 'needs_clarification') && (
            <CapturedField
              fieldKey="next_visit_date"
              label="Next Visit Date"
              value={draft.next_visit_date}
              rawEditValue={draft.next_visit_date || ''}
              editType="date"
              sourcePhrase={draft.next_visit_date_source_text}
              status={statuses.next_visit_date || (draft.next_visit_date ? 'extracted' : 'missing')}
              onVoiceCorrect={onVoiceCorrectField}
              onVisualSave={onVisualPatchFields ? handleFieldVisualSave : undefined}
              activeCorrectionField={activeCorrectionField}
            />
          )}
          {followUpText !== null && (
            <CapturedField
              fieldKey="follow_up_actions"
              label="Follow-Up Action"
              value={followUpText}
              status={statuses.follow_up_actions || (followUpText ? 'extracted' : 'missing')}
              onVoiceCorrect={onVoiceCorrectField}
              activeCorrectionField={activeCorrectionField}
            />
          )}
        </div>

        {/* Dynamic Captured Clinical Observations (rendered only when captured or added) */}
        {draft.observations && draft.observations.length > 0 && (
          <div className="pt-2 space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600 block">
              Captured Clinical Observations ({draft.observations.length})
            </span>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {draft.observations.map((obs) => (
                <div
                  key={obs.key}
                  className={`p-3 rounded-xl border flex items-start justify-between gap-2 ${
                    obs.status === 'needs_confirmation'
                      ? 'bg-amber-50/70 border-amber-300'
                      : 'bg-slate-50/70 border-slate-200'
                  }`}
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-semibold text-slate-700">{obs.label}</span>
                      {obs.status === 'needs_confirmation' && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-200 text-amber-950">
                          Needs Confirmation
                        </span>
                      )}
                    </div>
                    <p className="text-sm font-bold text-clinical-text mt-0.5 break-words">
                      {String(obs.value ?? '')}
                      {obs.unit ? ` ${obs.unit}` : ''}
                    </p>
                    {obs.source_text && (
                      <p className="text-[11px] text-slate-500 mt-0.5 truncate">
                        Source: &ldquo;{obs.source_text}&rdquo;
                      </p>
                    )}
                  </div>
                  {onRemoveObservation && draft.status === 'draft' && (
                    <button
                      type="button"
                      onClick={() => onRemoveObservation(obs.key)}
                      aria-label={`Remove ${obs.label}`}
                      className="compact-chip p-1 rounded-lg text-slate-500 hover:text-red-700 hover:bg-red-50"
                    >
                      <X className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Repeatable Clinical & Immunisation Events */}
        {draft.events && draft.events.length > 0 && (
          <div className="pt-2 space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600 block">
              Recorded Events &amp; Vaccinations ({draft.events.length})
            </span>
            <div className="flex flex-wrap gap-2">
              {draft.events.map((ev) => (
                <div
                  key={`${ev.event_type}:${ev.name}`}
                  className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs ${
                    ev.status === 'completed'
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-950'
                      : 'bg-sky-50 border-sky-200 text-sky-950'
                  }`}
                >
                  <span className="font-bold">{ev.name}</span>
                  <span className="uppercase text-[10px] font-bold px-1.5 py-0.5 rounded bg-white/80 border border-current/15">
                    {ev.status}
                  </span>
                  {onVisualPatchFields && draft.status === 'draft' && (
                    <button
                      type="button"
                      onClick={() => {
                        const toggled = (draft.events || []).map((item) =>
                          item.name === ev.name && item.event_type === ev.event_type
                            ? { ...item, status: item.status === 'completed' ? 'due' : 'completed' }
                            : item
                        );
                        onVisualPatchFields({ events: toggled });
                      }}
                      className="compact-chip text-[11px] underline font-semibold hover:opacity-80"
                    >
                      {ev.status === 'completed' ? 'Mark Due' : 'Mark Given'}
                    </button>
                  )}
                  {onRemoveEvent && draft.status === 'draft' && (
                    <button
                      type="button"
                      onClick={() => onRemoveEvent(ev.name)}
                      aria-label={`Remove event ${ev.name}`}
                      className="compact-chip p-0.5 rounded text-slate-500 hover:text-red-700"
                    >
                      <X className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick add custom observation */}
        {onVisualPatchFields && draft.status === 'draft' && (
          <div className="pt-1">
            {!addingNote ? (
              <button
                type="button"
                onClick={() => setAddingNote(true)}
                className="compact-chip inline-flex items-center gap-1 text-xs font-semibold text-clinical-primary hover:underline"
              >
                <Edit3 className="h-3 w-3" aria-hidden="true" />
                <span>+ Add Observation / Note</span>
              </button>
            ) : (
              <div className="flex flex-wrap items-center gap-2 p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                <input
                  type="text"
                  value={newObsLabel}
                  onChange={(e) => setNewObsLabel(e.target.value)}
                  placeholder="Label (e.g. Feeding, BP)"
                  className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white flex-1 min-w-[130px]"
                />
                <input
                  type="text"
                  value={newObsValue}
                  onChange={(e) => setNewObsValue(e.target.value)}
                  placeholder="Observed value or note"
                  className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white flex-[2] min-w-[160px]"
                />
                <button
                  type="button"
                  onClick={() => {
                    if (!newObsLabel.trim() || !newObsValue.trim()) return;
                    const key = newObsLabel.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_');
                    const nextObs = [
                      ...(draft.observations || []).filter((o) => o.key !== key),
                      {
                        key,
                        label: newObsLabel.trim(),
                        value: newObsValue.trim(),
                        value_type: 'text' as const,
                        status: 'confirmed' as const,
                        source_text: `${newObsLabel.trim()}: ${newObsValue.trim()}`,
                      },
                    ];
                    onVisualPatchFields({ observations: nextObs });
                    setNewObsLabel('');
                    setNewObsValue('');
                    setAddingNote(false);
                  }}
                  className="compact-chip px-3 py-1.5 rounded-lg bg-clinical-primary text-white text-xs font-bold"
                >
                  Save Note
                </button>
                <button
                  type="button"
                  onClick={() => setAddingNote(false)}
                  className="compact-chip px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        )}

        {/* Danger Signs Summary Row */}
        <div
          className={`p-3 rounded-xl border flex items-center justify-between gap-2 ${
            draft.danger_sign_flagged
              ? 'bg-red-50 border-red-300 text-red-950'
              : 'bg-emerald-50/60 border-emerald-200 text-emerald-950'
          }`}
        >
          <div className="flex items-center gap-2">
            {draft.danger_sign_flagged ? (
              <AlertTriangle className="h-4 w-4 text-clinical-danger shrink-0" aria-hidden="true" />
            ) : (
              <CheckCircle2 className="h-4 w-4 text-clinical-success shrink-0" aria-hidden="true" />
            )}
            <span className="text-xs font-bold">
              Danger Signs:{' '}
              {draft.danger_sign_flagged
                ? draft.danger_signs.join(', ')
                : 'No danger sign flagged in speech'}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};

export const VisitConfirmationActions: React.FC<{
  draft: VisitDraft;
  isSaving: boolean;
  requiresReReadBack?: boolean;
  hasUnresolvedClarifications?: boolean;
  onAcceptAndSave: () => void;
  onRejectAndCorrect: () => void;
  onDiscardAndRerecord: () => void;
}> = ({
  draft,
  isSaving,
  requiresReReadBack,
  hasUnresolvedClarifications,
  onAcceptAndSave,
  onRejectAndCorrect,
  onDiscardAndRerecord,
}) => {
  const [confirmDiscardOpen, setConfirmDiscardOpen] = useState(false);
  const canConfirm = !!draft.beneficiary_id && !hasUnresolvedClarifications;

  return (
    <div className="bg-white border border-clinical-border-subtle rounded-2xl p-4 sm:p-5 shadow-sm space-y-3">
      {!canConfirm && (
        <div
          role="status"
          className="p-3 rounded-xl bg-amber-50 border border-amber-300 text-xs text-amber-950 font-semibold"
        >
          {!draft.beneficiary_id
            ? 'Beneficiary identity must be selected or resolved before saving.'
            : 'Resolve highlighted "Needs Clarification" fields before final save.'}
        </div>
      )}

      {requiresReReadBack && (
        <p className="text-xs text-amber-800 font-medium">
          A correction was applied — verify the updated value above before tapping Accept &amp; Save.
        </p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <button
          type="button"
          onClick={onAcceptAndSave}
          disabled={isSaving || !canConfirm}
          className="min-h-[56px] px-6 py-3.5 rounded-xl bg-clinical-primary hover:bg-clinical-primary-dark text-white font-bold text-base shadow-md transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {isSaving ? (
            <>
              <RefreshCw className="h-5 w-5 animate-spin" aria-hidden="true" />
              <span>Saving Visit...</span>
            </>
          ) : (
            <>
              <Check className="h-5 w-5" aria-hidden="true" />
              <span>✓ ACCEPT &amp; SAVE</span>
            </>
          )}
        </button>

        <button
          type="button"
          onClick={onRejectAndCorrect}
          disabled={isSaving}
          className="min-h-[56px] px-6 py-3.5 rounded-xl bg-white hover:bg-amber-50 border-2 border-amber-500 text-amber-950 font-bold text-base transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <X className="h-5 w-5 text-amber-700" aria-hidden="true" />
          <span>✕ REJECT / CORRECT BY VOICE</span>
        </button>
      </div>

      <div className="flex justify-center pt-1">
        <button
          type="button"
          onClick={() => setConfirmDiscardOpen(true)}
          disabled={isSaving}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-red-700 px-3 py-1.5 rounded-lg"
        >
          <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
          <span>Discard Draft &amp; Re-record Entire Visit</span>
        </button>
      </div>

      <NativeConfirmDialog
        open={confirmDiscardOpen}
        title="Discard current draft and re-record?"
        description="This clears the current unconfirmed draft fields so you can record a fresh household visit."
        confirmLabel="Discard & Re-record"
        destructive
        onCancel={() => setConfirmDiscardOpen(false)}
        onConfirm={() => {
          setConfirmDiscardOpen(false);
          onDiscardAndRerecord();
        }}
      />
    </div>
  );
};

export const VisitSuccess: React.FC<{
  savedVisit: VisitDraft;
  onStartAnother: () => void;
  onGoHome: () => void;
}> = ({ savedVisit, onStartAnother, onGoHome }) => {
  const isSynced = savedVisit.status === 'committed' && savedVisit.sync_status === 'synced';
  return (
    <section
      aria-live="polite"
      className="bg-white border-2 border-clinical-success rounded-2xl p-6 sm:p-8 text-center shadow-sm space-y-4"
    >
      <div className="w-14 h-14 rounded-full bg-emerald-100 text-clinical-success mx-auto flex items-center justify-center">
        <CheckCircle2 className="h-8 w-8" aria-hidden="true" />
      </div>

      <div>
        <span className="text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-emerald-100 text-emerald-900">
          {isSynced ? 'Visit Committed & Synced' : 'Confirmed — Queued Offline for Sync'}
        </span>
        <h2 className="text-xl sm:text-2xl font-bold text-clinical-text mt-3">
          Visit Saved for {savedVisit.beneficiary_name || savedVisit.beneficiary_id}
        </h2>
        <p className="text-xs sm:text-sm text-clinical-text-secondary mt-1">
          {isSynced
            ? `Persistence Reference: ${savedVisit.persistence_record_id || savedVisit.visit_id}`
            : 'Your confirmed visit is safely stored in IndexedDB and will sync automatically when online.'}
        </p>
      </div>

      <div className="max-w-md mx-auto bg-slate-50 rounded-xl p-4 border border-slate-200 text-left text-xs space-y-2">
        <div className="flex justify-between">
          <span className="text-slate-500">Visit ID:</span>
          <span className="font-mono font-bold text-clinical-text">{savedVisit.visit_id}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Visit Type:</span>
          <span className="font-bold text-clinical-text">{savedVisit.visit_type || 'General'}</span>
        </div>
        {savedVisit.weight_kg !== null && (
          <div className="flex justify-between">
            <span className="text-slate-500">Weight:</span>
            <span className="font-bold tabular-nums text-clinical-text">
              {savedVisit.weight_kg} kg
            </span>
          </div>
        )}
        {savedVisit.next_visit_date && (
          <div className="flex justify-between items-center pt-1 border-t border-slate-200">
            <span className="text-slate-600 inline-flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5 text-clinical-primary" aria-hidden="true" />
              Next Follow-up:
            </span>
            <span className="font-bold tabular-nums text-clinical-primary">
              {savedVisit.next_visit_date}
            </span>
          </div>
        )}
      </div>

      <div className="flex flex-col sm:flex-row justify-center gap-3 pt-2">
        <button
          type="button"
          onClick={onStartAnother}
          className="px-6 py-3 rounded-xl bg-clinical-primary hover:bg-clinical-primary-dark text-white font-bold text-sm"
        >
          Start Another Voice Visit
        </button>
        <button
          type="button"
          onClick={onGoHome}
          className="px-6 py-3 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-50 font-semibold text-sm"
        >
          Return to ASHA Home
        </button>
      </div>
    </section>
  );
};

