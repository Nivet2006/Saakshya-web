# AGENT 3 — MASTER ARCHITECT & WEB/DATABASE LEAD
## ASHA Voice Field Register | PS1 · Healthcare | 24-hour hackathon

You are **Agent 3: Web Application, Supabase Database and Persistence Lead**. You are running in an **independent development environment / on a separate system** from Agents 1 and 2. Treat this document as your standalone source of truth for your assigned scope. Do not assume their repositories, local files, environment variables, or working directories are available on this machine.

You may create and coordinate as many specialist sub-agents or parallel workers as useful. You have architectural authority over the Agent 3 web application, database schema, migrations, authentication, Row Level Security (RLS), persistence, offline web drafts and supervisor portal. Review all delegated work before integration.

You do **not** own Agent 1's voice/AI backend or Agent 2's Android application. Respect the boundaries and integration rules in this document.

---

# 1. MISSION

Build a complete, production-minded web application for **ASHA Voice Field Register**. The web application is not merely a PHC supervisor dashboard. It must be a fully functional alternative to the Android application for ASHA workers, with **100% functional feature parity**, plus additional PHC supervisor and administrator capabilities.

Both clients must use the same platform:

- Agent 1's FastAPI voice backend and Gnani Prisma v3.0 / Timbre v3.0 services.
- The same LLM conversation and healthcare validation logic.
- The same Supabase PostgreSQL database.
- The same authentication and authorization model.
- The same versioned API and WebSocket event contracts.

Do not independently reimplement voice intelligence, medical extraction, danger-sign rules or conversational state logic in the web client. The browser is a client of the shared backend, not a second AI backend.

The central ASHA workflow must work entirely through voice while the web application is open:

`Login → Select Language → Start Voice Session → Capture Notes → Extract Fields → Detect Danger Signs → Read Back → Correct by Voice → Confirm → Save → Schedule Follow-up`

Normal workflow must not require typing. Provide accessible alternatives for permissions, device limitations and recovery, but do not make typing the primary interaction.

---

# 2. THREE-AGENT OWNERSHIP MODEL

## Agent 1 — AI Voice & Backend
Owns:
- Gnani Prisma v3.0 streaming STT.
- Gnani Timbre v3.0 streaming TTS.
- FastAPI voice backend and WebSocket protocol.
- Pipecat orchestration where verified compatible.
- LLM conversation management.
- Multilingual understanding and code-mix handling.
- VAD, endpointing, barge-in and interruption handling.
- Structured healthcare extraction and validation.
- Read-back/correction state machine.
- Deterministic danger-sign detection and escalation logic.
- Technology-independent API, event and JSON contracts.

## Agent 2 — Android Application
Owns:
- Kotlin and Jetpack Compose application.
- ASHA worker mobile experience.
- Android microphone, streaming audio and playback integration.
- Android offline drafts and sync UX.
- Android-specific authentication and screens.

## Agent 3 — YOU: Web & Database
Owns:
- Next.js + TypeScript web application.
- Complete ASHA Worker Web Portal with full Android feature parity.
- PHC supervisor command center and administrator experience.
- Supabase PostgreSQL schema, migrations, seed data and indexes.
- Authentication, role/PHC scoping and RLS policies.
- Beneficiary, visit, follow-up, immunisation and danger-alert persistence.
- Realtime web updates and notification presentation.
- Browser offline draft storage and synchronization.
- Reports, analytics and CSV/PDF exports.
- Web client integration with Agent 1's API and Agent 2's shared data model.

### Non-negotiable ownership boundaries

1. Agent 1 owns the actual danger-sign detection logic and clinical rule list. You persist and display its structured alert events; do not create a competing detector or change the official list.
2. Agent 1 owns the voice conversation and extraction business logic. The web client captures/plays audio, renders events and sends user actions according to the shared contract.
3. Agent 3 owns the actual Supabase schema, migrations, authentication and RLS. Agent 1 may define technology-independent JSON/API contracts but must not create competing Supabase migrations.
4. Agent 2 owns Android source code. Do not create or modify Android modules.
5. All clients must respect one canonical set of versioned contracts. Do not silently fork event names, field names, enum values or validation rules.

---

# 3. INDEPENDENT-REPOSITORY STARTUP — DO THIS FIRST

You are running on a separate system. Start by inspecting the repository available in your current working directory. Do not assume any files from Agent 1's or Agent 2's computer exist here.

Before substantial coding:

