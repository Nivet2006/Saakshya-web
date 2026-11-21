'use client';

import React, { useState } from 'react';
import { Beneficiary, FollowUpTask, LanguageCode, UserProfile, VisitDraft } from '@/types';
import { BeneficiaryCard } from '@/components/BeneficiaryCard';
import { TRANSLATIONS } from '@/lib/translations';
import {
  Mic,
  Users,
  Calendar,
  AlertTriangle,
  Search,
  CheckCircle2,
  Clock,
  PlusCircle,
  FileText,
  ShieldCheck,
} from 'lucide-react';

interface AshaPortalProps {
  currentProfile: UserProfile;
  currentLanguage: LanguageCode;
  beneficiaries: Beneficiary[];
  followUps: FollowUpTask[];
  recentVisits: VisitDraft[];
  onStartVoiceVisit: (beneficiary?: Beneficiary) => void;
  onToggleFollowUp: (taskId: string) => void;
}

export const AshaPortal: React.FC<AshaPortalProps> = ({
  currentProfile,
  currentLanguage,
  beneficiaries,
  followUps,
  recentVisits,
  onStartVoiceVisit,
  onToggleFollowUp,
}) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');

  const t = TRANSLATIONS[currentLanguage] || TRANSLATIONS['hi-IN'];

  const highRiskCount = beneficiaries.filter((b) => b.high_risk_status).length;
  const pendingFollowUps = followUps.filter((f) => f.status === 'PENDING');

  const filteredBeneficiaries = beneficiaries.filter((b) => {
    const matchesSearch =
      b.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.beneficiary_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.village.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;
    if (categoryFilter === 'HIGH_RISK') return b.high_risk_status;
    if (categoryFilter !== 'ALL' && b.category !== categoryFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Hero Voice Action Banner */}
      <div className="bg-gradient-to-r from-brand-700 via-brand-600 to-emerald-600 rounded-3xl p-6 sm:p-8 text-white shadow-xl flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="max-w-xl">
          <div className="inline-flex items-center gap-2 bg-white/20 backdrop-blur-md px-3 py-1 rounded-full text-xs font-semibold mb-3">
            <ShieldCheck className="h-4 w-4 text-emerald-200" />
            <span>{t.ashaPortal} · {currentProfile.assigned_area}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            {t.greeting}, {currentProfile.full_name}!
          </h1>
          <p className="mt-2 text-sm text-emerald-100 leading-relaxed">
            {t.bannerDescription}
          </p>

          <div className="mt-4 flex items-center gap-4 text-xs font-semibold text-emerald-100 flex-wrap">
            <span className="flex items-center gap-1.5">
              <Users className="h-4 w-4 text-white" />
              {beneficiaries.length} {t.totalBeneficiaries}
            </span>
            <span className="flex items-center gap-1.5">
              <AlertTriangle className="h-4 w-4 text-amber-300" />
              {highRiskCount} {t.highRisk}
            </span>
            <span className="flex items-center gap-1.5">
              <Calendar className="h-4 w-4 text-emerald-200" />
              {pendingFollowUps.length} {t.dueFollowUps}
            </span>
          </div>
        </div>

        {/* Big Start Voice Visit Button */}
        <button
          onClick={() => onStartVoiceVisit()}
          className="w-full md:w-auto px-8 py-5 rounded-2xl bg-white hover:bg-emerald-50 text-brand-800 font-extrabold text-lg shadow-2xl hover:scale-105 active:scale-95 transition-all flex items-center justify-center gap-3 shrink-0 group border-2 border-emerald-100"
          aria-label={t.startVoiceVisit}
        >
          <div className="w-12 h-12 rounded-full bg-emergency-600 group-hover:bg-emergency-500 text-white flex items-center justify-center shadow-lg animate-pulse-mic">
            <Mic className="h-7 w-7" />
          </div>
          <div className="text-left">
            <span className="block text-xs uppercase text-slate-500 font-bold tracking-wider">
              {t.instantVoiceVisit}
            </span>
            <span className="text-slate-900 font-black text-xl">{t.startVoiceVisit}</span>
          </div>
        </button>
      </div>

      {/* Main Grid: Beneficiaries & Tasks */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Beneficiary Directory (2 Columns) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                {t.assignedBeneficiaries}
              </h2>
              <p className="text-xs text-slate-500">
                {t.selectBeneficiaryHelp}
              </p>
            </div>

            {/* Search Input */}
            <div className="relative min-w-[240px]">
              <Search className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder={t.searchPlaceholder}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>

          {/* Category Filter Chips */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
            {[
              { id: 'ALL', label: t.allFilter },
              { id: 'HIGH_RISK', label: t.highRiskFilter },
              { id: 'PREGNANT_WOMAN', label: t.ancFilter },
              { id: 'INFANT', label: t.infantFilter },
              { id: 'CHILD', label: t.childFilter },
              { id: 'LACTATING_MOTHER', label: t.pncFilter },
            ].map((chip) => (
              <button
                key={chip.id}
                onClick={() => setCategoryFilter(chip.id)}
                className={`px-3 py-1.5 rounded-full font-semibold whitespace-nowrap transition-all ${
                  categoryFilter === chip.id
                    ? 'bg-brand-700 text-white shadow-sm'
                    : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100'
                }`}
              >
                {chip.label}
              </button>
            ))}
          </div>

          {/* Beneficiary Card Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {filteredBeneficiaries.map((b) => (
              <BeneficiaryCard
                key={b.id}
                beneficiary={b}
                language={currentLanguage}
                onStartVisit={(ben) => onStartVoiceVisit(ben)}
              />
            ))}
            {filteredBeneficiaries.length === 0 && (
              <div className="col-span-2 text-center py-10 bg-white rounded-2xl border border-dashed border-slate-200 text-slate-400 text-xs">
                {t.noBeneficiariesFound}
              </div>
            )}
          </div>
        </div>

        {/* Sidebar: Follow-ups & Recent Visits */}
        <div className="space-y-6">
          {/* Follow-up Tasks */}
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-brand-600" />
                <h3 className="font-bold text-slate-900 text-sm">{t.dueTasks}</h3>
              </div>
              <span className="text-xs font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">
                {pendingFollowUps.length}
              </span>
            </div>

            <div className="mt-3 space-y-2.5">
              {followUps.map((task) => (
                <div
                  key={task.id}
                  className={`p-3 rounded-xl border transition-all text-xs flex items-start gap-2.5 ${
                    task.status === 'COMPLETED'
                      ? 'bg-slate-50 border-slate-200 text-slate-400'
                      : task.priority === 'URGENT'
                      ? 'bg-red-50 border-red-200 text-red-900'
                      : 'bg-white border-slate-200'
                  }`}
                >
                  <button
                    onClick={() => onToggleFollowUp(task.id)}
                    className="mt-0.5 text-slate-400 hover:text-emerald-600 transition-colors"
                    aria-label="Toggle task completion"
                  >
                    {task.status === 'COMPLETED' ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    ) : (
                      <div className="h-4 w-4 rounded border border-slate-300" />
                    )}
                  </button>
                  <div className="flex-1">
                    <p
                      className={`font-semibold ${
                        task.status === 'COMPLETED' ? 'line-through text-slate-400' : 'text-slate-800'
                      }`}
                    >
                      {task.task_type}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      {task.beneficiary_name} · {t.nextFollowUp} {task.due_date}
                    </p>
                  </div>
                </div>
              ))}
              {followUps.length === 0 && (
                <p className="text-center py-4 text-slate-400 text-xs">{t.noPendingTasks}</p>
              )}
            </div>
          </div>

          {/* Recent Synced Visits */}
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
              <FileText className="h-4 w-4 text-brand-600" />
              <h3 className="font-bold text-slate-900 text-sm">{t.recentVisits}</h3>
            </div>

            <div className="mt-3 space-y-2.5">
              {recentVisits.map((v) => (
                <div key={v.draft_id} className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                  <div className="flex items-center justify-between font-bold text-slate-800">
                    <span>{v.beneficiary_name}</span>
                    <span className="text-[10px] bg-brand-100 text-brand-800 px-2 py-0.5 rounded font-mono">
                      {v.visit_type}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1 line-clamp-2">
                    {v.notes || v.raw_transcript_summary || t.confirmed}
                  </p>
                </div>
              ))}
              {recentVisits.length === 0 && (
                <p className="text-center py-4 text-slate-400 text-xs">{t.noVisitsRecorded}</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
