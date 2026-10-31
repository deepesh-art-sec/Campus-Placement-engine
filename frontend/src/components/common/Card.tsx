import React from "react";

export interface CardHeaderProps {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  children?: React.ReactNode;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  title,
  subtitle,
  action,
  className = "",
  children,
}) => (
  <div className={`p-4 sm:p-5 border-b border-[var(--border-card)] flex items-center justify-between gap-3 ${className}`}>
    <div>
      {typeof title === "string" ? (
        <h3 className="text-base font-black text-white tracking-tight">{title}</h3>
      ) : (
        title
      )}
      {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
      {children}
    </div>
    {action && <div className="shrink-0">{action}</div>}
  </div>
);

export const CardBody: React.FC<{ className?: string; children?: React.ReactNode }> = ({
  className = "",
  children,
}) => <div className={`p-4 sm:p-5 ${className}`}>{children}</div>;

export const CardFooter: React.FC<{ className?: string; children?: React.ReactNode }> = ({
  className = "",
  children,
}) => (
  <div className={`p-3 sm:p-4 bg-[var(--bg-input)] border-t border-[var(--border-card)] text-xs text-slate-400 ${className}`}>
    {children}
  </div>
);

export interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  footer?: React.ReactNode;
  glow?: "none" | "emerald" | "cyan" | "blue";
}

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  action,
  footer,
  children,
  glow = "none",
  className = "",
  ...props
}) => {
  const glowClasses = {
    none: "",
    emerald: "ring-1 ring-emerald-500/40 shadow-lg shadow-emerald-950/50",
    cyan: "ring-1 ring-cyan-500/40 shadow-lg shadow-cyan-950/50",
    blue: "ring-1 ring-blue-500/40 shadow-lg shadow-blue-950/50",
  }[glow];

  return (
    <div
      className={`corporate-card overflow-hidden text-slate-100 ${glowClasses} ${className}`}
      {...props}
    >
      {(title || action) && (
        <div className="p-4 sm:p-5 border-b border-[var(--border-card)] flex items-center justify-between gap-3">
          <div>
            {typeof title === "string" ? (
              <h3 className="text-base font-black text-white tracking-tight">{title}</h3>
            ) : (
              title
            )}
            {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}

      {children}

      {footer && (
        <div className="p-3 sm:p-4 bg-[var(--bg-input)] border-t border-[var(--border-card)] text-xs text-slate-400">
          {footer}
        </div>
      )}
    </div>
  );
};
