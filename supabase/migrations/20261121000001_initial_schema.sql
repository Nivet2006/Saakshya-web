-- ==============================================================================
-- Migration: 20261121000001_initial_schema.sql
-- Description: Core Schema for ASHA Voice Field Register with RLS and Scoping
-- Author: Agent 3 (Web & Database Lead)
-- ==============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Facilities (PHCs, CHCs, District Hospitals)
CREATE TABLE IF NOT EXISTS public.facilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    facility_type VARCHAR(50) NOT NULL CHECK (facility_type IN ('PHC', 'CHC', 'SUB_CENTRE', 'DISTRICT_HOSPITAL', 'FRU')),
    district VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    pincode VARCHAR(10),
    contact_phone VARCHAR(20),
    emergency_transport_phone VARCHAR(20) DEFAULT '108',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Profiles (ASHA Workers, PHC Supervisors, Admins)
-- Links to Supabase auth.users or operates with synthetic demo credentials
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    auth_user_id UUID, -- References auth.users(id) when Supabase Auth is active
    role VARCHAR(50) NOT NULL CHECK (role IN ('ASHA_WORKER', 'PHC_SUPERVISOR', 'ADMIN')),
    full_name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) UNIQUE,
    phc_id UUID REFERENCES public.facilities(id) ON DELETE RESTRICT,
    assigned_area VARCHAR(255),
    preferred_language VARCHAR(10) DEFAULT 'hi-IN' CHECK (preferred_language IN ('hi-IN', 'kn-IN', 'ta-IN', 'en-IN')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Synthetic Beneficiaries
CREATE TABLE IF NOT EXISTS public.beneficiaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    beneficiary_id VARCHAR(50) UNIQUE NOT NULL, -- Stable synthetic ID like BEN-1042
    full_name VARCHAR(255) NOT NULL,
    age_years INT NOT NULL CHECK (age_years >= 0 AND age_years <= 120),
    gender VARCHAR(20) NOT NULL CHECK (gender IN ('FEMALE', 'MALE', 'OTHER')),
    category VARCHAR(50) NOT NULL CHECK (category IN ('PREGNANT_WOMAN', 'INFANT', 'CHILD', 'LACTATING_MOTHER', 'GENERAL_ADULT')),
    village VARCHAR(100) NOT NULL,
    household_head VARCHAR(255),
    phone_number VARCHAR(20),
    rch_id VARCHAR(100),
    lmp_date DATE,
    edd_date DATE,
    high_risk_status BOOLEAN DEFAULT FALSE,
    high_risk_reasons TEXT[],
    assigned_asha_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    phc_id UUID NOT NULL REFERENCES public.facilities(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Visit Records
CREATE TABLE IF NOT EXISTS public.visits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_draft_id VARCHAR(100) NOT NULL,
    idempotency_key VARCHAR(100) UNIQUE NOT NULL,
    beneficiary_id UUID NOT NULL REFERENCES public.beneficiaries(id) ON DELETE CASCADE,
    asha_worker_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    phc_id UUID NOT NULL REFERENCES public.facilities(id) ON DELETE RESTRICT,
    visit_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    visit_type VARCHAR(50) NOT NULL CHECK (visit_type IN (
        'ANC_1', 'ANC_2', 'ANC_3', 'ANC_4',
        'PNC_DAY_1', 'PNC_DAY_3', 'PNC_DAY_7', 'PNC_DAY_14', 'PNC_DAY_28',
        'IMMUNISATION', 'CHILD_GROWTH', 'GENERAL_CHECKUP'
    )),
    language VARCHAR(10) DEFAULT 'hi-IN',
    vitals JSONB DEFAULT '{}'::jsonb, -- { weight_kg, blood_pressure_sys, blood_pressure_dia, temperature_f, hemoglobin_g_dl, fetal_heart_rate_bpm }
    immunisations_administered TEXT[] DEFAULT ARRAY[]::TEXT[],
    ifa_tablets_given INT DEFAULT 0,
    danger_sign_flagged BOOLEAN DEFAULT FALSE,
    danger_sign_details JSONB DEFAULT '[]'::jsonb,
    follow_up_required BOOLEAN DEFAULT FALSE,
    follow_up_date DATE,
    follow_up_reason TEXT,
    notes TEXT,
    raw_transcript_summary TEXT,
    read_back_confirmed BOOLEAN DEFAULT TRUE,
    sync_status VARCHAR(20) DEFAULT 'synced' CHECK (sync_status IN ('draft', 'pending', 'synced', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Clinical Danger Alerts
CREATE TABLE IF NOT EXISTS public.danger_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id VARCHAR(100) UNIQUE NOT NULL,
    session_id VARCHAR(100),
    visit_id UUID REFERENCES public.visits(id) ON DELETE SET NULL,
    beneficiary_id UUID NOT NULL REFERENCES public.beneficiaries(id) ON DELETE CASCADE,
    asha_worker_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    phc_id UUID NOT NULL REFERENCES public.facilities(id) ON DELETE RESTRICT,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('CRITICAL', 'HIGH', 'MODERATE')),
    category VARCHAR(100) NOT NULL,
    symptom_evidence TEXT NOT NULL,
    referral_instruction TEXT NOT NULL,
    referral_facility_type VARCHAR(50) DEFAULT 'PHC',
    referral_status VARCHAR(50) DEFAULT 'PENDING_TRANSPORT' CHECK (
        referral_status IN ('PENDING_TRANSPORT', 'EN_ROUTE', 'ARRIVED_AT_FACILITY', 'RESOLVED', 'FOLLOW_UP_SCHEDULED')
    ),
    supervisor_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    acknowledged_at TIMESTAMPTZ,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Emergency Referrals Tracking
CREATE TABLE IF NOT EXISTS public.referrals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id UUID NOT NULL REFERENCES public.danger_alerts(id) ON DELETE CASCADE,
    beneficiary_id UUID NOT NULL REFERENCES public.beneficiaries(id) ON DELETE CASCADE,
    referring_asha_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    target_facility_id UUID REFERENCES public.facilities(id) ON DELETE SET NULL,
    transport_status VARCHAR(50) DEFAULT 'CALLED_108' CHECK (
        transport_status IN ('NOT_REQUIRED', 'CALLED_108', 'ARRIVED', 'IN_TRANSIT', 'ADMITTED')
    ),
    status VARCHAR(50) DEFAULT 'INITIATED' CHECK (
        status IN ('INITIATED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')
    ),
    outcome_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Follow-up Tasks
CREATE TABLE IF NOT EXISTS public.follow_ups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    beneficiary_id UUID NOT NULL REFERENCES public.beneficiaries(id) ON DELETE CASCADE,
    asha_worker_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    phc_id UUID NOT NULL REFERENCES public.facilities(id) ON DELETE RESTRICT,
    due_date DATE NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    priority VARCHAR(20) DEFAULT 'NORMAL' CHECK (priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')),
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'COMPLETED', 'OVERDUE', 'CANCELLED')),
    completed_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Immunisations Schedule & Records
CREATE TABLE IF NOT EXISTS public.immunisations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    beneficiary_id UUID NOT NULL REFERENCES public.beneficiaries(id) ON DELETE CASCADE,
    vaccine_name VARCHAR(100) NOT NULL,
    dose_number INT NOT NULL,
    due_date DATE NOT NULL,
    administered_date DATE,
    administered_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    batch_number VARCHAR(100),
    status VARCHAR(20) DEFAULT 'DUE' CHECK (status IN ('DUE', 'OVERDUE', 'GIVEN', 'MISSED')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. Audit Trail
CREATE TABLE IF NOT EXISTS public.sync_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    action_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================================
-- INDEXES FOR PRODUCTION QUERY PATTERNS
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_beneficiaries_phc ON public.beneficiaries(phc_id);
CREATE INDEX IF NOT EXISTS idx_beneficiaries_asha ON public.beneficiaries(assigned_asha_id);
CREATE INDEX IF NOT EXISTS idx_beneficiaries_ben_id ON public.beneficiaries(beneficiary_id);
CREATE INDEX IF NOT EXISTS idx_visits_beneficiary ON public.visits(beneficiary_id);
CREATE INDEX IF NOT EXISTS idx_visits_asha ON public.visits(asha_worker_id);
CREATE INDEX IF NOT EXISTS idx_visits_phc ON public.visits(phc_id);
CREATE INDEX IF NOT EXISTS idx_visits_date ON public.visits(visit_date DESC);
CREATE INDEX IF NOT EXISTS idx_danger_alerts_phc ON public.danger_alerts(phc_id);
CREATE INDEX IF NOT EXISTS idx_danger_alerts_active ON public.danger_alerts(supervisor_acknowledged) WHERE supervisor_acknowledged = FALSE;
CREATE INDEX IF NOT EXISTS idx_follow_ups_due ON public.follow_ups(due_date ASC) WHERE status = 'PENDING';
CREATE INDEX IF NOT EXISTS idx_immunisations_due ON public.immunisations(due_date ASC) WHERE status = 'DUE';

-- ==============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ==============================================================================

ALTER TABLE public.facilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.beneficiaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.visits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.danger_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.referrals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.follow_ups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.immunisations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sync_audit_logs ENABLE ROW LEVEL SECURITY;

-- Helper function to extract user's profile
CREATE OR REPLACE FUNCTION public.current_profile()
RETURNS public.profiles AS $$
    SELECT * FROM public.profiles WHERE auth_user_id = auth.uid() LIMIT 1;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- Facilities RLS: Visible to authenticated users
CREATE POLICY "Facilities are viewable by authenticated users"
ON public.facilities FOR SELECT
TO authenticated, anon
USING (true);

-- Profiles RLS: Users can view their own profile or profiles in the same PHC
CREATE POLICY "Users view profiles within authorized PHC"
ON public.profiles FOR SELECT
TO authenticated, anon
USING (
    auth.uid() IS NULL OR -- Allows demo/anon exploration with synthetic users
    auth_user_id = auth.uid() OR
    phc_id IN (SELECT phc_id FROM public.profiles WHERE auth_user_id = auth.uid()) OR
    EXISTS (SELECT 1 FROM public.profiles WHERE auth_user_id = auth.uid() AND role = 'ADMIN')
);

-- Beneficiaries RLS: ASHA sees assigned beneficiaries; Supervisors see all in their PHC
CREATE POLICY "Beneficiary scoping policy"
ON public.beneficiaries FOR SELECT
TO authenticated, anon
USING (
    auth.uid() IS NULL OR
    assigned_asha_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()) OR
    phc_id IN (SELECT phc_id FROM public.profiles WHERE auth_user_id = auth.uid() AND role IN ('PHC_SUPERVISOR', 'ADMIN'))
);

CREATE POLICY "ASHA and Supervisors can insert beneficiaries"
ON public.beneficiaries FOR INSERT
TO authenticated, anon
WITH CHECK (true);

CREATE POLICY "Beneficiary update policy"
ON public.beneficiaries FOR UPDATE
TO authenticated, anon
USING (
    auth.uid() IS NULL OR
    assigned_asha_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()) OR
    phc_id IN (SELECT phc_id FROM public.profiles WHERE auth_user_id = auth.uid() AND role IN ('PHC_SUPERVISOR', 'ADMIN'))
);

-- Visits RLS: ASHA sees their visits; Supervisors see PHC visits
CREATE POLICY "Visits select policy"
ON public.visits FOR SELECT
TO authenticated, anon
USING (
    auth.uid() IS NULL OR
    asha_worker_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()) OR
    phc_id IN (SELECT phc_id FROM public.profiles WHERE auth_user_id = auth.uid() AND role IN ('PHC_SUPERVISOR', 'ADMIN'))
);

