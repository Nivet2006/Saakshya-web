# Voice Session Protocol Specification (`v1`)

> **Owner:** Agent 1 (AI Voice & Healthcare Backend)  
> **Schemas:** [`shared-contracts/voice-events.schema.json`](../shared-contracts/voice-events.schema.json), [`shared-contracts/visit.schema.json`](../shared-contracts/visit.schema.json), [`shared-contracts/danger-alert.schema.json`](../shared-contracts/danger-alert.schema.json)  
> **Contract Version:** `v1` (technology-independent; provider internals are never exposed to clients)

---

## 1. Transport & Session Lifecycle

1. **Create Session (HTTP):**
   - `POST /api/v1/sessions` with `{ "language": "indic-auto", "beneficiary_id": null | "BEN-1042", "worker_id": "ASHA-DEMO-01" }`.
   - Returns `session_id`, `websocket_path` (`/ws/voice/{session_id}`), and canonical `audio_format`.
2. **Open Full-Duplex WebSocket:**
   - Connect to `ws://<host>:<port>/ws/voice/{session_id}` (or `wss://` behind TLS).
   - Optional query params:
     - `language`: override session language (`indic-auto`, `hi-IN`, `kn-IN`, `ta-IN`, `en-IN`, etc.).
     - `disable_vad=true`: disables server-side local Silero VAD (testing/offline harness only; keep `false` for live mic sessions).
3. **Handshake Readiness:**
   - Wait for `session_ready` followed by `session_state` (`state: "listening"`).
   - If required server credentials are missing, the server emits `error` (`code: "MISSING_CREDENTIALS"`, `retryable: false`) and closes with WebSocket code `1011`.
4. **Active Conversation:**
   - Client streams continuous microphone audio while simultaneously receiving transcripts, draft updates, danger alerts, and streaming TTS audio.
5. **Graceful Termination:**
   - Client sends `{"schema_version": "v1", "type": "end_session"}` or closes the WebSocket cleanly (`1000`). The server cancels active tasks and tears down upstream connections.

---

## 2. Canonical Audio Framing (Uplink & Downlink)

A single uncompressed audio format is used end-to-end across clients, local VAD, streaming STT, and streaming TTS so zero server-side resampling is required:

| Parameter | Canonical Value |
|---|---|
| **Encoding** | Signed 16-bit little-endian linear PCM (`pcm_s16le`) |
| **Sample Rate** | `16000` Hz |
| **Channels** | `1` (mono) |
| **Sample Width** | `2` bytes |
| **Frame Duration** | `32` ms |
| **Frame Size** | `512` samples = `1024` bytes |

### Microphone Uplink (Client -> Server)
- **Primary (Recommended):** Send raw **WebSocket binary frames** of `1024` bytes (`pcm_s16le`, 32 ms each).
- **Fallback (JSON):** Send `{"schema_version": "v1", "type": "audio_chunk", "audio_base64": "<base64 PCM>"}`.
- **Important:** Do **not** wrap uplink frames in WAV/RIFF headers or Opus/AAC containers.

### TTS Audio Downlink (Server -> Client)
- Server emits:
  1. `assistant_response` (text + `turn_id` + `is_danger_escalation`)
  2. `tts_start` (`turn_id`, `sample_rate: 16000`, `encoding: "pcm_s16le"`, `channels: 1`)
  3. Zero or more `tts_audio_chunk` events (`turn_id`, monotonic `seq >= 1`, `audio_base64` raw `pcm_s16le` with any upstream WAV headers already stripped and int16-aligned)
  4. Either `tts_complete` (`turn_id`, `total_chunks`, `total_bytes`) OR `tts_cancelled` (`cancelled_turn_id`, `reason`).

---

## 3. Event Catalogue

### 3.1 Client -> Server JSON Messages

| `type` | Required Fields | Purpose |
|---|---|---|
| `audio_chunk` | `audio_base64` | Base64 PCM fallback when binary WS frames cannot be used |
| `barge_in` | *(none; optional `reason`)* | Explicit user interruption (e.g., mic tap) cancelling active TTS |
| `text_input` | `text` | Testing/accessibility text utterance fed into the same pipeline |
| `set_language` | `language` | Switch active response BCP-47 language (`hi-IN`, `kn-IN`, `ta-IN`, `en-IN`, `indic-auto`, etc.) |
| `confirm_visit` | `visit_id`, `confirmed` | Optional UI confirmation mirror of spoken confirmation |
| `persistence_ack` | `visit_id`, `correlation_id`, `accepted` | Persistence acknowledgement (alternative to HTTP `POST /api/v1/sessions/{session_id}/persistence-ack`) |
| `ping` | *(none; optional `client_timestamp`)* | Application heartbeat |
| `end_session` | *(none; optional `reason`)* | Graceful disconnect |

### 3.2 Server -> Client JSON Events

All server events carry `schema_version: "v1"`, `type`, `session_id`, and UTC ISO-8601 `timestamp` (`timestamp` may be omitted only on pre-session connection errors).

