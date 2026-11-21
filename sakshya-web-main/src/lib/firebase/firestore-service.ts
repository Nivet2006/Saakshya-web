import {
  collection,
  doc,
  getDocs,
  getDoc,
  setDoc,
  addDoc,
  updateDoc,
  deleteDoc,
  query,
  where,
  orderBy,
  limit,
  onSnapshot,
  serverTimestamp,
} from 'firebase/firestore';
import { db, isFirebaseConfigured } from './client';
import type {
  AuditLogEntry,
  Beneficiary,
  DangerAlert,
  Facility,
  FollowUpTask,
  ImmunisationScheduleItem,
  UserProfile,
  VisitDraft,
} from '@/types';

// Collection references
const COL_BENEFICIARIES = 'beneficiaries';
const COL_VISITS = 'visits';
const COL_DANGER_ALERTS = 'danger_alerts';
const COL_FOLLOW_UPS = 'follow_ups';
const COL_IMMUNISATIONS = 'immunisations';
const COL_PROFILES = 'user_profiles';
const COL_FACILITIES = 'facilities';
const COL_AUDIT_LOGS = 'audit_logs';

export const firestoreService = {
  isConfigured: () => isFirebaseConfigured,

  // ── Beneficiaries ──────────────────────────────────────────────────────────
  async getBeneficiaries(): Promise<Beneficiary[]> {
    if (!isFirebaseConfigured) return [];
    try {
      const q = query(collection(db, COL_BENEFICIARIES), orderBy('beneficiary_id', 'asc'));
      const snapshot = await getDocs(q);
      return snapshot.docs.map((docSnap) => ({
        id: docSnap.id,
        ...(docSnap.data() as Omit<Beneficiary, 'id'>),
      }));
    } catch (err) {
      console.warn('[Firebase] Failed to fetch beneficiaries:', err);
      return [];
    }
  },

  async addBeneficiary(b: Beneficiary): Promise<void> {
    if (!isFirebaseConfigured) return;
    const docId = b.id || b.beneficiary_id;
    await setDoc(
      doc(db, COL_BENEFICIARIES, docId),
      {
        ...b,
        updated_at: new Date().toISOString(),
      },
      { merge: true }
    );
  },

  // ── Visits ─────────────────────────────────────────────────────────────────
  async getVisits(): Promise<VisitDraft[]> {
    if (!isFirebaseConfigured) return [];
    try {
      const q = query(collection(db, COL_VISITS), orderBy('visit_date', 'desc'), limit(100));
      const snapshot = await getDocs(q);
      return snapshot.docs.map((docSnap) => ({
        draft_id: docSnap.id,
        ...(docSnap.data() as Omit<VisitDraft, 'draft_id'>),
      }));
    } catch (err) {
      console.warn('[Firebase] Failed to fetch visits:', err);
      return [];
    }
  },

  async saveVisit(visit: VisitDraft): Promise<void> {
    if (!isFirebaseConfigured) return;
    const docId = visit.visit_id || visit.draft_id;
    await setDoc(
      doc(db, COL_VISITS, docId),
      {
        ...visit,
        updated_at: new Date().toISOString(),
      },
      { merge: true }
    );
  },

  async clearAllVisits(): Promise<void> {
    if (!isFirebaseConfigured) return;
    try {
      const snapshot = await getDocs(collection(db, COL_VISITS));
      const deletePromises = snapshot.docs.map((d) => deleteDoc(d.ref));
      await Promise.all(deletePromises);
    } catch (err) {
      console.warn('[Firebase] Failed to clear visits:', err);
    }
  },

  // ── Danger Alerts ──────────────────────────────────────────────────────────
  async getDangerAlerts(): Promise<DangerAlert[]> {
    if (!isFirebaseConfigured) return [];
    try {
      const q = query(collection(db, COL_DANGER_ALERTS), orderBy('timestamp', 'desc'));
      const snapshot = await getDocs(q);
      return snapshot.docs.map((docSnap) => ({
        id: docSnap.id,
        ...(docSnap.data() as Omit<DangerAlert, 'id'>),
      }));
    } catch (err) {
      console.warn('[Firebase] Failed to fetch danger alerts:', err);
      return [];
    }
  },

  async saveDangerAlert(alert: DangerAlert): Promise<void> {
    if (!isFirebaseConfigured) return;
    const docId = alert.id || alert.alert_id;
    await setDoc(
      doc(db, COL_DANGER_ALERTS, docId),
      {
        ...alert,
        id: docId,
        updated_at: new Date().toISOString(),
      },
      { merge: true }
    );
  },

  async clearAllDangerAlerts(): Promise<void> {
    if (!isFirebaseConfigured) return;
    try {
      const snapshot = await getDocs(collection(db, COL_DANGER_ALERTS));
      const deletePromises = snapshot.docs.map((d) => deleteDoc(d.ref));
      await Promise.all(deletePromises);
    } catch (err) {
      console.warn('[Firebase] Failed to clear danger alerts:', err);
    }
  },

  // ── Follow Ups ─────────────────────────────────────────────────────────────
  async getFollowUps(): Promise<FollowUpTask[]> {
    if (!isFirebaseConfigured) return [];
    try {
      const q = query(collection(db, COL_FOLLOW_UPS), orderBy('due_date', 'asc'));
      const snapshot = await getDocs(q);
      return snapshot.docs.map((docSnap) => ({
        id: docSnap.id,
        ...(docSnap.data() as Omit<FollowUpTask, 'id'>),
      }));
    } catch (err) {
      console.warn('[Firebase] Failed to fetch follow-ups:', err);
      return [];
    }
  },

  async saveFollowUp(task: FollowUpTask): Promise<void> {
    if (!isFirebaseConfigured) return;
    await setDoc(doc(db, COL_FOLLOW_UPS, task.id), task, { merge: true });
  },

  async updateFollowUpStatus(taskId: string, status: 'PENDING' | 'OVERDUE' | 'COMPLETED' | 'CANCELLED'): Promise<void> {
    if (!isFirebaseConfigured) return;
    await updateDoc(doc(db, COL_FOLLOW_UPS, taskId), {
      status,
      updated_at: new Date().toISOString(),
    });
  },

  // ── Immunisations ──────────────────────────────────────────────────────────
  async getImmunisations(): Promise<ImmunisationScheduleItem[]> {
    if (!isFirebaseConfigured) return [];
    try {
      const q = query(collection(db, COL_IMMUNISATIONS), orderBy('due_date', 'asc'));
      const snapshot = await getDocs(q);
      return snapshot.docs.map((docSnap) => ({
        id: docSnap.id,
        ...(docSnap.data() as Omit<ImmunisationScheduleItem, 'id'>),
      }));
    } catch (err) {
      console.warn('[Firebase] Failed to fetch immunisations:', err);
      return [];
    }
  },

  async saveImmunisation(item: ImmunisationScheduleItem): Promise<void> {
    if (!isFirebaseConfigured) return;
    await setDoc(doc(db, COL_IMMUNISATIONS, item.id), item, { merge: true });
  },

  // ── Profiles & Facilities ──────────────────────────────────────────────────
  async getUserProfiles(): Promise<UserProfile[]> {
    if (!isFirebaseConfigured) return [];
    try {
      const snapshot = await getDocs(collection(db, COL_PROFILES));
      return snapshot.docs.map((docSnap) => ({
        id: docSnap.id,
        ...(docSnap.data() as Omit<UserProfile, 'id'>),
      }));
    } catch (err) {
      console.warn('[Firebase] Failed to fetch user profiles:', err);
      return [];
    }
  },

  async saveUserProfile(profile: UserProfile): Promise<void> {
    if (!isFirebaseConfigured) return;
    await setDoc(doc(db, COL_PROFILES, profile.id), profile, { merge: true });
  },

  async getFacilities(): Promise<Facility[]> {
    if (!isFirebaseConfigured) return [];
    try {
      const snapshot = await getDocs(collection(db, COL_FACILITIES));
      return snapshot.docs.map((docSnap) => ({
        id: docSnap.id,
        ...(docSnap.data() as Omit<Facility, 'id'>),
      }));
    } catch (err) {
      console.warn('[Firebase] Failed to fetch facilities:', err);
      return [];
    }
  },

  async saveFacility(facility: Facility): Promise<void> {
    if (!isFirebaseConfigured) return;
    await setDoc(doc(db, COL_FACILITIES, facility.id), facility, { merge: true });
  },

  // ── Audit Logs ─────────────────────────────────────────────────────────────
  async getAuditLogs(): Promise<AuditLogEntry[]> {
    if (!isFirebaseConfigured) return [];
    try {
      const q = query(collection(db, COL_AUDIT_LOGS), orderBy('timestamp', 'desc'), limit(100));
      const snapshot = await getDocs(q);
      return snapshot.docs.map((docSnap) => ({
        id: docSnap.id,
        ...(docSnap.data() as Omit<AuditLogEntry, 'id'>),
      }));
    } catch (err) {
      console.warn('[Firebase] Failed to fetch audit logs:', err);
      return [];
    }
  },

  async logAction(entry: AuditLogEntry): Promise<void> {
    if (!isFirebaseConfigured) return;
    await setDoc(doc(db, COL_AUDIT_LOGS, entry.id), entry, { merge: true });
  },
};
