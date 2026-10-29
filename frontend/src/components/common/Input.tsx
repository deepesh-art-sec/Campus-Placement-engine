import React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  helperText,
  leftIcon,
  rightIcon,
  id,
  className = "",
  disabled,
  ...props
}) => {
  const generatedId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

  return (
    <div className="w-full space-y-1.5 text-left">
      {label && (
        <label
          htmlFor={generatedId}
          className="block text-xs font-bold uppercase tracking-wider text-slate-300"
        >
          {label}
        </label>
      )}

      <div className="relative flex items-center">
        {leftIcon && (
          <div className="absolute left-3.5 pointer-events-none text-slate-400">
            {leftIcon}
          </div>
        )}

        <input
          id={generatedId}
          disabled={disabled}
          className={`w-full py-2.5 bg-[#080e1c] border rounded-xl text-xs sm:text-sm font-semibold text-white placeholder-slate-500 transition-all focus:bg-[#0d1527] focus:outline-none focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed ${
            leftIcon ? "pl-10" : "px-3.5"
          } ${rightIcon ? "pr-10" : "px-3.5"} ${
            error
              ? "border-rose-500/80 focus:border-rose-500 focus:ring-rose-500/30 text-rose-200"
              : "border-[#1e3258] focus:border-emerald-500 focus:ring-emerald-500/30"
          } ${className}`}
          {...props}
        />

        {rightIcon && (
          <div className="absolute right-3.5 text-slate-400">
            {rightIcon}
          </div>
        )}
      </div>

      {error ? (
        <p className="text-xs font-medium text-rose-400 mt-1">{error}</p>
      ) : helperText ? (
        <p className="text-[11px] text-slate-400 mt-1">{helperText}</p>
      ) : null}
    </div>
  );
};
