import React from "react";

export interface SkeletonProps {
  variant?: "text" | "rectangular" | "circular" | "card" | "table-row";
  width?: string | number;
  height?: string | number;
  className?: string;
  count?: number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  variant = "rectangular",
  width,
  height,
  className = "",
  count = 1,
}) => {
  const baseClasses = "bg-slate-200 animate-pulse rounded-xl border border-slate-200/60";

  const renderSingle = (key: number) => {
    if (variant === "text") {
      return (
        <div
          key={key}
          style={{ width: width || "100%", height: height || "1rem" }}
          className={`${baseClasses} rounded-md ${className}`}
        />
      );
    }

    if (variant === "circular") {
      return (
        <div
          key={key}
          style={{ width: width || "2.5rem", height: height || "2.5rem" }}
          className={`${baseClasses} rounded-full ${className}`}
        />
      );
    }

    if (variant === "card") {
      return (
        <div
          key={key}
          className={`p-5 rounded-2xl bg-white border border-slate-200 space-y-3 shadow-xs ${className}`}
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-slate-200 animate-pulse" />
            <div className="space-y-1.5 flex-1">
              <div className="h-4 bg-slate-200 rounded-md w-3/4 animate-pulse" />
              <div className="h-3 bg-slate-200/60 rounded-md w-1/2 animate-pulse" />
            </div>
          </div>
          <div className="h-16 bg-slate-100 rounded-xl animate-pulse" />
        </div>
      );
    }

    if (variant === "table-row") {
      return (
        <div
          key={key}
          className={`flex items-center gap-4 px-4 py-3 border-b border-slate-100 bg-white ${className}`}
        >
          <div className="h-3.5 bg-slate-200 rounded w-20 animate-pulse" />
          <div className="h-3.5 bg-slate-200 rounded w-36 animate-pulse" />
          <div className="h-3.5 bg-slate-200 rounded w-24 animate-pulse" />
          <div className="h-3.5 bg-slate-200 rounded w-16 animate-pulse" />
        </div>
      );
    }

    return (
      <div
        key={key}
        style={{ width: width || "100%", height: height || "2.5rem" }}
        className={`${baseClasses} ${className}`}
      />
    );
  };

  return (
    <>
      {Array.from({ length: count }).map((_, i) => renderSingle(i))}
    </>
  );
};
