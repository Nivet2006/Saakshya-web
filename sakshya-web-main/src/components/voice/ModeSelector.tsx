'use client';

import React from 'react';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type { AshaExperienceMode } from '@/types';
import { Layers, Mic } from 'lucide-react';

interface ModeSelectorProps {
  mode: AshaExperienceMode;
  onChange: (mode: AshaExperienceMode) => void;
}

export const ModeSelector: React.FC<ModeSelectorProps> = ({ mode, onChange }) => {
  const { ui } = useTranslation();
  return (
    <div
      role="group"
      aria-label="Experience Mode Selection"
      className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5"
    >
      <button
        type="button"
        onClick={() => onChange('basic')}
        aria-pressed={mode === 'basic'}
        className={`text-left p-3.5 sm:p-4 rounded-xl border-2 transition-all flex items-start gap-3 ${
          mode === 'basic'
            ? 'border-clinical-primary bg-teal-50/70 shadow-sm'
            : 'border-slate-200 bg-white hover:border-slate-300'
        }`}
      >
        <div
          className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
            mode === 'basic'
              ? 'bg-clinical-primary text-white'
              : 'bg-slate-100 text-slate-600'
          }`}
        >
          <Mic className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-bold text-clinical-text">{ui.basicModeTitle}</span>
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-clinical-primary text-white">
              {ui.basicModeBadge}
            </span>
          </div>
          <p className="text-xs text-clinical-text-secondary mt-1 leading-relaxed">
            {ui.basicModeDesc}
          </p>
        </div>
      </button>

      <button
        type="button"
        onClick={() => onChange('advanced')}
        aria-pressed={mode === 'advanced'}
        className={`text-left p-3.5 sm:p-4 rounded-xl border-2 transition-all flex items-start gap-3 ${
          mode === 'advanced'
            ? 'border-clinical-secondary bg-sky-50/70 shadow-sm'
            : 'border-slate-200 bg-white hover:border-slate-300'
        }`}
      >
        <div
          className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
            mode === 'advanced'
              ? 'bg-clinical-secondary text-white'
              : 'bg-slate-100 text-slate-600'
          }`}
        >
          <Layers className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-bold text-clinical-text">{ui.advancedModeTitle}</span>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
              {ui.advancedModeBadge}
            </span>
          </div>
          <p className="text-xs text-clinical-text-secondary mt-1 leading-relaxed">
            {ui.advancedModeDesc}
          </p>
        </div>
      </button>
    </div>
  );
};

