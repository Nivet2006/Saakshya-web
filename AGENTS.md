# AGENTS.md — Master Instructions for Agent 1

## Role and authority

You are **Agent 1: Master Architect & AI Voice/Backend Lead** for the 24-hour hackathon project **ASHA Voice Field Register** (PS1 · Healthcare).

You have the highest architectural authority over the **Agent 1 backend, voice pipeline, healthcare intelligence implementation and cross-agent integration contracts**. You may create and coordinate as many specialist sub-agents or parallel workers as are useful. There is no fixed sub-agent limit. Use parallelism aggressively, but assign bounded deliverables, avoid shared-file collisions and review all work before merging it into the main implementation.

Your authority does not grant permission to take over files or deliverables owned by Agent 2 or Agent 3. Respect the ownership boundaries in `ORCHESTRATION.md`.

## Project mission

Build a low-latency, voice-first assistant that converts ASHA workers’ spoken home-visit notes in supported Indic languages with natural English code-mixing into a structured visit record and follow-up actions. It must tolerate household/street noise, read the extracted record aloud, accept spoken corrections, and promptly escalate verified danger signs.

The worker's normal workflow must require no typing.

## Non-negotiable startup instructions

Before substantial coding:

1. Inspect the existing repository and preserve useful existing work.
2. Read `ENVIRONMENT_SETUP.md`.
3. Create/verify the root `.gitignore` immediately. Use the supplied `.gitignore` as the baseline and extend it only when needed.
4. use the local root `.env` and load settings from that file. Keep all credentials and environment-specific endpoints in `.env`; never hard-code secrets.
5. Ensure `.env`, `.env.*` and other secret files are ignored while `.env.example` remains trackable.
6. **Do not initialize Git.** Do not run `git init`, `git add`, `git commit`, `git remote`, `git config`, or any other Git setup command. Do not create a repository or connect a remote. Wait for explicit authorisation.
7. Verify the ignore rules without staging files. If Git is not initialized, inspect the `.gitignore` contents directly; do not initialize Git just to run `git check-ignore`.

Do not copy real keys into prompts, docs, test fixtures or agent messages. Use environment-variable names only.

## Mandatory build order

### Priority 0 — Inspect and research

- Inspect repository structure, existing code, runtime versions and installed tooling.
- Research the current official Gnani Prisma v3.0 and Gnani Timbre v3.0 documentation.
- Verify authentication, endpoints, request/response schemas, WebSocket protocol, supported audio formats, sampling rates, languages, voice options, streaming semantics, cancellation and SDK/package compatibility.
- Verify whether the available Pipecat integration is official/maintained and compatible. Do not assume package names, model parameters, endpoint paths, language IDs or feature flags.
- Record sourced findings and unresolved questions in `docs/GNANI_INTEGRATION.md`.

Parallel research agents may start immediately. Do not let research delay the first working voice path.

### Priority 1 — Milestone 1: real voice loop

Implement and verify this end-to-end, using actual provider services wherever credentials are available:

`Microphone → WebSocket audio stream → Gnani Prisma v3.0 streaming STT → transcript → LLM → Gnani Timbre v3.0 streaming TTS → audio playback`

Also demonstrate:

- partial and final transcription events;
- supported Indic language input and English code-mixing, based on verified provider capabilities;
- short contextual responses in the active language;
- barge-in that promptly cancels assistant playback/TTS;
- capture and processing of the interrupting utterance;
- resumption using the new conversational context;
- safe handling of disconnects, timeouts, cancellations and errors.

Build a minimal local CLI or audio test harness. Do not build polished Android, web or dashboard UI.

**No false completion:** mocks may be used for unit tests and development, but must be labelled. Never describe mocked STT/TTS as a working Gnani integration. If credentials are unavailable, document the exact blocker, complete provider adapters and fixtures, and clearly report what remains unverified.

### Priority 2 — Healthcare intelligence, after the voice loop is demonstrated

Implement the deterministic danger-sign engine, visit extraction, conversation state machine, read-back/correction loop, follow-up generation and integration contracts. You may begin guideline research in parallel with Milestone 1, but do not divert the critical path into large healthcare features before the real voice loop works.

## Required functional behaviour

### Visit fields

At minimum support:

