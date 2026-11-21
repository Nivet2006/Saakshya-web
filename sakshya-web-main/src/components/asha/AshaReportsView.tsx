'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { buildVisitsCsv } from '@/lib/analytics/supervisor-metrics';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type {
  Beneficiary,
  DangerAlert,
  FollowUpTask,
  UserProfile,
  VisitDraft,
} from '@/types';
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  FileText,
  Printer,
  ShieldAlert,
} from 'lucide-react';

type ReportTemplateId = 'visit_form' | 'monthly_register' | 'referral_slip';

const SAMPLE_TEST_VISITS: VisitDraft[] = [
  {
    visit_id: 'SAMPLE-VIS-001',
    beneficiary_id: 'BEN-1044',
    beneficiary_name: 'Baby of Kavitha Rao',
    visit_type: 'Newborn',
    weight_kg: 1.65,
    vaccinations_completed: ['BCG', 'OPV-0'],
    vaccinations_due: ['Hepatitis B'],
    next_visit_date: '2026-11-29',
    danger_signs: ['Very Low Birth Weight (<1.8 kg)', 'Lethargy / Poor Feeding'],
    danger_sign_flagged: true,
    follow_up_actions: [
      {
        action_type: 'danger_referral',
        description: 'Immediate PHC/FRU referral for VLBW newborn stabilization & KMC',
        due_date: '2026-11-22',
        priority: 'urgent',
      },
    ],
    observations: [
      {
        key: 'temperature',
        label: 'Temperature',
        value: 36.4,
        unit: '°C',
        category: 'measurement',
        status: 'confirmed',
      },
      {
        key: 'spo2_pct',
        label: 'SpO2 (Oxygen Saturation)',
        value: 95,
        unit: '%',
        category: 'measurement',
        status: 'confirmed',
      },
      {
        key: 'newborn_care_note',
        label: 'Newborn Care',
        value: 'KMC started, cord clean and dry',
        category: 'newborn_care',
        status: 'confirmed',
      },
    ],
    status: 'confirmed',
    confirmed_fields: ['beneficiary_id', 'visit_type', 'weight_kg', 'next_visit_date'],
    created_at: '2026-11-22T09:15:00Z',
  },
  {
    visit_id: 'SAMPLE-VIS-002',
    beneficiary_id: 'BEN-1042',
    beneficiary_name: 'Lakshmi Devi',
    visit_type: 'ANC',
    weight_kg: 52.5,
    vaccinations_completed: ['Td-1'],
    vaccinations_due: ['Td-2'],
    next_visit_date: '2026-12-05',
    danger_signs: [],
    danger_sign_flagged: false,
    follow_up_actions: [
      {
        action_type: 'ifa_adherence',
        description: 'Continue daily IFA & Calcium tablets; monitor Hb at next ANC',
        due_date: '2026-12-05',
        priority: 'normal',
      },
    ],
    observations: [
      {
        key: 'blood_pressure',
        label: 'Blood Pressure',
        value: '116/76',
        unit: 'mmHg',
        category: 'measurement',
        status: 'confirmed',
      },
      {
        key: 'hemoglobin_g_dl',
        label: 'Hemoglobin (Hb)',
        value: 10.8,
        unit: 'g/dL',
        category: 'measurement',
        status: 'confirmed',
      },
      {
        key: 'edd_date',
        label: 'Expected Delivery Date (EDD)',
        value: '2027-01-18',
        category: 'maternal_health',
        status: 'confirmed',
      },
    ],
    status: 'confirmed',
    confirmed_fields: ['beneficiary_id', 'visit_type', 'weight_kg', 'next_visit_date'],
    created_at: '2026-11-21T14:30:00Z',
  },
];

interface AshaReportsViewProps {
  profile: UserProfile;
  beneficiaries: Beneficiary[];
  visits: VisitDraft[];
  followUps: FollowUpTask[];
  dangerAlerts: DangerAlert[];
}

