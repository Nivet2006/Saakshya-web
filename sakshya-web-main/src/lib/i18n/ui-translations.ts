import type { LanguageCode } from '@/types';

export interface UiStrings {
  // AppShell & Header
  appName: string;
  ashaPortal: string;
  supervisorPortal: string;
  voiceApiLive: string;
  voiceApiOffline: string;
  checkingApi: string;
  signOut: string;
  languageLabel: string;
  online: string;
  offline: string;
  pendingSync: string;
  syncedVisits: string;
  ashaFieldMode: string;
  supervisorMode: string;

  // Navigation
  navHome: string;
  navVoiceVisit: string;
  navBeneficiaries: string;
  navFollowUps: string;
  navVisitHistory: string;
  navOfflineDrafts: string;
  navPhcOverview: string;
  navDangerAlerts: string;
  navAshaWorkers: string;
  navVisitRegister: string;
  navAnalytics: string;
  navReportsAudit: string;

  // Login Screen
  loginHeroTitle: string;
  loginHeroDesc: string;
  syntheticRolesHeading: string;
  zeroPiiNote: string;
  selectAppLanguage: string;
  staffSignInTitle: string;
  staffSignInDesc: string;
  emailLabel: string;
  passwordLabel: string;
  signInButton: string;
  signingInButton: string;
  localDemoModeNotice: string;

  // ASHA Home
  namasteGreeting: string;
  homeVoicePrompt: string;
  startVoiceVisit: string;
  assignedHouseholds: string;
  viewDirectory: string;
  visitsToday: string;
  totalLogged: string;
  pendingFollowUps: string;
  openTaskQueue: string;
  vaccinesDue: string;
  dueOverdueDoses: string;
  allTasks: string;
  noPendingTasks: string;
  recentSavedVisits: string;
  fullHistory: string;
  noVisitsRecorded: string;
  dangerFlagged: string;
  confirmed: string;
  dueLabel: string;
  nextVisitLabel: string;
  weightLabel: string;

  // Beneficiary Directory
  beneficiaryDirectoryTitle: string;
  beneficiaryDirectorySubtitle: string;
  searchBeneficiariesPlaceholder: string;
  allBeneficiaries: string;
  highRiskWatch: string;
  ancFilter: string;
  pncFilter: string;
  infantFilter: string;
  childFilter: string;
  noMatchingBeneficiaries: string;
  noMatchingBeneficiariesDesc: string;
  viewProfile: string;
  voiceVisitButton: string;
  householdHead: string;
  eddLabel: string;
  highRisk: string;
  yrsLabel: string;
  infantNewborn: string;

  // Follow-up Queue
  followUpsTitle: string;
  followUpsSubtitle: string;
  searchFollowUpsPlaceholder: string;
  upcomingTasks: string;
  overdueTab: string;
  pendingVaccinesTab: string;
  completedTab: string;
  noPendingVaccines: string;
  noPendingVaccinesDesc: string;
  noTasksInQueue: string;
  noTasksInQueueDesc: string;
  dueDateLabel: string;
  beneficiaryLabel: string;

  // Visit History
  visitHistoryTitle: string;
  visitHistorySubtitle: string;
  noSavedVisitsYet: string;
  noSavedVisitsDesc: string;
  colDate: string;
  colBeneficiary: string;
  colType: string;
  colWeight: string;
  colDangerSign: string;
  colStatus: string;
  colAction: string;
  inspectButton: string;
  clearStatus: string;
  flaggedStatus: string;
  visitRecordTitle: string;
  vaccinationsCompleted: string;
  vaccinationsDue: string;
  nextVisitDateLabel: string;
  persistenceRef: string;
  summaryTranscript: string;

  // Offline Drafts
  offlineDraftsTitle: string;
  offlineDraftsSubtitle: string;
  syncConfirmedQueue: string;
  syncingConfirmedVisits: string;
  offlinePolicyTitle: string;
  offlinePolicyDesc: string;
  noLocalDrafts: string;
  noLocalDraftsDesc: string;
  recordStatus: string;
  updatedLabel: string;
  retryOverwrite: string;
  removeLocal: string;
  syncedStatus: string;

  // Voice Visit Workspace
  basicModeTitle: string;
  basicModeBadge: string;
  basicModeDesc: string;
  advancedModeTitle: string;
  advancedModeBadge: string;
  advancedModeDesc: string;
  step1Title: string;
  step1Subtitle: string;
  changeBeneficiary: string;
  recentBeneficiaries: string;
  searchDirectoryPlaceholder: string;
  step2Title: string;
  step2Subtitle: string;
  autoDetectIndic: string;
  step3Title: string;
  step3Subtitle: string;
  connectedLabel: string;
  disconnectedLabel: string;
  startRecording: string;
  stopRecording: string;
  holdToSpeak: string;
  bargeInInterrupt: string;
  handsFreeLabel: string;
  pushToTalkLabel: string;
  typeInstead: string;
  sendText: string;
  stateIdle: string;
  stateConnecting: string;
  stateListening: string;
  stateTranscribing: string;
  stateProcessing: string;
  stateResponding: string;
  stateSpeaking: string;
  stateInterrupted: string;
  stateReconnecting: string;
  stateError: string;
  stateCompleted: string;
  liveTranscriptHeading: string;
  spokenDescriptionHeading: string;
  assistantSummaryHeading: string;
  visitSummaryHeading: string;
  confirmAndSaveVisit: string;
  reReadSummary: string;
  saveOfflineDraft: string;
  pauseReadback: string;
  resumeReadback: string;
  correctButton: string;
  confirmField: string;
  needsClarification: string;
  notIdentified: string;

  // Danger Alert Banner
  urgentDangerSign: string;
  matchedPhrase: string;
  urgentPhcReferral: string;
  guidelineReference: string;
  detectedAt: string;
  call108Emergency: string;
  acknowledgeAndRefer: string;
  acknowledgeAlert: string;
  markReferred: string;
  markResolved: string;
  acknowledgedBy: string;

  // Supervisor Portal
  commandCenterTitle: string;
  commandCenterSubtitle: string;
  alertCommandButton: string;
  registeredBeneficiaries: string;
  activeWorkers: string;
  totalVisits: string;
  activeDangerSigns: string;
  dangerAlertQueue: string;
  noActiveAlerts: string;
  fieldRegister: string;
  fieldRegisterSubtitle: string;
  exportCsv: string;
  printReport: string;
  ashaWorkersTitle: string;
  ashaWorkersSubtitle: string;
  analyticsTitle: string;
  analyticsSubtitle: string;
  reportsAuditTitle: string;
  reportsAuditSubtitle: string;
}

