import type { FollowUpTask, LanguageCode } from '@/types';

type NormalizedLang =
  | 'hi-IN'
  | 'kn-IN'
  | 'ta-IN'
  | 'te-IN'
  | 'ml-IN'
  | 'bn-IN'
  | 'mr-IN'
  | 'gu-IN'
  | 'pa-IN'
  | 'en-IN';

function resolveLang(lang?: LanguageCode): NormalizedLang {
  if (!lang || lang === 'indic-auto') return 'hi-IN';
  if (
    lang === 'hi-IN' ||
    lang === 'kn-IN' ||
    lang === 'ta-IN' ||
    lang === 'te-IN' ||
    lang === 'ml-IN' ||
    lang === 'bn-IN' ||
    lang === 'mr-IN' ||
    lang === 'gu-IN' ||
    lang === 'pa-IN' ||
    lang === 'en-IN'
  ) {
    return lang;
  }
  return 'en-IN';
}

const TASK_TYPE_MAP: Record<string, Record<NormalizedLang, string>> = {
  'Td-2 Vaccination & ANC Checkup': {
    'en-IN': 'Td-2 Vaccination & ANC Checkup',
    'hi-IN': 'टीडी-2 टीकाकरण और एएनसी जांच',
    'kn-IN': 'ಟಿಡಿ-2 ಲಸಿಕೆ ಮತ್ತು ಎಎನ್‌ಸಿ ತಪಾಸಣೆ',
    'ta-IN': 'டிடி-2 தடுப்பூசி & ஏஎன்சி பரிசோதனை',
    'te-IN': 'టిడి-2 టీకా & ఎఎన్‌సి తనిఖీ',
    'ml-IN': 'ടിഡി-2 വാക്സിനേഷനും എഎൻസി പരിശോധനയും',
    'mr-IN': 'टीडी-2 लसीकरण आणि एएनसी तपासणी',
    'bn-IN': 'টিডি-২ টিকাদান ও এএনসি পরীক্ষা',
    'gu-IN': 'ટીડી-૨ રસીકરણ અને એએનસી તપાસ',
    'pa-IN': 'ਟੀਡੀ-2 ਟੀਕਾਕਰਨ ਅਤੇ ਏਐਨਸੀ ਜਾਂਚ',
  },
  'MR-1 Measles-Rubella Overdue Immunisation Follow-up': {
    'en-IN': 'MR-1 Measles-Rubella Overdue Immunisation Follow-up',
    'hi-IN': 'एमआर-1 खसरा-रूबेला बाकी टीकाकरण फॉलो-अप',
    'kn-IN': 'ಎಂಆರ್-1 ದಡಾರ-ರುಬೆಲ್ಲಾ ಬಾಕಿ ಲಸಿಕೆ ಫಾಲೋ-ಅಪ್',
    'ta-IN': 'எம்ஆர்-1 தட்டம்மை-ரூபெல்லா நிலுவை தடுப்பூசி ஃபாலோ-அப்',
    'te-IN': 'ఎంఆర్-1 తట్టు-రుబెల్లా బకాయి టీకా ఫాలో-అప్',
    'ml-IN': 'എംആർ-1 അഞ്ചാംപനി-റുബെല്ല കുടിശ്ശിക വാക്സിൻ ഫോളോ-അപ്പ്',
    'mr-IN': 'एमआर-1 गोवर-रुबेला प्रलंबित लसीकरण फॉलो-अप',
    'bn-IN': 'এমআর-১ হাম-রুবেলা বকেয়া টিকাদান ফলো-আপ',
    'gu-IN': 'એમઆર-૧ ઓરી-રૂબેલા બાકી રસીકરણ ફોલો-અપ',
    'pa-IN': 'ਐਮਆਰ-1 ਖਸਰਾ-ਰੁਬੇਲਾ ਬਕਾਇਆ ਟੀਕਾਕਰਨ ਫਾਲੋ-ਅੱਪ',
  },
  'ANC Checkup': {
    'en-IN': 'ANC Checkup',
    'hi-IN': 'एएनसी (प्रसव पूर्व) जांच',
    'kn-IN': 'ಎಎನ್‌ಸಿ ತಪಾಸಣೆ',
    'ta-IN': 'ஏஎன்சி பரிசோதனை',
    'te-IN': 'ఎఎన్‌సి తనిఖీ',
    'ml-IN': 'എഎൻസി പരിശോധന',
    'mr-IN': 'एएनसी तपासणी',
    'bn-IN': 'এএনসি পরীক্ষা',
    'gu-IN': 'એએનસી તપાસ',
    'pa-IN': 'ਏਐਨਸੀ ਜਾਂਚ',
  },
  'PNC Follow-up': {
    'en-IN': 'PNC Follow-up',
    'hi-IN': 'पीएनसी (प्रसवोत्तर) जांच व फॉलो-अप',
    'kn-IN': 'ಪಿಎನ್‌ಸಿ ತಪಾಸಣೆ ಮತ್ತು ಫಾಲೋ-ಅಪ್',
    'ta-IN': 'பிஎன்சி பரிசோதனை & ஃபாலோ-அப்',
    'te-IN': 'పిఎన్‌సి తనిఖీ & ఫాలో-అప్',
    'ml-IN': 'പിഎൻസി പരിശോധനയും ഫോളോ-അപ്പും',
    'mr-IN': 'पीएनसी तपासणी आणि फॉलो-अप',
    'bn-IN': 'পিএনসি পরীক্ষা ও ফলো-আপ',
    'gu-IN': 'પીએનસી તપાસ અને ફોલો-અપ',
    'pa-IN': 'ਪੀਐਨਸੀ ਜਾਂਚ ਅਤੇ ਫਾਲੋ-ਅੱਪ',
  },
  'Newborn Care Follow-up': {
    'en-IN': 'Newborn Care Follow-up (HBNC)',
    'hi-IN': 'नवजात शिशु देखभाल फॉलो-अप (एचबीएनसी)',
    'kn-IN': 'ನವಜಾತ ಶಿಶು ಆರೈಕೆ ಫಾಲೋ-ಅಪ್ (ಎಚ್‌ಬಿಎನ್‌ಸಿ)',
    'ta-IN': 'பிறந்த குழந்தை பராமரிப்பு ஃபாலோ-அப் (HBNC)',
    'te-IN': 'నవజాత శిశు సంరక్షణ ఫాలో-అప్ (HBNC)',
    'ml-IN': 'നവജാത ശിശു പരിചരണ ഫോളോ-അപ്പ് (HBNC)',
    'mr-IN': 'नवजात शिशु काळजी फॉलो-अप (एचबीएनसी)',
    'bn-IN': 'নবজাতক যত্ন ফলো-আপ (এইচবিএনসি)',
    'gu-IN': 'નવજાત શિશુ સંભાળ ફોલો-અપ (એચબીએનસી)',
    'pa-IN': 'ਨਵਜੰਮੇ ਬੱਚੇ ਦੀ ਦੇਖਭਾਲ ਫਾਲੋ-ਅੱਪ (ਐਚਬੀਐਨਸੀ)',
  },
  'High Risk Pregnancy Monitoring': {
    'en-IN': 'High Risk Pregnancy Monitoring',
    'hi-IN': 'उच्च जोखिम गर्भावस्था निगरानी',
    'kn-IN': 'ಹೆಚ್ಚಿನ ಅಪಾಯದ ಗರ್ಭಧಾರಣೆ ಮೇಲ್ವಿಚಾರಣೆ',
    'ta-IN': 'அதிக ஆபத்துள்ள கர்ப்ப கண்காணிப்பு',
    'te-IN': 'అధిక ప్రమాద గర్భధారణ పర్యవేక్షణ',
    'ml-IN': 'ഉയർന്ന അപകടസാധ്യതയുള്ള ഗർഭധാരണ നിരീക്ഷണം',
    'mr-IN': 'उच्च जोखीम गर्भधारणा देखरेख',
    'bn-IN': 'উচ্চ ঝুঁকির গর্ভাবস্থা পর্যবেক্ষণ',
    'gu-IN': 'ઉચ્ચ જોખમી ગર્ભાવસ્થા દેખરેખ',
    'pa-IN': 'ਉੱਚ ਜੋਖਮ ਵਾਲੀ ਗਰਭ ਅਵਸਥਾ ਨਿਗਰਾਨੀ',
  },
  'Immediate PHC Referral': {
    'en-IN': 'Immediate PHC Referral Needed',
    'hi-IN': 'तत्काल प्राथमिक स्वास्थ्य केंद्र (PHC) रेफरल आवश्यक',
    'kn-IN': 'ತಕ್ಷಣದ ಪಿಎಚ್‌ಸಿ ರೆಫರಲ್ ಅಗತ್ಯವಿದೆ',
    'ta-IN': 'உடனடி ஆரம்ப சுகாதார நிலைய (PHC) பரிந்துரை தேவை',
    'te-IN': 'వెంటనే పిహెచ్‌సి రెఫరల్ అవసరం',
    'ml-IN': 'ഉടൻ തന്നെ പിഎച്ച്സി റഫറൽ ആവശ്യമാണ്',
    'mr-IN': 'तातडीने प्राथमिक आरोग्य केंद्र (PHC) रेफरल आवश्यक',
    'bn-IN': 'অবিলম্বে প্রাথমিক স্বাস্থ্য কেন্দ্র (PHC) রেফারেল প্রয়োজন',
    'gu-IN': 'ત્વરિત પ્રાથમિક આરોગ્ય કેન્દ્ર (PHC) રેફરલ જરૂરી',
    'pa-IN': 'ਤੁਰੰਤ ਮੁੱਢਲਾ ਸਿਹਤ ਕੇਂਦਰ (PHC) ਰੈਫਰਲ ਲੋੜੀਂਦਾ',
  },
};

