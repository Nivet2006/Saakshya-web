'use client';

import React from 'react';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type { DangerAlert, LanguageCode } from '@/types';
import {
  AlertTriangle,
  BookOpen,
  Building2,
  CheckCircle2,
  PhoneCall,
  ShieldAlert,
} from 'lucide-react';

interface DangerAlertBannerProps {
  alert: DangerAlert;
  onAcknowledge?: (alertId: string) => void;
  onUpdateStatus?: (alertId: string, nextStatus: DangerAlert['status']) => void;
  isSupervisorView?: boolean;
  language?: LanguageCode;
}

export const DangerAlertBanner: React.FC<DangerAlertBannerProps> = ({
  alert,
  onAcknowledge,
  onUpdateStatus,
  isSupervisorView = false,
  language,
}) => {
  const { ui } = useTranslation(language);
  const isAcked = alert.status !== 'active';

  const statusColors: Record<DangerAlert['status'], string> = {
    active: 'bg-white text-red-800 border-red-200',
    acknowledged: 'bg-amber-100 text-amber-900 border-amber-300',
    referred: 'bg-sky-100 text-sky-900 border-sky-300',
    resolved: 'bg-emerald-100 text-emerald-900 border-emerald-300',
  };

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="bg-clinical-danger text-white rounded-2xl p-4 sm:p-5 border-2 border-red-900 shadow-lg"
    >
      <div className="flex items-start gap-3">
        <div className="p-2.5 rounded-xl bg-white/15 shrink-0 mt-0.5">
          <AlertTriangle className="h-6 w-6 text-white" aria-hidden="true" />
        </div>

        <div className="flex-1 min-w-0">
          {/* Header Badges */}
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[11px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-white text-clinical-danger-dark">
                {ui.urgentDangerSign}
              </span>
              <span className="text-xs font-bold px-2 py-0.5 rounded bg-red-800/90 text-red-50">
                {alert.category} · {alert.subject}
              </span>
            </div>

            <span
              className={`text-[11px] font-bold uppercase px-2.5 py-0.5 rounded-full border ${
                statusColors[alert.status]
              }`}
            >
              {alert.status}
            </span>
          </div>

          {/* Canonical Sign Name & Patient */}
          <h3 className="text-base sm:text-lg font-extrabold mt-2 leading-snug text-white">
            {alert.beneficiary_name
              ? `${alert.beneficiary_name} (${alert.beneficiary_id || 'Unlinked'}) — `
              : ''}
            {alert.canonical_name}
          </h3>

          {/* Evidence */}
          <p className="text-xs sm:text-sm text-red-50 mt-1">
            <strong>{ui.matchedPhrase}:</strong> &ldquo;{alert.supporting_evidence}&rdquo;
          </p>

          {/* Mandatory Urgent PHC Referral Instruction */}
          <div className="mt-3 p-3.5 rounded-xl bg-red-800/90 border border-white/25">
            <p className="text-xs font-bold uppercase tracking-wider text-red-100 flex items-center gap-1.5">
              <Building2 className="h-4 w-4" aria-hidden="true" />
              <span>{ui.urgentPhcReferral}</span>
            </p>
            <p className="mt-1 text-sm sm:text-base font-semibold text-white leading-relaxed">
              {alert.referral_message}
            </p>
          </div>

          {/* Official NHM Guideline Source Citation */}
          <div className="mt-2.5 flex items-center gap-2 text-xs text-red-100 flex-wrap">
            <BookOpen className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span>
              <strong>{ui.guidelineReference}:</strong> {alert.source_guideline_ref}
            </span>
            <span>·</span>
            <span className="tabular-nums">
              {ui.detectedAt} {new Date(alert.detected_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>

          {/* Action Row */}
          <div className="mt-4 flex flex-wrap items-center gap-2.5">
            <a
              href="tel:108"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white text-clinical-danger-dark font-bold text-xs shadow-sm hover:bg-red-50 transition-colors"
            >
              <PhoneCall className="h-3.5 w-3.5" aria-hidden="true" />
              <span>{ui.call108Emergency}</span>
            </a>

            {!isAcked && onAcknowledge && (
              <button
                type="button"
                onClick={() => onAcknowledge(alert.alert_id)}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-950 hover:bg-slate-900 text-white font-bold text-xs shadow-sm"
              >
                <ShieldAlert className="h-3.5 w-3.5" aria-hidden="true" />
                <span>{isSupervisorView ? ui.acknowledgeAlert : ui.acknowledgeAndRefer}</span>
              </button>
            )}

            {isSupervisorView && onUpdateStatus && alert.status !== 'resolved' && (
              <>
                {alert.status === 'acknowledged' && (
                  <button
                    type="button"
                    onClick={() => onUpdateStatus(alert.alert_id, 'referred')}
                    className="px-3.5 py-2 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-bold text-xs"
                  >
                    {ui.markReferred}
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => onUpdateStatus(alert.alert_id, 'resolved')}
                  className="px-3.5 py-2 rounded-xl bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-xs"
                >
                  {ui.markResolved}
                </button>
              </>
            )}

            {alert.acknowledged_by && (
              <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-100 ml-auto">
                <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                <span>
                  {alert.status.toUpperCase()} by {alert.acknowledged_by}
                </span>
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
