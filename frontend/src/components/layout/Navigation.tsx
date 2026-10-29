import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import {
  Home,
  Users,
  Shield,
  Briefcase,
  CheckCircle,
  Calendar,
  Sparkles,
  Award,
  GitCompare,
  Download,
  Key,
  Lock,
  ChevronLeft,
  ChevronRight,
  Activity,
  Sliders,
  Files,
  Cpu,
  History,
  CheckCircle2,
} from "lucide-react";

export type NavTabId =
  | "drives"
  | "create_drive"
  | "announcements"
  | "students"
  | "rule_editor"
  | "policies"
  | "policy_simulator"
  | "eligibility"
  | "schedule"
  | "what_if"
  | "results"
  | "dispute"
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

interface SubItem {
  id: NavTabId;
  label: string;
  accessibleName: string;
  badge?: string;
}

interface NavModule {
  moduleNum: string;
  id: NavTabId;
  label: string;
  accessibleName: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  badgeVariant?: "success" | "brand" | "neutral" | "warning";
  subItems?: SubItem[];
}

export const Navigation: React.FC<NavigationProps> = ({
  activeTab,
  onSelectTab,
  userRole = "officer",
}) => {
  const [isCollapsed, setIsCollapsed] = useState(() => typeof window !== "undefined" && window.innerWidth < 1024);
  const [liveStudentCount, setLiveStudentCount] = useState<number | null>(null);
  const [liveClashCount, setLiveClashCount] = useState<number>(0);

  useEffect(() => {
    let active = true;
    Promise.all([
      api.get<{ total: number }>("/api/students?limit=1").catch(() => null),
      api.get<{ unresolved_clashes: number }>("/api/drives/overview-metrics").catch(() => null),
    ]).then(([stuRes, metRes]) => {
      if (!active) return;
      if (stuRes && typeof stuRes.total === "number") {
        setLiveStudentCount(stuRes.total);
      }
      if (metRes && typeof metRes.unresolved_clashes === "number") {
        setLiveClashCount(metRes.unresolved_clashes);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const rosterBadge = liveStudentCount !== null
    ? liveStudentCount >= 1000
      ? `${(liveStudentCount / 1000).toFixed(1)}k Roster`
      : `${liveStudentCount} Roster`
    : "1.8k Roster";

  const clashBadge = liveClashCount === 0 ? "0 Clashes" : `${liveClashCount} Clashes`;
  const clashVariant: "success" | "warning" = liveClashCount === 0 ? "success" : "warning";

  const modules: NavModule[] = [
    {
      moduleNum: "01",
      id: "drives",
      label: "Home / Overview",
      accessibleName: "Recruitment Drives",
      icon: Home,
    },
    {
      moduleNum: "02",
      id: "students",
      label: "Students",
      accessibleName: "Students & Importer",
      icon: Users,
      badge: rosterBadge,
    },
    {
      moduleNum: "03",
      id: "policies",
      label: "Offer Policy",
      accessibleName: "Offer Policies",
      icon: Shield,
      subItems: [
        {
          id: "policy_simulator",
          label: "Policy Simulator",
          accessibleName: "Policy Simulator",
          badge: "Sim",
        },
      ],
    },
    {
      moduleNum: "04",
      id: "create_drive",
      label: "Drives (Create)",
      accessibleName: "Extract Drive",
      icon: Briefcase,
      badge: "3 Modes",
      subItems: [
        {
          id: "announcements",
          label: "25 Announcements",
          accessibleName: "25 Announcements",
          badge: "25 Docs",
        },
      ],
    },
    {
      moduleNum: "05",
      id: "eligibility",
      label: "Rules & Eligibility",
      accessibleName: "Eligibility Runs",
      icon: CheckCircle,
      subItems: [
        {
          id: "rule_editor",
          label: "Rule Editor",
          accessibleName: "Rule Editor",
        },
      ],
    },
    {
      moduleNum: "06",
      id: "schedule",
      label: "Schedule",
      accessibleName: "Schedule Grid",
      icon: Calendar,
      badge: clashBadge,
      badgeVariant: clashVariant,
    },
    {
      moduleNum: "07",
      id: "what_if",
      label: "What-If & Publish",
      accessibleName: "What-If & Publish",
      icon: Sparkles,
    },
    {
      moduleNum: "08",
      id: "results",
      label: "Results & Enforcement",
      accessibleName: "Result Entry",
      icon: Award,
    },
    {
      moduleNum: "09",
      id: "dispute",
      label: "Disputes & Explanations",
      accessibleName: "Dispute Explainer",
      icon: GitCompare,
    },
    {
      moduleNum: "10",
      id: "export",
      label: "Messages & Export",
      accessibleName: "Company Export",
      icon: Download,
    },
    {
      moduleNum: "11",
      id: "users_roles",
      label: "Users & Roles",
      accessibleName: "Users & Roles",
      icon: Key,
      badge: "RBAC",
    },
    {
      moduleNum: "12",
      id: "audit_backup",
      label: "Audit & Settings",
      accessibleName: "Audit, Backup & Settings",
      icon: Lock,
      subItems: [
        {
          id: "offline_audit",
          label: "Offline Audit",
          accessibleName: "Offline Audit",
          badge: "Air-Gap",
        },
        {
          id: "audit",
          label: "Event Replay",
          accessibleName: "Event Replay",
        },
      ],
    },
  ];

  return (
    <aside
      className={`bg-[#080e1c] border-r border-[#1b2b4d] shrink-0 flex flex-col transition-all duration-200 select-none z-20 ${
        isCollapsed ? "w-16" : "w-64"
      }`}
      aria-label="Officer Dashboard Left Navigation"
    >
      {/* Sidebar Header with Module Index and Collapse Toggle */}
      <div className="p-3.5 border-b border-[#1b2b4d] flex items-center justify-between text-slate-300">
        {!isCollapsed && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-black tracking-widest text-emerald-400 uppercase font-mono">
              OFFICER SUITE
            </span>
            <span className="text-[9px] px-1.5 py-0.2 bg-[#111d38] border border-[#1b2b4d] rounded text-slate-400 font-bold">
              12 MODULES
            </span>
          </div>
        )}
        <button
          type="button"
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#111d38] transition-colors cursor-pointer ml-auto"
          title={isCollapsed ? "Expand sidebar navigation" : "Collapse sidebar navigation"}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Nav List with 12 Numbered Officer Modules */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-1 custom-scrollbar">
        {modules.map((mod) => {
          const Icon = mod.icon;
          const isMainActive = activeTab === mod.id;
          const isSubActive = mod.subItems?.some((sub) => activeTab === sub.id);
          const isActive = isMainActive || isSubActive;

          return (
            <div key={mod.id} className="space-y-0.5">
              <button
                type="button"
                aria-label={mod.accessibleName}
                onClick={() => onSelectTab(mod.id)}
                title={`${mod.moduleNum}. ${mod.label}`}
                className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-xl text-xs font-bold transition-all duration-150 cursor-pointer ${
                  isMainActive
                    ? "bg-gradient-to-r from-blue-700 via-teal-600 to-emerald-600 text-white shadow-md shadow-emerald-950/40 ring-1 ring-emerald-400/40"
                    : isSubActive
                    ? "bg-[#111d38] text-white border border-[#1b2b4d]"
                    : "text-slate-300 hover:text-white hover:bg-[#111d38]/80"
                }`}
              >
                <div className="flex items-center justify-center shrink-0">
                  <Icon
                    className={`w-4 h-4 ${
                      isMainActive ? "text-white" : "text-slate-400"
                    }`}
                  />
                </div>

                {!isCollapsed && (
                  <div className="flex items-center justify-between flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="text-[10px] font-mono font-bold text-slate-500">
                        {mod.moduleNum}
                      </span>
                      <span className="truncate text-left">{mod.label}</span>
                    </div>

                    {mod.badge && (
                      <span
                        className={`text-[9px] px-1.5 py-0.2 rounded-full font-black uppercase tracking-wider shrink-0 ml-1 ${
                          isMainActive
                            ? "bg-white/20 text-white"
                            : mod.badgeVariant === "success" || mod.badge === "0 Clashes"
                            ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                            : mod.badgeVariant === "warning"
                            ? "bg-amber-950 text-amber-300 border border-amber-800"
                            : "bg-[#111d38] text-slate-400 border border-[#1b2b4d]"
                        }`}
                      >
                        {mod.badge}
                      </span>
                    )}
                  </div>
                )}
              </button>

              {/* Sub-Items (Quick Shortcuts like 25 Announcements, Policy Simulator, Offline Audit) */}
              {!isCollapsed && mod.subItems && mod.subItems.length > 0 && (
                <div className="pl-7 pr-1 py-0.5 space-y-0.5">
                  {mod.subItems.map((sub) => {
                    const isCurrentSub = activeTab === sub.id;
                    return (
                      <button
                        key={sub.id}
                        type="button"
                        aria-label={sub.accessibleName}
                        onClick={() => onSelectTab(sub.id)}
                        className={`w-full flex items-center justify-between px-2 py-1 rounded-lg text-[11px] font-semibold transition-all cursor-pointer ${
                          isCurrentSub
                            ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                            : "text-slate-400 hover:text-slate-200 hover:bg-[#111d38]"
                        }`}
                      >
                        <span className="truncate">{sub.label}</span>
                        {sub.badge && (
                          <span className="text-[8px] px-1 rounded bg-[#111d38] text-slate-400 font-mono">
                            {sub.badge}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Sidebar Footer with Institutional Compliance Badges */}
      {!isCollapsed && (
        <div className="p-3 border-t border-[#1b2b4d] bg-[#050a14]/60 text-[11px] text-slate-400 space-y-1 font-mono">
          <div className="flex items-center gap-1.5 text-emerald-400 font-bold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Air-Gap Ready</span>
          </div>
          <div className="text-[10px] text-slate-500 truncate">
            Deterministic IM-101 Engine
          </div>
        </div>
      )}
    </aside>
  );
};
