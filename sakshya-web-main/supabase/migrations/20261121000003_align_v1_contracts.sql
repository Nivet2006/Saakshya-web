-- ==============================================================================
-- Migration: 20261121000003_align_v1_contracts.sql
-- Description: Aligns Supabase persistence schema with Agent 1 v1 schemas
--              and synthetic beneficiary IDs BEN-1042..BEN-1048.
-- ==============================================================================

ALTER TABLE public.visits
    ADD COLUMN IF NOT EXISTS visit_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS weight_kg NUMERIC(5, 2),
    ADD COLUMN IF NOT EXISTS vaccinations_completed TEXT[] DEFAULT ARRAY[]::TEXT[],
    ADD COLUMN IF NOT EXISTS vaccinations_due TEXT[] DEFAULT ARRAY[]::TEXT[],
    ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS committed_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS idx_visits_visit_id_unique
    ON public.visits(visit_id) WHERE visit_id IS NOT NULL;

ALTER TABLE public.danger_alerts
    ADD COLUMN IF NOT EXISTS canonical_danger_sign_id VARCHAR(120),
    ADD COLUMN IF NOT EXISTS canonical_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS source_guideline_ref VARCHAR(255),
    ADD COLUMN IF NOT EXISTS subject VARCHAR(40);

-- Align synthetic beneficiary BEN-1042..BEN-1048 names with Agent 1 backend directory
INSERT INTO public.beneficiaries (
    id, beneficiary_id, full_name, age_years, gender, category, village,
    high_risk_status, assigned_asha_id, phc_id
)
VALUES
    ('c0000000-0000-0000-0000-000000001048', 'BEN-1048', 'Lakshmi Narayanan', 29, 'FEMALE', 'LACTATING_MOTHER', 'Kaveri Demo Ward 3',
     false, 'b0000000-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000001')
ON CONFLICT (beneficiary_id) DO NOTHING;

UPDATE public.beneficiaries SET full_name = 'Lakshmi Devi' WHERE beneficiary_id = 'BEN-1042';
UPDATE public.beneficiaries SET full_name = 'Kavitha Rao', category = 'LACTATING_MOTHER' WHERE beneficiary_id = 'BEN-1043';
UPDATE public.beneficiaries SET full_name = 'Baby of Kavitha Rao', category = 'INFANT' WHERE beneficiary_id = 'BEN-1044';
UPDATE public.beneficiaries SET full_name = 'Sunita Kumari', category = 'PREGNANT_WOMAN' WHERE beneficiary_id = 'BEN-1045';
UPDATE public.beneficiaries SET full_name = 'Meena Selvam', category = 'CHILD' WHERE beneficiary_id = 'BEN-1046';
UPDATE public.beneficiaries SET full_name = 'Anita Devi', category = 'PREGNANT_WOMAN' WHERE beneficiary_id = 'BEN-1047';

