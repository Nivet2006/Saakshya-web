# Audio Pipeline, VAD, and Pipecat Compatibility Notes

**Scope:** Local macOS audio capture/playback, PyPI package compatibility (Python 3.12, Apple Silicon `arm64`), Pipecat vs. custom `asyncio` WebSocket architecture evaluation, and Silero VAD + barge-in tuning for noisy household/street environments.

---

## 1. Environment & Audio Hardware Observed on This Machine

- **Host:** macOS `27.2` (`Build 26B123`), `arm64` (Apple Silicon)
- **Python / Package Tooling:** `/opt/anaconda3/bin/python3` (`Python 3.12.7`), `uv` (`/Users/shriii/.local/bin/uv`), Homebrew (`/opt/homebrew/bin/brew`)
- **System PortAudio:** `portaudio` is **not** installed via Homebrew (`brew list portaudio` returned not installed).
- **Audio Devices (`system_profiler SPAudioDataType`):**
  - `SHRIRAM VS’s AirPods Pro` (Bluetooth): **Default Input** (`24000` Hz, 1 ch) & **Default Output** (`48000` Hz, 2 ch)
  - `MacBook Air Microphone` (Built-in): `44100` Hz, 1 ch
  - `MacBook Air Speakers` (Built-in): **Default System Output** (`44100` Hz, 2 ch)
  - `iPhone Microphone` (Continuity): `48000` Hz, 1 ch

### macOS Audio Capture Feasibility & Pitfalls

1. **`sounddevice` works without Homebrew `portaudio`:**
   - `sounddevice==0.5.6` publishes a universal2 macOS wheel (`sounddevice-0.5.6-py3-none-macosx_10_6_x86_64.macosx_10_6_universal2.whl`) that bundles `libportaudio.dylib`. No `brew install portaudio` is required.
   - By contrast, **`pyaudio==0.2.14`** (pulled by `pipecat-ai[local]`) has **no wheels on PyPI** (source distribution only) and fails to build on macOS without `brew install portaudio` and C build headers.
2. **Bluetooth AirPods HFP (Hands-Free Profile) Caveat:**
   - Opening a microphone `InputStream` on AirPods Pro forces macOS Bluetooth from A2DP (`48000` Hz stereo output) into HFP (`16000` or `24000` Hz mono). Opening an `OutputStream` at `48000` Hz concurrently with HFP mic capture can fail with sample-rate incompatibility or audio breakup.
   - **Recommended local CLI capture strategy:**
     - Query `sd.query_devices()` at startup and open streams at each device's supported native sample rate (or allow `--input-device` / `--output-device` CLI flags).
     - Resample capture/playback in software using **`soxr==1.1.0`** (`arm64` wheel available) to the canonical pipeline format (**16,000 Hz, mono, 16-bit signed little-endian PCM**).
     - For local barge-in testing without acoustic echo cancellation (AEC), use **MacBook Air Microphone + wired headphones**, or **AirPods Output + MacBook Air Microphone**, so assistant TTS output does not loop back into the mic and trigger self-barge-in.

---

## 2. PyPI Package Compatibility Matrix (Python 3.12 / macOS `arm64`)

All metadata below was verified against PyPI JSON APIs and `uv pip compile - --python-version 3.12` dry-run resolution on this host without modifying the global Anaconda environment.

