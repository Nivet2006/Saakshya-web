'use client';

import React, { useEffect, useState } from 'react';
import { Globe, Languages, Sparkles } from 'lucide-react';

declare global {
  interface Window {
    google: any;
    googleTranslateElementInit: any;
  }
}

interface GoogleTranslateWidgetProps {
  onLanguageChange?: (lang: string) => void;
}

export const GoogleTranslateWidget: React.FC<GoogleTranslateWidgetProps> = ({ onLanguageChange }) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    // Check if script already exists
    if (!document.getElementById('google-translate-script')) {
      window.googleTranslateElementInit = () => {
        if (window.google && window.google.translate) {
          new window.google.translate.TranslateElement(
            {
              pageLanguage: 'en',
              layout: window.google.translate.TranslateElement.InlineLayout.SIMPLE,
              autoDisplay: false,
            },
            'google_translate_element'
          );
          setIsLoaded(true);
        }
      };

      const script = document.createElement('script');
      script.id = 'google-translate-script';
      script.type = 'text/javascript';
      script.src = '//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
      script.async = true;
      document.body.appendChild(script);
    } else if (window.google && window.google.translate) {
      setIsLoaded(true);
    }
  }, []);

  return (
    <div className="relative inline-block text-left notranslate">
      {/* Hidden/Styled target container for Google Translate element */}
      <div
        id="google_translate_element"
        className="text-xs"
        style={{
          display: 'inline-block',
          verticalAlign: 'middle',
        }}
      />
    </div>
  );
};