| Category | `type` | Semantics |
|---|---|---|
| **Session** | `session_ready` | Confirms audio format, language, and session readiness |
| | `session_state` | State machine indicator (`idle`, `listening`, `processing`, `speaking`, `danger_escalation`, `read_back`, `awaiting_confirmation`, `committing`, `committed`, `closed`) + `turn_id` |
| | `pong` | Heartbeat reply |
| | `error` | Structured error (`code`, `message`, `retryable`, optional `turn_id`) |
| **STT** | `speech_start` / `speech_end` | Voice utterance boundaries (`utterance_id`) |
| | `partial_transcript` | Live streaming interim transcript (`text`, `stable_text`, `volatile_text`, `is_final: false`) |
| | `final_transcript` | Committed segment transcript (`text`, `language`, `latency_ms`, `is_final: true`) |
| **Assistant & TTS** | `assistant_response` | Text of assistant reply for `turn_id` (`is_danger_escalation` flag) |
| | `tts_start` / `tts_audio_chunk` / `tts_complete` | Streaming `pcm_s16le` playback tagged by `turn_id` and `seq` |
| **Barge-In** | `barge_in` | Turn counter incremented (`cancelled_turn_id`, `new_turn_id`, `trigger`) |
| | `tts_cancelled` | **Immediate audio flush directive** for `cancelled_turn_id` |
| **Visit Lifecycle** | `visit_draft_updated` | Extraction created/updated unconfirmed draft (`status: "draft"`) |
| | `clarification_required` | Ambiguous beneficiary, missing field, or uncertain danger phrase |
| | `read_back_started` | Assistant reading structured record aloud prior to confirmation |
| | `correction_applied` | Field-level patch preserving all other fields; `requires_re_read_back: true` |
| | `visit_confirmed` | Explicit worker confirmation received (`status: "confirmed"`, NOT yet durably persisted) |
| | `persistence_requested` | Handoff payload (`correlation_id`, `visit`, `danger_alerts`) to persistence layer |
| | `visit_committed` | Durable save confirmed (`status: "committed"`, `persistence_record_id`, `committed_at`) |
| | `persistence_rejected` | Durable save failed; client must retain local/unsaved state and allow retry |
| **Safety** | `danger_alert` | **Highest priority.** Independent of visit completion. `priority: "urgent"`, `danger_sign_flagged: true`, embeds `DangerAlert` |

---

## 4. Zero-Stale-Audio Barge-In Protocol

Every assistant speech turn is assigned a monotonically increasing `turn_id`.

```text
Server                                Client (Android / CLI)
  │─── tts_start (turn_id=1) ──────────►│ activeTurnId = 1; prepare AudioTrack
  │─── tts_audio_chunk (turn_id=1) ────►│ write PCM if chunk.turn_id == activeTurnId
  │                                     │
  │◄── [User interrupts / speaks] ──────│ continuous 32ms binary PCM uplink
  │ (Dual-gate VAD or partial >=2 words │
  │  or client barge_in event)          │
  │                                     │
  │─── barge_in (cancelled=1, new=2) ──►│ activeTurnId = 2
  │─── tts_cancelled (cancelled=1) ────►│ IMMEDIATE audioTrack.pause(); flush(); play()
  │─── tts_audio_chunk (stale turn=1) ─►│ DROPPED (turn_id < activeTurnId)
  │─── partial_transcript (new speech) ►│ render interrupting speech
```

**Client Obligations:**
1. Track `activeTurnId` (initially `0`). Advance on `tts_start` (`turn_id`) and `barge_in` (`new_turn_id`).
2. On `tts_cancelled` or `barge_in`, **immediately** clear any queued PCM bytes and flush the OS audio output buffer (`AudioTrack.pause(); AudioTrack.flush(); AudioTrack.play()` on Android).
3. Silently drop any `tts_audio_chunk` where `chunk.turn_id != activeTurnId`.
4. Keep microphone capture running continuously during assistant playback (with hardware Acoustic Echo Cancellation enabled) so natural voice barge-in works hands-free.

---

## 5. Danger-Sign Interruption Semantics

When Agent 1's deterministic danger-sign engine detects a verified maternal or newborn danger sign (on either partial or final transcripts):

1. Normal assistant generation/TTS is **immediately interrupted** (`barge_in` + `tts_cancelled` with `trigger/reason: "danger_sign"`).
2. `danger_alert` is emitted immediately **before** visit completion or confirmation.
3. `session_state` enters `danger_escalation`, and an urgent PHC/SNCU referral message is spoken in the active language (`assistant_response` with `is_danger_escalation: true`, followed by `tts_*`).
4. Even if the worker subsequently continues recording or correcting other visit fields, `danger_sign_flagged: true` and the matched `danger_signs` / `follow_up_actions` (`phc_referral`, `priority: "urgent"`) remain permanently attached to the visit record.
5. Clients **must never** suppress, hide, or downgrade a `danger_alert`.

---

## 6. Error Codes & Retryability

| Error Code | Retryable | Trigger & Client Action |
|---|---|---|
| `MISSING_CREDENTIALS` | `false` | Server missing required `.env` keys; notify operator |
| `INVALID_JSON` | `true` | Client sent malformed JSON text frame; fix serialization |
| `AUDIO_FORMAT_ERROR` | `true` | Non-aligned or invalid audio frame; verify 16kHz mono `pcm_s16le` |
| `STT_STREAM_ERROR` / `STT_LOOP_ERROR` / `STT_PROVIDER_ERROR` | `true` | Transient upstream STT issue; display brief banner and allow retry/reconnect |
| `TTS_STREAM_ERROR` | `true` | Transient upstream TTS issue; display `assistant_response` text even if audio failed |
| `TURN_PROCESSING_ERROR` | `true` | Transient LLM/orchestration failure; session returns to `listening` |
| `BENEFICIARY_NOT_FOUND` | `false` | Unknown synthetic `beneficiary_id` in `POST /api/v1/sessions` |
| `PERSISTENCE_FAILED` | `true` | Durable storage failed; retain confirmed record and prompt retry |
| `INVALID_STATE_TRANSITION` | `false` | Attempted invalid action (e.g., committing an unconfirmed `draft`) |
| `SESSION_INTERNAL_ERROR` | `true` | Unexpected backend exception; reconnect with a fresh session if socket closed |
