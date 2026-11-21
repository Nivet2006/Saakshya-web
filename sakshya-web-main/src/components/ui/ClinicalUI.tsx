'use client';

import React, { useEffect, useRef } from 'react';
import { useTranslation } from '@/lib/i18n/LanguageContext';
import type { FieldConfirmStatus } from '@/types';
import {
  AlertCircle,
  CheckCircle2,
  Edit3,
  HelpCircle,
  Inbox,
  RefreshCw,
  Sparkles,
} from 'lucide-react';

export const ClinicalCard: React.FC<{
  children: React.ReactNode;
  className?: string;
  padding?: 'sm' | 'md' | 'lg';
}> = ({ children, className = '', padding = 'md' }) => {
  const padClass = padding === 'sm' ? 'p-3' : padding === 'lg' ? 'p-5 sm:p-6' : 'p-4';
  return (
    <div
      className={`bg-clinical-card border border-clinical-border-subtle rounded-xl shadow-sm ${padClass} ${className}`}
    >
      {children}
    </div>
  );
};

export const FieldStatusPill: React.FC<{
  status: FieldConfirmStatus;
  compact?: boolean;
}> = ({ status, compact = false }) => {
  const { ui } = useTranslation();
  const config: Record<
    FieldConfirmStatus,
    { label: string; classes: string; icon: React.ReactNode }
  > = {
    extracted: {
      label: ui.statusExtracted,
      classes: 'bg-sky-50 text-sky-800 border-sky-200',
      icon: <Sparkles className="h-3 w-3" aria-hidden="true" />,
    },
    needs_clarification: {
      label: ui.needsClarification,
      classes: 'bg-amber-50 text-amber-800 border-amber-300',
      icon: <HelpCircle className="h-3 w-3" aria-hidden="true" />,
    },
    corrected: {
      label: ui.statusCorrected,
      classes: 'bg-indigo-50 text-indigo-800 border-indigo-200',
      icon: <Edit3 className="h-3 w-3" aria-hidden="true" />,
    },
    confirmed: {
      label: ui.confirmed,
      classes: 'bg-emerald-50 text-emerald-800 border-emerald-200',
      icon: <CheckCircle2 className="h-3 w-3" aria-hidden="true" />,
    },
    missing: {
      label: ui.notIdentified,
      classes: 'bg-slate-100 text-slate-600 border-slate-300',
      icon: <HelpCircle className="h-3 w-3" aria-hidden="true" />,
    },
  };

  const item = config[status];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border font-semibold ${
        compact ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-0.5 text-xs'
      } ${item.classes}`}
    >
      {item.icon}
      <span>{item.label}</span>
    </span>
  );
};

export const EmptyState: React.FC<{
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}> = ({ title, description, icon, action }) => (
  <div className="bg-clinical-card border border-dashed border-clinical-border rounded-xl p-8 text-center flex flex-col items-center justify-center">
    <div className="w-11 h-11 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center mb-3">
      {icon || <Inbox className="h-5 w-5" aria-hidden="true" />}
    </div>
    <h3 className="text-sm font-bold text-clinical-text">{title}</h3>
    <p className="text-xs text-clinical-muted mt-1 max-w-sm leading-relaxed">{description}</p>
    {action && <div className="mt-4">{action}</div>}
  </div>
);

export const ErrorBanner: React.FC<{
  title?: string;
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
  onDismiss?: () => void;
}> = ({ title = 'Connection Issue', message, onRetry, retryLabel = 'Retry', onDismiss }) => (
  <div
    role="alert"
    className="bg-red-50 border border-red-300 rounded-xl p-3.5 text-red-950 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
  >
    <div className="flex items-start gap-2.5 min-w-0">
      <AlertCircle className="h-5 w-5 text-clinical-danger shrink-0 mt-0.5" aria-hidden="true" />
      <div className="min-w-0">
        <p className="text-xs font-bold text-clinical-danger-dark">{title}</p>
        <p className="text-xs text-red-900 mt-0.5 leading-relaxed">{message}</p>
      </div>
    </div>
    <div className="flex items-center gap-2 shrink-0">
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white border border-red-300 text-red-800 hover:bg-red-100 text-xs font-semibold transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          <span>{retryLabel}</span>
        </button>
      )}
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="px-2.5 py-2 rounded-lg text-xs font-medium text-red-700 hover:bg-red-100"
        >
          Dismiss
        </button>
      )}
    </div>
  </div>
);

export const SkeletonCard: React.FC<{ rows?: number }> = ({ rows = 3 }) => (
  <div className="bg-white border border-slate-200 rounded-xl p-4 animate-pulse space-y-3">
    <div className="h-4 bg-slate-200 rounded w-1/3" />
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} className="h-3 bg-slate-100 rounded w-full" />
    ))}
  </div>
);

export const NativeConfirmDialog: React.FC<{
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}> = ({
  open,
  title,
  description,
  confirmLabel,
  cancelLabel = 'Cancel',
  destructive = false,
  onConfirm,
  onCancel,
}) => {
  const dialogRef = useRef<HTMLDialogElement | null>(null);

  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    if (open && !el.open) {
      el.showModal();
    } else if (!open && el.open) {
      el.close();
    }
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      onCancel={onCancel}
      aria-labelledby="confirm-dialog-title"
      className="rounded-2xl border border-slate-200 shadow-2xl p-0 max-w-md w-[calc(100%-2rem)] backdrop:bg-slate-900/60"
    >
      <div className="p-5 sm:p-6 bg-white">
        <h2 id="confirm-dialog-title" className="text-base font-bold text-clinical-text">
          {title}
        </h2>
        <p className="text-sm text-clinical-text-secondary mt-2 leading-relaxed">{description}</p>
        <div className="mt-5 flex flex-col-reverse sm:flex-row sm:justify-end gap-2.5">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2.5 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-100 text-sm font-semibold"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={`px-4 py-2.5 rounded-xl text-white text-sm font-bold shadow-sm ${
              destructive
                ? 'bg-clinical-danger hover:bg-red-700'
                : 'bg-clinical-primary hover:bg-clinical-primary-dark'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  );
};