1. Inspect the current repository, directory structure, existing app, package manager, Node.js version, installed dependencies, environment files and current Git status.
2. Preserve useful existing code. Do not overwrite a working project with a fresh scaffold.
3. Read any supplied `MASTER.md`, `AGENTS.md`, architecture notes, API schemas, OpenAPI spec, JSON Schemas, WebSocket protocol and integration handoff documents that are actually present. This `AGENT3_MASTER.md` remains the authority for your assigned scope.
4. Create/verify the root `.gitignore` immediately. Ensure `.env`, `.env.*` (except `.env.example`), `.next/`, `node_modules/`, build output, local databases, logs, test recordings and generated secrets are ignored.
5. Create/verify `.env.example` containing variable names and safe placeholders only.
6. Create local `.env.local` for Next.js from `.env.example` (or preserve an existing local env file). Never overwrite existing credentials. Keep all secrets out of source code, prompts, commits, logs and screenshots.
7. Configure Git for this independent project. If there is no repository, initialize one with `git init -b main`. If one already exists, preserve its history and configuration. Do not reinitialize.
8. Inspect `git status`, `.gitignore` and staged changes before every commit. Ensure `.env.local` and service-role credentials cannot be staged. Keep `.env.example` trackable.
9. Commit after each coherent milestone/batch and push the completed batch to the configured remote. If no remote exists, make local commits and report that pushing is blocked until a valid remote is provided/configured. Never invent a remote URL.
10. Never force-push, rewrite shared history or commit secrets. Do not stage the entire repository blindly; review the diff and staged file list.

### Suggested web `.env.example`

Use the existing project's established variable names if already defined. Otherwise start from this safe template and verify compatibility with the installed Supabase SDK and Agent 1 API:

```dotenv
# ASHA Voice Field Register — Agent 3 web environment
# Copy to .env.local and fill in local values. Never commit .env.local.

# Next.js
NODE_ENV=development
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Supabase public client configuration
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_OR_PUBLISHABLE_KEY

# Server-only secret. NEVER prefix with NEXT_PUBLIC_.
SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY

# Agent 1 voice / API backend — use the real URL supplied by Agent 1
NEXT_PUBLIC_VOICE_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_VOICE_WS_URL=ws://localhost:8000/ws/voice

# Optional app configuration
NEXT_PUBLIC_DEFAULT_LANGUAGE=hi-IN
NEXT_PUBLIC_SUPPORTED_LANGUAGES=hi-IN,kn-IN,ta-IN,en-IN
SYNTHETIC_DATA_ONLY=true
```

**Security:** `SUPABASE_SERVICE_ROLE_KEY` is server-only. Never expose it to browser bundles, client components, public runtime config or browser network calls. Prefer the Supabase anon/publishable key with strict RLS for normal browser operations. Use service-role access only in trusted server-side code when genuinely required, with explicit authorization checks. The `NEXT_PUBLIC_*` voice URL variables are endpoint addresses, not secrets; do not put API keys or bearer secrets in them.

Do not assume that the example WebSocket path or port is final. Replace it only after Agent 1 supplies the real protocol and endpoint. Do not expose the Gnani or LLM API keys in this web project; those belong in Agent 1's backend environment.

---

# 4. SOURCE-OF-TRUTH AND INTEGRATION HANDOFF

Because this is a separate machine, establish an explicit contract handoff before integrating live voice features.

Look for and consume the actual versioned artifacts from Agent 1 when available:

- `openapi.json` or equivalent API specification.
- Visit-record JSON Schema.
- WebSocket event schema.
- Danger-alert schema.
- Authentication/session expectations.
- Audio format, sample rate, framing, transport and WebSocket message details.
- Session creation, resume, cancellation and error semantics.
- Read-back, correction, confirmation and commit event semantics.

Likely filenames may include:
- `shared-contracts/openapi.json`
- `shared-contracts/visit.schema.json`
- `shared-contracts/voice-events.schema.json`
- `shared-contracts/danger-alert.schema.json`
- `docs/INTEGRATION_HANDOFF.md`

These are expected handoff artifacts, not permission to invent their contents. If they are not available yet:

1. Build a typed, replaceable frontend adapter interface and local contract fixtures clearly marked as fixtures.
2. Document every provisional assumption in `docs/AGENT1_INTEGRATION_BLOCKERS.md`.
3. Do not claim that live Gnani voice integration works against a mocked endpoint.
4. Do not lock the UI to guessed WebSocket event names or audio framing. Keep mapping logic isolated so it can be updated when the real contract arrives.
5. Continue with independently implementable database, authentication, UI and synthetic-data work.

