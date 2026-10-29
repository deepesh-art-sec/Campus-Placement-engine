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
    active: "bg-cyan-950/70 text-cyan-300 border-cyan-600/50",
    draft: "bg-amber-950/70 text-amber-300 border-amber-600/50",
    archived: "bg-slate-900 text-slate-400 border-slate-700/50",
    superseded: "bg-purple-950/70 text-purple-300 border-purple-600/50",
  };

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!onClick}
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md font-mono text-[11px] font-semibold border ${
        styles[status]
      } ${onClick ? "cursor-pointer hover:brightness-110 active:scale-95" : "cursor-default"} ${className}`}
      title={timestamp ? `Created on ${timestamp}` : undefined}
    >
      <GitBranch className="w-3 h-3 opacity-70" />
      <span>{formattedVersion}</span>
      {status === "active" && (
        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
      )}
      <span className="capitalize text-[10px] opacity-80">({status})</span>
    </button>
  );
};
