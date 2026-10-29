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
  const baseClasses = "bg-[#111e38]/80 animate-pulse rounded-xl border border-[#1b2b4d]/40";

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
          className={`p-5 rounded-2xl bg-[#0d1527] border border-[#1e3258] space-y-3 ${className}`}
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#111e38] animate-pulse" />
            <div className="space-y-1.5 flex-1">
              <div className="h-4 bg-[#111e38] rounded-md w-3/4 animate-pulse" />
              <div className="h-3 bg-[#111e38]/60 rounded-md w-1/2 animate-pulse" />
            </div>
          </div>
          <div className="h-16 bg-[#111e38]/40 rounded-xl animate-pulse" />
        </div>
      );
    }

    if (variant === "table-row") {
      return (
        <div
          key={key}
          className={`flex items-center gap-4 px-4 py-3 border-b border-[#1b2b4d] bg-[#080e1c] ${className}`}
        >
          <div className="h-3.5 bg-[#111e38] rounded w-20 animate-pulse" />
          <div className="h-3.5 bg-[#111e38] rounded w-36 animate-pulse" />
          <div className="h-3.5 bg-[#111e38] rounded w-24 animate-pulse" />
          <div className="h-3.5 bg-[#111e38] rounded w-16 animate-pulse" />
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
