import React, { useEffect } from "react";
import { CheckCircle2, AlertTriangle, Info, X, RotateCcw } from "lucide-react";

export type ToastType = "success" | "error" | "info" | "warning";

export interface ToastProps {
  id: string;
  message: string;
  type?: ToastType;
  duration?: number;
  onClose: (id: string) => void;
  onUndo?: () => void;
  undoLabel?: string;
}

export const Toast: React.FC<ToastProps> = ({
  id,
  message,
  type = "info",
  duration = 4000,
  onClose,
  onUndo,
  undoLabel = "Undo",
}) => {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => onClose(id), duration);
      return () => clearTimeout(timer);
    }
  }, [id, duration, onClose]);

  const icons = {
    success: <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />,
    error: <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />,
    warning: <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />,
    info: <Info className="w-4 h-4 text-cyan-400 shrink-0" />,
  }[type];

  const borders = {
    success: "border-emerald-500/40 bg-emerald-950/90 shadow-emerald-950/40",
    error: "border-rose-500/40 bg-rose-950/90 shadow-rose-950/40",
    warning: "border-amber-500/40 bg-amber-950/90 shadow-amber-950/40",
    info: "border-cyan-500/40 bg-[#0d1527]/95 shadow-cyan-950/40",
  }[type];

  return (
    <div
      role="alert"
      className={`flex items-center justify-between gap-3 px-4 py-3 rounded-2xl border text-xs sm:text-sm font-semibold text-white shadow-xl backdrop-blur-md transition-all animate-slide-up max-w-sm ${borders}`}
    >
      <div className="flex items-center gap-2.5">
        {icons}
        <span className="leading-snug">{message}</span>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {onUndo && (
          <button
            type="button"
            onClick={() => {
              onUndo();
              onClose(id);
            }}
            className="flex items-center gap-1 px-2 py-1 bg-white/10 hover:bg-white/20 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer"
          >
            <RotateCcw className="w-3 h-3" />
            <span>{undoLabel}</span>
          </button>
        )}

        <button
          type="button"
          onClick={() => onClose(id)}
          className="text-slate-400 hover:text-white p-0.5 rounded transition-colors"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
