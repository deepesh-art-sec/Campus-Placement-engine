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
    <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
          <span className="text-sm font-bold text-slate-900">{label}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full">
            {Math.round(progressPercent)}%
          </span>
          {isCancellable && onCancel && (
            <button
              onClick={onCancel}
              className="text-xs flex items-center gap-1 text-slate-500 hover:text-rose-600 font-medium px-2 py-1 rounded-lg hover:bg-rose-50 transition-colors cursor-pointer"
              title="Cancel operation"
            >
              <XCircle className="w-3.5 h-3.5" />
              Cancel
            </button>
          )}
        </div>
      </div>

      <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
        <div
          className="bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-out shadow-xs shadow-blue-500/30"
          style={{ width: `${Math.min(100, Math.max(0, progressPercent))}%` }}
        />
      </div>

      {subLabel && (
        <p className="text-xs text-slate-500 italic flex items-center justify-between">
          <span>{subLabel}</span>
          <span className="text-[11px] text-blue-600 font-mono font-semibold">Deterministic scheduler engine</span>
        </p>
      )}
    </div>
  );
};