export const EN_UI: UiStrings = {
  appName: 'Sakshya ASHA',
  ashaPortal: 'ASHA Portal',
  supervisorPortal: 'PHC Supervisor',
  voiceApiLive: 'Voice API Live',
  voiceApiOffline: 'Voice API Offline',
  checkingApi: 'Checking API',
  signOut: 'Sign out',
  languageLabel: 'Language',
  online: 'Online',
  offline: 'Offline',
  pendingSync: 'Pending',
  syncedVisits: 'Visits Synced',
  ashaFieldMode: 'ASHA Field Mode',
  supervisorMode: 'PHC Supervisor',

  navHome: 'Home',
  navVoiceVisit: 'Voice Visit',
  navBeneficiaries: 'Beneficiaries',
  navFollowUps: 'Follow-ups',
  navVisitHistory: 'Visit History',
  navOfflineDrafts: 'Offline Drafts',
  navPhcOverview: 'PHC Overview',
  navDangerAlerts: 'Danger Alerts',
  navAshaWorkers: 'ASHA Workers',
  navVisitRegister: 'Visit Register',
  navAnalytics: 'Analytics',
  navReportsAudit: 'Reports & Audit',

  loginHeroTitle: 'Voice-First Maternal & Newborn Field Register',
  loginHeroDesc:
    'Speak naturally during home visits in Indic languages. Records are structured, verified aloud for your confirmation, and monitored in real time for urgent danger signs.',
  syntheticRolesHeading: 'Synthetic Demo Roles (Zero PII)',
  zeroPiiNote: 'All beneficiaries (BEN-1042–BEN-1048) and visit records are synthetic demonstration fixtures.',
  selectAppLanguage: 'Select App & Voice Language',
  staffSignInTitle: 'Staff Sign In',
  staffSignInDesc: 'Sign in with your PHC or ASHA staff credentials, or choose a demo role on the left.',
  emailLabel: 'Email Address',
  passwordLabel: 'Password',
  signInButton: 'Sign In',
  signingInButton: 'Signing in...',
  localDemoModeNotice: 'Local Demo Mode: Supabase Auth is not configured. Use any synthetic role card on the left.',

  namasteGreeting: 'Namaste',
  homeVoicePrompt: 'Tap below to record a household visit by voice — zero typing required.',
  startVoiceVisit: 'Start Voice Visit',
  assignedHouseholds: 'Assigned Households',
  viewDirectory: 'View directory',
  visitsToday: 'Visits Today',
  totalLogged: 'total logged',
  pendingFollowUps: 'Pending Follow-ups',
  openTaskQueue: 'Open task queue',
  vaccinesDue: 'Vaccines Due',
  dueOverdueDoses: 'Due & overdue doses',
  allTasks: 'All Tasks',
  noPendingTasks: 'No pending follow-up tasks.',
  recentSavedVisits: 'Recent Saved Visits',
  fullHistory: 'Full History',
  noVisitsRecorded: 'No visits logged yet.',
  dangerFlagged: 'Danger Flagged',
  confirmed: 'Confirmed',
  dueLabel: 'Due',
  nextVisitLabel: 'Next visit',
  weightLabel: 'Weight',

  beneficiaryDirectoryTitle: 'Beneficiary Directory',
  beneficiaryDirectorySubtitle: 'Synthetic household registry aligned with Agent 1 backend (BEN-1042–BEN-1048).',
  searchBeneficiariesPlaceholder: 'Search name, BEN-ID, or ward...',
  allBeneficiaries: 'All Beneficiaries',
  highRiskWatch: 'High Risk Watch',
  ancFilter: 'Pregnant (ANC)',
  pncFilter: 'Postnatal (PNC)',
  infantFilter: 'Newborn / Infant',
  childFilter: 'Child',
  noMatchingBeneficiaries: 'No matching beneficiaries',
  noMatchingBeneficiariesDesc: 'Try clearing the search query or switching category filters.',
  viewProfile: 'View Profile',
  voiceVisitButton: 'Voice Visit',
  householdHead: 'Household Head',
  eddLabel: 'EDD',
  highRisk: 'High Risk',
  yrsLabel: 'yrs',
  infantNewborn: 'Infant/Newborn',

  followUpsTitle: 'Follow-ups & Immunisation Queue',
  followUpsSubtitle: 'Track scheduled maternal/newborn checkups, urgent PHC referrals, and due vaccine doses.',
  searchFollowUpsPlaceholder: 'Search beneficiary or task...',
  upcomingTasks: 'Upcoming Tasks',
  overdueTab: 'Overdue',
  pendingVaccinesTab: 'Pending Vaccines',
  completedTab: 'Completed',
  noPendingVaccines: 'No pending vaccinations',
  noPendingVaccinesDesc: 'All scheduled doses matching your search are up to date.',
  noTasksInQueue: 'No tasks in this queue',
  noTasksInQueueDesc: 'Tasks generated from confirmed voice visits will appear here automatically.',
  dueDateLabel: 'Due Date',
  beneficiaryLabel: 'Beneficiary',

  visitHistoryTitle: 'Visit History',
  visitHistorySubtitle: 'Explicitly confirmed and committed household visits. Unconfirmed drafts remain in Offline Drafts.',
  noSavedVisitsYet: 'No saved visits yet',
  noSavedVisitsDesc: 'Complete and confirm a voice visit to view it in your field history.',
  colDate: 'Date',
  colBeneficiary: 'Beneficiary',
  colType: 'Type',
  colWeight: 'Weight',
  colDangerSign: 'Danger Sign',
  colStatus: 'Status',
  colAction: 'Action',
  inspectButton: 'Inspect',
  clearStatus: 'Clear',
  flaggedStatus: 'Flagged',
  visitRecordTitle: 'Visit Record',
  vaccinationsCompleted: 'Vaccinations Completed',
  vaccinationsDue: 'Vaccinations Due',
  nextVisitDateLabel: 'Next Visit Date',
  persistenceRef: 'Persistence Ref',
  summaryTranscript: 'Summary Transcript',

  offlineDraftsTitle: 'Offline Drafts & Sync Queue',
  offlineDraftsSubtitle: 'Stored safely in IndexedDB with visit_id idempotency keys to prevent duplicates.',
  syncConfirmedQueue: 'Sync Confirmed Queue',
  syncingConfirmedVisits: 'Syncing Confirmed Visits...',
  offlinePolicyTitle: 'Offline Capability Policy',
  offlinePolicyDesc:
    'Local drafts and confirmed visit queues survive browser restarts offline. Live Gnani Prisma/Timbre voice AI requires active backend connectivity. Unconfirmed drafts are never auto-committed as completed visits.',
  noLocalDrafts: 'No local drafts in IndexedDB',
  noLocalDraftsDesc: 'Incomplete or offline-confirmed visits appear here with sync status and conflict controls.',
  recordStatus: 'Record',
  updatedLabel: 'Updated',
  retryOverwrite: 'Retry Overwrite Local',
  removeLocal: 'Remove Local',
  syncedStatus: 'Synced',

  basicModeTitle: 'BASIC MODE',
  basicModeBadge: 'Default · Recommended',
  basicModeDesc: 'Simple voice-first household visit: Select beneficiary → Speak notes → Review & Accept.',
  advancedModeTitle: 'ADVANCED MODE',
  advancedModeBadge: 'Detailed Clinical View',
  advancedModeDesc: 'Full maternal/newborn sections, vaccination ledger, audit trail & field-level confirmation.',
  step1Title: '1. Who are you visiting today?',
  step1Subtitle: 'Search or tap a beneficiary below, or identify them naturally while speaking.',
  changeBeneficiary: 'Change Beneficiary',
  recentBeneficiaries: 'Recent Beneficiaries',
  searchDirectoryPlaceholder: 'Search by name, BEN-ID or village...',
  step2Title: '2. Select Speaking Language',
  step2Subtitle: 'Supports Indic languages & natural English code-mixing via Gnani Prisma v3.0.',
  autoDetectIndic: 'Auto-Detect Indic (Mixed)',
  step3Title: '3. Voice Visit Assistant',
  step3Subtitle: 'Speak naturally about today’s visit. You can speak in your language.',
  connectedLabel: 'Connected',
  disconnectedLabel: 'Disconnected',
  startRecording: 'Start Recording',
  stopRecording: 'Stop & Process',
  holdToSpeak: 'Hold to Speak',
  bargeInInterrupt: 'Interrupt / Barge-in',
  handsFreeLabel: 'Hands-Free Mic',
  pushToTalkLabel: 'Push-to-Talk',
  typeInstead: 'Type note instead (fallback)',
  sendText: 'Send',
  stateIdle: 'Idle — Ready to Record',
  stateConnecting: 'Connecting to Voice Backend...',
  stateListening: 'Listening (Gnani Prisma Live)',
  stateTranscribing: 'Transcribing Speech...',
  stateProcessing: 'Processing Visit Extraction...',
  stateResponding: 'Preparing Spoken Response...',
  stateSpeaking: 'Assistant Speaking (Timbre TTS)',
  stateInterrupted: 'Interrupted (Barge-In)',
  stateReconnecting: 'Reconnecting...',
  stateError: 'Session Error',
  stateCompleted: 'Session Completed',
  liveTranscriptHeading: 'Live Transcription',
  spokenDescriptionHeading: 'A. Spoken Description',
  assistantSummaryHeading: 'Assistant Spoken Summary',
  visitSummaryHeading: 'B. Extracted Visit Summary',
  confirmAndSaveVisit: 'Confirm & Save Visit',
  reReadSummary: 'Re-read Aloud',
  saveOfflineDraft: 'Save Offline Draft',
  pauseReadback: 'Pause',
  resumeReadback: 'Resume',
  correctButton: 'Correct',
  confirmField: 'Confirm',
  needsClarification: 'Needs Clarification',
  notIdentified: 'Not identified — needs confirmation',

  urgentDangerSign: 'URGENT DANGER SIGN',
  matchedPhrase: 'Matched phrase',
  urgentPhcReferral: 'Urgent PHC Referral Instruction',
  guidelineReference: 'Guideline Reference',
  detectedAt: 'Detected',
  call108Emergency: 'Call 108 / Emergency Referral',
  acknowledgeAndRefer: 'Acknowledge & Refer to PHC',
  acknowledgeAlert: 'Acknowledge Alert',
  markReferred: 'Mark Referred / En Route',
  markResolved: 'Mark Resolved',
  acknowledgedBy: 'Acknowledged by',

  commandCenterTitle: 'PHC Supervisor Command Center',
  commandCenterSubtitle: 'Live aggregates across registered beneficiaries, field ASHA workers, and urgent NHM danger referrals.',
  alertCommandButton: 'Alert Command',
  registeredBeneficiaries: 'Registered Beneficiaries',
  activeWorkers: 'Active ASHA Workers',
  totalVisits: 'Total Visits',
  activeDangerSigns: 'Active Danger Alerts',
  dangerAlertQueue: 'Live Danger Sign Queue',
  noActiveAlerts: 'No active danger sign alerts.',
  fieldRegister: 'Field Visit Register',
  fieldRegisterSubtitle: 'Confirmed visits recorded by field ASHA workers',
  exportCsv: 'Export CSV',
  printReport: 'Print / PDF Report',
  ashaWorkersTitle: 'ASHA Worker Directory & Performance',
  ashaWorkersSubtitle: 'Monitor assigned household load, completed visits, pending follow-ups, and escalation activity.',
  analyticsTitle: 'PHC Operational Analytics',
  analyticsSubtitle: 'All visualisations are computed directly from persisted visits, danger alerts, follow-ups, and immunisation records.',
  reportsAuditTitle: 'PHC Reports & Compliance Audit',
  reportsAuditSubtitle: 'Export visit register CSVs, print official NHM summaries, and inspect immutable audit logs.',
};

