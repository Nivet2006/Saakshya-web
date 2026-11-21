'use client';

import React, { useState } from 'react';
import {
  assessClinicalRisk,
  getRiskColorClasses,
  type RiskLevel,
  type StructuredClinicalData,
} from '@/utils/riskEngine';
import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Info,
  ShieldCheck,
} from 'lucide-react';

interface ClinicalRiskBadgeProps {
  structured?: StructuredClinicalData;
  patientType?: string;
  compact?: boolean;
}

export const ClinicalRiskBadge: React.FC<ClinicalRiskBadgeProps> = ({
  structured = {},
  patientType = 'general',
  compact = false,
}) => {
  const [expanded, setExpanded] = useState(false);
  const assessment = assessClinicalRisk(structured, patientType);
  const { risk, category, rulesMatched, rationale, recommendedAction, factors } = assessment;
  const colors = getRiskColorClasses(risk);

  const riskIcons: Record<RiskLevel, React.ReactNode> = {
    Critical: <AlertOctagon className="h-4 w-4 text-white animate-pulse" aria-hidden="true" />,
    High: <AlertTriangle className="h-4 w-4 text-white" aria-hidden="true" />,
    Medium: <Info className="h-4 w-4 text-white" aria-hidden="true" />,
    Low: <CheckCircle2 className="h-4 w-4 text-white" aria-hidden="true" />,
  };

  const categoryLabels: Record<string, string> = {
    pregnant: 'Pregnant Mother (ANC / PNC)',
    child: 'Child (Newborn / Infant)',
    elder: 'Elderly Patient',
    adult: 'Adult / General Patient',
  };

  if (compact) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold border ${colors.badgeBg} ${colors.badgeText} ${colors.badgeBorder} shadow-sm`}
        title={`Clinical Risk: ${risk} (${categoryLabels[category] || category})`}
      >
        {riskIcons[risk]}
        <span>Risk: {risk}</span>
      </span>
    );
  }

  return (
    <div
      className={`rounded-2xl border p-4 sm:p-5 transition-all shadow-sm ${colors.bgLight} ${colors.cardBorder}`}
    >
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <div
            className={`p-2 rounded-xl flex items-center justify-center ${colors.badgeBg} shadow-sm`}
          >
            {riskIcons[risk]}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={`text-xs font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full ${colors.badgeBg} ${colors.badgeText}`}
              >
                Clinical Risk: {risk}
              </span>
              <span className="text-[11px] font-bold text-slate-600 bg-white/80 px-2 py-0.5 rounded border border-slate-200">
                {categoryLabels[category] || category}
              </span>
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-800 bg-emerald-100/80 px-2 py-0.5 rounded border border-emerald-200">
                <ShieldCheck className="h-3 w-3" />
                <span>Deterministic Rule Engine</span>
              </span>
            </div>
            <p className="text-xs text-slate-700 mt-1 font-medium">
              {recommendedAction}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-1 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white/80 hover:bg-white px-2.5 py-1 rounded-lg border border-slate-200 transition-colors"
        >
          <span>{expanded ? 'Hide Rationale' : 'Explain Risk'}</span>
          {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </button>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-slate-200/80 space-y-2 text-xs">
          {rulesMatched.length > 0 && (
            <div>
              <span className="font-bold text-slate-800 block mb-0.5">Rules Fired:</span>
              <ul className="list-disc list-inside space-y-0.5 text-slate-700 font-medium">
                {rulesMatched.map((rule, idx) => (
                  <li key={idx}>{rule}</li>
                ))}
              </ul>
            </div>
          )}

          {rationale.length > 0 && (
            <div>
              <span className="font-bold text-slate-800 block mb-0.5">Clinical Rationale (NHM Guidelines):</span>
              <ul className="list-disc list-inside space-y-0.5 text-slate-600">
                {rationale.map((rat, idx) => (
                  <li key={idx}>{rat}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="pt-1 flex items-center gap-2 flex-wrap text-[11px] text-slate-500">
            <span>Evaluated factors:</span>
            {factors.hasBleeding && (
              <span className="px-1.5 py-0.5 rounded bg-red-100 text-red-800 font-bold">Bleeding</span>
            )}
            {factors.hasHighBP && (
              <span className="px-1.5 py-0.5 rounded bg-orange-100 text-orange-800 font-bold">High BP</span>
            )}
            {factors.hasSwelling && (
              <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-bold">Swelling</span>
            )}
            {factors.hasBreathingIssue && (
              <span className="px-1.5 py-0.5 rounded bg-orange-100 text-orange-800 font-bold">Breathing Issue</span>
            )}
            {factors.feverDays !== null && (
              <span className="px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-800 font-bold">
                Fever: {factors.feverDays}d
              </span>
            )}
            {!factors.hasBleeding &&
              !factors.hasHighBP &&
              !factors.hasSwelling &&
              !factors.hasBreathingIssue &&
              factors.feverDays === null && (
                <span className="text-slate-400 italic">No acute symptom thresholds reached</span>
              )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ClinicalRiskBadge;
