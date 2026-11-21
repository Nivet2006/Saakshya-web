# Gnani Prisma v3.0 & Timbre v3.0 Integration Reference

> Verified against official installed packages (`gnani-vachana==0.11.0`, `pipecat-gnani==0.6.1`, `pipecat-ai==1.16.0`), official Gnani documentation (`docs.gnani.ai`), and live WebSocket handshakes/roundtrips on `api.vachana.ai` on 2026-11-21.

---

## 1. Authentication & Environment Variables

All Gnani services authenticate via the HTTP/WebSocket upgrade header `X-API-Key-ID` (case-insensitive; `gnani-vachana` sends `x-api-key-id` for STT WS and `X-API-Key-ID` for TTS WS/REST).

- Secret key variable: `GNANI_API_KEY` (loaded from root `.env`; never hardcoded or logged).
- Optional URL overrides: `GNANI_STT_WS_URL`, `GNANI_TTS_WS_URL` (defaults to official production URLs below when empty).
- Model variables: `GNANI_STT_MODEL=prisma-v3.0`, `GNANI_TTS_MODEL=timbre-v3.0`.

---

## 2. Gnani Prisma v3.0 — Realtime Streaming STT

### Endpoint & Handshake
- **WebSocket URL:** `wss://api.vachana.ai/stt/v3/stream`
- **REST URL (fallback/short clips <= 30s):** `https://api.vachana.ai/stt/v3`
- **Handshake headers (verified live):**
  - `x-api-key-id`: `<GNANI_API_KEY>`
  - `x-model`: `prisma-v3.0` (required; server defaults to `prisma-v2.5` if omitted)
  - `lang_code`: `indic-auto` (auto-detect per utterance, `prisma-v3.0` only) or BCP-47 code (`hi-IN`, `en-IN`, `kn-IN`, `ta-IN`, `te-IN`, `mr-IN`, `bn-IN`, `gu-IN`, `ml-IN`, `pa-IN`)
  - `x-language-candidates`: comma-separated 2–4 BCP-47 hints (only valid with `lang_code=indic-auto` and `prisma-v3.0`), e.g. `hi-IN,en-IN,kn-IN,ta-IN`
  - `x-format`: `transcribe` (primary default — enables Inverse Text Normalization (ITN) so spoken numbers, decimals, dates, and IDs normalize to digits; `prisma-v3.0` also supports `verbatim`, `codemix`, `transliterate`). Note: `codemix` keeps numbers as spoken words and is used only as an optional secondary recognition fallback (`POST /stt/v3`).
  - `x-sample-rate`: `16000` (supported streaming rates: `8000`, `16000`, `44100`, `48000`)
  - `x-partials`: `true` (**live-verified**: enables `partial_transcript` events every `partial_interval_ms=450` ms!)
  - `x-keywords`: JSON-encoded ASCII-escaped list of up to 200 focused clinical/measurement hint phrases plus the active session beneficiary (`ASHA_CORE_KEYWORDS` + active beneficiary name/ID)
  - `x-speaker-names`: JSON-encoded ASCII-escaped list of 1–4 active beneficiary/speaker names (fixed for the WS connection; also passed on REST secondary recognition)
  - `x-previous-text`: ASCII-safe rolling prior context (up to last 600 chars)
  - `x-topic`: concise ASHA home-visit domain description (up to 1600 chars)
  - Mid-session WebSocket `{"type": "update_settings", "format": ..., "language_code": ...}` is supported for `format`/`language_code` switching (returns `settings_updated`); context fields (`keywords`, `speaker_names`, `previous_text`, `topic`) are fixed per WS handshake and refreshed on reconnect / REST secondary recognition.
  - Optional server-side VAD tuning headers (from `gnani.stt.client.STREAM_TUNING_OPTIONS`):
    - `x-vad-threshold`: `0.0`–`1.0` (server default `0.7`)
    - `x-min-silence-ms`: `100`–`2000` (server default `500`)
    - `x-min-speech-ms`: `50`–`2000` (server default `100`)
    - `x-min-segment-ms`: `100`–`1000` (server default `120`)
    - `x-max-speech-s`: `5.0`–`120.0`
    - `x-idle-timeout-sec`: `5`–`900` (server default `60`; max session length 15 min)

### Audio Input Format
- Raw binary WebSocket frames: **16-bit signed little-endian mono PCM (`pcm_s16le`)**.
- Recommended frame size at 16 kHz: **512 samples = 1024 bytes = 32 ms** per frame.

