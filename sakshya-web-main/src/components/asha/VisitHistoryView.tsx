'use client';

import React, { useState } from 'react';
import { EmptyState } from '@/components/ui/ClinicalUI';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type { VisitDraft } from '@/types';
import { AlertTriangle, CheckCircle2, FileText, X } from 'lucide-react';

interface VisitHistoryViewProps {
  visits: VisitDraft[];
  onClearVisits?: () => void;
}

export const VisitHistoryView: React.FC<VisitHistoryViewProps> = ({ visits, onClearVisits }) => {
  const { ui } = useTranslation();
  const [selectedVisit, setSelectedVisit] = useState<VisitDraft | null>(null);

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-clinical-text">{ui.visitHistoryTitle}</h1>
          <p className="text-xs sm:text-sm text-clinical-text-secondary">
            {ui.visitHistorySubtitle}
          </p>
        </div>
        {visits.length > 0 && onClearVisits && (
          <button
            type="button"
            onClick={onClearVisits}
            className="text-xs font-medium text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 px-3 py-1.5 rounded-lg transition-colors"
          >
            Clear All Visits
          </button>
        )}
      </div>

      {visits.length === 0 ? (
        <EmptyState
          title={ui.noSavedVisitsYet}
          description={ui.noSavedVisitsDesc}
          icon={<FileText className="h-5 w-5" />}
        />
      ) : (
        <div
          tabIndex={0}
          role="region"
          aria-labelledby="visit-history-caption"
          className="clinical-table-wrapper bg-white border border-clinical-border-subtle rounded-2xl shadow-sm"
        >
          <table className="responsive-clinical-table w-full text-left text-xs sm:text-sm border-collapse">
            <caption id="visit-history-caption" className="sr-only">
              {ui.visitHistoryTitle}
            </caption>
            <thead className="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-600">
              <tr>
                <th scope="col" className="p-3.5">{ui.colDate}</th>
                <th scope="col" className="p-3.5">{ui.colBeneficiary}</th>
                <th scope="col" className="p-3.5">{ui.colType}</th>
                <th scope="col" className="p-3.5">{ui.colWeight}</th>
                <th scope="col" className="p-3.5">{ui.colDangerSign}</th>
                <th scope="col" className="p-3.5">{ui.colStatus}</th>
                <th scope="col" className="p-3.5">{ui.colAction}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {visits.map((v) => (
                <tr key={v.visit_id || v.draft_id} className="hover:bg-slate-50">
                  <td data-label="Date" className="p-3.5 tabular-nums text-slate-700">
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
                  <td data-label="Type" className="p-3.5">
                    <span className="px-2 py-0.5 rounded bg-slate-100 font-mono text-xs font-semibold">
                      {v.visit_type || 'General'}
                    </span>
                  </td>
                  <td data-label="Weight" className="p-3.5 tabular-nums font-semibold">
                    {v.weight_kg !== null ? `${v.weight_kg} kg` : '—'}
                  </td>
                  <td data-label="Danger Sign" className="p-3.5">
                    {v.danger_sign_flagged ? (
                      <span className="inline-flex items-center gap-1 text-xs font-bold text-red-800 bg-red-100 px-2.5 py-0.5 rounded-full">
                        <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
                        Flagged
                      </span>
                    ) : (
                      <span className="text-xs font-semibold text-emerald-700">Clear</span>
                    )}
                  </td>
                  <td data-label="Status" className="p-3.5">
                    <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                      <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                      {v.status}
                    </span>
                  </td>
                  <td data-label="Details" className="p-3.5">
                    <button
                      type="button"
                      onClick={() => setSelectedVisit(v)}
                      className="text-xs font-bold text-clinical-primary hover:underline"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail Modal */}
      {selectedVisit && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="visit-detail-title"
          className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center p-4"
        >
          <div className="bg-white rounded-2xl max-w-lg w-full p-5 sm:p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between gap-2 pb-3 border-b border-slate-200">
              <div>
                <h2 id="visit-detail-title" className="text-lg font-bold text-clinical-text">
                  Visit Record · {selectedVisit.visit_id}
                </h2>
                <p className="text-xs text-slate-500">
                  {selectedVisit.beneficiary_name} ({selectedVisit.beneficiary_id})
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedVisit(null)}
                aria-label="Close visit detail"
                className="p-2 rounded-lg text-slate-500 hover:bg-slate-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <dl className="grid grid-cols-2 gap-2.5 text-xs">
              <dt className="text-slate-500">Visit Type</dt>
              <dd className="font-bold">{selectedVisit.visit_type || '—'}</dd>
              <dt className="text-slate-500">Weight</dt>
              <dd className="font-bold tabular-nums">
                {selectedVisit.weight_kg !== null ? `${selectedVisit.weight_kg} kg` : '—'}
              </dd>
              <dt className="text-slate-500">Vaccinations Completed</dt>
              <dd>{selectedVisit.vaccinations_completed.join(', ') || 'None'}</dd>
              <dt className="text-slate-500">Vaccinations Due</dt>
              <dd>{selectedVisit.vaccinations_due.join(', ') || 'None'}</dd>
              <dt className="text-slate-500">Next Visit Date</dt>
              <dd className="tabular-nums font-semibold">{selectedVisit.next_visit_date || '—'}</dd>
              <dt className="text-slate-500">Persistence Ref</dt>
              <dd className="font-mono">{selectedVisit.persistence_record_id || 'Local'}</dd>
            </dl>

            {selectedVisit.raw_transcript_summary && (
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                <span className="font-bold text-slate-600 block mb-1">Summary Transcript:</span>
                <p className="text-clinical-text leading-relaxed">
                  {selectedVisit.raw_transcript_summary}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

