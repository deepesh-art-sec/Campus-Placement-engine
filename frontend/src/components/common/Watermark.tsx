import React from "react";
import { Shield, ExternalLink } from "lucide-react";

export const Watermark: React.FC = () => {
  return (
    <aside
      aria-label="Author Watermark"
      data-watermark="Made by Deepesh-art-sec"
      data-author="Deepesh-art-sec"
      data-repository="https://github.com/deepesh-art-sec/Campus-Placement-engine"
      className="fixed bottom-3 right-4 sm:bottom-4 sm:right-6 z-50 pointer-events-auto select-none print:hidden"
    >
      <a
        href="https://github.com/deepesh-art-sec"
        target="_blank"
        rel="noopener noreferrer"
        title="Engineered by Deepesh-art-sec (GitHub Profile)"
        className="group flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#080E1C]/90 hover:bg-[#0E1A38] backdrop-blur-md border border-cyan-500/40 hover:border-cyan-400 shadow-lg shadow-black/80 hover:shadow-cyan-500/25 transition-all duration-200 text-xs text-slate-200 hover:text-white"
      >
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
        </span>
        <Shield className="w-3.5 h-3.5 text-cyan-400 group-hover:scale-110 transition-transform" />
        <span className="text-[11px] font-mono font-bold tracking-tight">
          Made by <span className="text-cyan-400 font-extrabold group-hover:underline">Deepesh-art-sec</span>
        </span>
        <ExternalLink className="w-2.5 h-2.5 text-slate-400 group-hover:text-cyan-300 transition-colors" />
      </a>
    </aside>
  );
};

export default Watermark;
