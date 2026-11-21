'use client';

import React, { useMemo, useState } from 'react';
import { EmptyState } from '@/components/ui/ClinicalUI';
import type { WorkerMetricsRow } from '@/lib/analytics/supervisor-metrics';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type { VisitDraft } from '@/types';
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  MapPin,
  Phone,
  Search,
  Users,
  X,
} from 'lucide-react';

export const AshaWorkerManagementView: React.FC<{
  workerRows: WorkerMetricsRow[];
  visits: VisitDraft[];
}> = ({ workerRows, visits }) => {
  const { ui } = useTranslation();
  const [selectedWorker, setSelectedWorker] = useState<WorkerMetricsRow | null>(null);

  const workerVisits = useMemo(() => {
    if (!selectedWorker) return [];
    return visits.filter(
      (v) =>
        v.asha_worker_id === selectedWorker.worker.id ||
        v.worker_name === selectedWorker.worker.full_name
    );
  }, [selectedWorker, visits]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-clinical-text">
          {ui.ashaWorkersTitle}
        </h1>
        <p className="text-xs sm:text-sm text-clinical-text-secondary">
          {ui.ashaWorkersSubtitle}
        </p>
      </div>

      {workerRows.length === 0 ? (
        <EmptyState
          title="No ASHA workers assigned"
          description="Workers registered in this PHC sector will appear here."
          icon={<Users className="h-5 w-5" />}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {workerRows.map((row) => (
            <article
              key={row.worker.id}
              className="bg-white border border-clinical-border-subtle rounded-2xl p-4 shadow-sm flex flex-col justify-between gap-4"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h2 className="font-bold text-base text-clinical-text">
                      {row.worker.full_name}
                    </h2>
                    <span className="font-mono text-xs text-slate-500">
                      {row.worker.worker_code}
                    </span>
                  </div>
                  <span
                    className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full ${
                      row.worker.is_online
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {row.worker.is_online ? 'Online' : 'Offline'}
                  </span>
                </div>

                <div className="mt-3 space-y-1 text-xs text-slate-600">
                  <p className="flex items-center gap-1.5">
                    <MapPin className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
                    <span>{row.worker.assigned_area}</span>
                  </p>
                  {row.worker.phone_number && (
                    <p className="flex items-center gap-1.5 tabular-nums">
                      <Phone className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
                      <span>{row.worker.phone_number}</span>
                    </p>
                  )}
                </div>

                <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <dt className="text-slate-500">Households</dt>
                    <dd className="text-base font-bold tabular-nums text-clinical-text">
                      {row.assignedBeneficiaries}
                    </dd>
                  </div>
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <dt className="text-slate-500">Visits Logged</dt>
                    <dd className="text-base font-bold tabular-nums text-clinical-primary">
                      {row.completedVisits}
                    </dd>
                  </div>
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <dt className="text-slate-500">Pending Tasks</dt>
                    <dd className="text-base font-bold tabular-nums text-amber-700">
                      {row.pendingFollowUps}
                    </dd>
                  </div>
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <dt className="text-slate-500">Active Alerts</dt>
                    <dd
                      className={`text-base font-bold tabular-nums ${
                        row.activeAlerts > 0 ? 'text-clinical-danger' : 'text-slate-700'
                      }`}
                    >
                      {row.activeAlerts}
                    </dd>
                  </div>
                </dl>
              </div>

              <button
                type="button"
                onClick={() => setSelectedWorker(row)}
                className="w-full py-2.5 px-3 rounded-xl border border-slate-300 hover:bg-slate-50 text-xs font-bold text-clinical-text"
              >
                View Worker Activity
              </button>
            </article>
          ))}
        </div>
      )}

      {selectedWorker && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="worker-drawer-title"
          className="fixed inset-0 z-50 bg-slate-900/50 flex justify-end"
        >
          <div className="bg-white w-full max-w-md h-full overflow-y-auto p-5 sm:p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between gap-2 pb-3 border-b border-slate-200">
              <div>
                <h2 id="worker-drawer-title" className="text-lg font-bold text-clinical-text">
                  {selectedWorker.worker.full_name}
                </h2>
                <p className="text-xs text-slate-500">
                  {selectedWorker.worker.worker_code} · {selectedWorker.worker.assigned_area}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedWorker(null)}
                aria-label="Close worker details"
                className="p-2 rounded-lg text-slate-500 hover:bg-slate-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <h3 className="text-sm font-bold text-clinical-text">
              Recent Visits ({workerVisits.length})
            </h3>
            {workerVisits.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No visits recorded by this worker yet.</p>
            ) : (
              <ul className="space-y-2.5">
                {workerVisits.map((v) => (
                  <li
                    key={v.visit_id}
                    className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1"
                  >
                    <div className="flex justify-between font-bold">
                      <span>{v.beneficiary_name || v.beneficiary_id}</span>
                      <span>{v.visit_type}</span>
                    </div>
                    <p className="text-slate-500 tabular-nums">
                      {new Date(v.visit_date).toLocaleString()}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export const SupervisorVisitRegisterView: React.FC<{
  visits: VisitDraft[];
  workers: WorkerMetricsRow[];
}> = ({ visits, workers }) => {
  const { ui } = useTranslation();
  const [search, setSearch] = useState('');
  const [visitTypeFilter, setVisitTypeFilter] = useState('ALL');
  const [workerFilter, setWorkerFilter] = useState('ALL');
  const [dangerOnly, setDangerOnly] = useState(false);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return visits.filter((v) => {
      if (visitTypeFilter !== 'ALL' && v.visit_type !== visitTypeFilter) return false;
      if (workerFilter !== 'ALL' && v.asha_worker_id !== workerFilter) return false;
      if (dangerOnly && !v.danger_sign_flagged) return false;
      if (q) {
        const hay = `${v.beneficiary_name || ''} ${v.beneficiary_id || ''} ${v.visit_id}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [visits, search, visitTypeFilter, workerFilter, dangerOnly]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-clinical-text">{ui.fieldRegister}</h1>
        <p className="text-xs sm:text-sm text-clinical-text-secondary">
          {ui.fieldRegisterSubtitle}
        </p>
      </div>

      {/* Filters Toolbar */}
      <div className="bg-white border border-clinical-border-subtle rounded-2xl p-4 shadow-sm grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="relative">
          <Search
            className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
            aria-hidden="true"
          />
          <label htmlFor="reg-search" className="sr-only">
            Search visits
          </label>
          <input
            id="reg-search"
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Beneficiary name or BEN-ID..."
            className="w-full pl-9 pr-3 py-2 rounded-xl border border-clinical-border text-xs bg-slate-50"
          />
        </div>

        <div>
          <label htmlFor="reg-type-filter" className="sr-only">
            Filter by visit type
          </label>
          <select
            id="reg-type-filter"
            value={visitTypeFilter}
            onChange={(e) => setVisitTypeFilter(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-clinical-border text-xs font-semibold bg-slate-50"
          >
            <option value="ALL">All Visit Types</option>
            <option value="ANC">ANC</option>
            <option value="PNC">PNC</option>
            <option value="Newborn">Newborn</option>
            <option value="Immunisation">Immunisation</option>
          </select>
        </div>

        <div>
          <label htmlFor="reg-worker-filter" className="sr-only">
            Filter by ASHA worker
          </label>
          <select
            id="reg-worker-filter"
            value={workerFilter}
            onChange={(e) => setWorkerFilter(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-clinical-border text-xs font-semibold bg-slate-50"
          >
            <option value="ALL">All ASHA Workers</option>
            {workers.map((w) => (
              <option key={w.worker.id} value={w.worker.id}>
                {w.worker.full_name}
              </option>
            ))}
          </select>
        </div>

        <label className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-clinical-border bg-slate-50 text-xs font-semibold text-clinical-text cursor-pointer">
          <input
            type="checkbox"
            checked={dangerOnly}
            onChange={(e) => setDangerOnly(e.target.checked)}
            className="rounded border-slate-300 text-clinical-danger"
          />
          <span>Danger Sign Flagged Only</span>
        </label>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title="No visits match selected filters"
          description="Adjust your search or visit-type filters to view field records."
          icon={<ClipboardList className="h-5 w-5" />}
        />
      ) : (
        <div
          tabIndex={0}
          role="region"
          aria-labelledby="sup-register-caption"
          className="clinical-table-wrapper bg-white border border-clinical-border-subtle rounded-2xl shadow-sm"
        >
          <table className="responsive-clinical-table w-full text-left text-xs border-collapse">
            <caption id="sup-register-caption" className="sr-only">
              PHC Supervisor Field Visit Register
            </caption>
            <thead className="bg-slate-50 border-b border-slate-200 font-bold text-slate-600">
              <tr>
                <th scope="col" className="p-3.5">Date</th>
                <th scope="col" className="p-3.5">Beneficiary</th>
                <th scope="col" className="p-3.5">ASHA Worker</th>
                <th scope="col" className="p-3.5">Type</th>
                <th scope="col" className="p-3.5">Weight</th>
                <th scope="col" className="p-3.5">Danger Sign</th>
                <th scope="col" className="p-3.5">Next Visit</th>
                <th scope="col" className="p-3.5">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((v) => (
                <tr key={v.visit_id || v.draft_id} className="hover:bg-slate-50">
                  <td data-label="Date" className="p-3.5 tabular-nums">
                    {new Date(v.visit_date).toLocaleDateString()}
                  </td>
                  <td data-label="Beneficiary" className="p-3.5">
                    <span className="font-bold text-clinical-text block">
                      {v.beneficiary_name || 'Unlinked'}
                    </span>
                    <span className="font-mono text-[11px] text-slate-500">
                      {v.beneficiary_id || '—'}
                    </span>
                  </td>
                  <td data-label="ASHA Worker" className="p-3.5 text-slate-700">
                    {v.worker_name || v.asha_worker_id}
                  </td>
                  <td data-label="Type" className="p-3.5">
                    <span className="px-2 py-0.5 rounded bg-slate-100 font-mono font-bold">
                      {v.visit_type || 'General'}
                    </span>
                  </td>
                  <td data-label="Weight" className="p-3.5 tabular-nums font-semibold">
                    {v.weight_kg !== null ? `${v.weight_kg} kg` : '—'}
                  </td>
                  <td data-label="Danger Sign" className="p-3.5">
                    {v.danger_sign_flagged ? (
                      <span className="inline-flex items-center gap-1 font-bold text-red-800 bg-red-100 px-2 py-0.5 rounded-full">
                        <AlertTriangle className="h-3 w-3" aria-hidden="true" />
                        Flagged
                      </span>
                    ) : (
                      <span className="text-emerald-700 font-semibold">Normal</span>
                    )}
                  </td>
                  <td data-label="Next Visit" className="p-3.5 tabular-nums text-slate-600">
                    {v.next_visit_date || '—'}
                  </td>
                  <td data-label="Status" className="p-3.5">
                    <span className="inline-flex items-center gap-1 font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-full">
                      <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                      {v.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

