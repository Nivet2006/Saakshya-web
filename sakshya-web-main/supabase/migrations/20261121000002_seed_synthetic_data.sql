-- ==============================================================================
-- Migration: 20261121000002_seed_synthetic_data.sql
-- Description: Realistic Synthetic Demo Data for ASHA Voice Field Register
-- Author: Agent 3 (Web & Database Lead)
-- Notice: Contains only synthetic beneficiaries, mock facilities and dummy IDs.
-- ==============================================================================

-- 1. Insert Primary Health Centres (Facilities)
INSERT INTO public.facilities (id, code, name, facility_type, district, state, pincode, contact_phone, emergency_transport_phone)
VALUES
    ('a0000000-0000-0000-0000-000000000001', 'PHC-BALLABGARH-01', 'Ballabgarh Primary Health Centre', 'PHC', 'Faridabad', 'Haryana', '121004', '+91 129 2234001', '108'),
    ('a0000000-0000-0000-0000-000000000002', 'CHC-CHHAINSA-01', 'Chhainsa Community Health Centre (FRU)', 'CHC', 'Faridabad', 'Haryana', '121005', '+91 129 2234002', '108'),
    ('a0000000-0000-0000-0000-000000000003', 'PHC-KOLAR-RURAL-01', 'Kolar Rural Health Centre', 'PHC', 'Kolar', 'Karnataka', '563101', '+91 815 2241001', '108')
ON CONFLICT (code) DO NOTHING;

-- 2. Insert Profiles (ASHA Workers and Supervisors)
INSERT INTO public.profiles (id, role, full_name, phone_number, phc_id, assigned_area, preferred_language, is_active)
VALUES
    ('b0000000-0000-0000-0000-000000000001', 'ASHA_WORKER', 'Anita Devi', '+91 98765 43210', 'a0000000-0000-0000-0000-000000000001', 'Dayalpur Village (Ward 1-4)', 'hi-IN', true),
    ('b0000000-0000-0000-0000-000000000002', 'ASHA_WORKER', 'Sunita Rani', '+91 98765 43211', 'a0000000-0000-0000-0000-000000000001', 'Atali Village (Ward 1-3)', 'hi-IN', true),
    ('b0000000-0000-0000-0000-000000000003', 'ASHA_WORKER', 'Lakshmi Gowda', '+91 98765 43212', 'a0000000-0000-0000-0000-000000000003', 'Vokkaleri Village', 'kn-IN', true),
    ('b0000000-0000-0000-0000-000000000004', 'PHC_SUPERVISOR', 'Dr. Sunita Rao (Medical Officer)', '+91 98765 43220', 'a0000000-0000-0000-0000-000000000001', 'Ballabgarh PHC Sector', 'hi-IN', true),
    ('b0000000-0000-0000-0000-000000000005', 'ADMIN', 'District Healthcare Admin', '+91 98765 43299', 'a0000000-0000-0000-0000-000000000001', 'District HQ', 'en-IN', true)
ON CONFLICT (phone_number) DO NOTHING;