const PRIORITY_MAP: Record<string, Record<NormalizedLang, string>> = {
  HIGH: {
    'en-IN': 'HIGH',
    'hi-IN': 'उच्च',
    'kn-IN': 'ಹೆಚ್ಚು',
    'ta-IN': 'அதி முக்கியம்',
    'te-IN': 'అధిక',
    'ml-IN': 'ഉയർന്നത്',
    'mr-IN': 'उच्च',
    'bn-IN': 'উচ্চ',
    'gu-IN': 'ઉચ્ચ',
    'pa-IN': 'ਉੱਚ',
  },
  URGENT: {
    'en-IN': 'URGENT',
    'hi-IN': 'अति आवश्यक',
    'kn-IN': 'ತುರ್ತು',
    'ta-IN': 'அவசரம்',
    'te-IN': 'అత్యవసరం',
    'ml-IN': 'അടിയന്തിരം',
    'mr-IN': 'तातडीचे',
    'bn-IN': 'জরুরি',
    'gu-IN': 'તાકીદનું',
    'pa-IN': 'ਜ਼ਰੂਰੀ',
  },
  NORMAL: {
    'en-IN': 'NORMAL',
    'hi-IN': 'सामान्य',
    'kn-IN': 'ಸಾಮಾನ್ಯ',
    'ta-IN': 'சாதாரணம்',
    'te-IN': 'సాధారణ',
    'ml-IN': 'സാധാരണ',
    'mr-IN': 'सामान्य',
    'bn-IN': 'স্বাভাবিক',
    'gu-IN': 'સામાન્ય',
    'pa-IN': 'ਆਮ',
  },
  MEDIUM: {
    'en-IN': 'MEDIUM',
    'hi-IN': 'मध्यम',
    'kn-IN': 'ಮಧ್ಯಮ',
    'ta-IN': 'நடுத்தரம்',
    'te-IN': 'మధ్యస్థం',
    'ml-IN': 'ഇടത്തരം',
    'mr-IN': 'मध्यम',
    'bn-IN': 'মাঝারি',
    'gu-IN': 'મધ્યમ',
    'pa-IN': 'ਦਰਮਿਆਨਾ',
  },
  LOW: {
    'en-IN': 'LOW',
    'hi-IN': 'कम',
    'kn-IN': 'ಕಡಿಮೆ',
    'ta-IN': 'குறைந்த',
    'te-IN': 'తక్కువ',
    'ml-IN': 'കുറഞ്ഞത്',
    'mr-IN': 'कमी',
    'bn-IN': 'কম',
    'gu-IN': 'ઓછું',
    'pa-IN': 'ਘੱਟ',
  },
};

