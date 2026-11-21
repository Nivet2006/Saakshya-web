import type {
  Beneficiary,
  DangerAlert,
  FollowUpTask,
  ImmunisationScheduleItem,
  UserProfile,
  VisitDraft,
} from '@/types';

export interface SupervisorOverviewStats {
  totalBeneficiaries: number;
  activeAshaWorkers: number;
  onlineAshaWorkers: number;
  visitsCompletedToday: number;
  totalCommittedVisits: number;
  pendingDraftVisits: number;
  overdueFollowUps: number;
  upcomingImmunisations: number;
  activeDangerAlerts: number;
  referredOrAcknowledgedAlerts: number;
  immunisationCoveragePct: number;
  followUpCompletionPct: number;
}

export interface VisitTypeBreakdownItem {
  label: 'ANC' | 'PNC' | 'Newborn' | 'Immunisation' | 'Other';
  count: number;
  pct: number;
}

export interface DailyVisitVolumeItem {
  date: string;
  label: string;
  count: number;
  dangerCount: number;
}

export interface WorkerMetricsRow {
  worker: UserProfile;
  assignedBeneficiaries: number;
  completedVisits: number;
  pendingFollowUps: number;
  activeAlerts: number;
}

export function computeSupervisorOverview(params: {
  beneficiaries: Beneficiary[];
  workers: UserProfile[];
  visits: VisitDraft[];
  allLocalDrafts?: VisitDraft[];
  followUps: FollowUpTask[];
  immunisations: ImmunisationScheduleItem[];
  dangerAlerts: DangerAlert[];
  todayIso?: string;
}): SupervisorOverviewStats {
  const {
    beneficiaries,
    workers,
    visits,
    allLocalDrafts = [],
    followUps,
    immunisations,
    dangerAlerts,
    todayIso = new Date().toISOString().split('T')[0],
  } = params;

  const ashaWorkers = workers.filter((w) => w.role === 'ASHA_WORKER');
  const activeAshaWorkers = ashaWorkers.filter((w) => w.is_active).length;
  const onlineAshaWorkers = ashaWorkers.filter((w) => w.is_online).length;

  const committedVisits = visits.filter((v) => v.status === 'confirmed' || v.status === 'committed');
  const visitsCompletedToday = committedVisits.filter((v) =>
    v.visit_date.startsWith(todayIso)
  ).length;

  const pendingDraftVisits = allLocalDrafts.filter((d) => d.status === 'draft').length;

  const overdueFollowUps = followUps.filter(
    (f) => f.status !== 'COMPLETED' && f.status !== 'CANCELLED' && (f.status === 'OVERDUE' || f.due_date < todayIso)
  ).length;

  const upcomingImmunisations = immunisations.filter(
    (i) => i.status === 'DUE' || i.status === 'OVERDUE'
  ).length;

  const activeDangerAlerts = dangerAlerts.filter((a) => a.status === 'active').length;
  const referredOrAcknowledgedAlerts = dangerAlerts.filter(
    (a) => a.status === 'acknowledged' || a.status === 'referred'
  ).length;

  const givenVaccines = immunisations.filter((i) => i.status === 'GIVEN').length;
  const immunisationCoveragePct =
    immunisations.length > 0 ? Math.round((givenVaccines / immunisations.length) * 100) : 0;

  const completedFollowUps = followUps.filter((f) => f.status === 'COMPLETED').length;
  const followUpCompletionPct =
    followUps.length > 0 ? Math.round((completedFollowUps / followUps.length) * 100) : 0;

  return {
    totalBeneficiaries: beneficiaries.length,
    activeAshaWorkers,
    onlineAshaWorkers,
    visitsCompletedToday,
    totalCommittedVisits: committedVisits.length,
    pendingDraftVisits,
    overdueFollowUps,
    upcomingImmunisations,
    activeDangerAlerts,
    referredOrAcknowledgedAlerts,
    immunisationCoveragePct,
    followUpCompletionPct,
  };
}

