import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  HardDrive,
  LogOut,
  HelpCircle,
  Activity,
  Copy,
  Check,
  Cpu,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { api, auditTracker } from "../../api/client";

interface HeaderProps {
  onOpenTour?: () => void;
  onNavigateToAudit?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenTour, onNavigateToAudit }) => {
  const { user, logout } = useAuth();
  const externalCalls = auditTracker.getExternalCount();
  const [copied, setCopied] = useState(false);

  const [lanUrl, setLanUrl] = useState<string>(() => {
    if (typeof window !== "undefined") {
      if (window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
        return `${window.location.protocol}//${window.location.hostname}:8000`;
      }
    }
    return "http://localhost:8000";
  });

  useEffect(() => {
    api.get<any>("/api/lan-info").then((res) => {
      if (res?.primary_url) {
        setLanUrl(res.primary_url);
      }
    }).catch(() => {});
  }, []);

  const handleCopyLanUrl = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(lanUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <header className="bg-[#080e1c]/95 backdrop-blur-md border-b border-[#1b2b4d] sticky top-0 z-30 shadow-md no-print transition-all">
      {/* Top Air-Gap & LAN Status Banner */}
      <div className="bg-[#040810] text-slate-300 px-4 py-1.5 text-xs font-medium flex items-center justify-between border-b border-[#14223d]">
        <div className="flex items-center gap-2.5">
          <span className="flex h-2 w-2 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <div className="flex items-center gap-1.5 font-bold tracking-wide">
            <HardDrive className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-emerald-300 font-mono text-[11px]">
              Offline mode: all data stays on this machine
            </span>
          </div>
          <span className="text-slate-600 hidden md:inline">•</span>
          <span className="text-slate-400 text-[11px] hidden md:inline">
            Local SQLite WAL • Zero Outbound Telemetry • FERPA & DPDP Ready
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Quick Access Pill (Offline / LAN) */}
          <button
            type="button"
            onClick={handleCopyLanUrl}
            className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg bg-[#0e172a] hover:bg-[#152342] text-slate-300 text-[11px] font-mono transition-all border border-[#1b2b4d] hover:border-emerald-500/40 cursor-pointer"
            title="Click to copy local / LAN access link"
          >
            <span className="text-slate-400">
              {lanUrl.includes("localhost") || lanUrl.includes("127.0.0.1") ? "Offline:" : "LAN:"}
            </span>
            <span className="text-emerald-300 font-bold">{lanUrl}</span>
            {copied ? (
              <Check className="w-3 h-3 text-emerald-400 ml-0.5" />
            ) : (
              <Copy className="w-3 h-3 text-slate-400 hover:text-white ml-0.5" />
            )}
          </button>

          {/* Audit Pill */}
          <button
            type="button"
            onClick={onNavigateToAudit}
            className="flex items-center gap-1.5 bg-emerald-950/80 hover:bg-emerald-900/80 border border-emerald-800/60 px-2.5 py-0.5 rounded-lg text-[11px] font-semibold text-emerald-300 transition-colors cursor-pointer shadow-xs shadow-emerald-950/50"
            title="Verify 100% offline network compliance"
          >
            <Activity className="w-3 h-3 text-emerald-400" />
            <span>external calls: {externalCalls}</span>
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
          </button>
        </div>
      </div>

      {/* Main Header Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-blue-700 via-teal-600 to-emerald-500 flex items-center justify-center text-white font-black text-lg shadow-md shadow-emerald-500/20 ring-2 ring-emerald-500/20">
            PE
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-black text-white text-base tracking-tight">
                PLACEMENT ENGINE
              </span>
              <span className="text-[10px] font-black tracking-wider px-2 py-0.5 bg-blue-950/80 text-blue-300 border border-blue-800/60 rounded-full">
                ENTERPRISE
              </span>
              <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 rounded-full hidden sm:inline-flex items-center gap-1">
                <Cpu className="w-3 h-3 text-emerald-400" />
                CP-SAT Verified
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium hidden sm:block">
              Institutional Placement Eligibility, Policy & Clash-Free Scheduling Engine
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {onOpenTour && user?.role === "officer" && (
            <button
              type="button"
              onClick={onOpenTour}
              className="flex items-center gap-1.5 text-xs font-bold text-slate-200 hover:text-emerald-300 bg-[#111d38] hover:bg-[#162447] px-3 py-1.5 rounded-xl transition-all border border-[#1b2b4d] hover:border-emerald-500/40 cursor-pointer shadow-xs"
            >
              <HelpCircle className="w-4 h-4 text-emerald-400" />
              <span>Officer Guide</span>
            </button>
          )}

          {user && (
            <div className="flex items-center gap-3 pl-3 border-l border-[#1b2b4d]">
              <div className="text-right">
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
                className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-950/40 rounded-xl transition-all cursor-pointer border border-transparent hover:border-rose-900/40"
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
