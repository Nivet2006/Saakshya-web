'use client';

import React, { useMemo, useState } from 'react';
import { AddPatientModal, type NewPatientInput } from '@/components/asha/AddPatientModal';
import { EmptyState } from '@/components/ui/ClinicalUI';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type {
  Beneficiary,
  FollowUpTask,
  ImmunisationScheduleItem,
  LanguageCode,
  VisitDraft,
} from '@/types';
import {
  AlertCircle,
  Calendar,
  MapPin,
  Mic,
  Phone,
  Search,
  Syringe,
  User,
  UserPlus,
  X,
} from 'lucide-react';

interface BeneficiaryDirectoryViewProps {
  beneficiaries: Beneficiary[];
  visits: VisitDraft[];
  followUps: FollowUpTask[];
  immunisations: ImmunisationScheduleItem[];
  onStartVoiceVisit: (beneficiary: Beneficiary) => void;
  onAddBeneficiary?: (input: NewPatientInput) => Promise<Beneficiary>;
  currentLanguage?: LanguageCode;
}

export const BeneficiaryDirectoryView: React.FC<BeneficiaryDirectoryViewProps> = ({
  beneficiaries,
  visits,
  followUps,
  immunisations,
  onStartVoiceVisit,
  onAddBeneficiary,
  currentLanguage = 'hi-IN',
}) => {
  const { ui } = useTranslation();
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [selectedProfile, setSelectedProfile] = useState<Beneficiary | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return beneficiaries.filter((b) => {
      const matchQuery =
        !q ||
        b.full_name.toLowerCase().includes(q) ||
        b.beneficiary_id.toLowerCase().includes(q) ||
        b.village.toLowerCase().includes(q);
      if (!matchQuery) return false;
      if (categoryFilter === 'HIGH_RISK') return b.high_risk_status;
      if (categoryFilter !== 'ALL' && b.category !== categoryFilter) return false;
      return true;
    });
  }, [beneficiaries, search, categoryFilter]);

  const profileVisits = useMemo(() => {
    if (!selectedProfile) return [];
    return visits.filter(
      (v) =>
        v.beneficiary_id === selectedProfile.beneficiary_id ||
        v.beneficiary_uuid === selectedProfile.id
    );
  }, [selectedProfile, visits]);

  const profileFollowUps = useMemo(() => {
    if (!selectedProfile) return [];
    return followUps.filter(
      (f) =>
        f.beneficiary_id === selectedProfile.beneficiary_id ||
        f.beneficiary_uuid === selectedProfile.id
    );
  }, [selectedProfile, followUps]);

  const profileImmunisations = useMemo(() => {
    if (!selectedProfile) return [];
    return immunisations.filter(
      (i) =>
        i.beneficiary_id === selectedProfile.beneficiary_id ||
        i.beneficiary_uuid === selectedProfile.id
    );
  }, [selectedProfile, immunisations]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-clinical-text">
            {ui.beneficiaryDirectoryTitle}
          </h1>
          <p className="text-xs sm:text-sm text-clinical-text-secondary">
            {ui.beneficiaryDirectorySubtitle}
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 w-full sm:w-auto">
          <div className="relative w-full sm:w-72">
            <Search
              className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
              aria-hidden="true"
            />
            <label htmlFor="directory-search" className="sr-only">
              {ui.searchBeneficiariesPlaceholder}
            </label>
            <input
              id="directory-search"
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={ui.searchBeneficiariesPlaceholder}
              className="w-full pl-9 pr-3 py-2 rounded-xl border border-clinical-border bg-white text-sm"
            />
          </div>
          {onAddBeneficiary && (
            <button
              type="button"
              onClick={() => setShowAddModal(true)}
              className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-clinical-primary hover:bg-clinical-primary-dark text-white text-xs font-bold shadow-sm whitespace-nowrap"
            >
              <UserPlus className="h-4 w-4" aria-hidden="true" />
              <span>{ui.addNewPatientBtn}</span>
            </button>
          )}
        </div>
      </div>

      {/* Category Filter Chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {[
          { id: 'ALL', label: ui.allBeneficiaries },
          { id: 'HIGH_RISK', label: ui.highRiskWatch },
          { id: 'PREGNANT_WOMAN', label: ui.ancFilter },
          { id: 'LACTATING_MOTHER', label: ui.pncFilter },
          { id: 'INFANT', label: ui.infantFilter },
          { id: 'CHILD', label: ui.childFilter },
        ].map((chip) => (
          <button
            key={chip.id}
            type="button"
            onClick={() => setCategoryFilter(chip.id)}
            className={`compact-chip px-3.5 py-1.5 rounded-full text-xs font-semibold border whitespace-nowrap ${
              categoryFilter === chip.id
                ? 'bg-clinical-primary text-white border-clinical-primary'
                : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
            }`}
          >
            {chip.label}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title={ui.noMatchingBeneficiaries}
          description={ui.noMatchingBeneficiariesDesc}
          icon={<User className="h-5 w-5" />}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((ben) => (
            <article
              key={ben.beneficiary_id}
              className={`bg-white rounded-2xl border p-4 shadow-sm flex flex-col justify-between gap-3 ${
                ben.high_risk_status ? 'border-red-300' : 'border-clinical-border-subtle'
              }`}
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h2 className="font-bold text-base text-clinical-text">{ben.full_name}</h2>
                    <span className="inline-block mt-1 font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                      {ben.beneficiary_id}
                    </span>
                  </div>
                  {ben.high_risk_status && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-800">
                      <AlertCircle className="h-3 w-3" aria-hidden="true" />
                      {ui.highRisk}
                    </span>
                  )}
                </div>

                <div className="mt-3 space-y-1.5 text-xs text-slate-600">
                  <p className="capitalize">
                    {ben.category.toLowerCase().replace(/_/g, ' ')} ·{' '}
                    {ben.age_years > 0 ? `${ben.age_years} ${ui.yrsLabel}` : ui.infantNewborn}
                  </p>
                  <p className="flex items-center gap-1.5">
                    <MapPin className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
                    <span>{ben.village}</span>
                  </p>
                  {ben.edd_date && (
                    <p className="flex items-center gap-1.5 text-clinical-primary font-semibold">
                      <Calendar className="h-3.5 w-3.5" aria-hidden="true" />
                      <span className="tabular-nums">{ui.eddLabel}: {ben.edd_date}</span>
                    </p>
                  )}
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedProfile(ben)}
                  className="flex-1 py-2 px-3 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-50 text-xs font-bold"
                >
                  {ui.viewProfile}
                </button>
                <button
                  type="button"
                  onClick={() => onStartVoiceVisit(ben)}
                  className="flex-1 py-2 px-3 rounded-xl bg-clinical-primary hover:bg-clinical-primary-dark text-white text-xs font-bold flex items-center justify-center gap-1.5"
                >
                  <Mic className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>{ui.voiceVisitButton}</span>
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Beneficiary Profile Detail Slide-over Panel */}
      {selectedProfile && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="profile-drawer-title"
          className="fixed inset-0 z-50 bg-slate-900/50 flex justify-end"
        >
          <div className="bg-white w-full max-w-lg h-full overflow-y-auto p-5 sm:p-6 shadow-2xl space-y-5">
            <div className="flex items-start justify-between gap-3 pb-4 border-b border-slate-200">
              <div>
                <span className="font-mono text-xs font-bold text-clinical-primary bg-teal-50 px-2 py-0.5 rounded">
                  {selectedProfile.beneficiary_id}
                </span>
                <h2 id="profile-drawer-title" className="text-xl font-bold text-clinical-text mt-1">
                  {selectedProfile.full_name}
                </h2>
                <p className="text-xs text-slate-600 mt-0.5">
                  {selectedProfile.village} · {ui.householdHead}: {selectedProfile.household_head || '—'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedProfile(null)}
                aria-label={ui.cancelLabel}
                className="p-2 rounded-lg text-slate-500 hover:bg-slate-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {selectedProfile.phone_number && (
              <div className="flex items-center gap-2 text-xs text-slate-700">
                <Phone className="h-4 w-4 text-slate-400" aria-hidden="true" />
                <span className="tabular-nums">{selectedProfile.phone_number}</span>
                {selectedProfile.rch_id && (
                  <>
                    <span>·</span>
                    <span className="font-mono">RCH: {selectedProfile.rch_id}</span>
                  </>
                )}
              </div>
            )}

            {/* Visit History */}
            <section>
              <h3 className="text-sm font-bold text-clinical-text mb-2">
                {ui.visitHistoryTitle} ({profileVisits.length})
              </h3>
              {profileVisits.length === 0 ? (
                <p className="text-xs text-slate-500 italic">{ui.noRecordedVisitsYet}</p>
              ) : (
                <ul className="space-y-2">
                  {profileVisits.map((v) => (
                    <li
                      key={v.visit_id || v.draft_id}
                      className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1"
                    >
                      <div className="flex justify-between font-bold">
                        <span>{v.visit_type || ui.visitTypeLabel}</span>
                        <span className="tabular-nums text-slate-500">
                          {new Date(v.visit_date).toLocaleDateString()}
                        </span>
                      </div>
                      {v.weight_kg !== null && <p>{ui.weightLabel}: {v.weight_kg} kg</p>}
                      {v.raw_transcript_summary && (
                        <p className="text-slate-600">{v.raw_transcript_summary}</p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {/* Immunisation Records */}
            <section>
              <h3 className="text-sm font-bold text-clinical-text mb-2 flex items-center gap-1.5">
                <Syringe className="h-4 w-4 text-clinical-primary" aria-hidden="true" />
                <span>{ui.immunisationRecordsTitle} ({profileImmunisations.length})</span>
              </h3>
              {profileImmunisations.length === 0 ? (
                <p className="text-xs text-slate-500 italic">{ui.noScheduledVaccines}</p>
              ) : (
                <ul className="space-y-2">
                  {profileImmunisations.map((im) => (
                    <li
                      key={im.id}
                      className="p-2.5 rounded-xl border border-slate-200 flex items-center justify-between text-xs"
                    >
                      <div>
                        <span className="font-bold text-clinical-text">
                          {im.vaccine_name} (Dose {im.dose_number})
                        </span>
                        <span className="block text-slate-500 tabular-nums">{ui.dueLabel}: {im.due_date}</span>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                          im.status === 'GIVEN'
                            ? 'bg-emerald-100 text-emerald-800'
                            : im.status === 'OVERDUE'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {im.status}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {/* Pending Follow-ups */}
            <section>
              <h3 className="text-sm font-bold text-clinical-text mb-2">
                {ui.followUpsHeading} ({profileFollowUps.length})
              </h3>
              {profileFollowUps.length === 0 ? (
                <p className="text-xs text-slate-500 italic">{ui.noFollowUpsRecorded}</p>
              ) : (
                <ul className="space-y-2">
                  {profileFollowUps.map((f) => (
                    <li
                      key={f.id}
                      className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs flex justify-between gap-2"
                    >
                      <div>
                        <p className="font-bold text-clinical-text">{f.task_type}</p>
                        <p className="text-slate-500 tabular-nums">{ui.dueLabel}: {f.due_date}</p>
                      </div>
                      <span className="font-bold text-[11px]">{f.status}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <button
              type="button"
              onClick={() => {
                const target = selectedProfile;
                setSelectedProfile(null);
                onStartVoiceVisit(target);
              }}
              className="w-full py-3.5 rounded-xl bg-clinical-primary hover:bg-clinical-primary-dark text-white font-bold text-sm flex items-center justify-center gap-2"
            >
              <Mic className="h-4 w-4" aria-hidden="true" />
              <span>{ui.startVoiceVisit} · {selectedProfile.full_name}</span>
            </button>
          </div>
        </div>
      )}
      {onAddBeneficiary && (
        <AddPatientModal
          open={showAddModal}
          defaultLanguage={currentLanguage}
          onClose={() => setShowAddModal(false)}
          onSave={onAddBeneficiary}
        />
      )}
    </div>
  );
};

