# Agent 1 Integration Status & Provisional Assumptions
**Date:** 2026-11-21  
**Author:** Agent 3 (Web & Database Lead)  
**Status:** Provisional Local Adapters Active pending Agent 1 published contract handoff

## 1. Context & Purpose
Agent 3 is operating independently on this system. As specified in `AGENTS.md` and `INTEGRATION_CONTRACTS.md`, Agent 1 owns the FastAPI voice backend, Gnani Prisma STT/Timbre TTS orchestration, LLM medical extraction, and deterministic danger-sign rules.

Until Agent 1 publishes the live repository artifacts (`shared-contracts/openapi.json`, `shared-contracts/voice-events.schema.json`, etc.), Agent 3 has established typed, versioned adapter interfaces and local contract fixtures in `shared-contracts/` and `src/lib/contracts/`.

## 2. Provisional Protocol Assumptions

### 2.1 Audio Transport & Encoding
- **Transport:** WebSocket at `ws://localhost:8000/ws/voice`
- **Audio Framing:** Binary WebSocket frames or Base64 JSON messages
- **Format:** Linear PCM 16-bit, Single-channel (Mono), 16,000 Hz sample rate
- **Chunk Size:** 20ms to 50ms (320 to 800 samples per chunk, 640 to 1600 bytes)
- **Adapter Isolation:** All audio encoding in the web client is encapsulated in `src/lib/voice/audio-worklet-recorder.ts` and `src/lib/voice/voice-client.ts`, allowing instant format switching if Agent 1 specifies Opus, WebM, or different sample rates.

### 2.2 WebSocket Message Protocol (`v1`)
Client-to-Server Messages:
1. `session_start`: `{ type: "session_start", session_id: string, language: "hi-IN"|"kn-IN"|"ta-IN"|"en-IN", beneficiary_id?: string, asha_worker_id: string }`
2. `audio_chunk`: Binary 16kHz PCM or `{ type: "audio_chunk", data: base64_pcm }`
3. `barge_in`: `{ type: "barge_in", session_id: string, timestamp: string }`
4. `voice_correction`: `{ type: "voice_correction", session_id: string, field_name: string, target_value?: string }`
5. `confirm_visit`: `{ type: "confirm_visit", session_id: string, draft_id: string }`
6. `session_end`: `{ type: "session_end", session_id: string }`

Server-to-Client Events:
1. `session_ready`: `{ type: "session_ready", session_id: string, assigned_agent: string }`
2. `stt_partial`: `{ type: "stt_partial", session_id: string, text: string, is_final: false }`
3. `stt_final`: `{ type: "stt_final", session_id: string, text: string, is_final: true, language: string }`
4. `assistant_text`: `{ type: "assistant_text", session_id: string, text: string, state: "speaking"|"clarifying"|"reading_back" }`
5. `tts_audio_chunk`: `{ type: "tts_audio_chunk", session_id: string, chunk_index: number, audio: base64_audio, format: "wav"|"mp3" }`
6. `tts_complete`: `{ type: "tts_complete", session_id: string }`
7. `interrupted`: `{ type: "interrupted", session_id: string }`
8. `visit_extracted`: `{ type: "visit_extracted", session_id: string, draft: VisitDraftPayload }`
9. `danger_alert`: `{ type: "danger_alert", alert: DangerAlertPayload }`
10. `error`: `{ type: "error", code: string, message: string, retryable: boolean }`

### 2.3 Danger Sign Escalation Contract
Danger alerts are safety-critical and independently fired:
- Danger alerts must NEVER wait for visit completion or saving.
- The web UI will immediately display an urgent modal/banner, play an audio warning, highlight the danger category, and queue the alert for PHC supervisor real-time monitoring.

## 3. Action Items for Live Integration
When Agent 1 provides live backend endpoints:
1. Verify endpoint URL: `NEXT_PUBLIC_VOICE_WS_URL` and `NEXT_PUBLIC_VOICE_API_BASE_URL`.
2. Validate incoming WebSocket event signatures against `src/lib/contracts/voice-events.ts`.
3. Test end-to-end barge-in with live Timbre TTS cancellation.
4. Execute manual verification using the test checklist in `AGENT3_WEB_FEATURE_PARITY.md`.
