import {
  fastApiClient,
  FastApiError,
  getVoiceApiBaseUrl,
  getVoiceWsBaseUrl,
} from '@/lib/api/fastapi-client';
import type {
  BackendSessionStateV1,
  ClarificationCandidateV1,
  ClarificationReasonV1,
  ClientWebSocketEventV1,
  DangerAlertV1,
  ServerBargeInEventV1,
  ServerClarificationRequiredEventV1,
  ServerCorrectionAppliedEventV1,
  ServerDangerAlertEventV1,
  ServerErrorEventV1,
  ServerFinalTranscriptEventV1,
  ServerPartialTranscriptEventV1,
  ServerPersistenceRejectedEventV1,
  ServerPersistenceRequestedEventV1,
  ServerReadBackStartedEventV1,
  ServerSessionReadyEventV1,
  ServerVisitCommittedEventV1,
  ServerVisitConfirmedEventV1,
  ServerVisitDraftUpdatedEventV1,
  VisitRecordV1,
} from '@/lib/contracts/v1';
import type { LanguageCode, VoiceInteractionState } from '@/types';

const TARGET_SAMPLE_RATE = 16000;
const TARGET_FRAME_SAMPLES = 512; // 32ms @ 16kHz = 1024 bytes pcm_s16le

export interface AudioInputDeviceInfo {
  deviceId: string;
  label: string;
}

export interface AudioDiagnostics {
  captureSampleRate: number;
  channelCount: number;
  echoCancellation: boolean;
  noiseSuppression: boolean;
  autoGainControl: boolean;
  usedAudioWorklet: boolean;
  framesSent: number;
  bytesSent: number;
  droppedFrames: number;
  clippedSamples: number;
  lastRms: number;
  peakRms?: number;
  ambientNoiseRms: number;
  staleChunksDiscarded: number;
  localBargeInCount: number;
  localPlaybackStopMs: number | null;
  serverFramesReceived?: number;
  serverBytesReceived?: number;
  serverAudioRms?: number;
  sttConnected?: boolean;
}

export interface VoiceLatencyMetrics {
  lastTtfaMs: number | null;
  p50TtfaMs: number | null;
  p95TtfaMs: number | null;
  avgTtfaMs: number | null;
  greetingLatencyMs: number | null;
  lastSttFinalizationMs: number | null;
  lastTtsFirstChunkMs: number | null;
  turnCount: number;
}

function computePercentile(sorted: number[], pct: number): number | null {
  if (sorted.length === 0) return null;
  if (sorted.length === 1) return Math.round(sorted[0]);
  const rank = (pct / 100) * (sorted.length - 1);
  const low = Math.floor(rank);
  const high = Math.ceil(rank);
  if (low === high) return Math.round(sorted[low]);
  const weight = rank - low;
  return Math.round(sorted[low] * (1 - weight) + sorted[high] * weight);
}

export interface VoiceClientCallbacks {
  onStateChange: (state: VoiceInteractionState, backendState?: BackendSessionStateV1) => void;
  onSessionReady?: (event: ServerSessionReadyEventV1) => void;
  onConnectionChange?: (connected: boolean, reconnecting?: boolean) => void;
  onSpeechActivity?: (speaking: boolean, utteranceId: string | null) => void;
  onPartialTranscript: (event: ServerPartialTranscriptEventV1) => void;
  onFinalTranscript: (event: ServerFinalTranscriptEventV1) => void;
  onAssistantResponse: (text: string, turnId: number, isDangerEscalation: boolean, language: string) => void;
  onTtsPlaybackChange?: (isPlaying: boolean, isPaused: boolean, turnId: number) => void;
  onBargeIn?: (event: ServerBargeInEventV1) => void;
  onAudioLevel: (level: number, bands?: number[]) => void;
  onVisitDraftUpdated: (event: ServerVisitDraftUpdatedEventV1) => void;
  onClarificationRequired?: (event: ServerClarificationRequiredEventV1) => void;
  onReadBackStarted?: (event: ServerReadBackStartedEventV1) => void;
  onCorrectionApplied?: (event: ServerCorrectionAppliedEventV1) => void;
  onVisitConfirmed?: (event: ServerVisitConfirmedEventV1) => void;
  onPersistenceRequested?: (event: ServerPersistenceRequestedEventV1) => void;
  onVisitCommitted?: (event: ServerVisitCommittedEventV1) => void;
  onPersistenceRejected?: (event: ServerPersistenceRejectedEventV1) => void;
  onDangerAlert: (event: ServerDangerAlertEventV1) => void;
  onLatencyUpdate?: (metrics: VoiceLatencyMetrics) => void;
  onAudioDiagnostics?: (diag: AudioDiagnostics) => void;
  onError: (code: string, message: string, retryable: boolean) => void;
}

