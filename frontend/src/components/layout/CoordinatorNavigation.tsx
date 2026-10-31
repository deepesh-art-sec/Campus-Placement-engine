import React, { useState } from "react";
import {
  Home,
  Users,
  Briefcase,
  CheckCircle,
  Calendar,
  AlertTriangle,
  Award,
  MessageSquare,
  Clock,
  FileQuestion,
  FileSpreadsheet,
  Bell,
  ChevronLeft,
  ChevronRight,
  Shield,
  Lock,
  Target,
  UserCheck,
} from "lucide-react";

export type CoordinatorTabId =
  | "overview"
  | "students"
  | "drives"
  | "eligibility"
  | "schedule"
  | "clashes"
  | "results"
  | "communication"
  | "ontheday"
  | "attendance"
  | "requests"
  | "reports"
  | "notifications";

interface CoordinatorNavigationProps {
  activeTab: CoordinatorTabId;
  onSelectTab: (tab: CoordinatorTabId) => void;
  unreadCount?: number;
}

interface NavItem {
  num: string;
  id: CoordinatorTabId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  badgeVariant?: "brand" | "amber" | "rose" | "neutral";
}

export const CoordinatorNavigation: React.FC<CoordinatorNavigationProps> = ({
  activeTab,
  onSelectTab,
  unreadCount = 0,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(() => typeof window !== "undefined" && window.innerWidth < 1024);

  const navItems: NavItem[] = [
    { num: "01", id: "overview", label: "Dashboard", icon: Home },
    { num: "02", id: "students", label: "Students", icon: Users, badge: "Roster" },
    { num: "03", id: "drives", label: "Drives", icon: Briefcase },
    { num: "04", id: "eligibility", label: "Eligibility List", icon: CheckCircle },
    { num: "05", id: "schedule", label: "Scheduling", icon: Calendar },
    { num: "06", id: "clashes", label: "Student Clashes", icon: AlertTriangle, badge: "Pref", badgeVariant: "amber" },
    { num: "07", id: "results", label: "Result Entry", icon: Award, badge: "Pending", badgeVariant: "brand" },
    { num: "08", id: "communication", label: "Communication", icon: MessageSquare },
    { num: "09", id: "ontheday", label: "Attendance", icon: UserCheck, badge: "Live", badgeVariant: "brand" },
    { num: "10", id: "requests", label: "Requests to Officer", icon: FileQuestion },
    { num: "11", id: "reports", label: "Reports & Export", icon: FileSpreadsheet },
    {
      num: "12",
      id: "notifications",
      label: "Notifications",
      icon: Bell,
      badge: unreadCount > 0 ? String(unreadCount) : undefined,
      badgeVariant: "rose",
    },
  ];

  return (
    <aside
      className={`corporate-sidebar shrink-0 flex flex-col h-full max-h-full overflow-hidden sticky top-0 transition-all duration-200 select-none z-20 ${
        isCollapsed ? "w-16" : "w-60"
      }`}
      aria-label="Coordinator Navigation Sidebar"
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
              <span className="text-[11px] text-cyan-400 font-semibold block truncate">
                Coordinator Portal
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

      {/* 2. Navigation Modules */}
      <nav className="flex-1 min-h-0 overflow-y-auto px-3 py-4 space-y-1 custom-scrollbar">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id || (item.id === "ontheday" && (activeTab as string) === "attendance");
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              aria-label={item.label}
              data-testid={`coord-nav-${item.id}`}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-bold transition-all duration-150 cursor-pointer ${
                isActive
                  ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-lg shadow-cyan-500/20 font-extrabold"
                  : "text-slate-300 hover:text-white hover:bg-white/5"
              }`}
              title={isCollapsed ? item.label : undefined}
            >
              <div className="relative shrink-0 flex items-center justify-center">
                <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-slate-400"}`} />
              </div>

              {!isCollapsed && (
                <div className="flex-1 flex items-center justify-between min-w-0">
                  <span className="truncate">{item.label}</span>
                  {item.badge && (
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded-full font-black uppercase tracking-wider shrink-0 ml-1 ${
                        isActive
                          ? "bg-white/20 text-white"
                          : item.badgeVariant === "amber"
                          ? "bg-amber-950 text-amber-300 border border-amber-800"
                          : item.badgeVariant === "rose"
                          ? "bg-rose-950 text-rose-300 border border-rose-800"
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
      </nav>

      {/* 3. Security & Access Restriction Footer */}
      {!isCollapsed && (
        <div className="p-3 border-t border-[var(--sidebar-border)] bg-[var(--sidebar-bg)] shrink-0 space-y-2">
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-amber-400">
            <Lock className="w-3.5 h-3.5 text-amber-400" />
            <span>Coordinator Scope</span>
          </div>
          <p className="text-[10px] text-slate-400 leading-snug">
            Policy editing, rule modifications, and drive publishing require Placement Officer authorization.
          </p>
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
