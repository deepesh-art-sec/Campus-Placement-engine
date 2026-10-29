import React from "react";
import {
  ShieldCheck,
  HardDrive,
  LogOut,
  HelpCircle,
  Activity,
  Cpu,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { auditTracker } from "../../api/client";

interface HeaderProps {
  onOpenTour?: () => void;
  onNavigateToAudit?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenTour, onNavigateToAudit }) => {
  const { user, logout } = useAuth();
  const externalCalls = auditTracker.getExternalCount();

  return (
    <header className="bg-[#080e1c]/95 backdrop-blur-md border-b border-[#1b2b4d] sticky top-0 z-30 shadow-md no-print transition-all">
      {/* Top Air-Gap & LAN Status Banner */}
      <div className="bg-[#040810] text-slate-300 px-3 sm:px-4 py-1.5 text-xs font-medium flex flex-wrap items-center justify-between gap-1.5 border-b border-[#14223d]">
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex h-2 w-2 relative shrink-0">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <div className="flex items-center gap-1.5 font-bold tracking-wide truncate">
            <HardDrive className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span className="text-emerald-300 font-mono text-[11px] truncate">
              <span className="hidden sm:inline">Offline mode: all data stays on this machine</span>
              <span className="sm:hidden">Offline Mode</span>
            </span>
          </div>
          <span className="text-slate-600 hidden md:inline">•</span>
          <span className="text-slate-400 text-[11px] hidden lg:inline truncate">
            Local SQLite WAL • Zero Outbound Telemetry • FERPA & DPDP Ready
          </span>
        </div>

        <div className="flex items-center gap-2 sm:gap-3 shrink-0 ml-auto">
          {/* Status Badge */}
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-[#0e172a] text-slate-300 text-[11px] font-mono border border-[#1b2b4d]">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
            <span className="text-emerald-300 font-semibold">Online</span>
          </div>

          {/* Audit Pill */}
          <button
            type="button"
            onClick={onNavigateToAudit}
            className="flex items-center gap-1.5 bg-emerald-950/80 hover:bg-emerald-900/80 border border-emerald-800/60 px-2 py-0.5 rounded-lg text-[11px] font-semibold text-emerald-300 transition-colors cursor-pointer shadow-xs shadow-emerald-950/50"
            title="Verify 100% offline network compliance"
          >
            <Activity className="w-3 h-3 text-emerald-400 shrink-0" />
            <span className="hidden sm:inline">external calls: {externalCalls}</span>
            <span className="sm:hidden">ext: {externalCalls}</span>
            <ShieldCheck className="w-3 h-3 text-emerald-400 shrink-0" />
          </button>
        </div>
      </div>

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
