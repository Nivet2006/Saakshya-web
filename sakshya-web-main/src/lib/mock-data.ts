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

export const SYNTHETIC_FACILITIES: Facility[] = [
  {
    id: 'a0000000-0000-0000-0000-000000000001',
    code: 'PHC-RAMPUR-01',
    name: 'Rampur Primary Health Centre',
    facility_type: 'PHC',
    district: 'Varanasi',
    state: 'Uttar Pradesh',
    pincode: '221005',
    contact_phone: '+91 542 2230001',
    emergency_transport_phone: '108',
  },
  {
    id: 'a0000000-0000-0000-0000-000000000002',
    code: 'CHC-SHANTINAGAR-01',
    name: 'Shantinagar Community Health Centre (FRU)',
    facility_type: 'CHC',
    district: 'Mandya',
    state: 'Karnataka',
    pincode: '571401',
    contact_phone: '+91 823 2240002',
    emergency_transport_phone: '108',
  },
];

export const SYNTHETIC_PROFILES: UserProfile[] = [
  {
    id: 'b0000000-0000-0000-0000-000000000001',
    worker_code: 'ASHA-DEMO-01',
    role: 'ASHA_WORKER',
    full_name: 'Sunita Verma (ASHA)',
    phone_number: '+91 98765 00101',
    phc_id: 'a0000000-0000-0000-0000-000000000001',
    phc_name: 'Rampur Primary Health Centre',
    assigned_area: 'Rampur Demo Ward 1 & 2',
    preferred_language: 'hi-IN',
    is_active: true,
    is_online: true,
    last_active_at: new Date().toISOString(),
  },
  {
    id: 'b0000000-0000-0000-0000-000000000002',
    worker_code: 'ASHA-DEMO-02',
    role: 'ASHA_WORKER',
    full_name: 'Padma Murthy (ASHA)',
    phone_number: '+91 98765 00102',
    phc_id: 'a0000000-0000-0000-0000-000000000001',
    phc_name: 'Rampur Primary Health Centre',
    assigned_area: 'Shantinagar Demo Ward 2',
    preferred_language: 'kn-IN',
    is_active: true,
    is_online: true,
    last_active_at: new Date(Date.now() - 12 * 60000).toISOString(),
  },
  {
    id: 'b0000000-0000-0000-0000-000000000003',
    worker_code: 'ASHA-DEMO-03',
    role: 'ASHA_WORKER',
    full_name: 'Kalyani Natarajan (ASHA)',
    phone_number: '+91 98765 00103',
    phc_id: 'a0000000-0000-0000-0000-000000000001',
    phc_name: 'Rampur Primary Health Centre',
    assigned_area: 'Kaveri Demo Ward 3',
    preferred_language: 'ta-IN',
    is_active: true,
    is_online: false,
    last_active_at: new Date(Date.now() - 45 * 60000).toISOString(),
  },
  {
    id: 'b0000000-0000-0000-0000-000000000004',
    worker_code: 'SUP-PHC-01',
    role: 'PHC_SUPERVISOR',
    full_name: 'Dr. Sunita Rao (MOIC)',
    phone_number: '+91 98765 00200',
    phc_id: 'a0000000-0000-0000-0000-000000000001',
    phc_name: 'Rampur Primary Health Centre',
    assigned_area: 'Rampur PHC Sector',
    preferred_language: 'hi-IN',
    is_active: true,
    is_online: true,
    last_active_at: new Date().toISOString(),
  },
];

/**
 * 100% aligned with Agent 1 `backend/app/services/beneficiaries.py` (BEN-1042 .. BEN-1048).
 */
export const SYNTHETIC_BENEFICIARIES: Beneficiary[] = [];

export const SYNTHETIC_DANGER_ALERTS: DangerAlert[] = [];

const todayIsoDate = new Date().toISOString().split('T')[0];

export const SYNTHETIC_INITIAL_VISITS: VisitDraft[] = [];

export const SYNTHETIC_FOLLOW_UPS: FollowUpTask[] = [];

export const SYNTHETIC_IMMUNISATIONS: ImmunisationScheduleItem[] = [];

export const SYNTHETIC_AUDIT_LOGS: AuditLogEntry[] = [];