const STATUS_MAP: Record<string, Record<NormalizedLang, string>> = {
  OVERDUE: {
    'en-IN': 'OVERDUE',
    'hi-IN': 'विलंबित',
    'kn-IN': 'ಬಾಕಿ ಉಳಿದಿದೆ',
    'ta-IN': 'தவறியது',
    'te-IN': 'గడువు ముగిసింది',
    'ml-IN': 'കാലഹരണപ്പെട്ടു',
    'mr-IN': 'थकीत',
    'bn-IN': 'বকেয়া',
    'gu-IN': 'મુદતવીતી',
    'pa-IN': 'ਮਿਆਦ ਪੁੱਗੀ',
  },
  PENDING: {
    'en-IN': 'PENDING',
    'hi-IN': 'लंबित',
    'kn-IN': 'ಬಾಕಿ',
    'ta-IN': 'நிலுவை',
    'te-IN': 'పెండింగ్',
    'ml-IN': 'തീർച്ചപ്പെടുത്താത്തത്',
    'mr-IN': 'प्रलंबित',
    'bn-IN': 'অমীমাংসিত',
    'gu-IN': 'બાકી',
    'pa-IN': 'ਬਕਾਇਆ',
  },
  COMPLETED: {
    'en-IN': 'COMPLETED',
    'hi-IN': 'पूर्ण',
    'kn-IN': 'ಪೂರ್ಣಗೊಂಡಿದೆ',
    'ta-IN': 'முடிந்தது',
    'te-IN': 'పూర్తయింది',
    'ml-IN': 'പൂർത്തിയായി',
    'mr-IN': 'पूर्ण',
    'bn-IN': 'সম্পন্ন',
    'gu-IN': 'પૂર્ણ',
    'pa-IN': 'ਪੂਰਾ ਹੋਇਆ',
  },
  DUE: {
    'en-IN': 'DUE',
    'hi-IN': 'देय',
    'kn-IN': 'ಬಾಕಿ',
    'ta-IN': 'நிலுவை',
    'te-IN': 'బకాయి',
    'ml-IN': 'കുടിശ്ശിക',
    'mr-IN': 'देय',
    'bn-IN': 'দেয়',
    'gu-IN': 'બાકી',
    'pa-IN': 'ਦੇਣਯੋਗ',
  },
};