| Package | Latest PyPI | Python Req | macOS `arm64` Wheel? | Key Dependency & Compatibility Notes |
| :--- | :--- | :--- | :--- | :--- |
| `pipecat-ai` | `1.16.0` | `>=3.11` | `py3-none-any` | Base deps already include `onnxruntime<2,>=1.24.3`, `numpy<3,>=1.26.4`, `pipecat-resampler>=0.2.0`, `loudness>=0.2.0`, `soundfile~=0.13.1`, `websockets>=13.1`, `aiohttp<4,>=3.14.4`. `silero` extra adds no extra packages (`[]`). **`local` extra pulls `pyaudio~=0.2.14` (avoid on macOS without brew portaudio).** `google` extra pulls `google-genai<4,>=3.2.0` plus `google-cloud-speech`, `google-cloud-texttospeech`, `grpcio`. |
| `pipecat-gnani` | `0.6.1` | `>=3.11` | `py3-none-any` | Official Gnani Pipecat integration (`GnaniSTTService`, `GnaniTTSService`). Requires `pipecat-ai>=1.5.0,<2.0`, `gnani-vachana>=0.9.0,<1.0`, **`websockets>=12.0,<16.0`** (caps `websockets` below 16.0; resolves cleanly with `websockets==15.0.1`). |
| `gnani-vachana` | `0.11.0` | `>=3.9` | `py3-none-any` | Pure Python (`requests>=2.28.0`, `websockets>=12.0`). Can be used directly even without Pipecat. |
| `silero-vad` | `6.2.3` | `>=3.8` | `py3-none-any` | **Caveat:** Even with the `[onnx-cpu]` extra, `silero-vad` unconditionally requires **`torch>=1.12.0`**. If you want a torch-free backend venv, load `silero_vad.onnx` directly via `onnxruntime` + `numpy` (see Section 4). |
| `onnxruntime` | `1.32.0` | `>=3.11` | `macosx_14_0_arm64` | Clean native Apple Silicon wheel (`cp312-cp312-macosx_14_0_arm64.whl`). Note: cross-targeting older macOS tags like `macosx_13_0_arm64` fails for `>=1.24.3`; host macOS 27.2 resolves `1.32.0` cleanly. |
| `sounddevice` | `0.5.6` | `>=3.7` | `universal2` | Bundles PortAudio `.dylib` in wheel; `cffi` + optional `numpy`. |
| `webrtcvad` | `2.0.10` | unspecified | **None (sdist only)** | No binary wheels; requires compiling C code and fails easily on Python 3.12+ / Apple Silicon. |
| `webrtcvad-wheels` | `2.0.14.post1` | `>=3.10` | `macosx_11_0_arm64` | Drop-in prebuilt wheel (`cp312-cp312-macosx_11_0_arm64.whl`) if fallback GMM VAD is ever desired. (Silero ONNX is much more noise-resilient.) |
| `soxr` | `1.1.0` | `>=3.9` | `macosx_11_0_arm64` | Fast, high-quality audio resampling (`cp312-abi3-macosx_11_0_arm64.whl`). |
| `fastapi` | `0.165.0` | `>=3.11` | `py3-none-any` | Already `0.104.1` in base Anaconda; pin `>=0.115.6` in isolated `uv` venv. |
| `uvicorn` | `0.54.0` | `>=3.10` | `py3-none-any` | `[standard]` adds `uvloop`, `httptools`, `websockets>=13.0`, `watchfiles`. |
| `websockets` | `17.4` | `>=3.11` | `macosx_11_0_arm64` | Use `>=13.1,<16.0` if `pipecat-gnani` is installed (`15.0.1` resolves cleanly). |
| `google-genai` | `3.6.1` | `>=3.11` | `py3-none-any` | Cleanly resolves with both stacks (`anyio`, `httpx2`, `pydantic`, `websockets<18.0,>=13.0.0`). |
| `groq` | `1.7.0` | `>=3.10` | `py3-none-any` | Cleanly resolves with both stacks (`httpx`, `anyio`, `pydantic`). |
| `pydantic-settings` | `2.16.3` | `>=3.11` | `py3-none-any` | Pulls `python-dotenv>=1.2.2`, `pydantic>=2.7.0`. |
| `pyrnnoise` | `0.4.6` | unspecified | `macosx_26_0_universal2` | Optional RNNoise denoiser (`audiolab`, `matplotlib`, `numpy`, `tqdm` — heavy extras for a simple denoiser; only add if Silero tuning alone is insufficient). |

### Dry-Run Dependency Resolution Comparison (`uv pip compile`)

1. **Lean Custom `asyncio` Stack:** **50 resolved packages** (`fastapi==0.165.0`, `uvicorn==0.54.0`, `websockets==15.0.1`, `gnani-vachana==0.11.0`, `onnxruntime==1.32.0`, `numpy==2.5.5`, `sounddevice==0.5.6`, `soxr==1.1.0`, `webrtcvad-wheels==2.0.14.post1`, `google-genai==3.6.1`, `groq==1.7.0`, `pydantic-settings==2.16.3`). Zero `torch`, zero `pyaudio`, zero `grpcio` bloat.
2. **Pipecat Stack** (`pipecat-ai[google,groq,silero,websocket,runner]` + `pipecat-gnani` + `sounddevice` + `soxr`): **111 resolved packages** (adds `pipecat-ai==1.16.0`, `pipecat-gnani==0.6.1`, `pipecat-resampler==0.2.0`, `loudness==0.2.0`, `soundfile==0.13.1`, `openai`, `google-cloud-speech`, `google-cloud-texttospeech`, `grpcio`, `opentelemetry-*`, `sentry-sdk`, `typer`).

---

## 3. Architecture Evaluation: Pipecat vs. Lean Custom `asyncio` WebSocket Pipeline

