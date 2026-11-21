# Environment and Repository Bootstrap

This setup is mandatory at the start of Agent 1 work, before substantial coding.

## 1. Root `.env` file

Use a **local root `.env` file** for all secrets and machine-specific configuration. Do not hard-code API keys, tokens, provider endpoints or model credentials in source code.

Bootstrap steps:

1. Copy `.env.example` to `.env` in the repository root.
2. Fill values only after checking the current official Gnani and LLM provider documentation and the credentials issued to the team.
3. Keep the real `.env` local. Never paste its contents into agent prompts, chat messages, source files, logs or screenshots.
4. Configure the backend settings loader to read the root `.env` (for example, via `pydantic-settings`/`python-dotenv`, depending on the selected stack).
5. Validate required settings at startup and fail with a helpful message that names the missing variable, never its value.
6. Add new environment variable names to `.env.example` with blank or safe example values. Never copy secret values into the example file.

Provider endpoint and credential variable names in `.env.example` are configuration placeholders, not claims about Gnani's API schema. Adapt them to the exact documented authentication and endpoint requirements after verification. Do not invent URLs or model identifiers.

## 2. `.gitignore` immediately

Copy the supplied `.gitignore` to the project root before creating build artifacts or test recordings. Extend it for any generated secrets, caches, logs, local databases, temporary audio or build outputs introduced by the actual project.

Critical requirements:

- Ignore `.env`, `.env.*`, local secret files and credentials.
- Explicitly keep `.env.example` trackable (`!.env.example`).
- Ignore Python virtual environments, bytecode and caches.
- Ignore Node/Next.js dependencies and build output for the shared multi-app repository.
- Ignore logs, test outputs, generated audio and recordings by default.
- Do not ignore source files, dependency lockfiles or JSON Schemas needed by the other agents.

## 3. Git is intentionally not initialized

**Do not run any Git initialization or setup command yet.** Specifically, do not run:

- `git init`
- `git add`
- `git commit`
- `git remote add` or `git remote set-url`
- `git config` for repository setup
- any command that creates/connects a Git repository

Do not create a remote repository or push code. The user will decide when Git is initialized. You can create and edit files normally without Git.

If a tool or framework offers to initialize Git automatically, decline/disable that option. Do not run `git check-ignore` if no repository exists; inspect `.gitignore` directly instead.

## 4. Safe local audio/testing

- Use synthetic beneficiaries and synthetic test speech only.
- Do not save microphone recordings by default.
- If temporary test audio is required, make it opt-in, store it in an ignored directory, and remove it when no longer needed.
- Never log raw beneficiary health speech or credentials.
