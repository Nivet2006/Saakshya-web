# Web Integration Handoff & Manual Testing Checklist (`v1`)

> **Platform:** ASHA Voice Field Register (`sakshya-web-main`)  
> **Architecture:** Next.js 14 (App Router, TypeScript, Tailwind CSS) + Agent 1 FastAPI Voice Backend + Supabase PostgreSQL/Auth/Realtime + IndexedDB Offline Queue

---

## 1. Two-Mode ASHA Experience & Routes

| Area | Component | Behaviour |
|---|---|---|
| **Login & Role Session** | `src/components/auth/LoginScreen.tsx` | Supports Supabase Email/Password Auth (when configured) + instant Synthetic Role cards (`ASHA_WORKER`, `PHC_SUPERVISOR`) and preferred language selection. |
| **Responsive App Shell** | `src/components/layout/AppShell.tsx` | Mobile fixed bottom nav with center mic CTA + safe-area insets (`360px–767px`), slide-over tablet drawer (`768px–1023px`), persistent left clinical rail on desktop (`1024px–1920px+`). |
| **ASHA Home** | `src/components/asha/AshaHomeView.tsx` | Field summary, active critical danger alerts, pending follow-ups, recent visits, and prominent **Start Voice Visit** CTA. |
| **Voice Visit — Basic Mode (Default)** | `src/components/voice/BasicVisitView.tsx` | Simple 6-step voice-first flow: `BeneficiarySelector` → `LanguageSelector` → `VoiceRecorder` → `ProcessingIndicator` → `VisitSummaryCard` (*Here's what I understood from your visit*) → `VisitConfirmationActions` (`[ ✓ Accept & Save ]` / `[ ✕ Reject / Correct by Voice ]`) → `VisitSuccess`. |
| **Voice Visit — Advanced Mode** | `src/components/voice/AdvancedVisitView.tsx` | Shares the exact same `VisitDraft` and WebSocket session; displays 8 detailed sections (Beneficiary, Maternal ANC/PNC, Newborn HBNC, Immunisation Ledger, Danger Signs, Follow-up Actions, Full Transcript & Correction Diff Log, Field-Level Confirmation controls). |
| **Beneficiary Directory** | `src/components/asha/BeneficiaryDirectoryView.tsx` | Search by name/`BEN-ID`/ward, category chips, profile drawer with visit history, immunisations, follow-ups, and 1-tap voice start. |
| **Follow-Ups & Vaccines** | `src/components/asha/FollowUpQueueView.tsx` | Upcoming, Overdue, Pending Vaccinations, and Completed queues. |
| **Visit History** | `src/components/asha/VisitHistoryView.tsx` | Saved/committed visits in responsive mobile cards / desktop table with detail inspection dialog. |
| **Offline Drafts** | `src/components/asha/OfflineDraftsView.tsx` | IndexedDB (`asha_field_register_v2`) manager showing `draft`, `pending`, `failed`, `conflict`, and `synced` records. Never auto-commits unconfirmed `draft` records. |
| **Supervisor Command Center** | `src/components/supervisor/*` | Real computed KPI overview, Danger Alert Command (`active → acknowledged → referred → resolved`), ASHA Worker Management, Live Visit Register, Real Data Analytics Charts, Reports (CSV Export + Print/PDF + Audit Trail). |

---

## 2. Environment Variables (`.env.local`)

```env
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_VOICE_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_VOICE_WS_URL=ws://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
```

---

## 3. Supabase Schema, RLS & Real-Time

- Migrations live in `supabase/migrations/`:
  1. `20261121000001_initial_schema.sql` — tables + RLS policies (`facilities`, `profiles`, `beneficiaries`, `visits`, `danger_alerts`, `referrals`, `follow_ups`, `immunisations`, `sync_audit_logs`).
  2. `20261121000002_seed_synthetic_data.sql` — initial synthetic PHC/worker/beneficiary seed.
  3. `20261121000003_align_v1_contracts.sql` — adds `visit_id`, `weight_kg`, `vaccinations_completed`, `vaccinations_due`, `confirmed_at`, `committed_at`, danger metadata columns, and aligns `BEN-1042`..`BEN-1048`.
- **Service-role hygiene:** `SUPABASE_SERVICE_ROLE_KEY` is never referenced in `src/` or `NEXT_PUBLIC_*` variables.

---

## 4. Known Browser & Offline Limitations

1. **Live Voice AI Requires Network:** Gnani Prisma v3.0 STT and Timbre v3.0 TTS execute on Agent 1's FastAPI backend; voice streaming is unavailable offline. Offline mode stores incomplete drafts and queues confirmed visits in IndexedDB for sync when connectivity returns.
2. **Audio Autoplay & Microphone Permissions:** Browsers require a user gesture to unlock `AudioContext` playback and grant microphone access; tapping **Start Recording** initiates both cleanly.
3. **Google Stitch Access Note:** Stitch MCP tools were unavailable in this build session; UI tokens and responsive screens faithfully extend the existing `docs/DESIGN.md` and `docs/STITCH_DESIGN_HANDOFF.md` (`projects/12337212643351304899`) alongside direct two-mode ASHA requirements.

---

## 5. Manual End-to-End Testing Checklist (Owner Verification)

Run Backend (`port 8000`) and Frontend (`cd sakshya-web-main && npm run dev` on `port 3000`), then verify:

- [ ] **Auth & Role Navigation:** Open `http://localhost:3000`, verify Login renders cleanly, select `Sunita Verma (ASHA)`, confirm Basic Mode opens by default.
- [ ] **Beneficiary & Language:** Select `Lakshmi Devi (BEN-1042)` via search or quick cards; switch language (`hi-IN` → `kn-IN` → `hi-IN`) and reload page to verify persistence.
- [ ] **Mic Permission & Live Voice:** Tap **Start Recording**, grant mic permission, verify real Web Audio waveform responds to voice and `Connected` pill is green.
- [ ] **Live Transcription & Extraction:** Speak an ANC visit note (or use *Type to Backend* for deterministic input); verify interim (`volatile_text`) and final transcription plus extracted `VisitSummaryCard`.
- [ ] **Read-Back & Spoken Correction (Barge-In):** While Timbre audio plays back the summary, interrupt by speaking or tapping **Interrupt / Speak Now** (*"No, weight is 2.8 kilo"*). Verify playback cuts immediately, only `weight_kg` updates (`Corrected` pill), and remaining fields stay intact.
- [ ] **Urgent Danger Sign Override:** Speak a critical symptom (*"Pregnancy mein bleeding ho rahi hai"* or *"Baby ka chest indrawing ho raha hai"*). Confirm red `URGENT DANGER SIGN` banner interrupts speech immediately before form completion, displays official NHM guideline ref & PHC referral message, and remains attached.
- [ ] **Two-Mode Parity:** Switch to **ADVANCED MODE** mid-session or post-extraction; verify the exact same `visit_id`, weight, vaccinations, danger signs, and field confirmation controls reflect live state without resetting data.
- [ ] **Explicit Accept & Save:** Tap **✓ ACCEPT & SAVE** and confirm `VisitSuccess` displays `persistence_record_id` and `Next Follow-up`.
- [ ] **Offline Drafts & Reconnect Sync:** Toggle browser DevTools to Offline, check `Offline Drafts`, restore Online, tap **Sync Confirmed Queue**, and confirm no duplicate visit appears in `Visit History`.
- [ ] **Supervisor Command Center:** Switch profile / portal to `Dr. Sunita Rao (MOIC)`, verify KPIs reflect actual counts, acknowledge/refer/resolve danger alert, filter `Live Visit Register`, check `Analytics` charts, and test `Export CSV` + `Print / PDF Report`.
- [ ] **Responsive Viewports:** Check `360px`, `390px`, `430px` (mobile bottom nav, stacked cards, zero horizontal overflow), `768px`, `1024px` (drawer / 2-col layout), and `1280px`, `1440px`, `1920px` (left sidebar rail + multi-column workspace).
