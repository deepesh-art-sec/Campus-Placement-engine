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
  <div className={`p-4 sm:p-5 border-b border-[#1b2b4d] flex items-center justify-between gap-3 ${className}`}>
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
  <div className={`p-3 sm:p-4 bg-[#080e1c] border-t border-[#1b2b4d] text-xs text-slate-400 ${className}`}>
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
    emerald: "ring-1 ring-emerald-500/30 shadow-lg shadow-emerald-950/30",
    cyan: "ring-1 ring-cyan-500/30 shadow-lg shadow-cyan-950/30",
    blue: "ring-1 ring-blue-500/30 shadow-lg shadow-blue-950/30",
  }[glow];

  return (
    <div
      className={`bg-[#0d1527] border border-[#1e3258] rounded-2xl shadow-md text-slate-100 overflow-hidden ${glowClasses} ${className}`}
      {...props}
    >
      {(title || action) && (
        <div className="p-4 sm:p-5 border-b border-[#1b2b4d] flex items-center justify-between gap-3">
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
        <div className="p-3 sm:p-4 bg-[#080e1c] border-t border-[#1b2b4d] text-xs text-slate-400">
          {footer}
        </div>
      )}
    </div>
  );
};
