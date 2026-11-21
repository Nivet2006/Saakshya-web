'use client';

import React, { useMemo, useState } from 'react';
import { EmptyState } from '@/components/ui/ClinicalUI';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type { FollowUpTask, ImmunisationScheduleItem } from '@/types';
import { CalendarClock, CheckCircle2, Search, Syringe } from 'lucide-react';

interface FollowUpQueueViewProps {
  followUps: FollowUpTask[];
  immunisations: ImmunisationScheduleItem[];
  onToggleFollowUp: (taskId: string) => void;
}

export const FollowUpQueueView: React.FC<FollowUpQueueViewProps> = ({
  followUps,
  immunisations,
  onToggleFollowUp,
}) => {
  const { ui } = useTranslation();
  const [tab, setTab] = useState<'upcoming' | 'overdue' | 'vaccines' | 'completed'>('upcoming');
  const [search, setSearch] = useState('');

  const today = new Date().toISOString().split('T')[0];

  const filteredTasks = useMemo(() => {
    const q = search.trim().toLowerCase();
    return followUps.filter((task) => {
      const matchSearch =
        !q ||
        task.task_type.toLowerCase().includes(q) ||
        (task.beneficiary_name || '').toLowerCase().includes(q) ||
        task.beneficiary_id.toLowerCase().includes(q);
      if (!matchSearch) return false;
      if (tab === 'completed') return task.status === 'COMPLETED';
      if (tab === 'overdue') {
        return task.status !== 'COMPLETED' && (task.status === 'OVERDUE' || task.due_date < today);
      }
      if (tab === 'upcoming') {
        return task.status !== 'COMPLETED' && task.status !== 'OVERDUE' && task.due_date >= today;
      }
      return true;
    });
  }, [followUps, tab, search, today]);

  const pendingVaccines = useMemo(() => {
    const q = search.trim().toLowerCase();
    return immunisations.filter((i) => {
      const match =
        !q ||
        i.vaccine_name.toLowerCase().includes(q) ||
        (i.beneficiary_name || '').toLowerCase().includes(q);
      return match && (i.status === 'DUE' || i.status === 'OVERDUE');
    });
  }, [immunisations, search]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-clinical-text">
            {ui.followUpsTitle}
          </h1>
          <p className="text-xs sm:text-sm text-clinical-text-secondary">
            {ui.followUpsSubtitle}
          </p>
        </div>

        <div className="relative w-full sm:w-64">
          <Search
            className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
            aria-hidden="true"
          />
          <label htmlFor="followup-search" className="sr-only">
            {ui.searchFollowUpsPlaceholder}
          </label>
          <input
            id="followup-search"
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={ui.searchFollowUpsPlaceholder}
            className="w-full pl-9 pr-3 py-2 rounded-xl border border-clinical-border bg-white text-sm"
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {[
          { id: 'upcoming', label: ui.upcomingTasks },
          { id: 'overdue', label: ui.overdueTab },
          { id: 'vaccines', label: `${ui.pendingVaccinesTab} (${pendingVaccines.length})` },
          { id: 'completed', label: ui.completedTab },
        ].map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id as typeof tab)}
            className={`compact-chip px-3.5 py-2 rounded-xl text-xs font-bold border whitespace-nowrap ${
              tab === item.id
                ? 'bg-clinical-primary text-white border-clinical-primary'
                : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === 'vaccines' ? (
        pendingVaccines.length === 0 ? (
          <EmptyState
            title={ui.noPendingVaccines}
            description={ui.noPendingVaccinesDesc}
            icon={<Syringe className="h-5 w-5" />}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {pendingVaccines.map((v) => (
              <div
                key={v.id}
                className={`p-4 rounded-2xl bg-white border shadow-sm flex items-center justify-between gap-3 ${
                  v.status === 'OVERDUE' ? 'border-red-300 bg-red-50/30' : 'border-slate-200'
                }`}
              >
                <div>
                  <p className="font-bold text-sm text-clinical-text">
                    {v.vaccine_name} (Dose {v.dose_number})
                  </p>
                  <p className="text-xs text-slate-600 mt-0.5">
                    {v.beneficiary_name || v.beneficiary_id} ({v.beneficiary_id})
                  </p>
                  <p className="text-xs text-slate-500 mt-1 tabular-nums">{ui.dueDateLabel}: {v.due_date}</p>
                </div>
                <span
                  className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                    v.status === 'OVERDUE'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {v.status}
                </span>
              </div>
            ))}
          </div>
        )
      ) : filteredTasks.length === 0 ? (
        <EmptyState
          title={ui.noTasksInQueue}
          description={ui.noTasksInQueueDesc}
          icon={<CalendarClock className="h-5 w-5" />}
        />
      ) : (
        <ul className="space-y-3">
          {filteredTasks.map((task) => (
            <li
              key={task.id}
              className={`bg-white p-4 rounded-2xl border shadow-sm flex items-start gap-3 ${
                task.priority === 'URGENT' && task.status !== 'COMPLETED'
                  ? 'border-red-300 bg-red-50/30'
                  : 'border-clinical-border-subtle'
              }`}
            >
              <button
                type="button"
                onClick={() => onToggleFollowUp(task.id)}
                aria-label={`Mark ${task.task_type} as ${
                  task.status === 'COMPLETED' ? 'pending' : 'completed'
                }`}
                className="mt-0.5 text-slate-400 hover:text-clinical-primary shrink-0"
              >
                {task.status === 'COMPLETED' ? (
                  <CheckCircle2 className="h-6 w-6 text-clinical-success" />
                ) : (
                  <span className="block w-6 h-6 rounded-md border-2 border-slate-300" />
                )}
              </button>

              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p
                    className={`font-bold text-sm ${
                      task.status === 'COMPLETED'
                        ? 'line-through text-slate-400'
                        : 'text-clinical-text'
                    }`}
                  >
                    {task.task_type}
                  </p>
                  <span
                    className={`text-[11px] font-bold uppercase px-2.5 py-0.5 rounded-full ${
                      task.priority === 'URGENT'
                        ? 'bg-red-100 text-red-800'
                        : task.priority === 'HIGH'
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    {task.priority}
                  </span>
                </div>
                <p className="text-xs text-slate-600 mt-1">
                  {ui.beneficiaryLabel}: <strong>{task.beneficiary_name || task.beneficiary_id}</strong> · {ui.dueLabel}{' '}
                  <span className="tabular-nums font-semibold">{task.due_date}</span>
                </p>
                {task.notes && <p className="text-xs text-slate-500 mt-1">{task.notes}</p>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