export const AshaReportsView: React.FC<AshaReportsViewProps> = ({
  profile,
  beneficiaries,
  visits,
  followUps,
  dangerAlerts,
}) => {
  const { ui } = useTranslation();

  const [template, setTemplate] = useState<ReportTemplateId>('visit_form');
  const [useSampleData, setUseSampleData] = useState<boolean>(false);
  const [selectedVisitId, setSelectedVisitId] = useState<string>(() => visits[0]?.visit_id || '');
  const [phcName, setPhcName] = useState<string>(profile.phc_name || 'Rampur PHC');
  const [subCentre, setSubCentre] = useState<string>(profile.assigned_area || 'Sub-Centre Ward 1');
  const [referralFacility, setReferralFacility] = useState<string>('Nearest PHC / CHC Emergency');
  const [workerRemarks, setWorkerRemarks] = useState<string>('');

  const effectiveVisits = useSampleData ? SAMPLE_TEST_VISITS : visits;

  useEffect(() => {
    if (useSampleData) {
      setSelectedVisitId(SAMPLE_TEST_VISITS[0].visit_id);
    } else if (!selectedVisitId && visits.length > 0) {
      setSelectedVisitId(visits[0].visit_id);
    }
  }, [visits, selectedVisitId, useSampleData]);

  const sortedVisits = useMemo(
    () =>
      [...effectiveVisits].sort((a, b) =>
        (b.created_at || b.confirmed_at || '').localeCompare(a.created_at || a.confirmed_at || '')
      ),
    [effectiveVisits]
  );

  const activeVisit = useMemo(
    () => sortedVisits.find((v) => v.visit_id === selectedVisitId) || sortedVisits[0] || null,
    [sortedVisits, selectedVisitId]
  );

  const activeBeneficiary = useMemo(() => {
    if (!activeVisit) return null;
    return (
      beneficiaries.find((b) => b.beneficiary_id === activeVisit.beneficiary_id) || null
    );
  }, [activeVisit, beneficiaries]);

  const relatedFollowUps = useMemo(() => {
    if (!activeVisit) return [];
    return followUps.filter(
      (f) => activeVisit.beneficiary_id && f.beneficiary_id === activeVisit.beneficiary_id
    );
  }, [activeVisit, followUps]);

  const relatedAlerts = useMemo(() => {
    if (!activeVisit) return [];
    return dangerAlerts.filter(
      (a) =>
        a.visit_id === activeVisit.visit_id ||
        (activeVisit.beneficiary_id && a.beneficiary_id === activeVisit.beneficiary_id)
    );
  }, [activeVisit, dangerAlerts]);

  const registerSummary = useMemo(() => {
    const counts = {
      total: sortedVisits.length,
      anc: 0,
      pnc: 0,
      newborn: 0,
      immunisation: 0,
      danger: 0,
      confirmed: 0,
    };
    for (const v of sortedVisits) {
      if (v.visit_type === 'ANC') counts.anc += 1;
      else if (v.visit_type === 'PNC') counts.pnc += 1;
      else if (v.visit_type === 'Newborn') counts.newborn += 1;
      else if (v.visit_type === 'Immunisation') counts.immunisation += 1;
      if (v.danger_sign_flagged) counts.danger += 1;
      if (v.status === 'confirmed' || v.status === 'committed') counts.confirmed += 1;
    }
    return counts;
  }, [sortedVisits]);

  const handlePrintOrPdf = () => {
    if (typeof window !== 'undefined') {
      window.print();
    }
  };

  const handleDownloadCsv = () => {
    const csv = buildVisitsCsv(sortedVisits);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `asha_visit_register_${profile.worker_code || 'worker'}_${new Date()
      .toISOString()
      .slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const todayFormatted = new Date().toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });

  return (
    <div className="space-y-5">
      {/* Control Panel — Hidden on Print / PDF Export */}
      <div className="no-print space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-clinical-text">
              {ui.navReportsAudit} — ASHA Field Forms
            </h1>
            <p className="text-xs sm:text-sm text-clinical-text-secondary">
              Auto-filled NHM visit forms, monthly registers, and PHC referral slips ready to print or export as PDF.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setUseSampleData((prev) => !prev)}
              className={`px-3.5 py-2.5 rounded-xl border text-xs font-bold flex items-center gap-1.5 transition-colors ${
                useSampleData
                  ? 'bg-amber-50 border-amber-400 text-amber-900'
                  : 'bg-white border-slate-300 text-clinical-text hover:bg-slate-50'
              }`}
            >
              <CheckCircle2 className="h-4 w-4 text-amber-600" aria-hidden="true" />
              <span>{useSampleData ? 'Using Sample Data' : 'Load Sample Data'}</span>
            </button>
            {template === 'monthly_register' && (
              <button
                type="button"
                onClick={handleDownloadCsv}
                className="px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-clinical-text text-xs font-bold hover:bg-slate-50 flex items-center gap-1.5"
              >
                <Download className="h-4 w-4 text-clinical-primary" aria-hidden="true" />
                <span>Export CSV</span>
              </button>
            )}
            <button
              type="button"
              onClick={handlePrintOrPdf}
              className="px-4 py-2.5 rounded-xl bg-clinical-primary hover:bg-clinical-primary-dark text-white text-xs sm:text-sm font-bold shadow-sm flex items-center gap-2"
            >
              <Printer className="h-4 w-4" aria-hidden="true" />
              <span>Export PDF / Print</span>
            </button>
          </div>
        </div>

        {/* Template Selector Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <button
            type="button"
            onClick={() => setTemplate('visit_form')}
            className={`text-left p-4 rounded-2xl border transition-all ${
              template === 'visit_form'
                ? 'bg-emerald-50/70 border-clinical-primary ring-2 ring-clinical-primary/20'
                : 'bg-white border-clinical-border-subtle hover:border-slate-300'
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <FileText
                className={`h-4 w-4 ${
                  template === 'visit_form' ? 'text-clinical-primary' : 'text-slate-500'
                }`}
              />
              <span className="text-sm font-bold text-clinical-text">
                Home Visit Form (HBNC / ANC)
              </span>
            </div>
            <p className="text-xs text-slate-600">
              Predefined structured form auto-filled with vitals, weight, vaccines & follow-up.
            </p>
          </button>

          <button
            type="button"
            onClick={() => setTemplate('monthly_register')}
            className={`text-left p-4 rounded-2xl border transition-all ${
              template === 'monthly_register'
                ? 'bg-emerald-50/70 border-clinical-primary ring-2 ring-clinical-primary/20'
                : 'bg-white border-clinical-border-subtle hover:border-slate-300'
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <FileSpreadsheet
                className={`h-4 w-4 ${
                  template === 'monthly_register' ? 'text-clinical-primary' : 'text-slate-500'
                }`}
              />
              <span className="text-sm font-bold text-clinical-text">
                Monthly ASHA Visit Register
              </span>
            </div>
            <p className="text-xs text-slate-600">
              Complete tabular register summarizing all recorded household visits & totals.
            </p>
          </button>

          <button
            type="button"
            onClick={() => setTemplate('referral_slip')}
            className={`text-left p-4 rounded-2xl border transition-all ${
              template === 'referral_slip'
                ? 'bg-rose-50/70 border-clinical-danger ring-2 ring-clinical-danger/20'
                : 'bg-white border-clinical-border-subtle hover:border-slate-300'
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <ShieldAlert
                className={`h-4 w-4 ${
                  template === 'referral_slip' ? 'text-clinical-danger' : 'text-slate-500'
                }`}
              />
              <span className="text-sm font-bold text-clinical-text">
                PHC Danger Referral Slip
              </span>
            </div>
            <p className="text-xs text-slate-600">
              Printable emergency referral slip for high-risk or danger-sign flagged visits.
            </p>
          </button>
        </div>

        {/* Auto-feed Controls & Quick Form Overrides */}
        <div className="bg-white border border-clinical-border-subtle rounded-2xl p-4 shadow-sm grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {template !== 'monthly_register' && (
            <div>
              <label
                htmlFor="report-visit-select"
                className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1"
              >
                Auto-Feed From Visit
              </label>
              <select
                id="report-visit-select"
                value={activeVisit?.visit_id || ''}
                onChange={(e) => setSelectedVisitId(e.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-clinical-text"
              >
                {sortedVisits.length === 0 ? (
                  <option value="">No visits recorded yet</option>
                ) : (
                  sortedVisits.map((v) => (
                    <option key={v.visit_id} value={v.visit_id}>
                      {v.beneficiary_name || v.beneficiary_id || 'Unnamed'} ·{' '}
                      {v.visit_type || 'Visit'} ({(v.created_at || '').slice(0, 10) || 'Draft'})
                    </option>
                  ))
                )}
              </select>
            </div>
          )}

          <div>
            <label
              htmlFor="report-phc-input"
              className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1"
            >
              PHC / Facility Name
            </label>
            <input
              id="report-phc-input"
              type="text"
              value={phcName}
              onChange={(e) => setPhcName(e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-xs font-medium text-clinical-text"
            />
          </div>

          <div>
            <label
              htmlFor="report-subcentre-input"
              className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1"
            >
              Sub-Centre / Village Area
            </label>
            <input
              id="report-subcentre-input"
              type="text"
              value={subCentre}
              onChange={(e) => setSubCentre(e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-xs font-medium text-clinical-text"
            />
          </div>

          {template === 'referral_slip' ? (
            <div>
              <label
                htmlFor="report-referral-target"
                className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1"
              >
                Referred To (PHC / FRU)
              </label>
              <input
                id="report-referral-target"
                type="text"
                value={referralFacility}
                onChange={(e) => setReferralFacility(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-xs font-medium text-clinical-text"
              />
            </div>
          ) : (
            <div>
              <label
                htmlFor="report-remarks-input"
                className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1"
              >
                Worker Remarks (Optional)
              </label>
              <input
                id="report-remarks-input"
                type="text"
                value={workerRemarks}
                onChange={(e) => setWorkerRemarks(e.target.value)}
                placeholder="Add note to print on form..."
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-xs font-medium text-clinical-text"
              />
            </div>
          )}
        </div>
      </div>

      {/* =================================================================== */}
      {/* PRINTABLE A4 PREDEFINED FORM SHEET                                   */}
      {/* =================================================================== */}
      <article className="bg-white border border-slate-300 rounded-2xl p-6 sm:p-8 shadow-sm print:border-0 print:shadow-none print:p-0 text-slate-900">
        {/* Official NHM Header */}
        <header className="border-b-2 border-slate-800 pb-4 mb-5 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest text-teal-800">
              National Health Mission · ASHA Field Register (Sakshya)
            </p>
            <h2 className="text-lg sm:text-xl font-extrabold text-slate-900 mt-0.5">
              {template === 'visit_form'
                ? 'HOME VISIT CLINICAL RECORD FORM (HBNC / ANC / PNC)'
                : template === 'monthly_register'
                ? 'MONTHLY ASHA VISIT & IMMUNISATION REGISTER'
                : 'URGENT PHC / FRU REFERRAL SLIP (DANGER SIGN)'}
            </h2>
          </div>
          <div className="text-xs text-left sm:text-right space-y-0.5">
            <p>
              <span className="font-bold">Form ID:</span>{' '}
              <span className="font-mono">
                {template === 'visit_form'
                  ? 'NHM-HV-01'
                  : template === 'monthly_register'
                  ? 'NHM-REG-04'
                  : 'NHM-REF-02'}
              </span>
            </p>
            <p>
              <span className="font-bold">Generated:</span> {todayFormatted}
            </p>
          </div>
        </header>

        {/* Worker & Facility Metadata Grid */}
        <section className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 border border-slate-300 rounded-xl p-3 mb-5 text-xs">
          <div>
            <span className="block text-[10px] font-bold uppercase text-slate-500">
              ASHA Worker Name
            </span>
            <span className="font-bold text-slate-900">{profile.full_name}</span>
          </div>
          <div>
            <span className="block text-[10px] font-bold uppercase text-slate-500">
              Worker Code
            </span>
            <span className="font-mono font-bold text-slate-900">
              {profile.worker_code || 'ASHA-01'}
            </span>
          </div>
          <div>
            <span className="block text-[10px] font-bold uppercase text-slate-500">
              PHC / Facility
            </span>
            <span className="font-bold text-slate-900">{phcName}</span>
          </div>
          <div>
            <span className="block text-[10px] font-bold uppercase text-slate-500">
              Sub-Centre / Area
            </span>
            <span className="font-bold text-slate-900">{subCentre}</span>
          </div>
        </section>

        {/* TEMPLATE 1: HOME VISIT CLINICAL FORM */}
        {template === 'visit_form' && (
          <div className="space-y-5">
            {!activeVisit ? (
              <p className="text-sm text-slate-500 py-8 text-center border border-dashed border-slate-300 rounded-xl">
                No visit records found yet. Complete a Voice Visit first to auto-fill this form.
              </p>
            ) : (
              <>
                <table className="w-full border-collapse border border-slate-400 text-xs">
                  <tbody>
                    <tr>
                      <th className="border border-slate-400 bg-slate-100 px-3 py-2 text-left w-1/4">
                        Beneficiary Name
                      </th>
                      <td className="border border-slate-400 px-3 py-2 font-bold">
                        {activeVisit.beneficiary_name ||
                          activeBeneficiary?.full_name ||
                          'Not recorded'}
                      </td>
                      <th className="border border-slate-400 bg-slate-100 px-3 py-2 text-left w-1/4">
                        Beneficiary ID
                      </th>
                      <td className="border border-slate-400 px-3 py-2 font-mono">
                        {activeVisit.beneficiary_id || '—'}
                      </td>
                    </tr>
                    <tr>
                      <th className="border border-slate-400 bg-slate-100 px-3 py-2 text-left">
                        Visit Type
                      </th>
                      <td className="border border-slate-400 px-3 py-2 font-bold">
                        {activeVisit.visit_type || 'Unspecified'}
                      </td>
                      <th className="border border-slate-400 bg-slate-100 px-3 py-2 text-left">
                        Visit Date / Status
                      </th>
                      <td className="border border-slate-400 px-3 py-2">
                        {(activeVisit.created_at || '').slice(0, 10) || todayFormatted} ·{' '}
                        <span className="uppercase font-bold">{activeVisit.status}</span>
                      </td>
                    </tr>
                    <tr>
                      <th className="border border-slate-400 bg-slate-100 px-3 py-2 text-left">
                        Village / Household
                      </th>
                      <td className="border border-slate-400 px-3 py-2">
                        {activeBeneficiary?.village || subCentre}
                      </td>
                      <th className="border border-slate-400 bg-slate-100 px-3 py-2 text-left">
                        Recorded Weight
                      </th>
                      <td className="border border-slate-400 px-3 py-2 font-bold tabular-nums">
                        {activeVisit.weight_kg !== null ? `${activeVisit.weight_kg} kg` : '—'}
                      </td>
                    </tr>
                    <tr>
                      <th className="border border-slate-400 bg-slate-100 px-3 py-2 text-left">
                        Vaccines Given
                      </th>
                      <td className="border border-slate-400 px-3 py-2">
                        {activeVisit.vaccinations_completed.length > 0
                          ? activeVisit.vaccinations_completed.join(', ')
                          : 'None recorded'}
                      </td>
                      <th className="border border-slate-400 bg-slate-100 px-3 py-2 text-left">
                        Vaccines Due
                      </th>
                      <td className="border border-slate-400 px-3 py-2 font-semibold">
                        {activeVisit.vaccinations_due.length > 0
                          ? activeVisit.vaccinations_due.join(', ')
                          : 'None due'}
                      </td>
                    </tr>
                    <tr>
                      <th className="border border-slate-400 bg-slate-100 px-3 py-2 text-left">
                        Next Scheduled Visit
                      </th>
                      <td className="border border-slate-400 px-3 py-2 tabular-nums font-bold">
                        {activeVisit.next_visit_date || 'Not scheduled'}
                      </td>
                      <th className="border border-slate-400 bg-slate-100 px-3 py-2 text-left">
                        Danger Sign Flagged?
                      </th>
                      <td
                        className={`border border-slate-400 px-3 py-2 font-bold ${
                          activeVisit.danger_sign_flagged ? 'text-red-700 bg-red-50' : 'text-emerald-800'
                        }`}
                      >
                        {activeVisit.danger_sign_flagged
                          ? `YES — ${activeVisit.danger_signs.join(', ')}`
                          : 'NO (Routine Visit)'}
                      </td>
                    </tr>
                  </tbody>
                </table>

                {/* Vitals & Clinical Observations */}
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                    Vitals, Measurements & Clinical Observations
                  </h3>
                  {activeVisit.observations && activeVisit.observations.length > 0 ? (
                    <table className="w-full border-collapse border border-slate-400 text-xs">
                      <thead>
                        <tr className="bg-slate-100">
                          <th className="border border-slate-400 px-3 py-1.5 text-left">
                            Observation / Vital
                          </th>
                          <th className="border border-slate-400 px-3 py-1.5 text-left">Value</th>
                          <th className="border border-slate-400 px-3 py-1.5 text-left">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {activeVisit.observations.map((obs, idx) => (
                          <tr key={`${obs.key}-${idx}`}>
                            <td className="border border-slate-400 px-3 py-1.5 font-semibold">
                              {obs.label}
                            </td>
                            <td className="border border-slate-400 px-3 py-1.5 tabular-nums">
                              {String(obs.value)} {obs.unit || ''}
                            </td>
                            <td className="border border-slate-400 px-3 py-1.5 uppercase text-[11px]">
                              {obs.status}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <p className="text-xs text-slate-500 italic border border-slate-300 rounded-lg px-3 py-2">
                      No additional vital measurements recorded in this visit.
                    </p>
                  )}
                </div>

                {/* Follow-Up Actions */}
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                    Follow-Up & Referral Actions
                  </h3>
                  {relatedFollowUps.length > 0 || activeVisit.follow_up_actions.length > 0 ? (
                    <ul className="border border-slate-400 divide-y divide-slate-300 text-xs">
                      {activeVisit.follow_up_actions.map((act, i) => (
                        <li key={i} className="px-3 py-2 flex items-center justify-between gap-2">
                          <span>
                            <strong className="uppercase">{act.priority}:</strong> {act.description}
                          </span>
                          <span className="font-mono text-[11px] shrink-0">
                            {act.due_date || 'Immediate'}
                          </span>
                        </li>
                      ))}
                      {relatedFollowUps.map((f, idx) => (
                        <li
                          key={f.id || `followup-${idx}`}
                          className="px-3 py-2 flex items-center justify-between gap-2 bg-slate-50"
                        >
                          <span>{f.notes || f.task_type}</span>
                          <span className="font-mono text-[11px] shrink-0">
                            Due: {f.due_date} ({f.status})
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-slate-500 italic border border-slate-300 rounded-lg px-3 py-2">
                      No pending follow-up actions.
                    </p>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {/* TEMPLATE 2: MONTHLY ASHA VISIT REGISTER */}
        {template === 'monthly_register' && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 text-center text-xs">
              <div className="border border-slate-300 rounded-lg p-2">
                <span className="block text-[10px] font-bold uppercase text-slate-500">Total</span>
                <span className="text-base font-extrabold tabular-nums">{registerSummary.total}</span>
              </div>
              <div className="border border-slate-300 rounded-lg p-2">
                <span className="block text-[10px] font-bold uppercase text-slate-500">ANC</span>
                <span className="text-base font-extrabold tabular-nums">{registerSummary.anc}</span>
              </div>
              <div className="border border-slate-300 rounded-lg p-2">
                <span className="block text-[10px] font-bold uppercase text-slate-500">PNC</span>
                <span className="text-base font-extrabold tabular-nums">{registerSummary.pnc}</span>
              </div>
              <div className="border border-slate-300 rounded-lg p-2">
                <span className="block text-[10px] font-bold uppercase text-slate-500">
                  Newborn
                </span>
                <span className="text-base font-extrabold tabular-nums">
                  {registerSummary.newborn}
                </span>
              </div>
              <div className="border border-slate-300 rounded-lg p-2">
                <span className="block text-[10px] font-bold uppercase text-slate-500">
                  Immunis.
                </span>
                <span className="text-base font-extrabold tabular-nums">
                  {registerSummary.immunisation}
                </span>
              </div>
              <div className="border border-red-300 bg-red-50 rounded-lg p-2">
                <span className="block text-[10px] font-bold uppercase text-red-700">
                  Referrals
                </span>
                <span className="text-base font-extrabold text-red-700 tabular-nums">
                  {registerSummary.danger}
                </span>
              </div>
            </div>

            <table className="w-full border-collapse border border-slate-400 text-xs">
              <thead>
                <tr className="bg-slate-100">
                  <th className="border border-slate-400 px-2 py-2 text-left">#</th>
                  <th className="border border-slate-400 px-2 py-2 text-left">Date</th>
                  <th className="border border-slate-400 px-2 py-2 text-left">Beneficiary</th>
                  <th className="border border-slate-400 px-2 py-2 text-left">Type</th>
                  <th className="border border-slate-400 px-2 py-2 text-left">Weight</th>
                  <th className="border border-slate-400 px-2 py-2 text-left">Vaccines Due</th>
                  <th className="border border-slate-400 px-2 py-2 text-left">Danger Flag</th>
                  <th className="border border-slate-400 px-2 py-2 text-left">Next Visit</th>
                </tr>
              </thead>
              <tbody>
                {sortedVisits.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="border border-slate-400 px-3 py-6 text-center text-slate-500">
                      No visits recorded yet.
                    </td>
                  </tr>
                ) : (
                  sortedVisits.map((v, idx) => (
                    <tr key={v.visit_id}>
                      <td className="border border-slate-400 px-2 py-1.5 tabular-nums">{idx + 1}</td>
                      <td className="border border-slate-400 px-2 py-1.5 tabular-nums">
                        {(v.created_at || '').slice(0, 10) || '—'}
                      </td>
                      <td className="border border-slate-400 px-2 py-1.5 font-semibold">
                        {v.beneficiary_name || v.beneficiary_id || '—'}
                      </td>
                      <td className="border border-slate-400 px-2 py-1.5">{v.visit_type || '—'}</td>
                      <td className="border border-slate-400 px-2 py-1.5 tabular-nums">
                        {v.weight_kg !== null ? `${v.weight_kg} kg` : '—'}
                      </td>
                      <td className="border border-slate-400 px-2 py-1.5">
                        {v.vaccinations_due.join(', ') || '—'}
                      </td>
                      <td
                        className={`border border-slate-400 px-2 py-1.5 font-bold ${
                          v.danger_sign_flagged ? 'text-red-700' : 'text-emerald-800'
                        }`}
                      >
                        {v.danger_sign_flagged ? v.danger_signs.join(', ') || 'YES' : 'No'}
                      </td>
                      <td className="border border-slate-400 px-2 py-1.5 tabular-nums">
                        {v.next_visit_date || '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* TEMPLATE 3: URGENT PHC REFERRAL SLIP */}
        {template === 'referral_slip' && (
          <div className="space-y-4">
            <div className="border-2 border-red-700 bg-red-50/70 rounded-xl p-4 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-700 shrink-0 mt-0.5" />
              <div className="text-xs space-y-1">
                <p className="font-extrabold text-red-900 uppercase">
                  Priority Medical Referral — Immediate PHC / FRU Evaluation Required
                </p>
                <p className="text-red-800">
                  Referred Facility: <strong>{referralFacility}</strong>
                </p>
              </div>
            </div>

            {activeVisit ? (
              <table className="w-full border-collapse border border-slate-400 text-xs">
                <tbody>
                  <tr>
                    <th className="border border-slate-400 bg-slate-100 px-3 py-2 text-left w-1/3">
                      Patient / Beneficiary Name
                    </th>
                    <td className="border border-slate-400 px-3 py-2 font-bold">
                      {activeVisit.beneficiary_name || activeBeneficiary?.full_name || '—'} (
                      {activeVisit.beneficiary_id || 'ID Pending'})
                    </td>
                  </tr>
                  <tr>
                    <th className="border border-slate-400 bg-slate-100 px-3 py-2 text-left">
                      Visit Category & Date
                    </th>
                    <td className="border border-slate-400 px-3 py-2">
                      {activeVisit.visit_type || 'Home Visit'} ·{' '}
                      {(activeVisit.created_at || '').slice(0, 10) || todayFormatted}
                    </td>
                  </tr>
                  <tr>
                    <th className="border border-slate-400 bg-slate-100 px-3 py-2 text-left">
                      Detected Danger Signs / Clinical Reason
                    </th>
                    <td className="border border-slate-400 px-3 py-2 font-bold text-red-800">
                      {activeVisit.danger_signs.length > 0
                        ? activeVisit.danger_signs.join(', ')
                        : relatedAlerts.length > 0
                        ? relatedAlerts.map((a) => a.canonical_name).join(', ')
                        : 'High-risk clinical observation noted by ASHA worker'}
                    </td>
                  </tr>
                  <tr>
                    <th className="border border-slate-400 bg-slate-100 px-3 py-2 text-left">
                      Key Vitals Recorded
                    </th>
                    <td className="border border-slate-400 px-3 py-2">
                      {activeVisit.weight_kg !== null ? `Weight: ${activeVisit.weight_kg} kg. ` : ''}
                      {activeVisit.observations && activeVisit.observations.length > 0
                        ? activeVisit.observations
                            .map((o) => `${o.label}: ${o.value}${o.unit ? ` ${o.unit}` : ''}`)
                            .join(' | ')
                        : 'See home visit sheet'}
                    </td>
                  </tr>
                </tbody>
              </table>
            ) : (
              <p className="text-xs text-slate-500 italic">No visit selected.</p>
            )}
          </div>
        )}

        {/* Worker Remarks & Signature Block */}
        {workerRemarks.trim() && (
          <div className="mt-4 border border-slate-300 rounded-lg p-3 text-xs">
            <span className="font-bold uppercase text-[10px] text-slate-500 block mb-0.5">
              ASHA Worker Remarks
            </span>
            <p className="text-slate-900">{workerRemarks}</p>
          </div>
        )}

        <footer className="mt-8 pt-4 border-t border-slate-300 grid grid-cols-2 gap-8 text-xs">
          <div>
            <div className="h-10 border-b border-slate-400 mb-1" />
            <p className="font-bold text-slate-800">ASHA Worker Signature</p>
            <p className="text-[11px] text-slate-500">
              {profile.full_name} ({profile.worker_code || 'ASHA-01'})
            </p>
          </div>
          <div>
            <div className="h-10 border-b border-slate-400 mb-1" />
            <p className="font-bold text-slate-800">ANM / Medical Officer Verification</p>
            <p className="text-[11px] text-slate-500">{phcName}</p>
          </div>
        </footer>
      </article>
    </div>
  );
};
