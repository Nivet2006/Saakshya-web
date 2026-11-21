# ASHA Voice Field Register — AI Voice & Healthcare Backend (Agent 1)

**Project:** ASHA Voice Field Register (PS1 · Healthcare · 24-Hour Hackathon)  
**Owner:** Agent 1 — Master Architect & AI Voice/Backend Lead  
**Status:** Milestone 1 (Live Voice Loop) & Phase 2 (Healthcare Intelligence + `v1` Cross-Agent Contracts) **Verified & Passing**

A low-latency, voice-first Python/FastAPI backend that converts an ASHA worker's spoken home-visit notes in Indian languages with natural English code-mixing into structured visit records, spoken read-back confirmations, single-field voice corrections, follow-up actions, and immediate deterministic danger-sign PHC referral escalations — requiring **zero typing**.

---

## 1. Architecture & Verified Stack

```text
Microphone / Android / CLI (16 kHz, 16-bit LE mono PCM, 32 ms frames)
  └─► FastAPI WebSocket /ws/voice/{session_id}
        ├─► Local ONNX Silero VAD + Adaptive RMS Dual-Gate Barge-In
        ├─► Gnani Prisma v3.0 Streaming STT (wss://api.vachana.ai/stt/v3/stream)
        │     • indic-auto + 2–4 language candidates + format=codemix + x-partials=true + ASHA x-keywords
        ├─► Layer 1 Deterministic Danger-Sign Engine (runs on EVERY partial & final)
        │     • 44 NHM/MoHFW guideline-cited signs, Indic/ASR normalizer, clause negation/history/subject guards
        │     • Hard-interrupts active TTS immediately -> emits urgent v1 danger_alert -> PHC referral speech
        ├─► Healthcare Field Extractor (1C) + 9-State Conversation Machine (1B)
        │     • Synthetic beneficiary directory, weight/date/vaccination normalization, localized read-back,
        │       single-field correction patch, explicit confirmation gate, Agent 3 persistence-ack separation
        ├─► Replaceable LLM Adapter (Gemini 3.1 Flash-Lite zero-thinking / Groq optional fallback)
        └─► Gnani Timbre v3.0 Interruptible Streaming TTS (wss://api.vachana.ai/api/v1/tts)
              • 16 kHz linear_pcm, WAV header stripping + int16 alignment, socket-reset on barge-in (0 stale audio)
```

Key design documents:
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — System design, canonical audio format, barge-in architecture
- [docs/GNANI_INTEGRATION.md](docs/GNANI_INTEGRATION.md) — Live-verified Gnani Prisma v3.0 & Timbre v3.0 protocols
- [docs/DANGER_SIGN_GUIDELINES.md](docs/DANGER_SIGN_GUIDELINES.md) — Primary-source NHM/MoHFW citations (9 official PDFs)
- [docs/VOICE_PROTOCOL.md](docs/VOICE_PROTOCOL.md) — Full `v1` WebSocket event & binary PCM framing specification
- [docs/INTEGRATION_HANDOFF.md](docs/INTEGRATION_HANDOFF.md) — Handoff guide for Agent 2 (Android) and Agent 3 (Web/Supabase)
- [docs/DECISIONS.md](docs/DECISIONS.md) — Concise architectural decision log

---

## 2. Quick Setup & Running Locally

### Prerequisites
- Python `3.12` (tested on Python `3.12.7` / macOS `arm64`)
- `uv` (or `pip`)
- Valid credentials in root `.env` (never commit `.env`; `.gitignore` ignores `.env` and `.env.*` while keeping `.env.example` trackable)

### Installation
```bash
# 1. Create root .env from template if you don't already have one
cp -n .env.example .env
# Edit .env locally and populate GNANI_API_KEY and GEMINI_API_KEY

# 2. Create isolated virtual environment & install pinned dependencies
uv venv backend/.venv --python 3.12
uv pip install --python backend/.venv/bin/python -r backend/requirements.txt
```

### Start the FastAPI Backend
```bash
cd backend
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Verify readiness:
```bash
curl http://127.0.0.1:8000/health
```

### Run the Local CLI Voice / WAV / Barge-In Test Harness
```bash
# List audio devices
backend/.venv/bin/python backend/cli_client.py --list-devices