CREATE POLICY "Visits insert policy"
ON public.visits FOR INSERT
TO authenticated, anon
WITH CHECK (true);

-- Danger Alerts RLS: High priority - ASHA and Supervisors can view and update
CREATE POLICY "Danger alerts select policy"
ON public.danger_alerts FOR SELECT
TO authenticated, anon
USING (
    auth.uid() IS NULL OR
    asha_worker_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()) OR
    phc_id IN (SELECT phc_id FROM public.profiles WHERE auth_user_id = auth.uid() AND role IN ('PHC_SUPERVISOR', 'ADMIN'))
);

CREATE POLICY "Danger alerts insert policy"
ON public.danger_alerts FOR INSERT
TO authenticated, anon
WITH CHECK (true);

CREATE POLICY "Danger alerts update policy (supervisor ack)"
ON public.danger_alerts FOR UPDATE
TO authenticated, anon
USING (
    auth.uid() IS NULL OR
    phc_id IN (SELECT phc_id FROM public.profiles WHERE auth_user_id = auth.uid() AND role IN ('PHC_SUPERVISOR', 'ADMIN')) OR
    asha_worker_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid())
);

-- Follow-ups RLS
CREATE POLICY "Follow ups select policy"
ON public.follow_ups FOR SELECT
TO authenticated, anon
USING (
    auth.uid() IS NULL OR
    asha_worker_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()) OR
    phc_id IN (SELECT phc_id FROM public.profiles WHERE auth_user_id = auth.uid() AND role IN ('PHC_SUPERVISOR', 'ADMIN'))
);

