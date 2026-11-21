# MASTER.md — Start Here

You are starting Agent 1's development environment for **ASHA Voice Field Register** (PS1 · Healthcare).

## Read before coding

Read these documents completely and in this order:

1. `MASTER.md` — startup entry point.
2. `AGENTS.md` — authoritative Agent 1 project specification.
3. `ORCHESTRATION.md` — three-agent hierarchy, unlimited specialist delegation and ownership boundaries.
4. `EXECUTION_PLAN.md` — mandatory implementation order and Milestone 1 gate.
5. `ENVIRONMENT_SETUP.md` — `.env`, `.gitignore` and Git bootstrap.
6. `GIT_WORKFLOW.md` — safe commit and push cadence.
7. `INTEGRATION_CONTRACTS.md` — shared contracts for Android and Web.
8. All relevant briefs in `subagents/` before delegating those tasks.

Agent 3 has a separate mandatory specification: `AGENT3_WEB_FEATURE_PARITY.md`, with its ready-to-paste launch instruction in `AGENT3_LAUNCH_PROMPT.md`. The web app must be a complete ASHA Worker client with full functional parity with Android, in addition to the PHC supervisor experience. It is not a supervisor-only dashboard.

If instructions conflict, follow the stricter safety/ownership rule and treat `AGENTS.md` as the authoritative Agent 1 specification. Agent 3's parity specification is authoritative for Agent 3's web deliverables. Respect all three agents' ownership boundaries.

## First actions — exact order

1. Inspect the existing repository, current branch/history/remotes if Git already exists, project conventions and files. Preserve useful existing work; do not overwrite files blindly.
2. Set up the root `.gitignore` immediately using the supplied file as a baseline.
3. Create root `.env` from `.env.example` **only if `.env` does not already exist**. Preserve existing credentials. Keep all keys and private configuration in `.env`; never hard-code or expose secrets.
4. Verify `.env` is ignored and `.env.example` remains trackable. Do this before staging anything.
5. Initialize Git only if the working directory is not already a Git repository. Preserve existing repository history and remotes; never reinitialize an existing repository.
6. Follow `GIT_WORKFLOW.md`: commit and push coherent milestone batches, not every individual edit. Never force-push or overwrite remote history.
7. Read official Gnani Prisma v3.0 and Timbre v3.0 documentation. Verify APIs, SDKs, authentication, endpoints, streaming, audio formats, languages and cancellation behaviour. Verify Pipecat compatibility rather than assuming a package or parameter exists.
8. Spawn as many focused specialist sub-agents as useful. Follow `ORCHESTRATION.md` and each sub-agent brief. Parallelise research and independent work; avoid conflicting file ownership.
9. Implement and demonstrate the real Milestone 1 voice loop: microphone → WebSocket → Prisma STT → LLM → Timbre TTS → playback, including barge-in and resumption.

Do not build Android screens, the Next.js web application or Supabase migrations in this Agent 1 workstream. Agent 3 owns Web and Supabase; Agent 2 owns Android. Agent 1 owns voice/backend/healthcare intelligence and the shared API/event contracts.

## Definition of success

Prioritize a real, low-latency and interruptible provider-backed voice loop over broad scaffolding or polished UI. Never claim mocks are a real provider integration. Use synthetic health data only. Treat danger-sign detection and urgent PHC referral as safety-critical. Publish stable contracts that enable Agent 2 and Agent 3 to implement the same end-to-end workflow on Android and Web.
