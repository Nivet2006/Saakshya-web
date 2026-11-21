import { fastApiClient } from '@/lib/api/fastapi-client';
import {
  SYNTHETIC_AUDIT_LOGS,
  SYNTHETIC_BENEFICIARIES,
  SYNTHETIC_DANGER_ALERTS,
  SYNTHETIC_FOLLOW_UPS,
  SYNTHETIC_IMMUNISATIONS,
  SYNTHETIC_INITIAL_VISITS,
  SYNTHETIC_PROFILES,
} from '@/lib/mock-data';
import {
  cacheBeneficiariesLocally,
  getAllLocalDrafts,
  getCachedBeneficiariesLocally,
} from '@/lib/offline/indexeddb-store';
import { isRealSupabaseConfigured, supabase } from '@/lib/supabase/client';
import type {
  AuditLogEntry,
  Beneficiary,
  BeneficiaryCategory,
  DangerAlert,
  FollowUpTask,
  ImmunisationScheduleItem,
  UserProfile,
  VisitDraft,
} from '@/types';

const STORAGE_VISITS_KEY = 'sakshya_visits_v2';
const STORAGE_ALERTS_KEY = 'sakshya_alerts_v2';
const STORAGE_FOLLOWUPS_KEY = 'sakshya_followups_v2';
const STORAGE_AUDIT_KEY = 'sakshya_audit_v2';

class DataService {
  private beneficiaries: Beneficiary[] = [...SYNTHETIC_BENEFICIARIES];
  private profiles: UserProfile[] = [...SYNTHETIC_PROFILES];
  private visits: VisitDraft[] = [...SYNTHETIC_INITIAL_VISITS];
  private dangerAlerts: DangerAlert[] = [...SYNTHETIC_DANGER_ALERTS];
  private followUps: FollowUpTask[] = [...SYNTHETIC_FOLLOW_UPS];
  private immunisations: ImmunisationScheduleItem[] = [...SYNTHETIC_IMMUNISATIONS];
  private auditLogs: AuditLogEntry[] = [...SYNTHETIC_AUDIT_LOGS];
  private hydrated = false;

  hydrateFromLocalStorage(): void {
    if (this.hydrated || typeof window === 'undefined') return;
    this.hydrated = true;
    try {
      const v = localStorage.getItem(STORAGE_VISITS_KEY);
      if (v) this.visits = JSON.parse(v);
      const a = localStorage.getItem(STORAGE_ALERTS_KEY);
      if (a) this.dangerAlerts = JSON.parse(a);
      const f = localStorage.getItem(STORAGE_FOLLOWUPS_KEY);
      if (f) this.followUps = JSON.parse(f);
      const aud = localStorage.getItem(STORAGE_AUDIT_KEY);
      if (aud) this.auditLogs = JSON.parse(aud);
    } catch {
      // ignore storage errors
    }
  }

