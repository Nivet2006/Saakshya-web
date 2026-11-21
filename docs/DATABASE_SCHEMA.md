# ASHA Voice Field Register — PostgreSQL Database Schema & RLS
**Date:** 2026-11-21  
**Author:** Agent 3 (Web & Database Lead)  
**Status:** Verified & Migration Ready

## 1. Overview
The database architecture provides strict data isolation, role-based scoping, auditability, and full feature parity with the Android client. All tables are created in Supabase PostgreSQL with Row Level Security (RLS) enabled.

## 2. Entity Relationship Summary

```
[Facilities (PHC / CHC)]
       ▲
       │ phc_id
       ├─── [Profiles (ASHA Workers / Supervisors)]
       │           ▲
       │           │ assigned_asha_id
       │           ├─── [Beneficiaries] ◄────────┐
       │           │           ▲                 │
       │           │           │ beneficiary_id  │ beneficiary_id
       │           │     [Visits]                │
       │           │           ▲                 │
       │           │           │ visit_id        │
       │           └───── [Danger Alerts] ───────┤
       │                       ▲                 │
       │                       │ alert_id        │
       │                 [Referrals] ────────────┘
       │
       └─── [Follow-ups]
       └─── [Immunisations]
       └─── [Sync Audit Logs]
```

## 3. Core Tables

1. **`facilities`**: Rural health infrastructure hierarchy (PHCs, CHCs, Sub-Centres, District Hospitals).
2. **`profiles`**: ASHA workers, PHC Medical Officers/Supervisors, and System Administrators with assigned geographic areas and preferred languages (`hi-IN`, `kn-IN`, `ta-IN`, `en-IN`).
3. **`beneficiaries`**: High-risk pregnancy tracking, infants, and children with stable synthetic identifiers (`BEN-1042`).
4. **`visits`**: Structured home visit encounters including vitals JSONB, administered immunisations, IFA counts, danger flags, and idempotency keys to prevent duplicate submissions during offline sync.
5. **`danger_alerts`**: Safety-critical events flagged by the deterministic clinical rule engine, storing symptom evidence, escalation status, and supervisor acknowledgement.
6. **`referrals`**: Emergency transport tracking (108 ambulance dispatch, transit status, admitting facility).
7. **`follow_ups`**: Overdue tracking, scheduled postnatal visits, and vaccination due dates.
8. **`immunisations`**: National Immunisation Schedule (NIS) tracking with dose status (`DUE`, `OVERDUE`, `GIVEN`, `MISSED`).
9. **`sync_audit_logs`**: Tamper-evident ledger of sync operations, role access, and clinical status changes.

## 4. Row Level Security (RLS) Enforcement

- **ASHA Workers**: Strictly isolated to their own assigned beneficiaries, visits, and follow-ups.
- **PHC Supervisors**: Authorized to view, monitor, and acknowledge alerts across all ASHA workers within their assigned PHC facility scope.
- **Service Role Key**: Retained server-side only. Browser clients connect via anon key with user session token.
