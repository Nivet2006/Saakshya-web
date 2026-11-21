'use client';

import React, { useEffect, useState } from 'react';
import { syncManager } from '@/lib/sync/sync-manager';
import { getAllLocalDrafts } from '@/lib/offline/indexeddb-store';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import { LanguageCode } from '@/types';
import { RefreshCw, Wifi, WifiOff, CheckCircle2 } from 'lucide-react';

interface OfflineSyncBadgeProps {
  language?: LanguageCode;
}

export const OfflineSyncBadge: React.FC<OfflineSyncBadgeProps> = ({ language = 'hi-IN' }) => {
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [lastSyncResult, setLastSyncResult] = useState<string | null>(null);

  const { ui } = useTranslation(language);

  const checkPending = async () => {
    try {
      const drafts = await getAllLocalDrafts();
      const pending = drafts.filter((d) => d.sync_status === 'pending' || d.sync_status === 'failed');
      setPendingCount(pending.length);
    } catch (e) {
      console.warn('Could not read local drafts', e);
    }
  };

  useEffect(() => {
    setIsOnline(navigator.onLine);
    checkPending();

    const handleOnline = () => {
      setIsOnline(true);
      syncManager.triggerSync();
    };
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    const unsubscribe = syncManager.subscribe(() => {
      setIsSyncing(syncManager.isCurrentlySyncing());
      checkPending();
    });

    const interval = setInterval(checkPending, 8000);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      unsubscribe();
      clearInterval(interval);
    };
  }, []);

  const handleManualSync = async () => {
    setIsSyncing(true);
    const res = await syncManager.triggerSync();
    setIsSyncing(false);
    if (res.total > 0) {
      setLastSyncResult(`${res.synced}/${res.total} ${ui.syncedVisits}`);
      setTimeout(() => setLastSyncResult(null), 4000);
    }
  };

  return (
    <div className="flex items-center gap-2">
      {/* Network indicator */}
      <div
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
          isOnline ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'
        }`}
        title={isOnline ? ui.online : ui.offline}
      >
        {isOnline ? (
          <>
            <Wifi className="h-3.5 w-3.5 text-emerald-600" />
            <span className="hidden sm:inline">{ui.online}</span>
          </>
        ) : (
          <>
            <WifiOff className="h-3.5 w-3.5 text-amber-600" />
            <span>{ui.offline}</span>
          </>
        )}
      </div>

      {/* Drafts & Sync Button */}
      {pendingCount > 0 ? (
        <button
          onClick={handleManualSync}
          disabled={isSyncing || !isOnline}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 hover:bg-amber-200 transition-colors border border-amber-300 disabled:opacity-50"
          title={ui.syncConfirmedQueue}
        >
          <RefreshCw className={`h-3 w-3 ${isSyncing ? 'animate-spin' : ''}`} />
          <span>{pendingCount} {ui.pendingSync}</span>
        </button>
      ) : lastSyncResult ? (
        <div className="flex items-center gap-1 text-xs text-emerald-700 font-medium">
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
          <span className="hidden md:inline">{lastSyncResult}</span>
        </div>
      ) : null}
    </div>
  );
};
