import { getAllLocalDrafts, updateDraftSyncStatus } from '@/lib/offline/indexeddb-store';
import { supabase, syntheticRepo } from '@/lib/supabase/client';
import { VisitDraft } from '@/types';

class SyncManager {
  private isSyncing = false;
  private listeners: Array<() => void> = [];

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => {
        this.triggerSync();
      });
    }
  }

  subscribe(listener: () => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  private notify() {
    this.listeners.forEach((l) => l());
  }

  async triggerSync(): Promise<{ total: number; synced: number; failed: number }> {
    if (this.isSyncing) return { total: 0, synced: 0, failed: 0 };
    this.isSyncing = true;
    this.notify();

    let synced = 0;
    let failed = 0;
    const drafts = await getAllLocalDrafts();
    const pendingDrafts = drafts.filter(
      (d) => d.sync_status === 'pending' || d.sync_status === 'failed' || d.sync_status === 'draft'
    );

    for (const draft of pendingDrafts) {
      try {
        await updateDraftSyncStatus(draft.draft_id, 'syncing');
        this.notify();

        if (supabase) {
          const { error } = await supabase.from('visits').upsert(
            {
              client_draft_id: draft.draft_id,
              idempotency_key: draft.idempotency_key,
              beneficiary_id: draft.beneficiary_id,
              asha_worker_id: draft.asha_worker_id,
              phc_id: draft.phc_id,
              visit_date: draft.visit_date,
              visit_type: draft.visit_type,
              language: draft.language,
              vitals: draft.vitals,
              immunisations_administered: draft.immunisations_administered,
              ifa_tablets_given: draft.ifa_tablets_given || 0,
              danger_sign_flagged: draft.danger_signs_present,
              danger_sign_details: draft.danger_signs,
              follow_up_required: draft.follow_up_required,
              follow_up_date: draft.follow_up_date || null,
              follow_up_reason: draft.follow_up_reason || null,
              notes: draft.notes || null,
              read_back_confirmed: draft.read_back_confirmed,
              sync_status: 'synced',
            },
            { onConflict: 'idempotency_key' }
          );

          if (error) throw error;
        }

        // Always register in synthetic repo as well
        syntheticRepo.addVisit({
          ...draft,
          sync_status: 'synced',
        });

        await updateDraftSyncStatus(draft.draft_id, 'synced');
        synced++;
      } catch (err: any) {
        console.error('Failed to sync draft', draft.draft_id, err);
        await updateDraftSyncStatus(draft.draft_id, 'failed', err?.message || 'Sync failed');
        failed++;
      }
    }

    this.isSyncing = false;
    this.notify();
    return { total: pendingDrafts.length, synced, failed };
  }

  isCurrentlySyncing(): boolean {
    return this.isSyncing;
  }
}

export const syncManager = new SyncManager();
