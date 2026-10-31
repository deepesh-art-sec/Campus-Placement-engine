import React from "react";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "success" | "warning" | "danger" | "info" | "neutral" | "brand";
  size?: "sm" | "md";
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "neutral",
  size = "md",
  className = "",
}) => {
  const variantStyles = {
    success: "bg-emerald-950/80 text-emerald-300 border-emerald-700/60",
    warning: "bg-amber-950/80 text-amber-300 border-amber-700/60",
    danger: "bg-rose-950/80 text-rose-300 border-rose-700/60",
    info: "bg-cyan-950/80 text-cyan-300 border-cyan-700/60",
    neutral: "bg-[#0B1326] text-slate-300 border-[#16264C]",
    brand: "bg-blue-950/80 text-blue-300 border-blue-700/60",
  };

  const sizeStyles = {
    sm: "px-2 py-0.5 text-xs font-semibold",
    md: "px-2.5 py-1 text-xs font-bold",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {children}
    </span>
  );
};
