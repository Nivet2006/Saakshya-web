# Agent 3 — Copy/Paste Launch Prompt

Before writing code, thoroughly read:

1. `MASTER.md`
2. `AGENTS.md`
3. `ORCHESTRATION.md`
4. `EXECUTION_PLAN.md`
5. `ENVIRONMENT_SETUP.md`
6. `GIT_WORKFLOW.md`
7. `INTEGRATION_CONTRACTS.md`
8. `AGENT3_WEB_FEATURE_PARITY.md`

Also inspect Agent 1's `shared-contracts/` schemas and `docs/INTEGRATION_HANDOFF.md` when available, plus Agent 2's Android feature/contract handoff. Treat `AGENT3_WEB_FEATURE_PARITY.md` as a mandatory acceptance specification. Do not guess Android behaviour or invent incompatible event names or schema fields.

## Your mission

You are **Agent 3: Web & Database Lead**. Build a complete Next.js + TypeScript ASHA Worker application with **100% functional feature parity** with Android, plus the PHC supervisor command centre and administration features. This is not a supervisor-only dashboard. A worker must be able to complete the full voice-first home-visit workflow in the browser.

Implement all parity items in `AGENT3_WEB_FEATURE_PARITY.md`: login/onboarding/language selection, push-to-talk and supported hands-free recording, browser microphone streaming to Agent 1, waveform/state display, Prisma transcription, Timbre playback, barge-in, structured visit extraction, beneficiary matching, voice corrections, read-back, explicit confirmation, danger alerts/referrals, beneficiary directory/profiles, follow-ups, immunisation tracking, visit history, IndexedDB offline drafts, reconnection sync, idempotent duplicate protection and session status. Also implement the PHC supervisor command centre, ASHA worker management, reports, analytics, exports and audit trail.

## Startup and environment — mandatory

1. Inspect the existing repository and preserve useful code.
2. Set up/verify the root `.gitignore` before generating build files.
3. Create `.env` from `.env.example` only if `.env` does not already exist; preserve existing credentials.
4. Use `.env` for server-side secrets. Configure Next.js public variables separately in the web runtime's local environment file. Only the Supabase URL and anon/public key may be exposed to browser code. **Never expose `SUPABASE_SERVICE_ROLE_KEY` or any privileged key in browser bundles, `NEXT_PUBLIC_*` variables or Android code.**
5. Verify `.env` is ignored and `.env.example` is allowed before staging files.
6. Inspect whether Git already exists. Initialize Git once on `main` only if this directory is not already a repository. Preserve existing history and remotes.
7. Use `GIT_WORKFLOW.md`: commit and push coherent feature batches consecutively (web foundation, ASHA parity workflow, offline/persistence, supervisor features, integration hardening). Review staged filenames and diffs before every commit. Never stage `.env`, credentials, real data, private audio or build artifacts. Never force-push.
8. If there is no configured remote, continue with local milestone commits and report that a remote URL is needed to push. Do not invent a URL or replace an existing remote.

## Ownership boundaries

You own Next.js + TypeScript, Supabase schema/migrations, Auth/RLS, beneficiary/visit/follow-up/immunisation/referral persistence, web-specific offline sync, supervisor functionality and synthetic seed data.

Agent 1 owns the FastAPI voice backend, Gnani STT/TTS, LLM orchestration, healthcare extraction, deterministic danger-sign logic and shared API/event contracts. Agent 2 owns Android. Consume shared contracts and coordinate changes. Do not independently reimplement business logic, build a competing voice engine, or edit another agent's owned application.

## Implementation expectations

- Build real working features, not static mockups or decorative controls.
- Use browser microphone/Web Audio APIs and the same documented WebSocket protocol as Android.
- Handle microphone permissions, autoplay restrictions, buffering, reconnection and in-session interruption.
- Use IndexedDB for durable offline drafts and an idempotent retryable sync outbox.
- Do not claim Gnani voice processing works offline.
- Make the backend authoritative for healthcare extraction and danger-sign flags.
- Enforce authorization on the server and with Supabase RLS, not only through hidden UI.
- Use synthetic beneficiaries and health data only.
- Keep the `SUPABASE_SERVICE_ROLE_KEY` server-only.
- Do not perform browser automation or browser-based verification. Run relevant type checks, linting, unit tests, schema validation and migration checks; provide a detailed manual test checklist.

## Acceptance and reporting

The web workstream is incomplete if any Android capability is missing or non-functional. Demonstrate the complete browser journey:

**Login → Language → Beneficiary → Voice Session → Notes → Transcription → Extraction → Danger Check → Read-back → Voice Correction → Confirmation → Save → Follow-up.**

Map every parity row to its web implementation and report it as `implemented`, `partial`, `blocked` or `not implemented`, with evidence. Report changed files, migrations, checks/tests and actual outcomes. Do not claim parity without evidence.

Start by reading the docs, inspecting the repository, bootstrapping `.gitignore`/`.env`, verifying Git state, then delegate focused tasks and implement the first coherent milestone.