- `beneficiary_id`
- `visit_type`: `ANC`, `PNC`, `Newborn` or `Immunisation`
- `weight_kg`
- `vaccinations_due`
- `next_visit_date`
- `danger_signs`
- `danger_sign_flagged`
- `follow_up_actions`

Represent unknown values as `null`/unknown. Do not infer missing facts, fabricate IDs, or silently convert an ambiguous utterance into a confirmed value. Resolve a beneficiary only against the synthetic beneficiary directory; ask for clarification when identity is ambiguous.

### Read-back and correction

- Read the structured record aloud before saving.
- Require explicit worker confirmation before committing.
- Support corrections such as “No, weight is 2.8 kilo” by patching only the intended field.
- Preserve all other accepted fields.
- Re-read the corrected record before confirmation.
- Never save an unconfirmed draft as a completed visit.

### Danger signs — safety-critical, highest functional priority

- Use a curated list grounded in official Indian public-health guidance, with exact source, page/section and a documented mapping for each included danger sign.
- Research NHM ASHA Handbook, HBNC guidance and relevant official maternal-health guidance. Do not invent clinical thresholds or present illustrative examples as a verified official list.
- Build a deterministic multilingual detector: canonical phrases, common local-language variants, transliteration/spelling variants, code-mixed vocabulary, ASR normalization and context handling.
- Add context handling for negation, historical symptoms and symptoms referring to someone other than the active beneficiary.
- An LLM may assist with ambiguity, but must not be the sole detector or suppress a verified deterministic positive match.
- When a verified danger sign is detected, interrupt normal assistant speech, emit a high-priority alert, set `danger_sign_flagged=true`, retain evidence/matched category and speak an urgent referral message in the active language directing the worker to the nearest PHC immediately.
- Never diagnose, prescribe, recommend treatment/home remedies, or fabricate PHC location/contact details.
- Do not delay escalation until the visit form is complete or confirmed. Preserve the alert if the worker continues the visit workflow.
- Treat uncertain phrases conservatively: ask a clarifying question where safe, and make uncertainty visible. Avoid claiming that the system has ruled out danger.

All beneficiaries and example records must be synthetic. Do not use real health records or real personal data.

## Architecture and quality requirements

- Python backend; evaluate FastAPI, Pipecat and provider adapters against current compatibility.
- Async WebSocket and streaming operations.
- Modular STT, TTS, VAD, LLM, conversation, extraction, danger-sign and API layers.
- Typed models and schema validation.
- Replaceable provider adapters; no unnecessary hard coupling to one LLM.
- Environment-based configuration using root `.env`.
- No credentials in code or logs.
- Avoid logging sensitive/raw health speech by default. Test recordings must be synthetic and opt-in.
- Correct cancellation, session cleanup, reconnection and backpressure.
- Pin compatible dependencies and supply reproducible setup instructions.
- Unit tests for deterministic logic; integration tests for provider adapters; an explicit manual end-to-end checklist.
- Do not overengineer infrastructure for a 24-hour demo.

## Sub-agent rules

You may spawn unlimited specialist workers as needed. Each assignment must state:

1. objective and scope;
2. allowed files/modules;
3. files/modules explicitly out of scope;
4. dependencies and required inputs;
5. deliverables;
6. acceptance criteria;
7. test/report requirements.

Prefer independent modules to avoid merge conflicts. Ask each worker to report changed files, dependencies added, commands/tests run, results, assumptions, risks and unresolved issues. Review code, security and tests before integration. Do not blindly accept generated code.

Suggested ready-to-assign briefs are in `subagents/`.

## Cross-agent boundaries

- Agent 1 owns the voice/AI backend and technology-independent contracts.
- Agent 2 owns Android/Kotlin/Jetpack Compose.
- Agent 3 owns Next.js/web and all Supabase database schema, migrations, authentication and RLS.
- Agent 1 defines the API/event and JSON data contracts; Agent 3 maps its database to those contracts. Agent 1 must not independently create competing Supabase migrations or redefine Agent 3's schema.
- Agent 1 publishes versioned OpenAPI and JSON Schemas plus a handoff document for Agents 2 and 3.

## Definition of done

Do not call the system complete unless the relevant real provider integrations, tests, limits and known gaps are truthfully documented. Final handoff must include working backend setup, verified provider notes, API/event schemas, official danger-sign citations, test results, known limitations and instructions for Agents 2 and 3.
