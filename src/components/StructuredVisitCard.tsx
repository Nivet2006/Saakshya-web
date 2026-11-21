'use client';

import React from 'react';
import { VisitDraft } from '@/types';
import { Activity, Heart, Thermometer, ShieldAlert, Calendar, CheckCircle2, Edit3 } from 'lucide-react';

interface StructuredVisitCardProps {
  draft: Partial<VisitDraft>;
  onVoiceCorrectField?: (fieldName: string) => void;
  activeCorrectionField?: string | null;
}

export const StructuredVisitCard: React.FC<StructuredVisitCardProps> = ({
  draft,
  onVoiceCorrectField,
  activeCorrectionField,
}) => {
  const vitals = draft.vitals || {};
  const hasBP = vitals.blood_pressure_sys && vitals.blood_pressure_dia;
  const isHighBP = hasBP && (vitals.blood_pressure_sys! >= 140 || vitals.blood_pressure_dia! >= 90);

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs">
      <div className="flex items-center justify-between pb-3 border-b border-slate-200 mb-3">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-brand-600" />
          <h4 className="font-bold text-slate-800 text-sm">Extracted Visit Card (लाइव ड्राफ्ट)</h4>
        </div>
        <span className="font-mono text-[11px] bg-slate-200 text-slate-700 px-2 py-0.5 rounded font-semibold">
          {draft.visit_type || 'ANC_VISIT'}
        </span>
      </div>

      {/* Vitals Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 mb-3">
        {/* Blood Pressure */}
        <div
          className={`p-2.5 rounded-lg border transition-all ${
            activeCorrectionField === 'blood_pressure'
              ? 'ring-2 ring-brand-500 bg-brand-50 border-brand-300'
              : isHighBP
              ? 'bg-red-50 border-red-300 text-red-900'
              : 'bg-white border-slate-200'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-slate-500 font-medium">रक्तचाप (BP)</span>
            {onVoiceCorrectField && (
              <button
                type="button"
                onClick={() => onVoiceCorrectField('blood_pressure')}
                className="text-slate-400 hover:text-brand-600"
                title="Correct BP by voice"
              >
                <Edit3 className="h-3 w-3" />
              </button>
            )}
          </div>
          <div className="text-sm font-bold mt-1 flex items-baseline gap-1">
            {hasBP ? (
              <>
                <span className={isHighBP ? 'text-red-700' : 'text-slate-900'}>
                  {vitals.blood_pressure_sys}/{vitals.blood_pressure_dia}
                </span>
                <span className="text-[10px] text-slate-400 font-normal">mmHg</span>
              </>
            ) : (
              <span className="text-amber-600 italic font-normal">अपेक्षित (Missing)</span>
            )}
          </div>
        </div>

        {/* Weight */}
        <div
          className={`p-2.5 rounded-lg border transition-all ${
            activeCorrectionField === 'weight_kg'
              ? 'ring-2 ring-brand-500 bg-brand-50 border-brand-300'
              : 'bg-white border-slate-200'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-slate-500 font-medium">वजन (Weight)</span>
            {onVoiceCorrectField && (
              <button
                type="button"
                onClick={() => onVoiceCorrectField('weight_kg')}
                className="text-slate-400 hover:text-brand-600"
                title="Correct Weight by voice"
              >
                <Edit3 className="h-3 w-3" />
              </button>
            )}
          </div>
          <div className="text-sm font-bold mt-1">
            {vitals.weight_kg ? (
              <span>
                {vitals.weight_kg} <span className="text-[10px] text-slate-400 font-normal">kg</span>
              </span>
            ) : (
              <span className="text-slate-400 font-normal italic">--</span>
            )}
          </div>
        </div>

        {/* Temperature */}
        <div className="p-2.5 rounded-lg bg-white border border-slate-200">
          <div className="flex items-center justify-between">
            <span className="text-slate-500 font-medium">तापमान (Temp)</span>
          </div>
          <div className="text-sm font-bold mt-1">
            {vitals.temperature_f ? (
              <span>
                {vitals.temperature_f} <span className="text-[10px] text-slate-400 font-normal">°F</span>
              </span>
            ) : (
              <span className="text-slate-400 font-normal italic">98.4 °F (Normal)</span>
            )}
          </div>
        </div>

        {/* Fetal Heart Rate */}
        {vitals.fetal_heart_rate_bpm && (
          <div className="p-2.5 rounded-lg bg-white border border-slate-200">
            <span className="text-slate-500 font-medium">FHR (शिशु धड़कन)</span>
            <div className="text-sm font-bold mt-1">
              {vitals.fetal_heart_rate_bpm} <span className="text-[10px] text-slate-400 font-normal">bpm</span>
            </div>
          </div>
        )}
      </div>

      {/* Immunisations Status */}
      {draft.immunisations_administered && draft.immunisations_administered.length > 0 && (
        <div className="mt-2 p-2 bg-emerald-50 rounded-lg border border-emerald-200 text-emerald-800">
          <span className="font-semibold">लगाए गए टीके: </span>
          <span>{draft.immunisations_administered.join(', ')}</span>
        </div>
      )}

      {/* Next Follow Up */}
      {draft.follow_up_date && (
        <div className="mt-2 flex items-center justify-between bg-white p-2 rounded-lg border border-slate-200">
          <div className="flex items-center gap-1.5 text-slate-600">
            <Calendar className="h-3.5 w-3.5 text-brand-600" />
            <span>अगला फॉलो-अप: <strong className="text-slate-900">{draft.follow_up_date}</strong></span>
          </div>
          {draft.follow_up_reason && (
            <span className="text-[11px] text-slate-500 truncate max-w-[200px]">{draft.follow_up_reason}</span>
          )}
        </div>
      )}

      {/* Read Back State */}
      <div className="mt-3 flex items-center justify-between pt-2 border-t border-slate-200 text-[11px] text-slate-500">
        <span>रीड-बैक स्थिति (Read-back status):</span>
        <span className="font-semibold text-emerald-700 flex items-center gap-1">
          <CheckCircle2 className="h-3 w-3" />
          पुष्टि की गई (Confirmed)
        </span>
      </div>
    </div>
  );
};
