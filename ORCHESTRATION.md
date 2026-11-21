# Agent Orchestration and Ownership

## Authority model

Agent 1 is the master architect for the voice/backend workstream and the integration contracts. Agent 1 can spawn as many sub-agents as needed and can make implementation decisions within its ownership. Agents 2 and 3 work in separate environments and own their application/database domains.

```text
                    Agent 1 — Master Architect
                  AI Voice & Backend Lead (this laptop)
                               |
              +----------------+----------------+
              |                |                |
        Voice pipeline    Healthcare logic   Shared contracts
       Prisma / Timbre     Danger / visit     OpenAPI / events
       Pipecat / LLM      state / correction  JSON Schemas
              |
       Internal sub-agents (unlimited as needed)

       Agent 2 — Android                 Agent 3 — Web & Database
       Kotlin / Compose                  Next.js / TypeScript
       ASHA worker UX                    Supervisor dashboard
       Android audio client              Supabase schema / RLS / auth
       Offline drafts                    Persistence / reports
```

## Agent 1 sub-agent policy

There is no hard cap on internal sub-agents. Use the smallest number that gives genuine parallel progress; spawn further workers whenever scope or time justifies it. Parallelise research immediately. Keep the real voice loop as the critical path. Begin full implementation of healthcare submodules after the Milestone 1 voice loop is demonstrated, although guideline research and test-case preparation may proceed in parallel.

### Suggested specialist lanes

| Worker | Primary ownership | Starts |
|---|---|---|
| 1R — Gnani/Pipecat research | Official docs, API verification, package compatibility | Immediately |
| 1V — Audio pipeline research | Audio formats, VAD, WebSocket, barge-in design | Immediately |
| 1A — Danger-sign engine | Official guideline mapping and deterministic multilingual detector | Research immediately; implementation after Milestone 1 |
| 1B — Conversation state machine | Turn state, read-back, correction and confirmation | Design in parallel; implementation after Milestone 1 |
| 1C — Healthcare extraction | Typed visit fields, date/weight/vaccination parsing and validation | Design in parallel; implementation after Milestone 1 |
| 1D — Integration contracts | OpenAPI, JSON schemas, events and cross-laptop handoff | Define after the backend event model is agreed; coordinate early |

These are lanes, not a fixed staffing limit. Split work further when independent deliverables exist. One sub-agent may take more than one small task only when it does not compromise reviewability.

## File ownership

| Area | Owner | Agent 1 may do |
|---|---|---|
| `backend/**` voice and AI services | Agent 1 | Implement and review |
| `shared-contracts/**` | Agent 1 coordinates; all agents consume | Publish versioned contracts |
| `docs/**` backend and integration docs | Agent 1 | Write and maintain |
| `android/**` | Agent 2 | Read contracts; do not implement or overwrite |
| Web/Next.js app | Agent 3 | Read contracts; do not implement or overwrite |
| Supabase migrations/schema/RLS/auth | Agent 3 | Provide requirements and contract mapping only |

If the existing repository uses different paths, inspect and respect its actual structure rather than forcing this layout.

## Integration rules

1. Agree on event names, payload schemas, IDs, timestamps, error shape and versioning before clients bind to them.
2. Keep WebSocket transport events separate from persistent visit-record fields.
3. Use stable, documented enum values and ISO-8601 date/time formats.
4. Include a schema/version identifier in messages where useful.
5. Make danger-alert events high priority and independently consumable by both clients.
6. Do not require Android or web clients to understand provider-specific Gnani payloads.
7. Backend owns conversation state and safety-critical detection; clients render state and capture user input.
8. Agent 3 owns durable persistence. Agree on save/confirmation semantics before integration.
9. Keep backward compatibility where practical; announce breaking contract changes and update all schemas and the handoff document.
10. Do not modify another agent's owned modules to make an integration pass. Raise a contract issue and coordinate instead.

## Sub-agent handoff format

Every sub-agent must report:

- Summary of completed work.
- Exact files created/modified.
- Public interfaces and assumptions.
- Dependencies added and why.
- Commands/tests executed and actual outcomes.
- Whether tests used mocks or real services.
- Security/privacy considerations.
- Unresolved blockers and recommended next action.

Agent 1 reviews and accepts/rejects each contribution. No sub-agent may claim the entire milestone complete based only on its own module.
