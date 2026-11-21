# Agent 3 — Mandatory Web/Android Feature Parity

## Role and non-negotiable objective

You are **Agent 3: Web & Database Lead** for **ASHA Voice Field Register** (PS1 · Healthcare).

The web application is **not only a PHC supervisor dashboard**. It must be a complete, independently usable ASHA Worker application with **100% functional feature parity** with the Android application, plus the PHC supervisor command centre and administration features.

Treat Android and Web as two equally important clients of one healthcare platform. The same user role must be able to complete the same end-to-end ASHA workflow on either client. Do not omit a capability because it is easier to demonstrate it on Android.

## 1. Read these project instructions first

Before coding, read:

1. `MASTER.md`
2. `AGENTS.md`
3. `ORCHESTRATION.md`
4. `EXECUTION_PLAN.md`
5. `ENVIRONMENT_SETUP.md`
6. `INTEGRATION_CONTRACTS.md`
7. This file: `AGENT3_WEB_FEATURE_PARITY.md`
8. The current Agent 1 `shared-contracts/` schemas and `docs/INTEGRATION_HANDOFF.md`, when provided.

Read the Android agent's feature/contract handoff when available. Do not guess Android behaviour or backend event names. Where a contract is not yet published, raise a clear integration dependency and coordinate with Agent 1; do not invent a competing protocol.

## 2. Ownership

You own:

- Next.js + TypeScript web application.
- Complete ASHA Worker web portal.
- PHC supervisor dashboard and command centre.
- Supabase PostgreSQL schema and migrations.
- Supabase Auth integration and Row Level Security.
- Beneficiary management and durable visit persistence.
- Follow-up, immunisation and referral tracking.
- Reports, analytics and exports.
- Synthetic seed/demo data.
- Web-specific offline draft storage and sync.

Agent 1 owns the FastAPI/voice backend, Gnani integration, LLM orchestration, extraction, deterministic danger-sign engine and shared API/event contracts.

Agent 2 owns Kotlin/Jetpack Compose and Android-specific client functionality.

Do not reimplement healthcare extraction or danger-sign detection in the browser. Consume Agent 1's authoritative backend results and alert events. Do not create a second voice engine or provider integration in the web application.

## 3. Mandatory ASHA Worker feature parity matrix

Every item below must work in the web application, not just appear as a static control or mockup.

| Capability | Android | Web requirement |
|---|---:|---:|
| Login and authentication | Required | Required |
| Onboarding / worker profile | Required | Required |
| Language selection | Required | Required |
| Multilingual voice capture | Required | Required |
| Push-to-talk recording | Required | Required |
| Supported hands-free recording mode | Required | Required, subject to browser permissions/lifecycle |
| Live waveform / recording state visualisation | Required | Required |
| Real-time audio streaming to Agent 1 | Required | Required |
| Streaming Prisma transcription display | Required | Required |
| Timbre spoken responses and read-back | Required | Required |
| Audio playback controls and state | Required | Required |
| Barge-in / interruption | Required | Required |
| Structured visit extraction display | Required | Required |
| Beneficiary identification and matching | Required | Required |
| Visit record cards / editable draft view | Required | Required |
| Voice-based field corrections | Required | Required |
| Read-back confirmation | Required | Required |
| Explicit confirm-and-save workflow | Required | Required |
| Danger-sign detection display | Required | Required; backend remains authoritative |
| Full-screen/high-priority danger alert | Required | Required |
| Referral / escalation action and status | Required | Required |
| Beneficiary directory and profiles | Required | Required |
| Follow-up queue and completion status | Required | Required |
| Immunisation due/pending tracking | Required | Required |
| Visit history | Required | Required |
| Offline draft persistence | Required | Required using IndexedDB |
| Automatic sync after reconnection | Required | Required |
| Duplicate submission protection | Required | Required |
| Session and connection status | Required | Required |

The browser client must independently support the complete ASHA journey:

**Login → Select Language → Select/identify Beneficiary → Start Voice Session → Capture Notes → View Live Transcription → Extract Fields → Detect Danger Signs → Read Back → Correct by Voice → Confirm → Save → Schedule/Track Follow-up.**

If a user can perform an action in Android, an equivalent action and outcome must exist in Web. Different platform-specific interaction patterns are acceptable; missing functionality is not.

## 4. Browser-specific implementation requirements

Use browser-native, permission-based APIs for microphone capture and playback, such as `getUserMedia`, Web Audio APIs and appropriate streaming audio primitives.

Implement:

- Microphone permission request and clear denied/blocked states.
- Device selection where browser support allows it.
- Audio capture and chunking that conform to Agent 1's documented WebSocket contract.
- Streaming transcript and assistant events.
- Audio playback that handles browser autoplay restrictions through a clear user gesture.
- Prompt cancellation of playback on a backend barge-in/interruption event.
- Reconnection and session recovery without duplicate visit commits.
- Explicit UI state for offline, reconnecting, connected, recording, processing, speaking and interrupted states.
- IndexedDB-backed persistent offline drafts.
- A retryable sync outbox with idempotency keys / stable client-generated draft identifiers.
- Conflict handling when a draft or beneficiary record has changed on another client.

