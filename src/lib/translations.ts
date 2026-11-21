import { LanguageCode } from '@/types';

export interface Translations {
  // Common & Nav
  appName: string;
  appSubtitle: string;
  portalSubtitle: string;
  ashaPortal: string;
  supervisorPortal: string;
  online: string;
  offline: string;
  pendingSync: string;
  syncedVisits: string;

  // ASHA Portal
  greeting: string;
  bannerDescription: string;
  totalBeneficiaries: string;
  highRisk: string;
  dueFollowUps: string;
  startVoiceVisit: string;
  instantVoiceVisit: string;
  assignedBeneficiaries: string;
  selectBeneficiaryHelp: string;
  searchPlaceholder: string;
  allFilter: string;
  highRiskFilter: string;
  ancFilter: string;
  infantFilter: string;
  childFilter: string;
  pncFilter: string;
  dueTasks: string;
  recentVisits: string;
  noBeneficiariesFound: string;
  noPendingTasks: string;
  noVisitsRecorded: string;
  recordVoiceVisit: string;
  edd: string;
  yrs: string;
  infantLabel: string;

  // Voice Session Modal
  voiceVisitSession: string;
  beneficiaryLabel: string;
  listeningStatus: string;
  speakingStatus: string;
  processingStatus: string;
  interruptedStatus: string;
  connectingStatus: string;
  permissionDeniedStatus: string;
  sessionEndedStatus: string;
  bargeInButton: string;
  liveTranscriptionTitle: string;
  transcriptPlaceholder: string;
  assistantReadBackTitle: string;
  cancelButton: string;
  confirmAndSaveButton: string;
  savingButton: string;
  autoSaveNotice: string;

  // Structured Visit Card
  extractedVisitCard: string;
  bloodPressure: string;
  weight: string;
  temperature: string;
  fhr: string;
  missingField: string;
  administeredVaccines: string;
  nextFollowUp: string;
  readBackStatus: string;
  confirmed: string;
  correctVoiceTooltip: string;

  // Danger Alert
  criticalDangerDetected: string;
  referralProtocol: string;
  call108: string;
  transportStatus: string;
  supervisorAcknowledged: string;
  pendingSupervisorAck: string;
  acknowledgeButton: string;

  // Supervisor Portal
  commandCenterTitle: string;
  commandCenterSubtitle: string;
  exportCsv: string;
  totalVisits: string;
  activeDangerSigns: string;
  urgentBadge: string;
  activeWorkers: string;
  coverageRate: string;
  dangerAlertQueue: string;
  noActiveAlerts: string;
  fieldRegister: string;
  fieldRegisterSubtitle: string;
  colBeneficiary: string;
  colVisitType: string;
  colVitals: string;
  colDangerStatus: string;
  colFollowUp: string;
  colSyncStatus: string;
  normalStatus: string;
  alertStatus: string;
  allVisitTypes: string;
  notRequired: string;
}