# Stream live microphone audio (recommend headphones to prevent speaker echo)
backend/.venv/bin/python backend/cli_client.py --server ws://127.0.0.1:8000 --language indic-auto

# Repeatable WAV replay + mid-TTS barge-in test
backend/.venv/bin/python backend/cli_client.py --wav /path/to/visit.wav --barge-in-wav /path/to/correction.wav
```

---

## 3. Gnani Configuration & Environment Variable Reference

All configuration is loaded from the repository root `.env` via `backend/app/core/config.py`. Never hardcode secrets.

| Variable | Default / Example | Purpose |
|---|---|---|
| `GNANI_API_KEY` | *(secret, required for live)* | Gnani Vachana API key (`X-API-Key-ID`) |
| `GNANI_STT_MODEL` | `prisma-v3.0` | Gnani streaming STT model (`x-model`) |
| `GNANI_TTS_MODEL` | `timbre-v3.0` | Gnani streaming TTS model |
| `GNANI_STT_WS_URL` | `wss://api.vachana.ai/stt/v3/stream` | Optional Prisma v3.0 WS URL override |
| `GNANI_TTS_WS_URL` | `wss://api.vachana.ai/api/v1/tts` | Optional Timbre v3.0 WS URL override |
| `GNANI_TTS_VOICE` | `Shivani` | Multilingual Timbre v3.0 voice (34 voices supported across all 10 Indic languages) |
| `LLM_PROVIDER` | `gemini` | Primary LLM provider (`gemini` or `groq`) |
| `LLM_MODEL` | `gemini-3.1-flash-lite` | Low-latency LLM model (auto-fallback: `gemini-3.5-flash-lite`) |
| `GEMINI_API_KEY` | *(secret, required for live)* | Google Gemini API key |
| `GROQ_API_KEY` | *(optional secret)* | Optional Groq API key if using `LLM_PROVIDER=groq` |
| `DEFAULT_LANGUAGE` | `hi-IN` | Default spoken language (`hi-IN`, `en-IN`, `kn-IN`, `ta-IN`) |
| `SUPPORTED_LANGUAGES` | `hi-IN,kn-IN,ta-IN,en-IN` | Language candidates (2–4 BCP-47 codes passed to Prisma `indic-auto`) |
| `AUDIO_SAMPLE_RATE` | `16000` | Canonical PCM_S16LE sample rate (Hz) |
| `VAD_THRESHOLD` | `0.6` | ONNX Silero VAD speech threshold |
| `BARGE_IN_MIN_SPEECH_MS` | `300` | Sustained dual-gate speech required to trigger barge-in |
| `ENDPOINT_SILENCE_MS` | `700` | Trailing silence before finalizing a speech segment |
| `LOG_REDACT_PHI` | `true` | Redacts raw health speech from backend logs by default |
| `SYNTHETIC_DATA_ONLY` | `true` | Enforces synthetic beneficiary directory (`BEN-1042`..`BEN-1048`) |
| `DANGER_SIGN_PARTIAL_MATCHING` | `true` | Runs Layer-1 danger-sign detector on streaming partials as well as finals |

---

## 4. Official Cited Danger-Sign Guidelines (Summary)

All 44 canonical danger signs in `backend/app/danger_signs/catalog.py` are grounded strictly in official Indian public-health publications (see [docs/DANGER_SIGN_GUIDELINES.md](docs/DANGER_SIGN_GUIDELINES.md) for the exhaustive citation matrix, thresholds, and inter-guideline notes):

