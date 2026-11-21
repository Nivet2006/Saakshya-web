'use client';

import React, { useState } from 'react';
import { SYNTHETIC_PROFILES } from '@/lib/mock-data';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import { isRealSupabaseConfigured, supabase } from '@/lib/supabase/client';
import { PRISMA_LANGUAGES } from '@/lib/translations';
import type { LanguageCode, UserProfile } from '@/types';
import {
  AlertCircle,
  ArrowRight,
  Globe,
  HeartPulse,
  Lock,
  ShieldCheck,
  Stethoscope,
  UserCheck,
} from 'lucide-react';

interface LoginScreenProps {
  selectedLanguage: LanguageCode;
  onLanguageChange: (lang: LanguageCode) => void;
  onAuthenticated: (profile: UserProfile) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({
  selectedLanguage,
  onLanguageChange,
  onAuthenticated,
}) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const { ui } = useTranslation(selectedLanguage);

  const handleSupabaseLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);

    if (!email.trim() || !password) {
      setAuthError('Please enter your email and password.');
      return;
    }

    if (!supabase || !isRealSupabaseConfigured) {
      setAuthError(
        'Supabase Auth environment variables are not configured in .env.local. Use one of the synthetic role profiles below for local demonstration.'
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
            ...SYNTHETIC_PROFILES[0],
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

  const handleDemoRoleLogin = (profile: UserProfile) => {
    setAuthError(null);
    onAuthenticated({
      ...profile,
      preferred_language: profile.preferred_language || selectedLanguage,
    });
  };

  return (
    <div className="min-h-screen bg-clinical-canvas flex flex-col justify-center py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl w-full mx-auto grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
        {/* Left Brand & Quick Synthetic Role Sign-In */}
        <section className="bg-clinical-primary text-white rounded-2xl p-6 sm:p-8 flex flex-col justify-between shadow-lg">
          <div>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-11 h-11 rounded-xl bg-white/15 flex items-center justify-center">
                <HeartPulse className="h-6 w-6 text-white" aria-hidden="true" />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight">{ui.appName}</h1>
                <p className="text-xs text-teal-100">ASHA Voice Field Register · NHM Platform</p>
              </div>
            </div>

            <h2 className="text-2xl sm:text-3xl font-bold leading-tight">
              {ui.loginHeroTitle}
            </h2>
            <p className="mt-3 text-sm text-teal-50/90 leading-relaxed">
              {ui.loginHeroDesc}
            </p>

            {/* Synthetic Quick Access for Field Demo & Judging */}
            <div className="mt-7">
              <p className="text-xs font-bold uppercase tracking-wider text-teal-200 mb-3 flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                {ui.syntheticRolesHeading}
              </p>
              <div className="space-y-2.5">
                {SYNTHETIC_PROFILES.map((profile) => {
                  const isSupervisor = profile.role === 'PHC_SUPERVISOR';
                  return (
                    <button
                      key={profile.id}
                      type="button"
                      onClick={() => handleDemoRoleLogin(profile)}
                      className="w-full text-left p-3.5 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 transition-colors flex items-center justify-between gap-3"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-9 h-9 rounded-lg bg-white text-clinical-primary flex items-center justify-center shrink-0">
                          {isSupervisor ? (
                            <Stethoscope className="h-5 w-5" aria-hidden="true" />
                          ) : (
                            <UserCheck className="h-5 w-5" aria-hidden="true" />
                          )}
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-bold text-white truncate">
                            {profile.full_name}
                          </p>
                          <p className="text-xs text-teal-100 truncate">
                            {isSupervisor ? 'PHC Supervisor Command Center' : 'ASHA Worker Portal'} ·{' '}
                            {profile.assigned_area}
                          </p>
                        </div>
                      </div>
                      <ArrowRight className="h-4 w-4 text-teal-100 shrink-0" aria-hidden="true" />
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <p className="mt-6 text-[11px] text-teal-100/80">
            All beneficiaries (`BEN-1042`–`BEN-1048`) and visit records are synthetic demonstration fixtures.
          </p>
        </section>

        {/* Right Card: Language Selection + Supabase Account Sign-in */}
        <section className="bg-white border border-clinical-border-subtle rounded-2xl p-6 sm:p-8 shadow-sm flex flex-col justify-between">
          <div>
            <div className="mb-6">
              <label
                htmlFor="login-language-select"
                className="block text-xs font-bold uppercase tracking-wider text-clinical-text-secondary mb-2"
              >
                {ui.selectAppLanguage}
              </label>
              <div className="relative">
                <Globe
                  className="h-4 w-4 text-clinical-primary absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                  aria-hidden="true"
                />
                <select
                  id="login-language-select"
                  value={selectedLanguage}
                  onChange={(e) => onLanguageChange(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-clinical-border bg-slate-50 text-sm font-semibold text-clinical-text"
                >
                  {PRISMA_LANGUAGES.map((l) => (
                    <option key={l.code} value={l.code}>
                      {l.nativeName} ({l.name})
                    </option>
                  ))}
                  <option value="indic-auto">Auto-Detect Indic (Code-Mixed)</option>
                </select>
              </div>
            </div>

            <div className="border-t border-slate-200 pt-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-clinical-text flex items-center gap-2">
                  <Lock className="h-4 w-4 text-clinical-primary" aria-hidden="true" />
                  <span>{ui.staffSignInTitle}</span>
                </h2>
                <span
                  className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${
                    isRealSupabaseConfigured
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : 'bg-slate-100 text-slate-600 border border-slate-200'
                  }`}
                >
                  {isRealSupabaseConfigured ? 'Auth Connected' : 'Local Demo Mode'}
                </span>
              </div>

              {authError && (
                <div
                  role="alert"
                  className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-900 flex items-start gap-2"
                >
                  <AlertCircle className="h-4 w-4 text-clinical-danger shrink-0 mt-0.5" />
                  <span>{authError}</span>
                </div>
              )}

              <form onSubmit={handleSupabaseLogin} className="space-y-4">
                <div>
                  <label
                    htmlFor="login-email"
                    className="block text-xs font-semibold text-clinical-text mb-1.5"
                  >
                    {ui.emailLabel}
                  </label>
                  <input
                    id="login-email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="asha.worker@phc-demo.local"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-clinical-border text-sm bg-white"
                  />
                </div>

                <div>
                  <label
                    htmlFor="login-password"
                    className="block text-xs font-semibold text-clinical-text mb-1.5"
                  >
                    {ui.passwordLabel}
                  </label>
                  <input
                    id="login-password"
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter password"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-clinical-border text-sm bg-white"
                  />
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full py-3 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-sm font-bold transition-colors disabled:opacity-50"
                >
                  {isLoading ? ui.signingInButton : ui.signInButton}
                </button>
              </form>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100 text-xs text-clinical-text-secondary">
            Tip: Tap any role card on the left for instant offline-capable synthetic field walkthroughs.
          </div>
        </section>
      </div>
    </div>
  );
};

