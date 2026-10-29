import React from "react";
import { CircleDot } from "lucide-react";

export interface TimelineEvent {
  id: string;
  title: string;
  subtitle?: string;
  description?: string;
  timestamp: string;
  tag?: string;
  actor?: string;
  type?: string;
  tagColor?: "brand" | "emerald" | "amber" | "rose" | "cyan";
  icon?: React.ReactNode;
  content?: React.ReactNode;
}

export type TimelineItem = TimelineEvent;

export interface TimelineProps {
  items?: TimelineItem[];
  events?: TimelineEvent[];
  className?: string;
}

export const Timeline: React.FC<TimelineProps> = ({ items, events, className = "" }) => {
  const effectiveItems = events || items || [];

  const tagColorClasses = {
    brand: "bg-blue-950/80 text-blue-300 border-blue-800/50",
    emerald: "bg-emerald-950/80 text-emerald-300 border-emerald-800/50",
    amber: "bg-amber-950/80 text-amber-300 border-amber-800/50",
    rose: "bg-rose-950/80 text-rose-300 border-rose-800/50",
    cyan: "bg-cyan-950/80 text-cyan-300 border-cyan-800/50",
  };

  return (
    <div className={`relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-[#1b2b4d] ${className}`}>
      {effectiveItems.map((item) => (
        <div key={item.id} className="relative group">
          {/* Node Icon / Bullet */}
          <div className="absolute -left-[27px] top-1 w-5 h-5 rounded-full bg-[#0d1527] border-2 border-emerald-500 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition-transform shadow-sm shadow-emerald-950">
            {item.icon || <CircleDot className="w-2.5 h-2.5 fill-current" />}
          </div>

          <div className="bg-[#080e1c] border border-[#1e3258] rounded-2xl p-4 shadow-sm space-y-2 hover:border-emerald-500/40 transition-colors">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-bold text-white tracking-tight">{item.title}</h4>
                {item.tag && (
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider ${
                      tagColorClasses[item.tagColor || "brand"]
                    }`}
                  >
                    {item.tag}
                  </span>
                )}
              </div>
              <span className="text-[11px] font-mono text-slate-500 shrink-0">
                {item.timestamp}
              </span>
            </div>

            {(item.description || item.subtitle) && (
              <p className="text-xs text-slate-300 font-medium leading-relaxed">
                {item.description || item.subtitle}
              </p>
            )}

            {item.actor && (
              <div className="text-[10px] font-mono text-cyan-400 pt-1 border-t border-[#1e3258]/60">
                Actor: {item.actor}
              </div>
            )}

            {item.content}
          </div>
        </div>
      ))}
    </div>
  );
};
