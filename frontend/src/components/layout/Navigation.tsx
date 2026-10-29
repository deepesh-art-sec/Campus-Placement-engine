import React from "react";
import {
  Briefcase,
  PlusCircle,
  Files,
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
  Inbox,
  Lock,
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
  | "requests_manager"
  | "user_management"
  | "recruiter_portal"
  | "audit"
  | "offline_audit"
  | "dev_components";

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
        { id: "create_drive", label: "New Drive", icon: PlusCircle, badge: "Create" },
        { id: "announcements", label: "25 Announcements", icon: Files, badge: "25 Docs" },
        { id: "students", label: "Students & Importer", icon: Users },
      ],
    },
    {
      name: "Rules & Policy",
      tabs: [
        { id: "rule_editor", label: "Rule Editor", icon: Sliders },
        { id: "policies", label: "Offer Policies", icon: Shield },
        { id: "policy_simulator", label: "Policy Simulator", icon: Cpu, badge: "Simulate" },
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
      name: "Governance & Operations",
      tabs: [
        { id: "requests_manager", label: "Requests & Diff", icon: Inbox, badge: "Review" },
        { id: "user_management", label: "Users & Roles", icon: Lock },
        { id: "recruiter_portal", label: "Recruiter Desk", icon: Briefcase, badge: "Preview" },
        { id: "dispute", label: "Dispute Explainer", icon: GitCompare },
        { id: "export", label: "Company Export", icon: Download },
        { id: "audit", label: "Event Replay", icon: History },
        { id: "offline_audit", label: "Offline Audit", icon: Activity },
        { id: "dev_components", label: "UI Primitives (/dev)", icon: Sparkles, badge: "Prompt 0" },
      ],
    },
  ];

  return (
    <nav className="bg-[#080e1c]/95 backdrop-blur-md border-b border-[#1b2b4d] sticky top-[73px] z-20 shadow-sm no-print">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
        <div className="flex items-center gap-4 overflow-x-auto no-scrollbar py-0.5">
          {navGroups.map((group, groupIdx) => (
            <React.Fragment key={group.name}>
              {groupIdx > 0 && <div className="h-5 w-px bg-[#1b2b4d] shrink-0" />}
              <div className="flex items-center gap-1 shrink-0">
                <span className="text-[10px] uppercase font-bold tracking-wider text-slate-300 font-mono hidden xl:inline-block mr-1">
                  {group.name}
                </span>
                {group.tabs.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => onSelectTab(tab.id)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap cursor-pointer ${
                        isActive
                          ? "bg-gradient-to-r from-blue-700 to-emerald-600 text-white shadow-sm shadow-emerald-900/40"
                          : "text-slate-300 hover:text-white hover:bg-[#111d38]"
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span>{tab.label}</span>
                      {tab.badge && (
                        <span
                          className={`text-[9px] font-mono px-1.5 py-0.2 rounded-full font-bold ${
                            isActive
                              ? "bg-white/20 text-white"
                              : "bg-[#162447] text-emerald-400 border border-emerald-500/30"
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
