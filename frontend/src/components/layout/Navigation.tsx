import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import {
  Home,
  FileText,
  Users,
  Briefcase,
  Calendar,
  BarChart2,
  Settings,
  Inbox,
  CheckCircle,
  Shield,
  Sparkles,
  Award,
  GitCompare,
  Key,
  Lock,
  ChevronLeft,
  ChevronRight,
  Target,
  Sliders,
  UserCheck,
} from "lucide-react";

export type NavTabId =
  | "drives"
  | "message_box"
  | "attendance"
  | "create_drive"
  | "announcements"
  | "students"
  | "policies"
  | "policy_simulator"
  | "eligibility"
  | "schedule"
  | "what_if"
  | "results"
  | "export"
  | "users_roles"
  | "audit_backup"
  | "audit"
  | "offline_audit";

interface NavigationProps {
  activeTab: NavTabId;
  onSelectTab: (tab: NavTabId) => void;
  userRole?: string;
}

interface NavItem {
  id: NavTabId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  badgeVariant?: "success" | "brand" | "neutral" | "warning";
}

export const Navigation: React.FC<NavigationProps> = ({
  activeTab,
  onSelectTab,
  userRole = "officer",
}) => {
  const [isCollapsed, setIsCollapsed] = useState(() => typeof window !== "undefined" && window.innerWidth < 1024);
  const [liveStudentCount, setLiveStudentCount] = useState<number | null>(null);
  const [liveClashCount, setLiveClashCount] = useState<number>(0);
  const [livePendingCount, setLivePendingCount] = useState<number>(0);

  useEffect(() => {
    let active = true;
    Promise.all([
      api.get<{ total: number }>("/api/students?limit=1").catch(() => null),
      api.get<{ unresolved_clashes: number }>("/api/drives/overview-metrics").catch(() => null),
      api.get<{ total_pending: number }>("/api/officer/inbox/summary").catch(() => null),
    ]).then(([stuRes, metRes, inbRes]) => {
      if (!active) return;
      if (stuRes && typeof stuRes.total === "number") setLiveStudentCount(stuRes.total);
      if (metRes && typeof metRes.unresolved_clashes === "number") setLiveClashCount(metRes.unresolved_clashes);
      if (inbRes && typeof inbRes.total_pending === "number") setLivePendingCount(inbRes.total_pending);
    });
    return () => { active = false; };
  }, []);

  const rosterBadge = liveStudentCount !== null
    ? liveStudentCount >= 1000 ? `${(liveStudentCount / 1000).toFixed(1)}k` : `${liveStudentCount}`
    : "1.8k";

  // 1. Primary Reference Blueprint Nav Items
  const primaryNavItems: NavItem[] = [
    {
      id: "drives",
      label: "Dashboard",
      icon: Home,
    },
    {
      id: "announcements",
      label: "Announcements",
      icon: FileText,
    },
    {
      id: "students",
      label: "Students",
      icon: Users,
      badge: rosterBadge,
      badgeVariant: "brand",
    },
    {
      id: "create_drive",
      label: "Drives",
      icon: Briefcase,
    },
    {
      id: "schedule",
      label: "Scheduling",
      icon: Calendar,
      badge: liveClashCount === 0 ? "0 Clashes" : `${liveClashCount} Clashes`,
      badgeVariant: liveClashCount === 0 ? "success" : "warning",
    },
    {
      id: "export",
      label: "Reports",
      icon: BarChart2,
    },
    {
      id: "audit_backup",
      label: "Settings",
      icon: Settings,
    },
  ];

  // 2. Specialized Officer Modules
  const officerModules: NavItem[] = [
    {
      id: "message_box",
      label: "Message Box",
      icon: Inbox,
      badge: livePendingCount > 0 ? `${livePendingCount}` : undefined,
      badgeVariant: "warning",
    },
    {
      id: "attendance",
      label: "Attendance",
      icon: UserCheck,
      badge: "Live",
      badgeVariant: "brand",
    },
    {
      id: "eligibility",
      label: "Rules & Eligibility",
      icon: CheckCircle,
    },
    {
      id: "policies",
      label: "Offer Policies",
      icon: Shield,
    },
    {
      id: "what_if",
      label: "What-If & Publish",
      icon: Sparkles,
    },
    {
      id: "results",
      label: "Results Entry",
      icon: Award,
    },
    {
      id: "users_roles",
      label: "Users & Roles",
      icon: Key,
    },
    {
      id: "offline_audit",
      label: "Air-Gap Audit",
      icon: Lock,
    },
  ];

  return (
    <aside
      className={`corporate-sidebar shrink-0 flex flex-col h-full max-h-full overflow-hidden sticky top-0 transition-all duration-200 select-none z-20 ${
        isCollapsed ? "w-16" : "w-60"
      }`}
      aria-label="Campus Placement Engine Sidebar"
    >
      {/* 1. Logo & Product Branding at Top (Reference Match) */}
      <div className="p-4 flex items-center justify-between border-b border-[var(--sidebar-border)] bg-[var(--sidebar-bg)] shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center text-white shadow-lg shadow-cyan-500/25 shrink-0">
            <Briefcase className="w-5 h-5 text-white" />
          </div>
          {!isCollapsed && (
            <div className="min-w-0">
              <h1 className="font-extrabold text-white text-base tracking-tight leading-tight">
                IM-101
              </h1>
              <span className="text-[11px] text-cyan-400/90 font-medium block truncate">
                Placement Engine
              </span>
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* 2. Primary Navigation Menu List */}
      <nav className="flex-1 min-h-0 overflow-y-auto px-3 py-4 space-y-1 custom-scrollbar">
        {primaryNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectTab(item.id)}
              title={item.label}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-bold transition-all duration-150 cursor-pointer ${
                isActive
                  ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-lg shadow-cyan-500/20 font-extrabold"
                  : "text-slate-300 hover:text-white hover:bg-white/5"
              }`}
            >
              <div className="flex items-center justify-center shrink-0">
                <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-slate-400"}`} />
              </div>

              {!isCollapsed && (
                <div className="flex items-center justify-between flex-1 min-w-0">
                  <span className="truncate text-left">{item.label}</span>
                  {item.badge && (
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded-full font-black uppercase tracking-wider shrink-0 ml-1 ${
                        isActive
                          ? "bg-white/20 text-white"
                          : item.badgeVariant === "success" || item.badge === "0 Clashes"
                          ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                          : item.badgeVariant === "warning"
                          ? "bg-amber-950 text-amber-300 border border-amber-800"
                          : "bg-[#060B16] text-cyan-400 border border-cyan-500/30"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}

        {/* Officer Engine Modules Group */}
        {!isCollapsed && (
          <div className="pt-4 pb-1">
            <span className="text-[10px] font-black uppercase tracking-widest text-slate-500 font-mono px-2 block">
              Officer Modules
            </span>
          </div>
        )}

        {officerModules.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectTab(item.id)}
              title={item.label}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold transition-all duration-150 cursor-pointer ${
                isActive
                  ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-lg shadow-cyan-500/20 font-bold"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <div className="flex items-center justify-center shrink-0">
                <Icon className={`w-3.5 h-3.5 ${isActive ? "text-white" : "text-slate-400"}`} />
              </div>

              {!isCollapsed && (
                <div className="flex items-center justify-between flex-1 min-w-0">
                  <span className="truncate text-left text-[11px]">{item.label}</span>
                  {item.badge && (
                    <span
                      className={`text-[8px] px-1.5 py-0.2 rounded-full font-bold uppercase shrink-0 ml-1 ${
                        item.badgeVariant === "warning"
                          ? "bg-amber-500 text-white"
                          : "bg-blue-900/60 text-blue-300"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </nav>

      {/* 3. Sidebar Footer: Slogan & Architectural Outline (Reference Match) */}
      {!isCollapsed && (
        <div className="p-4 border-t border-[var(--sidebar-border)] bg-[var(--sidebar-bg)] shrink-0 space-y-3 relative overflow-hidden">
          {/* Target Slogan */}
          <div className="flex flex-col items-center justify-center text-center space-y-1 relative z-10">
            <div className="w-7 h-7 rounded-full bg-blue-950/80 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-sm">
              <Target className="w-4 h-4" />
            </div>
            <span className="text-[11px] font-bold text-slate-200 block">
              Better Placements
            </span>
            <span className="text-[10px] text-slate-400 block">
              Brighter Futures
            </span>
          </div>

          {/* Architectural campus skyline vector */}
          <div className="pt-1 opacity-25">
            <svg
              className="w-full h-9 text-cyan-400"
              viewBox="0 0 200 40"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M5 38H195M15 38V22L25 15L35 22V38M45 38V12H75V38M55 12V6H65V12M85 38V20L95 12L105 20V38M115 38V8H145V38M125 8V3L130 1L135 3V8M155 38V18H185V38M165 18V14H175V18"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>

          {/* Author Watermark */}
          <div className="pt-2 border-t border-[#121F38] text-center">
            <a
              href="https://github.com/deepesh-art-sec"
              target="_blank"
              rel="noopener noreferrer"
              title="Repository Author: Deepesh-art-sec"
              className="inline-flex items-center justify-center gap-1.5 text-[10px] font-mono font-bold text-cyan-400 hover:text-cyan-300 transition-colors group"
            >
              <Shield className="w-3 h-3 text-cyan-400 group-hover:scale-110 transition-transform" />
              <span>Made by Deepesh-art-sec</span>
            </a>
          </div>
        </div>
      )}
    </aside>
  );
};
