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
    brand: "bg-blue-50 text-blue-700 border-blue-200",
    emerald: "bg-emerald-50 text-emerald-700 border-emerald-200",
    amber: "bg-amber-50 text-amber-700 border-amber-200",
    rose: "bg-rose-50 text-rose-700 border-rose-200",
    cyan: "bg-sky-50 text-sky-700 border-sky-200",
  };

  return (
    <div className={`relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 ${className}`}>
      {effectiveItems.map((item) => (
        <div key={item.id} className="relative group">
          {/* Node Icon / Bullet */}
          <div className="absolute -left-[27px] top-1 w-5 h-5 rounded-full bg-white border-2 border-blue-600 flex items-center justify-center text-blue-600 group-hover:scale-110 transition-transform shadow-xs">
            {item.icon || <CircleDot className="w-2.5 h-2.5 fill-current" />}
          </div>

          <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-sm space-y-2 hover:border-blue-300 transition-colors">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-bold text-slate-900 tracking-tight">{item.title}</h4>
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
              <span className="text-[11px] font-mono text-slate-400 shrink-0">
                {item.timestamp}
              </span>
            </div>

            {(item.description || item.subtitle) && (
              <p className="text-xs text-slate-600 font-medium leading-relaxed">
                {item.description || item.subtitle}
              </p>
            )}

            {item.actor && (
              <div className="text-[10px] font-mono text-blue-600 pt-1 border-t border-slate-100">
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
