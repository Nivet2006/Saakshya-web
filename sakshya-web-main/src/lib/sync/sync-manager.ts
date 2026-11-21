import { fastApiClient } from '@/lib/api/fastapi-client';
import {
  getAllLocalDrafts,
  saveDraftLocally,
  updateDraftSyncStatus,
} from '@/lib/offline/indexeddb-store';
import { isRealSupabaseConfigured, supabase } from '@/lib/supabase/client';
import { dataService } from '@/services/data-service';
import type { VisitDraft } from '@/types';

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

  async persistConfirmedVisitNow(
    draft: VisitDraft,
    correlationId?: string
  ): Promise<{
    accepted: boolean;
    persistenceRecordId: string | null;
    committedAt: string | null;
    errorMessage?: string;
  }> {
    // Hard safety rule: NEVER persist an unconfirmed draft as a completed visit
    if (draft.status === 'draft' || !draft.confirmed_at) {
      return {
        accepted: false,
        persistenceRecordId: null,
        committedAt: null,
        errorMessage: 'Cannot persist unconfirmed draft. Explicit worker confirmation is required.',
      };
    }

    const committedAt = new Date().toISOString();
    let persistenceRecordId = draft.persistence_record_id || `supa_${draft.visit_id}`;

    try {
      if (supabase && isRealSupabaseConfigured) {
        // Conflict check: look up existing record by visit_id / idempotency_key
        const { data: existing } = await supabase
          .from('visits')
          .select('id, updated_at')
          .eq('idempotency_key', draft.idempotency_key)
          .maybeSingle();

        if (existing?.updated_at && new Date(existing.updated_at) > new Date(draft.updated_at)) {
          await saveDraftLocally({
            ...draft,
            sync_status: 'conflict',
            last_sync_error: 'Remote visit record is newer than local draft.',
          });
          this.notify();
          return {
            accepted: false,
            persistenceRecordId: null,
            committedAt: null,
            errorMessage: 'Conflict: remote visit record has a newer timestamp.',
          };
        }

        const { data: upserted, error } = await supabase
          .from('visits')
          .upsert(
            {
              client_draft_id: draft.draft_id,
              idempotency_key: draft.idempotency_key,
              beneficiary_id: draft.beneficiary_uuid,
              asha_worker_id: draft.asha_worker_id,
              phc_id: draft.phc_id,
              visit_date: draft.visit_date,
              visit_type: mapVisitTypeToSql(draft.visit_type),
              language: draft.language,
              vitals: {
                weight_kg: draft.weight_kg,
                weight_source_text: draft.weight_source_text,
              },
              immunisations_administered: draft.vaccinations_completed,
              danger_sign_flagged: draft.danger_sign_flagged,
              danger_sign_details: draft.danger_alerts,
              follow_up_required: draft.follow_up_actions.length > 0 || !!draft.next_visit_date,
              follow_up_date: draft.next_visit_date || null,
              follow_up_reason: draft.follow_up_actions[0]?.description || null,
              notes: draft.raw_transcript_summary || null,
              raw_transcript_summary: draft.raw_transcript_summary || null,
              read_back_confirmed: true,
              sync_status: 'synced',
            },
            { onConflict: 'idempotency_key' }
          )
          .select('id')
          .single();

        if (error) throw error;
        if (upserted?.id) {
          persistenceRecordId = upserted.id;
        }
      }

      const committedDraft: VisitDraft = {
        ...draft,
        status: 'committed',
        committed_at: committedAt,
        persistence_record_id: persistenceRecordId,
        sync_status: 'synced',
        last_sync_error: undefined,
        updated_at: committedAt,
      };

      await saveDraftLocally(committedDraft);
      dataService.recordCommittedVisit(committedDraft);

      // Acknowledge durable persistence back to Agent 1 if correlationId provided
      if (correlationId && draft.session_id) {
        try {
          await fastApiClient.acknowledgePersistence(draft.session_id, {
            schema_version: 'v1',
            visit_id: draft.visit_id,
            correlation_id: correlationId,
            accepted: true,
            persistence_record_id: persistenceRecordId,
            committed_at: committedAt,
          });
        } catch {
          // WS ack still works even if HTTP session already cleaned up
        }
      }

      this.notify();
      return {
        accepted: true,
        persistenceRecordId,
        committedAt,
      };
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Persistence failed';
      await saveDraftLocally({
        ...draft,
        sync_status: 'failed',
        last_sync_error: msg,
      });
      this.notify();
      return {
        accepted: false,
        persistenceRecordId: null,
        committedAt: null,
        errorMessage: msg,
      };
    }
  }

  async triggerSync(): Promise<{ total: number; synced: number; failed: number }> {
    if (this.isSyncing) return { total: 0, synced: 0, failed: 0 };
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      return { total: 0, synced: 0, failed: 0 };
    }

    this.isSyncing = true;
    this.notify();

    let synced = 0;
    let failed = 0;
    const drafts = await getAllLocalDrafts();
    // Strictly sync ONLY confirmed visits — never auto-commit unconfirmed drafts!
    const syncable = drafts.filter(
      (d) =>
        (d.status === 'confirmed' || d.status === 'committed') &&
        (d.sync_status === 'pending' || d.sync_status === 'failed')
    );

    for (const draft of syncable) {
      await updateDraftSyncStatus(draft.draft_id, 'syncing');
      this.notify();
      const result = await this.persistConfirmedVisitNow(draft);
      if (result.accepted) {
        synced++;
      } else {
        failed++;
      }
    }

    this.isSyncing = false;
    this.notify();
    return { total: syncable.length, synced, failed };
  }

  isCurrentlySyncing(): boolean {
    return this.isSyncing;
  }
}

function mapVisitTypeToSql(visitType: VisitDraft['visit_type']): string {
  switch (visitType) {
    case 'ANC':
      return 'ANC_1';
    case 'PNC':
      return 'PNC_DAY_7';
    case 'Newborn':
      return 'CHILD_GROWTH';
    case 'Immunisation':
      return 'IMMUNISATION';
    default:
      return 'GENERAL_CHECKUP';
  }
}

export const syncManager = new SyncManager();
