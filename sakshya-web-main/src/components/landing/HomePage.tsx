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
  Database,
} from 'lucide-react';
import { AmbientBackground } from '@/components/animations/AmbientBackground';
import { HealthWave } from '@/components/animations/HealthWave';
import { SYNTHETIC_PROFILES } from '@/lib/mock-data';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import { isRealSupabaseConfigured, supabase } from '@/lib/supabase/client';
import { auth, isFirebaseConfigured } from '@/lib/firebase/client';
import { signInWithEmailAndPassword } from 'firebase/auth';
import { PRISMA_LANGUAGES } from '@/lib/translations';
import type { LanguageCode, UserProfile } from '@/types';

interface HomePageProps {
  selectedLanguage: LanguageCode;
  onLanguageChange: (lang: LanguageCode) => void;
  onAuthenticated: (profile: UserProfile) => void;
}

/* ── Custom Animated Medical-Tech Field Register Illustration ── */
function AshaCommunityIllustration() {
  return (
    <svg
      viewBox="0 0 420 440"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className="w-full max-w-[420px] drop-shadow-xl select-none"
    >
      <defs>
        {/* Gradients */}
        <linearGradient id="tabletBezel" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#1E293B" />
          <stop offset="100%" stopColor="#0F172A" />
        </linearGradient>
        <linearGradient id="tabletScreen" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#FFFFFF" />
          <stop offset="100%" stopColor="#F8FAFC" />
        </linearGradient>
        <linearGradient id="tealGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#0D9488" />
          <stop offset="100%" stopColor="#059669" />
        </linearGradient>
        <linearGradient id="emeraldGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#10B981" />
          <stop offset="100%" stopColor="#047857" />
        </linearGradient>
        <linearGradient id="roseGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#F43F5E" />
          <stop offset="100%" stopColor="#E11D48" />
        </linearGradient>
        <linearGradient id="hudCardGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#F0FDFA" />
          <stop offset="100%" stopColor="#E6FFFA" />
        </linearGradient>
        <filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="8" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
        <filter id="cardShadow" x="-15%" y="-15%" width="130%" height="130%">
          <feDropShadow dx="0" dy="4" stdDeviation="6" floodColor="#0F172A" floodOpacity="0.08" />
        </filter>
      </defs>

      {/* ── 1. Ambient Background Sonar / Radar Rings ── */}
      <motion.circle
        cx="210"
        cy="220"
        r="170"
        fill="rgba(13,148,136,0.03)"
        stroke="rgba(13,148,136,0.08)"
        strokeWidth="1.5"
        strokeDasharray="6 6"
        animate={{ rotate: 360 }}
        transition={{ duration: 60, repeat: Infinity, ease: 'linear' }}
        style={{ transformOrigin: '210px 220px' }}
      />
      <motion.circle
        cx="210"
        cy="220"
        r="135"
        fill="rgba(13,148,136,0.03)"
        stroke="rgba(13,148,136,0.12)"
        strokeWidth="1"
        animate={{ scale: [0.97, 1.03, 0.97] }}
        transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
        style={{ transformOrigin: '210px 220px' }}
      />

      {/* ── 2. Telemetry Connection Lines & Pulsing Data Photons ── */}
      {/* Node 1: Top-Left (Mother & Child) -> Device */}
      <line x1="75" y1="85" x2="160" y2="150" stroke="#0D9488" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.4" />
      <motion.circle
        r="3.5"
        fill="#0D9488"
        animate={{ cx: [75, 160], cy: [85, 150], opacity: [0, 1, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
      />

      {/* Node 2: Top-Right (PHC Hospital) -> Device */}
      <line x1="345" y1="85" x2="260" y2="150" stroke="#0D9488" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.4" />
      <motion.circle
        r="3.5"
        fill="#10B981"
        animate={{ cx: [345, 260], cy: [85, 150], opacity: [0, 1, 0] }}
        transition={{ duration: 3.2, repeat: Infinity, ease: 'easeInOut', delay: 0.6 }}
      />

      {/* Node 3: Bottom-Left (10 Indic Dialects) -> Device */}
      <line x1="75" y1="355" x2="160" y2="290" stroke="#0D9488" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.4" />
      <motion.circle
        r="3.5"
        fill="#0D9488"
        animate={{ cx: [75, 160], cy: [355, 290], opacity: [0, 1, 0] }}
        transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut', delay: 1.2 }}
      />

      {/* Node 4: Bottom-Right (Zero Data Loss DB) -> Device */}
      <line x1="345" y1="355" x2="260" y2="290" stroke="#0D9488" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.4" />
      <motion.circle
        r="3.5"
        fill="#10B981"
        animate={{ cx: [345, 260], cy: [355, 290], opacity: [0, 1, 0] }}
        transition={{ duration: 3.8, repeat: Infinity, ease: 'easeInOut', delay: 1.8 }}
      />

      {/* ── 3. Central Smart Voice Field Register Device (Floating) ── */}
      <motion.g
        animate={{ y: [0, -7, 0] }}
        transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
        style={{ transformOrigin: '210px 220px' }}
      >
        {/* Device Outer Frame (Dark Slate Bezel) */}
        <rect
          x="110"
          y="85"
          width="200"
          height="270"
          rx="24"
          fill="url(#tabletBezel)"
          stroke="#334155"
          strokeWidth="2"
          filter="url(#cardShadow)"
        />

        {/* Top Speaker Ear-piece slit & camera */}
        <rect x="185" y="94" width="50" height="3" rx="1.5" fill="#475569" />
        <circle cx="170" cy="95.5" r="2.5" fill="#0D9488" opacity="0.8" />

        {/* Screen Bezel Inset */}
        <rect x="118" y="104" width="184" height="240" rx="16" fill="url(#tabletScreen)" />

        {/* Screen Status Bar */}
        <g transform="translate(126, 114)">
          {/* Signal / Battery / Status */}
          <circle cx="4" cy="4" r="3" fill="#10B981" />
          <text x="12" y="7" fontSize="7" fontWeight="700" fill="#0F172A" fontFamily="sans-serif">
            Sakshya Register
          </text>

          {/* Local DB Pill */}
          <rect x="116" y="-1" width="52" height="11" rx="4" fill="#ECFDF5" stroke="#A7F3D0" strokeWidth="0.8" />
          <circle cx="121" cy="4.5" r="2" fill="#059669" />
          <text x="126" y="7" fontSize="5.5" fontWeight="700" fill="#047857" fontFamily="sans-serif">
            LOCAL DB
          </text>
        </g>

        {/* ── Voice Capture HUD Box ── */}
        <g transform="translate(126, 128)">
          <rect
            x="0"
            y="0"
            width="168"
            height="58"
            rx="10"
            fill="url(#hudCardGrad)"
            stroke="#99F6E4"
            strokeWidth="1"
          />

          {/* Concentric Mic Sound Radar Waves */}
          <motion.circle
            cx="24"
            cy="29"
            r="18"
            fill="none"
            stroke="#0D9488"
            strokeWidth="1"
            animate={{ scale: [0.85, 1.25, 0.85], opacity: [0.6, 0.1, 0.6] }}
            transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
            style={{ transformOrigin: '24px 29px' }}
          />
          <motion.circle
            cx="24"
            cy="29"
            r="13"
            fill="none"
            stroke="#0D9488"
            strokeWidth="1"
            animate={{ scale: [0.9, 1.15, 0.9], opacity: [0.7, 0.2, 0.7] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
            style={{ transformOrigin: '24px 29px' }}
          />

          {/* Mic Button Circle */}
          <circle cx="24" cy="29" r="10" fill="url(#tealGrad)" />
          {/* Mic Icon Vector */}
          <rect x="22.5" y="25" width="3" height="5.5" rx="1.5" fill="#FFFFFF" />
          <path d="M21 27.5 C21 30 27 30 27 27.5" stroke="#FFFFFF" strokeWidth="0.9" fill="none" strokeLinecap="round" />
          <line x1="24" y1="30" x2="24" y2="32.5" stroke="#FFFFFF" strokeWidth="0.9" />

          {/* Live Listening Text */}
          <text x="44" y="19" fontSize="7" fontWeight="700" fill="#0F766E" fontFamily="sans-serif">
            Listening (10 Indic Dialects)
          </text>

          {/* Speech Equalizer Bars (Live Decibel Pulse) */}
          <g transform="translate(44, 25)">
            {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map((i) => {
              const baseHeight = [7, 12, 17, 10, 15, 19, 13, 20, 14, 9, 15, 8][i];
              return (
                <motion.rect
                  key={i}
                  x={i * 9.5}
                  y={12 - baseHeight / 2}
                  width="3.5"
                  height={baseHeight}
                  rx="1.75"
                  fill="#0D9488"
                  animate={{
                    height: [baseHeight * 0.5, baseHeight * 1.25, baseHeight * 0.5],
                    y: [12 - (baseHeight * 0.5) / 2, 12 - (baseHeight * 1.25) / 2, 12 - (baseHeight * 0.5) / 2],
                    opacity: [0.6, 1, 0.6],
                  }}
                  transition={{
                    duration: 1.2 + (i % 3) * 0.3,
                    repeat: Infinity,
                    delay: i * 0.08,
                    ease: 'easeInOut',
                  }}
                />
              );
            })}
          </g>

          <text x="44" y="49" fontSize="6" fill="#0D9488" opacity="0.9" fontFamily="sans-serif" fontStyle="italic">
            &quot;वजन ५४ किलो, कोई खतरे का लक्षण नहीं&quot;
          </text>
        </g>

        {/* ── Extracted Visit Structured Record Card ── */}
        <g transform="translate(126, 194)">
          <rect
            x="0"
            y="0"
            width="168"
            height="90"
            rx="10"
            fill="#FFFFFF"
            stroke="#E2E8F0"
            strokeWidth="1"
            filter="url(#cardShadow)"
          />

          {/* Patient Header */}
          <text x="10" y="15" fontSize="7.5" fontWeight="700" fill="#0F172A" fontFamily="sans-serif">
            Lakshmi Devi · BEN-1042
          </text>
          <rect x="114" y="7" width="44" height="10" rx="3" fill="#F1F5F9" />
          <text x="136" y="14.5" textAnchor="middle" fontSize="5.5" fontWeight="700" fill="#475569" fontFamily="sans-serif">
            ANC VISIT
          </text>

          {/* Vitals Pills Row */}
          <g transform="translate(10, 23)">
            {/* Weight Pill */}
            <rect x="0" y="0" width="46" height="15" rx="4" fill="#F8FAFC" stroke="#E2E8F0" strokeWidth="0.8" />
            <text x="5" y="10.5" fontSize="5.5" fontWeight="600" fill="#64748B" fontFamily="sans-serif">
              Weight: <tspan fontWeight="700" fill="#0F172A">54.0 kg</tspan>
            </text>

            {/* BP Pill */}
            <rect x="50" y="0" width="46" height="15" rx="4" fill="#F8FAFC" stroke="#E2E8F0" strokeWidth="0.8" />
            <text x="55" y="10.5" fontSize="5.5" fontWeight="600" fill="#64748B" fontFamily="sans-serif">
              BP: <tspan fontWeight="700" fill="#0F172A">118/76</tspan>
            </text>

            {/* Next Visit */}
            <rect x="100" y="0" width="48" height="15" rx="4" fill="#F8FAFC" stroke="#E2E8F0" strokeWidth="0.8" />
            <text x="104" y="10.5" fontSize="5.5" fontWeight="600" fill="#64748B" fontFamily="sans-serif">
              Due: <tspan fontWeight="700" fill="#0F172A">05 Dec</tspan>
            </text>
          </g>

          {/* Deterministic Clinical Risk Assessment Banner */}
          <g transform="translate(10, 45)">
            <rect x="0" y="0" width="148" height="17" rx="5" fill="#DCFCE7" stroke="#86EFAC" strokeWidth="0.8" />
            {/* Shield Checkmark icon */}
            <path
              d="M10 4.5 L14 6.5 L14 10.5 C14 13 10 14.5 10 14.5 C10 14.5 6 13 6 10.5 L6 6.5 Z"
              fill="#16A34A"
            />
            <path d="M8.5 9 L9.5 10 L12 7.5" stroke="#FFFFFF" strokeWidth="0.8" fill="none" />
            <text x="18" y="11.5" fontSize="6" fontWeight="700" fill="#15803D" fontFamily="sans-serif">
              Risk Model: NORMAL · No Danger Signs
            </text>
          </g>

          {/* Action Row: Read-Back & Confirm */}
          <g transform="translate(10, 68)">
            <rect x="0" y="0" width="148" height="15" rx="4" fill="url(#tealGrad)" />
            <text x="74" y="10" textAnchor="middle" fontSize="6.5" fontWeight="700" fill="#FFFFFF" fontFamily="sans-serif">
              ✓ Voice Verified · Ready to Sync
            </text>
          </g>
        </g>

        {/* Bottom Hardware Home Indicator */}
        <rect x="175" y="347" width="70" height="2.5" rx="1.25" fill="#334155" />
      </motion.g>

      {/* ── 4. Floating Satellite Nodes ── */}

      {/* Node 1: Top-Left (Mother & Child / ANC-PNC) */}
      <motion.g
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 4.5, repeat: Infinity, ease: 'easeInOut', delay: 0.3 }}
      >
        <g transform="translate(28, 45)">
          <rect
            x="0"
            y="0"
            width="90"
            height="62"
            rx="12"
            fill="#FFFFFF"
            stroke="#99F6E4"
            strokeWidth="1.2"
            filter="url(#cardShadow)"
          />
          <circle cx="20" cy="22" r="12" fill="#CCFBF1" />
          {/* Heart / Mother icon */}
          <path
            d="M20 26 C16 23 14 20 14 18 C14 16.3 15.3 15 17 15 C18 15 19.2 15.7 20 16.7 C20.8 15.7 22 15 23 15 C24.7 15 26 16.3 26 18 C26 20 24 23 20 26 Z"
            fill="#0D9488"
          />
          <text x="36" y="19" fontSize="6.5" fontWeight="700" fill="#0F172A" fontFamily="sans-serif">
            Maternal Care
          </text>
          <text x="36" y="27" fontSize="5.5" fontWeight="600" fill="#0D9488" fontFamily="sans-serif">
            ANC · PNC · HBNC
          </text>
          <rect x="8" y="38" width="74" height="16" rx="4" fill="#F0FDFA" />
          <text x="45" y="49" textAnchor="middle" fontSize="5.5" fontWeight="600" fill="#047857" fontFamily="sans-serif">
            Zero Missed Visits
          </text>
        </g>
      </motion.g>

      {/* Node 2: Top-Right (PHC Hospital & Emergency Referral) */}
      <motion.g
        animate={{ y: [0, -9, 0] }}
        transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut', delay: 0.9 }}
      >
        <g transform="translate(302, 45)">
          <rect
            x="0"
            y="0"
            width="90"
            height="62"
            rx="12"
            fill="#FFFFFF"
            stroke="#FECDD3"
            strokeWidth="1.2"
            filter="url(#cardShadow)"
          />
          <circle cx="20" cy="22" r="12" fill="#FFE4E6" />
          {/* Medical Cross Icon */}
          <rect x="18" y="16" width="4" height="12" rx="1.5" fill="#E11D48" />
          <rect x="14" y="20" width="12" height="4" rx="1.5" fill="#E11D48" />

          <text x="36" y="19" fontSize="6.5" fontWeight="700" fill="#0F172A" fontFamily="sans-serif">
            PHC Referral
          </text>
          <text x="36" y="27" fontSize="5.5" fontWeight="600" fill="#E11D48" fontFamily="sans-serif">
            Instant Triage
          </text>
          <rect x="8" y="38" width="74" height="16" rx="4" fill="#FFF1F2" />
          <text x="45" y="49" textAnchor="middle" fontSize="5.5" fontWeight="600" fill="#BE123C" fontFamily="sans-serif">
            108 SOS Protocol
          </text>
        </g>
      </motion.g>

      {/* Node 3: Bottom-Left (10 Indic Dialects Voice AI) */}
      <motion.g
        animate={{ y: [0, -7, 0] }}
        transition={{ duration: 4.8, repeat: Infinity, ease: 'easeInOut', delay: 1.4 }}
      >
        <g transform="translate(24, 325)">
          <rect
            x="0"
            y="0"
            width="96"
            height="58"
            rx="12"
            fill="#FFFFFF"
            stroke="#E2E8F0"
            strokeWidth="1.2"
            filter="url(#cardShadow)"
          />
          <text x="10" y="16" fontSize="7" fontWeight="700" fill="#0F172A" fontFamily="sans-serif">
            10 Indic Dialects
          </text>
          <text x="10" y="27" fontSize="6" fontWeight="600" fill="#0D9488" fontFamily="sans-serif">
            हिन्दी · தமிழ் · ಕನ್ನಡ · తెలుగు
          </text>
          <rect x="8" y="35" width="80" height="15" rx="4" fill="#F8FAFC" />
          <text x="48" y="45.5" textAnchor="middle" fontSize="5.5" fontWeight="700" fill="#475569" fontFamily="sans-serif">
            Natural Code-Mixing
          </text>
        </g>
      </motion.g>

      {/* Node 4: Bottom-Right (Offline-First Local DB) */}
      <motion.g
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 5.2, repeat: Infinity, ease: 'easeInOut', delay: 1.8 }}
      >
        <g transform="translate(300, 325)">
          <rect
            x="0"
            y="0"
            width="96"
            height="58"
            rx="12"
            fill="#FFFFFF"
            stroke="#A7F3D0"
            strokeWidth="1.2"
            filter="url(#cardShadow)"
          />
          <circle cx="20" cy="19" r="10" fill="#ECFDF5" />
          {/* Database Disk Icon */}
          <path
            d="M15 15 C15 13.5 25 13.5 25 15 C25 16.5 15 16.5 15 15 Z"
            stroke="#059669"
            strokeWidth="1"
            fill="none"
          />
          <path
            d="M15 15 L15 23 C15 24.5 25 24.5 25 23 L25 15"
            stroke="#059669"
            strokeWidth="1"
            fill="none"
          />
          <path
            d="M15 19 C15 20.5 25 20.5 25 19"
            stroke="#059669"
            strokeWidth="1"
            fill="none"
          />

          <text x="34" y="17" fontSize="6.5" fontWeight="700" fill="#0F172A" fontFamily="sans-serif">
            Local DB Store
          </text>
          <text x="34" y="26" fontSize="5.5" fontWeight="600" fill="#059669" fontFamily="sans-serif">
            IndexedDB Engine
          </text>
          <rect x="8" y="35" width="80" height="15" rx="4" fill="#F0FDF4" />
          <text x="48" y="45.5" textAnchor="middle" fontSize="5.5" fontWeight="700" fill="#047857" fontFamily="sans-serif">
            Zero Data Loss Sync
          </text>
        </g>
      </motion.g>
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

    setIsLoading(true);
    try {
      if (isFirebaseConfigured) {
        try {
          const userCredential = await signInWithEmailAndPassword(auth, email.trim(), password);
          if (userCredential.user) {
            const matchingProfile =
              SYNTHETIC_PROFILES.find(
                (p) =>
                  p.phone_number?.includes(email) ||
                  p.worker_code.toLowerCase().includes(email.toLowerCase())
              ) || doctorProfile;
            onAuthenticated({
              ...matchingProfile,
              auth_user_id: userCredential.user.uid,
              preferred_language: selectedLanguage,
            });
            return;
          }
        } catch (firebaseErr: unknown) {
          const errObj = firebaseErr as { code?: string; message?: string };
          if (
            errObj?.code === 'auth/configuration-not-found' ||
            errObj?.message?.includes('CONFIGURATION_NOT_FOUND')
          ) {
            setAuthError(
              'Firebase Auth is ready on sakshya-aasha, but Email/Password provider is not yet enabled in the Firebase console. Choose one of the 3 role buttons above to enter directly.'
            );
            return;
          }
          throw firebaseErr;
        }
      }

      if (!supabase || !isRealSupabaseConfigured) {
        setAuthError(
          'Please select one of the 3 role entry cards above to enter the portal directly.'
        );
        return;
      }

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
                <Database className="w-3.5 h-3.5 text-emerald-600" />
                <span>Local DB Storage</span>
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
                        <span className="text-xs font-bold text-slate-800">Staff Portal Login</span>
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                            isFirebaseConfigured || isRealSupabaseConfigured
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : 'bg-slate-100 text-slate-600 border border-slate-200'
                          }`}
                        >
                          {isFirebaseConfigured
                            ? 'Firebase: sakshya-aasha'
                            : isRealSupabaseConfigured
                            ? 'Supabase Connected'
                            : 'Local Mock'}
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
