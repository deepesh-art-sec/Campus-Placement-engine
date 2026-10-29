import React from "react";
import {
  LogOut,
  HelpCircle,
  Cpu,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

interface HeaderProps {
  onOpenTour?: () => void;
  onNavigateToAudit?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenTour }) => {
  const { user, logout } = useAuth();

  return (
    <header className="bg-[#080e1c]/95 backdrop-blur-md border-b border-[#1b2b4d] sticky top-0 z-30 shadow-md no-print transition-all shrink-0">
      {/* Main Header Bar */}
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 h-14 sm:h-16 flex items-center justify-between gap-2 overflow-hidden">
        <div className="flex items-center gap-2 sm:gap-3.5 min-w-0">
          <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl sm:rounded-2xl bg-gradient-to-tr from-blue-700 via-teal-600 to-emerald-500 flex items-center justify-center text-white font-black text-sm sm:text-lg shadow-md shadow-emerald-500/20 ring-2 ring-emerald-500/20 shrink-0">
            PE
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 sm:gap-2">
              <span className="font-black text-white text-sm sm:text-base tracking-tight truncate">
                <span className="hidden xs:inline">PLACEMENT ENGINE</span>
                <span className="xs:hidden">ENGINE</span>
              </span>
              <span className="text-[9px] sm:text-[10px] font-black tracking-wider px-1.5 sm:px-2 py-0.5 bg-blue-950/80 text-blue-300 border border-blue-800/60 rounded-full hidden sm:inline-block">
                ENTERPRISE
              </span>
              <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 rounded-full hidden md:inline-flex items-center gap-1">
                <Cpu className="w-3 h-3 text-emerald-400" />
                CP-SAT Verified
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium hidden md:block truncate">
              Institutional Placement Eligibility, Policy & Clash-Free Scheduling Engine
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
          {onOpenTour && user?.role === "officer" && (
            <button
              type="button"
              onClick={onOpenTour}
              className="flex items-center gap-1.5 text-xs font-bold text-slate-200 hover:text-emerald-300 bg-[#111d38] hover:bg-[#162447] px-2.5 sm:px-3 py-1.5 rounded-xl transition-all border border-[#1b2b4d] hover:border-emerald-500/40 cursor-pointer shadow-xs"
              title="Open guided walkthrough tour"
            >
              <HelpCircle className="w-4 h-4 text-emerald-400" />
              <span className="hidden md:inline">Officer Guide</span>
            </button>
          )}

          {user && (
            <div className="flex items-center gap-2 sm:gap-3 pl-2 sm:pl-3 border-l border-[#1b2b4d]">
              <div className="text-right hidden sm:block">
                <span className="text-xs font-bold text-slate-200 block capitalize">
                  {user.username}
                </span>
                <span className="text-[10px] font-bold text-emerald-300 bg-emerald-950/80 border border-emerald-800/60 px-1.5 py-0.2 rounded uppercase tracking-wider">
                  {user.role.replace("_", " ")}
                </span>
              </div>

              <button
                type="button"
                onClick={logout}
                className="p-1.5 sm:p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-950/40 rounded-xl transition-all cursor-pointer border border-transparent hover:border-rose-900/40 shrink-0"
                title="Sign out of local session"
                aria-label="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
