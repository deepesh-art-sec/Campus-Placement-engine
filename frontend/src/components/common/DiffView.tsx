import React from "react";
import { ArrowRight, Check, Minus, Plus } from "lucide-react";

export interface DiffEntry {
  field: string;
  label?: string;
  oldValue: any;
  newValue: any;
}

export interface DiffViewProps {
  title?: string;
  diffs?: DiffEntry[];
  before?: Record<string, any>;
  after?: Record<string, any>;
  oldText?: string;
  newText?: string;
  mode?: "fields" | "text";
  className?: string;
}

export const DiffView: React.FC<DiffViewProps> = ({
  title,
  diffs = [],
  before,
  after,
  oldText,
  newText,
  mode = "fields",
  className = "",
}) => {
  const effectiveDiffs: DiffEntry[] = React.useMemo(() => {
    if (diffs && diffs.length > 0) return diffs;
    if (!before && !after) return [];
    const keys = Array.from(new Set([...Object.keys(before || {}), ...Object.keys(after || {})]));
    return keys.map((k) => ({
      field: k,
      label: k.replace(/_/g, " ").toUpperCase(),
      oldValue: before ? before[k] : undefined,
      newValue: after ? after[k] : undefined,
    }));
  }, [diffs, before, after]);

  return (
    <div className={`bg-white border border-slate-200/90 rounded-2xl p-4 sm:p-5 space-y-4 text-slate-800 shadow-sm ${className}`}>
      {title && (
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <h4 className="text-sm font-black text-slate-900 tracking-tight">{title}</h4>
          <span className="text-[10px] font-mono uppercase bg-blue-50 border border-blue-200 text-blue-700 px-2.5 py-0.5 rounded-full font-bold">
            Audit Diff
          </span>
        </div>
      )}

      {mode === "fields" ? (
        <div className="space-y-2.5">
          {effectiveDiffs.length === 0 ? (
            <p className="text-xs text-slate-500 py-2 text-center">No field differences detected.</p>
          ) : (
            effectiveDiffs.map((d, idx) => {
              const isChanged = String(d.oldValue) !== String(d.newValue);
              return (
                <div
                  key={idx}
                  className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                >
                  <span className="font-mono font-bold text-slate-500 uppercase text-[11px] min-w-[120px]">
                    {d.label || d.field}
                  </span>
                  <div className="flex items-center gap-3 font-mono flex-1 justify-end">
                    <span className="px-2.5 py-1 rounded bg-rose-50 text-rose-700 border border-rose-200 line-through">
                      {d.oldValue !== undefined ? String(d.oldValue) : "None"}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span className={`px-2.5 py-1 rounded border font-bold ${
                      isChanged
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                        : "bg-slate-100 text-slate-600 border-slate-200"
                    }`}>
                      {d.newValue !== undefined ? String(d.newValue) : "None"}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 font-mono text-xs">
          <div className="p-3 bg-rose-50/50 rounded-xl border border-rose-200 text-rose-900 space-y-1">
            <span className="text-[10px] text-rose-600 uppercase block font-bold">Previous Content</span>
            <pre className="whitespace-pre-wrap">{oldText || "Empty"}</pre>
          </div>
          <div className="p-3 bg-emerald-50/50 rounded-xl border border-emerald-200 text-emerald-900 space-y-1">
            <span className="text-[10px] text-emerald-600 uppercase block font-bold">New Content</span>
            <pre className="whitespace-pre-wrap">{newText || "Empty"}</pre>
          </div>
        </div>
      )}
    </div>
  );
};