const BENEFICIARY_NAME_MAP: Record<string, Record<NormalizedLang, string>> = {
  'Lakshmi Devi': {
    'en-IN': 'Lakshmi Devi',
    'hi-IN': 'लक्ष्मी देवी',
    'kn-IN': 'ಲಕ್ಷ್ಮೀ ದೇವಿ',
    'ta-IN': 'லட்சுமி தேவி',
    'te-IN': 'లక్ష్మీ దేవి',
    'ml-IN': 'ലക്ഷ്മി ദേവി',
    'mr-IN': 'लक्ष्मी देवी',
    'bn-IN': 'লক্ষ্মী দেবী',
    'gu-IN': 'લક્ષ્મી દેવી',
    'pa-IN': 'ਲਕਸ਼ਮੀ ਦੇਵੀ',
  },
  'Meena Selvam': {
    'en-IN': 'Meena Selvam',
    'hi-IN': 'मीना सेल्वम',
    'kn-IN': 'ಮೀನಾ ಸೆಲ್ವಂ',
    'ta-IN': 'மீனா செல்வம்',
    'te-IN': 'మీనా సెల్వం',
    'ml-IN': 'മീന സെൽവം',
    'mr-IN': 'मीना सेल्वम',
    'bn-IN': 'মীনা সেলভাম',
    'gu-IN': 'મીના સેલ્વમ',
    'pa-IN': 'ਮੀਨਾ ਸੇਲਵਮ',
  },
  'Pooja Sharma': {
    'en-IN': 'Pooja Sharma',
    'hi-IN': 'पूजा शर्मा',
    'kn-IN': 'ಪೂಜಾ ಶರ್ಮಾ',
    'ta-IN': 'பூஜா சர்மா',
    'te-IN': 'పూజా శర్మ',
    'ml-IN': 'പൂജ ശർമ്മ',
    'mr-IN': 'पूजा शर्मा',
    'bn-IN': 'পূজা শর্মা',
    'gu-IN': 'પૂજા શર્મા',
    'pa-IN': 'ਪੂਜਾ ਸ਼ਰਮਾ',
  },
  'Kavita Patel': {
    'en-IN': 'Kavita Patel',
    'hi-IN': 'कविता पटेल',
    'kn-IN': 'ಕವಿತಾ ಪಟೇಲ್',
    'ta-IN': 'கவிதா படேல்',
    'te-IN': 'కవితా పటేల్',
    'ml-IN': 'കവിത പട്ടേൽ',
    'mr-IN': 'कविता पटेल',
    'bn-IN': 'কবিতা প্যাটেল',
    'gu-IN': 'કવિતા પટેલ',
    'pa-IN': 'ਕਵਿਤਾ ਪਟੇਲ',
  },
  'Sunita Verma': {
    'en-IN': 'Sunita Verma',
    'hi-IN': 'सुनीता वर्मा',
    'kn-IN': 'ಸುನೀತಾ ವರ್ಮಾ',
    'ta-IN': 'சுனிதா வர்மா',
    'te-IN': 'సునీతా వర్మ',
    'ml-IN': 'സുനിത വർമ്മ',
    'mr-IN': 'सुनीता वर्मा',
    'bn-IN': 'সুনীতা ভার্মা',
    'gu-IN': 'સુનિતા વર્મા',
    'pa-IN': 'ਸੁਨੀਤਾ ਵਰਮਾ',
  },
  'Anita Devi': {
    'en-IN': 'Anita Devi',
    'hi-IN': 'अनिता देवी',
    'kn-IN': 'ಅನಿತಾ ದೇವಿ',
    'ta-IN': 'அனிதா தேவி',
    'te-IN': 'అనిత దేవి',
    'ml-IN': 'അനിത ദേവി',
    'mr-IN': 'अनिता देवी',
    'bn-IN': 'অনিতা দেবী',
    'gu-IN': 'અનિતા દેવી',
    'pa-IN': 'ਅਨੀਤਾ ਦੇਵੀ',
  },
  'Anitha Sharma': {
    'en-IN': 'Anitha Sharma',
    'hi-IN': 'अनिता शर्मा',
    'kn-IN': 'ಅನಿತಾ ಶರ್ಮಾ',
    'ta-IN': 'அனிதா சர்மா',
    'te-IN': 'అనిత శర్మ',
    'ml-IN': 'അനിത ശർമ്മ',
    'mr-IN': 'अनिता शर्मा',
    'bn-IN': 'অনিতা শর্মা',
    'gu-IN': 'અનિતા શર્મા',
    'pa-IN': 'ਅਨੀਤਾ ਸ਼ਰਮਾ',
  },
};