| Phase | Representative Verified Danger Signs & Thresholds | Official Primary Source & Section/Page |
|---|---|---|
| **Antenatal (ANC)** | Any vaginal bleeding during pregnancy | NHSRC/MoHFW *ASHA Module 6* Part B §4, p. 30; *MCP Card 2018* p. 4; *Integrated ASHA Module 2026* §B.4.3, pp. 177, 183 |
| **Antenatal (ANC)** | Convulsions / fits / loss of consciousness | *ASHA Module 6* Part B §4, p. 31; *MCP Card 2018* p. 4; *Dakshata Operational Guidelines 2015* SCC CHECK-1, p. 14 |
| **Antenatal (ANC)** | Severe headache, blurred vision, swelling of face/hands, high BP (`>= 140/90 mmHg`) | *Integrated ASHA Module 2026* §B.4.3, pp. 177, 182–183; *ASHA Module 6* Part B §4, pp. 30–31; *Dakshata* CHECK-1, p. 14 |
| **Antenatal (ANC)** | Reduced/absent fetal movements; severe abdominal pain; high fever (`> 100°F` / `>= 38°C`); breathlessness; severe anaemia (`Hb < 7.0 g/dl`); PROM | *ASHA Module 6* Part B §4, pp. 30–32; *MCP Guidebook 2018* §6, p. 15; *Integrated ASHA Module 2026* pp. 177, 183 |
| **Intranatal** | Fresh bleeding; prolonged labour (`> 12h`); prolonged PROM; meconium-stained fluid; cord/limb prolapse; retained placenta (`> 30 min`) | *ASHA Module 6* Part B §4, p. 33 & Annexe 4, p. 66; *Dakshata* SCC CHECK-1–CHECK-3, pp. 14–16 |
| **Postnatal (PNC)** | Excessive postpartum bleeding (`> 5 pads/day`, `> 2–3 pads in 20–30 min`, `>= 500 ml`); puerperal sepsis (foul lochia + fever); fever `> 102°F`; fits/psychosis | *ASHA Module 6* Part C, pp. 49–53 & Annexe 5, p. 68; *Integrated ASHA Module 2026* §B.4.6, pp. 191–194; *Dakshata* CHECK-3–4, pp. 16–17 |
| **Newborn (HBNC)** | Birth asphyxia (no/weak cry); fast breathing (`>= 60/min`); severe chest indrawing; unable to feed/suck; lethargy/unconsciousness; convulsions | MoHFW *Revised HBNC Operational Guidelines 2014* Annexures 1b–1c, pp. 17–22 & p. 28; *ASHA Module 7* Part A & Annexe 1, pp. 20–31, 69–72 |
| **Newborn (HBNC)** | Fever (`> 99°F` / `37.2°C`); hypothermia (`< 95.9°F` / `35.5°C` or cold to touch); umbilical redness/pus; jaundice Day 1 or yellow palms/soles; `> 10` skin pustules; newborn bleeding; VLBW (`< 1.8 kg`) | *HBNC Operational Guidelines 2014* Annexures 1b–1c, pp. 17–22; *ASHA Module 6* Annexe 6, p. 71; *MCP Card 2018* pp. 5, 28; *Integrated ASHA Module 2026* §B.1.10, p. 46 |

**Safety Guardrail:** On any verified match, the assistant interrupts active speech immediately, flags `danger_sign_flagged = true`, emits a high-priority `v1` `danger_alert`, and speaks **referral instructions only** directing the worker to the nearest PHC immediately. It never diagnoses, prescribes medicine, recommends home remedies, or invents PHC locations/phone numbers. Layer 2 LLM can never suppress a Layer 1 positive match.

---

## 5. Verification & Test Results (2026-11-21)

Tests are strictly labelled by execution mode:

