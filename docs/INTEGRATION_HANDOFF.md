# Cross-Agent Integration Handoff (`v1`)

> **Published by:** Agent 1 (Master Architect & AI Voice/Backend Lead)  
> **Consumers:** Agent 2 (Android / Kotlin / Jetpack Compose) & Agent 3 (Next.js Web Dashboard / Supabase)  
> **Contract Version:** `v1`  
> **Timezone Policy:** All `*_at` timestamps are UTC ISO-8601 (`date-time`); all calendar dates (`next_visit_date`, `due_date`) are `YYYY-MM-DD` evaluated in **`Asia/Kolkata`**.

---

## 1. Published Contract Artifacts (`shared-contracts/`)

| File | Standard | Purpose |
|---|---|---|
| [`shared-contracts/visit.schema.json`](../shared-contracts/visit.schema.json) | JSON Schema Draft 2020-12 (`v1`) | Canonical structured ASHA visit record + `FollowUpAction` + synthetic ANC & danger-flagged Newborn examples |
| [`shared-contracts/danger-alert.schema.json`](../shared-contracts/danger-alert.schema.json) | JSON Schema Draft 2020-12 (`v1`) | Safety-critical urgent danger-sign alert with official NHM/MoHFW guideline citation |
| [`shared-contracts/voice-events.schema.json`](../shared-contracts/voice-events.schema.json) | JSON Schema Draft 2020-12 (`v1`) | Full discriminated union (`oneOf`) of all 8 client->server and 23 server->client WebSocket events + binary audio framing spec |
| [`shared-contracts/openapi.json`](../shared-contracts/openapi.json) | OpenAPI 3.1.0 (`1.0.0` / `v1`) | REST endpoints, request/response models, and structured error codes |
| [`shared-contracts/mock-events.jsonl`](../shared-contracts/mock-events.jsonl) | NDJSON (`v1`) | 46-event end-to-end synthetic session replay (clarification -> draft -> read-back -> TTS -> barge-in -> field correction -> urgent danger alert -> re-read-back -> confirm -> persistence ack -> commit) |
| [`docs/VOICE_PROTOCOL.md`](./VOICE_PROTOCOL.md) | Protocol Spec | Wire framing, barge-in flush sequence, danger interruption, error handling |

> **Zero Provider Leakage:** Clients MUST only consume these `v1` contracts. Do not parse or rely on provider-specific STT/TTS formats. Any optional diagnostic strings (`stt_provider`, `tts_provider`) in `session_ready` are informational only.

---

## 2. Backend Implementation Status (Truthful Readiness Matrix)

| Capability / Interface | Status in Agent 1 Backend | Notes |
|---|---|---|
| `GET /health` | **LIVE & Verified** | Returns readiness and live credential status |
| `POST /api/v1/sessions` | **LIVE & Verified** | Creates session metadata & validates synthetic `beneficiary_id` |
| `GET /api/v1/beneficiaries` | **LIVE & Verified** | Searches synthetic directory (`BEN-1042`..`BEN-1048`) |
| `WS /ws/voice/{session_id}` (voice loop, streaming partials/finals, LLM, streaming TTS, dual-gate VAD barge-in, `tts_cancelled`) | **LIVE & Verified** (Milestone 1) | Verified live with real streaming STT/TTS + local ONNX Silero VAD |
| Healthcare WS events (`visit_draft_updated`, `clarification_required`, `read_back_started`, `correction_applied`, `visit_confirmed`, `persistence_requested`, `visit_committed`, `persistence_rejected`, `danger_alert`) | **LIVE & Schema-Verified** (Phase 2) | Wired to 1A/1B/1C in `backend/app/healthcare/pipeline.py` & `/ws/voice/{session_id}`; verified 100% compliant against `voice-events.schema.json` in unit + LIVE Gnani E2E tests |
| `GET /api/v1/sessions/{session_id}/visit`, `POST /api/v1/sessions/{session_id}/persistence-ack`, `POST /api/v1/danger-signs/check` | **LIVE & Schema-Verified** (Phase 2) | Live in `backend/app/api/routes.py` with `409 INVALID_STATE_TRANSITION` guard on unconfirmed drafts and `v1` schema parity |

---

## 3. Integration Guide for Agent 2 (Android / Kotlin / Jetpack Compose)

### 3.1 Ownership Reminder
Agent 2 owns Android capture/playback, permissions, Compose UI, local offline draft caching, and network reconnection. **Do NOT reimplement danger-sign matching rules or healthcare field extraction on Android** — Agent 1's backend is authoritative.

