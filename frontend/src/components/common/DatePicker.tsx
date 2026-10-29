import React from "react";
import { Calendar } from "lucide-react";

export interface DatePickerProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange"> {
  label?: string;
  error?: string;
  helperText?: string;
  showPresets?: boolean;
  onPresetSelect?: (dateStr: string) => void;
  onChange?: (val: string) => void;
}

export const DatePicker: React.FC<DatePickerProps> = ({
  label,
  error,
  helperText,
  value,
  onChange,
  showPresets = false,
  onPresetSelect,
  id,
  className = "",
  disabled,
  ...props
}) => {
  const generatedId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

  const getPresetDate = (daysAhead: number) => {
    const d = new Date();
    d.setDate(d.getDate() + daysAhead);
    return d.toISOString().split("T")[0];
  };

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
        <div className="absolute left-3.5 pointer-events-none text-cyan-400">
          <Calendar className="w-4 h-4" />
        </div>

        <input
          type="date"
          id={generatedId}
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          disabled={disabled}
          className={`w-full pl-10 pr-4 py-2.5 bg-[#080e1c] border rounded-xl text-xs sm:text-sm font-semibold text-white transition-all focus:bg-[#0d1527] focus:outline-none focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed [color-scheme:dark] ${
            error
              ? "border-rose-500/80 focus:border-rose-500 focus:ring-rose-500/30 text-rose-200"
              : "border-[#1e3258] focus:border-emerald-500 focus:ring-emerald-500/30"
          } ${className}`}
          {...props}
        />
      </div>

      {showPresets && onPresetSelect && !disabled && (
        <div className="flex items-center gap-1.5 pt-1">
          <button
            type="button"
            onClick={() => onPresetSelect(getPresetDate(0))}
            className="px-2 py-0.5 rounded-md text-[10.5px] font-semibold bg-[#111d38] hover:bg-[#17264a] text-slate-300 hover:text-white border border-[#1e3258] transition-colors"
          >
            Today
          </button>
          <button
            type="button"
            onClick={() => onPresetSelect(getPresetDate(1))}
            className="px-2 py-0.5 rounded-md text-[10.5px] font-semibold bg-[#111d38] hover:bg-[#17264a] text-slate-300 hover:text-white border border-[#1e3258] transition-colors"
          >
            Tomorrow
          </button>
          <button
            type="button"
            onClick={() => onPresetSelect(getPresetDate(7))}
            className="px-2 py-0.5 rounded-md text-[10.5px] font-semibold bg-[#111d38] hover:bg-[#17264a] text-slate-300 hover:text-white border border-[#1e3258] transition-colors"
          >
            +7 Days
          </button>
        </div>
      )}

      {error ? (
        <p className="text-xs font-medium text-rose-400 mt-1">{error}</p>
      ) : helperText ? (
        <p className="text-[11px] text-slate-400 mt-1">{helperText}</p>
      ) : null}
    </div>
  );
};
