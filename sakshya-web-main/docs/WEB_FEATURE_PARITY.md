# Web / Android Feature Parity Matrix & Verification Status (`v1`)
**Date:** 2026-11-21  
**Author:** Agent 3 (Web Application, Supabase & Integration Lead)

| # | Capability | Implementation Component / Service | Status | Notes / Evidence |
|---|---|---|---|---|
| 1 | Login, Session & Logout | `src/components/auth/LoginScreen.tsx`, `src/app/page.tsx` | Implemented | Supports Supabase Email Auth when configured + Synthetic Role Demo Login + sign out cleanup. |
| 2 | Worker Profile & Role Routing | `src/components/layout/AppShell.tsx` | Implemented | Role-scoped navigation for ASHA Worker vs. PHC Supervisor. |
| 3 | Two-Mode ASHA UX (Basic Default + Advanced) | `src/components/voice/ModeSelector.tsx`, `BasicVisitView.tsx`, `AdvancedVisitView.tsx` | Implemented | Shared `useVoiceVisitSession` hook + identical `VisitDraft` data model. |
| 4 | Beneficiary Search, Selection & Clarification | `src/components/voice/BeneficiarySelector.tsx` | Implemented | Name/BEN-ID search, quick recent cards, `clarification_required` candidate tap cards. |
| 5 | Language Selection | `src/components/voice/LanguageSelector.tsx` | Implemented | 10 Indic languages + `indic-auto`, persisted in `localStorage` & synced via `set_language`. |
| 6 | Live Mic Capture (16kHz PCM, PTT & Hands-Free) | `src/lib/voice/voice-client.ts`, `VoiceRecorderAndTranscript.tsx` | Implemented | Linear resampler to `16000 Hz` mono `pcm_s16le`, `1024`-byte binary frames, PTT & Hands-Free toggle, device selector. |
| 7 | Real-Time Waveform & 11 Voice States | `VoiceRecorderAndTranscript.tsx` | Implemented | Web Audio `AnalyserNode` bands (zero fake idle motion) + 11 distinct state badges. |
| 8 | Live Partial & Final Transcription | `LiveTranscript` | Implemented | Renders `stable_text` + italic `volatile_text`, latency readout, accessible live region. |
| 9 | Timbre PCM Streaming Read-Back & Pause/Resume | `BrowserVoiceClient`, `SpokenDescription` | Implemented | `AudioBufferSourceNode` scheduler with `suspend()`/`resume()`. |
| 10 | Barge-In & Zero-Stale-Audio Flush | `BrowserVoiceClient`, `VoiceRecorder` | Implemented | Monotonic `activeTurnId` drops stale chunks; `tts_cancelled` / `barge_in` stops active sources immediately. |
| 11 | Structured Visit Extraction & Field Badges | `VisitSummaryCard`, `CapturedField`, `AdvancedVisitView` | Implemented | Never fabricates missing data (`null` displayed as *Not identified*); status pills (`Extracted`, `Needs Clarification`, `Corrected`, `Confirmed`). |
| 12 | Voice Field Correction (Patch Single Field) | `VoiceCorrectionControl`, `useVoiceVisitSession.ts` | Implemented | Triggers barge-in correction, reflects `correction_applied` while preserving unchanged fields + requires re-read-back. |
| 13 | Explicit Accept & Save + Discard Re-record | `VisitConfirmationActions`, `NativeConfirmDialog` | Implemented | Sends `confirm_visit`, completes `persistence_requested -> persistence_ack -> visit_committed`, shows `VisitSuccess`. |
| 14 | Urgent Danger-Sign Override & Referral Workflow | `DangerAlertBanner.tsx`, `DangerCommandCenterView.tsx` | Implemented | Immediate assertive alert independent of save; NHM guideline citation; `active -> acknowledged -> referred -> resolved`. |
| 15 | Beneficiary Directory, Profiles & Schedules | `BeneficiaryDirectoryView.tsx` | Implemented | Search, category chips, profile drawer with visit/vaccine/follow-up history. |
| 16 | Follow-Up Queue & Immunisations | `FollowUpQueueView.tsx` | Implemented | Upcoming, Overdue, Pending Vaccines, and Completed views. |
| 17 | Visit History & Detail Modal | `VisitHistoryView.tsx` | Implemented | Responsive stacked cards on mobile + accessible table on desktop. |
| 18 | Offline Drafts (IndexedDB) & Conflict Sync | `indexeddb-store.ts`, `sync-manager.ts`, `OfflineDraftsView.tsx` | Implemented | Idempotency keys (`visit_id`), never auto-commits `draft`, conflict status UI. |
| 19 | PHC Supervisor Command Center & Analytics | `src/components/supervisor/*`, `supervisor-metrics.ts` | Implemented | Zero hardcoded KPIs; real charts, worker directory, CSV export, print/PDF report, audit trail. |