### 3.2 Audio Capture (`AudioRecord` -> WebSocket Binary)
- Configure `AudioRecord`:
  - `sampleRateInHz = 16000`
  - `channelConfig = AudioFormat.CHANNEL_IN_MONO`
  - `audioFormat = AudioFormat.ENCODING_PCM_16BIT`
  - `audioSource = MediaRecorder.AudioSource.VOICE_COMMUNICATION` (enables platform AEC on most Android devices)
- Attach `AcousticEchoCanceler` and `NoiseSuppressor` to `audioRecord.audioSessionId` whenever `isAvailable() == true`.
- Read and transmit **`1024`-byte (`512` samples = `32` ms)** chunks as raw WebSocket **binary frames** (`ByteString`).
- Keep mic streaming continuously during assistant TTS so hands-free barge-in works. Also expose a large hands-free/accessible "Stop / Interrupt" button that sends `{"schema_version": "v1", "type": "barge_in", "reason": "user_tap"}`.

### 3.3 Audio Playback (`AudioTrack` & Immediate Flush on Barge-In)
- Configure `AudioTrack` in `MODE_STREAM`, `16000` Hz, `CHANNEL_OUT_MONO`, `ENCODING_PCM_16BIT`, `USAGE_VOICE_COMMUNICATION`, `CONTENT_TYPE_SPEECH`.
- Maintain a monotonic `activeTurnId: Int = 0` on the audio playback actor:
  1. On `tts_start`: set `activeTurnId = event.turn_id`; ensure `audioTrack.play()` is running.
  2. On `tts_audio_chunk`: **ignore** if `event.turn_id != activeTurnId`. Otherwise decode `audio_base64` and write PCM bytes to `AudioTrack`.
  3. On `barge_in`: set `activeTurnId = event.new_turn_id`, clear local playback queue, call `audioTrack.pause(); audioTrack.flush(); audioTrack.play()`.
  4. On `tts_cancelled`: if `event.cancelled_turn_id >= activeTurnId` (or matches playing turn), immediately clear queue and call `audioTrack.pause(); audioTrack.flush(); audioTrack.play()`.
  5. On `tts_complete`: mark speaking indicator idle once buffered audio drains.

### 3.4 UI Rendering Rules
- **Live Transcript:** Render `partial_transcript` with `stable_text` in normal ink and `volatile_text` muted/italic; replace with committed `final_transcript`.
- **Visit Draft Card (`visit_draft_updated`, `correction_applied`):**
  - Display `null` fields as `"Not recorded"` — never default `weight_kg` to `0` or fabricate dates.
  - Clearly badge `status == "draft"` as **Draft (Unconfirmed)**, `status == "confirmed"` as **Confirmed — Saving...**, and ONLY badge **Saved** when `visit_committed` arrives (`status == "committed"` with non-null `persistence_record_id`).
  - On `correction_applied`, briefly highlight `corrected_fields` and note that re-read-back is required before saving.
- **Clarification (`clarification_required`):** Show spoken `prompt_text` and optional tap-or-speak `candidates` (e.g., `BEN-1044` vs `BEN-1043`), keeping the workflow 100% voice-operable with zero typing required.
- **Urgent Danger Banner (`danger_alert`):**
  - Render immediately at the top of the screen with high-contrast red styling, audible chime/vibration, `canonical_name`, `referral_message`, and `source_guideline_ref`.
  - **Never** auto-dismiss when a subsequent `visit_draft_updated` arrives; keep visible until explicitly acknowledged.

### 3.5 Immediate Offline Mock Testing
Replay [`shared-contracts/mock-events.jsonl`](../shared-contracts/mock-events.jsonl) line-by-line into your WebSocket event parser (e.g., `kotlinx.serialization` sealed class discriminated on `type`) to verify every UI state before connecting to the live backend.

---

## 4. Integration Guide for Agent 3 (Next.js Dashboard & Supabase Persistence)

### 4.1 Ownership Reminder
Agent 3 owns all Supabase tables, SQL migrations, RLS policies, authentication, durable persistence, and the Next.js supervisor dashboard. Agent 1 intentionally does **not** create Supabase migrations or dictate DDL.

### 4.2 Logical Data Requirements (Mapping `v1` Contracts to Agent 3's Schema)