/**
 * Localizes a follow-up task type to the selected Indic language.
 */
export function localizeTaskType(taskType: string, lang?: LanguageCode): string {
  if (!taskType) return '';
  const normalizedLang = resolveLang(lang);
  if (normalizedLang === 'en-IN') return taskType;

  // Direct match
  if (TASK_TYPE_MAP[taskType]?.[normalizedLang]) {
    return TASK_TYPE_MAP[taskType][normalizedLang];
  }

  // Case-insensitive or partial match
  const lower = taskType.toLowerCase().trim();
  for (const [key, translations] of Object.entries(TASK_TYPE_MAP)) {
    if (lower === key.toLowerCase() || lower.includes(key.toLowerCase())) {
      return translations[normalizedLang];
    }
  }

  // Keywords fallback
  if (lower.includes('td-2') || lower.includes('td 2') || (lower.includes('anc') && lower.includes('vaccin'))) {
    return TASK_TYPE_MAP['Td-2 Vaccination & ANC Checkup'][normalizedLang];
  }
  if (lower.includes('mr-1') || lower.includes('measles') || lower.includes('rubella')) {
    return TASK_TYPE_MAP['MR-1 Measles-Rubella Overdue Immunisation Follow-up'][normalizedLang];
  }
  if (lower.includes('anc')) {
    return TASK_TYPE_MAP['ANC Checkup'][normalizedLang];
  }
  if (lower.includes('pnc')) {
    return TASK_TYPE_MAP['PNC Follow-up'][normalizedLang];
  }
  if (lower.includes('newborn') || lower.includes('hbnc')) {
    return TASK_TYPE_MAP['Newborn Care Follow-up'][normalizedLang];
  }
  if (lower.includes('phc') && lower.includes('referral')) {
    return TASK_TYPE_MAP['Immediate PHC Referral'][normalizedLang];
  }

  return taskType;
}