-- 3. Insert Synthetic Beneficiaries
INSERT INTO public.beneficiaries (
    id, beneficiary_id, full_name, age_years, gender, category, village, household_head,
    phone_number, rch_id, lmp_date, edd_date, high_risk_status, high_risk_reasons, assigned_asha_id, phc_id
)
VALUES
    -- Sunita Bai: High Risk Pregnant Woman (32 Weeks, Severe Pre-eclampsia danger sign scenario)
    ('c0000000-0000-0000-0000-000000001042', 'BEN-1042', 'Sunita Bai', 24, 'FEMALE', 'PREGNANT_WOMAN', 'Dayalpur', 'Ramesh Kumar',
     '+91 91234 56780', 'RCH-2026-HR-1042', '2026-04-10', '2027-01-15', true, ARRAY['Severe Pre-eclampsia Risk', 'BP 160/100', 'Persistent Headache'],
     'b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001'),

    -- Meena Devi & Child: Infant 6 Weeks (Pentavalent-1 Due)
    ('c0000000-0000-0000-0000-000000001043', 'BEN-1043', 'Meena Devi (Baby of Meena)', 0, 'FEMALE', 'INFANT', 'Dayalpur', 'Suresh Chand',
     '+91 91234 56781', 'RCH-2026-INF-1043', NULL, NULL, false, ARRAY[]::TEXT[],
     'b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001'),

    -- Radha Sharma: Pregnant Woman 28 Weeks (ANC-3 Due)
    ('c0000000-0000-0000-0000-000000001044', 'BEN-1044', 'Radha Sharma', 22, 'FEMALE', 'PREGNANT_WOMAN', 'Dayalpur', 'Vikram Sharma',
     '+91 91234 56782', 'RCH-2026-HR-1044', '2026-05-15', '2027-02-19', false, ARRAY[]::TEXT[],
     'b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001'),

    -- Aarav Patel: Child 14 Months (Measles-Rubella 1 Pending)
    ('c0000000-0000-0000-0000-000000001045', 'BEN-1045', 'Aarav Patel', 1, 'MALE', 'CHILD', 'Dayalpur', 'Mahesh Patel',
     '+91 91234 56783', 'RCH-2026-CHD-1045', NULL, NULL, false, ARRAY[]::TEXT[],
     'b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001'),

    -- Rajeshwari: Postnatal Mother Day 7
    ('c0000000-0000-0000-0000-000000001046', 'BEN-1046', 'Rajeshwari', 26, 'FEMALE', 'LACTATING_MOTHER', 'Atali', 'Dharmendra',
     '+91 91234 56784', 'RCH-2026-PNC-1046', '2026-02-01', '2026-11-08', false, ARRAY[]::TEXT[],
     'b0000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001'),

    -- Geetha Gowda: Pregnant Woman 36 Weeks (Karnataka PHC)
    ('c0000000-0000-0000-0000-000000001047', 'BEN-1047', 'Geetha Gowda', 25, 'FEMALE', 'PREGNANT_WOMAN', 'Vokkaleri', 'Manjunath',
     '+91 91234 56785', 'RCH-2026-KA-1047', '2026-03-20', '2026-12-25', false, ARRAY[]::TEXT[],
     'b0000000-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000003')
ON CONFLICT (beneficiary_id) DO NOTHING;

-- 4. Insert Visits
INSERT INTO public.visits (
    id, client_draft_id, idempotency_key, beneficiary_id, asha_worker_id, phc_id,
    visit_date, visit_type, language, vitals, immunisations_administered, ifa_tablets_given,
    danger_sign_flagged, follow_up_required, follow_up_date, follow_up_reason,
    notes, read_back_confirmed, sync_status
)
VALUES
    -- Past Visit for Sunita Bai where high BP was noted
    ('d0000000-0000-0000-0000-000000000001', 'draft-sunita-anc2', 'idemp-sunita-anc2-20261110',
     'c0000000-0000-0000-0000-000000001042', 'b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001',
     NOW() - INTERVAL '10 days', 'ANC_2', 'hi-IN',
     '{"weight_kg": 56.5, "blood_pressure_sys": 142, "blood_pressure_dia": 92, "temperature_f": 98.4, "hemoglobin_g_dl": 10.2, "fetal_heart_rate_bpm": 144}'::jsonb,
     ARRAY['TT-2'], 30, true, true, CURRENT_DATE + INTERVAL '4 days', 'Recheck BP and protein in urine',
     'Beneficiary advised rest and low sodium diet. Danger signs explained.', true, 'synced'),

    -- Recent Visit for Baby of Meena
    ('d0000000-0000-0000-0000-000000000002', 'draft-meena-bcg', 'idemp-meena-bcg-20261015',
     'c0000000-0000-0000-0000-000000001043', 'b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001',
     NOW() - INTERVAL '35 days', 'IMMUNISATION', 'hi-IN',
     '{"weight_kg": 3.4, "temperature_f": 98.2}'::jsonb,
     ARRAY['BCG', 'OPV-0', 'HepB-Birth'], 0, false, true, CURRENT_DATE + INTERVAL '2 days', 'Pentavalent 1 and Rota 1 due',
     'Healthy infant, exclusive breastfeeding confirmed.', true, 'synced')
ON CONFLICT (idempotency_key) DO NOTHING;

-- 5. Insert Danger Alert (Sunita Bai - Severe Pre-eclampsia / Emergency Referral)
INSERT INTO public.danger_alerts (
    id, alert_id, session_id, visit_id, beneficiary_id, asha_worker_id, phc_id,
    severity, category, symptom_evidence, referral_instruction, referral_facility_type,
    referral_status, supervisor_acknowledged, acknowledged_by, acknowledged_at, detected_at
)
VALUES
    ('e0000000-0000-0000-0000-000000000001', 'ALT-2026-001', 'sess-sunita-anc2',
     'd0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000001042',
     'b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001',
     'CRITICAL', 'severe_pre_eclampsia_eclampsia',
     'Reported persistent severe frontal headache, blurred vision, and BP reading 160/100 mmHg at 32 weeks gestation.',
     'Immediate referral to Chhainsa CHC/FRU for parenteral Magnesium Sulfate and antihypertensive evaluation. Arrange 108 ambulance.',
     'CHC', 'EN_ROUTE', false, NULL, NULL, NOW() - INTERVAL '2 hours')
