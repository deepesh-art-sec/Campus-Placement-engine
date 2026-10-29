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
    <div className={`bg-[#0d1527] border border-[#1e3258] rounded-2xl p-4 sm:p-5 space-y-4 text-slate-100 ${className}`}>
      {title && (
        <div className="flex items-center justify-between pb-3 border-b border-[#1b2b4d]">
          <h4 className="text-sm font-black text-white tracking-tight">{title}</h4>
          <span className="text-[10px] font-mono uppercase bg-[#080e1c] border border-[#1e3258] text-cyan-400 px-2 py-0.5 rounded-full font-bold">
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
                  className="p-3 bg-[#080e1c] border border-[#1b2b4d] rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                >
                  <span className="font-mono font-bold text-slate-400 uppercase text-[11px] min-w-[120px]">
                    {d.label || d.field}
                  </span>
                  <div className="flex items-center gap-3 font-mono flex-1 justify-end">
                    <span className="px-2.5 py-1 rounded bg-rose-950/40 text-rose-300 border border-rose-800/40 line-through">
                      {d.oldValue !== undefined ? String(d.oldValue) : "None"}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                    <span className={`px-2.5 py-1 rounded border font-bold ${
                      isChanged
                        ? "bg-emerald-950/50 text-emerald-300 border-emerald-600/50"
                        : "bg-slate-900 text-slate-400 border-slate-700"
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
          <div className="p-3 bg-[#080e1c] rounded-xl border border-rose-900/40 text-rose-200 space-y-1">
            <span className="text-[10px] text-rose-400 uppercase block font-bold">Previous Content</span>
            <pre className="whitespace-pre-wrap">{oldText || "Empty"}</pre>
          </div>
          <div className="p-3 bg-[#080e1c] rounded-xl border border-emerald-900/40 text-emerald-200 space-y-1">
            <span className="text-[10px] text-emerald-400 uppercase block font-bold">New Content</span>
            <pre className="whitespace-pre-wrap">{newText || "Empty"}</pre>
          </div>
        </div>
      )}
    </div>
  );
};
