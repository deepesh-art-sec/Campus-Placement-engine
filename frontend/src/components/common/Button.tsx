import React from "react";
import { Loader2 } from "lucide-react";

export type ButtonVariant = "primary" | "secondary" | "emerald" | "danger" | "outline" | "ghost";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  icon,
  iconPosition = "left",
  className = "",
  ...props
}) => {
  const baseClasses =
    "inline-flex items-center justify-center font-semibold transition-all rounded-xl cursor-pointer select-none focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[#060B16] disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none";

  const sizeClasses = {
    sm: "px-3 py-1.5 text-xs min-h-[36px] sm:min-h-[32px] gap-1.5",
    md: "px-4 py-2 text-xs sm:text-sm min-h-[44px] gap-2",
    lg: "px-6 py-3 text-sm sm:text-base min-h-[48px] gap-2.5",
  }[size];

  const variantClasses = {
    primary:
      "bg-[#2563EB] hover:bg-[#1D4ED8] active:bg-[#1E40AF] text-white shadow-md shadow-blue-600/30 focus:ring-cyan-400",
    secondary:
      "bg-[var(--bg-input)] hover:bg-[var(--bg-card-hover)] text-slate-200 hover:text-white border border-[var(--border-card)] hover:border-cyan-400/60 shadow-xs focus:ring-cyan-400",
    emerald:
      "bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white shadow-md shadow-emerald-600/30 focus:ring-emerald-500",
    danger:
      "bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white shadow-md shadow-rose-600/30 focus:ring-rose-500",
    outline:
      "bg-transparent hover:bg-white/5 text-slate-200 hover:text-white border border-[var(--border-card)] hover:border-cyan-400 focus:ring-cyan-400",
    ghost:
      "bg-transparent hover:bg-white/10 text-slate-300 hover:text-white border border-transparent focus:ring-slate-400",
  }[variant];

  return (
    <button
      disabled={disabled || loading}
      className={`${baseClasses} ${sizeClasses} ${variantClasses} ${className}`}
      {...props}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin text-current shrink-0" />
      ) : (
        icon && iconPosition === "left" && <span className="shrink-0">{icon}</span>
      )}
      <span>{children}</span>
      {!loading && icon && iconPosition === "right" && (
        <span className="shrink-0">{icon}</span>
      )}
    </button>
  );
};
