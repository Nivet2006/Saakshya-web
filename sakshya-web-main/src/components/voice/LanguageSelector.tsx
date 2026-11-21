'use client';

import React from 'react';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import { PRISMA_LANGUAGES } from '@/lib/translations';
import type { LanguageCode } from '@/types';
import { Globe } from 'lucide-react';

interface LanguageSelectorProps {
  selectedLanguage: LanguageCode;
  onChange: (lang: LanguageCode) => void;
  disabled?: boolean;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  selectedLanguage,
  onChange,
  disabled = false,
}) => {
  const { ui } = useTranslation(selectedLanguage);
  return (
    <section
      aria-labelledby="language-step-heading"
      className="bg-white border border-clinical-border-subtle rounded-xl p-4 sm:p-5 shadow-sm"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-sky-50 text-clinical-secondary flex items-center justify-center shrink-0">
            <Globe className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <h2 id="language-step-heading" className="text-sm sm:text-base font-bold text-clinical-text">
              {ui.step2Title}
            </h2>
            <p className="text-xs text-clinical-text-secondary">
              {ui.step2Subtitle}
            </p>
          </div>
        </div>

        <div className="sm:w-64">
          <label htmlFor="visit-language-select" className="sr-only">
            Voice recognition language
          </label>
          <select
            id="visit-language-select"
            disabled={disabled}
            value={selectedLanguage}
            onChange={(e) => onChange(e.target.value)}
            className="w-full px-3.5 py-2.5 rounded-xl border border-clinical-border bg-slate-50 text-sm font-semibold text-clinical-text"
          >
            {PRISMA_LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.nativeName} ({l.name})
              </option>
            ))}
            <option value="indic-auto">{ui.autoDetectIndic}</option>
          </select>
        </div>
      </div>

      {/* Quick one-tap pills for most frequent languages */}
      <div className="mt-3 flex items-center gap-2 flex-wrap">
        {['hi-IN', 'kn-IN', 'ta-IN', 'te-IN', 'en-IN', 'indic-auto'].map((code) => {
          const info = PRISMA_LANGUAGES.find((l) => l.code === code);
          const label = info ? info.nativeName : ui.autoDetectIndic;
          const active = selectedLanguage === code;
          return (
            <button
              key={code}
              type="button"
              disabled={disabled}
              aria-pressed={active}
              onClick={() => onChange(code)}
              className={`compact-chip px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
                active
                  ? 'bg-clinical-primary text-white border-clinical-primary'
                  : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>
    </section>
  );
};

