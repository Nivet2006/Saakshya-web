'use client';

import React, { useState, useEffect, useRef, useTransition } from 'react';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type { Beneficiary, BeneficiaryCategory, LanguageCode } from '@/types';
import {
  UserPlus,
  X,
  Mic,
  MicOff,
  Keyboard,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Volume2,
  RefreshCw,
} from 'lucide-react';

export interface NewPatientInput {
  full_name: string;
  category: BeneficiaryCategory;
  age_years: number;
  village: string;
  household_head?: string;
  phone_number?: string;
  edd_date?: string;
  high_risk_status: boolean;
  preferred_language: LanguageCode;
}

interface AddPatientModalProps {
  open: boolean;
  defaultLanguage: LanguageCode;
  onClose: () => void;
  onSave: (input: NewPatientInput) => Promise<Beneficiary>;
}

// Indic numeral conversion
function normalizeIndicDigits(text: string): string {
  const indicDigits = '०१२३४५६७८९';
  return text.replace(/[०-९]/g, (ch) => String(indicDigits.indexOf(ch)));
}

// Normalizes common spoken Hindi/English numbers for ages
function parseSpokenAge(raw: string): number | null {
  const normalized = normalizeIndicDigits(raw).toLowerCase();
  const digitMatch = normalized.match(/\b\d{1,2}\b/);
  if (digitMatch) {
    const n = parseInt(digitMatch[0], 10);
    if (!isNaN(n) && n >= 0 && n <= 100) return n;
  }

  const wordMap: Record<string, number> = {
    शून्य: 0,
    zero: 0,
    एक: 1,
    one: 1,
    दो: 2,
    two: 2,
    तीन: 3,
    three: 3,
    चार: 4,
    four: 4,
    पांच: 5,
    पाँच: 5,
    five: 5,
    छह: 6,
    six: 6,
    सात: 7,
    seven: 7,
    आठ: 8,
    eight: 8,
    नौ: 9,
    nine: 9,
    दस: 10,
    ten: 10,
    ग्यारह: 11,
    eleven: 11,
    बारह: 12,
    twelve: 12,
    तेरह: 13,
    thirteen: 13,
    चौदह: 14,
    fourteen: 14,
    पंद्रह: 15,
    fifteen: 15,
    सोलह: 16,
    sixteen: 16,
    सत्रह: 17,
    seventeen: 17,
    अट्ठारह: 18,
    eighteen: 18,
    उन्नीस: 19,
    nineteen: 19,
    बीस: 20,
    twenty: 20,
    इक्कीस: 21,
    बाईस: 22,
    तेईस: 23,
    चौबीस: 24,
    पच्चीस: 25,
    छब्बीस: 26,
    सत्ताईस: 27,
    अट्ठाईस: 28,
    उनतीस: 29,
    तीस: 30,
    thirty: 30,
    इकतीस: 31,
    बत्तीस: 32,
    तैंतीस: 33,
    चौंतीस: 34,
    पैंतीस: 35,
    छ्त्तीस: 36,
    सैंतीस: 37,
    अड़तीस: 38,
    उनतालीस: 39,
    चालीस: 40,
    forty: 40,
    पैंतालीस: 45,
    पचास: 50,
  };

  for (const [word, val] of Object.entries(wordMap)) {
    if (normalized.includes(word)) return val;
  }
  return null;
}

