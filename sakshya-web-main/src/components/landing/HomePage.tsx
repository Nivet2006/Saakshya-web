'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence, type Variants } from 'framer-motion';
import {
  HeartPulse,
  Users,
  Stethoscope,
  ArrowRight,
  ShieldCheck,
  Globe,
  Lock,
  ChevronDown,
  AlertCircle,
  WifiOff,
} from 'lucide-react';
import { AmbientBackground } from '@/components/animations/AmbientBackground';
import { HealthWave } from '@/components/animations/HealthWave';
import { SYNTHETIC_PROFILES } from '@/lib/mock-data';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import { isRealSupabaseConfigured, supabase } from '@/lib/supabase/client';
import { PRISMA_LANGUAGES } from '@/lib/translations';
import type { LanguageCode, UserProfile } from '@/types';

interface HomePageProps {
  selectedLanguage: LanguageCode;
  onLanguageChange: (lang: LanguageCode) => void;
  onAuthenticated: (profile: UserProfile) => void;
}

/* ── Custom Animated ASHA Community SVG Illustration ── */
function AshaCommunityIllustration() {
  return (
    <svg
      viewBox="0 0 340 380"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className="w-full max-w-[340px] drop-shadow-md select-none"
    >
      {/* Ambient background circles */}
      <circle cx="170" cy="200" r="140" fill="rgba(13,148,136,0.06)" />
      <circle cx="170" cy="200" r="105" fill="rgba(13,148,136,0.05)" />

      {/* Community connection nodes (pulsing) */}
      <motion.circle
        animate={{ opacity: [0.3, 0.9, 0.3], scale: [0.9, 1.2, 0.9] }}
        transition={{ duration: 3, repeat: Infinity }}
        cx="80"
        cy="100"
        r="10"
        fill="#0D9488"
        opacity="0.5"
      />
      <motion.circle
        animate={{ opacity: [0.25, 0.85, 0.25], scale: [0.9, 1.25, 0.9] }}
        transition={{ duration: 4, repeat: Infinity, delay: 0.5 }}
        cx="270"
        cy="120"
        r="8"
        fill="#047857"
        opacity="0.4"
      />
      <motion.circle
        animate={{ opacity: [0.4, 1, 0.4], scale: [0.9, 1.15, 0.9] }}
        transition={{ duration: 3.5, repeat: Infinity, delay: 1 }}
        cx="60"
        cy="270"
        r="12"
        fill="#0D9488"
        opacity="0.35"
      />
      <motion.circle
        animate={{ opacity: [0.3, 0.9, 0.3], scale: [0.85, 1.2, 0.85] }}
        transition={{ duration: 5, repeat: Infinity, delay: 0.3 }}
        cx="290"
        cy="280"
        r="9"
        fill="#059669"
        opacity="0.4"
      />

      {/* Connection lines from ASHA worker to community households */}
      <motion.line
        animate={{ opacity: [0.15, 0.5, 0.15] }}
        transition={{ duration: 4, repeat: Infinity }}
        x1="150"
        y1="165"
        x2="80"
        y2="100"
        stroke="#0D9488"
        strokeWidth="1.5"
        strokeDasharray="4 4"
      />
      <motion.line
        animate={{ opacity: [0.12, 0.45, 0.12] }}
        transition={{ duration: 4, repeat: Infinity, delay: 1 }}
        x1="190"
        y1="165"
        x2="270"
        y2="120"
        stroke="#0D9488"
        strokeWidth="1.5"
        strokeDasharray="4 4"
      />
      <motion.line
        animate={{ opacity: [0.12, 0.4, 0.12] }}
        transition={{ duration: 5, repeat: Infinity, delay: 0.5 }}
        x1="150"
        y1="210"
        x2="60"
        y2="270"
        stroke="#0D9488"
        strokeWidth="1.5"
        strokeDasharray="4 4"
      />
      <motion.line
        animate={{ opacity: [0.12, 0.4, 0.12] }}
        transition={{ duration: 4, repeat: Infinity, delay: 1.5 }}
        x1="195"
        y1="210"
        x2="290"
        y2="280"
        stroke="#0D9488"
        strokeWidth="1.5"
        strokeDasharray="4 4"
      />

      {/* ASHA Worker Character */}
      <motion.g
        animate={{ y: [0, -7, 0] }}
        transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
      >
        {/* Torso / Kurta */}
        <rect x="130" y="185" width="80" height="95" rx="18" fill="#0D9488" />
        {/* Collar detail */}
        <path d="M165,185 L170,200 L175,185" stroke="rgba(255,255,255,0.4)" strokeWidth="1.5" fill="none" />
        {/* Arms */}
        <rect x="100" y="190" width="34" height="18" rx="9" fill="#0D9488" />
        <rect x="206" y="190" width="34" height="18" rx="9" fill="#0D9488" />
        {/* Hands */}
        <circle cx="100" cy="199" r="10" fill="#E8B298" />
        <circle cx="240" cy="199" r="10" fill="#E8B298" />

        {/* Tablet / Field Register Device in hand */}
        <rect x="224" y="185" width="32" height="50" rx="5" fill="#1E293B" />
        <rect x="227" y="189" width="26" height="38" rx="3" fill="#F0FDF4" />
        {/* Screen health waveform */}
        <polyline
          points="230,215 235,208 240,218 245,203 250,210"
          stroke="#0D9488"
          strokeWidth="1.5"
          fill="none"
          strokeLinecap="round"
        />
        <circle cx="250" cy="210" r="2" fill="#E11D48" />

        {/* Head & Hair */}
        <circle cx="170" cy="165" r="32" fill="#E8B298" />
        <path
          d="M140,158 Q145,135 170,133 Q195,133 200,158 Q195,145 170,143 Q145,145 140,158Z"
          fill="#291D17"
        />
        {/* Dupatta drape */}
        <path d="M138,173 Q130,160 125,155 Q135,158 142,165" fill="#0F766E" opacity="0.8" />
        {/* Eyes & Smile */}
        <circle cx="160" cy="168" r="3" fill="#291D17" />
        <circle cx="180" cy="168" r="3" fill="#291D17" />
        <path d="M162,178 Q170,184 178,178" stroke="#291D17" strokeWidth="1.5" fill="none" strokeLinecap="round" />

        {/* Official ASHA badge */}
        <rect x="148" y="210" width="44" height="20" rx="4" fill="rgba(255,255,255,0.25)" />
        <text x="170" y="224" textAnchor="middle" fontSize="8" fill="white" fontFamily="sans-serif" fontWeight="700">
          ASHA
        </text>
      </motion.g>

      {/* Floating healthcare cross */}
      <motion.g
        animate={{ y: [0, -10, 0], rotate: [0, 4, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut', delay: 0.8 }}
        style={{ transformOrigin: '85px 60px' }}
      >
        <rect x="79" y="50" width="12" height="32" rx="3" fill="#0D9488" opacity="0.8" />
        <rect x="70" y="59" width="30" height="12" rx="3" fill="#0D9488" opacity="0.8" />
      </motion.g>

      {/* Floating green leaf */}
      <motion.g
        animate={{ y: [0, -9, 0], rotate: [0, -5, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 1.5 }}
        style={{ transformOrigin: '280px 75px' }}
      >
        <path d="M270,75 Q280,55 295,65 Q285,80 270,75Z" fill="#10B981" opacity="0.6" />
        <line x1="270" y1="75" x2="290" y2="62" stroke="#10B981" strokeWidth="1" opacity="0.4" />
      </motion.g>

      {/* Health vitals wave below character */}
      <g transform="translate(40,315)">
        <HealthWave width={260} height={40} color="#0D9488" opacity={0.35} />
      </g>
    </svg>
  );
}

const pageVariants: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.05 } },
};

const itemUp = (delay = 0): Variants => ({
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: 'easeOut', delay } },
});