| Test Suite | Label | Command | Result |
|---|---|---|---|
| Milestone 1 Unit/Mocked Tests (`test_voice_unit.py`) | **UNIT / MOCKED** | `backend/.venv/bin/pytest backend/tests/test_voice_unit.py -v` | **5/5 PASSED** (WAV strip/int16 align, Prisma parser, ONNX Silero VAD noise rejection, barge-in 0-stale-audio, REST endpoints) |
| Danger-Sign Engine (`test_danger_signs.py`) | **UNIT** | `backend/.venv/bin/pytest backend/tests/test_danger_signs.py -v` | **129/129 PASSED** (44 catalog signs, Hindi/Hinglish/Kannada/Tamil/ASR noise, negation/history/other-person, multi-clause, Layer-2 non-suppression) |
| Conversation State Machine (`test_conversation_sm.py`) | **UNIT** | `backend/.venv/bin/pytest backend/tests/test_conversation_sm.py -v` | **42/42 PASSED** (9 states, clarification, corrections, explicit confirmation gate, failed persistence ack, danger interrupt from all states, 4-language read-back) |
| Healthcare Field Extractor (`test_extraction.py`) | **UNIT** | `backend/.venv/bin/pytest backend/tests/test_extraction.py -v` | **70/70 PASSED** (synthetic beneficiary lookup/disambiguation, weight/fractions/grams/ASR artifacts, completed vs due vaccines, IST dates, correction patches) |
| Shared `v1` Contracts (`test_contracts.py`) | **UNIT / CONTRACT** | `backend/.venv/bin/pytest backend/tests/test_contracts.py -v` | **8/8 PASSED** (Draft 2020-12 JSON Schemas, OpenAPI 3.1.0, 46-line `mock-events.jsonl`, FastAPI REST parity) |
| Integrated Healthcare E2E (`test_healthcare_e2e.py`) | **INTEGRATION (MOCKED TRANSPORT)** | `backend/.venv/bin/pytest backend/tests/test_healthcare_e2e.py -v` | **3/3 PASSED** (Full ANC -> correction -> confirm -> persistence-ack -> committed, partial-transcript danger interrupt, 100% strict `v1` schema parity) |
| Golden Evaluation Harness (`test_eval_golden.py`) | **GOLDEN EVAL (1E)** | `backend/.venv/bin/pytest backend/tests/test_eval_golden.py -v -s` | **1/1 PASSED** — **Danger Recall: 100.0% (15/15)**, **Specificity: 100.0% (8/8)**, **Per-Field Extraction Accuracy: 100.0% across all 6 fields** |
| **LIVE Milestone 1 Voice Loop** (`test_milestone1_live.py`) | **LIVE-GNANI + LIVE-GEMINI (0 MOCKS)** | `backend/.venv/bin/python -u backend/tests/test_milestone1_live.py` | **PASSED** — 14 live Prisma partials, 2 live finals (215–332ms), live Gemini replies, live Timbre TTS (TTFB 628ms), live ONNX VAD mid-TTS barge-in with **0 stale chunks**, live context resumption |
| **LIVE Phase 2 Healthcare + Danger Escalation** (`test_phase2_live.py`) | **LIVE-GNANI (0 MOCKS)** | `backend/.venv/bin/python -u backend/tests/test_phase2_live.py` | **PASSED** — Live Prisma Hinglish ANC extraction (`BEN-1042`, `52.0 kg`, `TT` due) -> live Timbre read-back -> live mid-readback interruption with vaginal bleeding danger sign -> immediate `ANC_VAGINAL_BLEEDING` alert + live Timbre urgent PHC referral (TTFB 162ms), **100% `v1` schema valid** |

Run all 258 automated tests at once:
```bash
backend/.venv/bin/pytest backend/tests/ -q
```

---

## 6. Shared Integration Contracts (Agents 2 & 3)

Published under `shared-contracts/` (version `v1`, technology-independent, zero Gnani payload exposure):
- [shared-contracts/openapi.json](shared-contracts/openapi.json) — REST API (`GET /health`, `POST /api/v1/sessions`, `GET /api/v1/beneficiaries`, `GET /api/v1/sessions/{session_id}/visit`, `POST /api/v1/sessions/{session_id}/persistence-ack`, `POST /api/v1/danger-signs/check`)
- [shared-contracts/visit.schema.json](shared-contracts/visit.schema.json) — Structured visit record (`draft` / `confirmed` / `committed`)
- [shared-contracts/danger-alert.schema.json](shared-contracts/danger-alert.schema.json) — Urgent danger-sign alert event
- [shared-contracts/voice-events.schema.json](shared-contracts/voice-events.schema.json) — All 8 client->server and 23 server->client WebSocket events
- [shared-contracts/mock-events.jsonl](shared-contracts/mock-events.jsonl) — 46-event synthetic session replay for immediate offline client development

Ownership boundaries respected: Agent 1 owns `backend/`, `shared-contracts/`, and backend/protocol docs; Agent 2 owns Android/Kotlin/Compose; Agent 3 owns Next.js and all Supabase tables, migrations, auth, and RLS.

---

## 7. Manual End-to-End Testing Checklist