// Deterministic parser for spoken patient registration in Indic & English
export function parseSpokenPatientText(rawText: string) {
  const text = normalizeIndicDigits(rawText);
  const result: Partial<NewPatientInput> & { detectedFields: string[] } = {
    detectedFields: [],
  };

  // 1. Patient Name
  // Matches: नाम [है] <Name> | name [is] <Name> | रोगी/मरीज़ <Name> | patient [name is] <Name>
  const namePatterns = [
    /(?:नाम|name\s*(?:is)?|mariiz|mariz|rogi|मरीज़|मरीज|रोगी|पेशेंट|patient\s*(?:name)?)\s*(?:hai|is|ka\s*naam)?[:\s]+([^\d,\.\n]+?)(?=\s*(?:उम्र|age|saal|sal|वर्ष|varsh|years|साल|category|ward|गाँव|गांव|village|phone|फोन|mobile|मोबाइल|husband|पति|पिता|father|head|खतरा|high\s*risk|edd|$))/i,
    /(?:श्रीमती|mrs\.?|miss|shrimati)\s+([^\d,\.\n]+?)(?=\s*(?:उम्र|age|saal|sal|वर्ष|years|गाँव|गांव|village|phone|फोन|पति|husband|$))/i,
  ];

  for (const pat of namePatterns) {
    const m = text.match(pat);
    if (m && m[1]?.trim()) {
      let candidate = m[1].trim();
      candidate = candidate.replace(/^(is|hai|का\s*नाम|hai\s*ki)\s+/i, '').trim();
      if (candidate.length >= 2) {
        result.full_name = candidate;
        result.detectedFields.push('Name (' + candidate + ')');
        break;
      }
    }
  }

  // 2. Age
  // Matches: उम्र 24 साल | age 25 years | 26 वर्ष | आयु 28
  const agePatterns = [
    /(?:उम्र|age|आयु|aayu)\s*(?:hai|is)?[:\s]*([^\s,\.\n]+(?:\s*(?:साल|वर्ष|sal|saal|varsh|years|yrs))?)/i,
    /(\d+|[०-९]+)\s*(?:साल|वर्ष|sal|saal|varsh|years|yrs)/i,
  ];

  for (const pat of agePatterns) {
    const m = text.match(pat);
    if (m && m[1]) {
      const parsedAge = parseSpokenAge(m[1]);
      if (parsedAge !== null) {
        result.age_years = parsedAge;
        result.detectedFields.push(`Age (${parsedAge})`);
        break;
      }
    }
  }

  // 3. Category
  // Pregnant / ANC
  if (
    /(?:pregnant|garbhavati|garbhvati|गर्भवती|गर्भावती|पेट से|anc|गर्भावस्था|garbhavastha|ಗರ್ಭಿಣಿ|கர்ப்பிணி|గర్భిణి)/i.test(
      text
    )
  ) {
    result.category = 'PREGNANT_WOMAN';
    result.detectedFields.push('Category (Pregnant Woman / ANC)');
  }
  // Lactating / PNC
  else if (
    /(?:lactating|dhatri|धात्री|स्तनपान|stanpan|pnc|postnatal|shishu ki maa|दूध पिलाने|ಹಾಲುಣಿಸುವ|தாய்ப்பால்|తల్లి)/i.test(
      text
    )
  ) {
    result.category = 'LACTATING_MOTHER';
    result.detectedFields.push('Category (Lactating Mother / PNC)');
  }
  // Infant / Newborn
  else if (
    /(?:newborn|infant|shishu|शिशु|नवजात|navjaat|navjat|baby|नवजात शिशु|ನವಜಾತ|பிறந்த குழந்தை|శిశువు)/i.test(
      text
    )
  ) {
    result.category = 'INFANT';
    result.detectedFields.push('Category (Infant / Newborn)');
    if (result.age_years === undefined) result.age_years = 0;
  }
  // Child
  else if (
    /(?:child|baccha|balak|balkaa|बच्चा|बालक|baalika|balika|toddler|ಮಗು|குழந்தை|పిల్ల)/i.test(
      text
    )
  ) {
    result.category = 'CHILD';
    result.detectedFields.push('Category (Child)');
  }

  // 4. Village / Ward
  const villagePatterns = [
    /(?:गाँव|गांव|village|ward|वार्ड|nagar|नगर|colony|pura|ward\s*no\.?\s*\d+)\s*(?:hai|is)?[:\s]+([^\d,\.\n]+?(?:\s*(?:ward|वार्ड)\s*\d+)?)(?=\s*(?:उम्र|age|phone|फोन|mobile|मोबाइल|husband|पति|पिता|father|head|खतरा|high\s*risk|edd|$))/i,
    /(?:रहने\s*वाली|from)\s+([^\d,\.\n]+?)(?=\s*(?:उम्र|age|phone|फोन|पति|husband|$))/i,
  ];

  for (const pat of villagePatterns) {
    const m = text.match(pat);
    if (m && m[1]?.trim()) {
      let v = m[1].trim().replace(/^(is|hai|ki|se)\s+/i, '');
      if (v.length >= 2) {
        result.village = v;
        result.detectedFields.push(`Village (${v})`);
        break;
      }
    }
  }

  // 5. Household Head / Husband / Father
  const headPatterns = [
    /(?:पति|husband|pati|पिता|father|मुखिया|head|spouse)\s*(?:ka\s*naam|hai|is)?[:\s]+([^\d,\.\n]+?)(?=\s*(?:phone|फोन|mobile|मोबाइल|गाँव|गांव|village|उम्र|age|खतरा|high\s*risk|$))/i,
    /(?:wife\s*of|पत्नी)\s+([^\d,\.\n]+?)(?=\s*(?:phone|फोन|गाँव|गांव|village|$))/i,
  ];

  for (const pat of headPatterns) {
    const m = text.match(pat);
    if (m && m[1]?.trim()) {
      let h = m[1].trim().replace(/^(is|hai|ka|ke)\s+/i, '');
      if (h.length >= 2) {
        result.household_head = h;
        result.detectedFields.push(`Head/Husband (${h})`);
        break;
      }
    }
  }

  // 6. Phone Number (10 digits)
  const phonePatterns = [
    /(?:phone|फोन|mobile|मोबाइल|नंबर|number|tel)\s*(?:hai|is)?[:\s]*([0-9\s-]{10,14})/i,
    /\b([6-9]\d{4}\s*\d{5})\b/,
    /\b([6-9]\d{9})\b/,
  ];

  for (const pat of phonePatterns) {
    const m = text.match(pat);
    if (m && m[1]) {
      const cleanPhone = m[1].replace(/[\s-]/g, '');
      if (cleanPhone.length >= 10) {
        result.phone_number = cleanPhone;
        result.detectedFields.push(`Phone (${cleanPhone})`);
        break;
      }
    }
  }

  // 7. High Risk Status
  if (
    /(?:high\s*risk|हाई\s*रिस्क|खतरा|khatra|gambhīr|gambhir|गंभीर|complication|जोखिम|jokhim|अत्यधिक\s*जोखिम)/i.test(
      text
    )
  ) {
    result.high_risk_status = true;
    result.detectedFields.push('High Risk (Flagged)');
  }

  // 8. EDD Date (if mentioned)
  const eddMatch = text.match(/\b(202[6-9]-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))\b/);
  if (eddMatch) {
    result.edd_date = eddMatch[1];
    result.detectedFields.push(`EDD (${eddMatch[1]})`);
  }

  return result;
}

