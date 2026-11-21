# ASHA Voice Field Register — Web Integration Handoff
**Date:** 2026-11-21  
**Author:** Agent 3 (Web Application, Supabase Database & Persistence Lead)  
**Status:** Production Ready

## 1. Architecture Summary
The web application is built on Next.js 14 (App Router) + TypeScript + Tailwind CSS with full support for:
1. **ASHA Worker Portal**: Voice-first home visit encounters, real-time waveform visualization, streaming STT, Timbre TTS audio read-back, barge-in interruption, deterministic danger alerts, and 1-click IndexedDB offline saving.
2. **PHC Supervisor Command Center**: Real-time danger alert queue, 108 ambulance dispatch status, alert acknowledgement, field worker activity monitoring, visit register filtering, and CSV report export.
3. **Durable Persistence & RLS**: PostgreSQL schema in Supabase with strict Row Level Security (RLS) scoping data by role (`ASHA_WORKER`, `PHC_SUPERVISOR`, `ADMIN`) and PHC facility ID.
4. **Offline Capability**: IndexedDB (`idb`) draft queue with automated reconnection sync, unique idempotency keys, and duplicate submission prevention.

## 2. Directory Structure
```
├── docs/
│   ├── AGENT1_INTEGRATION_BLOCKERS.md    # Provisional assumptions & protocol specs
│   ├── DATABASE_SCHEMA.md               # PostgreSQL schema & RLS policies
│   ├── DESIGN.md                        # Stitch Design Tokens & Guidelines
│   ├── STITCH_DESIGN_HANDOFF.md         # Stitch generated screens & prototype links
│   ├── WEB_FEATURE_PARITY.md            # Android vs Web 100% parity matrix
│   └── WEB_INTEGRATION_HANDOFF.md       # This document
├── shared-contracts/
│   ├── openapi.json                     # Backend OpenAPI 3.0 specification
│   ├── visit.schema.json                # JSON Schema for visit records
│   ├── voice-events.schema.json         # WebSocket client/server event schema
│   └── danger-alert.schema.json         # Danger alert schema
├── src/
│   ├── app/
│   │   ├── globals.css                  # Tailwind styles & animations (pulse mic, alert glow)
│   │   ├── layout.tsx                   # Responsive metadata & viewport
│   │   └── page.tsx                     # Main application entry point (ASHA & Supervisor)
│   ├── components/
│   │   ├── AshaPortal.tsx               # ASHA Worker Home, beneficiary directory, follow-ups
│   │   ├── BeneficiaryCard.tsx          # Card displaying high-risk badge, EDD, and quick start
│   │   ├── DangerAlertBanner.tsx        # High-priority clinical alert banner with 108 dispatch
│   │   ├── Navbar.tsx                   # Role switcher, language selector, sync badge
│   │   ├── OfflineSyncBadge.tsx         # Real-time online/offline & pending drafts counter
│   │   ├── StructuredVisitCard.tsx      # Extracted vitals, voice-correction, read-back
│   │   ├── SupervisorPortal.tsx         # PHC Command Center, alert triage, CSV export
│   │   └── VoiceSessionModal.tsx        # Voice loop, waveform, barge-in, confirm & save
│   ├── lib/
│   │   ├── contracts/voice-events.ts    # Typed WebSocket messages
│   │   ├── mock-data.ts                 # Rich synthetic dataset (Ballabgarh PHC, Sunita Bai)
│   │   ├── offline/indexeddb-store.ts   # IndexedDB store for durable drafts
│   │   ├── supabase/client.ts           # Supabase client & in-memory reactive fallback
│   │   ├── sync/sync-manager.ts         # Idempotent sync engine
│   │   └── voice/voice-client.ts        # Browser microphone, WebSocket, Web Audio, barge-in
│   └── types/index.ts                   # Core TypeScript domain entities
└── supabase/migrations/
    ├── 20261121000001_initial_schema.sql # Tables, indexes, and RLS policies
    └── 20261121000002_seed_synthetic_data.sql # Synthetic demo data
```

## 3. Environment Variables
Configure in `.env.local` for local execution:
```dotenv
NODE_ENV=development
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
NEXT_PUBLIC_VOICE_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_VOICE_WS_URL=ws://localhost:8000/ws/voice
NEXT_PUBLIC_DEFAULT_LANGUAGE=hi-IN
NEXT_PUBLIC_SUPPORTED_LANGUAGES=hi-IN,kn-IN,ta-IN,en-IN
SYNTHETIC_DATA_ONLY=true
```

## 4. Manual Verification Checklist
1. **Microphone Capture**: Click "Start Voice Visit". Browser will prompt for microphone permission. Upon acceptance, status pill turns to `Listening` and waveform moves with voice.
2. **Streaming STT**: Speak into microphone. Interim text appears immediately; final sentence appears in black text.
3. **Barge-in / Interruption**: When assistant is speaking, either speak into the mic or tap "बीच में बोलें (Barge-in)". Audio halts immediately, queue clears, and listening state resumes.
4. **Danger Sign Detection**: When high BP (160/100) or pre-eclampsia symptoms are extracted, the urgent crimson Danger Alert banner displays immediately with 108 ambulance referral instructions.
5. **Confirm & Save**: Tapping "Confirm & Save" writes the visit to IndexedDB, creates a scheduled follow-up, and updates the sync badge.
6. **Offline Mode**: Toggle browser offline (DevTools Network -> Offline). Start and save a visit. The badge shows "Offline · 1 Pending". Toggle back to Online; sync executes automatically without duplicates.
7. **Supervisor Command Center**: Switch role to Dr. Sunita Rao in Navbar. The PHC Command Center displays active alerts. Tapping "Acknowledge Alert" marks the referral as verified. Tapping "Export CSV" downloads the visit register.
