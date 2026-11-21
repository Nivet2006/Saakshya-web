'use client';

import React from 'react';
import { useTranslation } from '@/lib/i18n/LanguageContext';
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

  const LANGUAGE_CHIPS: Array<{ code: LanguageCode; native: string; label: string }> = [
    { code: 'ml-IN', native: 'മലയാളം', label: 'മലയാളം (Malayalam)' },
    { code: 'hi-IN', native: 'हिन्दी', label: 'हिन्दी (Hindi)' },
    { code: 'kn-IN', native: 'ಕನ್ನಡ', label: 'ಕನ್ನಡ (Kannada)' },
    { code: 'ta-IN', native: 'தமிழ்', label: 'தமிழ் (Tamil)' },
    { code: 'te-IN', native: 'తెలుగు', label: 'తెలుగు (Telugu)' },
    { code: 'bn-IN', native: 'বাংলা', label: 'বাংলা (Bengali)' },
    { code: 'mr-IN', native: 'मराठी', label: 'मराठी (Marathi)' },
    { code: 'gu-IN', native: 'ગુજરાતી', label: 'ગુજરાતી (Gujarati)' },
    { code: 'pa-IN', native: 'ਪੰਜਾਬੀ', label: 'ਪੰਜਾਬੀ (Punjabi)' },
    { code: 'en-IN', native: 'English (India)', label: 'English (India)' },
    { code: 'indic-auto', native: 'Auto-Indic', label: 'Auto-Indic (Mixed)' },
  ];

  return (
    <section
      aria-labelledby="language-step-heading"
      className="bg-white border border-clinical-border-subtle rounded-xl p-4 sm:p-5 shadow-sm"
    >
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

      {/* Direct one-tap button chips for all Indic languages + English + Auto-Indic */}
      <div className="mt-3 flex items-center gap-2 flex-wrap" role="group" aria-label="Speaking language selection">
        {LANGUAGE_CHIPS.map((lang) => {
          const active = selectedLanguage === lang.code;
          return (
            <button
              key={lang.code}
              type="button"
              disabled={disabled}
              aria-pressed={active}
              onClick={() => onChange(lang.code)}
              className={`compact-chip px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
                active
                  ? 'bg-clinical-primary text-white border-clinical-primary shadow-sm font-bold'
                  : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
              }`}
            >
              {lang.label}
            </button>
          );
        })}
      </div>
    </section>
  );
};

