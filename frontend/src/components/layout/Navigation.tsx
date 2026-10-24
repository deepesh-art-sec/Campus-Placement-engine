import React from "react";
import {
  Briefcase,
  FileText,
  Users,
  Sliders,
  Shield,
  CheckCircle,
  Calendar,
  Sparkles,
  Award,
  GitCompare,
  Download,
  History,
  Activity,
  Cpu,
} from "lucide-react";

export type NavTabId =
  | "drives"
  | "create_drive"
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
  | "audit"
  | "offline_audit";

interface NavigationProps {
  activeTab: NavTabId;
  onSelectTab: (tab: NavTabId) => void;
  userRole?: string;
}

interface NavGroup {
  name: string;
  tabs: Array<{
    id: NavTabId;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    badge?: string;
  }>;
}

export const Navigation: React.FC<NavigationProps> = ({
  activeTab,
  onSelectTab,
  userRole = "officer",
}) => {
  const navGroups: NavGroup[] = [
    {
      name: "Setup & Roster",
      tabs: [
        { id: "drives", label: "Drives", icon: Briefcase },
        { id: "create_drive", label: "Extract Drive", icon: FileText, badge: "NLP" },
        { id: "students", label: "Students & Importer", icon: Users },
      ],
    },
    {
      name: "Rules & Policy",
      tabs: [
        { id: "rule_editor", label: "Rule Editor", icon: Sliders },
        { id: "policies", label: "Offer Policies", icon: Shield },
        { id: "policy_simulator", label: "Policy Simulator", icon: Cpu, badge: "New" },
      ],
    },
    {
      name: "Execution",
      tabs: [
        { id: "eligibility", label: "Eligibility Runs", icon: CheckCircle },
        { id: "schedule", label: "Schedule Grid", icon: Calendar, badge: "0 Clashes" },
        { id: "what_if", label: "What-If & Publish", icon: Sparkles },
        { id: "results", label: "Result Entry", icon: Award },
      ],
    },
    {
      name: "Governance",
      tabs: [
        { id: "dispute", label: "Dispute Explainer", icon: GitCompare },
        { id: "export", label: "Company Export", icon: Download },
        { id: "audit", label: "Event Replay", icon: History },
        { id: "offline_audit", label: "Offline Audit", icon: Activity },
      ],
    },
  ];

  return (
    <nav className="bg-[#080e1c]/95 backdrop-blur-md border-b border-[#1b2b4d] sticky top-[73px] z-20 shadow-sm no-print">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
        <div className="flex items-center gap-4 overflow-x-auto no-scrollbar py-0.5">
          {navGroups.map((group, groupIdx) => (
            <React.Fragment key={group.name}>
              {groupIdx > 0 && (
                <div className="h-6 w-px bg-[#1b2b4d] shrink-0 mx-1" aria-hidden="true" />
              )}
              <div className="flex items-center gap-1 shrink-0">
                <span className="text-[10px] uppercase font-black tracking-wider text-slate-500 mr-1 hidden xl:inline">
                  {group.name}
                </span>
                {group.tabs.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => onSelectTab(tab.id)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all duration-150 cursor-pointer ${
                        isActive
                          ? "bg-gradient-to-r from-blue-700 via-teal-600 to-emerald-600 text-white shadow-md shadow-emerald-900/40 ring-1 ring-emerald-400/40 scale-[1.02]"
                          : "text-slate-300 hover:text-white hover:bg-[#111d38]"
                      }`}
                    >
                      <Icon className={`w-3.5 h-3.5 ${isActive ? "text-white" : "text-slate-400"}`} />
                      <span>{tab.label}</span>
                      {tab.badge && (
                        <span
                          className={`text-[9px] px-1.5 py-0.2 rounded-full font-black uppercase tracking-wider ${
                            isActive
                              ? "bg-white/20 text-white"
                              : tab.badge === "0 Clashes"
                              ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800/60"
                              : tab.badge === "New"
                              ? "bg-blue-950/80 text-blue-300 border border-blue-800/60"
                              : "bg-[#111d38] text-slate-300 border border-[#1b2b4d]"
                          }`}
                        >
                          {tab.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </React.Fragment>
          ))}
        </div>
      </div>
    </nav>
  );
};