ON CONFLICT (alert_id) DO NOTHING;

-- 6. Insert Referral Tracking
INSERT INTO public.referrals (
    id, alert_id, beneficiary_id, referring_asha_id, target_facility_id,
    transport_status, status, outcome_notes
)
VALUES
    ('f0000000-0000-0000-0000-000000000001', 'e0000000-0000-0000-0000-000000000001',
     'c0000000-0000-0000-0000-000000001042', 'b0000000-0000-0000-0000-000000000001',
     'a0000000-0000-0000-0000-000000000002', 'IN_TRANSIT', 'IN_PROGRESS',
     '108 Ambulance dispatched from Ballabgarh Depot. Beneficiary accompanied by husband.')
ON CONFLICT DO NOTHING;

-- 7. Insert Follow-up Tasks
INSERT INTO public.follow_ups (
    id, beneficiary_id, asha_worker_id, phc_id, due_date, task_type, priority, status, notes
)
VALUES
    ('10000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000001042',
     'b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001',
     CURRENT_DATE, 'ANC Follow-up (High Risk BP Check)', 'URGENT', 'PENDING',
     'Verify FRU admission status and check post-referral vitals.'),

    ('10000000-0000-0000-0000-000000000002', 'c0000000-0000-0000-0000-000000001043',
     'b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001',
     CURRENT_DATE + INTERVAL '2 days', 'Immunisation Dose 1 (Pentavalent-1, OPV-1, RVV-1, fIPV-1)', 'HIGH', 'PENDING',
     'Advise mother to bring child to Dayalpur Anganwadi Session.'),

    ('10000000-0000-0000-0000-000000000003', 'c0000000-0000-0000-0000-000000001044',
     'b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001',
     CURRENT_DATE + INTERVAL '5 days', 'ANC-3 Routine Home Visit', 'NORMAL', 'PENDING',
     'Distribute IFA tablets and check fetal movements.')
ON CONFLICT DO NOTHING;

-- 8. Insert Immunisation Schedule
INSERT INTO public.immunisations (
    id, beneficiary_id, vaccine_name, dose_number, due_date, administered_date, status
)
VALUES
    -- Meena's baby: given at birth
    ('20000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000001043', 'BCG', 1, CURRENT_DATE - INTERVAL '35 days', CURRENT_DATE - INTERVAL '35 days', 'GIVEN'),
    ('20000000-0000-0000-0000-000000000002', 'c0000000-0000-0000-0000-000000001043', 'OPV', 0, CURRENT_DATE - INTERVAL '35 days', CURRENT_DATE - INTERVAL '35 days', 'GIVEN'),
    ('20000000-0000-0000-0000-000000000003', 'c0000000-0000-0000-0000-000000001043', 'HepB-Birth', 1, CURRENT_DATE - INTERVAL '35 days', CURRENT_DATE - INTERVAL '35 days', 'GIVEN'),
    -- Meena's baby: Due now (6 weeks)
    ('20000000-0000-0000-0000-000000000004', 'c0000000-0000-0000-0000-000000001043', 'Pentavalent', 1, CURRENT_DATE + INTERVAL '2 days', NULL, 'DUE'),
    ('20000000-0000-0000-0000-000000000005', 'c0000000-0000-0000-0000-000000001043', 'Rotavirus', 1, CURRENT_DATE + INTERVAL '2 days', NULL, 'DUE'),
    ('20000000-0000-0000-0000-000000000006', 'c0000000-0000-0000-0000-000000001043', 'fIPV', 1, CURRENT_DATE + INTERVAL '2 days', NULL, 'DUE'),
    -- Aarav Patel (Overdue for MR-1)
    ('20000000-0000-0000-0000-000000000007', 'c0000000-0000-0000-0000-000000001045', 'MR (Measles-Rubella)', 1, CURRENT_DATE - INTERVAL '60 days', NULL, 'OVERDUE'),
    ('20000000-0000-0000-0000-000000000008', 'c0000000-0000-0000-0000-000000001045', 'JE (Japanese Encephalitis)', 1, CURRENT_DATE - INTERVAL '60 days', NULL, 'OVERDUE')
ON CONFLICT DO NOTHING;