/** Resample arbitrary browser Float32 mono audio to exact 16,000 Hz PCM linear. */
export function resampleLinear(input: Float32Array, fromRate: number, toRate: number): Float32Array {
  if (fromRate === toRate || fromRate <= 0) return input;
  const ratio = fromRate / toRate;
  const outputLength = Math.floor(input.length / ratio);
  const output = new Float32Array(outputLength);
  for (let i = 0; i < outputLength; i++) {
    const srcIdx = i * ratio;
    const low = Math.floor(srcIdx);
    const high = Math.min(low + 1, input.length - 1);
    const frac = srcIdx - low;
    output[i] = input[low] * (1 - frac) + input[high] * frac;
  }
  return output;
}

/** Decode base64 raw 16kHz mono signed 16-bit LE PCM to Float32Array for Web Audio playback. */
export function decodePcmS16LeBase64(base64: string): Float32Array {
  const binary = atob(base64);
  const byteLen = binary.length - (binary.length % 2);
  const view = new DataView(new ArrayBuffer(byteLen));
  for (let i = 0; i < byteLen; i++) {
    view.setUint8(i, binary.charCodeAt(i));
  }
  const sampleCount = byteLen / 2;
  const floatData = new Float32Array(sampleCount);
  for (let i = 0; i < sampleCount; i++) {
    floatData[i] = view.getInt16(i * 2, true) / 32768.0;
  }
  return floatData;
}

export async function listAudioInputDevices(): Promise<AudioInputDeviceInfo[]> {
  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.enumerateDevices) {
    return [];
  }
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    return devices
      .filter((d) => d.kind === 'audioinput')
      .map((d, idx) => ({
        deviceId: d.deviceId,
        label: d.label || `Microphone ${idx + 1}`,
      }));
  } catch {
    return [];
  }
}

export class BrowserVoiceClient {
  private ws: WebSocket | null = null;
  private captureContext: AudioContext | null = null;
  private playbackContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private processor: ScriptProcessorNode | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private hpFilter: BiquadFilterNode | null = null;
  private audioSource: MediaStreamAudioSourceNode | null = null;
  private analyser: AnalyserNode | null = null;
  private silentGain: GainNode | null = null;
  private rafId: number | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;

  private pendingPcmSamples: number[] = [];
  private activeTurnId = 0;
  private minPlayableTurnId = 0;
  private cancelledTurnIds = new Set<number>();
  private playingSources: AudioBufferSourceNode[] = [];
  private nextPlaybackTime = 0;
  private isPlaybackPaused = false;
  private isPlayingAudio = false;
  private ambientNoiseFloorRms = 0.008;
  private localBargeInStreak = 0;
  private localBargeInSentTurnId = -1;
  private audioDiag: AudioDiagnostics = {
    captureSampleRate: TARGET_SAMPLE_RATE,
    channelCount: 1,
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true,
    usedAudioWorklet: false,
    framesSent: 0,
    bytesSent: 0,
    droppedFrames: 0,
    clippedSamples: 0,
    lastRms: 0,
    ambientNoiseRms: 0.008,
    staleChunksDiscarded: 0,
    localBargeInCount: 0,
    localPlaybackStopMs: null,
  };

  private sessionId = '';
  private language: LanguageCode = 'hi-IN';
  private workerId = 'ASHA-DEMO-01';
  private beneficiaryId: string | null = null;
  private callbacks: VoiceClientCallbacks;
  private isClosing = false;
  private isMicStreaming = true; // false when Push-to-Talk released or muted
  private lastPartialReceivedAt = 0;

  // Section 5 TTFA Latency Instrumentation
  private sessionReadyAtMs = 0;
  private speechStartedAtMs = 0;
  private speechEndedAtMs = 0;
  private transcriptFinalizedAtMs = 0;
  private llmFirstTokenAtMs = 0;
  private ttsFirstChunkAtMs = 0;
  private recordedTurnPlaybacks = new Set<number>();
  private ttfaSamplesMs: number[] = [];
  private greetingLatencyMs: number | null = null;
  private lastSttFinalizationMs: number | null = null;
  private lastTtsFirstChunkMs: number | null = null;

  constructor(callbacks: VoiceClientCallbacks) {
    this.callbacks = callbacks;
  }

  getSessionId(): string {
    return this.sessionId;
  }

  setMicTransmissionActive(active: boolean): void {
    this.isMicStreaming = active;
    if (!active) {
      this.pendingPcmSamples = [];
    }
    try {
      this.workletNode?.port.postMessage({ type: 'set_active', active });
    } catch {
      // ignore if worklet already closed
    }
  }

  /** Starts a full Agent 1 voice session: POST /api/v1/sessions -> WS /ws/voice/{session_id}. */
  async startSession(config: {
    language: LanguageCode;
    workerId: string;
    beneficiaryId?: string | null;
    deviceId?: string;
    handsFree?: boolean;
    existingSessionId?: string;
  }): Promise<string | null> {
    this.cleanupAudioOnly();
    this.closeSocketOnly();

    this.isClosing = false;
    this.language = config.language;
    this.workerId = config.workerId;
    this.beneficiaryId = config.beneficiaryId ?? null;
    this.isMicStreaming = config.handsFree ?? true;
    this.activeTurnId = 0;
    this.minPlayableTurnId = 0;
    this.cancelledTurnIds.clear();
    this.localBargeInStreak = 0;
    this.localBargeInSentTurnId = -1;
    this.ambientNoiseFloorRms = 0.008;

    this.callbacks.onStateChange('connecting');

    // 1. Acquire microphone permission
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      this.callbacks.onStateChange('error');
      this.callbacks.onError(
        'MICROPHONE_UNAVAILABLE',
        'Microphone capture requires HTTPS or http://localhost in this browser.',
        false
      );
      return null;
    }

