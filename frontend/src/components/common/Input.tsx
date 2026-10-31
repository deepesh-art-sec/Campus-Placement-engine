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
          <div className="absolute left-3.5 pointer-events-none text-cyan-400 opacity-70">
            {leftIcon}
          </div>
        )}

        <input
          id={generatedId}
          disabled={disabled}
          className={`w-full py-2.5 bg-[var(--bg-input)] border rounded-xl text-xs sm:text-sm font-semibold text-white placeholder-slate-500 transition-all focus:outline-none focus:ring-2 disabled:opacity-40 disabled:cursor-not-allowed ${
            leftIcon ? "pl-10" : "px-3.5"
          } ${rightIcon ? "pr-10" : "px-3.5"} ${
            error
              ? "border-rose-500 focus:border-rose-400 focus:ring-rose-500/20 text-rose-300"
              : "border-[var(--border-input)] focus:border-cyan-400 focus:ring-cyan-400/20"
          } ${className}`}
          {...props}
        />

        {rightIcon && (
          <div className="absolute right-3.5 pointer-events-none text-slate-400">
            {rightIcon}
          </div>
        )}
      </div>

      {error ? (
        <p className="text-xs text-rose-400 font-semibold">{error}</p>
      ) : helperText ? (
        <p className="text-xs text-slate-400">{helperText}</p>
      ) : null}
    </div>
  );
};