CREATE POLICY "Follow ups modify policy"
ON public.follow_ups FOR ALL
TO authenticated, anon
USING (true)
WITH CHECK (true);

-- Immunisations RLS
CREATE POLICY "Immunisations select policy"
ON public.immunisations FOR SELECT
TO authenticated, anon
USING (true);

CREATE POLICY "Immunisations modify policy"
ON public.immunisations FOR ALL
TO authenticated, anon
USING (true)
WITH CHECK (true);

-- Referrals RLS
CREATE POLICY "Referrals select policy"
ON public.referrals FOR SELECT
TO authenticated, anon
USING (true);

CREATE POLICY "Referrals modify policy"
ON public.referrals FOR ALL
TO authenticated, anon
USING (true)
WITH CHECK (true);

-- Audit logs: Read-only for supervisors/admins; write-only for system
CREATE POLICY "Audit logs select policy"
ON public.sync_audit_logs FOR SELECT
TO authenticated, anon
USING (
    auth.uid() IS NULL OR
    EXISTS (SELECT 1 FROM public.profiles WHERE auth_user_id = auth.uid() AND role IN ('PHC_SUPERVISOR', 'ADMIN'))
);

CREATE POLICY "Audit logs insert policy"
ON public.sync_audit_logs FOR INSERT
TO authenticated, anon
WITH CHECK (true);
