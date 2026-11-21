'use client';

import React from 'react';
import { Beneficiary, LanguageCode } from '@/types';
import { TRANSLATIONS } from '@/lib/translations';
import { User, Calendar, MapPin, AlertCircle, Phone, ArrowRight } from 'lucide-react';

interface BeneficiaryCardProps {
  beneficiary: Beneficiary;
  onStartVisit: (beneficiary: Beneficiary) => void;
  language?: LanguageCode;
}

export const BeneficiaryCard: React.FC<BeneficiaryCardProps> = ({
  beneficiary,
  onStartVisit,
  language = 'hi-IN',
}) => {
  const t = TRANSLATIONS[language] || TRANSLATIONS['hi-IN'];
  const isPregnant = beneficiary.category === 'PREGNANT_WOMAN';
  const isInfant = beneficiary.category === 'INFANT' || beneficiary.category === 'CHILD';

  return (
    <div
      className={`bg-white rounded-xl border p-4 shadow-sm hover:shadow-md transition-shadow ${
        beneficiary.high_risk_status ? 'border-red-300 ring-1 ring-red-100' : 'border-slate-200'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${
              beneficiary.high_risk_status
                ? 'bg-red-100 text-red-700'
                : 'bg-brand-100 text-brand-700'
            }`}
          >
            {beneficiary.full_name.charAt(0)}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-slate-900 text-base">{beneficiary.full_name}</h3>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold">
                {beneficiary.beneficiary_id}
              </span>
            </div>
            <p className="text-xs text-slate-500 flex items-center gap-1.5 mt-0.5">
              <span>{beneficiary.age_years > 0 ? `${beneficiary.age_years} ${t.yrs}` : t.infantLabel}</span>
              <span>·</span>
              <span className="capitalize">{beneficiary.category.toLowerCase().replace(/_/g, ' ')}</span>
            </p>
          </div>
        </div>

        {beneficiary.high_risk_status && (
          <span className="inline-flex items-center gap-1 bg-red-100 text-red-800 text-[11px] font-bold px-2 py-0.5 rounded-full">
            <AlertCircle className="h-3 w-3 text-red-600" />
            {t.highRisk}
          </span>
        )}
      </div>

      <div className="mt-3 pt-3 border-t border-slate-100 grid grid-cols-2 gap-2 text-xs text-slate-600">
        <div className="flex items-center gap-1.5">
          <MapPin className="h-3.5 w-3.5 text-slate-400" />
          <span className="truncate">{beneficiary.village}</span>
        </div>
        {beneficiary.phone_number && (
          <div className="flex items-center gap-1.5">
            <Phone className="h-3.5 w-3.5 text-slate-400" />
            <span>{beneficiary.phone_number}</span>
          </div>
        )}
        {isPregnant && beneficiary.edd_date && (
          <div className="col-span-2 flex items-center gap-1.5 text-brand-700 font-medium">
            <Calendar className="h-3.5 w-3.5 text-brand-600" />
            <span>{t.edd}: {beneficiary.edd_date}</span>
          </div>
        )}
      </div>

      {beneficiary.high_risk_reasons && beneficiary.high_risk_reasons.length > 0 && (
        <div className="mt-2 text-[11px] bg-red-50 text-red-700 p-1.5 rounded font-medium">
          {beneficiary.high_risk_reasons.join(', ')}
        </div>
      )}

      <div className="mt-3">
        <button
          onClick={() => onStartVisit(beneficiary)}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-brand-50 hover:bg-brand-100 text-brand-800 font-semibold text-xs transition-colors border border-brand-200"
        >
          <span>{t.recordVoiceVisit}</span>
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
};
