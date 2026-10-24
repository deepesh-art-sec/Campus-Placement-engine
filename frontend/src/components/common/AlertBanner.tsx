import React from "react";
import { AlertCircle, CheckCircle2, AlertTriangle, Info, X } from "lucide-react";

interface AlertBannerProps {
  type?: "info" | "success" | "warning" | "danger";
  title?: string;
  message: string;
  onClose?: () => void;
  action?: React.ReactNode;
}

export const AlertBanner: React.FC<AlertBannerProps> = ({
  type = "info",
  title,
  message,
  onClose,
  action,
}) => {
  const styles = {
    info: {
      container: "bg-sky-950/60 border-sky-800/70 text-sky-200 shadow-xs shadow-sky-950/50",
      icon: <Info className="w-5 h-5 text-sky-400 shrink-0" />,
    },
    success: {
      container: "bg-emerald-950/60 border-emerald-800/70 text-emerald-200 shadow-xs shadow-emerald-950/50",
      icon: <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />,
    },
    warning: {
      container: "bg-amber-950/60 border-amber-800/70 text-amber-200 shadow-xs shadow-amber-950/50",
      icon: <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />,
    },
    danger: {
      container: "bg-rose-950/60 border-rose-800/70 text-rose-200 shadow-xs shadow-rose-950/50",
      icon: <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />,
    },
  };

  const current = styles[type];

  return (
    <div className={`p-4 rounded-xl border flex items-start gap-3.5 ${current.container}`}>
      {current.icon}
      <div className="flex-1 text-sm">
        {title && <h4 className="font-bold mb-0.5 text-white">{title}</h4>}
        <p className="leading-relaxed opacity-95">{message}</p>
        {action && <div className="mt-2">{action}</div>}
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white p-0.5 rounded transition-colors cursor-pointer"
          aria-label="Dismiss alert"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