### How Pipecat (`1.16.0`) Works
- **Frame-based linear pipeline:** Audio enters via a `Transport` (`FastAPIWebsocketTransport` / `WebsocketServerTransport`) as `InputAudioRawFrame` -> `SileroVADAnalyzer` (`VADParams`) -> `STTService` (`GnaniSTTService`) -> `LLMUserAggregator` (`UserTurnStrategies`) -> `LLMService` -> `InterruptibleTTSService` (`GnaniTTSService`) -> `Transport` output.
- **Barge-in mechanism:** `VADUserTurnStartStrategy(enable_interruptions=True)` emits `UserStartedSpeakingFrame` and broadcasts an `InterruptionFrame` (a high-priority `SystemFrame` that bypasses normal queues) upstream and downstream, cancelling in-flight LLM generation, clearing `InterruptibleTTSService` buffers, and flushing the transport's outbound audio queue.

### Why Pipecat Creates Friction for ASHA Voice Field Register

1. **Integration Contract Mismatch (`INTEGRATION_CONTRACTS.md`):**
   - Agent 1 must expose a **versioned JSON + audio WebSocket protocol** (`shared-contracts/voice-events.schema.json`) consumed by Agent 2 (Android/Kotlin) and Agent 3 (Web) with explicit events: `partial_transcript`, `final_transcript`, `assistant_text`, `tts_audio_chunk`, `tts_complete`, `barge_in`, `tts_cancelled`, `visit_draft_updated`, `danger_alert`, `session_state`.
   - Pipecat's `FastAPIWebsocketTransport` defaults to `ProtobufFrameSerializer`. Supporting Agent 2's JSON envelope requires writing a custom `FrameSerializer` *plus* custom `Frame` subclasses for visit drafts and danger alerts.
2. **Deterministic Safety-Critical Control Flow (Phase 2):**
   - Our core pipeline is **not** a standard open-ended LLM chatbot. Verified danger signs must deterministically trigger **immediate speech interruption**, emit `danger_alert`, and speak an urgent PHC referral **without waiting for or trusting an LLM turn**. Read-back, field-level patch corrections, and explicit confirmation require a deterministic state machine.
   - Bending Pipecat's `LLMContextAggregatorPair` + `LLMService` around deterministic pre-LLM intercepts and state-machine read-backs requires custom `FrameProcessor`s and careful management of Pipecat 1.x frame ordering (`SystemFrame` vs `DataFrame` vs `ControlFrame`).
3. **Dual-VAD Conflict Risk:**
   - `GnaniSTTService` (Prisma v3.0 WebSocket) already performs server-side VAD/endpointing, while Pipecat runs `SileroVADAnalyzer` locally. Conflicting endpointing timers can cause premature turn submission or missed interruptions unless turn strategies are heavily customized.

### Recommendation

**Recommended Primary Architecture: Lean Custom `asyncio` + FastAPI WebSocket Pipeline**

- **Why:**
  - Directly implements the exact FastAPI `/ws/voice/{session_id}` JSON + PCM WebSocket contract shared by both the local `sounddevice` CLI harness (Milestone 1) and Android (Agent 2).
  - Keeps **barge-in, deterministic danger-sign interruption, and the visit state machine** explicit, debuggable, and unit-testable with zero framework black-box ordering surprises.
  - Uses **`onnxruntime`** directly on `silero_vad.onnx` (no `torch` needed) and thin async adapters for Gnani Prisma v3.0 / Timbre v3.0 (referencing or wrapping `gnani-vachana==0.11.0` or raw `websockets` per verified Gnani docs).
  - Smaller, faster dependency footprint (50 packages vs. 111) and zero `pyaudio` / PortAudio build failures on macOS.
- **When to reconsider Pipecat:** Only if Milestone 1 needs pre-built `GnaniSTTService`/`GnaniTTSService` (`pipecat-gnani==0.6.1`) immediately on Hour 1 *and* you accept implementing a custom `AndroidJsonFrameSerializer` plus custom `FrameProcessor`s for danger-sign bypass and state transitions (never using `pipecat-ai[local]`).

---

## 4. Recommended VAD, Noise Resilience & Barge-In Architecture

### A. Standalone `SileroVAD` via `onnxruntime` (No PyTorch)