Maintain contract compatibility. If a contract change is required, document the reason and coordinate the change through the shared specification rather than creating a web-only variant.

---

# 5. REQUIRED APPLICATION STRUCTURE

The web application has two equally important product areas under the same authenticated platform.

## A. ASHA Worker Web Portal — full Android feature parity

This is not optional and must not be deferred indefinitely in favour of the supervisor dashboard.

Implement every capability below:

1. Login, session management and onboarding.
2. Language selection and persisted language preference.
3. Multilingual voice capture.
4. Push-to-talk and supported hands-free recording while the app is active.
5. Real-time microphone audio streaming to Agent 1's backend.
6. Live waveform/audio-level visualization.
7. Streaming Prisma transcription events.
8. Timbre audio playback.
9. Barge-in/interruption and cancellation handling.
10. Conversation status and connection indicators.
11. Live structured visit extraction.
12. Beneficiary identification and matching against assigned synthetic beneficiaries.
13. Visit record cards showing extracted fields and missing/uncertain values.
14. Voice-based field corrections.
15. Spoken read-back confirmation.
16. Explicit confirm-and-save workflow.
17. Danger-sign alert presentation and urgent referral message playback.
18. Follow-up action creation and tracking.
19. Beneficiary directory and beneficiary profiles.
20. Immunisation/vaccination status and due tracking.
21. Visit history and visit details.
22. Offline visit draft storage using IndexedDB.
23. Automatic synchronization when connectivity returns.
24. Duplicate-submit protection and conflict handling.
25. Clear session, sync, microphone permission and network status.

Every Android feature must have a corresponding usable web implementation. Provide a feature-parity checklist mapping Android capability → web route/component/service → status → manual validation step.

## B. PHC Supervisor / Administrator Portal — additional capabilities

In addition to all ASHA functionality, provide:

- PHC supervisor overview/command center.
- Live danger-sign alert monitoring.
- Alert acknowledgement, referral status and follow-up monitoring.
- ASHA worker management and assignment visibility.
- Beneficiary administration within authorized PHC scope.
- Live/recent visit register.
- Follow-up and immunisation monitoring.
- Referral tracking.
- PHC coverage and operational analytics.
- Date, ASHA worker, village/area and visit-type filters where supported by stored data.
- CSV exports and useful PDF reports.
- Audit trail for important actions.
- Clear empty, loading, stale-data, permission-denied and error states.

Do not show unsupported analytics or fabricated metrics. All totals must derive from actual stored synthetic records and clearly scoped filters.

---

# 6. BROWSER VOICE IMPLEMENTATION

Use browser APIs for the web client while preserving Agent 1's shared voice protocol:

- `navigator.mediaDevices.getUserMedia()` for microphone access.
- Web Audio APIs / AudioWorklet where required by the verified backend audio format.
- The exact audio codec, sample rate, channel count, chunking and framing specified by Agent 1.
- WebSocket client with session lifecycle, reconnect handling and backpressure.
- Audio playback that correctly handles streaming chunks and cancellation.
- Explicit user gesture handling for browser autoplay restrictions.
- Microphone permission denied/unavailable and device-selection states.
- Device disconnect and network reconnect states.

Do not assume browser `MediaRecorder` output matches the backend's required streaming format. Verify and convert it if needed. Keep audio capture and protocol serialization in a dedicated service/hook rather than coupling it to UI components.

### Barge-in requirements

- Detect/forward user speech while assistant audio is playing according to Agent 1's protocol.
- Send the specified interruption/cancel event.
- Stop or flush current audio playback promptly.
- Prevent stale audio chunks from playing after an interruption.
- Preserve conversation/session identifiers and process the interrupting utterance.
- Reflect resumed assistant state in the UI.

### Browser limitations

- Do not claim background microphone recording is guaranteed; browser/OS lifecycle rules differ from Android.
- The full workflow must work while the web application is active and microphone permission is granted.
- Do not claim Gnani STT/TTS or LLM processing works offline.
- Offline support means saving drafts and queued user-approved operations locally, then synchronizing safely when connectivity returns.
- Explain permission, autoplay and connectivity constraints with actionable in-app guidance.

---

# 7. DATABASE, AUTHENTICATION AND RLS

Agent 3 owns the actual Supabase database implementation.

## 7.1 Schema and migrations

Inspect any existing schema and Agent 1's shared visit/alert contracts first. Design normalized PostgreSQL tables and migrations that map cleanly to those contracts. Avoid duplicating the same facts in unrelated tables.

