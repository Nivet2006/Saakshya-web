'use client';

import React from 'react';
import { DangerAlert, LanguageCode } from '@/types';
import { TRANSLATIONS } from '@/lib/translations';
import { AlertTriangle, PhoneCall, Building2, CheckCircle2 } from 'lucide-react';

interface DangerAlertBannerProps {
  alert: DangerAlert;
  onAcknowledge?: (alertId: string) => void;
  isSupervisorView?: boolean;
  language?: LanguageCode;
}

export const DangerAlertBanner: React.FC<DangerAlertBannerProps> = ({
  alert,
  onAcknowledge,
  isSupervisorView = false,
  language = 'hi-IN',
}) => {
  const t = TRANSLATIONS[language] || TRANSLATIONS['hi-IN'];

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="bg-emergency-600 text-white rounded-xl p-4 sm:p-5 shadow-lg border-2 border-emergency-500 danger-alert-glow mb-4"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-white/20 rounded-lg text-white mt-0.5">
            <AlertTriangle className="h-6 w-6 animate-bounce" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-black tracking-wider uppercase bg-white text-emergency-700 px-2.5 py-0.5 rounded-full shadow-sm">
                {t.criticalDangerDetected}
              </span>
              <span className="text-xs font-semibold bg-emergency-800/80 px-2 py-0.5 rounded">
                {alert.category.replace(/_/g, ' ')}
              </span>
            </div>

            <h3 className="text-base sm:text-lg font-bold mt-1 text-white">
              {alert.beneficiary_name ? `${alert.beneficiary_name}: ` : ''}
              {alert.symptom_evidence}
            </h3>

            <div className="mt-2 text-sm text-red-50 bg-emergency-700/80 p-3 rounded-lg border border-white/20">
              <p className="font-semibold text-white flex items-center gap-1.5">
                <Building2 className="h-4 w-4" />
                {t.referralProtocol}
              </p>
              <p className="mt-0.5 text-xs sm:text-sm">{alert.referral_instruction}</p>
            </div>

            <div className="mt-3 flex items-center gap-3 flex-wrap text-xs">
              <a
                href="tel:108"
                className="inline-flex items-center gap-1.5 bg-white text-emergency-700 font-bold px-3 py-1.5 rounded-lg shadow-sm hover:bg-slate-100 transition-colors"
              >
                <PhoneCall className="h-3.5 w-3.5 text-emergency-600" />
                {t.call108}
              </a>

              <span className="text-red-100">
                {t.transportStatus} <strong className="text-white">{alert.referral_status.replace(/_/g, ' ')}</strong>
              </span>

              {alert.supervisor_acknowledged ? (
                <span className="inline-flex items-center gap-1 text-emerald-200 font-semibold">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  {t.supervisorAcknowledged}
                </span>
              ) : isSupervisorView && onAcknowledge ? (
                <button
                  onClick={() => onAcknowledge(alert.alert_id)}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-3 py-1.5 rounded-lg shadow-sm transition-colors text-xs ml-auto"
                >
                  {t.acknowledgeButton}
                </button>
              ) : (
                <span className="text-amber-200 font-medium">{t.pendingSupervisorAck}</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
