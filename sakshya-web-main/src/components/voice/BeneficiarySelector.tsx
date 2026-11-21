'use client';

import React, { useMemo, useState } from 'react';
import { AddPatientModal, type NewPatientInput } from '@/components/asha/AddPatientModal';
import type { ClarificationCandidateV1 } from '@/lib/contracts/v1';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type { Beneficiary, LanguageCode } from '@/types';
import { AlertCircle, CheckCircle2, MapPin, Search, UserCheck, UserPlus, Users } from 'lucide-react';

interface BeneficiarySelectorProps {
  beneficiaries: Beneficiary[];
  selectedBeneficiary: Beneficiary | null;
  recentBeneficiaryIds?: string[];
  onSelect: (beneficiary: Beneficiary | null) => void;
  onAddBeneficiary?: (input: NewPatientInput) => Promise<Beneficiary>;
  currentLanguage?: LanguageCode;
  ambiguousCandidates?: ClarificationCandidateV1[];
  onSelectCandidate?: (candidate: ClarificationCandidateV1) => void;
  disabled?: boolean;
}

export const BeneficiarySelector: React.FC<BeneficiarySelectorProps> = ({
  beneficiaries,
  selectedBeneficiary,
  recentBeneficiaryIds = [],
  onSelect,
  onAddBeneficiary,
  currentLanguage = 'hi-IN',
  ambiguousCandidates,
  onSelectCandidate,
  disabled = false,
}) => {
  const { ui } = useTranslation();
  const [query, setQuery] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return beneficiaries;
    return beneficiaries.filter(
      (b) =>
        b.full_name.toLowerCase().includes(q) ||
        b.beneficiary_id.toLowerCase().includes(q) ||
        b.village.toLowerCase().includes(q)
    );
  }, [beneficiaries, query]);

  const recentList = useMemo(() => {
    if (!recentBeneficiaryIds.length) return beneficiaries.slice(0, 3);
    const matches = recentBeneficiaryIds
      .map((id) => beneficiaries.find((b) => b.beneficiary_id === id))
      .filter((b): b is Beneficiary => !!b);
    return matches.length > 0 ? matches : beneficiaries.slice(0, 3);
  }, [beneficiaries, recentBeneficiaryIds]);

  const formatCategory = (cat: Beneficiary['category']): string => {
    switch (cat) {
      case 'PREGNANT_WOMAN':
        return ui.categoryAncBeneficiary;
      case 'LACTATING_MOTHER':
        return ui.categoryPncMother;
      case 'INFANT':
        return ui.categoryNewbornInfant;
      case 'CHILD':
        return ui.categoryChild;
      default:
        return ui.categoryBeneficiary;
    }
  };

  return (
    <section
      aria-labelledby="beneficiary-step-heading"
      className="bg-white border border-clinical-border-subtle rounded-xl p-4 sm:p-5 shadow-sm"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
        <div>
          <h2 id="beneficiary-step-heading" className="text-base font-bold text-clinical-text">
            {ui.step1Title}
          </h2>
          <p className="text-xs text-clinical-text-secondary">
            {ui.step1Subtitle}
          </p>
        </div>

        <div className="flex items-center gap-3 self-start sm:self-auto">
          {onAddBeneficiary && !disabled && (
            <button
              type="button"
              onClick={() => setShowAddModal(true)}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-teal-50 border border-teal-200 text-clinical-primary hover:bg-teal-100 text-xs font-bold"
            >
              <UserPlus className="h-3.5 w-3.5" aria-hidden="true" />
              <span>{ui.addNewPatientBtn}</span>
            </button>
          )}
          {selectedBeneficiary && (
            <button
              type="button"
              disabled={disabled}
              onClick={() => onSelect(null)}
              className="text-xs font-semibold text-clinical-secondary hover:underline disabled:opacity-50"
            >
              {ui.changeBeneficiary}
            </button>
          )}
        </div>
      </div>

      {/* Ambiguous Beneficiary Clarification Prompt from Agent 1 */}
      {ambiguousCandidates && ambiguousCandidates.length > 0 && onSelectCandidate && (
        <div
          role="alert"
          className="mb-4 p-3.5 rounded-xl bg-amber-50 border-2 border-amber-400 text-amber-950"
        >
          <p className="text-xs font-bold flex items-center gap-1.5">
            <AlertCircle className="h-4 w-4 text-amber-700 shrink-0" aria-hidden="true" />
            <span>{ui.multipleBeneficiaryMatch}</span>
          </p>
          <div className="mt-2.5 flex flex-wrap gap-2">
            {ambiguousCandidates.map((cand) => (
              <button
                key={cand.id}
                type="button"
                onClick={() => onSelectCandidate(cand)}
                className="px-3.5 py-2 rounded-lg bg-white border border-amber-400 hover:bg-amber-100 text-xs font-bold text-amber-950 shadow-sm"
              >
                {cand.label} ({cand.id}){cand.detail ? ` · ${cand.detail}` : ''}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Selected Compact Beneficiary Card */}
      {selectedBeneficiary ? (
        <div className="p-3.5 rounded-xl bg-teal-50/70 border-2 border-clinical-primary flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-full bg-clinical-primary text-white flex items-center justify-center font-bold text-sm shrink-0">
              <UserCheck className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-bold text-clinical-text text-sm sm:text-base">
                  {selectedBeneficiary.full_name}
                </span>
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-white border border-teal-200 text-clinical-primary-dark">
                  {selectedBeneficiary.beneficiary_id}
                </span>
              </div>
              <p className="text-xs text-clinical-text-secondary mt-0.5 flex items-center gap-2 flex-wrap">
                <span>{formatCategory(selectedBeneficiary.category)}</span>
                <span>·</span>
                <span className="inline-flex items-center gap-1">
                  <MapPin className="h-3 w-3" aria-hidden="true" />
                  {selectedBeneficiary.village}
                </span>
              </p>
            </div>
          </div>
          <CheckCircle2 className="h-5 w-5 text-clinical-primary shrink-0" aria-hidden="true" />
        </div>
      ) : (
        <div className="space-y-3">
          {/* Search Input */}
          <div className="relative">
            <Search
              className="h-4 w-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none"
              aria-hidden="true"
            />
            <label htmlFor="beneficiary-search-input" className="sr-only">
              Search beneficiary by name, ID, or village
            </label>
            <input
              id="beneficiary-search-input"
              type="search"
              disabled={disabled}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={ui.searchDirectoryPlaceholder}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-clinical-border bg-slate-50 focus:bg-white text-sm"
            />
          </div>

          {/* Recently Visited Quick Chips */}
          {!query && recentList.length > 0 && (
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1">
                <Users className="h-3.5 w-3.5" aria-hidden="true" />
                <span>{ui.quickSelectRecent}</span>
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {recentList.map((ben) => (
                  <button
                    key={ben.beneficiary_id}
                    type="button"
                    disabled={disabled}
                    onClick={() => onSelect(ben)}
                    className="text-left p-2.5 rounded-xl border border-slate-200 hover:border-clinical-primary hover:bg-teal-50/40 transition-colors"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-xs text-clinical-text truncate">
                        {ben.full_name}
                      </span>
                      <span className="font-mono text-[10px] font-semibold bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
                        {ben.beneficiary_id}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5 truncate">
                      {formatCategory(ben.category)} · {ben.village}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Full Directory Selectable Cards */}
          <div className="max-h-56 overflow-y-auto space-y-1.5 pr-1">
            {filtered.map((ben) => (
              <button
                key={ben.beneficiary_id}
                type="button"
                disabled={disabled}
                onClick={() => onSelect(ben)}
                className="w-full text-left p-3 rounded-xl border border-slate-200 hover:border-clinical-primary hover:bg-teal-50/30 transition-colors flex items-center justify-between gap-3"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-clinical-text truncate">
                      {ben.full_name}
                    </span>
                    {ben.high_risk_status && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-800">
                        High Risk
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {formatCategory(ben.category)} · {ben.village}
                  </p>
                </div>
                <span className="font-mono text-xs font-bold text-clinical-primary bg-teal-50 px-2.5 py-1 rounded-lg border border-teal-200 shrink-0">
                  {ben.beneficiary_id}
                </span>
              </button>
            ))}

            {filtered.length === 0 && (
              <p className="text-xs text-slate-500 text-center py-4">
                No matching beneficiary in synthetic directory. You can still start speaking and say
                the name.
              </p>
            )}
          </div>
        </div>
      )}
      {onAddBeneficiary && (
        <AddPatientModal
          open={showAddModal}
          defaultLanguage={currentLanguage}
          onClose={() => setShowAddModal(false)}
          onSave={async (input) => {
            const created = await onAddBeneficiary(input);
            onSelect(created);
            return created;
          }}
        />
      )}
    </section>
  );
};