- [ ] Start backend (`uvicorn app.main:app --port 8000`) and confirm `GET /health` returns `"live_credentials_configured": true`.
- [ ] Run `cli_client.py --list-devices` and connect with headphones + microphone (`cli_client.py --language indic-auto`).
- [ ] **Routine Hinglish ANC Visit:** Speak *"Today I visited Lakshmi, ANC checkup done, weight 52 kilo, TT injection pending hai, IFA goli regularly nahi le rahi, next visit 25 November."* Verify live partials, final transcript, and spoken read-back.
- [ ] **Mid-Readback Barge-In & Single-Field Correction:** Interrupt the assistant while it is reading back by saying *"No, next visit is 28 November."* Verify assistant audio stops immediately, only `next_visit_date` updates to `2026-11-28`, all other fields remain intact, and the corrected record is re-read.
- [ ] **Explicit Confirmation:** Say *"Yes"* / *"Haan, confirm karo"*. Verify `visit_confirmed` and `persistence_requested` emit (record does not claim `committed` until persistence ack arrives).
- [ ] **Noisy Background Test:** Play household/street noise in background during TTS playback; verify transient noise does not continuously trigger false barge-in.
- [ ] **Immediate Danger-Sign Escalation:** Start a new session for `BEN-1044` (or say *"Kavitha newborn baby, chest indrawing ho raha hai"*). Verify immediate interruption, `danger_alert` (`danger_sign_flagged=true`, `priority="urgent"`), urgent PHC referral speech, and alert preservation if visit notes continue.
- [ ] **Negation Guard Test:** Say *"Sunita ANC checkup, weight 56 kilo, koi bleeding nahi hai"*. Verify NO false danger alert triggers.

---

## 8. 3-Minute Live Hackathon Demo Script

1. **0:00–0:30 — Setup & Live Health:** Show `GET /health` (`prisma-v3.0`, `timbre-v3.0`, `gemini-3.1-flash-lite`, `synthetic_data_only: true`) and connect CLI/Android client to `/ws/voice/{session_id}`.
2. **0:30–1:20 — Zero-Typing Hinglish ANC Visit + Live Partials:** Speak Lakshmi's code-mixed ANC visit note with ambient household audio. Point out live streaming partials, `BEN-1042` resolution, `52.0 kg` extraction, `TT` due vs completed separation, IFA follow-up action, and natural spoken read-back.
3. **1:20–1:55 — Live Mid-Speech Barge-In & Single-Field Correction:** Interrupt the read-back mid-sentence: *"Nahi, next visit 28 November hai."* Highlight instant TTS cancellation (0 stale audio), surgical single-field patch preserving weight/TT/IFA, re-read, and explicit *"Haan, confirm karo"* confirmation.
4. **1:55–2:40 — Safety-Critical Deterministic Danger-Sign Interrupt:** Report a newborn danger sign in Hinglish (*"Baby ka chest indrawing ho raha hai aur doodh nahi pee raha"*). Show instant Layer-1 escalation interrupting speech, `danger_alert` event with exact NHM HBNC 2014 p. 22 citation, urgent PHC referral speech (no diagnosis/prescription), and alert persistence across the session.
5. **2:40–3:00 — Cross-Agent Contracts & Evaluation Proof:** Highlight `shared-contracts/` (`v1` JSON Schemas + OpenAPI + 46-event `mock-events.jsonl` for Android & Supabase teams) and the Golden Eval Harness (**100% danger-sign recall**, **100% per-field accuracy**, **258 passing tests + 2 live Gnani E2E passes**).

---

## 9. Known Limitations

- **Bluetooth HFP on macOS:** Using AirPods simultaneously as mic + speaker forces macOS Bluetooth into HFP mode; use wired headphones or MacBook Air mic + headphones for cleanest local barge-in tests.
- **In-memory session store:** Agent 1 maintains active session state in memory for the 24-hour demo; durable storage, auth, and RLS are owned by Agent 3 (Supabase) via the `persistence_requested` / `persistence-ack` handshake.
- **Age-stratified IMNCI breathing thresholds (>2 months):** Newborn HBNC thresholds (`>= 60/min`) are active by default; older-infant age-bracketed IMNCI cutoffs (`>= 50/min` for 2–12m, `>= 40/min` for 1–5y) are documented in `docs/DANGER_SIGN_GUIDELINES.md` and can be parameterized when beneficiary DOB/age-in-months is supplied by Agent 3.
- **Spoken number words in Kannada/Tamil:** Unicode digits and English/Hindi/Hinglish spoken number words/fractions are normalized deterministically; Kannada/Tamil spelled-out number words rely on upstream Prisma ITN/digit normalization.