export const TRANSLATIONS: Record<LanguageCode, Translations> = {
  'hi-IN': {
    appName: 'साक्ष्या ASHA',
    appSubtitle: 'Voice Field Register',
    portalSubtitle: 'राष्ट्रीय स्वास्थ्य मिशन',
    ashaPortal: 'आशा पोर्टल',
    supervisorPortal: 'PHC सुपरवाइजर',
    online: 'ऑनलाइन',
    offline: 'ऑफ़लाइन',
    pendingSync: 'लंबित',
    syncedVisits: 'विज़िट सिंक हुईं',

    greeting: 'नमस्ते',
    bannerDescription: 'गृह भेंट का विवरण बिना टाइप किए बोलकर दर्ज करें। केवल माइक दबाएं और सामान्य भाषा में बोलें।',
    totalBeneficiaries: 'कुल लाभार्थी',
    highRisk: 'उच्च जोखिम (High Risk)',
    dueFollowUps: 'देय फॉलो-अप',
    startVoiceVisit: 'Start Voice Visit',
    instantVoiceVisit: 'तत्काल वॉयस विज़िट',
    assignedBeneficiaries: 'आवंटित लाभार्थी (Assigned Beneficiaries)',
    selectBeneficiaryHelp: 'विज़िट शुरू करने के लिए किसी भी लाभार्थी को चुनें',
    searchPlaceholder: 'नाम, BEN-ID या गांव खोजें...',
    allFilter: 'सभी (All)',
    highRiskFilter: '⚠️ उच्च जोखिम (High Risk)',
    ancFilter: 'गर्भवती (ANC)',
    infantFilter: 'शिशु (Infant)',
    childFilter: 'बच्चे (Child)',
    pncFilter: 'धात्री माता (PNC)',
    dueTasks: 'देय कार्य (Due Follow-ups)',
    recentVisits: 'हाल की विज़िट (Recent Visits)',
    noBeneficiariesFound: 'कोई लाभार्थी नहीं मिला।',
    noPendingTasks: 'कोई लंबित कार्य नहीं।',
    noVisitsRecorded: 'अभी तक कोई विज़िट नहीं हुई।',
    recordVoiceVisit: 'वॉयस विज़िट दर्ज करें',
    edd: 'प्रसव की संभावित तिथि (EDD)',
    yrs: 'वर्ष',
    infantLabel: 'शिशु',

    voiceVisitSession: 'वॉयस विज़िट सत्र (Voice Visit)',
    beneficiaryLabel: 'लाभार्थी:',
    listeningStatus: 'सुन रहे हैं (Listening)... बोलें',
    speakingStatus: 'सहायक बोल रहा है (Assistant Speaking)',
    processingStatus: 'प्रोसेसिंग (Extracting)...',
    interruptedStatus: 'इंटरप्ट (Barge-in detected)',
    connectingStatus: 'कनेक्ट हो रहा है...',
    permissionDeniedStatus: 'माइक्रोफ़ोन अनुमति नहीं है',
    sessionEndedStatus: 'सत्र समाप्त',
    bargeInButton: 'बीच में बोलें (Barge-in / Interrupt)',
    liveTranscriptionTitle: 'लाइव ट्रांसक्रिप्शन (Prisma STT):',
    transcriptPlaceholder: 'कृपया मरीज के लक्षण, रक्तचाप, वजन या टीके बोलें...',
    assistantReadBackTitle: 'सहायक रीड-बैक (Timbre Voice):',
    cancelButton: 'रद्द करें (Cancel)',
    confirmAndSaveButton: 'पुष्टि करें और सहेजें (Confirm & Save)',
    savingButton: 'सहेज रहे हैं...',
    autoSaveNotice: 'रिकॉर्ड बिना टाइप किए सीधे सहेजा जाएगा।',

    extractedVisitCard: 'Extracted Visit Card (लाइव ड्राफ्ट)',
    bloodPressure: 'रक्तचाप (BP)',
    weight: 'वजन (Weight)',
    temperature: 'तापमान (Temp)',
    fhr: 'FHR (शिशु धड़कन)',
    missingField: 'अपेक्षित (Missing)',
    administeredVaccines: 'लगाए गए टीके:',
    nextFollowUp: 'अगला फॉलो-अप:',
    readBackStatus: 'रीड-बैक स्थिति (Read-back status):',
    confirmed: 'पुष्टि की गई (Confirmed)',
    correctVoiceTooltip: 'बोलकर सही करें',

    criticalDangerDetected: 'CRITICAL DANGER SIGN DETECTED',
    referralProtocol: 'रेफरल प्रोटोकॉल:',
    call108: '108 एम्बुलेंस बुलाएं',
    transportStatus: 'परिवहन स्थिति:',
    supervisorAcknowledged: 'सुपरवाइजर द्वारा स्वीकृत',
    pendingSupervisorAck: 'सुपरवाइजर स्वीकृति प्रतीक्षित',
    acknowledgeButton: 'स्वीकार करें और रेफरल सत्यापित करें',

    commandCenterTitle: 'PHC कमांड सेंटर',
    commandCenterSubtitle: 'वास्तविक समय खतरा अलर्ट, आपातकालीन रेफरल और फील्ड निगरानी',
    exportCsv: 'रजिस्टर निर्यात करें (Export CSV)',
    totalVisits: 'कुल विज़िट (Total Visits)',
    activeDangerSigns: 'अस्वीकृत अलर्ट (Active Danger Signs)',
    urgentBadge: 'तत्काल',
    activeWorkers: 'सक्रिय ASHA कार्यकर्ता',
    coverageRate: 'टीकाकरण कवरेज (Coverage)',
    dangerAlertQueue: 'खतरा संकेत अलर्ट कतार (Live Danger Sign Queue)',
    noActiveAlerts: 'वर्तमान में कोई सक्रिय आपातकालीन अलर्ट नहीं है।',
    fieldRegister: 'क्षेत्रीय विज़िट रजिस्टर (Field Visit Register)',
    fieldRegisterSubtitle: 'सभी ASHA कार्यकर्ताओं द्वारा दर्ज किए गए रिकॉर्ड',
    colBeneficiary: 'लाभार्थी',
    colVisitType: 'विज़िट प्रकार',
    colVitals: 'रक्तचाप / वाइटल्स',
    colDangerStatus: 'खतरा स्थिति',
    colFollowUp: 'फॉलो-अप',
    colSyncStatus: 'सिंक स्थिति',
    normalStatus: 'सामान्य',
    alertStatus: 'खतरा चिन्ह (Alert)',
    allVisitTypes: 'सभी विज़िट प्रकार',
    notRequired: 'आवश्यक नहीं',
  },

  'kn-IN': {
    appName: 'ಸಾಕ್ಷ್ಯಾ ASHA',
    appSubtitle: 'Voice Field Register',
    portalSubtitle: 'ರಾಷ್ಟ್ರೀಯ ಆರೋಗ್ಯ ಅಭಿಯಾನ',
    ashaPortal: 'ಆಶಾ ಪೋರ್ಟಲ್',
    supervisorPortal: 'ಪಿಎಚ್‌ಸಿ ಮೇಲ್ವಿಚಾರಕರು',
    online: 'ಆನ್‌ಲೈನ್',
    offline: 'ಆಫ್‌ಲೈನ್',
    pendingSync: 'ಬಾಕಿ ಇದೆ',
    syncedVisits: 'ಭೇಟಿಗಳು ಸಿಂಕ್ ಆಗಿವೆ',

    greeting: 'ನಮಸ್ಕಾರ',
    bannerDescription: 'ಟೈಪ್ ಮಾಡದೆ ಧ್ವನಿಯ ಮೂಲಕ ಮನೆ ಭೇಟಿ ವಿವರಗಳನ್ನು ದಾಖಲಿಸಿ. ಮೈಕ್ ಒತ್ತಿ ಸಹಜವಾಗಿ ಮಾತನಾಡಿ.',
    totalBeneficiaries: 'ಒಟ್ಟು ಫಲಾನುಭವಿಗಳು',
    highRisk: 'ಹೆಚ್ಚಿನ ಅಪಾಯ (High Risk)',
    dueFollowUps: 'ಬಾಕಿ ಫಾಲೋ-ಅಪ್‌ಗಳು',
    startVoiceVisit: 'Start Voice Visit',
    instantVoiceVisit: 'ಧ್ವನಿ ಭೇಟಿ ಪ್ರಾರಂಭಿಸಿ',
    assignedBeneficiaries: 'ನಿಯೋಜಿತ ಫಲಾನುಭವಿಗಳು (Assigned Beneficiaries)',
    selectBeneficiaryHelp: 'ಭೇಟಿ ಪ್ರಾರಂಭಿಸಲು ಫಲಾನುಭವಿಯನ್ನು ಆಯ್ಕೆಮಾಡಿ',
    searchPlaceholder: 'ಹೆಸರು, BEN-ID ಅಥವಾ ಗ್ರಾಮ ಹುಡುಕಿ...',
    allFilter: 'ಎಲ್ಲವೂ (All)',
    highRiskFilter: '⚠️ ಹೆಚ್ಚಿನ ಅಪಾಯ (High Risk)',
    ancFilter: 'ಗರ್ಭಿಣಿ (ANC)',
    infantFilter: 'ಶಿಶು (Infant)',
    childFilter: 'ಮಕ್ಕಳು (Child)',
    pncFilter: 'ಬಾಣಂತಿ (PNC)',
    dueTasks: 'ಬಾಕಿ ಕಾರ್ಯಗಳು (Due Follow-ups)',
    recentVisits: 'ಇತ್ತೀಚಿನ ಭೇಟಿಗಳು (Recent Visits)',
    noBeneficiariesFound: 'ಯಾವುದೇ ಫಲಾನುಭವಿ ಕಂಡುಬಂದಿಲ್ಲ.',
    noPendingTasks: 'ಯಾವುದೇ ಬಾಕಿ ಕಾರ್ಯಗಳಿಲ್ಲ.',
    noVisitsRecorded: 'ಇನ್ನೂ ಯಾವುದೇ ಭೇಟಿ ದಾಖಲಾಗಿಲ್ಲ.',
    recordVoiceVisit: 'ಧ್ವನಿ ಭೇಟಿ ದಾಖಲಿಸಿ',
    edd: 'ಹೆರಿಗೆ ನಿರೀಕ್ಷಿತ ದಿನಾಂಕ (EDD)',
    yrs: 'ವರ್ಷ',
    infantLabel: 'ಶಿಶು',

    voiceVisitSession: 'ಧ್ವನಿ ಭೇಟಿ ಅವಧಿ (Voice Visit)',
    beneficiaryLabel: 'ಫಲಾನುಭವಿ:',
    listeningStatus: 'ಕೇಳಿಸಿಕೊಳ್ಳುತ್ತಿದ್ದೇವೆ (Listening)... ಮಾತನಾಡಿ',
    speakingStatus: 'ಸಹಾಯಕರು ಮಾತನಾಡುತ್ತಿದ್ದಾರೆ (Assistant Speaking)',
    processingStatus: 'ವಿಶ್ಲೇಷಿಸಲಾಗುತ್ತಿದೆ (Extracting)...',
    interruptedStatus: 'ಮಧ್ಯಪ್ರವೇಶ (Barge-in detected)',
    connectingStatus: 'ಸಂಪರ್ಕಿಸಲಾಗುತ್ತಿದೆ...',
    permissionDeniedStatus: 'ಮೈಕ್ರೊಫೋನ್ ಅನುಮತಿ ಇಲ್ಲ',
    sessionEndedStatus: 'ಅವಧಿ ಮುಕ್ತಾಯಗೊಂಡಿದೆ',
    bargeInButton: 'ಮಧ್ಯದಲ್ಲಿ ಮಾತನಾಡಿ (Barge-in / Interrupt)',
    liveTranscriptionTitle: 'ಲೈವ್ ಪ್ರತಿಲೇಖನ (Prisma STT):',
    transcriptPlaceholder: 'ರೋಗಿಯ ಲಕ್ಷಣಗಳು, ರಕ್ತದೊತ್ತಡ, ತೂಕ ಅಥವಾ ಲಸಿಕೆಗಳ ಬಗ್ಗೆ ಮಾತನಾಡಿ...',
    assistantReadBackTitle: 'ಸಹಾಯಕ ಓದುವಿಕೆ (Timbre Voice):',
    cancelButton: 'ರದ್ದುಮಾಡಿ (Cancel)',
    confirmAndSaveButton: 'ದೃಢೀಕರಿಸಿ ಮತ್ತು ಉಳಿಸಿ (Confirm & Save)',
    savingButton: 'ಉಳಿಸಲಾಗುತ್ತಿದೆ...',
    autoSaveNotice: 'ಟೈಪ್ ಮಾಡದೆಯೇ ರೆಕಾರ್ಡ್ ನೇರವಾಗಿ ಉಳಿಸಲಾಗುವುದು.',

    extractedVisitCard: 'ಹೊರತೆಗೆಯಲಾದ ಭೇಟಿ ಕಾರ್ಡ್ (ಲೈವ್ ಡ್ರಾಫ್ಟ್)',
    bloodPressure: 'ರಕ್ತದೊತ್ತಡ (BP)',
    weight: 'ತೂಕ (Weight)',
    temperature: 'ತಾಪಮಾನ (Temp)',
    fhr: 'ಭ್ರೂಣದ ಹೃದಯ ಬಡಿತ (FHR)',
    missingField: 'ಅಪೇಕ್ಷಿತ (Missing)',
    administeredVaccines: 'ನೀಡಲಾದ ಲಸಿಕೆಗಳು:',
    nextFollowUp: 'ಮುಂದಿನ ಫಾಲೋ-ಅಪ್:',
    readBackStatus: 'ಓದುವಿಕೆಯ ಸ್ಥಿತಿ (Read-back status):',
    confirmed: 'ದೃಢೀಕರಿಸಲಾಗಿದೆ (Confirmed)',
    correctVoiceTooltip: 'ಧ್ವನಿಯ ಮೂಲಕ ಸರಿಪಡಿಸಿ',

    criticalDangerDetected: 'ತೀವ್ರ ಅಪಾಯದ ಲಕ್ಷಣ ಪತ್ತೆಯಾಗಿದೆ',
    referralProtocol: 'ರೆಫರಲ್ ಶಿಷ್ಟಾಚಾರ:',
    call108: '108 ಆಂಬ್ಯುಲೆನ್ಸ್‌ಗೆ ಕರೆ ಮಾಡಿ',
    transportStatus: 'ಸಾರಿಗೆ ಸ್ಥಿತಿ:',
    supervisorAcknowledged: 'ಮೇಲ್ವಿಚಾರಕರು ಅಂಗೀಕರಿಸಿದ್ದಾರೆ',
    pendingSupervisorAck: 'ಮೇಲ್ವಿಚಾರಕರ ಅಂಗೀಕಾರ ಬಾಕಿ ಇದೆ',
    acknowledgeButton: 'ಅಂಗೀಕರಿಸಿ ಮತ್ತು ರೆಫರಲ್ ದೃಢೀಕರಿಸಿ',

    commandCenterTitle: 'ಪಿಎಚ್‌ಸಿ ಕಮಾಂಡ್ ಸೆಂಟರ್',
    commandCenterSubtitle: 'ನೈಜ ಸಮಯದ ಅಪಾಯದ ಎಚ್ಚರಿಕೆಗಳು, ತುರ್ತು ಉಲ್ಲೇಖಗಳು ಮತ್ತು ಕ್ಷೇತ್ರ ಮೇಲ್ವಿಚಾರಣೆ',
    exportCsv: 'ರಿಜಿಸ್ಟರ್ ರಫ್ತು ಮಾಡಿ (Export CSV)',
    totalVisits: 'ಒಟ್ಟು ಭೇಟಿಗಳು (Total Visits)',
    activeDangerSigns: 'ಸಕ್ರಿಯ ಅಪಾಯದ ಲಕ್ಷಣಗಳು',
    urgentBadge: 'ತುರ್ತು',
    activeWorkers: 'ಸಕ್ರಿಯ ಆಶಾ ಕಾರ್ಯಕರ್ತೆಯರು',
    coverageRate: 'ಲಸಿಕೆ ವ್ಯಾಪ್ತಿ (Coverage)',
    dangerAlertQueue: 'ಅಪಾಯ ಎಚ್ಚರಿಕೆ ಸರದಿ (Live Danger Sign Queue)',
    noActiveAlerts: 'ಪ್ರಸ್ತುತ ಯಾವುದೇ ಸಕ್ರಿಯ ತುರ್ತು ಎಚ್ಚರಿಕೆಗಳಿಲ್ಲ.',
    fieldRegister: 'ಕ್ಷೇತ್ರ ಭೇಟಿ ರಿಜಿಸ್ಟರ್ (Field Visit Register)',
    fieldRegisterSubtitle: 'ಆಶಾ ಕಾರ್ಯಕರ್ತೆಯರು ದಾಖಲಿಸಿದ ಎಲ್ಲಾ ದಾಖಲೆಗಳು',
    colBeneficiary: 'ಫಲಾನುಭವಿ',
    colVisitType: 'ಭೇಟಿ ಪ್ರಕಾರ',
    colVitals: 'ರಕ್ತದೊತ್ತಡ / ವೈಟಲ್ಸ್',
    colDangerStatus: 'ಅಪಾಯ ಸ್ಥಿತಿ',
    colFollowUp: 'ಫಾಲೋ-ಅಪ್',
    colSyncStatus: 'ಸಿಂಕ್ ಸ್ಥಿತಿ',
    normalStatus: 'ಸಾಮಾನ್ಯ',
    alertStatus: 'ಅಪಾಯ ಸೂಚನೆ (Alert)',
    allVisitTypes: 'ಎಲ್ಲಾ ಭೇಟಿ ಪ್ರಕಾರಗಳು',
    notRequired: 'ಅಗತ್ಯವಿಲ್ಲ',
  },

  'ta-IN': {
    appName: 'சாக்ஷியா ASHA',
    appSubtitle: 'Voice Field Register',
    portalSubtitle: 'தேசிய சுகாதார இயக்கம்',
    ashaPortal: 'ஆஷா போர்ட்டல்',
    supervisorPortal: 'பி.எச்.சி மேற்பார்வையாளர்',
    online: 'ஆன்லைன்',
    offline: 'ஆஃப்லைன்',
    pendingSync: 'நிலுவையில்',
    syncedVisits: 'வருகைகள் ஒத்திசைக்கப்பட்டன',

    greeting: 'வணக்கம்',
    bannerDescription: 'தட்டச்சு செய்யாமல் குரல் மூலம் வீட்டு வருகை விவரங்களை பதிவு செய்யுங்கள். மைக் அழுத்தி இயல்பாகப் பேசுங்கள்.',
    totalBeneficiaries: 'மொத்த பயனாளிகள்',
    highRisk: 'அதிக ஆபத்து (High Risk)',
    dueFollowUps: 'நிலுவை தொடர் ஆய்வுகள்',
    startVoiceVisit: 'Start Voice Visit',
    instantVoiceVisit: 'உடனடி குரல் வருகை',
    assignedBeneficiaries: 'ஒதுக்கப்பட்ட பயனாளிகள் (Assigned Beneficiaries)',
    selectBeneficiaryHelp: 'வருகையைத் தொடங்க பயனாளியைத் தேர்ந்தெடுக்கவும்',
    searchPlaceholder: 'பெயர், BEN-ID அல்லது கிராமம் தேடுக...',
    allFilter: 'அனைத்தும் (All)',
    highRiskFilter: '⚠️ அதிக ஆபத்து (High Risk)',
    ancFilter: 'கர்ப்பிணி (ANC)',
    infantFilter: 'சிசு (Infant)',
    childFilter: 'குழந்தைகள் (Child)',
    pncFilter: 'பாலூட்டும் தாய் (PNC)',
    dueTasks: 'நிலுவை பணிகள் (Due Follow-ups)',
    recentVisits: 'சமீபத்திய வருகைகள் (Recent Visits)',
    noBeneficiariesFound: 'பயனாளிகள் யாரும் கிடைக்கவில்லை.',
    noPendingTasks: 'நிலுவை பணிகள் இல்லை.',
    noVisitsRecorded: 'இதுவரை எந்த வருகையும் பதிவாகவில்லை.',
    recordVoiceVisit: 'குரல் வருகையைப் பதிவுசெய்',
    edd: 'பிரசவ உத்தேச தேதி (EDD)',
    yrs: 'ஆண்டுகள்',
    infantLabel: 'சிசு',

    voiceVisitSession: 'குரல் வருகை அமர்வு (Voice Visit)',
    beneficiaryLabel: 'பயனாளி:',
    listeningStatus: 'கேட்கிறது (Listening)... பேசுங்கள்',
    speakingStatus: 'உதவியாளர் பேசுகிறார் (Assistant Speaking)',
    processingStatus: 'செயலாக்குகிறது (Extracting)...',
    interruptedStatus: 'குறுக்கீடு (Barge-in detected)',
    connectingStatus: 'இணைக்கிறது...',
    permissionDeniedStatus: 'மைக்ரோஃபோன் அனுமதி மறுக்கப்பட்டது',
    sessionEndedStatus: 'அமர்வு முடிந்தது',
    bargeInButton: 'இடையில் பேசுங்கள் (Barge-in / Interrupt)',
    liveTranscriptionTitle: 'நேரலை எழுத்தாக்கம் (Prisma STT):',
    transcriptPlaceholder: 'நோயாளி அறிகுறிகள், இரத்த அழுத்தம், எடை அல்லது தடுப்பூசிகளைப் பேசுங்கள்...',
    assistantReadBackTitle: 'உதவியாளர் வாசிப்பு (Timbre Voice):',
    cancelButton: 'ரத்துசெய் (Cancel)',
    confirmAndSaveButton: 'உறுதிசெய்து சேமி (Confirm & Save)',
    savingButton: 'சேமிக்கிறது...',
    autoSaveNotice: 'தட்டச்சு செய்யாமல் நேரடியாகப் பதிவு சேமிக்கப்படும்.',

    extractedVisitCard: 'பிரித்தெடுக்கப்பட்ட வருகை அட்டை (நேரலை வரைவு)',
    bloodPressure: 'இரத்த அழுத்தம் (BP)',
    weight: 'எடை (Weight)',
    temperature: 'வெப்பநிலை (Temp)',
    fhr: 'கரு இதய துடிப்பு (FHR)',
    missingField: 'எதிர்பார்க்கப்படுகிறது (Missing)',
    administeredVaccines: 'வழங்கப்பட்ட தடுப்பூசிகள்:',
    nextFollowUp: 'அடுத்த தொடர் ஆய்வு:',
    readBackStatus: 'வாசிப்பு நிலை (Read-back status):',
    confirmed: 'உறுதிப்படுத்தப்பட்டது (Confirmed)',
    correctVoiceTooltip: 'குரல் மூலம் திருத்துங்கள்',

    criticalDangerDetected: 'அதிதீவிர ஆபத்து அறிகுறி கண்டறியப்பட்டது',
    referralProtocol: 'பரிந்துரை நெறிமுறை:',
    call108: '108 ஆம்புலன்ஸை அழைக்கவும்',
    transportStatus: 'போக்குவரத்து நிலை:',
    supervisorAcknowledged: 'மேற்பார்வையாளர் ஏற்றுக்கொண்டார்',
    pendingSupervisorAck: 'மேற்பார்வையாளர் ஏற்பு நிலுவையில் உள்ளது',
    acknowledgeButton: 'ஏற்றுக்கொண்டு பரிந்துரையை உறுதிசெய்',

    commandCenterTitle: 'பி.எச்.சி கட்டளை மையம்',
    commandCenterSubtitle: 'நிகழ்நேர ஆபத்து எச்சரிக்கைகள், அவசர பரிந்துரைகள் மற்றும் கள கண்காணிப்பு',
    exportCsv: 'பதிவேட்டை ஏற்றுமதி செய் (Export CSV)',
    totalVisits: 'மொத்த வருகைகள் (Total Visits)',
    activeDangerSigns: 'செயலில் உள்ள ஆபத்து அறிகுறிகள்',
    urgentBadge: 'அவசரம்',
    activeWorkers: 'செயலில் உள்ள ஆஷா பணியாளர்கள்',
    coverageRate: 'தடுப்பூசி பாதுகாப்பு (Coverage)',
    dangerAlertQueue: 'ஆபத்து எச்சரிக்கை வரிசை (Live Danger Sign Queue)',
    noActiveAlerts: 'தற்போது அவசர எச்சரிக்கைகள் எதுவும் இல்லை.',
    fieldRegister: 'கள வருகை பதிவேடு (Field Visit Register)',
    fieldRegisterSubtitle: 'ஆஷா பணியாளர்கள் பதிவு செய்த அனைத்து பதிவுகள்',
    colBeneficiary: 'பயனாளி',
    colVisitType: 'வருகை வகை',
    colVitals: 'இரத்த அழுத்தம் / முக்கிய அளவுகள்',
    colDangerStatus: 'ஆபத்து நிலை',
    colFollowUp: 'தொடர் ஆய்வு',
    colSyncStatus: 'ஒத்திசைவு நிலை',
    normalStatus: 'வழக்கமானது',
    alertStatus: 'ஆபத்து குறி (Alert)',
    allVisitTypes: 'அனைத்து வருகை வகைகள்',
    notRequired: 'தேவையில்லை',
  },

  'en-IN': {
    appName: 'Sakshya ASHA',
    appSubtitle: 'Voice Field Register',
    portalSubtitle: 'National Health Mission',
    ashaPortal: 'ASHA Portal',
    supervisorPortal: 'PHC Supervisor',
    online: 'Online',
    offline: 'Offline',
    pendingSync: 'Pending',
    syncedVisits: 'Visits Synced',

    greeting: 'Hello',
    bannerDescription: 'Record home visit details naturally using voice without any typing. Tap the mic and speak.',
    totalBeneficiaries: 'Total Beneficiaries',
    highRisk: 'High Risk',
    dueFollowUps: 'Due Follow-ups',
    startVoiceVisit: 'Start Voice Visit',
    instantVoiceVisit: 'Instant Voice Visit',
    assignedBeneficiaries: 'Assigned Beneficiaries',
    selectBeneficiaryHelp: 'Select any beneficiary to start visit',
    searchPlaceholder: 'Search by name, BEN-ID or village...',
    allFilter: 'All',
    highRiskFilter: '⚠️ High Risk',
    ancFilter: 'Pregnant (ANC)',
    infantFilter: 'Infant',
    childFilter: 'Child',
    pncFilter: 'Postnatal Mother (PNC)',
    dueTasks: 'Due Follow-ups',
    recentVisits: 'Recent Visits',
    noBeneficiariesFound: 'No beneficiaries found.',
    noPendingTasks: 'No pending follow-ups.',
    noVisitsRecorded: 'No visits recorded yet.',
    recordVoiceVisit: 'Record Voice Visit',
    edd: 'Expected Delivery Date (EDD)',
    yrs: 'yrs',
    infantLabel: 'Infant',

    voiceVisitSession: 'Voice Visit Session',
    beneficiaryLabel: 'Beneficiary:',
    listeningStatus: 'Listening... Please speak',
    speakingStatus: 'Assistant Speaking...',
    processingStatus: 'Extracting clinical vitals...',
    interruptedStatus: 'Barge-in / Interrupted',
    connectingStatus: 'Connecting to voice service...',
    permissionDeniedStatus: 'Microphone permission denied',
    sessionEndedStatus: 'Session ended',
    bargeInButton: 'Barge-in / Interrupt',
    liveTranscriptionTitle: 'Live Transcription (Prisma STT):',
    transcriptPlaceholder: 'Please speak patient vitals, BP, weight, symptoms, or immunisations...',
    assistantReadBackTitle: 'Assistant Read-Back (Timbre Voice):',
    cancelButton: 'Cancel',
    confirmAndSaveButton: 'Confirm & Save Visit',
    savingButton: 'Saving...',
    autoSaveNotice: 'Record will be saved directly without typing.',

    extractedVisitCard: 'Extracted Visit Card (Live Draft)',
    bloodPressure: 'Blood Pressure (BP)',
    weight: 'Weight',
    temperature: 'Temperature',
    fhr: 'Fetal Heart Rate (FHR)',
    missingField: 'Expected (Missing)',
    administeredVaccines: 'Administered Vaccines:',
    nextFollowUp: 'Next Follow-up:',
    readBackStatus: 'Read-Back Status:',
    confirmed: 'Confirmed',
    correctVoiceTooltip: 'Correct field by voice',

    criticalDangerDetected: 'CRITICAL DANGER SIGN DETECTED',
    referralProtocol: 'Referral Protocol:',
    call108: 'Call 108 Ambulance',
    transportStatus: 'Transport Status:',
    supervisorAcknowledged: 'Supervisor Acknowledged',
    pendingSupervisorAck: 'Pending Supervisor Acknowledgement',
    acknowledgeButton: 'Acknowledge & Confirm Referral',

    commandCenterTitle: 'PHC Command Center',
    commandCenterSubtitle: 'Real-time danger alerts, emergency referrals, and field monitoring',
    exportCsv: 'Export Register (CSV)',
    totalVisits: 'Total Visits',
    activeDangerSigns: 'Active Danger Signs',
    urgentBadge: 'URGENT',
    activeWorkers: 'Active ASHA Workers',
    coverageRate: 'Immunisation Coverage',
    dangerAlertQueue: 'Live Danger Sign Queue',
    noActiveAlerts: 'No active emergency alerts at this time.',
    fieldRegister: 'Field Visit Register',
    fieldRegisterSubtitle: 'All records logged by field ASHA workers',
    colBeneficiary: 'Beneficiary',
    colVisitType: 'Visit Type',
    colVitals: 'Blood Pressure / Vitals',
    colDangerStatus: 'Danger Status',
    colFollowUp: 'Follow-up',
    colSyncStatus: 'Sync Status',
    normalStatus: 'Normal',
    alertStatus: 'Alert Flagged',
    allVisitTypes: 'All Visit Types',
    notRequired: 'Not required',
  },
};
