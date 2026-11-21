'use client';

import React, { useState, useEffect } from 'react';
import { Beneficiary, DangerAlert, FollowUpTask, LanguageCode, UserProfile, VisitDraft } from '@/types';
import { SYNTHETIC_PROFILES } from '@/lib/mock-data';
import { syntheticRepo } from '@/lib/supabase/client';
import { Navbar } from '@/components/Navbar';
import { AshaPortal } from '@/components/AshaPortal';
import { SupervisorPortal } from '@/components/SupervisorPortal';
import { VoiceSessionModal } from '@/components/VoiceSessionModal';

export default function HomePage() {
  const [currentProfile, setCurrentProfile] = useState<UserProfile>(SYNTHETIC_PROFILES[0]);
  const [currentLanguage, setCurrentLanguage] = useState<LanguageCode>('hi-IN');
  const [activeTab, setActiveTab] = useState<'asha' | 'supervisor'>('asha');

  const [beneficiaries, setBeneficiaries] = useState<Beneficiary[]>([]);
  const [dangerAlerts, setDangerAlerts] = useState<DangerAlert[]>([]);
  const [visits, setVisits] = useState<VisitDraft[]>([]);
  const [followUps, setFollowUps] = useState<FollowUpTask[]>([]);

  // Active voice visit state
  const [isVoiceSessionOpen, setIsVoiceSessionOpen] = useState<boolean>(false);
  const [selectedBeneficiary, setSelectedBeneficiary] = useState<Beneficiary | null>(null);

  const refreshData = () => {
    setBeneficiaries(syntheticRepo.getBeneficiaries());
    setDangerAlerts(syntheticRepo.getDangerAlerts());
    setVisits(syntheticRepo.getVisits());
    setFollowUps(syntheticRepo.getFollowUps());
  };

  useEffect(() => {
    refreshData();
  }, []);

  const handleStartVoiceVisit = (beneficiary?: Beneficiary) => {
    // If no beneficiary passed, select the first high-risk or first assigned beneficiary
    const target = beneficiary || beneficiaries[0];
    if (target) {
      setSelectedBeneficiary(target);
      setIsVoiceSessionOpen(true);
    }
  };

  const handleVisitSaved = (savedDraft: VisitDraft) => {
    syntheticRepo.addVisit(savedDraft);
    refreshData();
  };

  const handleAcknowledgeAlert = (alertId: string) => {
    syntheticRepo.acknowledgeAlert(alertId, currentProfile.full_name);
    refreshData();
  };

  const handleToggleFollowUp = (taskId: string) => {
    const task = followUps.find((t) => t.id === taskId);
    if (task) {
      task.status = task.status === 'COMPLETED' ? 'PENDING' : 'COMPLETED';
      task.completed_at = task.status === 'COMPLETED' ? new Date().toISOString() : undefined;
      setFollowUps([...followUps]);
    }
  };

  const unacknowledgedAlertCount = dangerAlerts.filter((a) => !a.supervisor_acknowledged).length;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Universal Header Navbar */}
      <Navbar
        currentProfile={currentProfile}
        onProfileChange={(p) => {
          setCurrentProfile(p);
          if (p.role === 'PHC_SUPERVISOR' || p.role === 'ADMIN') {
            setActiveTab('supervisor');
          } else {
            setActiveTab('asha');
          }
        }}
        currentLanguage={currentLanguage}
        onLanguageChange={(lang) => setCurrentLanguage(lang)}
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab)}
        unresolvedAlertCount={unacknowledgedAlertCount}
      />

      {/* Main App Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'asha' ? (
          <AshaPortal
            currentProfile={currentProfile}
            currentLanguage={currentLanguage}
            beneficiaries={beneficiaries}
            followUps={followUps}
            recentVisits={visits}
            onStartVoiceVisit={handleStartVoiceVisit}
            onToggleFollowUp={handleToggleFollowUp}
          />
        ) : (
          <SupervisorPortal
            currentProfile={currentProfile}
            dangerAlerts={dangerAlerts}
            visits={visits}
            onAcknowledgeAlert={handleAcknowledgeAlert}
          />
        )}
      </main>

      {/* Active Voice Session Modal */}
      {isVoiceSessionOpen && selectedBeneficiary && (
        <VoiceSessionModal
          beneficiary={selectedBeneficiary}
          ashaWorker={currentProfile}
          language={currentLanguage}
          onClose={() => setIsVoiceSessionOpen(false)}
          onVisitSaved={handleVisitSaved}
        />
      )}
    </div>
  );
}
