import React from "react";
import { XCircle, Loader2 } from "lucide-react";

interface ProgressBarProps {
  label: string;
  progressPercent: number;
  isCancellable?: boolean;
  onCancel?: () => void;
  subLabel?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  label,
  progressPercent,
  isCancellable = true,
  onCancel,
  subLabel,
}) => {
  return (
    <div className="bg-[#0d1527] border border-[#1b2b4d] rounded-2xl p-4 shadow-md space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
          <span className="text-sm font-bold text-white">{label}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono font-bold text-emerald-300 bg-emerald-950/80 border border-emerald-800/60 px-2 py-0.5 rounded-full">
            {Math.round(progressPercent)}%
          </span>
          {isCancellable && onCancel && (
            <button
              onClick={onCancel}
              className="text-xs flex items-center gap-1 text-slate-400 hover:text-rose-400 font-medium px-2 py-1 rounded-lg hover:bg-rose-950/40 transition-colors cursor-pointer"
              title="Cancel operation"
            >
              <XCircle className="w-3.5 h-3.5" />
              Cancel
            </button>
          )}
        </div>
      </div>

      <div className="w-full bg-[#111d38] rounded-full h-2.5 overflow-hidden">
        <div
          className="bg-gradient-to-r from-blue-600 via-teal-500 to-emerald-500 h-2.5 rounded-full transition-all duration-300 ease-out shadow-xs shadow-emerald-500/50"
          style={{ width: `${Math.min(100, Math.max(0, progressPercent))}%` }}
        />
      </div>

      {subLabel && (
        <p className="text-xs text-slate-400 italic flex items-center justify-between">
          <span>{subLabel}</span>
          <span className="text-[11px] text-emerald-400 font-mono">Offline CP-SAT engine</span>
        </p>
      )}
    </div>
  );
};
