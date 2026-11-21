# Environment and Repository Bootstrap

Complete this setup before substantial implementation. Preserve any existing project configuration and credentials.

## 1. Root `.env` file

1. Use the supplied `.env.example` as the shared backend environment template.
2. Create a root `.env` by copying `.env.example` **only when `.env` does not already exist**. Never overwrite an existing `.env`.
3. Fill values using credentials issued to the team and provider documentation. Keep secrets, tokens and private endpoints in `.env`.
4. Load settings from `.env` using the chosen configuration library. Validate required settings at startup and report missing variable names without printing values.
5. Add new variable names to `.env.example` with blank or safe placeholder values. Never copy real secrets into `.env.example`, Markdown, logs, tests, agent prompts or screenshots.
6. Verify the Gnani URLs, model identifiers, language codes, audio formats and provider options against official docs. Blank endpoint fields are intentionally blank until verified; do not invent URLs.
7. `SUPABASE_SERVICE_ROLE_KEY` is server-only. Never expose it in browser bundles, `NEXT_PUBLIC_*` variables, Android packages or client-side logs.
8. Agent 3 must use a separate web runtime environment file for Next.js-specific public configuration. Only the Supabase URL and public/anon key may be exposed to the browser; privileged keys remain server-side. Coordinate exact variable names with the app implementation.

## 2. Root `.gitignore` — do this first

Copy/verify the supplied `.gitignore` at the repository root before generating build files, logs or recordings. It must ignore:

- `.env`, `.env.*`, credentials and local secrets, while explicitly retaining `.env.example`;
- Python virtual environments, caches and bytecode;
- Node/Next.js dependencies and build outputs;
- logs, local databases and generated audio/recordings by default;
- local IDE/OS files and generated test artifacts.

Extend the ignore file for additional generated secrets/artifacts introduced by the project. Do not ignore source files, lockfiles, migrations, schemas or other required deliverables.

Before the first commit, verify `.env` is ignored and `.env.example` is not ignored. Review the staged file list to ensure no secrets, recordings, credentials or generated artifacts are included.

## 3. Git initialization and collaboration

Git is now authorized for this workstream.

1. Inspect the directory first. If `.git/` already exists, preserve the repository, history, branch and configured remotes. **Never run `git init` in an existing repository.**
2. If and only if this directory is not already a Git repository, initialize it once with a `main` branch (use the Git version's supported syntax, e.g. `git init -b main`).
3. Do not rewrite history, delete branches, reset user changes, amend published commits or force-push.
4. Follow `GIT_WORKFLOW.md` for logical commit batches and push cadence.
5. Before every commit, review `git status`, the staged filenames and the staged diff. Confirm `.env` and other private files are absent.
6. If a remote is already configured, verify its URL and branch before pushing. Do not replace an existing remote.
7. If no remote is configured, continue making local milestone commits and report that a remote URL is required to push. Do not invent a remote URL or create a hosted repository without an approved URL/action.
8. If a push is rejected or the remote has diverged, stop and inspect the cause. Never force-push to make it succeed.

## 4. Synthetic-only audio and data

- Use synthetic beneficiaries and synthetic health information only.
- Do not save microphone recordings by default.
- Store optional synthetic test recordings in ignored directories and remove them when no longer needed.
- Never log raw beneficiary health speech, real PII or credentials.
