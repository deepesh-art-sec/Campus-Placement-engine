import React from "react";
import { GitBranch, Check, History } from "lucide-react";

interface VersionBadgeProps {
  version: string | number;
  status?: "active" | "draft" | "archived" | "superseded";
  timestamp?: string;
  onClick?: () => void;
  className?: string;
}

export const VersionBadge: React.FC<VersionBadgeProps> = ({
  version,
  status = "active",
  timestamp,
  onClick,
  className = "",
}) => {
  const formattedVersion = typeof version === "number" ? `v${version}.0` : version.startsWith("v") ? version : `v${version}`;

  const styles = {
    active: "bg-blue-50 text-blue-700 border-blue-200",
    draft: "bg-amber-50 text-amber-700 border-amber-200",
    archived: "bg-slate-100 text-slate-600 border-slate-200",
    superseded: "bg-purple-50 text-purple-700 border-purple-200",
  };

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!onClick}
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md font-mono text-[11px] font-semibold border ${
        styles[status]
      } ${onClick ? "cursor-pointer hover:brightness-95 active:scale-95" : "cursor-default"} ${className}`}
      title={timestamp ? `Created on ${timestamp}` : undefined}
    >
      <GitBranch className="w-3 h-3 opacity-70" />
      <span>{formattedVersion}</span>
      {status === "active" && (
        <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />
      )}
      <span className="capitalize text-[10px] opacity-80">({status})</span>
    </button>
  );
};