export const HomePage: React.FC<HomePageProps> = ({
  selectedLanguage,
  onLanguageChange,
  onAuthenticated,
}) => {
  const { ui } = useTranslation(selectedLanguage);
  const [showStaffLogin, setShowStaffLogin] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Map the 3 canonical roles from synthetic fixtures:
  const ashaProfile = SYNTHETIC_PROFILES[0]; // Sunita Verma (ASHA)
  const anmProfile = SYNTHETIC_PROFILES[1]; // Padma Murthy (ANM/Worker)
  const doctorProfile = SYNTHETIC_PROFILES[3] || SYNTHETIC_PROFILES[SYNTHETIC_PROFILES.length - 1]; // Dr. Sunita Rao (MOIC/Doctor)

  const handleRoleSelect = (profile: UserProfile, roleOverride?: 'ASHA_WORKER' | 'PHC_SUPERVISOR') => {
    onAuthenticated({
      ...profile,
      role: roleOverride || profile.role,
      preferred_language: selectedLanguage,
    });
  };

  const handleSupabaseLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);

    if (!email.trim() || !password) {
      setAuthError('Please enter your email and password.');
      return;
    }

    if (!supabase || !isRealSupabaseConfigured) {
      setAuthError(
        'Supabase Auth is not configured in .env.local. Choose one of the role entry buttons above to enter directly.'
      );
      return;
    }

    setIsLoading(true);
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password,
      });
      if (error || !data.user) {
        throw new Error(error?.message || 'Invalid credentials.');
      }

      const { data: dbProfile } = await supabase
        .from('profiles')
        .select('*')
        .eq('auth_user_id', data.user.id)
        .maybeSingle();

      const resolved: UserProfile = dbProfile
        ? {
            id: dbProfile.id,
            auth_user_id: data.user.id,
            worker_code: dbProfile.role === 'PHC_SUPERVISOR' ? 'SUP-PHC-01' : 'ASHA-DEMO-01',
            role: dbProfile.role,
            full_name: dbProfile.full_name,
            phone_number: dbProfile.phone_number,
            phc_id: dbProfile.phc_id,
            assigned_area: dbProfile.assigned_area,
            preferred_language: dbProfile.preferred_language || selectedLanguage,
            is_active: dbProfile.is_active,
          }
        : {
            ...ashaProfile,
            auth_user_id: data.user.id,
            full_name: data.user.email || 'Authenticated User',
            preferred_language: selectedLanguage,
          };

      onAuthenticated(resolved);
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : 'Sign-in failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative bg-slate-50 text-slate-800 flex flex-col justify-between overflow-x-hidden selection:bg-teal-500 selection:text-white">
      {/* Living organic ambient particle background */}
      <AmbientBackground intensity={0.9} />

      {/* Top Navbar */}
      <header className="relative z-10 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-5 pb-3 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-600 to-emerald-700 text-white flex items-center justify-center shadow-md shadow-teal-700/20">
            <HeartPulse className="h-6 w-6" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-lg tracking-tight text-slate-900">Sakshya</span>
            </div>
            <p className="text-xs text-slate-500 font-medium hidden sm:block">
              Voice field register
            </p>
          </div>
        </div>

        {/* Language Quick Dropdown */}
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="relative">
            <Globe className="h-4 w-4 text-teal-600 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <select
              aria-label="App Language"
              value={selectedLanguage}
              onChange={(e) => onLanguageChange(e.target.value as LanguageCode)}
              className="pl-9 pr-7 py-1.5 text-xs font-semibold rounded-lg border border-slate-200 bg-white/90 backdrop-blur-sm text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-teal-500 appearance-none cursor-pointer"
            >
              {PRISMA_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.nativeName} ({l.name})
                </option>
              ))}
              <option value="indic-auto">Auto-Detect Indic</option>
            </select>
            <ChevronDown className="h-3 w-3 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>
        </div>
      </header>

      {/* Main Hero & Three-Role Entry Flow */}
      <main className="relative z-10 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-10 my-auto">
        <motion.div
          variants={pageVariants}
          initial="hidden"
          animate="show"
          className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center"
        >
          {/* Left Column: Heading, Wave & Role Cards */}
          <div className="lg:col-span-7 flex flex-col justify-center">
            {/* Main Headline */}
            <motion.h1
              variants={itemUp(0.1)}
              className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-900 tracking-tight leading-[1.15]"
            >
              Zero missed visits.{' '}
              <span className="bg-gradient-to-r from-teal-700 to-emerald-600 bg-clip-text text-transparent">
                Safer rural healthcare.
              </span>
            </motion.h1>

            <motion.p
              variants={itemUp(0.15)}
              className="mt-3 text-base sm:text-lg text-slate-600 max-w-2xl leading-relaxed"
            >
              Record patient visits with natural voice in 10 Indic languages. Capture health vitals, detect clinical danger signs instantly, and sync automatically when network returns.
            </motion.p>

            {/* Signature Health Waveform */}
            <motion.div variants={itemUp(0.18)} className="my-5 opacity-90">
              <HealthWave width={320} height={42} color="#0D9488" opacity={0.5} />
            </motion.div>

            {/* ── Interactive Three-Role Cards ── */}
            <motion.div variants={itemUp(0.22)} className="space-y-3.5 max-w-xl">
              <p className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5 mb-1">
                <ShieldCheck className="h-4 w-4 text-teal-600" />
                Select Role to Enter Portal
              </p>

              {/* Role 1: ASHA Worker */}
              <motion.button
                whileHover={{ y: -3, scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
                type="button"
                onClick={() => handleRoleSelect(ashaProfile, 'ASHA_WORKER')}
                className="w-full text-left p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-teal-700 to-emerald-700 text-white shadow-lg shadow-teal-900/20 border border-teal-600/40 transition-all flex items-center justify-between group cursor-pointer"
              >
                <div className="flex items-center gap-4 min-w-0">
                  <div className="w-12 h-12 rounded-xl bg-white/20 backdrop-blur-md flex items-center justify-center shrink-0 border border-white/25 shadow-inner">
                    <HeartPulse className="h-6 w-6 text-white" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h2 className="text-base sm:text-lg font-bold text-white">ASHA Worker</h2>
                      <span className="text-[10px] font-bold bg-white/20 text-white px-2 py-0.5 rounded-full uppercase tracking-wide">
                        Field Mode
                      </span>
                    </div>
                    <p className="text-xs sm:text-sm text-teal-50/90 mt-0.5 font-medium truncate">
                      Record voice visits, offline maternal/child register &amp; danger alerts
                    </p>
                  </div>
                </div>
                <div className="w-8 h-8 rounded-full bg-white/15 flex items-center justify-center shrink-0 group-hover:bg-white/25 transition-colors ml-2">
                  <ArrowRight className="h-4 w-4 text-white" />
                </div>
              </motion.button>

              {/* Role 2: ANM Supervisor */}
              <motion.button
                whileHover={{ y: -3, scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
                type="button"
                onClick={() => handleRoleSelect(anmProfile, 'PHC_SUPERVISOR')}
                className="w-full text-left p-4 sm:p-5 rounded-2xl bg-white hover:bg-slate-50/90 text-slate-800 shadow-sm border border-slate-200/90 hover:border-slate-300 transition-all flex items-center justify-between group cursor-pointer"
              >
                <div className="flex items-center gap-4 min-w-0">
                  <div className="w-12 h-12 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center shrink-0 border border-teal-100 shadow-xs">
                    <Users className="h-6 w-6" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h2 className="text-base sm:text-lg font-bold text-slate-900">ANM Supervisor</h2>
                      <span className="text-[10px] font-bold bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full uppercase tracking-wide">
                        Sector Review
                      </span>
                    </div>
                    <p className="text-xs sm:text-sm text-slate-500 mt-0.5 truncate">
                      Supervise worker visits, monitor follow-ups &amp; verified high-risk cases
                    </p>
                  </div>
                </div>
                <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center shrink-0 group-hover:bg-teal-50 group-hover:text-teal-700 transition-colors ml-2">
                  <ArrowRight className="h-4 w-4 text-slate-500 group-hover:text-teal-700" />
                </div>
              </motion.button>

              {/* Role 3: PHC Doctor / MOIC */}
              <motion.button
                whileHover={{ y: -3, scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
                type="button"
                onClick={() => handleRoleSelect(doctorProfile, 'PHC_SUPERVISOR')}
                className="w-full text-left p-4 sm:p-5 rounded-2xl bg-white hover:bg-slate-50/90 text-slate-800 shadow-sm border border-slate-200/90 hover:border-slate-300 transition-all flex items-center justify-between group cursor-pointer"
              >
                <div className="flex items-center gap-4 min-w-0">
                  <div className="w-12 h-12 rounded-xl bg-rose-50 text-rose-700 flex items-center justify-center shrink-0 border border-rose-100 shadow-xs">
                    <Stethoscope className="h-6 w-6" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h2 className="text-base sm:text-lg font-bold text-slate-900">PHC Doctor / MOIC</h2>
                      <span className="text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200 px-2 py-0.5 rounded-full uppercase tracking-wide">
                        Command Center
                      </span>
                    </div>
                    <p className="text-xs sm:text-sm text-slate-500 mt-0.5 truncate">
                      Urgent danger sign triage, hospital emergency referrals &amp; clinical overview
                    </p>
                  </div>
                </div>
                <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center shrink-0 group-hover:bg-rose-50 group-hover:text-rose-700 transition-colors ml-2">
                  <ArrowRight className="h-4 w-4 text-slate-500 group-hover:text-rose-700" />
                </div>
              </motion.button>
            </motion.div>

            {/* Trust and Feature Badges */}
            <motion.div
              variants={itemUp(0.28)}
              className="mt-6 flex flex-wrap items-center gap-4 text-xs font-semibold text-slate-500"
            >
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>Works 100% Offline</span>
              </div>
              <span>•</span>
              <div className="flex items-center gap-1.5">
                <WifiOff className="w-3.5 h-3.5 text-slate-400" />
                <span>Zero Data Loss Auto-Sync</span>
              </div>
              <span>•</span>
              <div className="flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
                <span>NHM Official Guidelines Grounded</span>
              </div>
            </motion.div>
          </div>

          {/* Right Column: Custom Animated SVG Illustration + Optional Staff Sign-In */}
          <div className="lg:col-span-5 flex flex-col items-center justify-center relative">
            <motion.div
              initial={{ opacity: 0, scale: 0.92 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              className="relative flex items-center justify-center w-full py-4"
            >
              {/* Soft glowing ambient circle behind the illustration */}
              <motion.div
                animate={{ scale: [1, 1.07, 1], opacity: [0.6, 0.9, 0.6] }}
                transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
                className="absolute w-[80%] h-[80%] rounded-full bg-teal-500/10 blur-2xl pointer-events-none"
              />
              <AshaCommunityIllustration />
            </motion.div>

            {/* Secondary Staff Sign-In Toggle */}
            <div className="w-full max-w-sm mt-3">
              <button
                type="button"
                onClick={() => setShowStaffLogin(!showStaffLogin)}
                className="w-full py-2.5 px-4 rounded-xl text-xs font-bold text-slate-600 hover:text-slate-900 bg-white/70 hover:bg-white border border-slate-200/80 transition-all flex items-center justify-center gap-2 shadow-xs cursor-pointer"
              >
                <Lock className="w-3.5 h-3.5 text-slate-500" />
                <span>Staff Sign-in with Email &amp; Password</span>
                <ChevronDown
                  className={`w-3.5 h-3.5 text-slate-400 transition-transform ${showStaffLogin ? 'rotate-180' : ''}`}
                />
              </button>

              <AnimatePresence>
                {showStaffLogin && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.25 }}
                    className="overflow-hidden mt-3"
                  >
                    <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-md">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-xs font-bold text-slate-800">Supabase Staff Login</span>
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                            isRealSupabaseConfigured
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : 'bg-slate-100 text-slate-600 border border-slate-200'
                          }`}
                        >
                          {isRealSupabaseConfigured ? 'Supabase Connected' : 'Local Mock'}
                        </span>
                      </div>

                      {authError && (
                        <div className="mb-3 p-2.5 rounded-lg bg-red-50 border border-red-200 text-xs text-red-800 flex items-start gap-1.5">
                          <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                          <span>{authError}</span>
                        </div>
                      )}

                      <form onSubmit={handleSupabaseLogin} className="space-y-3">
                        <div>
                          <label className="block text-[11px] font-bold text-slate-600 mb-1">Email</label>
                          <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="asha@nhm.gov.in"
                            className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500"
                          />
                        </div>
                        <div>
                          <label className="block text-[11px] font-bold text-slate-600 mb-1">Password</label>
                          <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••"
                            className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500"
                          />
                        </div>
                        <button
                          type="submit"
                          disabled={isLoading}
                          className="w-full py-2 px-3 rounded-lg text-xs font-bold bg-teal-600 hover:bg-teal-700 text-white transition-colors flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
                        >
                          {isLoading ? 'Signing in...' : 'Sign In'}
                        </button>
                      </form>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 text-center text-xs text-slate-400">
        Sakshya · National Health Mission (NHM) Rural Tele-Health System · All demonstration fixtures BEN-1042–BEN-1048 are synthetic.
      </footer>
    </div>
  );
};
