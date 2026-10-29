import React from "react";
import { CheckCircle2, XCircle, AlertTriangle, Clock, ShieldCheck, RefreshCw, Slash, Check } from "lucide-react";

export type EngineStatus =
  | "ELIGIBLE"
  | "NOT_ELIGIBLE"
  | "OVERRIDDEN"
  | "PENDING"
  | "DRAFT"
  | "PUBLISHED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED"
  | "PENDING_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "APPLIED"
  | "OFFERED"
  | "ACCEPTED"
  | "OPTED_OUT"
  | "BLOCKED"
  | "PRESENT"
  | "ABSENT"
  | "LATE";

interface StatusPillProps {
  status: EngineStatus | string;
  label?: string;
  size?: "sm" | "md" | "lg";
  showIcon?: boolean;
  className?: string;
}

export const StatusPill: React.FC<StatusPillProps> = ({
  status,
  label,
  size = "md",
  showIcon = true,
  className = "",
}) => {
  const normStatus = (status || "").toUpperCase();

  const getStyleAndIcon = () => {
    switch (normStatus) {
      case "ELIGIBLE":
      case "APPROVED":
      case "ACCEPTED":
      case "PRESENT":
      case "PUBLISHED":
      case "COMPLETED":
        return {
          bg: "bg-emerald-950/60",
          text: "text-emerald-300",
          border: "border-emerald-700/60",
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />,
          dot: "bg-emerald-400",
        };
      case "NOT_ELIGIBLE":
      case "REJECTED":
      case "BLOCKED":
      case "ABSENT":
      case "CANCELLED":
        return {
          bg: "bg-rose-950/60",
          text: "text-rose-300",
          border: "border-rose-700/60",
          icon: <XCircle className="w-3.5 h-3.5 text-rose-400" />,
          dot: "bg-rose-400",
        };
      case "PENDING":
      case "PENDING_REVIEW":
      case "IN_PROGRESS":
      case "LATE":
        return {
          bg: "bg-amber-950/60",
          text: "text-amber-300",
          border: "border-amber-700/60",
          icon: <Clock className="w-3.5 h-3.5 text-amber-400" />,
          dot: "bg-amber-400",
        };
      case "OVERRIDDEN":
      case "APPLIED":
      case "OFFERED":
        return {
          bg: "bg-blue-950/60",
          text: "text-blue-300",
          border: "border-blue-700/60",
          icon: <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />,
          dot: "bg-blue-400",
        };
      case "DRAFT":
      case "OPTED_OUT":
      default:
        return {
          bg: "bg-slate-900/80",
          text: "text-slate-300",
          border: "border-slate-700/60",
          icon: <Slash className="w-3.5 h-3.5 text-slate-400" />,
          dot: "bg-slate-400",
        };
    }
  };

  const config = getStyleAndIcon();
  const displayLabel = label || normStatus.replace(/_/g, " ");

  const sizeClasses = {
    sm: "text-[10px] px-2 py-0.5 gap-1",
    md: "text-xs px-2.5 py-1 gap-1.5",
    lg: "text-sm px-3.5 py-1.5 gap-2 font-bold",
  };

  return (
    <span
      className={`inline-flex items-center font-mono font-semibold rounded-full border ${config.bg} ${config.text} ${config.border} ${sizeClasses[size]} ${className}`}
    >
      {showIcon && config.icon}
      <span>{displayLabel}</span>
    </span>
  );
};
