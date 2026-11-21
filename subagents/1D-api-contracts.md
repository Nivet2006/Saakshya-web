# Sub-agent 1D — API, WebSocket Events and Cross-Laptop Contracts

## Mission
Define stable, versioned technology-independent contracts so Agent 2 (Android) and Agent 3 (Web/Database) can integrate with Agent 1's voice/healthcare backend without guessing or duplicating business logic.

## Start condition
Start by reviewing existing repository structure and discussing event names/data shapes with Agent 1. Do not invent payload fields independently of the backend's agreed model. Publish a draft early for both other agents to review; finalise against the implemented backend.

## Required deliverables
- `shared-contracts/openapi.json`
- `shared-contracts/visit.schema.json`
- `shared-contracts/voice-events.schema.json`
- `shared-contracts/danger-alert.schema.json`
- `docs/INTEGRATION_HANDOFF.md`

## Contract coverage
Document:
- session creation/termination;
- WebSocket authentication/session binding as selected by Agent 1;
- audio input format, framing, sample rate, channels and encoding;
- partial/final transcript;
- assistant text response;
- TTS audio chunks/completion;
- barge-in/cancel and resume events;
- visit draft/field update;
- clarification request;
- read-back and correction;
- explicit confirmation;
- persistence acknowledgement/failure;
- high-priority danger-sign alert and acknowledgement;
- follow-up actions;
- structured errors and retryability.

## Design constraints
- Do not expose Gnani-specific payloads to clients.
- Use stable, documented event names and enum values.
- Include versioning and correlation/session IDs where appropriate.
- Use ISO-8601 timestamps/dates and define timezone semantics.
- Include synthetic examples and ensure they validate against the schemas.
- Make danger alerts independently consumable and high priority.
- Distinguish an unconfirmed draft from a confirmed record and a durably persisted record.
- Keep contracts aligned with actual backend implementation; no imaginary endpoints/events.

## Ownership boundaries
- Agent 1 owns backend and technology-independent contracts.
- Agent 2 owns Android implementation.
- Agent 3 owns Next.js, Supabase schema/migrations/auth/RLS and persistence implementation.
- Do not create Supabase migrations or a second database schema. Coordinate storage mapping with Agent 3.

## Out of scope
- No Android UI implementation.
- No Next.js UI implementation.
- No Supabase migration/schema ownership.
- No real PII or real health data.

## Handoff report
List contract files, versions, breaking/non-breaking decisions, payload examples, validation results, dependencies and integration actions required from Agents 2 and 3.