export function computeVisitTypeDistribution(visits: VisitDraft[]): VisitTypeBreakdownItem[] {
  const counts: Record<VisitTypeBreakdownItem['label'], number> = {
    ANC: 0,
    PNC: 0,
    Newborn: 0,
    Immunisation: 0,
    Other: 0,
  };

  visits.forEach((v) => {
    if (v.visit_type === 'ANC') counts.ANC++;
    else if (v.visit_type === 'PNC') counts.PNC++;
    else if (v.visit_type === 'Newborn') counts.Newborn++;
    else if (v.visit_type === 'Immunisation') counts.Immunisation++;
    else counts.Other++;
  });

  const total = Math.max(1, visits.length);
  return (Object.keys(counts) as Array<VisitTypeBreakdownItem['label']>).map((label) => ({
    label,
    count: counts[label],
    pct: visits.length === 0 ? 0 : Math.round((counts[label] / total) * 100),
  }));
}

export function computeDailyVisitVolume(visits: VisitDraft[], days = 7): DailyVisitVolumeItem[] {
  const result: DailyVisitVolumeItem[] = [];
  const now = new Date();
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 86400000);
    const iso = d.toISOString().split('T')[0];
    const dayVisits = visits.filter((v) => v.visit_date.startsWith(iso));
    result.push({
      date: iso,
      label: d.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' }),
      count: dayVisits.length,
      dangerCount: dayVisits.filter((v) => v.danger_sign_flagged).length,
    });
  }
  return result;
}

export function computeWorkerMetrics(params: {
  workers: UserProfile[];
  beneficiaries: Beneficiary[];
  visits: VisitDraft[];
  followUps: FollowUpTask[];
  dangerAlerts: DangerAlert[];
}): WorkerMetricsRow[] {
  const ashas = params.workers.filter((w) => w.role === 'ASHA_WORKER');
  return ashas.map((worker) => ({
    worker,
    assignedBeneficiaries: params.beneficiaries.filter((b) => b.assigned_asha_id === worker.id)
      .length,
    completedVisits: params.visits.filter(
      (v) => v.asha_worker_id === worker.id || v.worker_name === worker.full_name
    ).length,
    pendingFollowUps: params.followUps.filter(
      (f) => f.asha_worker_id === worker.id && f.status !== 'COMPLETED'
    ).length,
    activeAlerts: params.dangerAlerts.filter(
      (a) => a.asha_worker_id === worker.id && a.status === 'active'
    ).length,
  }));
}

export function buildVisitsCsv(visits: VisitDraft[]): string {
  const headers = [
    'Visit ID',
    'Persistence ID',
    'Visit Date',
    'Beneficiary ID',
    'Beneficiary Name',
    'Worker',
    'Visit Type',
    'Weight (kg)',
    'Vaccinations Completed',
    'Vaccinations Due',
    'Danger Sign Flagged',
    'Danger Signs',
    'Next Visit Date',
    'Status',
  ];

  const escapeCsv = (val: unknown): string => {
    const s = String(val ?? '');
    if (s.includes(',') || s.includes('"') || s.includes('\n')) {
      return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
  };

  const rows = visits.map((v) => [
    v.visit_id,
    v.persistence_record_id || '',
    v.visit_date,
    v.beneficiary_id || '',
    v.beneficiary_name || '',
    v.worker_name || v.asha_worker_id,
    v.visit_type || '',
    v.weight_kg ?? '',
    v.vaccinations_completed.join('; '),
    v.vaccinations_due.join('; '),
    v.danger_sign_flagged ? 'YES' : 'NO',
    v.danger_signs.join('; '),
    v.next_visit_date || '',
    v.status,
  ]);

  return [headers.map(escapeCsv).join(','), ...rows.map((r) => r.map(escapeCsv).join(','))].join(
    '\n'
  );
}