const HI_UI: UiStrings = {
  appName: 'साक्ष्या ASHA',
  ashaPortal: 'आशा पोर्टल',
  supervisorPortal: 'PHC सुपरवाइजर',
  voiceApiLive: 'वॉइस API चालू',
  voiceApiOffline: 'वॉइस API बंद',
  checkingApi: 'API जांच रहे हैं',
  signOut: 'लॉग आउट',
  languageLabel: 'भाषा',
  online: 'ऑनलाइन',
  offline: 'ऑफ़लाइन',
  pendingSync: 'लंबित',
  syncedVisits: 'सिंक की गई विज़िट',
  ashaFieldMode: 'आशा फील्ड मोड',
  supervisorMode: 'PHC सुपरवाइजर',

  navHome: 'होम',
  navVoiceVisit: 'वॉइस विज़िट',
  navBeneficiaries: 'लाभार्थी',
  navFollowUps: 'फॉलो-अप',
  navVisitHistory: 'विज़िट इतिहास',
  navOfflineDrafts: 'ऑफ़लाइन ड्राफ्ट',
  navPhcOverview: 'PHC अवलोकन',
  navDangerAlerts: 'खतरे के अलर्ट',
  navAshaWorkers: 'आशा कार्यकर्ता',
  navVisitRegister: 'विज़िट रजिस्टर',
  navAnalytics: 'एनालिटिक्स',
  navReportsAudit: 'रिपोर्ट व ऑडिट',

  loginHeroTitle: 'वॉइस-फर्स्ट मातृ एवं नवजात फील्ड रजिस्टर',
  loginHeroDesc: 'गृह भेंट के दौरान अपनी भाषा में स्वाभाविक रूप से बोलें। रिकॉर्ड स्वतः तैयार होते हैं, पुष्टि के लिए पढ़कर सुनाए जाते हैं और खतरे के संकेतों पर तुरंत अलर्ट मिलता है।',
  syntheticRolesHeading: 'डेमो भूमिकाएँ (बिना व्यक्तिगत डेटा)',
  zeroPiiNote: 'सभी लाभार्थी (BEN-1042–BEN-1048) और विज़िट रिकॉर्ड केवल डेमो के लिए हैं।',
  selectAppLanguage: 'ऐप और बोलने की भाषा चुनें',
  staffSignInTitle: 'स्टाफ लॉग इन',
  staffSignInDesc: 'अपने PHC या आशा स्टाफ ईमेल से लॉग इन करें, या बाईं ओर से डेमो भूमिका चुनें।',
  emailLabel: 'ईमेल पता',
  passwordLabel: 'पासवर्ड',
  signInButton: 'लॉग इन करें',
  signingInButton: 'लॉग इन हो रहा है...',
  localDemoModeNotice: 'लोकल डेमो मोड: Supabase Auth कॉन्फ़िगर नहीं है। बाईं ओर किसी भी डेमो कार्ड पर क्लिक करें।',

  namasteGreeting: 'नमस्ते',
  homeVoicePrompt: 'बिना टाइप किए बोलकर गृह भेंट दर्ज करने के लिए नीचे दबाएं।',
  startVoiceVisit: 'वॉइस विज़िट शुरू करें',
  assignedHouseholds: 'आवंटित परिवार',
  viewDirectory: 'सूची देखें',
  visitsToday: 'आज की विज़िट',
  totalLogged: 'कुल दर्ज',
  pendingFollowUps: 'बाकी फॉलो-अप',
  openTaskQueue: 'कार्य सूची खोलें',
  vaccinesDue: 'बाकी टीके',
  dueOverdueDoses: 'देय और विलंबित खुराक',
  allTasks: 'सभी कार्य',
  noPendingTasks: 'कोई लंबित फॉलो-अप कार्य नहीं।',
  recentSavedVisits: 'हाल की सहेजी गई विज़िट',
  fullHistory: 'पूरा इतिहास',
  noVisitsRecorded: 'अभी कोई विज़िट दर्ज नहीं हुई।',
  dangerFlagged: 'खतरा चिह्नित',
  confirmed: 'पुष्ट',
  dueLabel: 'देय',
  nextVisitLabel: 'अगली विज़िट',
  weightLabel: 'वजन',

  beneficiaryDirectoryTitle: 'लाभार्थी सूची',
  beneficiaryDirectorySubtitle: 'Agent 1 बैकएंड के साथ सिंक किया गया परिवार रजिस्टर (BEN-1042–BEN-1048)।',
  searchBeneficiariesPlaceholder: 'नाम, BEN-ID या वार्ड खोजें...',
  allBeneficiaries: 'सभी लाभार्थी',
  highRiskWatch: 'उच्च जोखिम निगरानी',
  ancFilter: 'गर्भवती (ANC)',
  pncFilter: 'प्रसूता माता (PNC)',
  infantFilter: 'नवजात / शिशु',
  childFilter: 'बच्चा',
  noMatchingBeneficiaries: 'कोई लाभार्थी नहीं मिला',
  noMatchingBeneficiariesDesc: 'खोज शब्द साफ़ करें या श्रेणी फ़िल्टर बदलें।',
  viewProfile: 'प्रोफ़ाइल देखें',
  voiceVisitButton: 'वॉइस विज़िट',
  householdHead: 'परिवार के मुखिया',
  eddLabel: 'प्रसव तिथि (EDD)',
  highRisk: 'उच्च जोखिम',
  yrsLabel: 'वर्ष',
  infantNewborn: 'नवजात/शिशु',

  followUpsTitle: 'फॉलो-अप और टीकाकरण सूची',
  followUpsSubtitle: 'नियमित जांच, तत्काल PHC रेफरल और देय टीकों को ट्रैक करें।',
  searchFollowUpsPlaceholder: 'लाभार्थी या कार्य खोजें...',
  upcomingTasks: 'आगामी कार्य',
  overdueTab: 'विलंबित',
  pendingVaccinesTab: 'बाकी टीके',
  completedTab: 'पूर्ण',
  noPendingVaccines: 'कोई टीकाकरण लंबित नहीं',
  noPendingVaccinesDesc: 'आपकी खोज से मेल खाने वाली सभी खुराकें अद्यतन हैं।',
  noTasksInQueue: 'इस सूची में कोई कार्य नहीं',
  noTasksInQueueDesc: 'पुष्ट वॉइस विज़िट से बने कार्य यहाँ स्वतः दिखेंगे।',
  dueDateLabel: 'नियत तिथि',
  beneficiaryLabel: 'लाभार्थी',

  visitHistoryTitle: 'विज़िट इतिहास',
  visitHistorySubtitle: 'पुष्ट और सहेजी गई गृह भेंट। अपुष्ट ड्राफ्ट ऑफ़लाइन ड्राफ्ट में रहते हैं।',
  noSavedVisitsYet: 'अभी कोई सहेजी गई विज़िट नहीं',
  noSavedVisitsDesc: 'इतिहास में देखने के लिए एक वॉइस विज़िट पूरी करके पुष्टि करें।',
  colDate: 'तिथि',
  colBeneficiary: 'लाभार्थी',
  colType: 'प्रकार',
  colWeight: 'वजन',
  colDangerSign: 'खतरे का संकेत',
  colStatus: 'स्थिति',
  colAction: 'कार्रवाई',
  inspectButton: 'जांचें',
  clearStatus: 'सामान्य',
  flaggedStatus: 'चिह्नित',
  visitRecordTitle: 'विज़िट रिकॉर्ड',
  vaccinationsCompleted: 'पूर्ण टीकाकरण',
  vaccinationsDue: 'देय टीकाकरण',
  nextVisitDateLabel: 'अगली विज़िट तिथि',
  persistenceRef: 'रिकॉर्ड संदर्भ',
  summaryTranscript: 'सारांश प्रतिलेख',

  offlineDraftsTitle: 'ऑफ़लाइन ड्राफ्ट व सिंक कतार',
  offlineDraftsSubtitle: 'डुप्लिकेट रोकने के लिए visit_id कुंजी के साथ IndexedDB में सुरक्षित।',
  syncConfirmedQueue: 'पुष्ट कतार सिंक करें',
  syncingConfirmedVisits: 'सिंक हो रहा है...',
  offlinePolicyTitle: 'ऑफ़लाइन कार्य नीति',
  offlinePolicyDesc: 'स्थानीय ड्राफ्ट ऑफ़लाइन भी सुरक्षित रहते हैं। लाइव वॉइस AI के लिए बैकएंड कनेक्शन आवश्यक है। अपुष्ट ड्राफ्ट कभी स्वतः सहेजे नहीं जाते।',
  noLocalDrafts: 'IndexedDB में कोई स्थानीय ड्राफ्ट नहीं',
  noLocalDraftsDesc: 'अधूरी या ऑफ़लाइन-पुष्ट विज़िट यहाँ दिखेंगी।',
  recordStatus: 'रिकॉर्ड',
  updatedLabel: 'अद्यतन',
  retryOverwrite: 'स्थानीय डेटा से पुनः प्रयास करें',
  removeLocal: 'स्थानीय हटाएं',
  syncedStatus: 'सिंक हुआ',

  basicModeTitle: 'सरल मोड (Basic)',
  basicModeBadge: 'डिफ़ॉल्ट · अनुशंसित',
  basicModeDesc: 'आसान वॉइस विज़िट: लाभार्थी चुनें → बोलकर दर्ज करें → सुनें और सहेजें।',
  advancedModeTitle: 'उन्नत मोड (Advanced)',
  advancedModeBadge: 'विस्तृत क्लिनिकल दृश्य',
  advancedModeDesc: 'पूर्ण मातृ/नवजात अनुभाग, टीकाकरण लेज़र, ऑडिट और फील्ड-वार पुष्टि।',
  step1Title: '1. आज आप किससे मिलने जा रही हैं?',
  step1Subtitle: 'नीचे लाभार्थी चुनें या बोलते समय उनका नाम बताएं।',
  changeBeneficiary: 'लाभार्थी बदलें',
  recentBeneficiaries: 'हाल के लाभार्थी',
  searchDirectoryPlaceholder: 'नाम, BEN-ID या गाँव से खोजें...',
  step2Title: '2. बोलने की भाषा चुनें',
  step2Subtitle: 'Gnani Prisma v3.0 के साथ भारतीय भाषाएँ और हिंदी-अंग्रेज़ी मिश्रित बोली समर्थित।',
  autoDetectIndic: 'ऑटो-डिटेक्ट (मिश्रित भारतीय)',
  step3Title: '3. वॉइस विज़िट सहायक',
  step3Subtitle: 'आज की भेंट के बारे में अपनी भाषा में स्वाभाविक रूप से बोलें।',
  connectedLabel: 'जुड़ा हुआ',
  disconnectedLabel: 'डिस्कनेक्ट',
  startRecording: 'रिकॉर्डिंग शुरू करें',
  stopRecording: 'रोकें और प्रोसेस करें',
  holdToSpeak: 'बोलने के लिए दबाए रखें',
  bargeInInterrupt: 'बीच में रोकें (Barge-in)',
  handsFreeLabel: 'हैंड्स-फ्री माइक',
  pushToTalkLabel: 'दबाकर बोलें',
  typeInstead: 'बोलने के बजाय लिखें',
  sendText: 'भेजें',
  stateIdle: 'तैयार — रिकॉर्ड करने के लिए दबाएं',
  stateConnecting: 'वॉइस सेवा से जुड़ रहा है...',
  stateListening: 'सुन रहा है (Gnani Prisma लाइव)',
  stateTranscribing: 'आवाज़ को टेक्स्ट में बदल रहा है...',
  stateProcessing: 'विवरण निकाला जा रहा है...',
  stateResponding: 'जवाब तैयार हो रहा है...',
  stateSpeaking: 'सहायक बोल रहा है (Timbre TTS)',
  stateInterrupted: 'बीच में रोका गया (Barge-In)',
  stateReconnecting: 'पुनः जुड़ रहा है...',
  stateError: 'सत्र त्रुटि',
  stateCompleted: 'सत्र पूर्ण',
  liveTranscriptHeading: 'लाइव प्रतिलेख (Transcription)',
  spokenDescriptionHeading: 'A. बोला गया विवरण',
  assistantSummaryHeading: 'सहायक द्वारा पढ़ा गया सारांश',
  visitSummaryHeading: 'B. निकाला गया विज़िट सारांश',
  confirmAndSaveVisit: 'पुष्टि करें और सहेजें',
  reReadSummary: 'दोबारा सुनें',
  saveOfflineDraft: 'ऑफ़लाइन ड्राफ्ट सहेजें',
  pauseReadback: 'रोकें',
  resumeReadback: 'जारी रखें',
  correctButton: 'सुधारें',
  confirmField: 'पुष्टि करें',
  needsClarification: 'स्पष्टीकरण आवश्यक',
  notIdentified: 'पहचान नहीं हुई — पुष्टि आवश्यक',

  urgentDangerSign: 'तत्काल खतरे का संकेत',
  matchedPhrase: 'पहचाना गया वाक्य',
  urgentPhcReferral: 'तत्काल PHC रेफरल निर्देश',
  guidelineReference: 'दिशानिर्देश संदर्भ',
  detectedAt: 'पहचान समय',
  call108Emergency: '108 एम्बुलेंस / आपातकालीन कॉल',
  acknowledgeAndRefer: 'स्वीकार करें और PHC भेजें',
  acknowledgeAlert: 'अलर्ट स्वीकार करें',
  markReferred: 'रेफर किया गया चिह्नित करें',
  markResolved: 'समाधान चिह्नित करें',
  acknowledgedBy: 'स्वीकृतकर्ता',

  commandCenterTitle: 'PHC सुपरवाइजर कमांड सेंटर',
  commandCenterSubtitle: 'पंजीकृत लाभार्थियों, आशा कार्यकर्ताओं और तत्काल NHM रेफरल का लाइव विवरण।',
  alertCommandButton: 'अलर्ट कमांड',
  registeredBeneficiaries: 'पंजीकृत लाभार्थी',
  activeWorkers: 'सक्रिय आशा कार्यकर्ता',
  totalVisits: 'कुल विज़िट',
  activeDangerSigns: 'सक्रिय खतरे के अलर्ट',
  dangerAlertQueue: 'लाइव खतरा संकेत कतार',
  noActiveAlerts: 'अभी कोई सक्रिय खतरा अलर्ट नहीं है।',
  fieldRegister: 'फील्ड विज़िट रजिस्टर',
  fieldRegisterSubtitle: 'आशा कार्यकर्ताओं द्वारा दर्ज पुष्ट विज़िट',
  exportCsv: 'CSV डाउनलोड करें',
  printReport: 'प्रिंट / PDF रिपोर्ट',
  ashaWorkersTitle: 'आशा कार्यकर्ता सूची और प्रदर्शन',
  ashaWorkersSubtitle: 'आवंटित परिवार, पूर्ण विज़िट, लंबित फॉलो-अप और रेफरल देखें।',
  analyticsTitle: 'PHC संचालन एनालिटिक्स',
  analyticsSubtitle: 'सभी चार्ट सहेजी गई विज़िट, अलर्ट और टीकाकरण डेटा से लाइव गणना किए गए हैं।',
  reportsAuditTitle: 'PHC रिपोर्ट और अनुपालन ऑडिट',
  reportsAuditSubtitle: 'विज़िट रजिस्टर CSV निर्यात करें, NHM सारांश प्रिंट करें और ऑडिट लॉग देखें।',
};

