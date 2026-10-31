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
    if (isPositive) return <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />;
    if (isNegative) return <XCircle className="w-4 h-4 text-rose-600 shrink-0" />;
    return <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />;
  };

  const borderClasses = isPositive
    ? "border-emerald-200 bg-emerald-50/70 text-emerald-950"
    : isNegative
    ? "border-rose-200 bg-rose-50/70 text-rose-950"
    : "border-amber-200 bg-amber-50/70 text-amber-950";

  const badgeClasses = isPositive
    ? "bg-emerald-100 text-emerald-800 border-emerald-300"
    : isNegative
    ? "bg-rose-100 text-rose-800 border-rose-300"
    : "bg-amber-100 text-amber-800 border-amber-300";

  return (
    <div className={`p-3.5 rounded-2xl border text-xs flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-xs ${borderClasses} ${className}`}>
      <div className="flex items-start sm:items-center gap-3">
        {getIcon()}
        <div className="flex flex-wrap items-center gap-2">
          <span className={`px-2.5 py-0.5 rounded-full font-mono text-[11px] font-bold border uppercase tracking-wider ${badgeClasses}`}>
            {statusLabel}
          </span>
          <span className="font-semibold text-slate-800">{effectiveReason}</span>
        </div>
      </div>

      {effectiveAction && (
        <div className="flex items-center gap-1.5 text-xs text-slate-700 bg-white px-3 py-1.5 rounded-xl border border-slate-200 shadow-xs shrink-0">
          <span className="text-[10px] uppercase font-bold text-slate-500 font-mono">Next:</span>
          <span className="font-medium text-slate-800">{effectiveAction}</span>
          <ArrowRight className="w-3.5 h-3.5 text-blue-600 ml-1" />
        </div>
      )}
    </div>
  );
};