Likely domain entities include (adapt to the existing project and verified contracts):

- user profiles / role assignments;
- PHC centres or facilities;
- ASHA worker profiles and PHC/area assignments;
- synthetic beneficiaries and household/area references;
- visit records;
- immunisation/vaccination records or structured visit fields;
- follow-up tasks;
- danger alerts;
- referral status/history;
- synchronization/idempotency metadata;
- audit events.

Do not create tables simply because they appear in this illustrative list. Define relationships, foreign keys, uniqueness, indexes, nullability, timestamps, status constraints and deletion behaviour deliberately.

Requirements:
- Version all schema changes as repeatable SQL migrations.
- Seed only synthetic demo data.
- Use stable synthetic IDs such as `BEN-1042`.
- Store dates/timestamps with clear timezone semantics; do not silently interpret ambiguous spoken dates in the browser.
- Preserve unknown extracted values as null/unknown.
- Make server/client ownership of writes explicit.
- Add indexes for real query patterns: PHC scope, ASHA worker, beneficiary, visit date, follow-up due date and active danger alerts.
- Ensure migrations can be applied from a clean database and are documented.
- Do not place real patient data, real phone numbers or real addresses in seeds.

## 7.2 Authentication and authorization

Implement secure Supabase authentication appropriate to the existing project. At minimum support the roles required by the product:

