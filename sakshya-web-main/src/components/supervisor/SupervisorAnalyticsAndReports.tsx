'use client';

import React, { useMemo, useState } from 'react';
import {
  buildVisitsCsv,
  type DailyVisitVolumeItem,
  type SupervisorOverviewStats,
  type VisitTypeBreakdownItem,
  type WorkerMetricsRow,
} from '@/lib/analytics/supervisor-metrics';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type { AuditLogEntry, DangerAlert, UserProfile, VisitDraft } from '@/types';
import { BarChart3, Download, FileSpreadsheet, Printer, Shield } from 'lucide-react';

export const SupervisorAnalyticsView: React.FC<{
  stats: SupervisorOverviewStats;
  dailyVolume: DailyVisitVolumeItem[];
  typeDistribution: VisitTypeBreakdownItem[];
  workerRows: WorkerMetricsRow[];
  dangerAlerts: DangerAlert[];
}> = ({ stats, dailyVolume, typeDistribution, workerRows, dangerAlerts }) => {
  const { ui } = useTranslation();
  const maxDaily = Math.max(1, ...dailyVolume.map((d) => d.count));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-clinical-text">
          {ui.analyticsTitle}
        </h1>
        <p className="text-xs sm:text-sm text-clinical-text-secondary">
          {ui.analyticsSubtitle}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Daily Visit Volume (Last 7 Days) */}
        <figure className="bg-white border border-clinical-border-subtle rounded-2xl p-5 shadow-sm">
          <figcaption className="text-sm font-bold text-clinical-text flex items-center gap-2 mb-4">
            <BarChart3 className="h-4 w-4 text-clinical-primary" aria-hidden="true" />
            <span>7-Day Visit Volume &amp; Danger Escalations</span>
          </figcaption>

          <div className="h-48 flex items-end justify-between gap-2 pt-4 border-b border-slate-200 pb-2">
            {dailyVolume.map((item) => {
              const barHeightPct = Math.round((item.count / maxDaily) * 100);
              return (
                <div key={item.date} className="flex-1 flex flex-col items-center justify-end h-full">
                  <span className="text-[11px] font-bold tabular-nums text-slate-700 mb-1">
                    {item.count}
                  </span>
                  <div className="w-full max-w-[36px] bg-slate-100 rounded-t-lg h-32 flex flex-col justify-end overflow-hidden">
                    <div
                      className={`w-full transition-all ${
                        item.dangerCount > 0 ? 'bg-clinical-danger' : 'bg-clinical-primary'
                      }`}
                      style={{ height: `${Math.max(item.count > 0 ? 12 : 2, barHeightPct)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between gap-2 mt-2 text-[11px] text-slate-500 font-medium">
            {dailyVolume.map((item) => (
              <span key={item.date} className="flex-1 text-center truncate">
                {item.label}
              </span>
            ))}
          </div>
        </figure>

        {/* Visit Type Distribution */}
        <section className="bg-white border border-clinical-border-subtle rounded-2xl p-5 shadow-sm space-y-4">
          <h2 className="text-sm font-bold text-clinical-text">
            ANC / PNC / Newborn / Immunisation Mix
          </h2>
          <div className="space-y-3">
            {typeDistribution.map((row) => (
              <div key={row.label}>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <span className="text-clinical-text">{row.label}</span>
                  <span className="tabular-nums text-slate-600">
                    {row.count} visits ({row.pct}%)
                  </span>
                </div>
                <div className="w-full h-2.5 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full bg-clinical-secondary rounded-full"
                    style={{ width: `${row.pct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Coverage & Follow-Up Gauges */}
        <section className="bg-white border border-clinical-border-subtle rounded-2xl p-5 shadow-sm space-y-4">
          <h2 className="text-sm font-bold text-clinical-text">
            Immunisation Coverage &amp; Follow-Up Completion
          </h2>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Immunisation Doses Administered</span>
                <span className="tabular-nums text-clinical-primary font-bold">
                  {stats.immunisationCoveragePct}%
                </span>
              </div>
              <div className="w-full h-3 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full bg-clinical-primary rounded-full"
                  style={{ width: `${stats.immunisationCoveragePct}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Follow-Up Task Completion</span>
                <span className="tabular-nums text-clinical-secondary font-bold">
                  {stats.followUpCompletionPct}%
                </span>
              </div>
              <div className="w-full h-3 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full bg-clinical-secondary rounded-full"
                  style={{ width: `${stats.followUpCompletionPct}%` }}
                />
              </div>
            </div>

            <p className="text-xs text-slate-600 pt-2 border-t border-slate-100">
              Total Danger Alerts Logged: <strong className="tabular-nums">{dangerAlerts.length}</strong>{' '}
              ({stats.activeDangerAlerts} currently active).
            </p>
          </div>
        </section>

        {/* Worker Activity Comparison */}
        <section className="bg-white border border-clinical-border-subtle rounded-2xl p-5 shadow-sm space-y-3">
          <h2 className="text-sm font-bold text-clinical-text">ASHA Worker Activity Summary</h2>
          <ul className="space-y-2.5 text-xs">
            {workerRows.map((w) => (
              <li
                key={w.worker.id}
                className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-2"
              >
                <div>
                  <span className="font-bold text-clinical-text block">{w.worker.full_name}</span>
                  <span className="text-slate-500">
                    {w.assignedBeneficiaries} households assigned
                  </span>
                </div>
                <div className="text-right tabular-nums">
                  <span className="font-bold text-clinical-primary block">
                    {w.completedVisits} visits
                  </span>
                  <span className="text-slate-500">{w.pendingFollowUps} pending tasks</span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
};

export const SupervisorReportsView: React.FC<{
  visits: VisitDraft[];
  workers: UserProfile[];
  auditLogs: AuditLogEntry[];
}> = ({ visits, workers, auditLogs }) => {
  const { ui } = useTranslation();
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [workerId, setWorkerId] = useState('ALL');
  const [visitType, setVisitType] = useState('ALL');

  const filtered = useMemo(() => {
    return visits.filter((v) => {
      const dateStr = v.visit_date.split('T')[0];
      if (fromDate && dateStr < fromDate) return false;
      if (toDate && dateStr > toDate) return false;
      if (workerId !== 'ALL' && v.asha_worker_id !== workerId) return false;
      if (visitType !== 'ALL' && v.visit_type !== visitType) return false;
      return true;
    });
  }, [visits, fromDate, toDate, workerId, visitType]);

  const handleDownloadCsv = () => {
    const csv = buildVisitsCsv(filtered);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `phc_visit_report_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handlePrintPdf = () => {
    if (typeof window !== 'undefined') {
      window.print();
    }
  };

  const dangerCount = filtered.filter((v) => v.danger_sign_flagged).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-clinical-text">
            {ui.reportsAuditTitle}
          </h1>
          <p className="text-xs sm:text-sm text-clinical-text-secondary">
            {ui.reportsAuditSubtitle}
          </p>
        </div>

        <div className="flex items-center gap-2 no-print">
          <button
            type="button"
            onClick={handleDownloadCsv}
            className="px-4 py-2.5 rounded-xl bg-clinical-primary hover:bg-clinical-primary-dark text-white text-xs font-bold flex items-center gap-1.5"
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            <span>Export CSV</span>
          </button>
          <button
            type="button"
            onClick={handlePrintPdf}
            className="px-4 py-2.5 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-clinical-text text-xs font-bold flex items-center gap-1.5"
          >
            <Printer className="h-4 w-4" aria-hidden="true" />
            <span>Print / PDF Report</span>
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white border border-clinical-border-subtle rounded-2xl p-4 shadow-sm grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 no-print">
        <div>
          <label htmlFor="rep-from" className="block text-[11px] font-bold text-slate-600 mb-1">
            From Date
          </label>
          <input
            id="rep-from"
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs bg-slate-50"
          />
        </div>
        <div>
          <label htmlFor="rep-to" className="block text-[11px] font-bold text-slate-600 mb-1">
            To Date
          </label>
          <input
            id="rep-to"
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs bg-slate-50"
          />
        </div>
        <div>
          <label htmlFor="rep-worker" className="block text-[11px] font-bold text-slate-600 mb-1">
            ASHA Worker
          </label>
          <select
            id="rep-worker"
            value={workerId}
            onChange={(e) => setWorkerId(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs font-semibold bg-slate-50"
          >
            <option value="ALL">All Workers</option>
            {workers
              .filter((w) => w.role === 'ASHA_WORKER')
              .map((w) => (
                <option key={w.id} value={w.id}>
                  {w.full_name}
                </option>
              ))}
          </select>
        </div>
        <div>
          <label htmlFor="rep-type" className="block text-[11px] font-bold text-slate-600 mb-1">
            Visit Type
          </label>
          <select
            id="rep-type"
            value={visitType}
            onChange={(e) => setVisitType(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs font-semibold bg-slate-50"
          >
            <option value="ALL">All Visit Types</option>
            <option value="ANC">ANC</option>
            <option value="PNC">PNC</option>
            <option value="Newborn">Newborn</option>
            <option value="Immunisation">Immunisation</option>
          </select>
        </div>
      </div>

      {/* Report Totals */}
      <section className="bg-white border border-clinical-border-subtle rounded-2xl p-5 shadow-sm">
        <h2 className="text-sm font-bold text-clinical-text flex items-center gap-2 mb-3">
          <FileSpreadsheet className="h-4 w-4 text-clinical-primary" aria-hidden="true" />
          <span>Report Totals</span>
        </h2>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-xs text-slate-500 block">Filtered Visits</span>
            <strong className="text-xl font-bold tabular-nums">{filtered.length}</strong>
          </div>
          <div className="p-3 rounded-xl bg-red-50 border border-red-200">
            <span className="text-xs text-red-700 block">Danger Sign Visits</span>
            <strong className="text-xl font-bold tabular-nums text-red-900">{dangerCount}</strong>
          </div>
          <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200">
            <span className="text-xs text-emerald-700 block">Routine / Safe</span>
            <strong className="text-xl font-bold tabular-nums text-emerald-900">
              {filtered.length - dangerCount}
            </strong>
          </div>
        </div>
      </section>

      {/* Audit Trail */}
      <section className="bg-white border border-clinical-border-subtle rounded-2xl p-5 shadow-sm space-y-3 no-print">
        <h2 className="text-sm font-bold text-clinical-text flex items-center gap-2">
          <Shield className="h-4 w-4 text-clinical-primary" aria-hidden="true" />
          <span>System Audit Trail ({auditLogs.length})</span>
        </h2>
        <ul className="divide-y divide-slate-100 text-xs">
          {auditLogs.slice(0, 15).map((log) => (
            <li key={log.id} className="py-2.5 flex flex-wrap items-center justify-between gap-2">
              <div>
                <span className="font-mono text-[11px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 mr-2">
                  {log.action_type}
                </span>
                <span className="font-semibold text-clinical-text">{log.summary}</span>
                <span className="text-slate-500 ml-2">by {log.actor_name}</span>
              </div>
              <span className="tabular-nums text-slate-500">
                {new Date(log.created_at).toLocaleString()}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
};

