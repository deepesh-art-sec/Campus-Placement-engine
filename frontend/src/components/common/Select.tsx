import React from "react";
import { ChevronDown } from "lucide-react";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: SelectOption[];
  error?: string;
  helperText?: string;
}

export const Select: React.FC<SelectProps> = ({
  label,
  options,
  error,
  helperText,
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

      <div className="relative">
        <select
          id={generatedId}
          disabled={disabled}
          className={`w-full appearance-none px-3.5 py-2.5 pr-10 bg-[var(--bg-input)] border rounded-xl text-xs sm:text-sm font-semibold text-white transition-all focus:outline-none focus:ring-2 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer ${
            error
              ? "border-rose-500 focus:border-rose-400 focus:ring-rose-500/20 text-rose-300"
              : "border-[var(--border-input)] focus:border-cyan-400 focus:ring-cyan-400/20"
          } ${className}`}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#0A1122] text-white">
              {opt.label}
            </option>
          ))}
        </select>

        <div className="absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
          <ChevronDown className="w-4 h-4" />
        </div>
      </div>

      {error ? (
        <p className="text-xs text-rose-400 font-semibold">{error}</p>
      ) : helperText ? (
        <p className="text-xs text-slate-400">{helperText}</p>
      ) : null}
    </div>
  );
};
