# Execution Plan — 24-Hour Hackathon

## Critical path

**First deliverable: real, interruptible Gnani voice conversation.** Do not start Android screens, Next.js dashboard work or database migrations in this workstream.

## Phase 0 — Bootstrap and verify (immediate)

- [ ] Inspect repository and existing runtime/tooling.
- [ ] Read `ENVIRONMENT_SETUP.md`.
- [ ] Create/verify `.gitignore` before implementation.
- [ ] Create local root `.env` from `.env.example` and configure dotenv loading.
- [ ] Do not initialize Git or run any Git setup command.
- [ ] Spawn parallel documentation/research workers for Gnani Prisma, Gnani Timbre, Pipecat compatibility and audio/VAD/barge-in.
- [ ] Record only verified API details in `docs/GNANI_INTEGRATION.md`.
- [ ] Decide and document the smallest viable architecture.

## Phase 1 — Milestone 1: voice loop (highest priority)

### Build

- [ ] Python backend foundation (FastAPI if suitable).
- [ ] WebSocket session and audio transport.
- [ ] Real Gnani Prisma v3.0 streaming STT adapter.
- [ ] Partial/final transcript events.
- [ ] LLM turn manager with concise responses and session context.
- [ ] Real Gnani Timbre v3.0 TTS adapter.
- [ ] Audio playback in a local CLI/minimal test harness.
- [ ] VAD/endpointing appropriate to the verified audio stack.
- [ ] Barge-in: stop/cancel current TTS and accept the new utterance.
- [ ] Resume conversation using the new input.
- [ ] Error handling, cleanup, timeout and reconnect behaviour.

### Acceptance gate M1

M1 is accepted only after the team can demonstrate, with real provider services and available credentials:

1. Microphone audio streams to Prisma.
2. Actual multilingual transcription is received for the tested supported language(s), including code-mixing where supported.
3. Transcript reaches the LLM and a contextual answer is generated.
4. Timbre speaks the response and audio is heard by the test client.
5. Worker interrupts mid-speech; output stops promptly.
6. The new utterance is transcribed, processed and answered correctly.
7. No stale audio continues after cancellation.

Keep a short recording/log excerpt using synthetic speech only, or document a manual witness checklist. Do not log real beneficiary speech. Mocks do not satisfy this gate. If keys/API access are unavailable, report M1 as blocked/unverified, not passed.

## Phase 2 — Healthcare intelligence (after M1)

Parallelise specialist implementation:

- [ ] 1A: research-cited danger-sign list, multilingual aliases, deterministic detector and tests.
- [ ] 1B: conversational state machine, read-back, correction and confirmation.
- [ ] 1C: typed healthcare field extraction and validation.
- [ ] 1D: versioned OpenAPI, JSON Schemas and integration handoff.
- [ ] Integrate danger escalation as a high-priority interrupt from any relevant conversation state.
- [ ] Ensure a positive danger alert is preserved even if visit confirmation is incomplete.

## Phase 3 — Integration hardening

- [ ] Agent 2 can create/resume a voice session and consume transcript, TTS, visit and alert events using published contracts.
- [ ] Agent 3 can persist confirmed records and render follow-ups/danger alerts using published contracts.
- [ ] Validate schema examples against the actual implementation.
- [ ] Run unit tests for parsers/state machine/detector.
- [ ] Run provider integration tests where real credentials are available.
- [ ] Test danger-sign cases and correction edge cases.
- [ ] Prepare manual end-to-end checklist; no browser automation or browser verification.

## Priority when time is short

1. Real Prisma → LLM → Timbre voice loop.
2. Reliable barge-in and session recovery.
3. Deterministic danger-sign detection and immediate escalation.
4. Correct extraction of required fields and voice correction.
5. Stable contracts for the other two laptops.
6. Documentation polish and optional enhancements.

Do not trade safety-critical behaviour for cosmetic features. Report known limitations honestly.
