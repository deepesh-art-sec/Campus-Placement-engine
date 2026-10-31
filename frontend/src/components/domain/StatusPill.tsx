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
          bg: "bg-emerald-50",
          text: "text-emerald-700",
          border: "border-emerald-200",
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />,
          dot: "bg-emerald-500",
        };
      case "NOT_ELIGIBLE":
      case "REJECTED":
      case "BLOCKED":
      case "ABSENT":
      case "CANCELLED":
        return {
          bg: "bg-rose-50",
          text: "text-rose-700",
          border: "border-rose-200",
          icon: <XCircle className="w-3.5 h-3.5 text-rose-600" />,
          dot: "bg-rose-500",
        };
      case "PENDING":
      case "PENDING_REVIEW":
      case "IN_PROGRESS":
      case "LATE":
        return {
          bg: "bg-amber-50",
          text: "text-amber-700",
          border: "border-amber-200",
          icon: <Clock className="w-3.5 h-3.5 text-amber-600" />,
          dot: "bg-amber-500",
        };
      case "OVERRIDDEN":
      case "APPLIED":
      case "OFFERED":
        return {
          bg: "bg-blue-50",
          text: "text-blue-700",
          border: "border-blue-200",
          icon: <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />,
          dot: "bg-blue-500",
        };
      case "DRAFT":
      case "OPTED_OUT":
      default:
        return {
          bg: "bg-slate-100",
          text: "text-slate-700",
          border: "border-slate-200",
          icon: <Slash className="w-3.5 h-3.5 text-slate-500" />,
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
