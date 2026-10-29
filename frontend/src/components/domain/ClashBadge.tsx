import React from "react";
import { CheckCircle2, AlertOctagon, HelpCircle } from "lucide-react";

interface ClashBadgeProps {
  clashCount?: number;
  label?: string;
  onClick?: () => void;
  className?: string;
}

export const ClashBadge: React.FC<ClashBadgeProps> = ({
  clashCount = 0,
  label,
  onClick,
  className = "",
}) => {
  const isZero = clashCount === 0;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!onClick}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-bold transition-all ${
        isZero
          ? "bg-emerald-950/80 text-emerald-300 border border-emerald-600/50 shadow-sm shadow-emerald-950/50"
          : "bg-rose-950/80 text-rose-300 border border-rose-600/60 animate-pulse shadow-sm shadow-rose-950/50"
      } ${onClick ? "cursor-pointer hover:brightness-110 active:scale-95" : "cursor-default"} ${className}`}
      title={
        isZero
          ? "Verified: No room or time overlap across candidate interviews"
          : `Warning: ${clashCount} scheduling overlap${clashCount > 1 ? "s" : ""} detected`
      }
    >
      {isZero ? (
        <>
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>{label || "0 Clashes Verified"}</span>
        </>
      ) : (
        <>
          <AlertOctagon className="w-3.5 h-3.5 text-rose-400" />
          <span>{label || `${clashCount} Clash${clashCount > 1 ? "es" : ""} Detected`}</span>
        </>
      )}
    </button>
  );
};
