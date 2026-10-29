import React from "react";
import { Database, UploadCloud, UserCheck, ShieldAlert, Cpu } from "lucide-react";

export type ProvenanceSource =
  | "erp"
  | "csv_import"
  | "self_reported"
  | "coordinator_verified"
  | "officer_override"
  | "engine_generated";

interface SourceBadgeProps {
  source: ProvenanceSource | string;
  timestamp?: string;
  className?: string;
}

export const SourceBadge: React.FC<SourceBadgeProps> = ({
  source,
  timestamp,
  className = "",
}) => {
  const norm = source.toLowerCase();

  const getDetails = () => {
    switch (norm) {
      case "erp":
        return {
          label: "College ERP",
          icon: <Database className="w-3 h-3 text-cyan-400" />,
          color: "bg-cyan-950/70 text-cyan-300 border-cyan-800/60",
        };
      case "csv_import":
        return {
          label: "CSV Upload",
          icon: <UploadCloud className="w-3 h-3 text-emerald-400" />,
          color: "bg-emerald-950/70 text-emerald-300 border-emerald-800/60",
        };
      case "coordinator_verified":
        return {
          label: "Coordinator Verified",
          icon: <UserCheck className="w-3 h-3 text-teal-400" />,
          color: "bg-teal-950/70 text-teal-300 border-teal-800/60",
        };
      case "officer_override":
        return {
          label: "Officer Override",
          icon: <ShieldAlert className="w-3 h-3 text-amber-400" />,
          color: "bg-amber-950/70 text-amber-300 border-amber-800/60",
        };
      case "self_reported":
        return {
          label: "Student Submission",
          icon: <UserCheck className="w-3 h-3 text-indigo-400" />,
          color: "bg-indigo-950/70 text-indigo-300 border-indigo-800/60",
        };
      default:
        return {
          label: norm.replace(/_/g, " "),
          icon: <Cpu className="w-3 h-3 text-slate-400" />,
          color: "bg-slate-900 text-slate-300 border-slate-700/60",
        };
    }
  };

  const info = getDetails();

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md font-mono text-[10px] uppercase font-bold border ${info.color} ${className}`}
      title={timestamp ? `Ingested at ${timestamp}` : undefined}
    >
      {info.icon}
      <span>{info.label}</span>
    </span>
  );
};
