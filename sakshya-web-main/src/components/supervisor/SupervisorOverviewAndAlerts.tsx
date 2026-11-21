'use client';

import React, { useState } from 'react';
import { DangerAlertBanner } from '@/components/DangerAlertBanner';
import type { SupervisorNavSection } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/ui/ClinicalUI';
import type { SupervisorOverviewStats } from '@/lib/analytics/supervisor-metrics';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type { DangerAlert, LanguageCode, UserProfile, VisitDraft } from '@/types';
import {
  AlertTriangle,
  ArrowRight,
  Building2,
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  Radio,
  ShieldCheck,
  Syringe,
  Users,
} from 'lucide-react';

interface SupervisorOverviewViewProps {
  profile: UserProfile;
  stats: SupervisorOverviewStats;
  dangerAlerts: DangerAlert[];
  recentVisits: VisitDraft[];
  language: LanguageCode;
  realtimeConnected: boolean;
  onAcknowledgeAlert: (alertId: string) => void;
  onUpdateAlertStatus: (alertId: string, nextStatus: DangerAlert['status']) => void;
  onNavigateSection: (sec: SupervisorNavSection) => void;
}

export const SupervisorOverviewView: React.FC<SupervisorOverviewViewProps> = ({
  profile,
  stats,
  dangerAlerts,
  recentVisits,
  language,
  realtimeConnected,
  onAcknowledgeAlert,
  onUpdateAlertStatus,
  onNavigateSection,
}) => {
  const { ui } = useTranslation(language);
  const activeAlerts = dangerAlerts.filter((a) => a.status === 'active');

  return (
    <div className="space-y-6">
      {/* Operational Command Header */}
      <section className="bg-slate-900 text-white rounded-2xl p-5 sm:p-7 shadow-md flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-800 text-teal-300 border border-slate-700">
              <Building2 className="h-3.5 w-3.5" aria-hidden="true" />
              <span>{profile.phc_name}</span>
            </span>
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300">
              <Radio className="h-3 w-3 text-emerald-400" aria-hidden="true" />
              <span>{realtimeConnected ? 'Supabase Realtime Active' : 'Local Live Sync'}</span>
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold mt-2">{ui.commandCenterTitle}</h1>
          <p className="text-xs sm:text-sm text-slate-300 mt-1">
            {ui.commandCenterSubtitle}
          </p>
        </div>

        <button
          type="button"
          onClick={() => onNavigateSection('alerts')}
          className="px-4 py-3 rounded-xl bg-clinical-danger hover:bg-red-700 text-white font-bold text-sm flex items-center justify-center gap-2 shrink-0"
        >
          <AlertTriangle className="h-4 w-4" aria-hidden="true" />
          <span>{ui.alertCommandButton} ({stats.activeDangerAlerts})</span>
        </button>
      </section>

      {/* 8 Real Operational Metrics */}
      <section aria-label="PHC Operational Aggregates" className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
        <KpiCard
          label={ui.registeredBeneficiaries}
          value={stats.totalBeneficiaries}
          sub="Active PHC directory"
          icon={<Users className="h-4 w-4 text-clinical-primary" />}
        />
        <KpiCard
          label={ui.activeWorkers}
          value={`${stats.onlineAshaWorkers}/${stats.activeAshaWorkers}`}
          sub="Online / Total assigned"
          icon={<CheckCircle2 className="h-4 w-4 text-clinical-success" />}
        />
        <KpiCard
          label="Visits Completed Today"
          value={stats.visitsCompletedToday}
          sub={`${stats.totalCommittedVisits} total committed`}
          icon={<ClipboardList className="h-4 w-4 text-clinical-secondary" />}
        />
        <KpiCard
          label="Pending Unconfirmed Drafts"
          value={stats.pendingDraftVisits}
          sub="Awaiting worker review"
          icon={<CalendarClock className="h-4 w-4 text-slate-500" />}
        />
        <KpiCard
          label="Overdue Follow-Ups"
          value={stats.overdueFollowUps}
          sub={`${stats.followUpCompletionPct}% completion rate`}
          icon={<CalendarClock className="h-4 w-4 text-clinical-warning" />}
          highlight={stats.overdueFollowUps > 0 ? 'warning' : undefined}
        />
        <KpiCard
          label="Upcoming Immunisations"
          value={stats.upcomingImmunisations}
          sub={`${stats.immunisationCoveragePct}% doses given`}
          icon={<Syringe className="h-4 w-4 text-clinical-secondary" />}
        />
        <KpiCard
          label="Active Danger Alerts"
          value={stats.activeDangerAlerts}
          sub="Needs immediate review"
          icon={<AlertTriangle className="h-4 w-4 text-clinical-danger" />}
          highlight={stats.activeDangerAlerts > 0 ? 'danger' : undefined}
        />
        <KpiCard
          label="Active Referrals"
          value={stats.referredOrAcknowledgedAlerts}
          sub="Acknowledged / En route"
          icon={<ShieldCheck className="h-4 w-4 text-clinical-primary" />}
        />
      </section>

      {/* Immediate Active Danger Alerts Queue */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-clinical-text flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-clinical-danger" aria-hidden="true" />
            <span>Unacknowledged Critical Danger Alerts</span>
          </h2>
          <button
            type="button"
            onClick={() => onNavigateSection('alerts')}
            className="text-xs font-bold text-clinical-primary hover:underline flex items-center gap-1"
          >
            <span>Open Alert Command</span>
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </div>

        {activeAlerts.length > 0 ? (
          activeAlerts.map((alert) => (
            <DangerAlertBanner
              key={alert.alert_id}
              alert={alert}
              language={language}
              isSupervisorView
              onAcknowledge={onAcknowledgeAlert}
              onUpdateStatus={onUpdateAlertStatus}
            />
          ))
        ) : (
          <div className="p-5 bg-white border border-clinical-border-subtle rounded-xl text-xs text-slate-600 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-clinical-success" aria-hidden="true" />
            <span>All current danger alerts have been acknowledged or resolved.</span>
          </div>
        )}
      </section>

      {/* Recent Register Preview */}
      <section className="bg-white border border-clinical-border-subtle rounded-2xl p-4 sm:p-5 shadow-sm">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <h2 className="text-sm font-bold text-clinical-text">Recent Live Visit Activity</h2>
          <button
            type="button"
            onClick={() => onNavigateSection('register')}
            className="text-xs font-bold text-clinical-primary hover:underline flex items-center gap-1"
          >
            <span>Full Register</span>
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </div>

        <ul className="mt-3 divide-y divide-slate-100">
          {recentVisits.slice(0, 5).map((v) => (
            <li key={v.visit_id || v.draft_id} className="py-2.5 flex flex-wrap items-center justify-between gap-2 text-xs">
              <div>
                <span className="font-bold text-clinical-text">{v.beneficiary_name || v.beneficiary_id}</span>
                <span className="text-slate-500 ml-2">
                  by {v.worker_name || v.asha_worker_id} · {v.visit_type || 'Visit'}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {v.danger_sign_flagged && (
                  <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-800 font-bold text-[11px]">
                    Danger Flagged
                  </span>
                )}
                <span className="tabular-nums text-slate-500">
                  {new Date(v.visit_date).toLocaleDateString()}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
};

export const DangerCommandCenterView: React.FC<{
  dangerAlerts: DangerAlert[];
  language: LanguageCode;
  onAcknowledgeAlert: (alertId: string) => void;
  onUpdateAlertStatus: (alertId: string, nextStatus: DangerAlert['status']) => void;
}> = ({ dangerAlerts, language, onAcknowledgeAlert, onUpdateAlertStatus }) => {
  const { ui } = useTranslation(language);
  const [statusFilter, setStatusFilter] = useState<'all' | DangerAlert['status']>('all');

  const filtered = dangerAlerts.filter(
    (a) => statusFilter === 'all' || a.status === statusFilter
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-clinical-text">
            {ui.dangerAlertQueue}
          </h1>
          <p className="text-xs sm:text-sm text-clinical-text-secondary">
            {ui.commandCenterSubtitle}
          </p>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          {(['all', 'active', 'acknowledged', 'referred', 'resolved'] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setStatusFilter(s)}
              className={`compact-chip px-3 py-1.5 rounded-full text-xs font-bold capitalize border ${
                statusFilter === s
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title="No alerts match this status filter"
          description="Danger sign alerts appear here immediately when detected during ASHA voice visits."
          icon={<AlertTriangle className="h-5 w-5" />}
        />
      ) : (
        <div className="space-y-4">
          {filtered.map((alert) => (
            <DangerAlertBanner
              key={alert.alert_id}
              alert={alert}
              language={language}
              isSupervisorView
              onAcknowledge={onAcknowledgeAlert}
              onUpdateStatus={onUpdateAlertStatus}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const KpiCard: React.FC<{
  label: string;
  value: string | number;
  sub: string;
  icon: React.ReactNode;
  highlight?: 'danger' | 'warning';
}> = ({ label, value, sub, icon, highlight }) => (
  <div
    className={`rounded-2xl border p-4 shadow-sm ${
      highlight === 'danger'
        ? 'bg-red-50/70 border-red-300'
        : highlight === 'warning'
        ? 'bg-amber-50/70 border-amber-300'
        : 'bg-white border-clinical-border-subtle'
    }`}
  >
    <div className="flex items-center justify-between gap-2">
      <span className="text-xs font-semibold text-clinical-text-secondary">{label}</span>
      {icon}
    </div>
    <p className="text-2xl font-bold text-clinical-text mt-2 tabular-nums">{value}</p>
    <p className="text-[11px] text-slate-500 mt-0.5">{sub}</p>
  </div>
);

