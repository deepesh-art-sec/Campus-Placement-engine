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
          icon: <Database className="w-3 h-3 text-sky-600" />,
          color: "bg-sky-50 text-sky-700 border-sky-200",
        };
      case "csv_import":
        return {
          label: "CSV Upload",
          icon: <UploadCloud className="w-3 h-3 text-emerald-600" />,
          color: "bg-emerald-50 text-emerald-700 border-emerald-200",
        };
      case "coordinator_verified":
        return {
          label: "Coordinator Verified",
          icon: <UserCheck className="w-3 h-3 text-teal-600" />,
          color: "bg-teal-50 text-teal-700 border-teal-200",
        };
      case "officer_override":
        return {
          label: "Officer Override",
          icon: <ShieldAlert className="w-3 h-3 text-amber-600" />,
          color: "bg-amber-50 text-amber-700 border-amber-200",
        };
      case "self_reported":
        return {
          label: "Student Submission",
          icon: <UserCheck className="w-3 h-3 text-indigo-600" />,
          color: "bg-indigo-50 text-indigo-700 border-indigo-200",
        };
      default:
        return {
          label: norm.replace(/_/g, " "),
          icon: <Cpu className="w-3 h-3 text-blue-600" />,
          color: "bg-blue-50 text-blue-700 border-blue-200",
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