  private persistLocalStorage(): void {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(STORAGE_VISITS_KEY, JSON.stringify(this.visits));
      localStorage.setItem(STORAGE_ALERTS_KEY, JSON.stringify(this.dangerAlerts));
      localStorage.setItem(STORAGE_FOLLOWUPS_KEY, JSON.stringify(this.followUps));
      localStorage.setItem(STORAGE_AUDIT_KEY, JSON.stringify(this.auditLogs));
    } catch {
      // ignore storage quota errors
    }
  }

  /** Syncs synthetic beneficiaries with Agent 1's live GET /api/v1/beneficiaries and Supabase when online. */
  async refreshBeneficiaries(): Promise<Beneficiary[]> {
    this.hydrateFromLocalStorage();
    try {
      const backendList = await fastApiClient.listBeneficiaries();
      if (backendList.beneficiaries?.length) {
        const merged = backendList.beneficiaries.map((b) => {
          const existing = this.beneficiaries.find(
            (cur) => cur.beneficiary_id.toUpperCase() === b.beneficiary_id.toUpperCase()
          );
          if (existing) {
            return {
              ...existing,
              full_name: b.full_name,
              village: b.village,
              preferred_language: b.preferred_language,
            };
          }
          return {
            id: `c0000000-0000-0000-0000-${b.beneficiary_id.replace('BEN-', '').padStart(12, '0')}`,
            beneficiary_id: b.beneficiary_id,
            full_name: b.full_name,
            age_years: b.category === 'newborn' || b.category === 'infant' ? 0 : 25,
            gender: 'FEMALE' as const,
            category: mapBackendCategory(b.category),
            village: b.village,
            high_risk_status: false,
            high_risk_reasons: [],
            assigned_asha_id: 'b0000000-0000-0000-0000-000000000001',
            phc_id: 'a0000000-0000-0000-0000-000000000001',
            preferred_language: b.preferred_language,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          };
        });
        this.beneficiaries = merged;
        await cacheBeneficiariesLocally(merged);
      }
    } catch {
      const cached = await getCachedBeneficiariesLocally();
      if (cached.length > 0) {
        this.beneficiaries = cached;
      }
    }

    if (supabase && isRealSupabaseConfigured) {
      try {
        const { data } = await supabase.from('beneficiaries').select('*').order('beneficiary_id');
        if (data && data.length > 0) {
          this.beneficiaries = data as unknown as Beneficiary[];
        }
      } catch {
        // Fallback already populated
      }
    }

    return [...this.beneficiaries];
  }

  getBeneficiaries(ashaId?: string, phcId?: string): Beneficiary[] {
    this.hydrateFromLocalStorage();
    return this.beneficiaries.filter((b) => {
      if (ashaId && b.assigned_asha_id && b.assigned_asha_id !== ashaId) return false;
      if (phcId && b.phc_id !== phcId) return false;
      return true;
    });
  }

  getProfiles(phcId?: string): UserProfile[] {
    return phcId ? this.profiles.filter((p) => p.phc_id === phcId) : [...this.profiles];
  }

  getVisits(ashaId?: string, phcId?: string): VisitDraft[] {
    this.hydrateFromLocalStorage();
    return this.visits
      .filter((v) => {
        if (ashaId && v.asha_worker_id !== ashaId) return false;
        if (phcId && v.phc_id !== phcId) return false;
        return true;
      })
      .sort((a, b) => new Date(b.visit_date).getTime() - new Date(a.visit_date).getTime());
  }

  async getAllVisitsMergedWithOffline(): Promise<VisitDraft[]> {
    this.hydrateFromLocalStorage();
    const localDrafts = await getAllLocalDrafts();
    const byId = new Map<string, VisitDraft>();
    for (const v of this.visits) {
      byId.set(v.visit_id || v.draft_id, v);
    }
    for (const d of localDrafts) {
      byId.set(d.visit_id || d.draft_id, d);
    }
    return Array.from(byId.values()).sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    );
  }

  getDangerAlerts(phcId?: string): DangerAlert[] {
    this.hydrateFromLocalStorage();
    return this.dangerAlerts
      .filter((a) => !phcId || a.phc_id === phcId)
      .sort((a, b) => new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime());
  }

  getFollowUps(ashaId?: string, phcId?: string): FollowUpTask[] {
    this.hydrateFromLocalStorage();
    return this.followUps.filter((f) => {
      if (ashaId && f.asha_worker_id !== ashaId) return false;
      if (phcId && f.phc_id !== phcId) return false;
      return true;
    });
  }

  getImmunisations(beneficiaryId?: string): ImmunisationScheduleItem[] {
    this.hydrateFromLocalStorage();
    return beneficiaryId
      ? this.immunisations.filter((i) => i.beneficiary_id === beneficiaryId)
      : [...this.immunisations];
  }

  getAuditLogs(): AuditLogEntry[] {
    this.hydrateFromLocalStorage();
    return [...this.auditLogs].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }

  /** Registers an active danger alert immediately (independent of visit completion). */
  registerDangerAlert(alert: DangerAlert, actor?: UserProfile): void {
    this.hydrateFromLocalStorage();
    const existingIdx = this.dangerAlerts.findIndex((a) => a.alert_id === alert.alert_id);
    if (existingIdx >= 0) {
      this.dangerAlerts[existingIdx] = { ...this.dangerAlerts[existingIdx], ...alert };
    } else {
      this.dangerAlerts.unshift(alert);
      this.auditLogs.unshift({
        id: `aud-${Date.now()}`,
        actor_name: actor?.full_name || alert.asha_worker_name || 'ASHA Worker',
        actor_role: actor?.role || 'ASHA_WORKER',
        action_type: 'DANGER_ALERT_EMITTED',
        entity_type: 'danger_alert',
        entity_id: alert.alert_id,
        summary: `${alert.canonical_name} (${alert.source_guideline_ref})`,
        created_at: new Date().toISOString(),
      });
    }

    if (supabase && isRealSupabaseConfigured && alert.beneficiary_id) {
      const benUuid = this.beneficiaries.find((b) => b.beneficiary_id === alert.beneficiary_id)?.id;
      if (benUuid) {
        supabase
          .from('danger_alerts')
          .upsert(
            {
              alert_id: alert.alert_id,
              session_id: alert.session_id || null,
              beneficiary_id: benUuid,
              asha_worker_id: alert.asha_worker_id || 'b0000000-0000-0000-0000-000000000001',
              phc_id: alert.phc_id,
              severity: 'CRITICAL',
              category: alert.category,
              symptom_evidence: alert.supporting_evidence,
              referral_instruction: alert.referral_message,
              referral_facility_type: alert.referral_facility_type || 'PHC',
              referral_status: 'PENDING_TRANSPORT',
              supervisor_acknowledged: false,
              detected_at: alert.detected_at,
            },
            { onConflict: 'alert_id' }
          )
          .then(() => {}, () => {});
      }
    }

    this.persistLocalStorage();
  }

  /** Transitions danger alert workflow: active -> acknowledged -> referred -> resolved. */
  updateDangerAlertStatus(
    alertId: string,
    nextStatus: DangerAlert['status'],
    actor: UserProfile,
    referralNotes?: string
  ): DangerAlert | undefined {
    this.hydrateFromLocalStorage();
    const target = this.dangerAlerts.find((a) => a.alert_id === alertId);
    if (!target) return undefined;

    target.status = nextStatus;
    if (nextStatus !== 'active' && !target.acknowledged_at) {
      target.acknowledged_by = actor.full_name;
      target.acknowledged_at = new Date().toISOString();
    }
    if (referralNotes !== undefined) {
      target.referral_notes = referralNotes;
    }

    this.auditLogs.unshift({
      id: `aud-${Date.now()}`,
      actor_name: actor.full_name,
      actor_role: actor.role,
      action_type: `ALERT_${nextStatus.toUpperCase()}`,
      entity_type: 'danger_alert',
      entity_id: alertId,
      summary: `Alert ${alertId} marked ${nextStatus}`,
      created_at: new Date().toISOString(),
    });

    if (supabase && isRealSupabaseConfigured) {
      const referralStatus =
        nextStatus === 'resolved'
          ? 'RESOLVED'
          : nextStatus === 'referred'
          ? 'EN_ROUTE'
          : 'ARRIVED_AT_FACILITY';
      supabase
        .from('danger_alerts')
        .update({
          supervisor_acknowledged: nextStatus !== 'active',
          acknowledged_at: target.acknowledged_at,
          referral_status: referralStatus,
        })
        .eq('alert_id', alertId)
        .then(() => {}, () => {});
    }

    this.persistLocalStorage();
    return { ...target };
  }

  /** Records ONLY explicitly confirmed/committed visits into the saved visit register. */
  recordCommittedVisit(visit: VisitDraft): void {
    this.hydrateFromLocalStorage();
    if (visit.status === 'draft') return;

    const existingIdx = this.visits.findIndex(
      (v) => v.visit_id === visit.visit_id || v.idempotency_key === visit.idempotency_key
    );
    if (existingIdx >= 0) {
      this.visits[existingIdx] = visit;
    } else {
      this.visits.unshift(visit);
    }

    for (const alert of visit.danger_alerts) {
      this.registerDangerAlert(alert);
    }

    // Generate structured follow-up tasks without duplicating
    visit.follow_up_actions.forEach((act, idx) => {
      const taskId = `fu_${visit.visit_id}_${idx}`;
      if (!this.followUps.some((f) => f.id === taskId)) {
        this.followUps.unshift({
          id: taskId,
          beneficiary_uuid: visit.beneficiary_uuid,
          beneficiary_id: visit.beneficiary_id || 'UNASSIGNED',
          beneficiary_name: visit.beneficiary_name || undefined,
          asha_worker_id: visit.asha_worker_id,
          phc_id: visit.phc_id,
          due_date: act.due_date || new Date().toISOString().split('T')[0],
          task_type: act.description,
          action_type: act.action_type,
          priority:
            act.priority === 'urgent' ? 'URGENT' : act.priority === 'high' ? 'HIGH' : 'NORMAL',
          status: 'PENDING',
          notes: act.source_phrase || undefined,
          created_at: new Date().toISOString(),
        });
      }
    });

    this.auditLogs.unshift({
      id: `aud-${Date.now()}`,
      actor_name: visit.worker_name || 'ASHA Worker',
      actor_role: 'ASHA_WORKER',
      action_type: 'VISIT_COMMITTED',
      entity_type: 'visit',
      entity_id: visit.visit_id,
      summary: `${visit.visit_type || 'Visit'} saved for ${visit.beneficiary_name || visit.beneficiary_id || 'Beneficiary'}`,
      created_at: new Date().toISOString(),
    });

    this.persistLocalStorage();
  }

  toggleFollowUpStatus(taskId: string): FollowUpTask | undefined {
    this.hydrateFromLocalStorage();
    const task = this.followUps.find((f) => f.id === taskId);
    if (!task) return undefined;
    task.status = task.status === 'COMPLETED' ? 'PENDING' : 'COMPLETED';
    task.completed_at = task.status === 'COMPLETED' ? new Date().toISOString() : undefined;
    this.persistLocalStorage();
    return { ...task };
  }

  /** Subscribes to Supabase Realtime danger_alerts if configured. */
  subscribeToRealtimeAlerts(onNewOrUpdated: () => void): () => void {
    const client = supabase;
    if (!client || !isRealSupabaseConfigured) {
      return () => {};
    }
    const channel = client
      .channel('danger-alerts-realtime')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'danger_alerts' },
        () => onNewOrUpdated()
      )
      .subscribe();

    return () => {
      client.removeChannel(channel).catch(() => {});
    };
  }
}

function mapBackendCategory(cat: string): BeneficiaryCategory {
  switch (cat) {
    case 'pregnant_woman':
      return 'PREGNANT_WOMAN';
    case 'postnatal_mother':
      return 'LACTATING_MOTHER';
    case 'newborn':
    case 'infant':
      return 'INFANT';
    default:
      return 'CHILD';
  }
}

export const dataService = new DataService();