const KN_UI: UiStrings = {
  ...EN_UI,
  appName: 'ಸಾಕ್ಷ್ಯ ASHA',
  ashaPortal: 'ಆಶಾ ಪೋರ್ಟಲ್',
  supervisorPortal: 'PHC ಮೇಲ್ವಿಚಾರಕರು',
  voiceApiLive: 'ವಾಯ್ಸ್ API ಚಾಲನೆ',
  voiceApiOffline: 'ವಾಯ್ಸ್ API ಆಫ್‌ಲೈನ್',
  checkingApi: 'API ಪರಿಶೀಲನೆ',
  signOut: 'ಲಾಗ್ ಔಟ್',
  languageLabel: 'ಭಾಷೆ',
  online: 'ಆನ್‌ಲೈನ್',
  offline: 'ಆಫ್‌ಲೈನ್',
  pendingSync: 'ಬಾಕಿ',
  syncedVisits: 'ಸಿಂಕ್ ಆದ ಭೇಟಿಗಳು',
  ashaFieldMode: 'ಆಶಾ ಕ್ಷೇತ್ರ ಮೋಡ್',
  supervisorMode: 'PHC ಮೇಲ್ವಿಚಾರಕರು',

  navHome: 'ಮುಖಪುಟ',
  navVoiceVisit: 'ವಾಯ್ಸ್ ಭೇಟಿ',
  navBeneficiaries: 'ಫಲಾನುಭವಿಗಳು',
  navFollowUps: 'ಫಾಲೋ-ಅಪ್‌ಗಳು',
  navVisitHistory: 'ಭೇಟಿ ಇತಿಹಾಸ',
  navOfflineDrafts: 'ಆಫ್‌ಲೈನ್ ಡ್ರಾಫ್ಟ್',
  navPhcOverview: 'PHC ಅವಲೋಕನ',
  navDangerAlerts: 'ಅಪಾಯದ ಎಚ್ಚರಿಕೆ',
  navAshaWorkers: 'ಆಶಾ ಕಾರ್ಯಕರ್ತರು',
  navVisitRegister: 'ಭೇಟಿ ರಿಜಿಸ್ಟರ್',
  navAnalytics: 'ವಿಶ್ಲೇಷಣೆ',
  navReportsAudit: 'ವರದಿ ಮತ್ತು ಆಡಿಟ್',

  loginHeroTitle: 'ಧ್ವನಿ-ಆಧಾರಿತ ತಾಯಿ ಮತ್ತು ನವಜಾತ ಶಿಶು ಕ್ಷೇತ್ರ ರಿಜಿಸ್ಟರ್',
  loginHeroDesc: 'ಮನೆ ಭೇಟಿಯ ಸಮಯದಲ್ಲಿ ನಿಮ್ಮ ಭಾಷೆಯಲ್ಲಿ ಸಹಜವಾಗಿ ಮಾತನಾಡಿ. ದಾಖಲೆಗಳು ಸ್ವಯಂಚಾಲಿತವಾಗಿ ಸಿದ್ಧವಾಗುತ್ತವೆ ಮತ್ತು ಅಪಾಯದ ಲಕ್ಷಣಗಳಿಗೆ ತಕ್ಷಣ ಎಚ್ಚರಿಕೆ ನೀಡಲಾಗುತ್ತದೆ.',
  syntheticRolesHeading: 'ಡೆಮೋ ಪಾತ್ರಗಳು (Zero PII)',
  selectAppLanguage: 'ಆ್ಯಪ್ ಮತ್ತು ಧ್ವನಿ ಭಾಷೆ ಆಯ್ಕೆಮಾಡಿ',
  staffSignInTitle: 'ಸಿಬ್ಬಂದಿ ಲಾಗಿನ್',
  signInButton: 'ಲಾಗಿನ್ ಆಗಿ',

  namasteGreeting: 'ನಮಸ್ಕಾರ',
  homeVoicePrompt: 'ಟೈಪ್ ಮಾಡದೆ ಧ್ವನಿಯ ಮೂಲಕ ಮನೆ ಭೇಟಿ ದಾಖಲಿಸಲು ಕೆಳಗೆ ಟ್ಯಾಪ್ ಮಾಡಿ.',
  startVoiceVisit: 'ವಾಯ್ಸ್ ಭೇಟಿ ಪ್ರಾರಂಭಿಸಿ',
  assignedHouseholds: 'ನಿಯೋಜಿತ ಕುಟುಂಬಗಳು',
  viewDirectory: 'ಪಟ್ಟಿ ನೋಡಿ',
  visitsToday: 'ಇಂದಿನ ಭೇಟಿಗಳು',
  pendingFollowUps: 'ಬಾಕಿ ಫಾಲೋ-ಅಪ್‌ಗಳು',
  vaccinesDue: 'ಬಾಕಿ ಲಸಿಕೆಗಳು',
  allTasks: 'ಎಲ್ಲಾ ಕಾರ್ಯಗಳು',
  recentSavedVisits: 'ಇತ್ತೀಚಿನ ಭೇಟಿಗಳು',
  fullHistory: 'ಪೂರ್ಣ ಇತಿಹಾಸ',
  dangerFlagged: 'ಅಪಾಯ ಪತ್ತೆಯಾಗಿದೆ',
  confirmed: 'ದೃಢೀಕರಿಸಲಾಗಿದೆ',

  beneficiaryDirectoryTitle: 'ಫಲಾನುಭವಿಗಳ ಪಟ್ಟಿ',
  searchBeneficiariesPlaceholder: 'ಹೆಸರು, BEN-ID ಅಥವಾ ವಾರ್ಡ್ ಹುಡುಕಿ...',
  allBeneficiaries: 'ಎಲ್ಲಾ ಫಲಾನುಭವಿಗಳು',
  highRiskWatch: 'ಹೆಚ್ಚಿನ ಅಪಾಯ',
  ancFilter: 'ಗರ್ಭಿಣಿ (ANC)',
  pncFilter: 'ಬಾಣಂತಿ (PNC)',
  infantFilter: 'ನವಜಾತ ಶಿಶು',
  childFilter: 'ಮಗು',
  viewProfile: 'ವಿವರ ನೋಡಿ',
  voiceVisitButton: 'ವಾಯ್ಸ್ ಭೇಟಿ',
  highRisk: 'ಹೆಚ್ಚಿನ ಅಪಾಯ',

  followUpsTitle: 'ಫಾಲೋ-ಅಪ್ ಮತ್ತು ಲಸಿಕೆ ಪಟ್ಟಿ',
  upcomingTasks: 'ಮುಂಬರುವ ಕಾರ್ಯಗಳು',
  overdueTab: 'ಮೀರಿದವು',
  pendingVaccinesTab: 'ಬಾಕಿ ಲಸಿಕೆಗಳು',
  completedTab: 'ಪೂರ್ಣಗೊಂಡವು',

  visitHistoryTitle: 'ಭೇಟಿ ಇತಿಹಾಸ',
  offlineDraftsTitle: 'ಆಫ್‌ಲೈನ್ ಡ್ರಾಫ್ಟ್ ಮತ್ತು ಸಿಂಕ್',
  syncConfirmedQueue: 'ಕ್ಯೂ ಸಿಂಕ್ ಮಾಡಿ',

  basicModeTitle: 'ಸರಳ ಮೋಡ್ (Basic)',
  advancedModeTitle: 'ಸುಧಾರಿತ ಮೋಡ್ (Advanced)',
  step1Title: '1. ಇಂದು ನೀವು ಯಾರನ್ನು ಭೇಟಿಯಾಗುತ್ತಿದ್ದೀರಿ?',
  step2Title: '2. ಮಾತನಾಡುವ ಭಾಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ',
  step3Title: '3. ವಾಯ್ಸ್ ಭೇಟಿ ಸಹಾಯಕ',
  startRecording: 'ರೆಕಾರ್ಡಿಂಗ್ ಪ್ರಾರಂಭಿಸಿ',
  stopRecording: 'ನಿಲ್ಲಿಸಿ ಮತ್ತು ಪ್ರಕ್ರಿಯೆಗೊಳಿಸಿ',
  bargeInInterrupt: 'ಮಧ್ಯೆ ನಿಲ್ಲಿಸಿ (Barge-in)',
  confirmAndSaveVisit: 'ದೃಢೀಕರಿಸಿ ಮತ್ತು ಉಳಿಸಿ',
  reReadSummary: 'ಮತ್ತೆ ಓದಿ ಕೇಳಿಸಿ',

  urgentDangerSign: 'ತುರ್ತು ಅಪಾಯದ ಲಕ್ಷಣ',
  urgentPhcReferral: 'ತುರ್ತು PHC ರೆಫರಲ್ ಸೂಚನೆ',
  call108Emergency: '108 ಆಂಬ್ಯುಲೆನ್ಸ್ ಕರೆ ಮಾಡಿ',
  acknowledgeAndRefer: 'ದೃಢೀಕರಿಸಿ ಮತ್ತು PHC ಗೆ ಕಳುಹಿಸಿ',
  acknowledgeAlert: 'ಎಚ್ಚರಿಕೆ ದೃಢೀಕರಿಸಿ',

  commandCenterTitle: 'PHC ಮೇಲ್ವಿಚಾರಕ ಕಮಾಂಡ್ ಸೆಂಟರ್',
  registeredBeneficiaries: 'ನೋಂದಾಯಿತ ಫಲಾನುಭವಿಗಳು',
  activeWorkers: 'ಸಕ್ರಿಯ ಆಶಾ ಕಾರ್ಯಕರ್ತರು',
  totalVisits: 'ಒಟ್ಟು ಭೇಟಿಗಳು',
  activeDangerSigns: 'ಸಕ್ರಿಯ ಅಪಾಯದ ಎಚ್ಚರಿಕೆಗಳು',
  dangerAlertQueue: 'ಲೈವ್ ಅಪಾಯದ ಎಚ್ಚರಿಕೆ ಪಟ್ಟಿ',
  fieldRegister: 'ಕ್ಷೇತ್ರ ಭೇಟಿ ರಿಜಿಸ್ಟರ್',
  exportCsv: 'CSV ರಫ್ತು ಮಾಡಿ',
  printReport: 'ಪ್ರಿಂಟ್ / PDF ವರದಿ',
  ashaWorkersTitle: 'ಆಶಾ ಕಾರ್ಯಕರ್ತರ ಪಟ್ಟಿ',
  analyticsTitle: 'PHC ಕಾರ್ಯಾಚರಣೆ ವಿಶ್ಲೇಷಣೆ',
  reportsAuditTitle: 'PHC ವರದಿಗಳು ಮತ್ತು ಆಡಿಟ್',
};

