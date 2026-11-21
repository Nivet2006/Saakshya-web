# Architecture — ASHA Voice Field Register (Agent 1 Backend)

## 1. High-Level Voice & Intelligence Architecture

```text
[Client: CLI Harness / Android App (Agent 2)]
        │  WebSocket: /ws/voice/{session_id}
        │  - Binary or base64 PCM_S16LE (16kHz, mono, 512 samples / 32ms)
        │  - JSON control & structured events (v1 contract)
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   FastAPI Async Voice Session Manager                │
├──────────────────────┬───────────────────────┬───────────────────────┤
│   Local ONNX Silero  │  Gnani Prisma v3.0    │  Deterministic Layer1 │
│   VAD + RMS Noise    │  Streaming STT WS     │  Danger-Sign Engine   │
│   Floor & Dual-Gate  │  (indic-auto, codemix,│  (runs on EVERY       │
│   Barge-In Detector  │   partials + finals,  │   partial & final)    │
│                      │   ASHA keywords)      │                       │
└──────────┬───────────┴───────────┬───────────┴───────────┬───────────┘
           │ barge_in              │ partial/final         │ DANGER HIT!
           │ (inc turn_id,         │ transcript            │ (hard interrupt,
           │  cancel TTS/LLM)      ▼                       │  bypass LLM)
           │            ┌──────────────────────┐           │
           │            │ Conversation Manager │           │
           │            │ & State Machine (P2) │           │
           │            │ + Extractor (P2)     │           │
           │            │ + LLM Adapter        │           │
           │            └──────────┬───────────┘           │
           │                       │ short contextual text │ urgent PHC
           │                       ▼                       ▼ referral text
           │            ┌──────────────────────────────────────────────┐
           └───────────►│  Gnani Timbre v3.0 Streaming TTS WS Adapter  │
                        │  (16kHz linear_pcm, WAV strip, int16 align,  │
                        │   socket reset on barge-in -> 0 stale audio) │
                        └──────────────────────┬───────────────────────┘
                                               │ PCM chunks tagged with turn_id
                                               ▼
                        [Client Playback + Immediate Flush on tts_cancelled]
```

## 2. Canonical Audio Format (Single Format Across Stack)
- **Encoding:** Signed 16-bit little-endian linear PCM (`pcm_s16le`)
- **Sample Rate:** `16000` Hz (natively supported by Silero VAD, Gnani Prisma v3.0, and Gnani Timbre v3.0 — zero server-side resampling required)
- **Channels:** `1` (mono)
- **Frame Size:** `512` samples = `1024` bytes = `32` ms

## 3. Core Subsystems & Modular Layout

```text
backend/
├── app/
│   ├── main.py                       # FastAPI entrypoint, lifespan, CORS, health
│   ├── core/
│   │   ├── config.py                 # pydantic-settings loading root .env
│   │   └── logging.py                # Structured logging with PHI redaction
│   ├── api/
│   │   ├── routes.py                 # REST endpoints (/health, /api/v1/sessions, /api/v1/beneficiaries)
│   │   └── ws.py                     # WebSocket /ws/voice/{session_id}
│   ├── voice/
│   │   ├── interfaces.py             # Replaceable STT, TTS, LLM, VAD protocols
│   │   ├── stt/
│   │   │   └── gnani_prisma.py       # Live Gnani Prisma v3.0 WS adapter (partials + finals)
│   │   ├── tts/
│   │   │   └── gnani_timbre.py       # Live Gnani Timbre v3.0 WS adapter (interruptible)
│   │   ├── vad/
│   │   │   └── silero_onnx.py        # Zero-torch ONNX Silero VAD + RMS dual-gate barge-in
│   │   ├── llm/
│   │   │   └── gemini_adapter.py     # Replaceable Gemini/Groq LLM adapter
│   │   └── orchestration/
│   │       └── session.py            # Asyncio turn coordinator, turn_id cancellation, reconnect
│   ├── danger_signs/                 # Phase 2 (Sub-agent 1A): official deterministic engine
│   ├── conversation/                 # Phase 2 (Sub-agent 1B): visit state machine & read-back
│   ├── extraction/                   # Phase 2 (Sub-agent 1C): typed visit field extraction
│   └── services/
│       └── beneficiaries.py          # Synthetic beneficiary directory (BEN-1001..BEN-1010)
├── cli_client.py                     # Minimal local mic / WAV replay / barge-in test harness
├── requirements.txt                  # Pinned compatible dependencies
└── tests/                            # Unit, mocked, and live-labelled test suites
```

## 4. Barge-In & Zero-Stale-Audio Guarantee
1. Every assistant response gets a monotonically increasing integer `turn_id`.
2. While the assistant is speaking (`assistant_speaking=True`), the local ONNX Silero VAD evaluates every 32 ms client audio frame with a **dual gate**:
   - Silero speech probability >= `BARGE_IN_VAD_THRESHOLD` (default `0.72`)
   - Frame RMS >= `max(min_rms_floor, 2.5 * adaptive_noise_floor_rms)`
   - Sustained for `BARGE_IN_MIN_SPEECH_MS` (default `300` ms, allowing 1 frame dip)
3. When triggered (or when a client sends an explicit `barge_in` control event):
   - Increment `active_turn_id`.
   - Cancel active LLM generation and TTS streaming tasks.
   - Reset/close the Gnani Timbre WebSocket so the upstream server immediately stops generating stale audio.
   - Emit `tts_cancelled` and `barge_in` events over WebSocket; client immediately flushes its speaker output buffer.
   - Any late audio chunks with `chunk.turn_id != active_turn_id` are dropped silently.
   - The interrupting utterance continues streaming into Prisma v3.0 (including buffered pre-roll audio) and triggers the next turn with updated conversation context.

## 5. Safety & Privacy Design
- All beneficiaries and fixtures are 100% synthetic (`BEN-1001`..`BEN-1010`).
- `LOG_REDACT_PHI=true` by default: logs record event types, latencies, session IDs, and character lengths without dumping raw health speech.
- No secrets in source code, docs, or contracts; all credentials loaded via `backend/app/core/config.py` from root `.env`.

