# Git Workflow — Milestone Commits and Pushes

Git is authorized for this project. Use version control continuously, but group related consecutive edits into reviewable milestones. Do not make a commit for every keystroke or individual file change.

## Bootstrap

- Inspect for an existing `.git/` directory first.
- If this is already a repository, preserve its history, branch, remotes and working-tree changes.
- If it is not a repository, initialize Git once on `main` after `.gitignore` and `.env` handling are in place.
- Ensure `.env` and `.env.*` are ignored, with `.env.example` explicitly allowed.
- Never stage credentials, `.env`, service-role keys, private certificates, real health data, real audio or local build artifacts.

## Commit and push cadence

Create a commit after each coherent batch of related work, then push that commit when a valid remote is configured and the current branch is ready to publish. Use these suggested milestones; adapt to actual progress without creating empty or premature commits:

1. **Bootstrap and architecture** — `.gitignore`, `.env.example`, project structure, docs, verified architecture decisions and initial tests.
2. **Provider adapters** — verified Gnani Prisma/Timbre adapters, LLM adapter, configuration, error handling and unit tests.
3. **Voice loop** — actual microphone/WebSocket/STT/LLM/TTS/playback path, test harness, barge-in and resume. Label real-provider evidence accurately.
4. **Healthcare intelligence** — visit extraction, state machine, voice corrections, deterministic danger-sign engine, source citations and test suite.
5. **Integration handoff** — OpenAPI/JSON Schemas, event protocol, examples and Agent 2/Agent 3 handoff documentation.

For Agent 3, use equivalent feature batches: (a) web shell/auth/RLS/schema foundation, (b) ASHA voice client and feature-parity workflow, (c) offline drafts/sync and persistence, (d) supervisor command centre/reports, and (e) integration hardening and handoff. Keep commits focused and coordinate shared-contract changes first.

## Safe sequence for every batch

1. Finish the related edits and run the relevant tests/checks.
2. Inspect `git status --short` and review the changes.
3. Stage only intended source, docs, schemas, migrations and test files. Prefer explicit paths or carefully review `git add -A` consequences.
4. Review `git diff --cached --name-only` and `git diff --cached --stat`.
5. Confirm `.env`, private keys, credentials, real data, recordings and generated artifacts are not staged.
6. Commit with a descriptive message, e.g. `feat(voice): add Prisma streaming adapter`.
7. If a remote is configured and the branch/remote are verified, push the current branch using a normal, non-force push.
8. If no remote exists, keep the local commit and report `push blocked: no remote configured`; do not invent a URL.
9. If push is rejected, stop and reconcile safely. Never force-push, reset away work or rewrite shared history.

## Cadence guidance

Push after each completed milestone batch (or after a few tightly related implementation batches when they form one coherent, tested feature), not after every small edit. Do not wait until the end of the 24-hour hackathon to publish all work. At each handoff, report the latest commit hash, branch, push status and any uncommitted work.

## Secret hygiene

- Never `git add -f .env`.
- Never copy secrets into commit messages, docs, screenshots or issue text.
- If a secret is accidentally committed, treat it as compromised: notify the project owner, rotate/revoke it, and follow a coordinated cleanup process. Do not assume deleting the file in a later commit removes it from history.
