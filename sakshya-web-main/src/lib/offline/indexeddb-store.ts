import { openDB, DBSchema, IDBPDatabase } from 'idb';
import type { Beneficiary, SyncStatus, VisitDraft } from '@/types';

interface AshaDB extends DBSchema {
  visit_drafts: {
    key: string;
    value: VisitDraft;
    indexes: {
      'by-sync-status': SyncStatus;
      'by-beneficiary': string;
      'by-date': string;
    };
  };
  cached_beneficiaries: {
    key: string;
    value: Beneficiary;
  };
}

const DB_NAME = 'asha_field_register_v2';
const DB_VERSION = 1;

let dbPromise: Promise<IDBPDatabase<AshaDB>> | null = null;

function getDB(): Promise<IDBPDatabase<AshaDB>> {
  if (typeof window === 'undefined' || typeof indexedDB === 'undefined') {
    return Promise.reject(new Error('IndexedDB is only accessible in browser runtime'));
  }
  if (!dbPromise) {
    dbPromise = openDB<AshaDB>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains('visit_drafts')) {
          const store = db.createObjectStore('visit_drafts', { keyPath: 'draft_id' });
          store.createIndex('by-sync-status', 'sync_status');
          store.createIndex('by-beneficiary', 'beneficiary_id');
          store.createIndex('by-date', 'visit_date');
        }
        if (!db.objectStoreNames.contains('cached_beneficiaries')) {
          db.createObjectStore('cached_beneficiaries', { keyPath: 'beneficiary_id' });
        }
      },
    });
  }
  return dbPromise;
}

export async function saveDraftLocally(draft: VisitDraft): Promise<void> {
  const db = await getDB();
  await db.put('visit_drafts', {
    ...draft,
    updated_at: new Date().toISOString(),
  });
}

export async function getDraftLocally(draftId: string): Promise<VisitDraft | undefined> {
  const db = await getDB();
  return db.get('visit_drafts', draftId);
}

export async function getAllLocalDrafts(): Promise<VisitDraft[]> {
  if (typeof window === 'undefined' || typeof indexedDB === 'undefined') return [];
  try {
    const db = await getDB();
    const list = await db.getAll('visit_drafts');
    return list.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
  } catch {
    return [];
  }
}

export async function getPendingDrafts(): Promise<VisitDraft[]> {
  const all = await getAllLocalDrafts();
  return all.filter(
    (d) =>
      d.status === 'confirmed' &&
      (d.sync_status === 'pending' || d.sync_status === 'failed')
  );
}

export async function updateDraftSyncStatus(
  draftId: string,
  status: SyncStatus,
  error?: string,
  persistenceRecordId?: string | null,
  committedAt?: string | null
): Promise<void> {
  const db = await getDB();
  const draft = await db.get('visit_drafts', draftId);
  if (draft) {
    draft.sync_status = status;
    if (error !== undefined) {
      draft.last_sync_error = error;
    }
    if (persistenceRecordId) {
      draft.persistence_record_id = persistenceRecordId;
      draft.status = 'committed';
    }
    if (committedAt) {
      draft.committed_at = committedAt;
    }
    draft.updated_at = new Date().toISOString();
    await db.put('visit_drafts', draft);
  }
}

export async function deleteLocalDraft(draftId: string): Promise<void> {
  const db = await getDB();
  await db.delete('visit_drafts', draftId);
}

export async function clearWorkerLocalData(): Promise<void> {
  if (typeof window === 'undefined' || typeof indexedDB === 'undefined') return;
  try {
    const db = await getDB();
    await db.clear('visit_drafts');
  } catch {
    // ignore cleanup errors
  }
}

export async function cacheBeneficiariesLocally(beneficiaries: Beneficiary[]): Promise<void> {
  if (typeof window === 'undefined' || typeof indexedDB === 'undefined') return;
  try {
    const db = await getDB();
    const tx = db.transaction('cached_beneficiaries', 'readwrite');
    for (const b of beneficiaries) {
      await tx.store.put(b);
    }
    await tx.done;
  } catch {
    // non-fatal
  }
}

export async function getCachedBeneficiariesLocally(): Promise<Beneficiary[]> {
  if (typeof window === 'undefined' || typeof indexedDB === 'undefined') return [];
  try {
    const db = await getDB();
    return db.getAll('cached_beneficiaries');
  } catch {
    return [];
  }
}
