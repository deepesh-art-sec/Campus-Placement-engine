import React, { useState, useEffect } from "react";
import { AlertTriangle, X } from "lucide-react";
import { Button } from "./Button";

export interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  description?: string;
  message?: string;
  confirmWord?: string; // If provided, requires user to type this word to enable confirm button
  confirmText?: string; // alias for confirmWord
  confirmButtonText?: string;
  cancelButtonText?: string;
  variant?: "danger" | "warning" | "brand";
  requireTypedConfirm?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  title,
  description,
  message,
  confirmWord,
  confirmText,
  confirmButtonText = "Confirm Action",
  cancelButtonText = "Cancel",
  variant = "danger",
  requireTypedConfirm = false,
  onConfirm,
  onCancel,
  loading = false,
}) => {
  const [typedValue, setTypedValue] = useState("");

  const targetWord = confirmWord || confirmText || (requireTypedConfirm ? "CONFIRM" : undefined);
  const effectiveDescription = description || message || "";

  useEffect(() => {
    if (isOpen) setTypedValue("");
  }, [isOpen]);

  if (!isOpen) return null;

  const isConfirmed = targetWord ? typedValue.trim().toUpperCase() === targetWord.toUpperCase() : true;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="corporate-card rounded-3xl max-w-md w-full p-6 sm:p-7 shadow-2xl border border-[var(--border-card)] text-slate-100 space-y-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div
              className={`w-11 h-11 rounded-2xl flex items-center justify-center shrink-0 ${
                variant === "danger"
                  ? "bg-rose-950/80 border border-rose-500/50 text-rose-400"
                  : variant === "warning"
                  ? "bg-amber-950/80 border border-amber-500/50 text-amber-400"
                  : "bg-blue-950/80 border border-blue-500/50 text-blue-400"
              }`}
            >
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-black text-white tracking-tight">{title}</h3>
              <span className="text-[10px] font-mono uppercase text-slate-400">Irreversible Action</span>
            </div>
          </div>
          <button
            onClick={onCancel}
            disabled={loading}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-[var(--bg-card-hover)] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-slate-300 font-medium leading-relaxed">
          {effectiveDescription}
        </p>

        {targetWord && (
          <div className="space-y-2 pt-2">
            <label className="block text-[11px] font-bold text-slate-300 uppercase tracking-wider">
              Type <span className="text-rose-400 font-mono font-black">{targetWord}</span> to verify:
            </label>
            <input
              type="text"
              value={typedValue}
              onChange={(e) => setTypedValue(e.target.value)}
              placeholder={`Type "${targetWord}" here`}
              disabled={loading}
              className="w-full px-3.5 py-2.5 bg-[var(--bg-input)] border border-[var(--border-input)] rounded-xl text-xs font-mono font-bold text-white focus:outline-none focus:border-rose-500 transition-all"
            />
          </div>
        )}

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-[var(--border-card)]">
          <Button variant="outline" size="sm" onClick={onCancel} disabled={loading}>
            {cancelButtonText}
          </Button>
          <Button
            variant={variant === "danger" ? "danger" : "primary"}
            size="sm"
            onClick={onConfirm}
            loading={loading}
            disabled={!isConfirmed || loading}
          >
            {confirmButtonText}
          </Button>
        </div>
      </div>
    </div>
  );
};