export const AddPatientModal: React.FC<AddPatientModalProps> = ({
  open,
  defaultLanguage,
  onClose,
  onSave,
}) => {
  const { ui } = useTranslation();

  // Mode: 'type' (manual keyboard input) vs 'speech' (voice input & auto-fill)
  const [mode, setMode] = useState<'type' | 'speech'>('type');

  // Form Fields State
  const [fullName, setFullName] = useState('');
  const [category, setCategory] = useState<BeneficiaryCategory>('PREGNANT_WOMAN');
  const [ageYears, setAgeYears] = useState('24');
  const [village, setVillage] = useState('Rampur Demo Ward 1');
  const [householdHead, setHouseholdHead] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [eddDate, setEddDate] = useState('');
  const [highRisk, setHighRisk] = useState(false);
  const [preferredLang, setPreferredLang] = useState<LanguageCode>(
    defaultLanguage === 'indic-auto' ? 'hi-IN' : defaultLanguage
  );
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Speech Recognition State
  const [isListening, setIsListening] = useState(false);
  const [speechTranscript, setSpeechTranscript] = useState('');
  const [speechLang, setSpeechLang] = useState<LanguageCode>(
    defaultLanguage === 'indic-auto' ? 'hi-IN' : defaultLanguage
  );
  const [speechSupported, setSpeechSupported] = useState(true);
  const [parsedSummary, setParsedSummary] = useState<string[]>([]);
  const recognitionRef = useRef<any>(null);

  // Check Web Speech API support
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const hasSpeech =
        'webkitSpeechRecognition' in window || 'SpeechRecognition' in (window as any);
      setSpeechSupported(hasSpeech);
    }
  }, []);

  // Cleanup speech recognition on unmount or close
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {}
      }
    };
  }, []);

  if (!open) return null;

  // Toggle Voice Recognition
  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const startListening = () => {
    setErrorMsg(null);
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setErrorMsg('Web Speech API is not supported in this browser. You can paste spoken text below.');
      return;
    }

    try {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {}
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = speechLang;

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event: any) => {
        let currentTranscript = '';
        for (let i = 0; i < event.results.length; i++) {
          currentTranscript += event.results[i][0].transcript + ' ';
        }
        setSpeechTranscript(currentTranscript);
        // Automatically parse in background
        applyParsedSpeech(currentTranscript);
      };

      recognition.onerror = (event: any) => {
        if (event.error !== 'no-speech') {
          console.warn('[AddPatient Speech Error]', event.error);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error('[AddPatient] Failed to start speech recognition:', err);
      setIsListening(false);
      setErrorMsg('Could not access microphone. Please check browser microphone permissions.');
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
    }
    setIsListening(false);
    if (speechTranscript) {
      applyParsedSpeech(speechTranscript);
    }
  };

  // Parses spoken transcript and populates form fields
  const applyParsedSpeech = (textToParse: string) => {
    if (!textToParse.trim()) return;
    const parsed = parseSpokenPatientText(textToParse);

    if (parsed.full_name) setFullName(parsed.full_name);
    if (parsed.category) setCategory(parsed.category);
    if (parsed.age_years !== undefined) setAgeYears(String(parsed.age_years));
    if (parsed.village) setVillage(parsed.village);
    if (parsed.household_head) setHouseholdHead(parsed.household_head);
    if (parsed.phone_number) setPhoneNumber(parsed.phone_number);
    if (parsed.edd_date) setEddDate(parsed.edd_date);
    if (parsed.high_risk_status !== undefined) setHighRisk(parsed.high_risk_status);

    if (parsed.detectedFields.length > 0) {
      setParsedSummary(parsed.detectedFields);
    }
  };

  // Quick fill sample templates for rapid testing / 1-tap demo
  const sampleVoicePrompts = [
    {
      lang: 'हिन्दी (Hindi)',
      text: 'नाम अनीता शर्मा, उम्र 24 साल, गर्भवती महिला, गांव रामपूर वार्ड 1, पति राहुल शर्मा, फोन 9876543210',
    },
    {
      lang: 'English / Hinglish',
      text: 'Name Priya Devi, age 26 years, pregnant woman, village Rampur Ward 2, husband Mohan Lal, high risk',
    },
    {
      lang: 'ಕನ್ನಡ (Kannada)',
      text: 'ಹೆಸರು ಕವಿತಾ ರಾವ್, ವಯಸ್ಸು 27, ಬಾಣಂತಿ, ಶಾಂತಿನಗರ ವಾರ್ಡ್ 2, ಪತಿ ಶ್ರೀನಿವಾಸ್, ಫೋನ್ 9000001043',
    },
    {
      lang: 'தமிழ் (Tamil)',
      text: 'பெயர் மீனா செல்வம், வயது 25, கர்ப்பிணி, கிராமம் காவேரி வார்டு 3, கணவர் செல்வம், போன் 9000001046',
    },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isListening) {
      stopListening();
    }
    const cleanName = fullName.trim();
    if (!cleanName) {
      setErrorMsg('Please enter or speak the patient name.');
      return;
    }
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await onSave({
        full_name: cleanName,
        category,
        age_years: Math.max(0, Number.parseInt(ageYears || '0', 10) || 0),
        village: village.trim() || 'Rampur Demo Ward 1',
        household_head: householdHead.trim() || undefined,
        phone_number: phoneNumber.trim() || undefined,
        edd_date: category === 'PREGNANT_WOMAN' && eddDate ? eddDate : undefined,
        high_risk_status: highRisk,
        preferred_language: preferredLang,
      });
      setFullName('');
      setHouseholdHead('');
      setPhoneNumber('');
      setEddDate('');
      setHighRisk(false);
      setSpeechTranscript('');
      setParsedSummary([]);
      onClose();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Could not save patient.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-patient-title"
      className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4 overflow-y-auto"
    >
      <div className="bg-white rounded-3xl max-w-xl w-full p-5 sm:p-6 shadow-2xl space-y-4 max-h-[94vh] flex flex-col border border-slate-100">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 pb-3 border-b border-slate-200 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-teal-50 text-clinical-primary flex items-center justify-center border border-teal-100 shadow-sm">
              <UserPlus className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 id="add-patient-title" className="text-lg font-bold text-clinical-text">
                {ui.addNewPatientTitle}
              </h2>
              <p className="text-xs text-slate-500">
                Register beneficiary into cloud database with zero typing option
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={ui.cancelLabel}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Input Mode Selector: Typing vs Speech */}
        <div className="grid grid-cols-2 gap-2 p-1 bg-slate-100 rounded-2xl shrink-0">
          <button
            type="button"
            onClick={() => setMode('type')}
            className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl font-bold text-xs transition-all ${
              mode === 'type'
                ? 'bg-white text-clinical-primary shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Keyboard className="h-4 w-4" />
            <span>Type Details</span>
          </button>
          <button
            type="button"
            onClick={() => setMode('speech')}
            className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl font-bold text-xs transition-all ${
              mode === 'speech'
                ? 'bg-gradient-to-r from-teal-600 to-emerald-600 text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Mic className="h-4 w-4" />
            <span>🎙️ Speak to Register (Voice Mode)</span>
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="overflow-y-auto space-y-4 pr-1 flex-1">
          {/* SPEECH REGISTRATION SECTION */}
          {mode === 'speech' && (
            <div className="p-4 rounded-2xl bg-gradient-to-br from-teal-50/70 via-emerald-50/40 to-slate-50 border border-teal-200/80 space-y-3">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="relative flex h-2.5 w-2.5">
                    {isListening && (
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                    )}
                    <span
                      className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                        isListening ? 'bg-rose-500' : 'bg-teal-500'
                      }`}
                    ></span>
                  </span>
                  <span className="text-xs font-bold text-slate-800">
                    {isListening ? 'Listening live... बोलिए...' : 'Voice Registration / बोलकर भरें'}
                  </span>
                </div>

                {/* Spoken Language Dropdown */}
                <select
                  value={speechLang}
                  onChange={(e) => setSpeechLang(e.target.value as LanguageCode)}
                  className="px-2 py-1 rounded-lg border border-teal-200 bg-white text-[11px] font-semibold text-slate-700"
                >
                  <option value="hi-IN">हिन्दी (Hindi)</option>
                  <option value="kn-IN">ಕನ್ನಡ (Kannada)</option>
                  <option value="ta-IN">தமிழ் (Tamil)</option>
                  <option value="te-IN">తెలుగు (Telugu)</option>
                  <option value="ml-IN">മലയാളം (Malayalam)</option>
                  <option value="mr-IN">मराठी (Marathi)</option>
                  <option value="bn-IN">বাংলা (Bengali)</option>
                  <option value="gu-IN">ગુજરાતી (Gujarati)</option>
                  <option value="pa-IN">ਪੰਜਾਬੀ (Punjabi)</option>
                  <option value="en-IN">English (India)</option>
                </select>
              </div>

              {/* Big Interactive Mic Action Button */}
              <div className="flex flex-col items-center justify-center py-2">
                <button
                  type="button"
                  onClick={toggleListening}
                  className={`relative flex items-center justify-center gap-3 px-6 py-3.5 rounded-full font-bold text-sm shadow-md transition-all transform active:scale-95 ${
                    isListening
                      ? 'bg-rose-600 hover:bg-rose-700 text-white animate-pulse'
                      : 'bg-clinical-primary hover:bg-clinical-primary-dark text-white'
                  }`}
                >
                  {isListening ? (
                    <>
                      <MicOff className="h-5 w-5" />
                      <span>Stop Listening / समाप्त करें</span>
                    </>
                  ) : (
                    <>
                      <Mic className="h-5 w-5" />
                      <span>Start Speaking / बोलना शुरू करें</span>
                    </>
                  )}
                </button>
                <p className="text-[11px] text-slate-500 mt-2 text-center">
                  {isListening
                    ? 'Speak name, age, category, village, and phone naturally.'
                    : 'Tap microphone and speak the patient details in one natural sentence.'}
                </p>
              </div>

              {/* Live Transcript Box */}
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">
                  Spoken Transcript / बोली गई बात:
                </label>
                <textarea
                  rows={2}
                  value={speechTranscript}
                  onChange={(e) => {
                    setSpeechTranscript(e.target.value);
                    applyParsedSpeech(e.target.value);
                  }}
                  placeholder="e.g. 'नाम अनीता शर्मा, उम्र 24 साल, गर्भवती महिला, गांव रामपूर वार्ड 1, पति राहुल शर्मा, फोन 9876543210'..."
                  className="w-full px-3 py-2 rounded-xl border border-teal-200 text-xs bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              {/* Parsed Fields Feedback Badge */}
              {parsedSummary.length > 0 && (
                <div className="p-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-[11px] flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold">
                      {parsedSummary.length} fields detected & auto-filled from speech:
                    </span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {parsedSummary.map((f, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-900 font-semibold text-[10px]"
                        >
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* 1-Tap Sample Voice Templates */}
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">
                  Or test with 1-click voice simulation:
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                  {sampleVoicePrompts.map((s, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => {
                        setSpeechTranscript(s.text);
                        applyParsedSpeech(s.text);
                      }}
                      className="text-left p-2 rounded-xl bg-white border border-slate-200 hover:border-teal-400 text-[11px] text-slate-700 transition-colors"
                    >
                      <span className="font-bold text-clinical-primary block text-[10px]">
                        {s.lang}
                      </span>
                      <span className="line-clamp-1 italic text-slate-600">{s.text}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* PATIENT DETAILS FORM (Populated by speech or keyboard) */}
          <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
            {errorMsg && (
              <div className="p-2.5 rounded-xl bg-red-50 border border-red-200 text-red-800 font-semibold flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div className="flex items-center justify-between pb-1 border-b border-slate-100">
              <span className="font-bold text-slate-700 uppercase tracking-wider text-[11px]">
                {mode === 'speech' ? 'Review Form Fields Before Saving' : 'Enter Beneficiary Details'}
              </span>
              {mode === 'speech' && (
                <span className="text-[10px] text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                  Auto-populated from Voice
                </span>
              )}
            </div>

            <div>
              <label htmlFor="np-name" className="block font-bold text-slate-700 mb-1">
                {ui.patientNameLabel} *
              </label>
              <input
                id="np-name"
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g. Anita Sharma / अनीता शर्मा"
                className="w-full px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor="np-category" className="block font-bold text-slate-700 mb-1">
                  {ui.patientCategoryLabel}
                </label>
                <select
                  id="np-category"
                  value={category}
                  onChange={(e) => {
                    const next = e.target.value as BeneficiaryCategory;
                    setCategory(next);
                    if (next === 'INFANT') setAgeYears('0');
                    else if (ageYears === '0') setAgeYears('24');
                  }}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs font-semibold bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                >
                  <option value="PREGNANT_WOMAN">{ui.ancFilter}</option>
                  <option value="LACTATING_MOTHER">{ui.pncFilter}</option>
                  <option value="INFANT">{ui.infantFilter}</option>
                  <option value="CHILD">{ui.childFilter}</option>
                </select>
              </div>

              <div>
                <label htmlFor="np-age" className="block font-bold text-slate-700 mb-1">
                  {ui.patientAgeLabel}
                </label>
                <input
                  id="np-age"
                  type="number"
                  min={0}
                  max={99}
                  value={ageYears}
                  onChange={(e) => setAgeYears(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor="np-village" className="block font-bold text-slate-700 mb-1">
                  {ui.villageWardLabel}
                </label>
                <input
                  id="np-village"
                  type="text"
                  value={village}
                  onChange={(e) => setVillage(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div>
                <label htmlFor="np-lang" className="block font-bold text-slate-700 mb-1">
                  {ui.languageLabel}
                </label>
                <select
                  id="np-lang"
                  value={preferredLang}
                  onChange={(e) => setPreferredLang(e.target.value as LanguageCode)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs font-semibold bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                >
                  <option value="hi-IN">हिन्दी (Hindi)</option>
                  <option value="ta-IN">தமிழ் (Tamil)</option>
                  <option value="kn-IN">ಕನ್ನಡ (Kannada)</option>
                  <option value="te-IN">తెలుగు (Telugu)</option>
                  <option value="ml-IN">മലയാളം (Malayalam)</option>
                  <option value="bn-IN">বাংলা (Bengali)</option>
                  <option value="mr-IN">मराठी (Marathi)</option>
                  <option value="gu-IN">ગુજરાતી (Gujarati)</option>
                  <option value="pa-IN">ਪੰਜਾਬੀ (Punjabi)</option>
                  <option value="en-IN">English (India)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor="np-head" className="block font-bold text-slate-700 mb-1">
                  {ui.householdHead}
                </label>
                <input
                  id="np-head"
                  type="text"
                  value={householdHead}
                  onChange={(e) => setHouseholdHead(e.target.value)}
                  placeholder="e.g. Rahul Sharma"
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div>
                <label htmlFor="np-phone" className="block font-bold text-slate-700 mb-1">
                  {ui.phoneOptionalLabel}
                </label>
                <input
                  id="np-phone"
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="98765-00000"
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
            </div>

            {category === 'PREGNANT_WOMAN' && (
              <div>
                <label htmlFor="np-edd" className="block font-bold text-slate-700 mb-1">
                  {ui.eddLabel}
                </label>
                <input
                  id="np-edd"
                  type="date"
                  value={eddDate}
                  onChange={(e) => setEddDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
            )}

            <label className="flex items-center gap-2 pt-1 cursor-pointer">
              <input
                type="checkbox"
                checked={highRisk}
                onChange={(e) => setHighRisk(e.target.checked)}
                className="rounded border-slate-300 text-rose-600 focus:ring-rose-500 h-4 w-4"
              />
              <span className="font-semibold text-slate-700">{ui.highRiskPatientLabel}</span>
            </label>

            {/* Modal Actions */}
            <div className="pt-3 border-t border-slate-200 flex justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2.5 rounded-xl border border-slate-300 text-slate-700 font-bold hover:bg-slate-50 transition-colors"
              >
                {ui.cancelLabel}
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-5 py-2.5 rounded-xl bg-clinical-primary hover:bg-clinical-primary-dark text-white font-bold disabled:opacity-60 flex items-center gap-2 shadow-sm transition-all"
              >
                {submitting ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>{ui.savingVisitBtn}</span>
                  </>
                ) : (
                  <>
                    <UserPlus className="h-4 w-4" />
                    <span>{ui.savePatientBtn}</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
