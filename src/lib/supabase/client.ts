import { createClient as createSupabaseClient } from '@supabase/supabase-js';
import {
  SYNTHETIC_BENEFICIARIES,
  SYNTHETIC_DANGER_ALERTS,
  SYNTHETIC_FACILITIES,
  SYNTHETIC_FOLLOW_UPS,
  SYNTHETIC_IMMUNISATIONS,
  SYNTHETIC_PROFILES,
} from '@/lib/mock-data';
import { Beneficiary, DangerAlert, FollowUpTask, ImmunisationScheduleItem, UserProfile, VisitDraft } from '@/types';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

const isRealSupabaseConfigured =
  supabaseUrl.startsWith('https://') &&
  !supabaseUrl.includes('YOUR_PROJECT_REF') &&
  !supabaseUrl.includes('placeholder-project');

export const supabase = isRealSupabaseConfigured
  ? createSupabaseClient(supabaseUrl, supabaseAnonKey)
  : null;

// Persistent in-memory / local storage repository for seamless offline & synthetic demonstration
class SyntheticRepository {
  private beneficiaries: Beneficiary[] = [...SYNTHETIC_BENEFICIARIES];
  private profiles: UserProfile[] = [...SYNTHETIC_PROFILES];
  private visits: VisitDraft[] = [];
  private dangerAlerts: DangerAlert[] = [...SYNTHETIC_DANGER_ALERTS];
  private followUps: FollowUpTask[] = [...SYNTHETIC_FOLLOW_UPS];
  private immunisations: ImmunisationScheduleItem[] = [...SYNTHETIC_IMMUNISATIONS];

  constructor() {
    if (typeof window !== 'undefined') {
      try {
        const storedVisits = localStorage.getItem('asha_synthetic_visits');
        if (storedVisits) this.visits = JSON.parse(storedVisits);

        const storedAlerts = localStorage.getItem('asha_synthetic_alerts');
        if (storedAlerts) this.dangerAlerts = JSON.parse(storedAlerts);
      } catch (e) {
        console.warn('Could not read from localStorage', e);
      }
    }
  }

  getBeneficiaries(ashaId?: string, phcId?: string): Beneficiary[] {
    return this.beneficiaries.filter((b) => {
      if (ashaId && b.assigned_asha_id !== ashaId) return false;
      if (phcId && b.phc_id !== phcId) return false;
      return true;
    });
  }

  getBeneficiary(id: string): Beneficiary | undefined {
    return this.beneficiaries.find((b) => b.id === id || b.beneficiary_id === id);
  }

  getProfiles(phcId?: string): UserProfile[] {
    if (phcId) return this.profiles.filter((p) => p.phc_id === phcId);
    return this.profiles;
  }

  getProfile(id: string): UserProfile | undefined {
    return this.profiles.find((p) => p.id === id);
  }

  getDangerAlerts(phcId?: string): DangerAlert[] {
    if (phcId) return this.dangerAlerts.filter((a) => a.phc_id === phcId);
    return this.dangerAlerts;
  }

  acknowledgeAlert(alertId: string, acknowledgedBy: string): DangerAlert | undefined {
    const alert = this.dangerAlerts.find((a) => a.alert_id === alertId);
    if (alert) {
      alert.supervisor_acknowledged = true;
      alert.acknowledged_by = acknowledgedBy;
      alert.acknowledged_at = new Date().toISOString();
      alert.referral_status = 'ARRIVED_AT_FACILITY';
      this.persist();
    }
    return alert;
  }

  addVisit(visit: VisitDraft): void {
    const existingIndex = this.visits.findIndex((v) => v.idempotency_key === visit.idempotency_key);
    if (existingIndex >= 0) {
      this.visits[existingIndex] = visit;
    } else {
      this.visits.unshift(visit);
    }

    if (visit.danger_signs && visit.danger_signs.length > 0) {
      visit.danger_signs.forEach((alert) => {
        if (!this.dangerAlerts.some((a) => a.alert_id === alert.alert_id)) {
          this.dangerAlerts.unshift(alert);
        }
      });
    }

    if (visit.follow_up_required && visit.follow_up_date) {
      this.followUps.unshift({
        id: `fu-${Date.now()}`,
        beneficiary_id: visit.beneficiary_id,
        beneficiary_name: visit.beneficiary_name,
        asha_worker_id: visit.asha_worker_id,
        phc_id: visit.phc_id,
        due_date: visit.follow_up_date,
        task_type: visit.follow_up_reason || 'Routine Visit Follow-up',
        priority: visit.danger_signs_present ? 'URGENT' : 'NORMAL',
        status: 'PENDING',
        created_at: new Date().toISOString(),
      });
    }

    this.persist();
  }

  getVisits(ashaId?: string, phcId?: string): VisitDraft[] {
    return this.visits.filter((v) => {
      if (ashaId && v.asha_worker_id !== ashaId) return false;
      if (phcId && v.phc_id !== phcId) return false;
      return true;
    });
  }

  getFollowUps(ashaId?: string, phcId?: string): FollowUpTask[] {
    return this.followUps.filter((f) => {
      if (ashaId && f.asha_worker_id !== ashaId) return false;
      if (phcId && f.phc_id !== phcId) return false;
      return true;
    });
  }

  getImmunisations(beneficiaryId?: string): ImmunisationScheduleItem[] {
    if (beneficiaryId) return this.immunisations.filter((i) => i.beneficiary_id === beneficiaryId);
    return this.immunisations;
  }

  private persist() {
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('asha_synthetic_visits', JSON.stringify(this.visits));
        localStorage.setItem('asha_synthetic_alerts', JSON.stringify(this.dangerAlerts));
      } catch (e) {
        // storage quota exceeded or disabled
      }
    }
  }
}

export const syntheticRepo = new SyntheticRepository();
