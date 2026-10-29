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
    "inline-flex items-center justify-center font-bold transition-all rounded-xl cursor-pointer select-none focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[#060b14] disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none";

  const sizeClasses = {
    sm: "px-3 py-1.5 text-xs min-h-[36px] sm:min-h-[32px] gap-1.5",
    md: "px-4 py-2 text-xs sm:text-sm min-h-[44px] gap-2", // Mobile touch target >= 44px
    lg: "px-6 py-3 text-sm sm:text-base min-h-[48px] gap-2.5",
  }[size];

  const variantClasses = {
    primary:
      "bg-gradient-to-r from-blue-700 via-teal-600 to-emerald-600 hover:from-blue-600 hover:via-teal-500 hover:to-emerald-500 text-white border border-emerald-400/30 shadow-md shadow-emerald-950/40 focus:ring-emerald-500",
    secondary:
      "bg-[#111d38] hover:bg-[#17264a] text-slate-100 border border-[#1e3258] hover:border-emerald-500/50 shadow-sm focus:ring-blue-500",
    emerald:
      "bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white border border-emerald-400/40 shadow-md shadow-emerald-950/40 focus:ring-emerald-400",
    danger:
      "bg-gradient-to-r from-rose-700 to-red-600 hover:from-rose-600 hover:to-red-500 text-white border border-rose-400/30 shadow-md shadow-rose-950/40 focus:ring-rose-500",
    outline:
      "bg-transparent hover:bg-[#111d38] text-slate-300 hover:text-white border border-[#1e3258] hover:border-slate-500 focus:ring-slate-400",
    ghost:
      "bg-transparent hover:bg-[#111d38]/80 text-slate-400 hover:text-white border border-transparent focus:ring-slate-500",
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
      {!loading && icon && iconPosition === "right" && <span className="shrink-0">{icon}</span>}
    </button>
  );
};
