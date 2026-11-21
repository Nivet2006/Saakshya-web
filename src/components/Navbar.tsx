'use client';

import React from 'react';
import { UserProfile, LanguageCode } from '@/types';
import { SYNTHETIC_PROFILES } from '@/lib/mock-data';
import { OfflineSyncBadge } from '@/components/OfflineSyncBadge';
import { Globe, UserCheck, ShieldAlert, HeartPulse } from 'lucide-react';

interface NavbarProps {
  currentProfile: UserProfile;
  onProfileChange: (profile: UserProfile) => void;
  currentLanguage: LanguageCode;
  onLanguageChange: (lang: LanguageCode) => void;
  activeTab: 'asha' | 'supervisor';
  onTabChange: (tab: 'asha' | 'supervisor') => void;
  unresolvedAlertCount: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentProfile,
  onProfileChange,
  currentLanguage,
  onLanguageChange,
  activeTab,
  onTabChange,
  unresolvedAlertCount,
}) => {
  return (
    <header className="sticky top-0 z-30 bg-white border-b border-slate-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Portal Switcher */}
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-brand-600 flex items-center justify-center text-white shadow-sm font-bold text-xl">
              <HeartPulse className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 tracking-tight text-lg">
                  साक्ष्या ASHA
                </span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-brand-100 text-brand-800 hidden sm:inline-block">
                  Voice Field Register
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">
                National Health Mission · {currentProfile.phc_name}
              </p>
            </div>
          </div>

          {/* Navigation Mode: Worker vs Supervisor */}
          <div className="flex bg-slate-100 p-1 rounded-lg border border-slate-200">
            <button
              onClick={() => onTabChange('asha')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                activeTab === 'asha'
                  ? 'bg-white text-brand-700 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              ASHA Portal
            </button>
            <button
              onClick={() => onTabChange('supervisor')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all flex items-center gap-1.5 ${
                activeTab === 'supervisor'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span>PHC Supervisor</span>
              {unresolvedAlertCount > 0 && (
                <span className="inline-flex items-center justify-center px-1.5 py-0.5 text-[10px] font-bold bg-emergency-600 text-white rounded-full">
                  {unresolvedAlertCount}
                </span>
              )}
            </button>
          </div>

          {/* Right Controls: Language Selector, Sync Badge, Profile Switcher */}
          <div className="flex items-center gap-3">
            <OfflineSyncBadge />

            {/* Language Selector */}
            <div className="flex items-center bg-slate-50 border border-slate-200 rounded-lg px-2 py-1">
              <Globe className="h-4 w-4 text-slate-500 mr-1.5 hidden sm:block" />
              <select
                value={currentLanguage}
                onChange={(e) => onLanguageChange(e.target.value as LanguageCode)}
                className="bg-transparent text-xs font-medium text-slate-700 focus:outline-none cursor-pointer"
                aria-label="Select Language"
              >
                <option value="hi-IN">हिन्दी (Hindi)</option>
                <option value="kn-IN">ಕನ್ನಡ (Kannada)</option>
                <option value="ta-IN">தமிழ் (Tamil)</option>
                <option value="en-IN">English</option>
              </select>
            </div>

            {/* Profile Selector (Demo Mode) */}
            <div className="flex items-center bg-slate-50 border border-slate-200 rounded-lg px-2 py-1">
              <UserCheck className="h-4 w-4 text-brand-600 mr-1.5 hidden sm:block" />
              <select
                value={currentProfile.id}
                onChange={(e) => {
                  const p = SYNTHETIC_PROFILES.find((prof) => prof.id === e.target.value);
                  if (p) onProfileChange(p);
                }}
                className="bg-transparent text-xs font-semibold text-slate-800 focus:outline-none cursor-pointer max-w-[130px] sm:max-w-none"
                aria-label="Current User Profile"
              >
                {SYNTHETIC_PROFILES.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.full_name} ({p.role === 'ASHA_WORKER' ? 'ASHA' : 'Doctor'})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
