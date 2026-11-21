# Cross-Laptop Integration Contracts

This document sets the interface expectations for all three development environments. Agent 1 owns the technology-independent contract definitions and publishes the actual versioned files under `shared-contracts/`. Agent 3 owns the Supabase implementation and Agent 2 owns the Android client.

## Ownership

### Agent 1 — backend and contracts

Publishes:

- `shared-contracts/openapi.json`
- `shared-contracts/visit.schema.json`
- `shared-contracts/voice-events.schema.json`
- `shared-contracts/danger-alert.schema.json`
- `docs/INTEGRATION_HANDOFF.md`

Defines API and WebSocket behaviour, event names, payload formats, validation and confirmation semantics.

### Agent 2 — Android

Consumes the documented HTTP/WebSocket APIs and event schemas. Owns Android audio capture/playback, lifecycle, permissions, UI, local drafts and offline experience. It must not reimplement the danger-sign rules or healthcare extraction in the client.

### Agent 3 — Web and database

Consumes the documented API/data contracts. Owns Next.js dashboard, Supabase tables, migrations, RLS, authentication, durable persistence and reports. Agent 1 provides data requirements but must not create competing Supabase migrations.

## Contract design requirements

### Common conventions

- Use JSON over documented HTTP/WebSocket interfaces unless a verified provider/client constraint requires otherwise.
- Use stable event names and versioned schemas.
- Include a request/session/correlation identifier where needed.
- Use ISO-8601 dates and timestamps with an explicit timezone policy.
- Use stable enum values; do not expose provider-specific payloads directly to clients.
- Represent unprovided/unconfirmed fields as null or explicit unknown status, not guessed values.
- Define error codes, retryability and cancellation semantics.
- Include synthetic examples in schemas/docs.

### Voice session protocol

The final protocol must document, at minimum:

- session creation and termination;
- audio input format (codec/container, sample rate, channel count, frame/chunk rules and encoding);
- client audio chunk messages;
- partial transcript event;
- final transcript event;
- assistant text response event;
- TTS audio chunk and completion events;
- barge-in/interruption event;
- cancellation of current TTS generation/playback;
- session state and recoverable error events.

Do not fill protocol values by assumption. Verify provider requirements and select a single client-facing format that the backend can reliably transcode to/from provider formats.

### Visit lifecycle

The backend owns conversational extraction and the draft until the worker explicitly confirms it. The contract must distinguish at least:

- draft created/updated;
- field requires clarification;
- read-back started/completed;
- correction received/applied;
- worker confirmed;
- persistence accepted/rejected;
- visit committed.

The exact persistence call/acknowledgement sequence must be agreed with Agent 3. Never represent a local draft as durably saved until the persistence layer confirms success.

### Danger alerts

Danger alerts are high-priority events. They must be emitted independently of visit completion and include, where available:

- alert identifier;
- synthetic beneficiary identifier;
- session/visit draft identifier;
- matched canonical danger-sign identifier;
- supporting phrase/evidence (avoid unnecessarily retaining raw audio/transcript);
- source guideline reference identifier;
- detection timestamp;
- alert status and acknowledgement state;
- escalation message language;
- `danger_sign_flagged: true`.

Clients must render urgent alerts promptly. Backend detection remains authoritative; clients must not suppress or downgrade alerts.

## Contract change process

1. Agent 1 updates the relevant OpenAPI/JSON Schema files.
2. Agent 1 documents the change and compatibility impact in `docs/INTEGRATION_HANDOFF.md`.
3. Agent 1 notifies both other agents of changed fields/events and any migration/client action required.
4. Agent 2 and Agent 3 update their consumers/implementations within their own workspaces.
5. Validate example payloads against the schemas before calling the integration complete.

Do not silently rename fields or change enum values after another agent has integrated them.
