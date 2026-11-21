'use client';

import React from 'react';
import { DangerAlertBanner } from '@/components/DangerAlertBanner';
import type { AshaNavSection } from '@/components/layout/AppShell';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type {
  Beneficiary,
  DangerAlert,
  FollowUpTask,
  ImmunisationScheduleItem,
  LanguageCode,
  UserProfile,
  VisitDraft,
} from '@/types';
import {
  AlertTriangle,
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  Mic,
  Syringe,
  Users,
} from 'lucide-react';

interface AshaHomeViewProps {
  profile: UserProfile;
  language: LanguageCode;
  beneficiaries: Beneficiary[];
  visits: VisitDraft[];
  followUps: FollowUpTask[];
  immunisations: ImmunisationScheduleItem[];
  dangerAlerts: DangerAlert[];
  onStartVoiceVisit: (beneficiary?: Beneficiary) => void;
  onNavigateSection: (section: AshaNavSection) => void;
  onAcknowledgeAlert: (alertId: string) => void;
  onClearVisits?: () => void;
  onClearAlerts?: () => void;
}

export const AshaHomeView: React.FC<AshaHomeViewProps> = ({
  profile,
  language,
  beneficiaries,
  visits,
  followUps,
  immunisations,
  dangerAlerts,
  onStartVoiceVisit,
  onNavigateSection,
  onAcknowledgeAlert,
  onClearVisits,
  onClearAlerts,
}) => {
  const { ui } = useTranslation(language);
  const todayStr = new Date().toISOString().split('T')[0];
  const todayVisits = visits.filter((v) => v.visit_date.startsWith(todayStr));
  const pendingFollowUps = followUps.filter((f) => f.status !== 'COMPLETED' && f.status !== 'CANCELLED');
  const dueVaccines = immunisations.filter((i) => i.status === 'DUE' || i.status === 'OVERDUE');
  const activeAlerts = dangerAlerts.filter((a) => a.status === 'active');

  return (
    <div className="space-y-5">
      {/* Compact Welcome & Immediate Primary Voice Visit Action */}
      <section className="bg-clinical-primary text-white rounded-2xl p-5 sm:p-7 shadow-md flex flex-col md:flex-row md:items-center justify-between gap-5">
        <div className="max-w-xl">
          <p className="text-xs font-semibold text-teal-100 uppercase tracking-wider">
            {profile.assigned_area} · {profile.phc_name}
          </p>
          <h1 className="text-2xl sm:text-3xl font-bold mt-1">
            {ui.namasteGreeting}, {profile.full_name}
          </h1>
          <p className="text-sm text-teal-50/90 mt-1.5 leading-relaxed">
            {ui.homeVoicePrompt}
          </p>
        </div>

        <button
          type="button"
          onClick={() => onStartVoiceVisit()}
          className="w-full md:w-auto min-h-[60px] px-7 py-4 rounded-2xl bg-white hover:bg-teal-50 text-clinical-primary-dark font-bold text-base shadow-lg transition-transform active:scale-95 flex items-center justify-center gap-3 shrink-0"
        >
          <div className="w-10 h-10 rounded-full bg-clinical-primary text-white flex items-center justify-center">
            <Mic className="h-5 w-5" aria-hidden="true" />
          </div>
          <span>{ui.startVoiceVisit}</span>
        </button>
      </section>

      {/* Active Critical Alerts */}
      {activeAlerts.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-bold text-red-800 uppercase tracking-wider">
              {ui.activeDangerAlertsLabel} ({activeAlerts.length})
            </span>
            {onClearAlerts && (
              <button
                type="button"
                onClick={onClearAlerts}
                className="text-xs font-semibold text-red-700 hover:text-red-900 bg-red-100 hover:bg-red-200 border border-red-300 px-2.5 py-1 rounded-lg transition-colors"
              >
                {ui.clearAllAlerts}
              </button>
            )}
          </div>
          {activeAlerts.map((alert) => (
            <DangerAlertBanner
              key={alert.alert_id}
              alert={alert}
              language={language}
              onAcknowledge={onAcknowledgeAlert}
            />
          ))}
        </div>
      )}

      {/* Real Operational Field Counters */}
      <section aria-label="Today's Field Summary" className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <MetricButton
          icon={<Users className="h-5 w-5 text-clinical-primary" />}
          label={ui.assignedHouseholds}
          value={beneficiaries.length}
          hint={ui.viewDirectory}
          onClick={() => onNavigateSection('beneficiaries')}
        />
        <MetricButton
          icon={<CheckCircle2 className="h-5 w-5 text-clinical-success" />}
          label={ui.visitsToday}
          value={todayVisits.length}
          hint={`${visits.length} ${ui.totalLogged}`}
          onClick={() => onNavigateSection('history')}
        />
        <MetricButton
          icon={<CalendarClock className="h-5 w-5 text-clinical-warning" />}
          label={ui.pendingFollowUps}
          value={pendingFollowUps.length}
          hint={ui.openTaskQueue}
          onClick={() => onNavigateSection('followups')}
        />
        <MetricButton
          icon={<Syringe className="h-5 w-5 text-clinical-secondary" />}
          label={ui.vaccinesDue}
          value={dueVaccines.length}
          hint={ui.dueOverdueDoses}
          onClick={() => onNavigateSection('followups')}
        />
      </section>

      {/* Two-Column Quick Views */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Urgent & Upcoming Follow-ups */}
        <section className="bg-white border border-clinical-border-subtle rounded-2xl p-4 sm:p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 className="text-sm font-bold text-clinical-text flex items-center gap-2">
              <CalendarClock className="h-4 w-4 text-clinical-primary" aria-hidden="true" />
              <span>{ui.pendingFollowUps}</span>
            </h2>
            <button
              type="button"
              onClick={() => onNavigateSection('followups')}
              className="text-xs font-semibold text-clinical-primary hover:underline flex items-center gap-1"
            >
              <span>{ui.allTasks}</span>
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>

          <ul className="mt-3 space-y-2.5">
            {pendingFollowUps.slice(0, 4).map((task) => (
              <li
                key={task.id}
                className={`p-3 rounded-xl border text-xs ${
                  task.priority === 'URGENT'
                    ? 'bg-red-50 border-red-200'
                    : task.status === 'OVERDUE'
                    ? 'bg-amber-50 border-amber-200'
                    : 'bg-slate-50 border-slate-200'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-clinical-text">{task.task_type}</span>
                  <span
                    className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                      task.priority === 'URGENT'
                        ? 'bg-red-200 text-red-900'
                        : 'bg-white text-slate-700 border border-slate-200'
                    }`}
                  >
                    {task.priority}
                  </span>
                </div>
                <p className="text-slate-600 mt-1">
                  {task.beneficiary_name || task.beneficiary_id} · {ui.dueLabel}{' '}
                  <span className="tabular-nums font-semibold">{task.due_date}</span>
                </p>
              </li>
            ))}
            {pendingFollowUps.length === 0 && (
              <li className="text-xs text-slate-500 py-4 text-center">{ui.noPendingTasks}</li>
            )}
          </ul>
        </section>

        {/* Recent Confirmed Visits */}
        <section className="bg-white border border-clinical-border-subtle rounded-2xl p-4 sm:p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 className="text-sm font-bold text-clinical-text">{ui.recentSavedVisits}</h2>
            <div className="flex items-center gap-3">
              {visits.length > 0 && onClearVisits && (
                <button
                  type="button"
                  onClick={onClearVisits}
                  className="text-xs text-red-600 hover:text-red-700 hover:underline font-medium"
                >
                  {ui.clearAll}
                </button>
              )}
              <button
                type="button"
                onClick={() => onNavigateSection('history')}
                className="text-xs font-semibold text-clinical-primary hover:underline flex items-center gap-1"
              >
                <span>{ui.fullHistory}</span>
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>
          </div>

          <ul className="mt-3 space-y-2.5">
            {visits.slice(0, 4).map((v) => (
              <li
                key={v.visit_id || v.draft_id}
                className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs flex items-center justify-between gap-3"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-bold text-clinical-text">
                      {v.beneficiary_name || v.beneficiary_id}
                    </span>
                    <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                      {v.visit_type || 'Visit'}
                    </span>
                    {v.danger_sign_flagged && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-800">
                        <AlertTriangle className="h-3 w-3" aria-hidden="true" />
                        {ui.dangerFlagged}
                      </span>
                    )}
                  </div>
                  <p className="text-slate-500 mt-1 truncate">
                    {v.weight_kg !== null ? `${ui.weightLabel}: ${v.weight_kg} kg · ` : ''}
                    {v.next_visit_date ? `${ui.nextVisitLabel}: ${v.next_visit_date}` : ui.confirmed}
                  </p>
                </div>
                <span className="text-[11px] font-bold text-emerald-800 bg-emerald-50 px-2 py-1 rounded-lg border border-emerald-200 shrink-0">
                  {v.status}
                </span>
              </li>
            ))}
            {visits.length === 0 && (
              <li className="text-xs text-slate-500 py-4 text-center">{ui.noVisitsRecorded}</li>
            )}
          </ul>
        </section>
      </div>
    </div>
  );
};

const MetricButton: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: number;
  hint: string;
  onClick: () => void;
}> = ({ icon, label, value, hint, onClick }) => (
  <button
    type="button"
    onClick={onClick}
    className="text-left bg-white border border-clinical-border-subtle hover:border-clinical-primary rounded-2xl p-4 shadow-sm transition-colors"
  >
    <div className="flex items-center justify-between">
      <span className="text-xs font-semibold text-clinical-text-secondary">{label}</span>
      {icon}
    </div>
    <p className="text-2xl font-bold text-clinical-text mt-2 tabular-nums">{value}</p>
    <p className="text-[11px] text-slate-500 mt-0.5">{hint}</p>
  </button>
);