#### A. Durable Visits (from `shared-contracts/visit.schema.json`)
Map these required contract fields into Agent 3's visit storage:
- **Identifiers:** `visit_id` (unique idempotency key from Agent 1), `session_id`, `worker_id`, `beneficiary_id` (`BEN-xxxx` nullable), `beneficiary_name` (nullable).
- **Clinical/Register Fields:** `visit_type` (`ANC | PNC | Newborn | Immunisation | null`), `weight_kg` (numeric nullable), `weight_source_text`, `vaccinations_completed` (string array), `vaccinations_due` (string array), `next_visit_date` (date in `Asia/Kolkata`, nullable), `next_visit_date_source_text`, `danger_signs` (string array), `danger_sign_flagged` (boolean, indexed for supervisor triage), `follow_up_actions` (structured list of `{action_type, description, due_date, priority, source_phrase}`).
- **Lifecycle & Audit:** `status` (`confirmed` -> `committed` upon durable write; **never persist `draft` as a completed visit**), `confirmed_at` (UTC), `committed_at` (UTC), `language`, `timezone` (`Asia/Kolkata`), `synthetic` (`true` for demo records).
- Return Agent 3's primary key/UUID as opaque string `persistence_record_id`.

#### B. Danger Alerts (from `shared-contracts/danger-alert.schema.json`)
Store independently of visits so urgent alerts appear on the supervisor dashboard **immediately upon detection**, even before a visit is confirmed or committed:
- **Identifiers:** `alert_id` (unique idempotency key), `session_id`, `visit_id`, `beneficiary_id` (nullable).
- **Clinical & Guideline Provenance:** `canonical_danger_sign_id`, `canonical_name`, `subject` (`mother | newborn | infant`), `category` (`ANC | Intranatal | PNC | Newborn`), `supporting_evidence` (short matched phrase only, <= 200 chars), `match_type`, `source_guideline_ref` (official NHM/MoHFW citation).
- **Escalation & Workflow:** `detected_at` (UTC), `status` (`active | acknowledged | referred | resolved`), `acknowledged_by`, `acknowledged_at`, `escalation_language`, `referral_message`, `danger_sign_flagged` (`true`), `priority` (`urgent`).

### 4.3 Two-Phase Confirmation & Persistence Handshake

```text
ASHA Worker speaks "Haan, save kar do" (after full read-back)
  │
  ▼
Agent 1 emits:
  1. visit_confirmed        (status = "confirmed", confirmed_at set, persistence_record_id = null)
  2. persistence_requested  (correlation_id, visit, danger_alerts)
  │
  ▼
Agent 3 (or Android -> Agent 3 API) durably writes visit + danger_alerts to Supabase
  │
  ├── On Success:
  │     Send HTTP POST /api/v1/sessions/{session_id}/persistence-ack
  │     (or WS client message type="persistence_ack")
  │     with: { accepted: true, visit_id, correlation_id, persistence_record_id, committed_at }
  │     ──► Agent 1 emits: visit_committed (status = "committed")
  │
  └── On Failure:
        Send accepted: false, error_code: "PERSISTENCE_FAILED", error_message: "..."
        ──► Agent 1 emits: persistence_rejected (retryable: true)
            Visit stays status = "confirmed" (NOT committed); worker/client can retry.
```

**Critical Safety & Integrity Rules for Agent 3:**
1. **Idempotency:** Upsert on `visit_id` (visits) and `alert_id` (danger alerts) so retried `persistence_requested` handoffs never create duplicate records.
2. **Never auto-commit drafts:** Reject any persistence request where `visit.status != "confirmed"` or `visit.confirmed_at == null`.
3. **Independent Urgent Alert Visibility:** Surface `danger_alert` items immediately in the supervisor dashboard's urgent queue, displaying `canonical_name`, `beneficiary_id`, `source_guideline_ref`, `supporting_evidence`, and acknowledgement controls (`active -> acknowledged -> referred -> resolved`).
4. **Privacy / Synthetic Guardrail:** Keep `synthetic = true` visible in demo mode; avoid storing raw audio clips or full raw transcripts in general dashboard tables.

---

## 5. Contract Change Process

1. Agent 1 updates the relevant schema(s) in `shared-contracts/` and adds/updates validation tests in `backend/tests/test_contracts.py`.
2. Agent 1 updates this handoff document with breaking vs. non-breaking notes.
3. Never silently rename fields or alter enum values once Agents 2 or 3 have bound to them; introduce additive optional fields within `v1` or bump `schema_version` to `v2` for breaking changes.
4. Run `backend/.venv/bin/pytest backend/tests/test_contracts.py -v` before notifying Agents 2 and 3.
