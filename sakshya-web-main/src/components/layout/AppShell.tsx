'use client';

import React, { useState } from 'react';
import { OfflineSyncBadge } from '@/components/OfflineSyncBadge';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import { PRISMA_LANGUAGES } from '@/lib/translations';
import type { LanguageCode, UserProfile } from '@/types';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CalendarClock,
  ClipboardList,
  FileSpreadsheet,
  Globe,
  HeartPulse,
  History,
  Home,
  LogOut,
  MapPin,
  Menu,
  Mic,
  RefreshCw,
  Stethoscope,
  Users,
  WifiOff,
  X,
} from 'lucide-react';

export type AshaNavSection =
  | 'home'
  | 'voice'
  | 'beneficiaries'
  | 'routemap'
  | 'followups'
  | 'history'
  | 'offline'
  | 'reports';

export type SupervisorNavSection =
  | 'overview'
  | 'alerts'
  | 'workers'
  | 'register'
  | 'analytics'
  | 'reports';

interface AppShellProps {
  currentProfile: UserProfile;
  portal: 'asha' | 'supervisor';
  onPortalChange: (portal: 'asha' | 'supervisor') => void;
  ashaSection: AshaNavSection;
  onAshaSectionChange: (sec: AshaNavSection) => void;
  supervisorSection: SupervisorNavSection;
  onSupervisorSectionChange: (sec: SupervisorNavSection) => void;
  currentLanguage: LanguageCode;
  onLanguageChange: (lang: LanguageCode) => void;
  backendHealthy: boolean | null;
  unresolvedAlertCount: number;
  offlinePendingCount: number;
  onSignOut: () => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  currentProfile,
  portal,
  onPortalChange,
  ashaSection,
  onAshaSectionChange,
  supervisorSection,
  onSupervisorSectionChange,
  currentLanguage,
  onLanguageChange,
  backendHealthy,
  unresolvedAlertCount,
  offlinePendingCount,
  onSignOut,
  children,
}) => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { ui, t } = useTranslation(currentLanguage);

  const ashaNavItems: Array<{
    id: AshaNavSection;
    label: string;
    icon: React.ReactNode;
    badge?: number;
  }> = [
    { id: 'home', label: ui.navHome, icon: <Home className="h-4 w-4" aria-hidden="true" /> },
    { id: 'voice', label: ui.navVoiceVisit, icon: <Mic className="h-4 w-4" aria-hidden="true" /> },
    {
      id: 'beneficiaries',
      label: ui.navBeneficiaries,
      icon: <Users className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 'routemap',
      label: 'Route Map',
      icon: <MapPin className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 'followups',
      label: ui.navFollowUps,
      icon: <CalendarClock className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 'history',
      label: ui.navVisitHistory,
      icon: <History className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 'offline',
      label: ui.navOfflineDrafts,
      icon: <RefreshCw className="h-4 w-4" aria-hidden="true" />,
      badge: offlinePendingCount > 0 ? offlinePendingCount : undefined,
    },
    {
      id: 'reports',
      label: ui.navReportsAudit,
      icon: <FileSpreadsheet className="h-4 w-4" aria-hidden="true" />,
    },
  ];

  const supervisorNavItems: Array<{
    id: SupervisorNavSection;
    label: string;
    icon: React.ReactNode;
    badge?: number;
  }> = [
    {
      id: 'overview',
      label: ui.navPhcOverview,
      icon: <Activity className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 'alerts',
      label: ui.navDangerAlerts,
      icon: <AlertTriangle className="h-4 w-4" aria-hidden="true" />,
      badge: unresolvedAlertCount > 0 ? unresolvedAlertCount : undefined,
    },
    {
      id: 'workers',
      label: ui.navAshaWorkers,
      icon: <Users className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 'register',
      label: ui.navVisitRegister,
      icon: <ClipboardList className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 'analytics',
      label: ui.navAnalytics,
      icon: <BarChart3 className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 'reports',
      label: ui.navReportsAudit,
      icon: <FileSpreadsheet className="h-4 w-4" aria-hidden="true" />,
    },
  ];

  const activeItems = portal === 'asha' ? ashaNavItems : supervisorNavItems;

  const handleSelectNav = (id: string) => {
    if (portal === 'asha') {
      onAshaSectionChange(id as AshaNavSection);
    } else {
      onSupervisorSectionChange(id as SupervisorNavSection);
    }
    setDrawerOpen(false);
  };

  return (
    <div className="min-h-screen bg-clinical-canvas flex flex-col">
      {/* Compact Sticky Top Header */}
      <header className="sticky top-0 z-30 bg-white border-b border-clinical-border-subtle no-print">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 h-16 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <button
              type="button"
              onClick={() => setDrawerOpen(!drawerOpen)}
              className="lg:hidden p-2 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100"
              aria-label="Toggle navigation menu"
              aria-expanded={drawerOpen}
            >
              {drawerOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>

            <div className="h-9 w-9 rounded-xl bg-clinical-primary text-white flex items-center justify-center shrink-0">
              <HeartPulse className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-bold text-clinical-text text-sm sm:text-base truncate">
                  {ui.appName}
                </span>
                <span
                  className={`hidden sm:inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
                    backendHealthy === true
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                      : backendHealthy === false
                      ? 'bg-amber-50 text-amber-800 border-amber-200'
                      : 'bg-slate-100 text-slate-600 border-slate-200'
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      backendHealthy === true
                        ? 'bg-emerald-600'
                        : backendHealthy === false
                        ? 'bg-amber-600'
                        : 'bg-slate-400'
                    }`}
                  />
                  {backendHealthy === true
                    ? ui.voiceApiLive
                    : backendHealthy === false
                    ? ui.voiceApiOffline
                    : ui.checkingApi}
                </span>
              </div>
              <p className="text-[11px] text-clinical-text-secondary truncate hidden sm:block">
                {currentProfile.phc_name || 'Rampur PHC'} · {currentProfile.full_name}
              </p>
            </div>
          </div>

          {/* Right Action Cluster */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Portal Switcher */}
            <div
              role="group"
              aria-label="Workspace Portal"
              className="hidden sm:flex bg-slate-100 p-0.5 rounded-lg border border-slate-200"
            >
              <button
                type="button"
                onClick={() => onPortalChange('asha')}
                className={`px-2.5 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                  portal === 'asha'
                    ? 'bg-white text-clinical-primary shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {ui.ashaPortal}
              </button>
              <button
                type="button"
                onClick={() => onPortalChange('supervisor')}
                className={`px-2.5 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
                  portal === 'supervisor'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Stethoscope className="h-3.5 w-3.5" aria-hidden="true" />
                <span>{ui.supervisorPortal}</span>
                {unresolvedAlertCount > 0 && (
                  <span className="px-1.5 py-0.2 rounded-full bg-clinical-danger text-white text-[10px] font-bold tabular-nums">
                    {unresolvedAlertCount}
                  </span>
                )}
              </button>
            </div>

            <OfflineSyncBadge language={currentLanguage} />

            {/* Compact Language Switcher */}
            <div className="flex items-center bg-slate-50 border border-slate-200 rounded-lg px-2 py-1">
              <Globe className="h-3.5 w-3.5 text-clinical-primary mr-1 hidden md:block" aria-hidden="true" />
              <label htmlFor="header-lang-select" className="sr-only">
                Language
              </label>
              <select
                id="header-lang-select"
                value={currentLanguage}
                onChange={(e) => onLanguageChange(e.target.value)}
                className="bg-transparent text-xs font-semibold text-slate-800 max-w-[105px] sm:max-w-[140px]"
              >
                {PRISMA_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.nativeName} ({l.name})
                  </option>
                ))}
                <option value="indic-auto">{ui.autoDetectIndic}</option>
              </select>
            </div>

            <button
              type="button"
              onClick={onSignOut}
              className="p-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              aria-label={ui.signOut}
              title={ui.signOut}
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      </header>

      {/* Tablet/Mobile Slide-Over Drawer Navigation */}
      {drawerOpen && (
        <div className="fixed inset-0 z-40 lg:hidden flex">
          <div
            className="fixed inset-0 bg-slate-900/50"
            onClick={() => setDrawerOpen(false)}
            aria-hidden="true"
          />
          <nav
            aria-label="Drawer Navigation"
            className="relative z-50 w-72 max-w-[85vw] bg-white h-full border-r border-slate-200 p-4 flex flex-col justify-between shadow-xl"
          >
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                <div>
                  <p className="text-sm font-bold text-clinical-text">{currentProfile.full_name}</p>
                  <p className="text-xs text-clinical-text-secondary">
                    {currentProfile.worker_code} · {currentProfile.assigned_area}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setDrawerOpen(false)}
                  aria-label="Close navigation menu"
                  className="p-2 rounded-lg text-slate-500 hover:bg-slate-100"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="mt-4 flex gap-1.5 bg-slate-100 p-1 rounded-xl">
                <button
                  type="button"
                  onClick={() => onPortalChange('asha')}
                  className={`flex-1 py-2 text-xs font-bold rounded-lg ${
                    portal === 'asha' ? 'bg-white text-clinical-primary shadow-sm' : 'text-slate-600'
                  }`}
                >
                  {ui.ashaPortal}
                </button>
                <button
                  type="button"
                  onClick={() => onPortalChange('supervisor')}
                  className={`flex-1 py-2 text-xs font-bold rounded-lg ${
                    portal === 'supervisor' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
                  }`}
                >
                  {ui.supervisorPortal}
                </button>
              </div>

              <ul className="mt-4 space-y-1">
                {activeItems.map((item) => {
                  const isActive =
                    portal === 'asha' ? ashaSection === item.id : supervisorSection === item.id;
                  return (
                    <li key={item.id}>
                      <button
                        type="button"
                        aria-current={isActive ? 'page' : undefined}
                        onClick={() => handleSelectNav(item.id)}
                        className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                          isActive
                            ? 'bg-clinical-primary-soft text-clinical-primary-dark'
                            : 'text-slate-700 hover:bg-slate-100'
                        }`}
                      >
                        <span className="flex items-center gap-2.5">
                          {item.icon}
                          <span>{item.label}</span>
                        </span>
                        {item.badge !== undefined && (
                          <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-clinical-danger text-white">
                            {item.badge}
                          </span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>

            <button
              type="button"
              onClick={onSignOut}
              className="w-full py-2.5 px-3 rounded-xl border border-slate-300 text-slate-700 font-semibold text-sm flex items-center justify-center gap-2 hover:bg-slate-50"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              <span>{ui.signOut}</span>
            </button>
          </nav>
        </div>
      )}

      {/* Main Content Grid: Persistent Desktop Left Rail + Main Viewport */}
      <div className="flex-1 max-w-7xl w-full mx-auto flex">
        <aside className="hidden lg:flex w-60 shrink-0 flex-col justify-between border-r border-clinical-border-subtle bg-white px-3 py-5 no-print">
          <nav aria-label="Primary">
            <p className="px-3 text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
              {portal === 'asha' ? ui.ashaFieldMode : ui.supervisorMode}
            </p>
            <ul className="space-y-1">
              {activeItems.map((item) => {
                const isActive =
                  portal === 'asha' ? ashaSection === item.id : supervisorSection === item.id;
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      aria-current={isActive ? 'page' : undefined}
                      onClick={() => handleSelectNav(item.id)}
                      className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                        isActive
                          ? 'bg-clinical-primary-soft text-clinical-primary-dark border border-teal-200'
                          : 'text-slate-700 hover:bg-slate-100'
                      }`}
                    >
                      <span className="flex items-center gap-2.5">
                        {item.icon}
                        <span>{item.label}</span>
                      </span>
                      {item.badge !== undefined && (
                        <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-clinical-danger text-white tabular-nums">
                          {item.badge}
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>

          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs">
            <p className="font-bold text-clinical-text">{currentProfile.full_name}</p>
            <p className="text-clinical-text-secondary mt-0.5">{currentProfile.worker_code}</p>
            <p className="text-[11px] text-slate-500 mt-1">{currentProfile.assigned_area}</p>
            {backendHealthy === false && (
              <p className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold text-amber-800">
                <WifiOff className="h-3 w-3" aria-hidden="true" />
                <span>{ui.offlineDraftsBanner}</span>
              </p>
            )}
          </div>
        </aside>

        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 min-w-0 px-3 sm:px-6 py-4 sm:py-6 pb-24 lg:pb-8"
        >
          {children}
        </main>
      </div>

      {/* Mobile Fixed Bottom Navigation Bar (360px - 1023px) */}
      <nav
        aria-label="Mobile Bottom Navigation"
        className="lg:hidden fixed bottom-0 left-0 right-0 z-30 bg-white border-t border-clinical-border shadow-lg mobile-bottom-nav no-print"
      >
        {portal === 'asha' ? (
          <div className="grid grid-cols-5 items-center gap-1 pt-1">
            <MobileTabButton
              active={ashaSection === 'home'}
              onClick={() => onAshaSectionChange('home')}
              icon={<Home className="h-5 w-5" />}
              label={ui.navHome}
            />
            <MobileTabButton
              active={ashaSection === 'beneficiaries'}
              onClick={() => onAshaSectionChange('beneficiaries')}
              icon={<Users className="h-5 w-5" />}
              label={ui.navBeneficiaries}
            />
            <div className="flex justify-center -mt-4">
              <button
                type="button"
                aria-current={ashaSection === 'voice' ? 'page' : undefined}
                onClick={() => onAshaSectionChange('voice')}
                className={`w-14 h-14 rounded-full flex items-center justify-center shadow-lg border-2 border-white transition-transform active:scale-95 ${
                  ashaSection === 'voice'
                    ? 'bg-clinical-primary-dark text-white ring-2 ring-teal-300'
                    : 'bg-clinical-primary text-white'
                }`}
                aria-label={ui.startVoiceVisit}
              >
                <Mic className="h-6 w-6" aria-hidden="true" />
              </button>
            </div>
            <MobileTabButton
              active={ashaSection === 'followups'}
              onClick={() => onAshaSectionChange('followups')}
              icon={<CalendarClock className="h-5 w-5" />}
              label={ui.navFollowUps}
            />
            <MobileTabButton
              active={ashaSection === 'history' || ashaSection === 'offline'}
              onClick={() => onAshaSectionChange(offlinePendingCount > 0 ? 'offline' : 'history')}
              icon={<History className="h-5 w-5" />}
              label={offlinePendingCount > 0 ? `${ui.pendingSync} (${offlinePendingCount})` : ui.navVisitHistory}
            />
          </div>
        ) : (
          <div className="grid grid-cols-4 items-center gap-1 pt-1">
            <MobileTabButton
              active={supervisorSection === 'overview'}
              onClick={() => onSupervisorSectionChange('overview')}
              icon={<Activity className="h-5 w-5" />}
              label={ui.navPhcOverview}
            />
            <MobileTabButton
              active={supervisorSection === 'alerts'}
              onClick={() => onSupervisorSectionChange('alerts')}
              icon={<AlertTriangle className="h-5 w-5" />}
              label={`${ui.navDangerAlerts}${unresolvedAlertCount > 0 ? ` (${unresolvedAlertCount})` : ''}`}
            />
            <MobileTabButton
              active={supervisorSection === 'register'}
              onClick={() => onSupervisorSectionChange('register')}
              icon={<ClipboardList className="h-5 w-5" />}
              label={ui.navVisitRegister}
            />
            <MobileTabButton
              active={supervisorSection === 'analytics' || supervisorSection === 'reports'}
              onClick={() => onSupervisorSectionChange('analytics')}
              icon={<BarChart3 className="h-5 w-5" />}
              label={ui.navAnalytics}
            />
          </div>
        )}
      </nav>
    </div>
  );
};

const MobileTabButton: React.FC<{
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}> = ({ active, onClick, icon, label }) => (
  <button
    type="button"
    aria-current={active ? 'page' : undefined}
    onClick={onClick}
    className={`flex flex-col items-center justify-center py-1 px-1 rounded-lg text-[11px] font-semibold transition-colors ${
      active ? 'text-clinical-primary' : 'text-slate-500 hover:text-slate-900'
    }`}
  >
    {icon}
    <span className="mt-0.5 truncate max-w-full">{label}</span>
  </button>
);