- ASHA worker.
- PHC supervisor.
- Administrator (only if required by the demo's actual operations).

Authorization must be enforced server-side and in PostgreSQL RLS, not only by hiding UI controls.

Define and test access boundaries. For example:
- An ASHA worker can access only their own profile, assigned beneficiaries and permitted visit/follow-up records.
- A PHC supervisor can access records within their authorized PHC/facility scope.
- An administrator can access only the scope explicitly granted by policy.
- Unauthenticated users cannot access protected beneficiary, visit, alert or report data.

Do not trust client-supplied `user_id`, role, PHC ID or ownership fields. Resolve identity from the authenticated session and validate authorization on every server-side operation.

## 7.3 RLS and secret handling

- Enable RLS on all tables containing user, beneficiary, visit, alert, follow-up or audit information.
- Write explicit select/insert/update/delete policies based on authenticated identity and authorized PHC/ASHA assignments.
- Test both allowed and denied access paths.
- Never use the service-role key in browser code.
- Do not weaken RLS to make the demo easier.
- Keep service-role operations server-side and narrowly scoped, with application authorization checks.
- Never log raw health transcripts, secrets or sensitive payloads by default.

---

# 8. OFFLINE DRAFTS AND SYNCHRONIZATION

The web client must support offline draft handling using IndexedDB.

Implement:
- Durable storage of unsubmitted visit drafts.
- A local client-generated draft/operation ID.
- Clear `pending`, `syncing`, `synced`, `failed` and `conflict` states (or equivalent contract-aligned states).
- Retry when connectivity returns and the app is active.
- Idempotent server submission using a stable client operation/idempotency key.
- Duplicate protection on both client and server/database layer where appropriate.
- Safe conflict handling; never silently overwrite a newer confirmed visit.
- Visible last-sync time and pending-count indicator.
- Cleanup only after the server confirms successful persistence.

Offline limitations:
- Do not run the Gnani voice pipeline offline.
- Do not imply a draft has been saved to Supabase until server confirmation is received.
- Do not queue a danger alert in a way that hides the need for immediate real-world PHC referral. An offline UI must communicate connectivity loss clearly; a local alert display does not equal server notification.
- Avoid persisting raw audio. Persist structured drafts and only the minimum information necessary for recovery.

---

# 9. DANGER-SIGN ALERTS AND SAFETY UX

Agent 1 is the source of truth for danger-sign matching and referral escalation. The web client must reliably receive, persist, display and preserve alert events.

When the backend emits a verified danger-sign event:

1. Immediately show a prominent, accessible alert in the active ASHA workflow.
2. Do not hide or defer it behind the normal visit form.
3. Show the matched danger-sign category and the safe referral instruction returned by the backend.
4. Mark the visit/alert as danger-flagged according to the shared contract.
5. Persist the alert using a secure server-side/database path.
6. Notify authorized PHC supervisors in real time where Supabase Realtime/approved backend events are configured.
7. Support acknowledgement and referral status tracking without implying that acknowledgement replaces referral.
8. Keep an audit record of authorized status changes.
9. Preserve the alert if the visit is later corrected, cancelled or partially completed.

Do not add medical diagnosis, medicine recommendations, treatment advice or home remedies. Do not invent a nearest PHC's location or phone number. Display only verified referral information supplied by the system or configured data.

For real-time monitoring, use Supabase Realtime or the approved event path with strict PHC-scoped authorization. Handle reconnects and re-fetch active alerts so transient WebSocket failures do not permanently lose an alert from the supervisor view.

---

# 10. UX, ACCESSIBILITY AND DESIGN EXPECTATIONS

Build a responsive, polished application for desktop, tablet and mobile browsers. The worker's interface must be easy to operate while moving between households and must not assume a large desktop screen.

Priorities:
- Voice-first worker home screen with one obvious start/stop control.
- Clear recording, listening, processing, speaking, interrupted and disconnected states.
- Large touch targets and legible typography.
- High contrast and accessible labels.
- Language-aware labels and status messages.
- Readable live transcript and structured visit preview.
- Clear missing/uncertain field presentation.
- Danger alert visually and semantically distinct, with screen-reader announcement.
- Minimal steps to start a visit and confirm a record.
- Useful offline/sync feedback.
- Supervisor pages optimized for reviewing alerts, follow-ups and operational status.

Avoid generic placeholder dashboards, static mock charts, nonfunctional controls and decorative UI that does not connect to real state. Prefer a coherent, consistent design system and reusable components. Make every visible action work or clearly mark it unavailable.

Do not let styling work delay the complete voice workflow and secure persistence.

---

# 10A. GOOGLE STITCH — MANDATORY UI DESIGN WORKFLOW

**You must use Google Stitch to design the web application's interface before implementing the main UI.** Do not jump directly from this specification to ad-hoc JSX/Tailwind screens.

Use the current Google Stitch workspace at <https://stitch.withgoogle.com/>. If a Stitch MCP server, SDK or supported agent integration is available in the development environment, use it. Otherwise, use the Stitch web application directly. Do not claim Stitch was used unless an actual Stitch project/design was created and reviewed.

Google Stitch is the design/prototyping stage, not the production application runtime. Its generated screens and code are design inputs. Implement the approved design in the existing Next.js + TypeScript codebase, wire every interaction to real application state/APIs, and preserve the shared architecture. Do not replace the application with a static Stitch export or deploy a separate disconnected prototype.

## 10A.1 Create a coherent Stitch project

Create one project named **ASHA Voice Field Register** and design both product areas under one consistent design system:

- **ASHA Worker Portal:** mobile-first, voice-first, low-friction interface for use between household visits.
- **PHC Supervisor Portal:** desktop-first operational command center that remains fully usable on tablet and mobile.

Both areas must look and feel like parts of the same healthcare platform. Do not create two unrelated themes.

## 10A.2 Design the complete screen inventory

Create and iterate on the important screens and states, not just a landing page or dashboard.

**ASHA Worker screens:**
1. Sign in / session state.
2. First-time onboarding and language selection.
3. Worker home with assigned beneficiaries, today's visits and follow-ups.
4. Start visit / choose or identify beneficiary.
5. Active voice capture with prominent microphone control, waveform/audio level, language and connection state.
6. Listening, partial transcription, processing, assistant speaking, interrupted and reconnecting states.
7. Live transcript and structured visit draft.
8. Read-back / review and explicit confirmation.
9. Voice correction state with the field being corrected clearly identified.
10. Full-screen, accessible danger-sign alert and referral instruction state.
11. Beneficiary directory and beneficiary profile.
12. Visit history and visit detail.
13. Immunisation/vaccination tracking.
14. Follow-up queue and follow-up detail.
15. Offline drafts, pending sync, sync failure and conflict resolution.

**PHC Supervisor / Admin screens:**
1. PHC command center overview.
2. Live danger-sign alert queue and alert detail.
3. ASHA worker list, worker detail and assignment views.
4. Beneficiary administration and beneficiary detail.
5. Visit register with filters and visit detail.
6. Follow-up and immunisation monitoring.
7. Referral tracking.
8. Analytics and coverage reports.
9. Export/report configuration and audit trail.

Prioritise the complete ASHA voice journey and danger-alert states. Avoid spending disproportionate design time on decorative analytics before the worker workflow is designed.

## 10A.3 Responsive design is mandatory

Design and explicitly review responsive layouts for these viewport classes:

- **Small mobile:** approximately 360–390 CSS px wide.
- **Large mobile:** approximately 414–430 CSS px wide.
- **Tablet:** approximately 768–1024 CSS px wide, including portrait and landscape where relevant.
- **Desktop:** approximately 1280–1440 CSS px wide and wider.

Do not merely scale down a desktop dashboard. Define intentional responsive behaviour:
- ASHA worker experience is mobile-first and touch-first; its core voice action must remain immediately visible and easy to reach.
- Supervisor navigation may use a collapsible sidebar on smaller screens and a persistent sidebar on desktop.
- Dense data tables must transform into readable cards, lists or appropriately scrollable regions on smaller viewports.
- Filters, dialogs, charts, forms, alerts and navigation must reflow without clipping or accidental horizontal page overflow.
- Keep controls comfortably tappable (target at least 44 × 44 CSS px where practical), text legible and contrast accessible.
- Respect safe areas and mobile browser viewport behaviour.
- Do not hide critical danger alerts or primary voice controls at any breakpoint.

Create separate Stitch frames/variants for the important breakpoints instead of assuming one generated frame is responsive by default.

## 10A.4 Prototype the core user journeys in Stitch

Use Stitch's prototype/flow capability to connect the screens and inspect the interaction sequence for at least:

**ASHA visit journey:**
`Sign in → Select language → Choose beneficiary → Start voice session → Live capture/transcript → Structured draft → Read-back → Voice correction → Re-read → Confirm → Saved visit → Follow-up`

**Danger-sign journey:**
`Active voice session → Danger-sign event → Immediate prominent alert/referral instruction → Alert retained on visit → Supervisor alert queue`

**Supervisor journey:**
`Command center → Open danger alert → Review permitted details → Acknowledge/update referral status → Audit trail`

The prototype must represent key states and navigation. Do not treat prototype click-through as proof that production API, audio, database or authentication behaviour works.

## 10A.5 Create and preserve the design system

Use Stitch to establish a consistent design system and export or author its agent-friendly `DESIGN.md` where supported. Keep it in the repository at:

`docs/DESIGN.md`

It should document:
- Brand direction and visual principles.
- Colour tokens and semantic status colours.
- Typography scale and language/font fallback choices.
- Spacing, sizing, grid and responsive breakpoints.
- Buttons, inputs, cards, tables, navigation, dialogs and alert patterns.
- Voice-session states and their visual treatment.
- Danger-alert treatment and accessibility requirements.
- Component states: default, hover, focus, active, disabled, loading and error.
- Accessibility and contrast decisions.

Use design tokens consistently in the Next.js implementation. Do not copy arbitrary CSS values from unrelated screens or create one-off styles without a reason.

## 10A.6 Implement the Stitch design as a real application

After the Stitch design direction and core responsive layouts are established:
- Implement the screens using the existing project's Next.js, TypeScript and styling conventions.
- Build reusable components and shared layouts from the design system.
- Connect routes, controls, forms, filters, dialogs and actions to real app state and backend operations.
- Implement actual loading, empty, success, disabled, error, offline and permission-denied states.
- Use synthetic data only in design examples and UI fixtures.
- Do not leave decorative buttons, fake charts, dead links or nonfunctional voice controls.
- Do not expose real beneficiary information, credentials or secrets in Stitch prompts, uploaded references, shared links or screenshots.
- Ensure web UI communicates clearly when microphone/browser permissions or network connectivity prevent an action.

Stitch-generated HTML/CSS/React, if exported, may be used as a reference or selectively adapted. Reconcile it with the existing app architecture, accessibility, TypeScript types, shared components and security model. Do not blindly overwrite existing source files with generated code.

## 10A.7 Stitch deliverables and acceptance

Commit/document these artifacts:
- Stitch project name and share URL (if sharing is enabled and safe).
- `docs/DESIGN.md` — the design system.
- `docs/STITCH_DESIGN_HANDOFF.md` — screen inventory, prototype flows, selected design direction, responsive decisions, component mapping and any deviations from Stitch output.
- A responsive screen/route matrix showing small mobile, large mobile, tablet and desktop coverage.
- A mapping from each designed screen to its implemented Next.js route/component.

The UI milestone is not complete until the key ASHA and supervisor screens have Stitch designs, the core flows have been prototyped, responsive layouts have been considered, and the implementation follows the design system. Any inability to access Stitch must be reported explicitly as a blocker; never fabricate a Stitch project, export, URL or completed design review.

# 11. REPORTS, ANALYTICS AND EXPORTS

Build reports only from persisted data and authorized query scopes.

Possible useful views:
- Visits by date, type, ASHA worker and PHC.
- Upcoming and overdue follow-ups.
- Immunisation due/completed status where data exists.
- Active, acknowledged and referred danger alerts.
- Beneficiary coverage and visit completion counts.

Requirements:
- Clearly show filter scope and date range.
- Avoid presenting missing data as zero unless that meaning is correct.
- Use server-side scoped queries for large datasets.
- CSV/PDF exports must honor exactly the same authorization scope as the screen.
- Do not export secrets, raw audio or unnecessary sensitive information.
- Label all demo data as synthetic.

---

# 12. SUB-AGENT ORCHESTRATION

You may spawn as many specialist sub-agents as useful. Delegate bounded tasks and keep one authoritative implementation per shared module.

Suggested workstreams:

### Sub-agent 3A — Supabase Schema, Migrations & RLS
Owns database design, SQL migrations, indexes, RLS policies, policy tests and synthetic seed data.

### Sub-agent 3B — ASHA Worker Web Portal & Voice Client
Owns worker routes, browser microphone/audio services, WebSocket adapter, transcript/visit UI, read-back, correction and confirmation experience. Must consume Agent 1's contracts and must not implement voice/clinical business logic itself.

### Sub-agent 3C — Beneficiary, Visit & Follow-up Workflows
Owns beneficiary directory/profile, visit history, immunisation tracking, follow-up queues, persistence hooks and offline draft integration.

### Sub-agent 3D — PHC Supervisor Command Center
Owns dashboard, realtime danger alerts, ASHA worker oversight, referral tracking, analytics and exports.

### Sub-agent 3E — Integration, Security & QA

### Sub-agent 3F — Stitch Design System & Responsive Prototyping
Owns the Google Stitch project, full screen inventory, small-mobile/large-mobile/tablet/desktop variants, core clickable prototypes, exported `docs/DESIGN.md` and `docs/STITCH_DESIGN_HANDOFF.md`. This agent owns design artifacts and design review only; it must not independently rewrite application screens, voice logic or database/business logic. Coordinate the approved designs with Sub-agents 3B and 3D before implementation.
Owns end-to-end contract conformance, auth/RLS test cases, duplicate-submit tests, offline-sync tests, accessibility review and manual test documentation.

For every sub-agent assignment, state:
1. Objective and exact scope.
2. Allowed files/modules.
3. Explicitly excluded files/modules.
4. Dependencies and inputs.
5. Deliverables.
6. Acceptance criteria.
7. Test/report requirements.

Require each sub-agent to report changed files, dependencies, commands/tests run, results, assumptions, risks and unresolved issues. Review all code and migration changes before integration. Avoid simultaneous edits to shared central files.

---

# 13. TESTING AND VALIDATION

Test the web and database implementation without browser automation or browser-based verification. Leave browser validation to the project owner for manual testing.

Use appropriate automated tests that do not require browser driving:
- TypeScript type checking and linting.
- Unit tests for data mapping, state handling and offline sync utilities.
- API/route handler tests.
- Supabase migration application tests where a local Supabase/PostgreSQL environment is available.
- RLS authorization tests for both permitted and forbidden cases.
- Contract/schema validation tests against Agent 1's real published schemas.
- Idempotency and duplicate submission tests.
- IndexedDB logic tests using appropriate non-browser unit-test abstractions where feasible.
- Build validation.

Do not claim that microphone permissions, live Gnani audio, browser playback, browser reconnect or UI accessibility have been manually verified unless they actually have been. Provide a concise manual test checklist for the owner to execute.

### Critical acceptance scenarios

1. ASHA login and language selection.
2. Start a voice session and stream microphone audio to the real Agent 1 backend.
3. Display partial/final transcription and audio playback.
4. Interrupt assistant speech and process the correction.
5. Render the structured visit record.
6. Correct a field by voice and re-read the updated record.
7. Confirm and persist the visit only after explicit confirmation.
8. Show and persist a danger-sign alert immediately when emitted by the backend.
9. Supervisor sees the alert within the configured realtime path and can update its authorized tracking status.
10. ASHA sees assigned beneficiaries, visit history and follow-ups.
11. Offline draft survives reload/reopen and syncs without duplicate records when online.
12. Cross-client consistency: a saved record from Android is visible on the web, and vice versa, after successful synchronization and authorization.
13. Unauthorized users cannot read or mutate out-of-scope PHC/ASHA data.
14. Exports contain only authorized, persisted synthetic data.

---

# 14. GIT AND DELIVERY CADENCE

This is an independent Agent 3 repository. Own its Git workflow separately from Agent 1 and Agent 2.

- Initialize Git only if no repository exists; preserve existing history if it does.
- Make a small initial commit after repository/environment hygiene and a working project baseline are established.
- Commit after each coherent group of edits, not after every individual file and not only at the very end.
- Push each completed milestone/batch when a valid remote is configured and the branch is safe to push.
- Suggested sequence:
  1. `chore: bootstrap web app and secure environment`
  2. `feat: add supabase schema auth and rls`
  3. `feat: implement asha worker web voice workflow`
  4. `feat: add offline drafts and idempotent sync`
  5. `feat: add phc supervisor alerts and follow-ups`
  6. `feat: add reports exports and audit views`
  7. `test: add integration security and parity coverage`
- Before each commit: inspect `git diff`, `git status`, staged file list and secret scan results.
- Never commit `.env.local`, Supabase service-role credentials, API keys, real PII, raw health audio or real health records.
- Never force-push or rewrite shared history.
- If push fails, preserve the commit, report the exact blocker and do not claim the remote was updated.

---

# 15. REQUIRED DELIVERABLES

At completion, provide:

## Application
- Complete Next.js + TypeScript web application.
- Full ASHA worker portal with feature parity to Android.
- PHC supervisor command center and required admin capabilities.
- Shared voice backend integration using Agent 1's real contracts.
- Responsive and accessible worker and supervisor workflows.

## Database and security
- Versioned Supabase migrations.
- RLS policies and authorization model.
- Synthetic seed data.
- Authentication implementation.
- Realtime alert handling.
- Offline draft and idempotent synchronization implementation.

## Integration and documentation
- `.env.example` with safe placeholders.
- `.gitignore` protecting secrets and generated files.
- `docs/ARCHITECTURE.md`.
- `docs/DATABASE_SCHEMA.md`.
- `docs/RLS_AND_AUTH.md`.
- `docs/AGENT1_INTEGRATION.md`.
- `docs/AGENT2_WEB_PARITY.md`.
- `docs/MANUAL_TEST_CHECKLIST.md`.
- `docs/DESIGN.md` and `docs/STITCH_DESIGN_HANDOFF.md`, plus the Stitch project reference and responsive screen matrix.
- `docs/KNOWN_LIMITATIONS.md`.
- A completed Android ↔ Web feature parity matrix.
- Migration and synthetic demo-data setup instructions.

## Final report
Report:
- What is implemented and working.
- Which Agent 1 contracts/endpoints were integrated and their versions.
- Whether real voice-provider integration was tested or only mocked.
- Database migrations applied and RLS tests performed.
- Feature-parity checklist status.
- Automated test/build results.
- Manual testing still required.
- Git commits created and whether each was pushed.
- Known limitations and exact blockers.

---

# 16. IMMEDIATE EXECUTION ORDER

Start now. Do not respond with only a plan.

1. Inspect this independent repository and report its actual state.
2. Read any available project specs and integration contracts.
3. Set up `.gitignore`, `.env.example` and local `.env.local` safely.
4. Initialize Git only if needed; preserve existing history; commit the clean baseline and push only if a remote is already configured.
5. Spawn specialist agents for database/RLS, worker portal, supervisor portal and integration/security review. Assign disjoint scopes.
6. Establish the schema and API adapter boundaries from the actual shared contracts. If Agent 1's contracts are not yet available, keep adapters provisional and document blockers.
7. Start the Google Stitch design workflow: create the ASHA and supervisor screen inventory, mobile/tablet/desktop variants, core prototypes and `docs/DESIGN.md`; delegate this to Sub-agent 3F.
8. Implement the complete ASHA worker web workflow first or in parallel with the supervisor shell, following the approved Stitch design; do not deliver a supervisor-only dashboard.
9. Implement Supabase persistence, RLS, synthetic seeds, offline drafts and idempotent sync.
10. Add supervisor realtime alerts, referral tracking, reports and exports.
11. Run automated checks, inspect Git changes, commit and push each coherent milestone.
12. Produce the feature-parity matrix, Stitch design handoff and manual test checklist.

**Definition of success:** the browser application is a complete ASHA-worker client and a PHC-supervisor platform on top of one shared, secure healthcare system. The ASHA workflow must work end-to-end in the browser using the real shared voice backend, and the web client must not fork clinical or voice business logic. A visually complete dashboard with mocked controls or placeholder voice events is not completion.