### Server-to-Client Events (Verified Live)
When `x-partials: true` is sent, live `wss://api.vachana.ai/stt/v3/stream` emits JSON text frames:
1. `{"type": "connected", "message": "STT service ready — VAD service connected", "request_id": "...", "config": {"sample_rate": 16000, "chunk_size": 512, "partials_enabled": true, "partial_interval_ms": 450, "partial_max_window_s": 15.0, "language_code": "indic-auto", "format": "codemix", "language_candidates": ["hi", "en"]}}`
2. `{"type": "speech_start", "utterance_id": "u...", "t_ms": 0, "timestamp": "..."}`
3. `{"type": "partial_transcript", "utterance_id": "u...", "seq": 1, "is_final": false, "text": "...", "stable_text": "...", "volatile_text": "...", "timestamp": "..."}`
4. `{"type": "speech_end", "utterance_id": "u...", "t_ms": 3616, "audio_ms": 3616, "timestamp": "..."}`
5. `{"type": "final_transcript", "text": "...", "audio_duration_ms": 3616.0, "segment_id": "...", "segment_index": 1, "utterance_id": "u...", "is_final": true, "latency": 157, "detected_language_code": "en-IN", "timestamp": "..."}`
   *(Note: legacy / non-partial sessions may emit `"type": "transcript"` instead of `"final_transcript"`; our adapter handles both.)*
6. `{"type": "error", "message": "..."}`

### Live Verification Observation (2026-11-21)
- Connected in **0.92s**.
- Synthesized Hinglish utterance streamed in 1024-byte chunks produced live `speech_start` -> 9 `partial_transcript` events -> `speech_end` -> 2 `final_transcript` events with **146–157 ms** server latency.
- Observed realistic code-mixed ASR artifact (`"ववेट is fifty two kilo, TT injection pending hai."`), confirming the need for script/ASR normalization in Layer-1 danger-sign detection and healthcare extraction.

---

## 3. Gnani Timbre v3.0 — Realtime Streaming TTS

### Endpoints
- **Realtime WebSocket (primary, lowest latency + interruption support):** `wss://api.vachana.ai/api/v1/tts`
- **SSE Streaming:** `https://api.vachana.ai/api/v1/tts/sse`
- **REST Batch:** `https://api.vachana.ai/api/v1/tts/inference`

### Handshake & Request Payload (Verified Live)
- **WS Headers:** `X-API-Key-ID: <GNANI_API_KEY>`, `Content-Type: application/json`, optional `X-API-Request-ID`.
- **Client JSON Request per utterance:**
  ```json
  {
    "text": "नमस्ते, आज की विजिट शुरू करें।",
    "voice": "Shivani",
    "model": "timbre-v3.0",
    "language": "hi-IN",
    "audio_config": {
      "sample_rate": 16000,
      "encoding": "linear_pcm",
      "num_channels": 1,
      "sample_width": 2,
      "container": "wav"
    }
  }
  ```
- **Supported Languages (`SUPPORTED_TTS_LANGUAGES`):** `auto`, `hi-IN`, `en-IN`, `ta-IN`, `te-IN`, `kn-IN`, `ml-IN`, `mr-IN`, `bn-IN`, `gu-IN`, `pa-IN`.
- **Voices (`TIMBRE_V30_VOICES`, 34 voices, all multilingual across all 10 languages):** `Shivani` (default feminine for ASHA assistant), `Lakshmi`, `Avinash`, `Kalpana`, `Chetana`, `Vasudha`, `Riyaa`, `Tarika`, `Sneha`, `Swathi`, `Shruthi`, `Shubham`, `Prakash`, `Devansh`, `Yashraj`, etc. *(Do not use `timbre-v2.5` voices like `Pranav`/`Nalini` with `timbre-v3.0`.)*
- **Speed:** `0.8` to `1.2` for `timbre-v3.0` (rounded to `0.8`, `1.0`, `1.2`; omit to use voice default).
- **Audio Config:** `sample_rate` in `(8000, 16000, 22050, 24000, 44100, 48000)`, `encoding="linear_pcm"`, `container="wav"` (strip 44-byte RIFF/WAV header on first chunk and align to 2-byte int16 sample boundaries).

### Server-to-Client Messages & Barge-In Cancellation
- Audio arrives either as binary frames or JSON `{"type": "audio", "data": {"audio": "<base64>"}}`.
- Each request terminates with two `complete` frames:
  1. `{"type": "complete", "data": {"is_final": true, "audio": "..."}}` (final audio chunk — ends request)
  2. `{"type": "complete", "message": "Streaming completed"}` (acknowledgement with no `data` dict — ignore)
- **Cancellation on Barge-In:** Following `pipecat-gnani`'s `GnaniTTSService(InterruptibleTTSService)` design, cancel in-flight synthesis immediately by closing the active Timbre WebSocket connection and opening a fresh connection (or reconnecting lazily/eagerly), discarding any buffered chunks belonging to the superseded `turn_id`.

### Live Verification Observation (2026-11-21)
- WS handshake opened in **1.68s**; **TTFB = 0.27s**; full 6.80s Hinglish audio streamed in **1.33s** across 64 chunks (217,644 bytes).

---

## 4. `pipecat-gnani` Compatibility Assessment

