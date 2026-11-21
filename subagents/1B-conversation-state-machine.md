# Sub-agent 1B — Conversation State Machine, Read-Back and Corrections

## Mission
Design and implement the backend conversation workflow for collecting visit notes, asking clarifying questions, reading the structured record aloud, applying voice corrections and requiring explicit confirmation before commit.

## Start condition
Design the state model and event interface in parallel with Milestone 1. Implement the healthcare workflow after the voice loop is demonstrated, unless Agent 1 explicitly reprioritises.

## Required states
At minimum support:

- `IDLE`
- `GATHERING_NOTES`
- `EXTRACTING_FIELDS`
- `CLARIFICATION_REQUIRED`
- `READ_BACK_CONFIRMATION`
- `CORRECTION_PATCH`
- `READY_TO_CONFIRM`
- `COMMITTED`

A high-priority `DANGER_ESCALATION` interrupt path must be reachable from any relevant active state. Do not make danger escalation wait for the visit state machine to reach a convenient point.

## Behaviour requirements
- Preserve per-session context and active synthetic beneficiary context.
- Ask only for required missing/ambiguous information; do not repeatedly ask for already confirmed fields.
- Read all required fields aloud before save.
- Accept corrections such as “No, weight is 2.8 kilo” and patch only the intended field.
- Retain other accepted values when one field is corrected.
- Re-read affected/corrected information and obtain explicit confirmation.
- Never commit an unconfirmed draft.
- Distinguish `draft`, `confirmed` and `persisted/committed`; do not claim durable save without Agent 3/persistence acknowledgement.
- Preserve danger alerts even if the user interrupts or abandons the form.
- Handle barge-in/cancellation without replaying stale assistant text or audio.

## Interfaces
Coordinate state transitions and events with Agent 1 and Agent 1D. Keep business state independent from Pipecat/provider-specific implementation details.

## Out of scope
- No Android UI.
- No web dashboard.
- No Supabase tables/migrations/RLS.
- No real personal or health data.

## Deliverables
- state diagram or state-transition table;
- typed state machine implementation;
- event/action definitions;
- tests for happy path, missing fields, corrections, repeated corrections, interruption, danger escalation from each active state and failed persistence acknowledgement;
- concise integration notes.

## Handoff report
List changed files, transitions implemented, tests and results, assumptions, unresolved edge cases and event-contract dependencies.
