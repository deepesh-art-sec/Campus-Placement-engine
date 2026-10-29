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
    { num: "01", id: "overview", label: "Overview", icon: Home },
    { num: "02", id: "students", label: "Students", icon: Users, badge: "Roster" },
    { num: "03", id: "drives", label: "Drives (Read/Prep)", icon: Briefcase },
    { num: "04", id: "eligibility", label: "Eligibility List", icon: CheckCircle },
    { num: "05", id: "schedule", label: "Schedule (View)", icon: Calendar },
    { num: "06", id: "clashes", label: "Student Clashes", icon: AlertTriangle, badge: "Pref", badgeVariant: "amber" },
    { num: "07", id: "results", label: "Result Entry", icon: Award, badge: "Pending", badgeVariant: "brand" },
    { num: "08", id: "communication", label: "Communication", icon: MessageSquare },
    { num: "09", id: "ontheday", label: "On-The-Day View", icon: Clock, badge: "Live", badgeVariant: "brand" },
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
      className={`bg-[#060b14] border-r border-[#15233e] flex flex-col transition-all duration-300 select-none ${
        isCollapsed ? "w-20" : "w-64"
      }`}
    >
      {/* Role Badge & Collapse Toggle */}
      <div className="p-4 border-b border-[#15233e] flex items-center justify-between">
        {!isCollapsed && (
          <div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
              <span className="text-xs font-bold text-white uppercase tracking-wider">
                Coordinator
              </span>
            </div>
            <p className="text-[10px] text-slate-400 mt-0.5">Staff Assistant Operations</p>
          </div>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 rounded-lg bg-[#0e192d] hover:bg-[#192b4d] text-slate-400 hover:text-white transition"
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation Modules */}
      <nav className="flex-1 overflow-y-auto p-2 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              aria-label={item.label}
              data-testid={`coord-nav-${item.id}`}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                isActive
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-900/30 font-bold"
                  : "text-slate-400 hover:text-slate-100 hover:bg-[#0c1628]"
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
                      className={`text-[10px] px-1.5 py-0.2 rounded-md font-bold uppercase tracking-wider ${
                        item.badgeVariant === "brand"
                          ? "bg-indigo-500/30 text-indigo-200 border border-indigo-400/30"
                          : item.badgeVariant === "amber"
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                          : item.badgeVariant === "rose"
                          ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                          : "bg-slate-700/50 text-slate-300 border border-slate-600/40"
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

      {/* Security & Access Restriction Footer */}
      {!isCollapsed && (
        <div className="p-3 border-t border-[#15233e] bg-[#040810]/60 m-2 rounded-xl">
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-amber-400">
            <Lock className="w-3.5 h-3.5 text-amber-400" />
            <span>Coordinator Scope</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1 leading-snug">
            Policy editing, rule modifications, and drive publishing require Placement Officer authorization.
          </p>
        </div>
      )}
    </aside>
  );
};