/**
 * Localizes a priority string (HIGH, URGENT, NORMAL, LOW).
 */
export function localizePriority(priority: string, lang?: LanguageCode): string {
  if (!priority) return '';
  const normalizedLang = resolveLang(lang);
  if (normalizedLang === 'en-IN') return priority.toUpperCase();

  const upper = priority.toUpperCase().trim();
  if (PRIORITY_MAP[upper]?.[normalizedLang]) {
    return PRIORITY_MAP[upper][normalizedLang];
  }
  return priority;
}

/**
 * Localizes a task or vaccine status string (OVERDUE, PENDING, COMPLETED, DUE).
 */
export function localizeStatus(status: string, lang?: LanguageCode): string {
  if (!status) return '';
  const normalizedLang = resolveLang(lang);
  if (normalizedLang === 'en-IN') return status.toUpperCase();

  const upper = status.toUpperCase().trim();
  if (STATUS_MAP[upper]?.[normalizedLang]) {
    return STATUS_MAP[upper][normalizedLang];
  }
  return status;
}

/**
 * Localizes or transliterates a beneficiary name if present in synthetic directory.
 */
export function localizeBeneficiaryName(name?: string | null, lang?: LanguageCode): string {
  if (!name) return '';
  const normalizedLang = resolveLang(lang);
  if (normalizedLang === 'en-IN') return name;

  const trimmed = name.trim();
  if (BENEFICIARY_NAME_MAP[trimmed]?.[normalizedLang]) {
    return BENEFICIARY_NAME_MAP[trimmed][normalizedLang];
  }
  return trimmed;
}

/**
 * Localizes a full follow-up task record.
 */
export function localizeFollowUpTask(task: FollowUpTask, lang?: LanguageCode) {
  return {
    ...task,
    task_type: localizeTaskType(task.task_type, lang),
    priority: localizePriority(task.priority, lang),
    status: localizeStatus(task.status, lang),
    beneficiary_name: localizeBeneficiaryName(task.beneficiary_name, lang),
  };
}