- Official package `pipecat-gnani==0.6.1` (requiring `gnani-vachana>=0.9.0,<1.0` and `pipecat-ai>=1.5.0,<2.0`) installs and resolves cleanly on Python 3.12.7.
- **Critical Gap Discovered Live:** `pipecat_gnani.stt.GnaniSTTService` (0.6.1) only inspects `msg_type == "transcript"` and does not send `x-partials: true` or handle `partial_transcript` / `final_transcript` events emitted by `prisma-v3.0` when partials are enabled.
- Therefore, Agent 1 implements clean, direct async WebSocket adapters (`GnaniPrismaSTTAdapter` and `GnaniTimbreTTSAdapter`) based on the verified `gnani-vachana` wire protocol, while reusing `pipecat`'s bundled ONNX `silero_vad.onnx` model for noise-resilient local VAD and barge-in gating.

---

## 5. Numeric, Context & Streaming Accuracy Findings (Verified Live)

### Contextual Headers: WebSocket Handshake vs REST (`/stt/v3`)
- Live handshake inspection (`wss://api.vachana.ai/stt/v3/stream`) confirmed that `connected.config` echoes `format`, `language_code`, `language_candidates`, and `bias_word_count` (derived from `x-keywords`), while `speaker_names`, `previous_text`, and `topic` are not echoed in `connected.config`.
- Mid-session `{"type": "update_settings", "format": ..., "language_code": ...}` ignores `keywords`, `speaker_names`, and `previous_text` (`bias_word_count` remains unchanged).
- Therefore, `GnaniPrismaSTTAdapter.reconnect_with_context()` closes and reopens the WebSocket cleanly whenever active beneficiary identity changes mid-session, and `GnaniRestSecondaryRecognizer` always sends full `keywords`, `speaker_names`, `previous_text`, and `topic` via `/stt/v3`.
- A/B probe on `B04_compound_kg_grams` (`"Meena Selvam immunisation visit..."`) showed `with_context` improved sentence segmentation and punctuation on both REST and WS compared to `without_context`.

### Expanded 20-Case Live Benchmark (`backend/scripts/benchmark_prisma_numeric.py`)
Evaluated on synthetic Gnani Timbre v3.0 speech covering clean decimals, grams/kilograms, dates, spoken IDs, regional phrasing (`en-IN`, `hi-IN`, `kn-IN`, `mr-IN`, `ta-IN`), Hinglish (`"do point aath"`, `"10 days baad"`), Marathi (`"अडीच किलो"`), 14 dB broadband noise, 8 dB non-stationary street babble, 9 dB low-gain clipped mic audio (`gain=0.22`), and adversarial ambiguous/conflicting inputs:

- **REST `format="transcribe"` (primary, avg 751.1 ms):**
  - Numeric exact-match accuracy: **90.0%** (18/20)
  - Decimal accuracy: **88.2%** (15/17)
  - Unit recognition accuracy: **88.2%** (15/17)
  - Date accuracy: **100.0%** (8/8)
  - Beneficiary ID accuracy: **90.0%** (9/10)
  - Numeric omission rate: **0.0%** (0/20)
  - Incorrect numeric confirmation rate: **10.0%** (2/20)
- **REST `format="codemix"` (avg 690.5 ms):**
  - Numeric exact-match accuracy: **85.0%** (17/20), Decimal **82.4%** (14/17), Unit **88.2%** (15/17), Date **100.0%** (8/8), Beneficiary ID **90.0%** (9/10), Numeric omission rate **5.0%** (dropped `11.4` from `"HB 11.4"` under 8 dB street babble), Incorrect confirmation **10.0%**.
- **Streaming WebSocket `format="transcribe"` (avg 6908.9 ms incl. realtime streaming + endpoint silence):**
  - Numeric exact-match accuracy: **90.0%** (18/20), Decimal **88.2%**, Unit **88.2%**, Date **100.0%**, Beneficiary ID **90.0%**, Numeric omission **5.0%** (`B16_low_gain_babble_9db` dropped below server VAD at `gain=0.22`), Incorrect confirmation **5.0%** (1/20).
- **Per-language breakdown (REST `transcribe`):** `en-IN` (n=9) 100.0% across all metrics; `kn-IN` (n=3) 100.0%; `mr-IN` (n=1) 100.0%; `hi-IN` (n=6) 80.0% numeric exact-match (failed on `B16_low_gain_babble_9db`); `ta-IN` (n=1) 0.0% numeric weight exact-match due to Gnani Tamil sandhi merging `"எடை ஆறு, புள்ளி ஐந்து"` into `"எடையாறு, புள்ளி 5"`.
- **Secondary recognition (`GnaniRestSecondaryRecognizer`):** triggered only on the **2/20 (10%)** ambiguous/conflicting adversarial utterances (`B18`, `B19`), with **526.5 ms** and **913.7 ms** added latency and **0 ms** overhead on the remaining 18 utterances.


