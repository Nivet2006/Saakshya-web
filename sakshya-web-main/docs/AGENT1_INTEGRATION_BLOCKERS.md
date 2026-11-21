# Agent 1 Integration Status (`v1` Live Alignment)
**Date:** 2026-11-21  
**Status:** **RESOLVED — Aligned with Agent 1 Authoritative `v1` Contracts**

## 1. Completed Contract Alignment
All provisional WebSocket assumptions from initial scaffolding have been replaced with Agent 1's authoritative `v1` specifications copied into `shared-contracts/` (`openapi.json`, `visit.schema.json`, `danger-alert.schema.json`, `voice-events.schema.json`, `mock-events.jsonl`):

1. **Session Handshake:** `src/lib/voice/voice-client.ts` calls `POST /api/v1/sessions` via `src/lib/api/fastapi-client.ts`, reads `{ session_id, websocket_path, audio_format }`, and connects to `WS /ws/voice/{session_id}?language=...`.
2. **Audio Framing:** Browser microphone capture automatically resamples native browser audio rates (e.g., 44.1kHz / 48kHz) down to exact `16000 Hz` mono `pcm_s16le`, transmitting `512`-sample (`1024`-byte, `32 ms`) binary frames.
3. **Downlink Playback & Barge-In Flush:** `tts_audio_chunk` raw `pcm_s16le` payloads are decoded to `Float32Array` AudioBuffers scheduled via Web Audio `AudioBufferSourceNode`, filtered by monotonic `activeTurnId`, and flushed instantaneously on `barge_in` or `tts_cancelled`.
4. **Authoritative Visit & Danger-Sign Ownership:** Client-side fake regex extraction in `VoiceSessionModal` has been removed. All transcription (`partial_transcript`, `final_transcript`), field extraction (`visit_draft_updated`), clarification (`clarification_required`), voice corrections (`correction_applied`), read-back (`read_back_started`), and NHM danger-sign detection (`danger_alert`) originate solely from Agent 1.
5. **Two-Phase Persistence Handshake:** On `persistence_requested`, `useVoiceVisitSession` commits confirmed records via `syncManager.persistConfirmedVisitNow()` and replies with `POST /api/v1/sessions/{session_id}/persistence-ack` + WS `persistence_ack`, transitioning to `visit_committed` ONLY after persistence confirmation.
6. **Beneficiary Parity:** Synthetic beneficiaries `BEN-1042` through `BEN-1048` in `src/lib/mock-data.ts` and Supabase migration `20261121000003_align_v1_contracts.sql` match `backend/app/services/beneficiaries.py` and refresh dynamically via `GET /api/v1/beneficiaries`.

## 2. Environment Notes
- Ensure Agent 1's FastAPI backend is running on `http://localhost:8000` (`backend/.venv/bin/uvicorn app.main:app --app-dir backend --port 8000`).
- `.env.local` configures `NEXT_PUBLIC_VOICE_API_BASE_URL=http://localhost:8000` and `NEXT_PUBLIC_VOICE_WS_URL=ws://localhost:8000`.
- When `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` remain placeholders, the UI safely operates in local synthetic + IndexedDB mode with clear status indicators and zero false cloud-sync claims.
