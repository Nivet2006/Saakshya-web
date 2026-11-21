'use client';

import React, { useState } from 'react';
import { DangerAlert, UserProfile, VisitDraft } from '@/types';
import { DangerAlertBanner } from '@/components/DangerAlertBanner';
import {
  Activity,
  AlertTriangle,
  Building2,
  Calendar,
  Download,
  FileSpreadsheet,
  Filter,
  HeartPulse,
  PhoneCall,
  Search,
  ShieldCheck,
  Users,
} from 'lucide-react';

interface SupervisorPortalProps {
  currentProfile: UserProfile;
  dangerAlerts: DangerAlert[];
  visits: VisitDraft[];
  onAcknowledgeAlert: (alertId: string) => void;
}

export const SupervisorPortal: React.FC<SupervisorPortalProps> = ({
  currentProfile,
  dangerAlerts,
  visits,
  onAcknowledgeAlert,
}) => {
  const [filterVillage, setFilterVillage] = useState<string>('ALL');
  const [filterType, setFilterType] = useState<string>('ALL');

  const unacknowledgedAlerts = dangerAlerts.filter((a) => !a.supervisor_acknowledged);
  const criticalCount = dangerAlerts.filter((a) => a.severity === 'CRITICAL').length;
  const highRiskVisits = visits.filter((v) => v.danger_signs_present).length;

  const exportCSV = () => {
    const headers = [
      'Draft ID',
      'Beneficiary ID',
      'Beneficiary Name',
      'Visit Type',
      'Visit Date',
      'Blood Pressure',
      'Weight (kg)',
      'Danger Sign Flagged',
      'Follow-up Date',
    ];

    const rows = visits.map((v) => [
      v.draft_id,
      v.beneficiary_id,
      `"${v.beneficiary_name}"`,
      v.visit_type,
      v.visit_date,
      v.vitals?.blood_pressure_sys ? `"${v.vitals.blood_pressure_sys}/${v.vitals.blood_pressure_dia}"` : '""',
      v.vitals?.weight_kg || '',
      v.danger_signs_present ? 'YES' : 'NO',
      v.follow_up_date || '',
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `phc_visit_register_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Supervisor Command Center Header */}
      <div className="bg-slate-900 rounded-3xl p-6 sm:p-8 text-white shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center gap-2 bg-slate-800 px-3 py-1 rounded-full text-xs font-semibold mb-2 text-slate-300">
            <Building2 className="h-4 w-4 text-brand-400" />
            <span>PHC कमांड सेंटर · {currentProfile.phc_name}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            {currentProfile.full_name}
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            वास्तविक समय खतरा अलर्ट, आपातकालीन रेफरल और फील्ड निगरानी
          </p>
        </div>

        {/* CSV Export Action */}
        <button
          onClick={exportCSV}
          className="px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-bold shadow-md transition-all flex items-center gap-2"
        >
          <FileSpreadsheet className="h-4 w-4" />
          <span>रजिस्टर निर्यात करें (Export CSV)</span>
        </button>
      </div>

      {/* Operational Metrics Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <span className="text-xs text-slate-500 font-medium">कुल विज़िट (Total Visits)</span>
          <div className="text-2xl font-black text-slate-900 mt-1 flex items-baseline gap-2">
            <span>{visits.length + 12}</span>
            <span className="text-xs font-semibold text-emerald-600">+4 आज</span>
          </div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-red-200 shadow-sm bg-red-50/30">
          <span className="text-xs text-red-600 font-semibold">अस्वीकृत अलर्ट (Active Danger Signs)</span>
          <div className="text-2xl font-black text-red-700 mt-1 flex items-baseline gap-2">
            <span>{unacknowledgedAlerts.length}</span>
            <span className="text-xs font-semibold bg-red-100 text-red-800 px-1.5 py-0.5 rounded">तत्काल</span>
          </div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <span className="text-xs text-slate-500 font-medium">सक्रिय ASHA कार्यकर्ता</span>
          <div className="text-2xl font-black text-slate-900 mt-1">
            <span>3</span>
            <span className="text-xs font-normal text-slate-400 ml-1">/ 3 ऑनलाइन</span>
          </div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <span className="text-xs text-slate-500 font-medium">टीकाकरण कवरेज (Coverage)</span>
          <div className="text-2xl font-black text-emerald-600 mt-1">
            <span>94.2%</span>
          </div>
        </div>
      </div>

      {/* Live Danger Alert Queue (High Priority) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-emergency-600 animate-pulse" />
            <h2 className="text-base font-bold text-slate-900">
              खतरा संकेत अलर्ट कतार (Live Danger Sign Queue)
            </h2>
          </div>
          <span className="text-xs font-bold text-slate-500">
            {dangerAlerts.length} कुल रिकॉर्ड
          </span>
        </div>

        {dangerAlerts.map((alert) => (
          <DangerAlertBanner
            key={alert.alert_id}
            alert={alert}
            isSupervisorView={true}
            onAcknowledge={onAcknowledgeAlert}
          />
        ))}

        {dangerAlerts.length === 0 && (
          <div className="p-6 bg-white rounded-2xl border border-dashed border-slate-200 text-center text-slate-400 text-xs">
            वर्तमान में कोई सक्रिय आपातकालीन अलर्ट नहीं है।
          </div>
        )}
      </div>

      {/* Live Visit Register Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-slate-50">
          <div>
            <h3 className="font-bold text-slate-900 text-sm">क्षेत्रीय विज़िट रजिस्टर (Field Visit Register)</h3>
            <p className="text-xs text-slate-500">सभी ASHA कार्यकर्ताओं द्वारा दर्ज किए गए रिकॉर्ड</p>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <Filter className="h-3.5 w-3.5 text-slate-400" />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-slate-700 font-medium focus:outline-none"
            >
              <option value="ALL">सभी विज़िट प्रकार</option>
              <option value="ANC">गर्भावस्था (ANC)</option>
              <option value="IMMUNISATION">टीकाकरण (Immunisation)</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="p-3">लाभार्थी</th>
                <th className="p-3">विज़िट प्रकार</th>
                <th className="p-3">रक्तचाप / वाइटल्स</th>
                <th className="p-3">खतरा स्थिति</th>
                <th className="p-3">फॉलो-अप</th>
                <th className="p-3">सिंक स्थिति</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {visits.map((v) => (
                <tr key={v.draft_id} className="hover:bg-slate-50 transition-colors">
                  <td className="p-3">
                    <span className="font-bold text-slate-900 block">{v.beneficiary_name}</span>
                    <span className="text-[10px] text-slate-400 font-mono">{v.beneficiary_id}</span>
                  </td>
                  <td className="p-3 font-semibold text-slate-700">
                    <span className="px-2 py-0.5 rounded bg-slate-100 font-mono text-[11px]">
                      {v.visit_type}
                    </span>
                  </td>
                  <td className="p-3 font-medium">
                    {v.vitals?.blood_pressure_sys ? (
                      <span className={v.danger_signs_present ? 'text-red-600 font-bold' : 'text-slate-800'}>
                        {v.vitals.blood_pressure_sys}/{v.vitals.blood_pressure_dia} mmHg
                      </span>
                    ) : (
                      <span className="text-slate-400 italic">--</span>
                    )}
                  </td>
                  <td className="p-3">
                    {v.danger_signs_present ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-red-700 bg-red-100 px-2 py-0.5 rounded-full">
                        <AlertTriangle className="h-3 w-3" />
                        खतरा चिन्ह (Alert)
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                        <ShieldCheck className="h-3 w-3 text-emerald-600" />
                        सामान्य
                      </span>
                    )}
                  </td>
                  <td className="p-3 text-slate-600">
                    {v.follow_up_date || 'आवश्यक नहीं'}
                  </td>
                  <td className="p-3">
                    <span className="text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded text-[11px]">
                      Synced
                    </span>
                  </td>
                </tr>
              ))}
              {visits.length === 0 && (
                <tr>
                  <td colSpan={6} className="p-6 text-center text-slate-400 text-xs">
                    कोई विज़िट डेटा उपलब्ध नहीं है।
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