    try {
      const audioConstraints: MediaTrackConstraints = {
        channelCount: 1,
        sampleRate: { ideal: TARGET_SAMPLE_RATE },
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      };
      if (config.deviceId && config.deviceId !== 'default') {
        audioConstraints.deviceId = { exact: config.deviceId };
      }

      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: audioConstraints,
      });
    } catch (err) {
      const msg =
        err instanceof Error && err.name === 'NotAllowedError'
          ? 'Microphone permission denied. Enable microphone access in browser settings to record.'
          : 'Could not access microphone device. Check hardware and permissions.';
      this.callbacks.onStateChange('error');
      this.callbacks.onError('MICROPHONE_PERMISSION_DENIED', msg, true);
      return null;
    }

    // 2. Initialize Web Audio Capture (native rate + 85Hz high-pass) & Playback contexts
    try {
      const track = this.mediaStream.getAudioTracks()[0];
      const settings = track?.getSettings?.() ?? {};
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.captureContext = new AudioCtx();
      if (this.captureContext.state === 'suspended') {
        await this.captureContext.resume();
      }
      this.audioSource = this.captureContext.createMediaStreamSource(this.mediaStream);
      this.hpFilter = this.captureContext.createBiquadFilter();
      this.hpFilter.type = 'highpass';
      this.hpFilter.frequency.value = 85;
      this.hpFilter.Q.value = 0.707;
      this.analyser = this.captureContext.createAnalyser();
      this.analyser.fftSize = 64;
      this.audioSource.connect(this.hpFilter);
      this.hpFilter.connect(this.analyser);

      this.audioDiag = {
        captureSampleRate: this.captureContext.sampleRate,
        channelCount: Number(settings.channelCount || 1),
        echoCancellation: Boolean(settings.echoCancellation ?? true),
        noiseSuppression: Boolean(settings.noiseSuppression ?? true),
        autoGainControl: Boolean(settings.autoGainControl ?? true),
        usedAudioWorklet: false,
        framesSent: 0,
        bytesSent: 0,
        droppedFrames: 0,
        clippedSamples: 0,
        lastRms: 0,
        ambientNoiseRms: this.ambientNoiseFloorRms,
        staleChunksDiscarded: 0,
        localBargeInCount: 0,
        localPlaybackStopMs: null,
      };
      this.callbacks.onAudioDiagnostics?.({ ...this.audioDiag });

      this.playbackContext = new AudioCtx({ sampleRate: TARGET_SAMPLE_RATE });
      if (this.playbackContext.state === 'suspended') {
        await this.playbackContext.resume();
      }

      this.startWaveformLoop();
    } catch (err) {
      this.cleanupAudioOnly();
      const msg = err instanceof Error ? err.message : 'Failed to initialize Web Audio pipeline';
      this.callbacks.onStateChange('error');
      this.callbacks.onError('AUDIO_INIT_ERROR', msg, true);
      return null;
    }

    // 3. Create session with Agent 1 FastAPI backend
    let wsPath = '';
    try {
      if (config.existingSessionId) {
        this.sessionId = config.existingSessionId;
        wsPath = `/ws/voice/${encodeURIComponent(config.existingSessionId)}`;
      } else {
        const created = await fastApiClient.createSession({
          language: this.language,
          beneficiary_id: this.beneficiaryId,
          worker_id: this.workerId,
        });
        this.sessionId = created.session_id;
        wsPath = created.websocket_path;
      }
    } catch (err) {
      this.cleanupAudioOnly();
      const code = err instanceof FastApiError ? err.code : 'BACKEND_UNREACHABLE';
      const msg =
        err instanceof FastApiError
          ? err.message
          : 'Voice backend server is unreachable. Check that FastAPI is running on port 8000.';
      this.callbacks.onStateChange('error');
      this.callbacks.onConnectionChange?.(false, false);
      this.callbacks.onError(code, msg, true);
      return null;
    }

    // 4. Open WebSocket to /ws/voice/{session_id}?language=...&greet=true
    const wsUrl = `${getVoiceWsBaseUrl()}${wsPath}?language=${encodeURIComponent(this.language)}&greet=true`;
    this.openWebSocket(wsUrl);
    return this.sessionId;
  }

  private openWebSocket(wsUrl: string): void {
    const ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';
    this.ws = ws;

    ws.onopen = () => {
      if (this.isClosing) {
        ws.close(1000);
        return;
      }
      this.callbacks.onConnectionChange?.(true, false);
      this.startPcmUplink();
      this.pingTimer = setInterval(() => {
        this.sendJson({
          schema_version: 'v1',
          type: 'ping',
          client_timestamp: new Date().toISOString(),
        });
      }, 15000);
    };

    ws.onmessage = (event) => {
      if (typeof event.data !== 'string') return;
      try {
        const payload = JSON.parse(event.data) as Record<string, unknown>;
        this.handleServerEvent(payload);
      } catch (err) {
        console.error('Malformed WebSocket JSON event', err);
      }
    };

    ws.onerror = () => {
      if (!this.isClosing) {
        this.callbacks.onConnectionChange?.(false, false);
        this.callbacks.onStateChange('error');
        this.callbacks.onError(
          'WS_CONNECTION_ERROR',
          'WebSocket voice connection interrupted. Retry to reconnect.',
          true
        );
      }
    };

    ws.onclose = (ev) => {
      if (this.pingTimer) {
        clearInterval(this.pingTimer);
        this.pingTimer = null;
      }
      this.callbacks.onConnectionChange?.(false, false);
      if (!this.isClosing) {
        if (ev.code === 1011) {
          this.callbacks.onStateChange('error');
        } else {
          this.callbacks.onStateChange('completed');
        }
      }
    };
  }

  private async startPcmUplink(): Promise<void> {
    if (!this.captureContext || !this.audioSource) return;
    const captureNode = this.hpFilter || this.audioSource;

    const handleFrameStats = (rms: number, clipped: number) => {
      this.audioDiag.lastRms = rms;
      if (clipped > 0) {
        this.audioDiag.clippedSamples += clipped;
      }
      if (!this.isPlayingAudio && rms > 0.0005) {
        // Track quiet ambient floor for adaptive local barge-in thresholding
        const alpha = rms < this.ambientNoiseFloorRms * 2.5 ? 0.08 : 0.015;
        this.ambientNoiseFloorRms = this.ambientNoiseFloorRms * (1 - alpha) + rms * alpha;
        this.audioDiag.ambientNoiseRms = this.ambientNoiseFloorRms;
      }
      if (this.isPlayingAudio && !this.isPlaybackPaused && this.isMicStreaming) {
        const bargeInRmsFloor = Math.max(0.055, this.ambientNoiseFloorRms * 3.8);
        if (rms >= bargeInRmsFloor) {
          this.localBargeInStreak += 1;
          if (
            this.localBargeInStreak >= 4 &&
            this.localBargeInSentTurnId !== this.activeTurnId
          ) {
            this.localBargeInSentTurnId = this.activeTurnId;
            this.localBargeInStreak = 0;
            this.triggerBargeIn('local_vad');
          }
        } else {
          this.localBargeInStreak = Math.max(0, this.localBargeInStreak - 1);
        }
      } else {
        this.localBargeInStreak = 0;
      }
    };

    if (this.captureContext.audioWorklet) {
      try {
        await this.captureContext.audioWorklet.addModule('/audio-capture-worklet.js?v=2');
        if (!this.captureContext || this.isClosing) return;

        this.silentGain = this.captureContext.createGain();
        this.silentGain.gain.value = 0;
        this.silentGain.connect(this.captureContext.destination);

        this.workletNode = new AudioWorkletNode(
          this.captureContext,
          'sakshya-capture-processor',
          { numberOfInputs: 1, numberOfOutputs: 1, channelCount: 1 }
        );
        this.workletNode.port.postMessage({ type: 'set_active', active: this.isMicStreaming });
        this.workletNode.port.onmessage = (ev: MessageEvent) => {
          const payload = ev.data as {
            pcmBuffer?: ArrayBuffer;
            buffer?: ArrayBuffer;
            rms?: number;
            peak?: number;
            clipped?: number;
            clippedSamples?: number;
          };
          const pcmBuf = payload?.pcmBuffer ?? payload?.buffer;
          if (!pcmBuf) return;
          if (!this.isMicStreaming) return;
          if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            this.audioDiag.droppedFrames += 1;
            return;
          }
          const rmsVal = Number(payload.rms || 0);
          const clipVal = Number(payload.clippedSamples ?? payload.clipped ?? 0);
          handleFrameStats(rmsVal, clipVal);
          if (payload.peak !== undefined) {
            this.audioDiag.peakRms = Number(payload.peak);
          }
          this.ws.send(pcmBuf);
          this.audioDiag.framesSent += 1;
          this.audioDiag.bytesSent += pcmBuf.byteLength;
          if (this.audioDiag.framesSent % 10 === 0) {
            this.callbacks.onAudioDiagnostics?.({ ...this.audioDiag });
          }
        };
        captureNode.connect(this.workletNode);
        this.workletNode.connect(this.silentGain);
        this.audioDiag.usedAudioWorklet = true;
        this.callbacks.onAudioDiagnostics?.({ ...this.audioDiag });
        return;
      } catch (err) {
        console.warn('AudioWorklet init failed, falling back to ScriptProcessorNode:', err);
      }
    }

    // Fallback: ScriptProcessorNode if AudioWorklet unavailable
    const inputRate = this.captureContext.sampleRate;
    this.processor = this.captureContext.createScriptProcessor(1024, 1, 1);
    this.silentGain = this.captureContext.createGain();
    this.silentGain.gain.value = 0;

    captureNode.connect(this.processor);
    this.processor.connect(this.silentGain);
    this.silentGain.connect(this.captureContext.destination);

    this.processor.onaudioprocess = (ev) => {
      if (!this.isMicStreaming) return;
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        this.audioDiag.droppedFrames += 1;
        return;
      }

      const rawFloat = ev.inputBuffer.getChannelData(0);
      const resampled = resampleLinear(rawFloat, inputRate, TARGET_SAMPLE_RATE);

      for (let i = 0; i < resampled.length; i++) {
        if (Math.abs(resampled[i]) >= 0.999) {
          this.audioDiag.clippedSamples += 1;
        }
        const clamped = Math.max(-1, Math.min(1, resampled[i]));
        const sample = clamped < 0 ? Math.round(clamped * 0x8000) : Math.round(clamped * 0x7fff);
        this.pendingPcmSamples.push(sample);
      }

      while (this.pendingPcmSamples.length >= TARGET_FRAME_SAMPLES) {
        const chunk = this.pendingPcmSamples.splice(0, TARGET_FRAME_SAMPLES);
        const frame = new Int16Array(chunk);
        let energy = 0;
        for (let i = 0; i < frame.length; i++) {
          const norm = frame[i] / 32768.0;
          energy += norm * norm;
        }
        handleFrameStats(Math.sqrt(energy / frame.length), 0);
        this.ws.send(frame.buffer);
        this.audioDiag.framesSent += 1;
        this.audioDiag.bytesSent += frame.buffer.byteLength;
        if (this.audioDiag.framesSent % 20 === 0) {
          this.callbacks.onAudioDiagnostics?.({ ...this.audioDiag });
        }
      }
    };
  }

  private startWaveformLoop(): void {
    if (!this.analyser) return;
    const bins = new Uint8Array(this.analyser.frequencyBinCount);

    const tick = () => {
      if (!this.analyser) return;
      if (!this.isMicStreaming) {
        this.callbacks.onAudioLevel(0, new Array(16).fill(0));
      } else {
        this.analyser.getByteFrequencyData(bins);
        let sum = 0;
        const bands: number[] = [];
        const step = Math.max(1, Math.floor(bins.length / 16));
        for (let i = 0; i < bins.length; i++) {
          sum += bins[i];
          if (i % step === 0 && bands.length < 16) {
            bands.push(Math.min(1, bins[i] / 180));
          }
        }
        const level = Math.min(1, sum / (bins.length * 110));
        this.callbacks.onAudioLevel(level, bands);
      }
      this.rafId = requestAnimationFrame(tick);
    };

    this.rafId = requestAnimationFrame(tick);
  }

  private handleServerEvent(raw: Record<string, unknown>): void {
    const type = raw.type as string;
    switch (type) {
      case 'server_audio_stats':
      case 'audio_diagnostics': {
        this.audioDiag.serverFramesReceived = Number(raw.frames_received || raw.frames || 0);
        this.audioDiag.serverBytesReceived = Number(raw.bytes_received || raw.bytes || 0);
        this.audioDiag.serverAudioRms = Number(raw.rms || 0);
        if (raw.stt_connected !== undefined) {
          this.audioDiag.sttConnected = Boolean(raw.stt_connected);
        }
        this.callbacks.onAudioDiagnostics?.({ ...this.audioDiag });
        break;
      }
      case 'session_ready': {
        this.sessionReadyAtMs = Date.now();
        const ev = raw as unknown as ServerSessionReadyEventV1;
        this.callbacks.onSessionReady?.(ev);
        this.callbacks.onStateChange('listening', 'listening');
        break;
      }
      case 'session_state': {
        const backendState = raw.state as BackendSessionStateV1;
        const mapped = mapBackendStateToUiState(backendState);
        this.callbacks.onStateChange(mapped, backendState);
        break;
      }
      case 'speech_start': {
        this.speechStartedAtMs = Date.now();
        this.callbacks.onSpeechActivity?.(true, (raw.utterance_id as string | null) ?? null);
        break;
      }
      case 'speech_end': {
        this.speechEndedAtMs = Date.now();
        this.callbacks.onSpeechActivity?.(false, (raw.utterance_id as string | null) ?? null);
        break;
      }
      case 'partial_transcript': {
        const ev = raw as unknown as ServerPartialTranscriptEventV1;
        const now = Date.now();
        if (!this.speechStartedAtMs) this.speechStartedAtMs = now;
        this.lastPartialReceivedAt = now;
        this.callbacks.onStateChange('transcribing');
        this.callbacks.onPartialTranscript(ev);
        break;
      }
      case 'final_transcript': {
        const ev = raw as unknown as ServerFinalTranscriptEventV1;
        const now = Date.now();
        this.transcriptFinalizedAtMs = now;
        if (!this.speechEndedAtMs) {
          this.speechEndedAtMs =
            typeof ev.latency_ms === 'number' && ev.latency_ms >= 0
              ? now - ev.latency_ms
              : now;
        }
        this.lastSttFinalizationMs = Math.max(0, Math.round(now - this.speechEndedAtMs));
        this.callbacks.onFinalTranscript(ev);
        this.callbacks.onStateChange('processing');
        break;
      }
      case 'assistant_response': {
        const turnId = Number(raw.turn_id || 1);
        this.llmFirstTokenAtMs = Date.now();
        this.callbacks.onStateChange('responding');
        this.callbacks.onAssistantResponse(
          String(raw.text || ''),
          turnId,
          Boolean(raw.is_danger_escalation),
          String(raw.language || this.language)
        );
        break;
      }
      case 'tts_start': {
        const turnId = Number(raw.turn_id || 1);
        if (turnId < this.minPlayableTurnId || this.cancelledTurnIds.has(turnId)) {
          return;
        }
        if (turnId > this.activeTurnId) {
          this.activeTurnId = turnId;
        }
        this.isPlaybackPaused = false;
        this.isPlayingAudio = true;
        this.localBargeInSentTurnId = -1;
        this.callbacks.onStateChange('speaking', 'speaking');
        this.callbacks.onTtsPlaybackChange?.(true, false, turnId);
        break;
      }
      case 'tts_audio_chunk': {
        const turnId = Number(raw.turn_id || 0);
        if (
          turnId < this.minPlayableTurnId ||
          this.cancelledTurnIds.has(turnId) ||
          turnId !== this.activeTurnId
        ) {
          // Zero-stale-audio rule: discard stale chunks synchronously before decoding
          this.audioDiag.staleChunksDiscarded += 1;
          return;
        }
        const seq = Number(raw.seq || 1);
        if (seq === 1) {
          this.ttsFirstChunkAtMs = Date.now();
          if (this.llmFirstTokenAtMs > 0) {
            this.lastTtsFirstChunkMs = Math.max(
              0,
              Math.round(this.ttsFirstChunkAtMs - this.llmFirstTokenAtMs)
            );
          }
        }
        this.enqueuePcmPlayback(
          String(raw.audio_base64 || ''),
          Number(raw.sample_rate || 16000),
          turnId
        );
        break;
      }
      case 'tts_complete': {
        const turnId = Number(raw.turn_id || this.activeTurnId);
        if (turnId < this.minPlayableTurnId || this.cancelledTurnIds.has(turnId)) {
          return;
        }
        this.isPlayingAudio = false;
        this.callbacks.onTtsPlaybackChange?.(false, false, turnId);
        this.callbacks.onStateChange('listening', 'listening');
        break;
      }
      case 'barge_in': {
        const ev = raw as unknown as ServerBargeInEventV1;
        this.cancelledTurnIds.add(ev.cancelled_turn_id);
        this.minPlayableTurnId = Math.max(this.minPlayableTurnId, ev.new_turn_id);
        this.activeTurnId = Math.max(this.activeTurnId, ev.new_turn_id);
        this.flushAudioPlayback();
        this.callbacks.onTtsPlaybackChange?.(false, false, ev.cancelled_turn_id);
        this.callbacks.onBargeIn?.(ev);
        this.callbacks.onStateChange('interrupted');
        break;
      }
      case 'tts_cancelled': {
        const cancelledTurnId = Number(raw.cancelled_turn_id || 0);
        this.cancelledTurnIds.add(cancelledTurnId);
        const nextAllowed = cancelledTurnId + 1;
        this.minPlayableTurnId = Math.max(this.minPlayableTurnId, nextAllowed);
        if (this.activeTurnId <= cancelledTurnId) {
          this.activeTurnId = nextAllowed;
        }
        this.flushAudioPlayback();
        this.callbacks.onTtsPlaybackChange?.(false, false, cancelledTurnId);
        this.callbacks.onStateChange('interrupted');
        break;
      }
      case 'visit_draft_updated': {
        this.callbacks.onVisitDraftUpdated(raw as unknown as ServerVisitDraftUpdatedEventV1);
        break;
      }
      case 'clarification_required': {
        this.callbacks.onClarificationRequired?.(raw as unknown as ServerClarificationRequiredEventV1);
        break;
      }
      case 'read_back_started': {
        this.callbacks.onReadBackStarted?.(raw as unknown as ServerReadBackStartedEventV1);
        break;
      }
      case 'correction_applied': {
        this.callbacks.onCorrectionApplied?.(raw as unknown as ServerCorrectionAppliedEventV1);
        break;
      }
      case 'visit_confirmed': {
        this.callbacks.onVisitConfirmed?.(raw as unknown as ServerVisitConfirmedEventV1);
        break;
      }
      case 'persistence_requested': {
        this.callbacks.onPersistenceRequested?.(raw as unknown as ServerPersistenceRequestedEventV1);
        break;
      }
      case 'visit_committed': {
        this.callbacks.onVisitCommitted?.(raw as unknown as ServerVisitCommittedEventV1);
        this.callbacks.onStateChange('completed', 'committed');
        break;
      }
      case 'persistence_rejected': {
        this.callbacks.onPersistenceRejected?.(raw as unknown as ServerPersistenceRejectedEventV1);
        break;
      }
      case 'danger_alert': {
        this.callbacks.onDangerAlert(raw as unknown as ServerDangerAlertEventV1);
        break;
      }
      case 'error': {
        const err = raw as unknown as ServerErrorEventV1;
        this.callbacks.onStateChange('error');
        this.callbacks.onError(err.code, err.message, err.retryable);
        break;
      }
      case 'pong':
      default:
        break;
    }
  }

  private enqueuePcmPlayback(base64: string, sampleRate: number, turnId?: number): void {
    if (!base64 || !this.playbackContext) return;
    try {
      if (this.playbackContext.state === 'suspended' && !this.isPlaybackPaused) {
        void this.playbackContext.resume().catch(() => {});
      }
      const floatSamples = decodePcmS16LeBase64(base64);
      if (floatSamples.length === 0) return;

      const audioBuffer = this.playbackContext.createBuffer(1, floatSamples.length, sampleRate);
      audioBuffer.getChannelData(0).set(floatSamples);

      const source = this.playbackContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.playbackContext.destination);

      const now = this.playbackContext.currentTime;
      const startAt = Math.max(now + 0.005, this.nextPlaybackTime);
      this.nextPlaybackTime = startAt + audioBuffer.duration;

      this.playingSources.push(source);
      source.onended = () => {
        this.playingSources = this.playingSources.filter((s) => s !== source);
      };
      source.start(startAt);

      if (turnId && !this.recordedTurnPlaybacks.has(turnId)) {
        this.recordedTurnPlaybacks.add(turnId);
        this.recordFirstAudioPlayed(turnId, Math.round((startAt - now) * 1000));
      }
    } catch (err) {
      console.warn('PCM playback decode warning:', err);
    }
  }

  private recordFirstAudioPlayed(turnId: number, scheduleOffsetMs: number): void {
    const audioFirstPlayedAtMs = Date.now() + Math.max(0, scheduleOffsetMs);
    let turnTtfaMs: number | null = null;

    if (this.speechEndedAtMs > 0) {
      turnTtfaMs = Math.max(0, Math.round(audioFirstPlayedAtMs - this.speechEndedAtMs));
      this.ttfaSamplesMs.push(turnTtfaMs);
      this.speechStartedAtMs = 0;
      this.speechEndedAtMs = 0;
    } else if (this.greetingLatencyMs === null && this.sessionReadyAtMs > 0) {
      this.greetingLatencyMs = Math.max(
        0,
        Math.round(audioFirstPlayedAtMs - this.sessionReadyAtMs)
      );
    }

    const sorted = [...this.ttfaSamplesMs].sort((a, b) => a - b);
    const avg =
      sorted.length > 0
        ? Math.round(sorted.reduce((acc, v) => acc + v, 0) / sorted.length)
        : null;

    this.callbacks.onLatencyUpdate?.({
      lastTtfaMs:
        turnTtfaMs ??
        (this.ttfaSamplesMs.length > 0
          ? this.ttfaSamplesMs[this.ttfaSamplesMs.length - 1]
          : null),
      p50TtfaMs: computePercentile(sorted, 50),
      p95TtfaMs: computePercentile(sorted, 95),
      avgTtfaMs: avg,
      greetingLatencyMs: this.greetingLatencyMs,
      lastSttFinalizationMs: this.lastSttFinalizationMs,
      lastTtsFirstChunkMs: this.lastTtsFirstChunkMs,
      turnCount: this.ttfaSamplesMs.length,
    });

    if (this.sessionId) {
      fetch(`${getVoiceApiBaseUrl()}/api/v1/sessions/${encodeURIComponent(this.sessionId)}/metrics/client-playback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          schema_version: 'v1',
          turn_id: turnId,
          client_ttfa_ms: turnTtfaMs,
          audio_first_played_epoch_ms: audioFirstPlayedAtMs,
        }),
        keepalive: true,
      }).catch(() => {});
    }
  }

  flushAudioPlayback(): void {
    this.playingSources.forEach((src) => {
      try {
        src.stop();
        src.disconnect();
      } catch {
        // already stopped
      }
    });
    this.playingSources = [];
    this.nextPlaybackTime = 0;
    this.isPlayingAudio = false;
    this.isPlaybackPaused = false;
  }

  async pausePlayback(): Promise<void> {
    if (this.playbackContext && this.playbackContext.state === 'running') {
      await this.playbackContext.suspend();
      this.isPlaybackPaused = true;
      this.callbacks.onTtsPlaybackChange?.(this.isPlayingAudio, true, this.activeTurnId);
    }
  }

  async resumePlayback(): Promise<void> {
    if (this.playbackContext && this.playbackContext.state === 'suspended') {
      await this.playbackContext.resume();
      this.isPlaybackPaused = false;
      this.callbacks.onTtsPlaybackChange?.(this.isPlayingAudio, false, this.activeTurnId);
    }
  }

  triggerBargeIn(reason = 'user_tap'): void {
    const t0 = typeof performance !== 'undefined' ? performance.now() : Date.now();
    const cancelledTurn = this.activeTurnId;
    this.cancelledTurnIds.add(cancelledTurn);
    this.minPlayableTurnId = Math.max(this.minPlayableTurnId, cancelledTurn + 1);
    this.activeTurnId = this.minPlayableTurnId;
    this.flushAudioPlayback();
    const stopMs = Math.round(((typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0) * 100) / 100;
    this.audioDiag.localBargeInCount += 1;
    this.audioDiag.localPlaybackStopMs = stopMs;
    this.callbacks.onTtsPlaybackChange?.(false, false, cancelledTurn);
    this.callbacks.onAudioDiagnostics?.({ ...this.audioDiag });
    this.callbacks.onStateChange('interrupted');
    this.sendJson({
      schema_version: 'v1',
      type: 'barge_in',
      reason,
      client_timestamp: new Date().toISOString(),
    });
  }

  sendTextInput(text: string, language?: string): boolean {
    if (!text.trim()) return false;
    return this.sendJson({
      schema_version: 'v1',
      type: 'text_input',
      text: text.trim(),
      language: language || this.language,
    });
  }

  setLanguage(language: LanguageCode): void {
    this.language = language;
    this.sendJson({
      schema_version: 'v1',
      type: 'set_language',
      language,
    });
  }

  sendConfirmVisit(visitId: string, confirmed: boolean): boolean {
    return this.sendJson({
      schema_version: 'v1',
      type: 'confirm_visit',
      visit_id: visitId,
      confirmed,
      worker_id: this.workerId,
      confirmation_method: 'ui_button',
    });
  }

  sendPatchFields(fields: Record<string, unknown>): boolean {
    return this.sendJson({
      schema_version: 'v1',
      type: 'patch_fields',
      fields,
    });
  }

  sendRemoveObservation(key: string): boolean {
    return this.sendJson({
      schema_version: 'v1',
      type: 'remove_observation',
      key,
    });
  }

  sendRemoveEvent(name: string): boolean {
    return this.sendJson({
      schema_version: 'v1',
      type: 'remove_event',
      name,
    });
  }

  sendFinishNotes(): boolean {
    return this.sendJson({
      schema_version: 'v1',
      type: 'finish_notes',
    });
  }

  sendPersistenceAck(payload: {
    visitId: string;
    correlationId: string;
    accepted: boolean;
    persistenceRecordId?: string | null;
    committedAt?: string | null;
    errorCode?: string | null;
    errorMessage?: string | null;
  }): boolean {
    return this.sendJson({
      schema_version: 'v1',
      type: 'persistence_ack',
      visit_id: payload.visitId,
      correlation_id: payload.correlationId,
      accepted: payload.accepted,
      persistence_record_id: payload.persistenceRecordId ?? null,
      committed_at: payload.committedAt ?? null,
      error_code: payload.errorCode ?? null,
      error_message: payload.errorMessage ?? null,
    });
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  getLastPartialTimestamp(): number {
    return this.lastPartialReceivedAt;
  }

  private sendJson(msg: ClientWebSocketEventV1): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return false;
    }
    this.ws.send(JSON.stringify(msg));
    return true;
  }

  private cleanupAudioOnly(): void {
    this.flushAudioPlayback();
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    if (this.workletNode) {
      this.workletNode.port.onmessage = null;
      this.workletNode.disconnect();
      this.workletNode = null;
    }
    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    if (this.hpFilter) {
      this.hpFilter.disconnect();
      this.hpFilter = null;
    }
    if (this.silentGain) {
      this.silentGain.disconnect();
      this.silentGain = null;
    }
    if (this.audioSource) {
      this.audioSource.disconnect();
      this.audioSource = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((t) => t.stop());
      this.mediaStream = null;
    }
    if (this.captureContext) {
      this.captureContext.close().catch(() => {});
      this.captureContext = null;
    }
    if (this.playbackContext) {
      this.playbackContext.close().catch(() => {});
      this.playbackContext = null;
    }
    this.analyser = null;
    this.pendingPcmSamples = [];
  }

  private closeSocketOnly(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
    if (this.ws) {
      try {
        if (this.ws.readyState === WebSocket.OPEN) {
          this.sendJson({
            schema_version: 'v1',
            type: 'end_session',
            reason: 'client_stop',
          });
        }
        this.ws.close(1000, 'Session ended');
      } catch {
        // ignore close error
      }
      this.ws = null;
    }
  }

  stopSession(): void {
    this.isClosing = true;
    this.closeSocketOnly();
    this.cleanupAudioOnly();
    this.callbacks.onConnectionChange?.(false, false);
    this.callbacks.onStateChange('idle');
  }
}

export function mapBackendStateToUiState(state: BackendSessionStateV1): VoiceInteractionState {
  switch (state) {
    case 'idle':
      return 'idle';
    case 'listening':
      return 'listening';
    case 'processing':
      return 'processing';
    case 'speaking':
    case 'read_back':
      return 'speaking';
    case 'danger_escalation':
      return 'responding';
    case 'awaiting_confirmation':
      return 'listening';
    case 'committing':
      return 'processing';
    case 'committed':
    case 'closed':
      return 'completed';
    default:
      return 'idle';
  }
}

export type {
  VisitRecordV1,
  DangerAlertV1,
  ClarificationReasonV1,
  ClarificationCandidateV1,
};
