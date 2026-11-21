'use client';

import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { HealthWave } from '@/components/animations/HealthWave';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type { AudioInputDeviceInfo } from '@/lib/voice/voice-client';
import type { TranscriptLine, VoiceInteractionState } from '@/types';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  FastForward,
  Keyboard,
  Loader2,
  Mic,
  MicOff,
  Radio,
  RefreshCw,
  Send,
  Sparkles,
  Square,
  Volume2,
} from 'lucide-react';

interface VoiceRecorderProps {
  interactionState: VoiceInteractionState;
  isConnected: boolean;
  handsFree: boolean;
  pttPressed: boolean;
  audioLevel: number;
  waveformBands: number[];
  durationSeconds: number;
  language: string;
  inputDevices: AudioInputDeviceInfo[];
  selectedDeviceId: string;
  isCorrectingMode?: boolean;
  targetCorrectionField?: string | null;
  onSelectDevice: (deviceId: string) => void;
  onToggleHandsFree: (handsFree: boolean) => void;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onPttDown: () => void;
  onPttUp: () => void;
  onBargeIn: () => void;
  onSendTextUtterance?: (text: string) => void;
}

const STATE_BADGE_CLASS: Record<VoiceInteractionState, string> = {
  idle: 'bg-slate-100 text-slate-700 border-slate-300',
  connecting: 'bg-sky-50 text-sky-800 border-sky-300',
  listening: 'bg-emerald-50 text-emerald-800 border-emerald-300',
  transcribing: 'bg-teal-50 text-teal-800 border-teal-300',
  processing: 'bg-amber-50 text-amber-800 border-amber-300',
  responding: 'bg-sky-50 text-sky-800 border-sky-300',
  speaking: 'bg-indigo-50 text-indigo-800 border-indigo-300',
  interrupted: 'bg-amber-100 text-amber-900 border-amber-400',
  reconnecting: 'bg-amber-50 text-amber-800 border-amber-300',
  error: 'bg-red-50 text-red-800 border-red-300',
  completed: 'bg-emerald-100 text-emerald-900 border-emerald-300',
};