Silero VAD v6 (`silero_vad.onnx`, ~2 MB) runs directly on CPU via `onnxruntime` (`CPUExecutionProvider`):
- **Input chunk:** `16,000` Hz mono `float32` normalized to `[-1.0, 1.0]`, shape `[1, 512]` (**32 ms** per frame — matches Gnani streaming STT's 512-sample / 1,024-byte `int16` frame cadence).
- **State tensor:** Recurrent LSTM state `state` of shape `[2, 1, 128]` (`float32`), initialized to zeros per session and reset on stream restart.
- **Sample rate tensor:** `np.array([16000], dtype=np.int64)`.
- **Outputs:** `(speech_prob, new_state)`.

### B. Silero VAD Tuning for Noisy Household / Street Environments

ASHA workers operate in homes with family chatter, TV/radio, crying children, kitchen clatter, and street traffic. Default VAD settings (`threshold=0.5`, `min_speech_duration_ms=100`) cause constant false barge-ins.

| Parameter | Typical Default | Recommended ASHA Field Starting Point | Rationale |
| :--- | :--- | :--- | :--- |
| `threshold` (speech start probability) | `0.50` | **`0.65`** (range `0.60–0.70`) | Rejects stationary fans/traffic and low-confidence background babble without silencing soft-spoken workers (`>0.80` drops quiet speakers). |
| `neg_threshold` (hysteresis exit) | `threshold - 0.15` | **`0.45`** | Prevents rapid speech/silence chattering during mid-word consonant dips. |
| `min_speech_duration_ms` (normal listening) | `100 ms` | **`192–256 ms`** (6–8 frames of 32 ms) | Filters transient clatter, coughs, door slams, and mic bumps. |
| `min_silence_duration_ms` (end-of-turn) | `100–200 ms` | **`450–600 ms`** (for read-back/notes; or align with Prisma final event) | Prevents chopping natural mid-sentence pauses or Indic/English code-switching hesitations. |
| `speech_pad_ms` (pre-roll ring buffer) | `30–100 ms` | **`160–224 ms`** (5–7 frames) | Preserves initial soft consonants (e.g., *s, f, p, h*) when forwarding speech to Prisma STT after VAD triggers. |

### C. Dual-Gate Barge-In (Preventing Household Chatter from Interrupting TTS)

When the assistant is **idle/listening**, keep the normal threshold (`0.65`, `192 ms`) and stream pre-roll + speech continuously to Prisma STT.
When the assistant is **actively speaking (TTS playing)**:

1. **Sustained Speech + Energy Dual Gate:**
   - Require **both** Silero speech probability `>= 0.72` **and** frame RMS energy above an adaptive noise-floor gate (e.g., `frame_rms >= max(min_rms_floor, noise_floor_rms * 2.5)`) sustained for **`256–320 ms`** (8–10 consecutive 32 ms frames, allowing at most 1 dip frame).
   - *Why:* Distant background TV/chatter often triggers Silero's vocal classifier at low RMS, while loud kitchen clatter spikes RMS without Silero speech probability. Requiring *both* sustained Silero probability and elevated RMS relative to the tracked background noise floor prevents false interruptions while keeping genuine worker barge-in responsive (~300 ms).
   - **Noise-floor tracking:** Continuously update an exponential moving average (EMA) of `frame_rms` only during confirmed non-speech frames (`prob < 0.30`).
2. **Pre-Roll Preservation on Barge-In:**
   - Keep a `320 ms` (10-frame) circular PCM ring buffer. The instant barge-in fires, flush the ring buffer + ongoing mic frames into a fresh Prisma STT stream so the beginning of the interrupting utterance (e.g., *"Nahi, weight 2.8..."*) is never clipped.
3. **Deterministic Generation-Token (`turn_id`) Cancellation:**
   - Assign a monotonically increasing `turn_id` to every assistant response/TTS stream.
   - On barge-in trigger:
     1. Increment `session.active_turn_id`.
     2. Cancel `active_llm_task` and `active_tts_task` (`asyncio.Task.cancel()`) and close/abort the active Timbre TTS WebSocket stream.
     3. Drain `outbound_audio_queue` immediately and drop any queued chunk whose `turn_id != session.active_turn_id`.
     4. Send `{ "event": "tts_cancelled", "turn_id": old_turn_id, "reason": "barge_in" }` immediately to the client so the local CLI (`sounddevice`) or Android (`AudioTrack.flush()`) clears its local playback buffer within milliseconds—guaranteeing **zero stale audio** plays after interruption.
4. **Safety Rule for Danger-Sign Escalation:**
   - While speaking an urgent danger-sign referral, keep barge-in active (workers must still be able to confirm or add symptoms), but **never clear `danger_sign_flagged=true` or the emitted `danger_alert`** on interruption.
