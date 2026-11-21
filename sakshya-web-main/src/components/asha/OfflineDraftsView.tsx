'use client';

import React, { useEffect, useState } from 'react';
import { EmptyState } from '@/components/ui/ClinicalUI';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import {
  deleteLocalDraft,
  getAllLocalDrafts,
  saveDraftLocally,
} from '@/lib/offline/indexeddb-store';
import { syncManager } from '@/lib/sync/sync-manager';
import type { VisitDraft } from '@/types';
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  Info,
  RefreshCw,
  Trash2,
  WifiOff,
} from 'lucide-react';

interface OfflineDraftsViewProps {
  onSynced?: () => void;
}

export const OfflineDraftsView: React.FC<OfflineDraftsViewProps> = ({ onSynced }) => {
  const { ui } = useTranslation();
  const [drafts, setDrafts] = useState<VisitDraft[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);

  const load = async () => {
    const items = await getAllLocalDrafts();
    setDrafts(items);
  };

  useEffect(() => {
    load();
    const unsub = syncManager.subscribe(() => {
      setIsSyncing(syncManager.isCurrentlySyncing());
      load();
    });
    return () => unsub();
  }, []);

  const handleSyncNow = async () => {
    setIsSyncing(true);
    await syncManager.triggerSync();
    setIsSyncing(false);
    await load();
    onSynced?.();
  };

  const handleResolveConflictKeepLocal = async (draft: VisitDraft) => {
    await saveDraftLocally({
      ...draft,
      sync_status: 'pending',
      last_sync_error: undefined,
      updated_at: new Date().toISOString(),
    });
    await handleSyncNow();
  };

  const handleDelete = async (draftId: string) => {
    await deleteLocalDraft(draftId);
    await load();
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-clinical-text">
            {ui.offlineDraftsTitle}
          </h1>
          <p className="text-xs sm:text-sm text-clinical-text-secondary">
            {ui.offlineDraftsSubtitle}
          </p>
        </div>

        <button
          type="button"
          onClick={handleSyncNow}
          disabled={isSyncing}
          className="px-4 py-2.5 rounded-xl bg-clinical-primary hover:bg-clinical-primary-dark text-white text-xs font-bold flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${isSyncing ? 'animate-spin' : ''}`} aria-hidden="true" />
          <span>{isSyncing ? ui.syncingConfirmedVisits : ui.syncConfirmedQueue}</span>
        </button>
      </div>

      {/* Truthful Offline Scope Notice */}
      <div className="p-3.5 rounded-xl bg-sky-50 border border-sky-200 text-xs text-sky-950 flex items-start gap-2.5">
        <Info className="h-4 w-4 text-clinical-secondary shrink-0 mt-0.5" aria-hidden="true" />
        <div>
          <p className="font-bold">{ui.offlinePolicyTitle}</p>
          <p className="mt-0.5 leading-relaxed">
            {ui.offlinePolicyDesc}
          </p>
        </div>
      </div>

      {drafts.length === 0 ? (
        <EmptyState
          title={ui.noLocalDrafts}
          description={ui.noLocalDraftsDesc}
          icon={<Database className="h-5 w-5" />}
        />
      ) : (
        <ul className="space-y-3">
          {drafts.map((d) => (
            <li
              key={d.draft_id}
              className="bg-white border border-clinical-border-subtle rounded-2xl p-4 shadow-sm space-y-2.5"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="font-bold text-sm text-clinical-text">
                    {d.beneficiary_name || d.beneficiary_id || 'Unresolved Beneficiary'}
                  </span>
                  <span className="ml-2 font-mono text-[11px] text-slate-500">{d.visit_id}</span>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                    Record: {d.status}
                  </span>
                  <SyncPill status={d.sync_status} />
                </div>
              </div>

              {d.last_sync_error && (
                <div className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-xs text-red-900 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-clinical-danger" />
                  <span>{d.last_sync_error}</span>
                </div>
              )}

              <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 text-xs text-slate-500">
                <span className="tabular-nums">
                  Updated {new Date(d.updated_at).toLocaleString()}
                </span>
                <div className="flex items-center gap-2">
                  {d.sync_status === 'conflict' && (
                    <button
                      type="button"
                      onClick={() => handleResolveConflictKeepLocal(d)}
                      className="px-3 py-1.5 rounded-lg bg-amber-600 text-white font-bold text-xs"
                    >
                      Retry Overwrite Local
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => handleDelete(d.draft_id)}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:text-red-700 hover:border-red-200 font-semibold"
                  >
                    <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    <span>Remove Local</span>
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

const SyncPill: React.FC<{ status: VisitDraft['sync_status'] }> = ({ status }) => {
  if (status === 'synced') {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
        <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
        Synced
      </span>
    );
  }
  if (status === 'conflict' || status === 'failed') {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-red-100 text-red-800">
        <AlertTriangle className="h-3 w-3" aria-hidden="true" />
        {status}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900">
      <WifiOff className="h-3 w-3" aria-hidden="true" />
      {status}
    </span>
  );
};

