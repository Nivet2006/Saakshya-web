'use client';

import React, { useEffect, useRef, useState } from 'react';
import type { AudioDiagnostics, AudioInputDeviceInfo } from '@/lib/voice/voice-client';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Cpu,
  Mic,
  Play,
  Radio,
  RefreshCw,
  Server,
  Volume2,
  Wifi,
  XCircle,
} from 'lucide-react';

interface AudioDiagnosticsPanelProps {
  diagnostics: AudioDiagnostics | null;
  audioLevel: number;
  waveformBands: number[];
  isConnected: boolean;
  sessionId: string;
  inputDevices: AudioInputDeviceInfo[];
  selectedDeviceId: string;
  onSelectDevice: (deviceId: string) => void;
  onSendTextUtterance?: (text: string) => void;
  language: string;
}

export const AudioDiagnosticsPanel: React.FC<AudioDiagnosticsPanelProps> = ({
  diagnostics,
  audioLevel,
  waveformBands,
  isConnected,
  sessionId,
  inputDevices,
  selectedDeviceId,
  onSelectDevice,
  onSendTextUtterance,
  language,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [micPermission, setMicPermission] = useState<'granted' | 'prompt' | 'denied' | 'unknown'>('unknown');

  // Local Loopback Mic Test state
  const [isTestingLocalMic, setIsTestingLocalMic] = useState(false);
  const [localTestCountdown, setLocalTestCountdown] = useState(0);
  const [localAudioUrl, setLocalAudioUrl] = useState<string | null>(null);
  const [isPlayingBack, setIsPlayingBack] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  // Check browser mic permission status
  useEffect(() => {
    if (typeof navigator !== 'undefined' && navigator.permissions?.query) {
      navigator.permissions
        .query({ name: 'microphone' as PermissionName })
        .then((p) => {
          setMicPermission(p.state as 'granted' | 'prompt' | 'denied');
          p.onchange = () => {
            setMicPermission(p.state as 'granted' | 'prompt' | 'denied');
          };
        })
        .catch(() => setMicPermission('unknown'));
    }
  }, []);

  // Run local 40-second record & playback loopback test
  const stopLocalMicTest = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  };

  const startLocalMicTest = async () => {
    try {
      if (localAudioUrl) {
        URL.revokeObjectURL(localAudioUrl);
        setLocalAudioUrl(null);
      }
      audioChunksRef.current = [];
      const constraints: MediaStreamConstraints = {
        audio: selectedDeviceId && selectedDeviceId !== 'default' ? { deviceId: { exact: selectedDeviceId } } : true,
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      setMicPermission('granted');

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const url = URL.createObjectURL(blob);
        setLocalAudioUrl(url);
        setIsTestingLocalMic(false);
        // Automatically play back to verify speaker/mic loop
        setTimeout(() => {
          if (audioPlayerRef.current) {
            audioPlayerRef.current.play().catch(() => {});
          }
        }, 100);
      };

      recorder.start();
      setIsTestingLocalMic(true);
      setLocalTestCountdown(40);

      const interval = setInterval(() => {
        setLocalTestCountdown((prev) => {
          if (prev <= 1 || !mediaRecorderRef.current || mediaRecorderRef.current.state !== 'recording') {
            clearInterval(interval);
            if (recorder.state === 'recording') {
              recorder.stop();
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (err) {
      alert(`Microphone access error: ${err instanceof Error ? err.message : String(err)}`);
      setIsTestingLocalMic(false);
    }
  };

  const hasFrames = (diagnostics?.framesSent ?? 0) > 0;
  const isServerRx = (diagnostics?.serverFramesReceived ?? 0) > 0;
  const rmsPercentage = Math.min(100, Math.round(audioLevel * 100));

  return (
    <section aria-label="Audio & STT Diagnostics Panel" className="bg-slate-900 text-white rounded-2xl border border-slate-700 shadow-lg overflow-hidden">
      {/* Header with status pill and toggle */}
      <div className="p-4 sm:p-5 flex items-center justify-between gap-3 bg-slate-950 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-teal-500/20 text-teal-400 flex items-center justify-center">
            <Radio className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold tracking-tight">Audio Capture &amp; Gnani STT Diagnostics</h2>
              <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                isConnected && hasFrames
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : isConnected
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  : 'bg-slate-800 text-slate-400'
              }`}>
                {isConnected && hasFrames ? 'STREAMING PCM' : isConnected ? 'CONNECTED (0 FRAMES)' : 'DISCONNECTED'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Live microphone capture, 16kHz PCM downmix, WebSocket uplink, and Gnani Prisma verification
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
        >
          {isOpen ? 'Hide Diagnostics' : 'Show Diagnostics'}
        </button>
      </div>

      {isOpen && (
        <div className="p-4 sm:p-6 space-y-6 text-xs">
          {/* 1. Live Pipeline Stages Health Matrix */}
          <div>
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2.5">
              Pipeline Stages Verification (Section 1 Trace)
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {/* Stage 1: Microphone Hardware */}
              <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-300">1. Mic Permission</span>
                  {micPermission === 'granted' ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  ) : micPermission === 'denied' ? (
                    <XCircle className="h-4 w-4 text-red-400" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-amber-400" />
                  )}
                </div>
                <p className="font-mono text-[10px] text-slate-400 capitalize">{micPermission}</p>
                <div className="text-[10px] text-slate-400 truncate">
                  Device: {inputDevices.find((d) => d.deviceId === selectedDeviceId)?.label || 'Default'}
                </div>
              </div>

              {/* Stage 2: Web Audio Capture */}
              <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-300">2. Web Audio PCM</span>
                  {diagnostics?.usedAudioWorklet || diagnostics ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-slate-500" />
                  )}
                </div>
                <p className="font-mono text-[10px] text-slate-400">
                  {diagnostics?.usedAudioWorklet ? 'AudioWorklet (16kHz Mono)' : 'ScriptProcessor Fallback'}
                </p>
                <div className="text-[10px] text-slate-400">
                  Native: {diagnostics?.captureSampleRate ?? 48000}Hz → 16,000Hz
                </div>
              </div>

              {/* Stage 3: WebSocket Transport */}
              <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-300">3. Frontend WS Send</span>
                  {hasFrames ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  ) : isConnected ? (
                    <AlertCircle className="h-4 w-4 text-amber-400" />
                  ) : (
                    <XCircle className="h-4 w-4 text-slate-600" />
                  )}
                </div>
                <p className="font-mono text-[10px] text-slate-400">
                  {diagnostics?.framesSent ?? 0} frames ({Math.round((diagnostics?.bytesSent ?? 0) / 1024)} KB)
                </p>
                <div className="text-[10px] text-slate-400">
                  Dropped: {diagnostics?.droppedFrames ?? 0}
                </div>
              </div>

              {/* Stage 4: FastAPI & Gnani STT */}
              <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-slate-300">4. Gnani Prisma STT</span>
                  {diagnostics?.sttConnected ?? isConnected ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-slate-500" />
                  )}
                </div>
                <p className="font-mono text-[10px] text-slate-400">
                  Server Rx: {diagnostics?.serverFramesReceived ?? (hasFrames ? 'Active' : 0)} frames
                </p>
                <div className="text-[10px] text-slate-400">
                  Model: prisma-v3.0 ({language})
                </div>
              </div>
            </div>
          </div>

          {/* 2. Live Audio Level Meter & Frequency Band Monitor */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <Activity className="h-3.5 w-3.5 text-teal-400" />
                Live Microphone Signal Level Meter
              </span>
              <span className="font-mono text-[11px] text-teal-400 font-bold">
                RMS: {rmsPercentage}% · Raw: {(diagnostics?.lastRms ?? 0).toFixed(4)}
                {(diagnostics?.clippedSamples ?? 0) > 0 && (
                  <span className="text-red-400 ml-2 font-bold">⚠️ Clipped: {diagnostics?.clippedSamples}</span>
                )}
              </span>
            </div>

            {/* Visual RMS meter bar */}
            <div className="w-full h-3 rounded-full bg-slate-800 overflow-hidden flex items-center p-0.5">
              <div
                className={`h-full rounded-full transition-all duration-75 ${
                  rmsPercentage > 85 ? 'bg-red-500' : rmsPercentage > 50 ? 'bg-amber-400' : 'bg-emerald-400'
                }`}
                style={{ width: `${Math.max(2, rmsPercentage)}%` }}
              />
            </div>

            {/* 16 Frequency Spectrum Bands */}
            <div className="flex items-end gap-1 h-8 pt-1">
              {waveformBands.map((band, idx) => (
                <div
                  key={idx}
                  className="flex-1 bg-teal-500/40 rounded-t-sm transition-all duration-75"
                  style={{ height: `${Math.max(4, Math.round((band / 255) * 100))}%` }}
                />
              ))}
            </div>
          </div>

          {/* 3. Section 2: Local Microphone Loopback Test */}
          <div className="p-4 rounded-xl bg-slate-850 bg-slate-800/40 border border-slate-700 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h4 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <Mic className="h-4 w-4 text-clinical-secondary" />
                Local Microphone Loopback Test (Prove Hardware / Capture)
              </h4>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Records a 40-second audio clip from your mic and plays it back directly into your speakers. Proves your browser audio capture is working independently of Gnani.
              </p>
            </div>

            <div className="flex items-center gap-3 shrink-0 flex-wrap">
              {isTestingLocalMic ? (
                <div className="flex items-center gap-2">
                  <span className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-teal-300 font-mono text-xs flex items-center gap-2">
                    <RefreshCw className="h-3.5 w-3.5 animate-spin text-teal-400" />
                    Recording: {localTestCountdown}s remaining
                  </span>
                  <button
                    type="button"
                    onClick={stopLocalMicTest}
                    className="px-3 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold text-xs transition-colors"
                  >
                    Stop &amp; Play Now
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={startLocalMicTest}
                  className="px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-bold text-xs flex items-center gap-2 transition-colors shadow-sm"
                >
                  <Play className="h-3.5 w-3.5" />
                  <span>Run 40s Mic Test</span>
                </button>
              )}

              {localAudioUrl && (
                <div className="flex items-center gap-2">
                  <audio
                    ref={audioPlayerRef}
                    src={localAudioUrl}
                    onPlay={() => setIsPlayingBack(true)}
                    onEnded={() => setIsPlayingBack(false)}
                    controls
                    className="h-8 max-w-[200px]"
                  />
                  <span className="text-[10px] text-emerald-400 font-bold">✅ Captured!</span>
                </div>
              )}
            </div>
          </div>

          {/* 4. Section 8: Isolated Test Utterance Control */}
          <div className="p-4 rounded-xl bg-slate-850 bg-slate-800/40 border border-slate-700 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h4 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <Server className="h-4 w-4 text-emerald-400" />
                Section 8 Isolated Pipeline Test
              </h4>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Send the documented test utterance: &quot;Hello, my name is Lakshmi. Baby weight is 2.8 kilograms.&quot;
              </p>
            </div>

            <button
              type="button"
              onClick={() => {
                onSendTextUtterance?.('Hello, my name is Lakshmi. Baby weight is 2.8 kilograms.');
              }}
              disabled={!isConnected}
              className="px-3.5 py-2 rounded-xl bg-slate-700 hover:bg-slate-600 disabled:opacity-40 text-white font-bold text-xs shrink-0 transition-colors"
            >
              Send Synthetic Test Utterance
            </button>
          </div>
        </div>
      )}
    </section>
  );
};
