import React from "react";
import { CheckCircle2, XCircle, AlertCircle, ArrowRight } from "lucide-react";

export type DecisionStatus = string;

export interface ReasonLineProps {
  status: DecisionStatus;
  statusText?: string;
  reason?: string;
  why?: string; // alias for reason
  action?: string; // "What to do next"
  whatNext?: string; // alias for action
  variant?: "success" | "danger" | "warning" | "neutral";
  className?: string;
}

export const ReasonLine: React.FC<ReasonLineProps> = ({
  status,
  statusText,
  reason,
  why,
  action,
  whatNext,
  variant,
  className = "",
}) => {
  const normStatus = (status || "").toLowerCase();
  const effectiveReason = reason || why || "";
  const effectiveAction = action || whatNext;

  const isPositive =
    variant === "success" ||
    normStatus === "eligible" ||
    normStatus === "allowed" ||
    normStatus.includes("active candidate");
  const isNegative =
    variant === "danger" ||
    normStatus === "ineligible" ||
    normStatus === "not eligible" ||
    normStatus === "blocked";

  const statusLabel = statusText || status;

  const getIcon = () => {
    if (isPositive) return <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />;
    if (isNegative) return <XCircle className="w-4 h-4 text-rose-400 shrink-0" />;
    return <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />;
  };

  const borderClasses = isPositive
    ? "border-emerald-500/30 bg-emerald-950/20 text-emerald-100"
    : isNegative
    ? "border-rose-500/30 bg-rose-950/20 text-rose-100"
    : "border-amber-500/30 bg-amber-950/20 text-amber-100";

  const badgeClasses = isPositive
    ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
    : isNegative
    ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
    : "bg-amber-500/20 text-amber-300 border-amber-500/40";

  return (
    <div className={`p-3.5 rounded-2xl border text-xs flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-sm ${borderClasses} ${className}`}>
      <div className="flex items-start sm:items-center gap-3">
        {getIcon()}
        <div className="flex flex-wrap items-center gap-2">
          <span className={`px-2 py-0.5 rounded-full font-mono text-[11px] font-bold border uppercase tracking-wider ${badgeClasses}`}>
            {statusLabel}
          </span>
          <span className="font-semibold text-slate-100">{effectiveReason}</span>
        </div>
      </div>

      {effectiveAction && (
        <div className="flex items-center gap-1.5 text-xs text-slate-300 bg-[#080e1c]/80 px-3 py-1.5 rounded-xl border border-[#1e3258] shrink-0">
          <span className="text-[10px] uppercase font-bold text-slate-500 font-mono">Next:</span>
          <span className="font-medium text-slate-200">{effectiveAction}</span>
          <ArrowRight className="w-3.5 h-3.5 text-cyan-400 ml-1" />
        </div>
      )}
    </div>
  );
};