const TA_UI: UiStrings = {
  ...EN_UI,
  appName: 'சாக்ஷ்யா ASHA',
  ashaPortal: 'ஆஷா போர்டல்',
  supervisorPortal: 'PHC மேற்பார்வையாளர்',
  voiceApiLive: 'குரல் API இயங்குகிறது',
  voiceApiOffline: 'குரல் API ஆஃப்லைன்',
  signOut: 'வெளியேறு',
  languageLabel: 'மொழி',
  online: 'ஆன்லைன்',
  offline: 'ஆஃப்லைன்',
  pendingSync: 'நிலுவை',
  syncedVisits: 'ஒத்திசைக்கப்பட்டவை',
  ashaFieldMode: 'ஆஷா கள முறை',
  supervisorMode: 'PHC மேற்பார்வையாளர்',

  navHome: 'முகப்பு',
  navVoiceVisit: 'குரல் வருகை',
  navBeneficiaries: 'பயனாளிகள்',
  navFollowUps: 'தொடர் கண்காணிப்பு',
  navVisitHistory: 'வருகை வரலாறு',
  navOfflineDrafts: 'ஆஃப்லைன் வரைவுகள்',
  navPhcOverview: 'PHC மேலோட்டம்',
  navDangerAlerts: 'அபாய எச்சரிக்கை',
  navAshaWorkers: 'ஆஷா பணியாளர்கள்',
  navVisitRegister: 'வருகைப் பதிவேடு',
  navAnalytics: 'பகுப்பாய்வு',
  navReportsAudit: 'அறிக்கைகள்',

  loginHeroTitle: 'குரல் வழி தாய் மற்றும் சிசு களப் பதிவேடு',
  selectAppLanguage: 'மொழியைத் தேர்ந்தெடுக்கவும்',
  staffSignInTitle: 'பணியாளர் உள்நுழைவு',
  signInButton: 'உள்நுழைக',

  namasteGreeting: 'வணக்கம்',
  homeVoicePrompt: 'தட்டச்சு செய்யாமல் குரல் மூலம் வீட்டு வருகையை பதிவு செய்ய கீழே தட்டவும்.',
  startVoiceVisit: 'குரல் வருகையைத் தொடங்கு',
  assignedHouseholds: 'ஒதுக்கப்பட்ட குடும்பங்கள்',
  visitsToday: 'இன்றைய வருகைகள்',
  pendingFollowUps: 'நிலுவை பணிகள்',
  vaccinesDue: 'தடுப்பூசிகள் நிலுவை',
  recentSavedVisits: 'சமீபத்திய வருகைகள்',
  dangerFlagged: 'அபாயம் கண்டறியப்பட்டது',
  confirmed: 'உறுதிசெய்யப்பட்டது',

  beneficiaryDirectoryTitle: 'பயனாளிகள் பட்டியல்',
  allBeneficiaries: 'அனைத்து பயனாளிகள்',
  highRiskWatch: 'அதிக ஆபத்து',
  ancFilter: 'கர்ப்பிணி (ANC)',
  pncFilter: 'பாலூட்டும் தாய் (PNC)',
  infantFilter: 'பச்சிளம் குழந்தை',
  childFilter: 'குழந்தை',
  viewProfile: 'விவரம் காண்க',
  voiceVisitButton: 'குரல் வருகை',

  followUpsTitle: 'தொடர் கண்காணிப்பு & தடுப்பூசி',
  visitHistoryTitle: 'வருகை வரலாறு',
  offlineDraftsTitle: 'ஆஃப்லைன் வரைவுகள் & ஒத்திசைவு',

  basicModeTitle: 'எளிய முறை (Basic)',
  advancedModeTitle: 'மேம்பட்ட முறை (Advanced)',
  step1Title: '1. இன்று யாரைச் சந்திக்கிறீர்கள்?',
  step2Title: '2. பேசும் மொழியைத் தேர்ந்தெடுக்கவும்',
  step3Title: '3. குரல் வருகை உதவியாளர்',
  startRecording: 'பதிவைத் தொடங்கு',
  stopRecording: 'நிறுத்தி செயலாக்கு',
  bargeInInterrupt: 'இடையில் நிறுத்து',
  confirmAndSaveVisit: 'உறுதிசெய்து சேமி',

  urgentDangerSign: 'அவசர அபாய அறிகுறி',
  urgentPhcReferral: 'அவசர PHC பரிந்துரை',
  call108Emergency: '108 ஆம்புலன்ஸ் அழைக்கவும்',
  acknowledgeAndRefer: 'ஏற்று PHC-க்கு அனுப்பு',

  commandCenterTitle: 'PHC மேற்பார்வையாளர் மையம்',
  registeredBeneficiaries: 'பதிவு செய்யப்பட்ட பயனாளிகள்',
  activeWorkers: 'செயலில் உள்ள ஆஷா பணியாளர்கள்',
  totalVisits: 'மொத்த வருகைகள்',
  activeDangerSigns: 'செயலில் உள்ள அபாய எச்சரிக்கைகள்',
  exportCsv: 'CSV பதிவிறக்கு',
  printReport: 'அறிக்கை அச்சிடு',
};

