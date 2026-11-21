'use client';

import React, { createContext, useContext, useEffect } from 'react';
import { getUiStrings, type UiStrings } from '@/lib/i18n/ui-translations';
import { TRANSLATIONS, type Translations } from '@/lib/translations';
import type { LanguageCode } from '@/types';

interface LanguageContextValue {
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
  ui: UiStrings;
  t: Translations;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export const LanguageProvider: React.FC<{
  language: LanguageCode;
  onLanguageChange: (lang: LanguageCode) => void;
  children: React.ReactNode;
}> = ({ language, onLanguageChange, children }) => {
  const ui = getUiStrings(language);
  const t = TRANSLATIONS[language] || TRANSLATIONS['en-IN'];

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.lang = language === 'indic-auto' ? 'en-IN' : language;
    }
  }, [language]);

  return (
    <LanguageContext.Provider
      value={{
        language,
        setLanguage: onLanguageChange,
        ui,
        t,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
};

export function useTranslation(overrideLanguage?: LanguageCode): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (ctx && !overrideLanguage) {
    return ctx;
  }
  const effectiveLang = overrideLanguage || ctx?.language || 'hi-IN';
  return {
    language: effectiveLang,
    setLanguage: ctx?.setLanguage || (() => {}),
    ui: getUiStrings(effectiveLang),
    t: TRANSLATIONS[effectiveLang] || TRANSLATIONS['en-IN'],
  };
}