export const VoiceRecorder: React.FC<VoiceRecorderProps> = ({
  interactionState,
  isConnected,
  handsFree,
  pttPressed,
  audioLevel,
  waveformBands,
  durationSeconds,
  language,
  inputDevices,
  selectedDeviceId,
  isCorrectingMode,
  targetCorrectionField,
  onSelectDevice,
  onToggleHandsFree,
  onStartRecording,
  onStopRecording,
  onPttDown,
  onPttUp,
  onBargeIn,
  onSendTextUtterance,
}) => {
  const { ui } = useTranslation(language);
  const [showTextFallback, setShowTextFallback] = useState(false);
  const [typedUtterance, setTypedUtterance] = useState('');

  const stateLabels: Record<VoiceInteractionState, string> = {
    idle: ui.stateIdle,
    connecting: ui.stateConnecting,
    listening: ui.stateListening,
    transcribing: ui.stateTranscribing,
    processing: ui.stateProcessing,
    responding: ui.stateResponding,
    speaking: ui.stateSpeaking,
    interrupted: ui.stateInterrupted,
    reconnecting: ui.stateReconnecting,
    error: ui.stateError,
    completed: ui.stateCompleted,
  };

  const stateHelpers: Record<VoiceInteractionState, string> = {
    idle: ui.helperIdle,
    connecting: ui.helperConnecting,
    listening: ui.helperListening,
    transcribing: ui.helperTranscribing,
    processing: ui.helperProcessing,
    responding: ui.helperResponding,
    speaking: ui.helperSpeaking,
    interrupted: ui.helperInterrupted,
    reconnecting: ui.helperReconnecting,
    error: ui.helperError,
    completed: ui.helperCompleted,
  };

  const isSessionActive =
    isConnected ||
    ['connecting', 'listening', 'transcribing', 'processing', 'responding', 'speaking', 'interrupted'].includes(
      interactionState
    );

  const badgeClass = STATE_BADGE_CLASS[interactionState];
  const helperText = stateHelpers[interactionState];
  const mins = String(Math.floor(durationSeconds / 60)).padStart(2, '0');
  const secs = String(durationSeconds % 60).padStart(2, '0');

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!typedUtterance.trim() || !onSendTextUtterance) return;
    onSendTextUtterance(typedUtterance.trim());
    setTypedUtterance('');
  };

  return (
    <section
      aria-labelledby="voice-capture-heading"
      className="bg-white border border-clinical-border-subtle rounded-2xl p-4 sm:p-6 shadow-sm"
    >
      {/* Header status row */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-4 border-b border-slate-100">
        <div>
          <h2 id="voice-capture-heading" className="text-base font-bold text-clinical-text">
            {ui.step3Title}
          </h2>
          <p className="text-xs text-clinical-text-secondary">
            {ui.step3Subtitle}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${
              isConnected
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                : 'bg-slate-100 text-slate-600 border-slate-200'
            }`}
          >
            <Radio className="h-3.5 w-3.5" aria-hidden="true" />
            <span>{isConnected ? `${ui.connectedLabel} (${language})` : ui.disconnectedLabel}</span>
          </span>

          {isSessionActive && (
            <span className="font-mono text-xs font-bold px-2.5 py-1 rounded-full bg-slate-900 text-white tabular-nums">
              {mins}:{secs}
            </span>
          )}
        </div>
      </div>

      {/* Correction Prompt Banner */}
      {isCorrectingMode && (
        <div
          role="status"
          className="mt-3 p-3 rounded-xl bg-indigo-50 border border-indigo-200 text-xs text-indigo-950 font-semibold flex items-center gap-2"
        >
          <Mic className="h-4 w-4 text-indigo-700 shrink-0" aria-hidden="true" />
          <span>
            {ui.voiceCorrectionActive}
            {targetCorrectionField ? ` (${targetCorrectionField})` : ''}: {ui.voiceCorrectionHint}
          </span>
        </div>
      )}

      {/* Central Mic Control + Live Waveform */}
      <div className="py-5 flex flex-col items-center text-center">
        {/* Status Pill */}
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border mb-4 ${badgeClass}`}
        >
          {interactionState === 'connecting' || interactionState === 'processing' ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          ) : interactionState === 'speaking' ? (
            <Volume2 className="h-3.5 w-3.5" aria-hidden="true" />
          ) : interactionState === 'error' ? (
            <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" />
          ) : interactionState === 'completed' ? (
            <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
          ) : null}
          <span>{stateLabels[interactionState]}</span>
        </span>

        {/* Primary Microphone Action */}
        {!isSessionActive ? (
          <div className="flex flex-col items-center gap-3 w-full">
            <button
              type="button"
              onClick={onStartRecording}
              className="w-full sm:w-auto min-w-[240px] min-h-[64px] px-8 py-4 rounded-2xl bg-clinical-primary hover:bg-clinical-primary-dark text-white font-bold text-base sm:text-lg shadow-lg transition-all active:scale-95 flex items-center justify-center gap-3 group"
            >
              <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                <Mic className="h-6 w-6" aria-hidden="true" />
              </div>
              <span>{ui.startRecording}</span>
            </button>

            {/* Ambient HealthWave & Indic numeral hint in idle state */}
            <div className="w-full max-w-sm flex flex-col items-center gap-1.5 pt-2">
              <HealthWave width={300} height={32} color="#0D9488" opacity={0.35} />
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-50 border border-slate-200 text-[11px] font-semibold text-slate-600">
                <Sparkles className="h-3 w-3 text-teal-600 shrink-0" />
                <span>Indic Numerals: &ldquo;वजन २.५ किलो&rdquo; or &ldquo;2.5 kg&rdquo; normalized cleanly</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4 w-full">
            {/* Live Mic / Push-to-Talk Circle with Concentric Radar Pulse */}
            <div className="flex items-center justify-center gap-5 flex-wrap">
              {handsFree ? (
                <div className="relative flex items-center justify-center">
                  {/* Concentric Animated Radar Rings */}
                  <motion.div
                    className="absolute w-24 h-24 rounded-full border-2 border-emerald-500/40 pointer-events-none"
                    animate={{ scale: [1, 1.45, 1.8], opacity: [0.8, 0.3, 0] }}
                    transition={{ duration: 2.0, repeat: Infinity, ease: 'easeOut' }}
                  />
                  <motion.div
                    className="absolute w-20 h-20 rounded-full bg-emerald-400/20 blur-sm pointer-events-none"
                    animate={{ scale: [1, 1.25, 1], opacity: [0.3, 0.7, 0.3] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                  />
                  <div
                    className={`relative w-20 h-20 rounded-full flex items-center justify-center transition-all shadow-md ${
                      interactionState === 'speaking'
                        ? 'bg-indigo-600 text-white'
                        : interactionState === 'error'
                        ? 'bg-clinical-danger text-white'
                        : 'bg-emerald-600 text-white animate-mic-active'
                    }`}
                    aria-label="Live microphone active"
                  >
                    {interactionState === 'speaking' ? (
                      <Volume2 className="h-9 w-9" aria-hidden="true" />
                    ) : (
                      <Mic className="h-9 w-9" aria-hidden="true" />
                    )}
                  </div>
                </div>
              ) : (
                <div className="relative flex items-center justify-center">
                  {pttPressed && (
                    <motion.div
                      className="absolute w-28 h-28 rounded-full border-2 border-red-500/40 pointer-events-none"
                      animate={{ scale: [1, 1.4, 1.7], opacity: [0.8, 0.3, 0] }}
                      transition={{ duration: 1.6, repeat: Infinity, ease: 'easeOut' }}
                    />
                  )}
                  <button
                    type="button"
                    onPointerDown={onPttDown}
                    onPointerUp={onPttUp}
                    onPointerCancel={onPttUp}
                    onPointerLeave={onPttUp}
                    aria-pressed={pttPressed}
                    className={`relative w-24 h-24 rounded-full flex flex-col items-center justify-center font-bold text-xs transition-all select-none shadow-md ${
                      pttPressed
                        ? 'bg-clinical-danger text-white scale-95 animate-mic-active'
                        : 'bg-slate-800 hover:bg-slate-700 text-white'
                    }`}
                  >
                    {pttPressed ? (
                      <Mic className="h-8 w-8 mb-1" aria-hidden="true" />
                    ) : (
                      <MicOff className="h-7 w-7 mb-1" aria-hidden="true" />
                    )}
                    <span>{pttPressed ? (ui.speakingShortLabel || 'Speaking') : (ui.holdToSpeak || 'Hold to Talk')}</span>
                  </button>
                </div>
              )}

              {/* Interrupt / Barge-In Button */}
              {interactionState === 'speaking' && (
                <button
                  type="button"
                  onClick={onBargeIn}
                  className="px-4 py-3 rounded-xl bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-sm shadow-md flex items-center gap-2 active:scale-95 transition-all"
                >
                  <FastForward className="h-4 w-4" aria-hidden="true" />
                  <span>{ui.bargeInInterrupt}</span>
                </button>
              )}

              {/* Stop Session Button */}
              <button
                type="button"
                onClick={onStopRecording}
                className="px-4 py-3 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-800 font-bold text-sm flex items-center gap-2 active:scale-95 transition-all"
              >
                <Square className="h-4 w-4 fill-current" aria-hidden="true" />
                <span>{ui.stopRecording}</span>
              </button>
            </div>

            {/* Animated Vitals HealthWave Card with dynamic color & micro-interaction */}
            <div className="w-full max-w-md p-3.5 rounded-2xl bg-gradient-to-r from-teal-50/80 via-emerald-50/60 to-cyan-50/80 border border-teal-200/90 shadow-sm flex flex-col items-center gap-2 transition-colors">
              <div className="flex items-center justify-between w-full px-2 text-[11px] font-bold">
                <div className="flex items-center gap-1.5 text-teal-900">
                  <Activity className="h-3.5 w-3.5 text-teal-600 animate-pulse" />
                  <span>Vitals Audio Stream · Active Health Monitoring</span>
                </div>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-white/90 border border-teal-200 text-teal-800 shadow-2xs">
                  {interactionState === 'speaking'
                    ? 'Timbre TTS'
                    : interactionState === 'interrupted'
                    ? 'Barge-In Active'
                    : '16kHz PCM Live'}
                </span>
              </div>

              <div className="overflow-hidden w-full flex justify-center py-0.5">
                <HealthWave
                  width={340}
                  height={40}
                  color={
                    interactionState === 'speaking'
                      ? '#6366F1'
                      : interactionState === 'interrupted'
                      ? '#F59E0B'
                      : interactionState === 'error'
                      ? '#EF4444'
                      : '#0D9488'
                  }
                  opacity={0.85}
                />
              </div>

              {/* Real Web Audio Waveform Visualizer (amplitude reacting) */}
              <div
                className="w-full h-8 bg-white/90 border border-teal-100 rounded-xl px-3 flex items-center justify-center gap-1.5 shadow-inner"
                aria-hidden="true"
              >
                {waveformBands.map((band, idx) => {
                  const heightPct = isConnected
                    ? Math.max(15, Math.min(95, Math.round((band * 0.7 + audioLevel * 0.3) * 100)))
                    : 10;
                  return (
                    <span
                      key={idx}
                      className={`w-1 rounded-full transition-all duration-75 ${
                        interactionState === 'speaking'
                          ? 'bg-indigo-500'
                          : audioLevel > 0.08
                          ? 'bg-clinical-primary'
                          : 'bg-slate-300'
                      }`}
                      style={{ height: `${heightPct}%` }}
                    />
                  );
                })}
              </div>
            </div>
          </div>
        )}

        <p className="text-xs text-clinical-text-secondary mt-3 max-w-md">{helperText}</p>
      </div>

      {/* Mode & Mic Hardware Controls */}
      <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-600">{ui.micModeLabel}:</span>
          <div className="inline-flex bg-slate-100 p-0.5 rounded-lg border border-slate-200">
            <button
              type="button"
              onClick={() => onToggleHandsFree(true)}
              className={`compact-chip px-2.5 py-1 rounded-md font-semibold ${
                handsFree ? 'bg-white text-clinical-primary shadow-sm' : 'text-slate-600'
              }`}
            >
              {ui.handsFreeLabel}
            </button>
            <button
              type="button"
              onClick={() => onToggleHandsFree(false)}
              className={`compact-chip px-2.5 py-1 rounded-md font-semibold ${
                !handsFree ? 'bg-white text-clinical-primary shadow-sm' : 'text-slate-600'
              }`}
            >
              {ui.pushToTalkLabel}
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {inputDevices.length > 0 && (
            <div>
              <label htmlFor="audio-input-select" className="sr-only">
                Microphone device
              </label>
              <select
                id="audio-input-select"
                value={selectedDeviceId}
                onChange={(e) => onSelectDevice(e.target.value)}
                disabled={isSessionActive}
                className="px-2.5 py-1 rounded-lg border border-slate-200 bg-slate-50 text-xs text-slate-700 max-w-[180px]"
              >
                <option value="default">{ui.defaultMicrophone}</option>
                {inputDevices.map((d) => (
                  <option key={d.deviceId} value={d.deviceId}>
                    {d.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {onSendTextUtterance && (
            <button
              type="button"
              onClick={() => setShowTextFallback(!showTextFallback)}
              className="compact-chip inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 font-semibold"
            >
              <Keyboard className="h-3.5 w-3.5" aria-hidden="true" />
              <span>{ui.typeToBackend}</span>
            </button>
          )}
        </div>
      </div>

      {/* Accessibility / Testing Backend Text Input (routes directly to Agent 1 WS text_input) */}
      {showTextFallback && onSendTextUtterance && (
        <form onSubmit={handleTextSubmit} className="mt-3 pt-3 border-t border-slate-100 flex gap-2">
          <label htmlFor="ws-text-utterance" className="sr-only">
            {ui.typeToBackend}
          </label>
          <input
            id="ws-text-utterance"
            type="text"
            value={typedUtterance}
            onChange={(e) => setTypedUtterance(e.target.value)}
            disabled={!isConnected}
            placeholder={
              isConnected ? ui.typeUtterancePlaceholder : ui.startSessionToTypePlaceholder
            }
            className="flex-1 px-3 py-2 rounded-xl border border-slate-300 text-xs bg-white disabled:bg-slate-100"
          />
          <button
            type="submit"
            disabled={!isConnected || !typedUtterance.trim()}
            className="px-3.5 py-2 rounded-xl bg-clinical-primary text-white text-xs font-bold flex items-center gap-1.5 disabled:opacity-40"
          >
            <Send className="h-3.5 w-3.5" aria-hidden="true" />
            <span>{ui.sendText}</span>
          </button>
        </form>
      )}
    </section>
  );
};

export const LiveTranscript: React.FC<{
  history: TranscriptLine[];
  partialStable: string;
  partialVolatile: string;
  language: string;
}> = ({ history, partialStable, partialVolatile, language }) => {
  const { ui } = useTranslation(language);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
    if (nearBottom) {
      el.scrollTop = el.scrollHeight;
    }
  }, [history.length, partialStable, partialVolatile]);

  return (
    <section
      aria-label={ui.liveTranscriptHeading}
      className="bg-white border border-clinical-border-subtle rounded-2xl p-4 shadow-sm"
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-clinical-text">{ui.liveTranscriptHeading}</h3>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold">
          {language}
        </span>
      </div>

      <div
        ref={scrollRef}
        aria-live="polite"
        className="max-h-64 overflow-y-auto space-y-2.5 pr-1"
      >
        {history.length === 0 && !partialStable && !partialVolatile && (
          <p className="text-xs text-slate-500 italic py-4 text-center">
            {ui.liveTranscriptPlaceholder}
          </p>
        )}

        {history.map((line) => {
          const isAsha = line.role === 'asha';
          const isDanger = line.role === 'danger';
          return (
            <div
              key={line.id}
              className={`p-3 rounded-xl border text-sm leading-relaxed ${
                isDanger
                  ? 'bg-red-50 border-red-300 text-red-950'
                  : isAsha
                  ? 'bg-slate-50 border-slate-200 text-clinical-text ml-0 sm:mr-8'
                  : 'bg-teal-50/70 border-teal-200 text-teal-950 sm:ml-8'
              }`}
            >
              <div className="flex items-center justify-between gap-2 text-[11px] font-bold mb-1">
                <span className={isDanger ? 'text-red-800' : isAsha ? 'text-slate-600' : 'text-clinical-primary-dark'}>
                  {isDanger
                    ? ui.urgentReferralSpeechLabel
                    : isAsha
                    ? ui.ashaWorkerLabel
                    : ui.sakshyaAssistantLabel}
                </span>
                {line.latency_ms !== undefined && line.latency_ms !== null && (
                  <span className="text-slate-400 font-mono">{Math.round(line.latency_ms)}ms</span>
                )}
              </div>
              <p className="text-sm leading-relaxed">{line.text}</p>
            </div>
          );
        })}

        {/* Streaming Partial Transcription: stable normal text + volatile italic text */}
        {(partialStable || partialVolatile) && (
          <div className="p-3 rounded-xl border border-dashed border-clinical-secondary bg-sky-50/50 text-sm">
            <span className="block text-[10px] font-bold uppercase tracking-wider text-clinical-secondary mb-1">
              {ui.listeningLiveLabel}
            </span>
            <p className="text-clinical-text">
              <span>{partialStable}</span>
              {partialVolatile && (
                <span className="text-clinical-secondary italic">
                  {partialStable ? ' ' : ''}
                  {partialVolatile}
                </span>
              )}
            </p>
          </div>
        )}
      </div>
    </section>
  );
};

export const ProcessingIndicator: React.FC<{ active: boolean; message?: string }> = ({
  active,
  message,
}) => {
  const { ui } = useTranslation();
  if (!active) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="p-4 rounded-xl bg-teal-50 border border-teal-300 flex items-center gap-3 text-teal-950"
    >
      <RefreshCw className="h-5 w-5 text-clinical-primary animate-spin shrink-0" aria-hidden="true" />
      <div>
        <p className="text-sm font-bold">{ui.processingVisitNotesTitle}</p>
        <p className="text-xs text-teal-800">{message || ui.processingVisitNotesDesc}</p>
      </div>
    </div>
  );
};

