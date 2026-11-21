# ASHA Voice Field Register — Multi-Agent Orchestration Pack

This pack coordinates three independent development environments. Agent 1 owns the AI voice/backend and shared contracts; Agent 2 owns Android; Agent 3 owns the complete Web ASHA client and Supabase, including 100% functional feature parity with Android plus PHC supervisor features.

## Files

- `MASTER.md` — Agent 1 startup entry point and reading order.
- `AGENTS.md` — authoritative Agent 1 scope, architecture and safety instructions.
- `ORCHESTRATION.md` — three-agent authority, unlimited internal sub-agents and ownership boundaries.
- `EXECUTION_PLAN.md` — mandatory build order and real Gnani voice-loop acceptance gate.
- `ENVIRONMENT_SETUP.md` — root `.env`, `.gitignore` and repository bootstrap.
- `GIT_WORKFLOW.md` — safe milestone commits and consecutive pushes.
- `INTEGRATION_CONTRACTS.md` — shared HTTP/WebSocket/data contracts for Android and Web.
- `AGENT3_WEB_FEATURE_PARITY.md` — complete mandatory web parity and supervisor specification.
- `AGENT1_LAUNCH_PROMPT.md` — ready-to-paste Agent 1 first message.
- `AGENT3_LAUNCH_PROMPT.md` — ready-to-paste Agent 3 startup prompt.
- `subagents/` — specialist prompts for danger signs, state machine, extraction and API contracts.
- `.env.example` — environment template with placeholders only.
- `.gitignore` — root ignore baseline.

## Agent 1 — paste `AGENT1_LAUNCH_PROMPT.md` first

Use `AGENT1_LAUNCH_PROMPT.md` as the first message to the Agent 1 coding environment. It directs the agent to read the complete project instructions, bootstrap `.env`/`.gitignore`, initialize Git only when needed, and use milestone-based commits and pushes.

## Agent 3 — paste this on the Web/Database laptop

Use `AGENT3_LAUNCH_PROMPT.md`. The web application must include the full ASHA Worker workflow with 100% functional parity against Android, plus the PHC supervisor command centre. A supervisor-only dashboard is unacceptable.

## Environment and safety notes

1. Copy the pack contents into the project root, preserving the `subagents/` folder.
2. Copy `.env.example` to `.env` locally only if `.env` does not already exist; fill in actual credentials locally.
3. Never commit `.env`, API keys, service-role keys, real beneficiary information or real audio.
4. `SUPABASE_SERVICE_ROLE_KEY` is server-only; never expose it to browser or Android clients.
5. Verify provider endpoints, model settings, language support and streaming semantics against official documentation before implementation.
6. Use synthetic beneficiary data and synthetic test speech only.
7. The `GIT_WORKFLOW.md` cadence groups related edits into milestone commits and pushes; do not push every individual file edit.
