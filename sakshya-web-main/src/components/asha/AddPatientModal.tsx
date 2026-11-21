'use client';

import React, { useState } from 'react';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type { Beneficiary, BeneficiaryCategory, LanguageCode } from '@/types';
import { UserPlus, X } from 'lucide-react';

export interface NewPatientInput {
  full_name: string;
  category: BeneficiaryCategory;
  age_years: number;
  village: string;
  household_head?: string;
  phone_number?: string;
  edd_date?: string;
  high_risk_status: boolean;
  preferred_language: LanguageCode;
}

interface AddPatientModalProps {
  open: boolean;
  defaultLanguage: LanguageCode;
  onClose: () => void;
  onSave: (input: NewPatientInput) => Promise<Beneficiary>;
}

export const AddPatientModal: React.FC<AddPatientModalProps> = ({
  open,
  defaultLanguage,
  onClose,
  onSave,
}) => {
  const { ui } = useTranslation();
  const [fullName, setFullName] = useState('');
  const [category, setCategory] = useState<BeneficiaryCategory>('PREGNANT_WOMAN');
  const [ageYears, setAgeYears] = useState('24');
  const [village, setVillage] = useState('Rampur Demo Ward 1');
  const [householdHead, setHouseholdHead] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [eddDate, setEddDate] = useState('');
  const [highRisk, setHighRisk] = useState(false);
  const [preferredLang, setPreferredLang] = useState<LanguageCode>(
    defaultLanguage === 'indic-auto' ? 'hi-IN' : defaultLanguage
  );
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanName = fullName.trim();
    if (!cleanName) {
      setErrorMsg('Please enter the patient name.');
      return;
    }
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await onSave({
        full_name: cleanName,
        category,
        age_years: Math.max(0, Number.parseInt(ageYears || '0', 10) || 0),
        village: village.trim() || 'Rampur Demo Ward 1',
        household_head: householdHead.trim() || undefined,
        phone_number: phoneNumber.trim() || undefined,
        edd_date: category === 'PREGNANT_WOMAN' && eddDate ? eddDate : undefined,
        high_risk_status: highRisk,
        preferred_language: preferredLang,
      });
      setFullName('');
      setHouseholdHead('');
      setPhoneNumber('');
      setEddDate('');
      setHighRisk(false);
      onClose();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Could not save patient.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-patient-title"
      className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center p-4"
    >
      <div className="bg-white rounded-2xl max-w-lg w-full p-5 sm:p-6 shadow-2xl space-y-4 max-h-[92vh] overflow-y-auto">
        <div className="flex items-start justify-between gap-2 pb-3 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl bg-teal-50 text-clinical-primary flex items-center justify-center">
              <UserPlus className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 id="add-patient-title" className="text-lg font-bold text-clinical-text">
                {ui.addNewPatientTitle}
              </h2>
              <p className="text-xs text-slate-500">{ui.zeroPiiNote}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={ui.cancelLabel}
            className="p-2 rounded-lg text-slate-500 hover:bg-slate-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
          {errorMsg && (
            <div className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-red-800 font-semibold">
              {errorMsg}
            </div>
          )}

          <div>
            <label htmlFor="np-name" className="block font-bold text-slate-700 mb-1">
              {ui.patientNameLabel} *
            </label>
            <input
              id="np-name"
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Priya Devi"
              className="w-full px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label htmlFor="np-category" className="block font-bold text-slate-700 mb-1">
                {ui.patientCategoryLabel}
              </label>
              <select
                id="np-category"
                value={category}
                onChange={(e) => {
                  const next = e.target.value as BeneficiaryCategory;
                  setCategory(next);
                  if (next === 'INFANT') setAgeYears('0');
                  else if (ageYears === '0') setAgeYears('24');
                }}
                className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs font-semibold bg-white"
              >
                <option value="PREGNANT_WOMAN">{ui.ancFilter}</option>
                <option value="LACTATING_MOTHER">{ui.pncFilter}</option>
                <option value="INFANT">{ui.infantFilter}</option>
                <option value="CHILD">{ui.childFilter}</option>
              </select>
            </div>

            <div>
              <label htmlFor="np-age" className="block font-bold text-slate-700 mb-1">
                {ui.patientAgeLabel}
              </label>
              <input
                id="np-age"
                type="number"
                min={0}
                max={99}
                value={ageYears}
                onChange={(e) => setAgeYears(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label htmlFor="np-village" className="block font-bold text-slate-700 mb-1">
                {ui.villageWardLabel}
              </label>
              <input
                id="np-village"
                type="text"
                value={village}
                onChange={(e) => setVillage(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs bg-white"
              />
            </div>

            <div>
              <label htmlFor="np-lang" className="block font-bold text-slate-700 mb-1">
                {ui.languageLabel}
              </label>
              <select
                id="np-lang"
                value={preferredLang}
                onChange={(e) => setPreferredLang(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs font-semibold bg-white"
              >
                <option value="hi-IN">हिन्दी (Hindi)</option>
                <option value="ta-IN">தமிழ் (Tamil)</option>
                <option value="kn-IN">ಕನ್ನಡ (Kannada)</option>
                <option value="te-IN">తెలుగు (Telugu)</option>
                <option value="ml-IN">മലയാളം (Malayalam)</option>
                <option value="bn-IN">বাংলা (Bengali)</option>
                <option value="mr-IN">मराठी (Marathi)</option>
                <option value="gu-IN">ગુજરાતી (Gujarati)</option>
                <option value="pa-IN">ਪੰਜਾਬੀ (Punjabi)</option>
                <option value="en-IN">English (India)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label htmlFor="np-head" className="block font-bold text-slate-700 mb-1">
                {ui.householdHead}
              </label>
              <input
                id="np-head"
                type="text"
                value={householdHead}
                onChange={(e) => setHouseholdHead(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs bg-white"
              />
            </div>

            <div>
              <label htmlFor="np-phone" className="block font-bold text-slate-700 mb-1">
                {ui.phoneOptionalLabel}
              </label>
              <input
                id="np-phone"
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="98765-00000"
                className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs bg-white"
              />
            </div>
          </div>

          {category === 'PREGNANT_WOMAN' && (
            <div>
              <label htmlFor="np-edd" className="block font-bold text-slate-700 mb-1">
                {ui.eddLabel}
              </label>
              <input
                id="np-edd"
                type="date"
                value={eddDate}
                onChange={(e) => setEddDate(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs bg-white"
              />
            </div>
          )}

          <label className="flex items-center gap-2 pt-1 cursor-pointer">
            <input
              type="checkbox"
              checked={highRisk}
              onChange={(e) => setHighRisk(e.target.checked)}
              className="rounded border-slate-300 text-red-600"
            />
            <span className="font-semibold text-slate-700">{ui.highRiskPatientLabel}</span>
          </label>

          <div className="pt-3 border-t border-slate-200 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-slate-300 text-slate-700 font-bold hover:bg-slate-50"
            >
              {ui.cancelLabel}
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 rounded-xl bg-clinical-primary hover:bg-clinical-primary-dark text-white font-bold disabled:opacity-60"
            >
              {submitting ? ui.savingVisitBtn : ui.savePatientBtn}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