const TE_UI: UiStrings = {
  ...EN_UI,
  appName: 'సాక్ష్య ASHA',
  ashaPortal: 'ఆశా పోర్టల్',
  supervisorPortal: 'PHC సూపర్‌వైజర్',
  voiceApiLive: 'వాయిస్ API లైవ్',
  voiceApiOffline: 'వాయిస్ API ఆఫ్‌లైన్',
  signOut: 'సైన్ అవుట్',
  languageLabel: 'భాష',
  online: 'ఆన్‌లైన్',
  offline: 'ఆఫ్‌లైన్',
  navHome: 'హోమ్',
  navVoiceVisit: 'వాయిస్ విజిట్',
  navBeneficiaries: 'లబ్ధిదారులు',
  navFollowUps: 'ఫాలో-అప్‌లు',
  navVisitHistory: 'విజిట్ చరిత్ర',
  navOfflineDrafts: 'ఆఫ్‌లైన్ డ్రాఫ్ట్‌లు',
  navPhcOverview: 'PHC అవలోకనం',
  navDangerAlerts: 'ప్రమాద హెచ్చరికలు',
  navAshaWorkers: 'ఆశా కార్యకర్తలు',
  navVisitRegister: 'విజిట్ రిజిస్టర్',
  navAnalytics: 'విశ్లేషణ',
  navReportsAudit: 'నివేదికలు',
  namasteGreeting: 'నమస్కారం',
  homeVoicePrompt: 'టైప్ చేయకుండా మాటల ద్వారా గృహ సందర్శనను నమోదు చేయడానికి క్రింద నొక్కండి.',
  startVoiceVisit: 'వాయిస్ విజిట్ ప్రారంభించండి',
  assignedHouseholds: 'కేటాయించిన కుటుంబాలు',
  visitsToday: 'నేటి విజిట్లు',
  pendingFollowUps: 'పెండింగ్ ఫాలో-అప్‌లు',
  vaccinesDue: 'బಾಕీ టీకాలు',
  beneficiaryDirectoryTitle: 'లబ్ధిదారుల జాబితా',
  followUpsTitle: 'ఫాలో-అప్‌లు & టీకాల జాబితా',
  visitHistoryTitle: 'విజిట్ చరిత్ర',
  offlineDraftsTitle: 'ఆఫ్‌లైన్ డ్రాఫ్ట్‌లు & సింక్',
  startRecording: 'రికార్డింగ్ ప్రారంభించండి',
  stopRecording: 'ఆపి ప్రాసెస్ చేయండి',
  confirmAndSaveVisit: 'నిర్ధారించి సేవ్ చేయండి',
  urgentDangerSign: 'తక్షణ ప్రమాద సంకేతం',
  call108Emergency: '108 అంబులెన్స్‌కు కాల్ చేయండి',
  commandCenterTitle: 'PHC సూపర్‌వైజర్ కమాండ్ సెంటర్',
};

