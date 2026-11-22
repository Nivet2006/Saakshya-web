'use client';

import React, { useMemo, useState } from 'react';
import type { Beneficiary, DangerAlert, UserProfile, VisitDraft } from '@/types';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  MapPin,
  Mic,
  Navigation,
  Route,
} from 'lucide-react';

interface AshaRouteMapViewProps {
  profile: UserProfile;
  beneficiaries: Beneficiary[];
  visits: VisitDraft[];
  dangerAlerts: DangerAlert[];
  onStartVoiceVisit: (beneficiary: Beneficiary) => void;
}

const DEMO_DISTANCES = [
  { dist: '350 m', eta: '4 min walk', house: 'House #14' },
  { dist: '820 m', eta: '9 min walk', house: 'House #22' },
  { dist: '1.4 km', eta: '14 min walk', house: 'House #31' },
  { dist: '2.1 km', eta: '22 min walk', house: 'House #08' },
  { dist: '2.7 km', eta: '26 min walk', house: 'House #45' },
];

export const AshaRouteMapView: React.FC<AshaRouteMapViewProps> = ({
  profile,
  beneficiaries,
  visits,
  dangerAlerts,
  onStartVoiceVisit,
}) => {
  const [filter, setFilter] = useState<'all' | 'urgent' | 'pending' | 'completed'>('all');
  const [selectedStopId, setSelectedStopId] = useState<string | null>(
    beneficiaries[0]?.beneficiary_id || null
  );

  const stops = useMemo(() => {
    return beneficiaries.slice(0, 8).map((ben, idx) => {
      const benVisits = visits.filter((v) => v.beneficiary_id === ben.beneficiary_id);
      const hasDanger =
        ben.high_risk_status ||
        benVisits.some((v) => v.danger_sign_flagged) ||
        dangerAlerts.some(
          (a) => a.beneficiary_id === ben.beneficiary_id && a.status === 'active'
        );
      const isCompleted = benVisits.some(
        (v) => v.status === 'confirmed' || v.status === 'committed'
      );
      const status: 'urgent' | 'completed' | 'pending' = hasDanger
        ? 'urgent'
        : isCompleted
        ? 'completed'
        : 'pending';
      const geo = DEMO_DISTANCES[idx % DEMO_DISTANCES.length];
      return {
        stopNumber: idx + 1,
        beneficiary: ben,
        status,
        house: geo.house,
        distance: geo.dist,
        eta: geo.eta,
      };
    });
  }, [beneficiaries, visits, dangerAlerts]);

  const filteredStops = useMemo(() => {
    if (filter === 'all') return stops;
    return stops.filter((s) => s.status === filter);
  }, [stops, filter]);

  const activeStop =
    filteredStops.find((s) => s.beneficiary.beneficiary_id === selectedStopId) ||
    filteredStops[0] ||
    null;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-clinical-text flex items-center gap-2">
            <Route className="h-5 w-5 text-clinical-primary" aria-hidden="true" />
            <span>Field Route Map</span>
          </h1>
          <p className="text-xs sm:text-sm text-clinical-text-secondary">
            Optimized household visit sequence from {profile.phc_name || 'Rampur PHC'} ·{' '}
            {profile.assigned_area || 'Ward 1'} ({stops.length} homes · ~3.2 km)
          </p>
        </div>

        {/* Status Filter Chips */}
        <div className="flex flex-wrap gap-1.5 bg-slate-100 p-1 rounded-xl border border-slate-200">
          {(
            [
              ['all', `All (${stops.length})`],
              ['urgent', 'Urgent'],
              ['pending', 'Pending'],
              ['completed', 'Completed'],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setFilter(key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                filter === key
                  ? 'bg-white text-clinical-primary shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Split Layout: Map Canvas + Household Stop Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Map Canvas Card */}
        <section className="lg:col-span-7 bg-white border border-clinical-border-subtle rounded-2xl overflow-hidden shadow-sm">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
            <div className="flex items-center gap-2 text-xs font-bold text-clinical-text">
              <MapPin className="h-4 w-4 text-clinical-primary" aria-hidden="true" />
              <span>Today&apos;s GPS Route · {profile.assigned_area || 'Rampur Ward 1'}</span>
            </div>
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
              <Clock className="h-3 w-3" aria-hidden="true" />
              ~28 min total
            </span>
          </div>

          <div className="relative bg-slate-100">
            <img
              src="/images/asha-route-map.jpg"
              alt="Saakshya ASHA field route map showing PHC Rampur and numbered household visit pins"
              className="w-full h-auto max-h-[560px] object-cover block"
            />
          </div>

          {/* Active Stop Quick Action Footer */}
          {activeStop && (
            <div className="p-4 border-t border-slate-100 bg-white flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-clinical-primary text-white text-[11px] font-bold">
                    {activeStop.stopNumber}
                  </span>
                  <p className="text-sm font-bold text-clinical-text truncate">
                    {activeStop.house} · {activeStop.beneficiary.full_name}
                  </p>
                  {activeStop.status === 'urgent' && (
                    <span className="px-2 py-0.5 rounded-full bg-red-50 text-red-700 border border-red-200 text-[10px] font-bold uppercase">
                      Urgent
                    </span>
                  )}
                </div>
                <p className="text-xs text-clinical-text-secondary mt-0.5">
                  {activeStop.beneficiary.village} · {activeStop.distance} ({activeStop.eta})
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                    `${activeStop.beneficiary.village} PHC`
                  )}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-2 rounded-xl border border-slate-300 bg-white text-clinical-text text-xs font-bold hover:bg-slate-50 flex items-center gap-1.5"
                >
                  <Navigation className="h-3.5 w-3.5 text-clinical-primary" aria-hidden="true" />
                  <span>Navigate</span>
                </a>
                <button
                  type="button"
                  onClick={() => onStartVoiceVisit(activeStop.beneficiary)}
                  className="px-3.5 py-2 rounded-xl bg-clinical-primary hover:bg-clinical-primary-dark text-white text-xs font-bold shadow-sm flex items-center gap-1.5"
                >
                  <Mic className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>Start Voice Visit</span>
                </button>
              </div>
            </div>
          )}
        </section>

        {/* Sequential Stop List */}
        <aside className="lg:col-span-5 bg-white border border-clinical-border-subtle rounded-2xl p-4 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <h2 className="text-sm font-bold text-clinical-text">
              Scheduled Household Stops
            </h2>
            <span className="text-[11px] font-semibold text-slate-500">
              Tap stop to focus
            </span>
          </div>

          {filteredStops.length === 0 ? (
            <p className="text-xs text-slate-500 py-8 text-center">
              No households match this filter.
            </p>
          ) : (
            <ul className="space-y-2.5">
              {filteredStops.map((stop) => {
                const isSelected =
                  activeStop?.beneficiary.beneficiary_id === stop.beneficiary.beneficiary_id;
                return (
                  <li key={stop.beneficiary.beneficiary_id}>
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => setSelectedStopId(stop.beneficiary.beneficiary_id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setSelectedStopId(stop.beneficiary.beneficiary_id);
                        }
                      }}
                      className={`p-3 rounded-xl border transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-emerald-50/60 border-clinical-primary ring-1 ring-clinical-primary/20'
                          : 'bg-white border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-start gap-2.5 min-w-0">
                          <span
                            className={`mt-0.5 inline-flex items-center justify-center h-6 w-6 rounded-full text-xs font-bold shrink-0 ${
                              stop.status === 'urgent'
                                ? 'bg-clinical-danger text-white'
                                : stop.status === 'completed'
                                ? 'bg-emerald-600 text-white'
                                : 'bg-clinical-primary text-white'
                            }`}
                          >
                            {stop.status === 'completed' ? (
                              <CheckCircle2 className="h-3.5 w-3.5" />
                            ) : (
                              stop.stopNumber
                            )}
                          </span>
                          <div className="min-w-0">
                            <p className="text-sm font-bold text-clinical-text truncate">
                              {stop.beneficiary.full_name}
                            </p>
                            <p className="text-[11px] text-clinical-text-secondary truncate">
                              {stop.house} · {stop.beneficiary.village} · {stop.beneficiary.beneficiary_id}
                            </p>
                          </div>
                        </div>

                        <span className="text-[11px] font-semibold text-slate-600 tabular-nums shrink-0">
                          {stop.distance}
                        </span>
                      </div>

                      <div className="mt-2.5 flex items-center justify-between gap-2">
                        {stop.status === 'urgent' ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-red-700">
                            <AlertTriangle className="h-3 w-3" aria-hidden="true" />
                            High-Risk Priority Visit
                          </span>
                        ) : stop.status === 'completed' ? (
                          <span className="text-[11px] font-semibold text-emerald-700">
                            Visit Confirmed
                          </span>
                        ) : (
                          <span className="text-[11px] font-medium text-slate-500">
                            {stop.eta} · {stop.beneficiary.category.replace('_', ' ')}
                          </span>
                        )}

                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onStartVoiceVisit(stop.beneficiary);
                          }}
                          className="px-2.5 py-1 rounded-lg bg-clinical-primary-soft text-clinical-primary-dark hover:bg-emerald-100 text-[11px] font-bold"
                        >
                          Visit Now
                        </button>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </aside>
      </div>
    </div>
  );
};