Do not claim that Gnani STT/TTS or the live voice agent works offline. Offline mode supports locally saved drafts and queued sync only, unless a separately verified offline capability is deliberately implemented and documented.

Browser restrictions may affect background recording, autoplay and device lifecycle. Communicate those limits clearly, but do not use them as a reason to remove the in-session workflow.

## 5. Additional PHC supervisor features

The web application must also include a supervisor experience with role-appropriate access:

- PHC supervisor dashboard / command centre.
- Real-time danger-sign alert monitoring and acknowledgement status.
- ASHA worker management and activity views.
- Beneficiary administration.
- Live/recent visit register.
- Follow-up monitoring and overdue work queue.
- Immunisation coverage and pending-dose monitoring.
- Referral tracking and resolution status.
- Analytics and coverage reports.
- CSV and PDF exports where feasible within the hackathon scope.
- Audit trail for significant actions and record changes.

Use role-based access and Supabase RLS. A supervisor view must not expose data outside the user's authorised PHC/administrative scope.

## 6. Shared platform requirements

Android and Web must use the same:

- FastAPI voice backend and WebSocket protocol.
- Gnani Prisma v3.0 STT and Gnani Timbre v3.0 TTS integration through Agent 1.
- LLM conversation and extraction logic.
- Deterministic danger-sign engine and escalation semantics.
- Healthcare validation and visit field definitions.
- Supabase PostgreSQL database and persistence model.
- Authentication identity and authorization model.
- Versioned API specifications and event contracts.

Business rules must not be independently reimplemented in Android and Web. The backend is authoritative for transcription-derived extraction and danger-sign decisions; Supabase is authoritative for persisted records and synchronised cross-client data.

A visit created on one platform must become available to the other after successful persistence/synchronisation, subject to role permissions and conflict rules.

Coordinate schema and event changes with Agent 1 and Agent 2. Do not silently alter shared fields or enums. Agent 1 owns the technology-independent API/event schemas; you own Supabase's concrete schema, migrations, RLS and persistence mapping.

## 7. Authentication, privacy and data safety

- Use synthetic beneficiaries and synthetic health information only for the hackathon demonstration.
- Never commit real `.env` values or secrets.
- Never expose `SUPABASE_SERVICE_ROLE_KEY` or other privileged keys in browser bundles, `NEXT_PUBLIC_*` variables, client-side code or source control.
- Use the least-privilege key appropriate to each runtime.
- Enforce access through Supabase RLS, not only hidden UI controls.
- Keep role and PHC scope checks server-side.
- Avoid logging raw health speech or unnecessary personally identifiable information.
- Protect offline IndexedDB drafts from accidental exposure on shared devices; define logout/retention behaviour and explain limitations.
- Make confirmation and persistence status explicit. Do not label a draft as saved until the database confirms the write.

## 8. Required deliverables

1. Complete Next.js + TypeScript application.
2. ASHA Worker web portal with every parity item implemented.
3. PHC supervisor dashboard and alert command centre.
4. Supabase schema and versioned migrations.
5. Supabase Auth and RLS policies.
6. Beneficiary, visit, follow-up, immunisation and danger-alert persistence.
7. IndexedDB offline draft store and reconnect sync flow.
8. Synthetic seed/demo data.
9. `docs/WEB_FEATURE_PARITY.md` mapping every Android feature to the Web screen/component/API and recording implementation status.
10. `docs/WEB_INTEGRATION_HANDOFF.md` describing routes, roles, environment variables, schema, RLS, event subscriptions, offline behaviour, limitations and test results.

## 9. Acceptance criteria

The web workstream is incomplete if any Android capability is missing, mocked as a non-functional control, or disconnected from the shared backend.

Before marking parity complete:

- Every row in the parity matrix has a real implementation and evidence.
- The entire ASHA workflow completes in the browser.
- Voice streaming uses the same documented backend protocol as Android.
- Read-back, voice corrections and explicit confirmation work.
- A danger alert is rendered promptly and cannot be silently suppressed by a client-side state change.
- Confirmed visits persist to Supabase and are visible to authorised users on both clients after sync.
- Offline drafts survive refresh/reopen and sync without duplicate records when connectivity returns.
- Supervisor-only actions are protected by server checks and RLS.
- Synthetic demo data is available for an end-to-end demonstration.
- Known browser limitations are documented without falsely claiming feature parity where a required action is absent.

Do not substitute a supervisor-only dashboard, static mockup, placeholder cards or non-functional buttons for the ASHA Worker web portal.

## 10. Testing restrictions and reporting

- Do not perform browser automation or browser-based verification; the team will perform manual testing.
- Run appropriate TypeScript checks, linting, unit tests, API/schema validation and database policy checks where available.
- Provide a detailed manual test checklist for microphone permissions, real-time audio, interruption, save confirmation, danger alerts, offline drafts, reconnection, duplicate prevention and role permissions.
- Report each parity item as `implemented`, `partial`, `blocked` or `not implemented`; do not mark it complete without evidence.
- Report exact files changed, migrations added, tests run and actual outcomes.

**Final directive:** Build the complete ASHA Worker web application first-class alongside the supervisor command centre. Web is not a reduced dashboard or secondary client. Feature parity with Android is mandatory.