const ML_UI: UiStrings = {
  ...EN_UI,
  appName: 'സാക്ഷ്യ ASHA',
  ashaPortal: 'ആശ പോർട്ടൽ',
  supervisorPortal: 'PHC സൂപ്പർവൈസർ',
  signOut: 'സൈൻ ഔട്ട്',
  languageLabel: 'ഭാഷ',
  online: 'ഓൺലൈൻ',
  offline: 'ഓഫ്‌ലൈൻ',
  navHome: 'ഹോം',
  navVoiceVisit: 'വോയ്‌സ് വിസിറ്റ്',
  navBeneficiaries: 'ഗുണഭോക്താക്കൾ',
  navFollowUps: 'ഫോളോ-അപ്പുകൾ',
  navVisitHistory: 'സന്ദർശന ചരിത്രം',
  navOfflineDrafts: 'ഓഫ്‌ലൈൻ ഡ്രാഫ്റ്റുകൾ',
  navPhcOverview: 'PHC അവലോകനം',
  navDangerAlerts: 'അപകട മുന്നറിയിപ്പുകൾ',
  navAshaWorkers: 'ആശാ പ്രവർത്തകർ',
  navVisitRegister: 'സന്ദർശന രജിസ്റ്റർ',
  navAnalytics: 'അനലിറ്റിക്സ്',
  navReportsAudit: 'റിപ്പോർട്ടുകൾ',
  namasteGreeting: 'നമസ്കാരം',
  homeVoicePrompt: 'ടൈപ്പ് ചെയ്യാതെ ശബ്ദത്തിലൂടെ ഗൃഹസന്ദർശനം രേഖപ്പെടുത്താൻ താഴെ ടാപ്പ് ചെയ്യുക.',
  startVoiceVisit: 'വോയ്‌സ് വിസിറ്റ് ആരംഭിക്കുക',
  assignedHouseholds: 'ചുമതലയുള്ള വീടുകൾ',
  visitsToday: 'ഇന്നത്തെ സന്ദർശനങ്ങൾ',
  pendingFollowUps: 'ബാക്കി ഫോളോ-അപ്പുകൾ',
  vaccinesDue: 'നൽകാനുള്ള വാക്സിനുകൾ',
  beneficiaryDirectoryTitle: 'ഗുണഭോക്താക്കളുടെ പട്ടിക',
  followUpsTitle: 'ഫോളോ-അപ്പുകളും വാക്സിനേഷനും',
  visitHistoryTitle: 'സന്ദർശന ചരിത്രം',
  offlineDraftsTitle: 'ഓഫ്‌ലൈൻ ഡ്രാഫ്റ്റുകൾ',
  startRecording: 'റെക്കോർഡിംഗ് തുടങ്ങുക',
  stopRecording: 'നിർത്തി പ്രോസസ്സ് ചെയ്യുക',
  confirmAndSaveVisit: 'സ്ഥിരീകരിച്ച് സംരക്ഷിക്കുക',
  urgentDangerSign: 'അടിയന്തര അപകട ലക്ഷണം',
  call108Emergency: '108 ആംബുലൻസ് വിളിക്കുക',
  commandCenterTitle: 'PHC സൂപ്പർവൈസർ കമാൻഡ് സെന്റർ',
};

const BN_UI: UiStrings = {
  ...EN_UI,
  appName: 'সাক্ষ্য ASHA',
  ashaPortal: 'আশা পোর্টাল',
  supervisorPortal: 'PHC সুপারভাইজার',
  signOut: 'লগ আউট',
  languageLabel: 'ভাষা',
  online: 'অনলাইন',
  offline: 'অফলাইন',
  navHome: 'হোম',
  navVoiceVisit: 'ভয়েস ভিজিট',
  navBeneficiaries: 'সুবিধাভোগী',
  navFollowUps: 'ফলো-আপ',
  navVisitHistory: 'ভিজিটের ইতিহাস',
  navOfflineDrafts: 'অফলাইন ড্রাফট',
  navPhcOverview: 'PHC ওভারভিউ',
  navDangerAlerts: 'বিপদ সতর্কতা',
  navAshaWorkers: 'আশা কর্মী',
  navVisitRegister: 'ভিজিট রেজিস্টার',
  navAnalytics: 'বিশ্লেষণ',
  navReportsAudit: 'রিপোর্ট ও অডিট',
  namasteGreeting: 'নমস্কার',
  homeVoicePrompt: 'টাইপ না করে কণ্ঠস্বরের মাধ্যমে গৃহ পরিদর্শন রেকর্ড করতে নিচে ট্যাপ করুন।',
  startVoiceVisit: 'ভয়েস ভিজিট শুরু করুন',
  assignedHouseholds: 'বরাদ্দকৃত পরিবার',
  visitsToday: 'আজকের ভিজিট',
  pendingFollowUps: 'বাকি ফলো-আপ',
  vaccinesDue: 'বাকি টিকা',
  beneficiaryDirectoryTitle: 'সুবিধাভোগী তালিকা',
  followUpsTitle: 'ফলো-আপ ও টিকাদান তালিকা',
  visitHistoryTitle: 'ভিজিটের ইতিহাস',
  offlineDraftsTitle: 'অফলাইন ড্রাফট ও সিঙ্ক',
  startRecording: 'রেকর্ডিং শুরু করুন',
  stopRecording: 'থামান ও প্রসেস করুন',
  confirmAndSaveVisit: 'নিশ্চিত করে সংরক্ষণ করুন',
  urgentDangerSign: 'জরুরি বিপদের লক্ষণ',
  call108Emergency: '১০৮ অ্যাম্বুলেন্সে কল করুন',
  commandCenterTitle: 'PHC সুপারভাইজার কমান্ড সেন্টার',
};

