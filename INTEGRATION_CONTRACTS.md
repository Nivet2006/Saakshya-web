# Cross-Laptop Integration Contracts

This document sets the interface expectations for all three development environments. Agent 1 owns the technology-independent API/event contracts. Agent 2 owns the Android client. Agent 3 owns the complete Web client, Supabase schema/migrations/auth/RLS and durable persistence.

## Ownership

### Agent 1 — voice/backend and shared contracts

Publishes:

- `shared-contracts/openapi.json`
- `shared-contracts/visit.schema.json`
- `shared-contracts/voice-events.schema.json`
- `shared-contracts/danger-alert.schema.json`
- `docs/INTEGRATION_HANDOFF.md`

Defines provider-independent HTTP/WebSocket behaviour, event names, payload formats, validation and confirmation semantics. Owns voice streaming, STT/TTS, LLM orchestration, extraction and deterministic danger-sign rules.

### Agent 2 — Android

Owns Kotlin/Jetpack Compose, ASHA Android experience, Android audio capture/playback, lifecycle and permissions, Android local drafts and offline experience. Consumes the same documented backend APIs/events as Web. Does not independently reimplement healthcare extraction or danger-sign logic.

### Agent 3 — Web and database

Owns a **full-featured ASHA Worker web application with 100% functional parity with Android**, in addition to the PHC supervisor command centre. Also owns Next.js/TypeScript, Supabase schema/migrations, Auth, RLS, durable persistence, web offline drafts/sync, reports and analytics.

See `AGENT3_WEB_FEATURE_PARITY.md` for the complete mandatory matrix and acceptance criteria. A supervisor-only dashboard is not an acceptable web deliverable.

## Shared platform invariants

Android and Web use the same:

- FastAPI voice backend and client-facing WebSocket protocol.
- Gnani Prisma v3.0 STT and Gnani Timbre v3.0 TTS services through Agent 1.
- LLM conversation manager and structured extraction logic.
- Deterministic danger-sign engine and escalation semantics.
- Visit field definitions, validation rules and state transitions.
- Supabase PostgreSQL database and persisted visit records.
- Authentication identities and role/PHC authorization model.
- Versioned OpenAPI and JSON event contracts.

No client may fork clinical/business rules. Agent 1's backend is authoritative for transcription-derived extraction and danger-sign decisions. Supabase is authoritative for durable, synchronised records after successful persistence.

## Contract design requirements

### Common conventions

- Use JSON over documented HTTP/WebSocket interfaces unless a verified provider/client constraint requires otherwise.
- Use stable event names and versioned schemas.
- Include request/session/correlation identifiers where needed.
- Use ISO-8601 dates and timestamps with an explicit timezone policy.
- Use stable enum values; never expose provider-specific Gnani payloads directly to clients.
- Represent unprovided/unconfirmed fields as null or an explicit unknown status, not guessed values.
- Define error codes, retryability and cancellation semantics.
- Include synthetic examples in schemas/docs.

### Voice session protocol

Document at minimum:

- session creation and termination;
- audio input format (codec/container, sample rate, channel count, frame/chunk rules and encoding);
- client audio chunk messages;
- partial and final transcript events;
- assistant text response event;
- TTS audio chunk and completion events;
- barge-in/interruption event;
- cancellation of current TTS generation/playback;
- session state and recoverable error events.

Do not assume protocol values. Verify provider requirements and select one client-facing format that the backend can reliably transcode to/from provider formats. Both Android and Web must use the same protocol.

### Visit lifecycle

Backend owns conversational extraction and the visit draft until worker confirmation. The contract must distinguish:

- draft created/updated;
- field requires clarification;
- read-back started/completed;
- correction received/applied;
- worker confirmed;
- persistence accepted/rejected;
- visit committed.

Coordinate the persistence call/acknowledgement with Agent 3. Neither client may represent an in-memory/offline draft as durably saved until Supabase confirms the write.

### Danger alerts

Danger alerts are high-priority, independently emitted events and must not depend on the visit being complete or saved. Include, where available:

- alert identifier;
- synthetic beneficiary identifier;
- session/visit draft identifier;
- matched canonical danger-sign identifier;
- minimum necessary supporting phrase/evidence (avoid retaining raw audio unnecessarily);
- source guideline reference identifier;
- detection timestamp;
- alert status and acknowledgement state;
- escalation message language;
- `danger_sign_flagged: true`.

Both clients must render urgent alerts promptly. Neither client may suppress or downgrade backend-confirmed alerts.

### Offline and cross-client sync

- Android and Web may use platform-specific local storage mechanisms.
- Web must use IndexedDB for persistent drafts; Android uses its own appropriate local persistence.
- Local drafts must have stable IDs and idempotency keys to prevent duplicate commits.
- Sync must distinguish local-only, queued, syncing, synced and failed states.
- A visit started on one client must become available on the other after a successful server persistence/sync, subject to authorization.
- Define conflict handling for edits made on more than one client.
- Offline mode does not imply that Gnani voice processing is available offline.

## Contract change process

1. Agent 1 updates the relevant OpenAPI/JSON Schema files.
2. Agent 1 documents compatibility impact in `docs/INTEGRATION_HANDOFF.md`.
3. Agent 1 notifies Agent 2 and Agent 3 of changed fields/events and required actions.
4. Agent 2 and Agent 3 update their own consumers/implementations.
5. Validate example payloads against schemas before declaring integration complete.

Do not silently rename fields, change enum values or change save semantics after another agent has integrated them.