const MR_UI: UiStrings = {
  ...EN_UI,
  appName: 'साक्ष्य ASHA',
  ashaPortal: 'आशा पोर्टल',
  supervisorPortal: 'PHC पर्यवेक्षक',
  signOut: 'लॉग आउट',
  languageLabel: 'भाषा',
  online: 'ऑनलाइन',
  offline: 'ऑफलाइन',
  navHome: 'मुख्यपृष्ठ',
  navVoiceVisit: 'व्हॉइस भेट',
  navBeneficiaries: 'लाभार्थी',
  navFollowUps: 'फॉलो-अप',
  navVisitHistory: 'भेटींचा इतिहास',
  navOfflineDrafts: 'ऑफलाइन मसुदे',
  navPhcOverview: 'PHC आढावा',
  navDangerAlerts: 'धोक्याचे अलर्ट',
  navAshaWorkers: 'आशा सेविका',
  navVisitRegister: 'भेट नोंदवही',
  navAnalytics: 'विश्लेषण',
  navReportsAudit: 'अहवाल आणि ऑडिट',
  namasteGreeting: 'नमस्कार',
  homeVoicePrompt: 'टाइप न करता आवाजाद्वारे गृहभेट नोंदवण्यासाठी खाली टॅप करा.',
  startVoiceVisit: 'व्हॉइस भेट सुरू करा',
  assignedHouseholds: 'नेमलेली कुटुंबे',
  visitsToday: 'आजच्या भेटी',
  pendingFollowUps: 'प्रलंबित फॉलो-अप',
  vaccinesDue: 'प्रलंबित लसीकरण',
  beneficiaryDirectoryTitle: 'लाभार्थी यादी',
  followUpsTitle: 'फॉलो-अप आणि लसीकरण यादी',
  visitHistoryTitle: 'भेटींचा इतिहास',
  offlineDraftsTitle: 'ऑफलाइन मसुदे आणि सिंक',
  startRecording: 'रेकॉर्डिंग सुरू करा',
  stopRecording: 'थांबवा आणि प्रक्रिया करा',
  confirmAndSaveVisit: 'पुष्टी करा आणि जतन करा',
  urgentDangerSign: 'तातडीचे धोक्याचे लक्षण',
  call108Emergency: '१०८ रुग्णवाहिकेला कॉल करा',
  commandCenterTitle: 'PHC पर्यवेक्षक कमांड सेंटर',
};

const GU_UI: UiStrings = {
  ...EN_UI,
  appName: 'સાક્ષ્ય ASHA',
  ashaPortal: 'આશા પોર્ટલ',
  supervisorPortal: 'PHC સુપરવાઇઝર',
  signOut: 'લૉગ આઉટ',
  languageLabel: 'ભાષા',
  online: 'ઓનલાઇન',
  offline: 'ઓફલાઇન',
  navHome: 'હોમ',
  navVoiceVisit: 'વોઇસ વિઝિટ',
  navBeneficiaries: 'લાભાર્થીઓ',
  navFollowUps: 'ફોલો-અપ',
  navVisitHistory: 'મુલાકાત ઇતિહાસ',
  navOfflineDrafts: 'ઓફલાઇન ડ્રાફ્ટ',
  navPhcOverview: 'PHC ઝાંખી',
  navDangerAlerts: 'જોખમ એલર્ટ',
  navAshaWorkers: 'આશા વર્કર્સ',
  navVisitRegister: 'મુલાકાત રજિસ્ટર',
  navAnalytics: 'એનાલિટિક્સ',
  navReportsAudit: 'અહેવાલો અને ઓડિટ',
  namasteGreeting: 'નમસ્તે',
  homeVoicePrompt: 'ટાઇપ કર્યા વગર અવાજ દ્વારા ગૃહ મુલાકાત નોંધવા નીચે ટેપ કરો.',
  startVoiceVisit: 'વોઇસ વિઝિટ શરૂ કરો',
  assignedHouseholds: 'ફાળવેલ પરિવારો',
  visitsToday: 'આજની મુલાકાતો',
  pendingFollowUps: 'બાકી ફોલો-અપ',
  vaccinesDue: 'બાકી રસીઓ',
  beneficiaryDirectoryTitle: 'લાભાર્થી ડિરેક્ટરી',
  followUpsTitle: 'ફોલો-અપ અને રસીકરણ યાદી',
  visitHistoryTitle: 'મુલાકાત ઇતિહાસ',
  offlineDraftsTitle: 'ઓફલાઇન ડ્રાફ્ટ અને સિંક',
  startRecording: 'રેકોર્ડિંગ શરૂ કરો',
  stopRecording: 'રોકો અને પ્રોસેસ કરો',
  confirmAndSaveVisit: 'પુષ્ટિ કરો અને સાચવો',
  urgentDangerSign: 'તાત્કાલિક જોખમનું ચિહ્ન',
  call108Emergency: '૧૦૮ એમ્બ્યુલન્સ બોલાવો',
  commandCenterTitle: 'PHC સુપરવાઇઝર કમાન્ડ સેન્ટર',
};

const PA_UI: UiStrings = {
  ...EN_UI,
  appName: 'ਸਾਕਸ਼ਿਆ ASHA',
  ashaPortal: 'ਆਸ਼ਾ ਪੋਰਟਲ',
  supervisorPortal: 'PHC ਸੁਪਰਵਾਈਜ਼ਰ',
  signOut: 'ਲੌਗ ਆਊਟ',
  languageLabel: 'ਭਾਸ਼ਾ',
  online: 'ਔਨਲਾਈਨ',
  offline: 'ਔਫਲਾਈਨ',
  navHome: 'ਹੋਮ',
  navVoiceVisit: 'ਵਾਇਸ ਵਿਜ਼ਿਟ',
  navBeneficiaries: 'ਲਾਭਪਾਤਰੀ',
  navFollowUps: 'ਫਾਲੋ-ਅੱਪ',
  navVisitHistory: 'ਵਿਜ਼ਿਟ ਇਤਿਹਾਸ',
  navOfflineDrafts: 'ਔਫਲਾਈਨ ਡਰਾਫਟ',
  navPhcOverview: 'PHC ਸੰਖੇਪ',
  navDangerAlerts: 'ਖ਼ਤਰੇ ਦੇ ਅਲਰਟ',
  navAshaWorkers: 'ਆਸ਼ਾ ਵਰਕਰ',
  navVisitRegister: 'ਵਿਜ਼ਿਟ ਰਜਿਸਟਰ',
  navAnalytics: 'ਵਿਸ਼ਲੇਸ਼ਣ',
  navReportsAudit: 'ਰਿਪੋਰਟਾਂ ਅਤੇ ਆਡਿਟ',
  namasteGreeting: 'ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ',
  homeVoicePrompt: 'ਟਾਈਪ ਕੀਤੇ ਬਿਨਾਂ ਆਵਾਜ਼ ਰਾਹੀਂ ਘਰ ਦਾ ਦੌਰਾ ਦਰਜ ਕਰਨ ਲਈ ਹੇਠਾਂ ਦਬਾਓ।',
  startVoiceVisit: 'ਵਾਇਸ ਵਿਜ਼ਿਟ ਸ਼ੁਰੂ ਕਰੋ',
  assignedHouseholds: 'ਨਿਰਧਾਰਤ ਪਰਿਵਾਰ',
  visitsToday: 'ਅੱਜ ਦੇ ਦੌਰੇ',
  pendingFollowUps: 'ਬਕਾਇਆ ਫਾਲੋ-ਅੱਪ',
  vaccinesDue: 'ਬਕਾਇਆ ਟੀਕੇ',
  beneficiaryDirectoryTitle: 'ਲਾਭਪਾਤਰੀ ਸੂਚੀ',
  followUpsTitle: 'ਫਾਲੋ-ਅੱਪ ਅਤੇ ਟੀਕਾਕਰਨ ਸੂਚੀ',
  visitHistoryTitle: 'ਵਿਜ਼ਿਟ ਇਤਿਹਾਸ',
  offlineDraftsTitle: 'ਔਫਲਾਈਨ ਡਰਾਫਟ ਅਤੇ ਸਿੰਕ',
  startRecording: 'ਰਿਕਾਰਡਿੰਗ ਸ਼ੁਰੂ ਕਰੋ',
  stopRecording: 'ਰੋਕੋ ਅਤੇ ਪ੍ਰੋਸੈਸ ਕਰੋ',
  confirmAndSaveVisit: 'ਪੁਸ਼ਟੀ ਕਰੋ ਅਤੇ ਸੇਵ ਕਰੋ',
  urgentDangerSign: 'ਤੁਰੰਤ ਖ਼ਤਰੇ ਦਾ ਸੰਕੇਤ',
  call108Emergency: '੧੦੮ ਐਂਬੂਲੈਂਸ ਨੂੰ ਕਾਲ ਕਰੋ',
  commandCenterTitle: 'PHC ਸੁਪਰਵਾਈਜ਼ਰ ਕਮਾਂਡ ਸੈਂਟਰ',
};

export const UI_TRANSLATIONS: Record<string, UiStrings> = {
  'en-IN': EN_UI,
  'indic-auto': EN_UI,
  'hi-IN': HI_UI,
  'kn-IN': KN_UI,
  'ta-IN': TA_UI,
  'te-IN': TE_UI,
  'ml-IN': ML_UI,
  'bn-IN': BN_UI,
  'mr-IN': MR_UI,
  'gu-IN': GU_UI,
  'pa-IN': PA_UI,
};

export function getUiStrings(language: LanguageCode): UiStrings {
  return UI_TRANSLATIONS[language] || EN_UI;
}

