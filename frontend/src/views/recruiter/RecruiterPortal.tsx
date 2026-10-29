import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  Briefcase,
  Users,
  CheckCircle2,
  Clock,
  Calendar,
  Download,
  Printer,
  Search,
  Filter,
  FileText,
  History,
  MessageSquare,
  Send,
  AlertCircle,
  Check,
  ChevronLeft,
  ChevronRight,
  Phone,
  Mail,
  Building2,
  ShieldCheck,
  Eye,
  X,
  UserCheck,
  HelpCircle,
  MapPin,
} from "lucide-react";

type RecruiterTab =
  | "drive"
  | "shortlist"
  | "schedule"
  | "requirements"
  | "versions"
  | "export"
  | "contact"
  | "ontheday"
  | "results";

interface DriveOverview {
  drive_id: string;
  company_id: string;
  company_name: string;
  job_role: string;
  drive_date: string;
  mode: string;
  ctc_lpa: number;
  is_dream: boolean;
  status: string;
  version: number;
  version_date: string;
  number_of_rounds: number;
  total_shortlisted: number;
  total_scheduled: number;
  attendance_enabled: boolean;
  results_released: boolean;
  officer_contact: {
    name: string;
    title: string;
    email: string;
    phone: string;
    office: string;
  };
}

interface ShortlistCandidate {
  roll_no: string;
  name: string;
  branch: string;
  cgpa: number;
  tenth_percentage: number;
  twelfth_percentage: number | null;
  active_backlogs: number;
  gap_years: number;
}

interface VerificationCriterion {
  criterion: string;
  required: string;
  candidate_value: string;
  passed: boolean;
  verification: string;
}

interface WhyBreakdown {
  candidate: {
    roll_no: string;
    name: string;
    branch: string;
    cgpa: number;
  };
  verdict: string;
  company_name: string;
  criteria: VerificationCriterion[];
}

interface ScheduleSlot {
  slot_id: string;
  round_number: number;
  round_name: string;
  start_time: string;
  end_time: string;
  venue: string;
  building: string;
  panel: string;
  candidate_name: string;
  candidate_roll_no: string;
  candidate_branch: string;
}

interface RequirementRule {
  rule_type: string;
  condition: string;
  plain_english: string;
}

interface VersionTimelineItem {
  version_number: number;
  timestamp: string;
  headline: string;
  officer_note: string;
  diff: {
    parameter: string;
    previous: string;
    updated: string;
    impact: string;
  }[];
}

interface RecruiterInquiry {
  id: string;
  title: string;
  description: string;
  status: string;
  submitted_at: string;
  officer_response?: string;
  officer_name?: string;
  resolved_at?: string;
}

interface AttendanceData {
  enabled: boolean;
  company_name: string;
  total_scheduled: number;
  present_count: number;
  absent_count: number;
  late_count: number;
  pending_count: number;
  turnout_percentage: number;
  rooms: Record<string, { present: number; absent: number; late: number; pending: number; total: number }>;
}

interface ResultCandidate {
  roll_no: string;
  name: string;
  branch: string;
  ctc_lpa: number;
  status: string;
  is_dream: boolean;
  confirmed_date: string;
}

export const RecruiterPortal: React.FC = () => {
  const [activeTab, setActiveTab] = useState<RecruiterTab>("drive");
  const [overview, setOverview] = useState<DriveOverview | null>(null);
  const [shortlist, setShortlist] = useState<ShortlistCandidate[]>([]);
  const [filteredShortlist, setFilteredShortlist] = useState<ShortlistCandidate[]>([]);
  const [scheduleSlots, setScheduleSlots] = useState<ScheduleSlot[]>([]);
  const [requirements, setRequirements] = useState<RequirementRule[]>([]);
  const [versions, setVersions] = useState<VersionTimelineItem[]>([]);
  const [inquiries, setInquiries] = useState<RecruiterInquiry[]>([]);
  const [attendance, setAttendance] = useState<AttendanceData | null>(null);
  const [resultsList, setResultsList] = useState<ResultCandidate[]>([]);

  // Search & Filters for Shortlist
  const [searchQuery, setSearchQuery] = useState("");
  const [branchFilter, setBranchFilter] = useState("all");
  const [sortBy, setSortBy] = useState<"cgpa" | "name" | "roll_no">("cgpa");

  // "Why This Student" Drawer / Modal State
  const [selectedCandidateRoll, setSelectedCandidateRoll] = useState<string | null>(null);
  const [whyBreakdown, setWhyBreakdown] = useState<WhyBreakdown | null>(null);
  const [whyLoading, setWhyLoading] = useState(false);

  // Contact / Feedback Form State
  const [inquirySubject, setInquirySubject] = useState("");
  const [inquiryCategory, setInquiryCategory] = useState("schedule_change");
  const [inquiryMessage, setInquiryMessage] = useState("");
  const [inquiryCandidateRoll, setInquiryCandidateRoll] = useState("");
  const [inquirySubmitting, setInquirySubmitting] = useState(false);
  const [inquirySuccess, setInquirySuccess] = useState<string | null>(null);
  const [inquiryError, setInquiryError] = useState<string | null>(null);

  // Global loading & errors
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scheduleViewMode, setScheduleViewMode] = useState<"list" | "day">("list");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => typeof window !== "undefined" && window.innerWidth < 1024);

  // Load Overview Data on Mount
  const fetchAllData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [ovRes, slRes, scRes, reqRes, verRes, inqRes, attRes, resRes] = await Promise.allSettled([
        api.get<DriveOverview>("/api/recruiter/my-drive"),
        api.get<{ total: number; shortlist: ShortlistCandidate[] }>("/api/recruiter/shortlist"),
        api.get<{ slots: ScheduleSlot[] }>("/api/recruiter/schedule"),
        api.get<{ rules: RequirementRule[] }>("/api/recruiter/requirements"),
        api.get<{ timeline: VersionTimelineItem[] }>("/api/recruiter/versions"),
        api.get<RecruiterInquiry[]>("/api/recruiter/inquiries"),
        api.get<AttendanceData>("/api/recruiter/attendance"),
        api.get<{ selected_candidates: ResultCandidate[] }>("/api/recruiter/results"),
      ]);

      if (ovRes.status === "fulfilled") setOverview(ovRes.value);
      if (slRes.status === "fulfilled") {
        const list = slRes.value.shortlist || [];
        setShortlist(list);
        setFilteredShortlist(list);
      }
      if (scRes.status === "fulfilled") setScheduleSlots(scRes.value.slots || []);
      if (reqRes.status === "fulfilled") setRequirements(reqRes.value.rules || []);
      if (verRes.status === "fulfilled") setVersions(verRes.value.timeline || []);
      if (inqRes.status === "fulfilled") setInquiries(inqRes.value || []);
      if (attRes.status === "fulfilled") setAttendance(attRes.value);
      if (resRes.status === "fulfilled") setResultsList(resRes.value.selected_candidates || []);
    } catch (err: any) {
      setError(err.message || "Failed to load corporate recruitment portal data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  // Filter shortlist when search query, branch filter, or sort changes
  useEffect(() => {
    let result = [...shortlist];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.roll_no.toLowerCase().includes(q) ||
          s.branch.toLowerCase().includes(q)
      );
    }

    if (branchFilter !== "all") {
      result = result.filter((s) => s.branch === branchFilter);
    }

    result.sort((a, b) => {
      if (sortBy === "cgpa") return b.cgpa - a.cgpa;
      if (sortBy === "name") return a.name.localeCompare(b.name);
      return a.roll_no.localeCompare(b.roll_no);
    });

    setFilteredShortlist(result);
  }, [searchQuery, branchFilter, sortBy, shortlist]);

  // Open "Why This Student" modal
  const handleInspectCandidate = async (rollNo: string) => {
    setSelectedCandidateRoll(rollNo);
    setWhyLoading(true);
    setWhyBreakdown(null);
    try {
      const res = await api.get<WhyBreakdown>(`/api/recruiter/candidate/${rollNo}/why`);
      setWhyBreakdown(res);
    } catch (err: any) {
      setError(err.message || "Failed to verify candidate requirements.");
    } finally {
      setWhyLoading(false);
    }
  };

  // Submit Feedback / Inquiry
  const handleInquirySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setInquirySubmitting(true);
      setInquiryError(null);
      setInquirySuccess(null);

      await api.post("/api/recruiter/feedback", {
        subject: inquirySubject,
        category: inquiryCategory,
        message: inquiryMessage,
        candidate_roll_no: inquiryCandidateRoll || undefined,
      });

      setInquirySuccess("Inquiry submitted to Placement Officer. We will respond promptly.");
      setInquirySubject("");
      setInquiryMessage("");
      setInquiryCandidateRoll("");

      // Refresh inquiries
      const updatedInquiries = await api.get<RecruiterInquiry[]>("/api/recruiter/inquiries");
      setInquiries(updatedInquiries || []);
    } catch (err: any) {
      setInquiryError(err.message || "Failed to submit inquiry.");
    } finally {
      setInquirySubmitting(false);
    }
  };

  // Pre-fill feedback from Requirements tab
  const handleFlagRequirement = (rule: RequirementRule) => {
    setInquirySubject(`Clarification on Rule: ${rule.rule_type}`);
    setInquiryCategory("rule_feedback");
    setInquiryMessage(`Regarding the rule "${rule.condition}": We would like to request clarification / review with the Placement Cell regarding this threshold.`);
    setActiveTab("contact");
  };

  const branches = Array.from(new Set(shortlist.map((s) => s.branch))).filter(Boolean);

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-400 space-y-3">
        <div className="w-10 h-10 border-4 border-emerald-500/30 border-t-emerald-400 rounded-full animate-spin mx-auto" />
        <p className="text-sm font-semibold">Authenticating corporate session and loading drive data...</p>
      </div>
    );
  }

  if (error && !overview) {
    return (
      <div className="p-8 bg-[#0d1527] border border-[#1b2b4d] rounded-3xl max-w-lg mx-auto text-center space-y-4 text-white">
        <Briefcase className="w-12 h-12 text-slate-500 mx-auto" />
        <h3 className="text-base font-bold text-white">Corporate Portal Access Restricted</h3>
        <p className="text-xs text-slate-400">{error}</p>
      </div>
    );
  }

  const navItems = [
    {
      num: "01",
      id: "drive" as RecruiterTab,
      label: "01 Home / My Drive",
      accessibleName: "01 Home / My Drive",
      icon: Building2,
    },
    {
      num: "02",
      id: "shortlist" as RecruiterTab,
      label: "02 Shortlist",
      accessibleName: "02 Shortlist",
      icon: Users,
      badge: String(overview?.total_shortlisted || shortlist.length),
    },
    {
      num: "04",
      id: "schedule" as RecruiterTab,
      label: "04 Schedule",
      accessibleName: "04 Schedule",
      icon: Calendar,
      badge: String(scheduleSlots.length),
    },
    {
      num: "05",
      id: "requirements" as RecruiterTab,
      label: "05 Requirements Used",
      accessibleName: "05 Requirements Used",
      icon: FileText,
    },
    {
      num: "06",
      id: "versions" as RecruiterTab,
      label: "06 Changes & Versions",
      accessibleName: "06 Changes & Versions",
      icon: History,
    },
    {
      num: "07",
      id: "export" as RecruiterTab,
      label: "07 Export Files",
      accessibleName: "07 Export Files",
      icon: Download,
    },
    {
      num: "08",
      id: "contact" as RecruiterTab,
      label: "08 Contact College",
      accessibleName: "08 Contact College",
      icon: MessageSquare,
    },
    {
      num: "09",
      id: "ontheday" as RecruiterTab,
      label: "09 On-The-Day Floor",
      accessibleName: "09 On-The-Day Floor",
      icon: Clock,
    },
    {
      num: "10",
      id: "results" as RecruiterTab,
      label: "10 Results",
      accessibleName: "10 Results",
      icon: CheckCircle2,
      badge: String(resultsList.length),
    },
  ];

  return (
    <div className="flex-1 flex overflow-hidden w-full h-full">
      {/* Left Vertical Navigation Sidebar (Identical to Coordinator and Officer) */}
      <aside
        className={`bg-[#080e1c] border-r border-[#1b2b4d] shrink-0 flex flex-col transition-all duration-200 select-none z-20 ${
          isSidebarCollapsed ? "w-16" : "w-64"
        }`}
        aria-label="Recruiter Dashboard Left Navigation"
      >
        {/* Sidebar Header with Module Index and Collapse Toggle */}
        <div className="p-3.5 border-b border-[#1b2b4d] flex items-center justify-between text-slate-300">
          {!isSidebarCollapsed && (
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
                <span className="text-[10px] font-black tracking-widest text-emerald-400 uppercase font-mono">
                  RECRUITER SUITE
                </span>
                <span className="text-[9px] px-1.5 py-0.2 bg-[#111d38] border border-[#1b2b4d] rounded text-slate-400 font-bold shrink-0">
                  9 MODULES
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-semibold truncate mt-0.5">
                {overview?.company_name || "Company Portal"} • Read-Only
              </p>
            </div>
          )}
          <button
            type="button"
            onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#111d38] transition-colors cursor-pointer ml-auto"
            title={isSidebarCollapsed ? "Expand sidebar navigation" : "Collapse sidebar navigation"}
          >
            {isSidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Vertical Nav List */}
        <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-1 custom-scrollbar">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                aria-label={item.accessibleName}
                onClick={() => setActiveTab(item.id)}
                title={item.label}
                className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-bold transition-all duration-150 cursor-pointer ${
                  isActive
                    ? "bg-gradient-to-r from-blue-700 via-teal-600 to-emerald-600 text-white shadow-md shadow-emerald-950/40 ring-1 ring-emerald-400/40"
                    : "text-slate-300 hover:text-white hover:bg-[#111d38]/80"
                }`}
              >
                <div className="flex items-center justify-center shrink-0">
                  <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-slate-400"}`} />
                </div>
                {!isSidebarCollapsed && (
                  <>
                    <span className="truncate">{item.label}</span>
                    {item.badge && (
                      <span className="ml-auto text-[10px] px-1.5 py-0.5 bg-[#111d38] border border-[#1b2b4d] rounded-md font-mono font-bold text-slate-300">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </button>
            );
          })}
        </nav>

        {/* Sidebar Footer */}
        {!isSidebarCollapsed && (
          <div className="p-3 border-t border-[#1b2b4d] text-[10px] text-slate-500 text-center font-mono">
            Tenant Isolated • Corporate Portal
          </div>
        )}
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8 overflow-y-auto space-y-6">
        {/* Privacy & Air-Gap Assurance Banner */}
        <div className="p-3 bg-[#080e1c] border border-emerald-500/30 rounded-2xl flex items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-2 text-emerald-400 font-semibold">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>Tenant Isolated Corporate Portal • Strictly Scoped to {overview?.company_name || "Company"} • FERPA & DPDP Compliant</span>
          </div>
          <Badge variant="brand" size="sm">Recruiter Read-Only</Badge>
        </div>

      {/* Top Company Drive Header */}
      {overview && (
        <div className="bg-[#0d1527] p-6 rounded-3xl border border-[#1b2b4d] shadow-md flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-black text-white tracking-tight">{overview.company_name}</h1>
              <Badge variant="success" size="sm">{overview.status.toUpperCase()}</Badge>
              {overview.is_dream && <Badge variant="brand" size="sm">Dream Tier</Badge>}
            </div>
            <p className="text-xs text-slate-400 font-medium">
              Role: <strong className="text-slate-200">{overview.job_role}</strong> • Drive Date:{" "}
              <strong className="text-slate-200">{new Date(overview.drive_date).toLocaleDateString()}</strong> • Mode:{" "}
              <strong className="text-slate-200 uppercase">{overview.mode.replace("_", " ")}</strong> • Version:{" "}
              <strong className="text-emerald-400 font-mono">v{overview.version} ({overview.version_date})</strong>
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap no-print">
            <button
              type="button"
              onClick={() => setActiveTab("export")}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-[#111d38] hover:bg-[#162447] text-slate-200 hover:text-white border border-[#1b2b4d] hover:border-emerald-500/40 text-xs font-bold rounded-xl transition-all cursor-pointer"
            >
              <Download className="w-3.5 h-3.5 text-emerald-400" />
              <span>Download Files</span>
            </button>
            <button
              type="button"
              onClick={() => window.print()}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-[#111d38] hover:bg-[#162447] text-slate-200 hover:text-white border border-[#1b2b4d] hover:border-blue-500/40 text-xs font-bold rounded-xl transition-all cursor-pointer"
            >
              <Printer className="w-3.5 h-3.5 text-blue-400" />
              <span>Print Timetable</span>
            </button>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODULE 1: HOME / MY DRIVE OVERVIEW
      ========================================================================= */}
      {activeTab === "drive" && overview && (
        <div className="space-y-6">
          {/* Key Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-[#0d1527] p-4 rounded-2xl border border-[#1b2b4d] space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Shortlisted Candidates</span>
              <div className="text-2xl font-black text-emerald-400 font-mono">{overview.total_shortlisted}</div>
              <span className="text-[11px] text-slate-400">Approved by Placement Cell</span>
            </div>

            <div className="bg-[#0d1527] p-4 rounded-2xl border border-[#1b2b4d] space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Scheduled Slots</span>
              <div className="text-2xl font-black text-blue-400 font-mono">{overview.total_scheduled}</div>
              <span className="text-[11px] text-slate-400">0 clashes guaranteed</span>
            </div>

            <div className="bg-[#0d1527] p-4 rounded-2xl border border-[#1b2b4d] space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Recruitment Rounds</span>
              <div className="text-2xl font-black text-purple-400 font-mono">{overview.number_of_rounds} Rounds</div>
              <span className="text-[11px] text-slate-400">Technical & Managerial</span>
            </div>

            <div className="bg-[#0d1527] p-4 rounded-2xl border border-[#1b2b4d] space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Compensation Package</span>
              <div className="text-2xl font-black text-amber-400 font-mono">{overview.ctc_lpa} LPA</div>
              <span className="text-[11px] text-slate-400">{overview.is_dream ? "Dream Tier" : "Core Engineering"}</span>
            </div>
          </div>

          {/* Drive Operational Specs */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-[#0d1527] p-6 rounded-3xl border border-[#1b2b4d] space-y-4">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Building2 className="w-4 h-4 text-emerald-400" />
                <span>Drive Execution Profile</span>
              </h2>

              <div className="space-y-3 text-xs">
                <div className="flex justify-between py-2 border-b border-[#1b2b4d]">
                  <span className="text-slate-400">Corporate Entity:</span>
                  <span className="font-bold text-white">{overview.company_name}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-[#1b2b4d]">
                  <span className="text-slate-400">Target Role Title:</span>
                  <span className="font-bold text-white">{overview.job_role}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-[#1b2b4d]">
                  <span className="text-slate-400">Drive Execution Date:</span>
                  <span className="font-bold text-emerald-400">{new Date(overview.drive_date).toLocaleDateString("en-IN", { dateStyle: "full" })}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-[#1b2b4d]">
                  <span className="text-slate-400">Engagement Mode:</span>
                  <span className="font-bold text-white uppercase">{overview.mode.replace("_", " ")}</span>
                </div>
                <div className="flex justify-between py-2">
                  <span className="text-slate-400">Active Rule Version:</span>
                  <span className="font-mono font-bold text-emerald-400">v{overview.version} ({overview.version_date})</span>
                </div>
              </div>
            </div>

            <div className="bg-[#0d1527] p-6 rounded-3xl border border-[#1b2b4d] space-y-4">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Phone className="w-4 h-4 text-blue-400" />
                <span>Institutional Placement Cell Contact</span>
              </h2>

              <div className="p-4 bg-[#080e1c] rounded-2xl border border-[#1b2b4d] space-y-3 text-xs">
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Lead Placement Officer</span>
                  <span className="text-sm font-bold text-white block">{overview.officer_contact.name}</span>
                  <span className="text-[11px] text-emerald-400">{overview.officer_contact.title}</span>
                </div>

                <div className="space-y-1.5 pt-2 border-t border-[#1b2b4d] text-slate-300">
                  <div className="flex items-center gap-2">
                    <Mail className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                    <span>{overview.officer_contact.email}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Phone className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>{overview.officer_contact.phone}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <MapPin className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <span>{overview.officer_contact.office}</span>
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setActiveTab("contact")}
                className="w-full py-2.5 bg-gradient-to-r from-blue-600 via-teal-600 to-emerald-600 hover:from-blue-500 hover:via-teal-500 hover:to-emerald-500 text-white font-bold text-xs rounded-xl shadow-md transition-all cursor-pointer flex items-center justify-center gap-1.5"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>Submit Logistics Request to Placement Officer</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODULE 2: APPROVED SHORTLIST
      ========================================================================= */}
      {activeTab === "shortlist" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Users className="w-4 h-4 text-emerald-400" />
                <span>Approved Candidate Shortlist ({filteredShortlist.length})</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Exclusively displays authorized academic fields approved by the Placement Officer. Personal contact information remains confidential.
              </p>
            </div>

            <a
              href="/api/recruiter/export/shortlist.csv"
              download
              className="flex items-center gap-1.5 px-3.5 py-2 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white text-xs font-bold rounded-xl border border-emerald-400/30 shadow-md transition-all self-start sm:self-auto cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export CSV</span>
            </a>
          </div>

          {/* Search & Filter Bar */}
          <div className="p-4 bg-[#0d1527] rounded-2xl border border-[#1b2b4d] flex flex-col md:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search candidates by name, roll number, or department..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-[#080e1c] border border-[#1b2b4d] rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={branchFilter}
                onChange={(e) => setBranchFilter(e.target.value)}
                className="px-3 py-2 bg-[#080e1c] border border-[#1b2b4d] rounded-xl text-xs text-white focus:outline-none focus:border-emerald-500 cursor-pointer"
              >
                <option value="all">All Disciplines</option>
                {branches.map((b) => (
                  <option key={b} value={b}>
                    {b}
                  </option>
                ))}
              </select>

              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="px-3 py-2 bg-[#080e1c] border border-[#1b2b4d] rounded-xl text-xs text-white focus:outline-none focus:border-emerald-500 cursor-pointer"
              >
                <option value="cgpa">Sort: CGPA (High to Low)</option>
                <option value="name">Sort: Candidate Name</option>
                <option value="roll_no">Sort: Roll Number</option>
              </select>
            </div>
          </div>

          {/* Candidate Table */}
          <div className="bg-[#0d1527] rounded-3xl border border-[#1b2b4d] shadow-md overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#080e1c] border-b border-[#1b2b4d] text-slate-400 font-bold uppercase tracking-wider">
                  <th className="px-5 py-3">Roll No</th>
                  <th className="px-5 py-3">Candidate Full Name</th>
                  <th className="px-5 py-3">Branch</th>
                  <th className="px-5 py-3 text-right">CGPA</th>
                  <th className="px-5 py-3 text-right">10th %</th>
                  <th className="px-5 py-3 text-right">12th %</th>
                  <th className="px-5 py-3 text-center">Backlogs</th>
                  <th className="px-5 py-3 text-center">Verification</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1b2b4d]">
                {filteredShortlist.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-slate-400 text-xs">
                      No candidates match your current search and discipline filters.
                    </td>
                  </tr>
                ) : (
                  filteredShortlist.slice(0, 100).map((s) => (
                    <tr
                      key={s.roll_no}
                      onClick={() => handleInspectCandidate(s.roll_no)}
                      className="hover:bg-[#111d38] cursor-pointer transition-colors group"
                    >
                      <td className="px-5 py-3 font-mono font-bold text-emerald-400">{s.roll_no}</td>
                      <td className="px-5 py-3 font-bold text-white group-hover:text-emerald-300 transition-colors">
                        {s.name}
                      </td>
                      <td className="px-5 py-3 text-slate-300">{s.branch}</td>
                      <td className="px-5 py-3 font-mono font-bold text-emerald-300 text-right">{s.cgpa.toFixed(2)}</td>
                      <td className="px-5 py-3 text-slate-300 text-right">{s.tenth_percentage.toFixed(1)}%</td>
                      <td className="px-5 py-3 text-slate-300 text-right">
                        {s.twelfth_percentage ? `${s.twelfth_percentage.toFixed(1)}%` : "N/A"}
                      </td>
                      <td className="px-5 py-3 text-center">
                        <span
                          className={`font-mono font-bold text-[11px] px-2 py-0.5 rounded-full ${
                            s.active_backlogs === 0
                              ? "bg-emerald-950/60 text-emerald-300 border border-emerald-800/60"
                              : "bg-rose-950/60 text-rose-300 border border-rose-800/60"
                          }`}
                        >
                          {s.active_backlogs}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-center">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleInspectCandidate(s.roll_no);
                          }}
                          className="px-2.5 py-1 bg-[#111d38] hover:bg-emerald-950 text-slate-300 hover:text-emerald-300 rounded-lg border border-[#1b2b4d] hover:border-emerald-500/50 text-[11px] font-semibold transition-all flex items-center gap-1 mx-auto cursor-pointer"
                        >
                          <Eye className="w-3 h-3 text-emerald-400" />
                          <span>Why Eligible</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
            {filteredShortlist.length > 100 && (
              <div className="p-3 bg-[#080e1c] border-t border-[#1b2b4d] text-center text-xs text-slate-400">
                Displaying first 100 of {filteredShortlist.length} candidates. Download full CSV export for complete roster.
              </div>
            )}
          </div>
        </div>
      )}

      {/* =========================================================================
          MODULE 3: "WHY THIS STUDENT" DRAWER / MODAL
      ========================================================================= */}
      {selectedCandidateRoll && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs">
          <div className="bg-[#0d1527] rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-[#1b2b4d] space-y-5 text-slate-100 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-3 border-b border-[#1b2b4d]">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-xl bg-emerald-950/90 text-emerald-400 border border-emerald-800/60 flex items-center justify-center font-bold">
                  <UserCheck className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Why This Student Is In The Room</h3>
                  <p className="text-[11px] text-slate-400">Rule-by-rule qualification verification against company criteria</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedCandidateRoll(null)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-[#111d38] transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {whyLoading ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                Verifying criteria against institutional registry...
              </div>
            ) : whyBreakdown ? (
              <div className="space-y-4">
                {/* Candidate Overview Card */}
                <div className="p-3.5 bg-[#080e1c] rounded-2xl border border-[#1b2b4d] flex items-center justify-between">
                  <div>
                    <span className="text-sm font-bold text-white block">{whyBreakdown.candidate.name}</span>
                    <span className="text-xs text-slate-400">{whyBreakdown.candidate.branch}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-mono font-bold text-emerald-400 block">{whyBreakdown.candidate.roll_no}</span>
                    <span className="text-[11px] font-bold text-slate-300">CGPA: {whyBreakdown.candidate.cgpa.toFixed(2)}</span>
                  </div>
                </div>

                {/* Overall Verdict Banner */}
                <div className="p-3 bg-emerald-950/60 border border-emerald-800/80 rounded-2xl flex items-center gap-2 text-xs text-emerald-300">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span><strong>Candidate Verified:</strong> Meets 100% of {whyBreakdown.company_name} eligibility requirements with 0 policy conflicts.</span>
                </div>

                {/* Criteria Tick-List */}
                <div className="space-y-2">
                  <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block">Company Requirements Checklist</span>
                  <div className="divide-y divide-[#1b2b4d] border border-[#1b2b4d] rounded-2xl overflow-hidden text-xs">
                    {whyBreakdown.criteria.map((c, idx) => (
                      <div key={idx} className="p-3 bg-[#080e1c] flex items-start gap-3">
                        <div className="w-5 h-5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-700/60 flex items-center justify-center shrink-0 mt-0.5">
                          <Check className="w-3.5 h-3.5" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-white">{c.criterion}</span>
                            <span className="font-mono text-emerald-400 font-bold">{c.candidate_value}</span>
                          </div>
                          <p className="text-[11px] text-slate-400 mt-0.5">{c.verification} (Required: {c.required})</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="button"
                    onClick={() => setSelectedCandidateRoll(null)}
                    className="px-4 py-2 bg-[#111d38] hover:bg-[#162447] text-white text-xs font-bold rounded-xl cursor-pointer"
                  >
                    Close Verification
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* =========================================================================
          MODULE 4: SCHEDULE & TIMETABLE
      ========================================================================= */}
      {activeTab === "schedule" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Calendar className="w-4 h-4 text-emerald-400" />
                <span>Interview Round Schedule ({scheduleSlots.length} Allocated Slots)</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Deterministic clash-free timetable verified by the constraint solver.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex items-center bg-[#080e1c] p-1 rounded-xl border border-[#1b2b4d]">
                <button
                  type="button"
                  onClick={() => setScheduleViewMode("list")}
                  className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                    scheduleViewMode === "list" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-white"
                  }`}
                >
                  List View
                </button>
                <button
                  type="button"
                  onClick={() => setScheduleViewMode("day")}
                  className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                    scheduleViewMode === "day" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-white"
                  }`}
                >
                  Day Grid
                </button>
              </div>

              <a
                href="/api/recruiter/export/schedule.csv"
                download
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[#111d38] hover:bg-[#162447] text-slate-200 hover:text-white border border-[#1b2b4d] text-xs font-bold rounded-xl transition-all cursor-pointer"
              >
                <Download className="w-3.5 h-3.5 text-emerald-400" />
                <span>Export CSV</span>
              </a>
            </div>
          </div>

          {scheduleSlots.length === 0 ? (
            <div className="p-12 bg-[#0d1527] border border-[#1b2b4d] rounded-3xl text-center text-xs text-slate-400">
              Interview slots are being generated by the Placement Cell solver. They will appear here once finalized.
            </div>
          ) : (
            <div className="bg-[#0d1527] rounded-3xl border border-[#1b2b4d] shadow-md overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#080e1c] border-b border-[#1b2b4d] text-slate-400 font-bold uppercase tracking-wider">
                    <th className="px-5 py-3">Round</th>
                    <th className="px-5 py-3">Slot Time</th>
                    <th className="px-5 py-3">Venue / Cabin</th>
                    <th className="px-5 py-3">Evaluation Panel</th>
                    <th className="px-5 py-3">Candidate</th>
                    <th className="px-5 py-3">Roll No</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1b2b4d]">
                  {scheduleSlots.slice(0, 100).map((sl) => (
                    <tr key={sl.slot_id} className="hover:bg-[#111d38] transition-colors">
                      <td className="px-5 py-3 font-bold text-white">
                        <Badge variant="brand" size="sm">Round {sl.round_number}</Badge>
                      </td>
                      <td className="px-5 py-3 font-mono font-bold text-emerald-300">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3 text-emerald-400" />
                          <span>{sl.start_time}</span>
                        </div>
                      </td>
                      <td className="px-5 py-3 text-slate-200">
                        <div className="font-semibold text-white">{sl.venue}</div>
                        <div className="text-[10px] text-slate-400">{sl.building}</div>
                      </td>
                      <td className="px-5 py-3 text-slate-300 font-semibold">{sl.panel}</td>
                      <td className="px-5 py-3 font-bold text-white">{sl.candidate_name}</td>
                      <td className="px-5 py-3 font-mono text-emerald-400">{sl.candidate_roll_no}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {scheduleSlots.length > 100 && (
                <div className="p-3 bg-[#080e1c] border-t border-[#1b2b4d] text-center text-xs text-slate-400">
                  Showing first 100 of {scheduleSlots.length} interview slots. Download schedule CSV for full schedule.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          MODULE 5: REQUIREMENTS USED
      ========================================================================= */}
      {activeTab === "requirements" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <FileText className="w-4 h-4 text-emerald-400" />
                <span>Eligibility Conditions Applied For Your Drive</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                These conditions were agreed with the placement cell and applied deterministically to compute the approved shortlist.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {requirements.map((r, idx) => (
              <div key={idx} className="bg-[#0d1527] p-5 rounded-2xl border border-[#1b2b4d] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>{r.rule_type}</span>
                  </span>
                  <button
                    type="button"
                    onClick={() => handleFlagRequirement(r)}
                    className="text-[11px] font-semibold text-amber-400 hover:text-amber-300 flex items-center gap-1 cursor-pointer"
                  >
                    <HelpCircle className="w-3 h-3" />
                    <span>This looks wrong</span>
                  </button>
                </div>

                <div className="p-3 bg-[#080e1c] rounded-xl border border-[#1b2b4d] space-y-1">
                  <div className="text-xs font-bold text-emerald-300">{r.condition}</div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">{r.plain_english}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* =========================================================================
          MODULE 6: CHANGES & VERSIONS
      ========================================================================= */}
      {activeTab === "versions" && (
        <div className="space-y-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <History className="w-4 h-4 text-emerald-400" />
              <span>Drive Version History & Parameter Diffs</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Every cut-off modification, student addition, and schedule recalculation creates an immutable version log.
            </p>
          </div>

          <div className="space-y-4">
            {versions.map((v) => (
              <div key={v.version_number} className="bg-[#0d1527] p-5 rounded-3xl border border-[#1b2b4d] space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#1b2b4d]">
                  <div className="flex items-center gap-3">
                    <Badge variant="brand">Version {v.version_number}</Badge>
                    <span className="text-sm font-bold text-white">{v.headline}</span>
                  </div>
                  <span className="text-xs font-mono text-slate-400">{v.timestamp}</span>
                </div>

                <p className="text-xs text-slate-300 italic bg-[#080e1c] p-3 rounded-xl border border-[#1b2b4d]">
                  "{v.officer_note}"
                </p>

                {/* Diff Table */}
                <div className="border border-[#1b2b4d] rounded-2xl overflow-x-auto text-xs">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="bg-[#080e1c] text-slate-400 font-bold uppercase tracking-wider text-[11px]">
                        <th className="px-4 py-2.5">Parameter</th>
                        <th className="px-4 py-2.5">Previous Value</th>
                        <th className="px-4 py-2.5">Updated Value</th>
                        <th className="px-4 py-2.5">Operational Impact</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1b2b4d]">
                      {v.diff.map((d, dIdx) => (
                        <tr key={dIdx} className="hover:bg-[#111d38]">
                          <td className="px-4 py-2.5 font-bold text-white">{d.parameter}</td>
                          <td className="px-4 py-2.5 text-rose-400 font-mono line-through">{d.previous}</td>
                          <td className="px-4 py-2.5 text-emerald-400 font-mono font-bold">{d.updated}</td>
                          <td className="px-4 py-2.5 text-slate-300 font-medium">{d.impact}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* =========================================================================
          MODULE 7: EXPORT FILES
      ========================================================================= */}
      {activeTab === "export" && overview && (
        <div className="space-y-6">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Download className="w-4 h-4 text-emerald-400" />
              <span>Corporate File Exports (Company Format)</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Downloads data formatted according to the column mappings configured by the Placement Officer for {overview.company_name}.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-[#0d1527] p-6 rounded-3xl border border-[#1b2b4d] space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-950 text-emerald-400 border border-emerald-800/60 flex items-center justify-center font-bold">
                  <Users className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Candidate Shortlist Roster</h3>
                  <p className="text-[11px] text-slate-400">CSV spreadsheet of all {overview.total_shortlisted} verified candidates</p>
                </div>
              </div>

              <div className="p-3 bg-[#080e1c] rounded-xl border border-[#1b2b4d] text-xs text-slate-300 space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-400">Current Drive Version:</span>
                  <span className="font-mono font-bold text-emerald-400">v{overview.version}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Included Columns:</span>
                  <span>Roll No, Full Name, Program, Branch, CGPA, 10th %, 12th %</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Privacy Status:</span>
                  <span className="text-emerald-400 font-semibold">Strictly Redacted (No DOB/Phone)</span>
                </div>
              </div>

              <a
                href="/api/recruiter/export/shortlist.csv"
                download
                className="w-full py-2.5 bg-gradient-to-r from-blue-600 via-teal-600 to-emerald-600 hover:from-blue-500 hover:via-teal-500 hover:to-emerald-500 text-white font-bold text-xs rounded-xl shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer"
              >
                <Download className="w-4 h-4" />
                <span>Download Shortlist (.CSV)</span>
              </a>
            </div>

            <div className="bg-[#0d1527] p-6 rounded-3xl border border-[#1b2b4d] space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-950 text-blue-400 border border-blue-800/60 flex items-center justify-center font-bold">
                  <Calendar className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Interview Schedule Timetable</h3>
                  <p className="text-[11px] text-slate-400">Detailed room and panel allocations for all {scheduleSlots.length} slots</p>
                </div>
              </div>

              <div className="p-3 bg-[#080e1c] rounded-xl border border-[#1b2b4d] text-xs text-slate-300 space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-400">Venue Allocations:</span>
                  <span>Campus Main Block Cabins</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Clash Status:</span>
                  <span className="text-emerald-400 font-bold">0 Clashes Verified</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Format:</span>
                  <span>Standard Corporate Interview Matrix (.CSV)</span>
                </div>
              </div>

              <a
                href="/api/recruiter/export/schedule.csv"
                download
                className="w-full py-2.5 bg-[#111d38] hover:bg-[#162447] text-white font-bold text-xs rounded-xl border border-[#1b2b4d] hover:border-blue-500/50 shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer"
              >
                <Download className="w-4 h-4" />
                <span>Download Schedule (.CSV)</span>
              </a>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODULE 8: CONTACT THE COLLEGE / INQUIRIES
      ========================================================================= */}
      {activeTab === "contact" && overview && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Officer Contact Card */}
            <div className="lg:col-span-1 bg-[#0d1527] p-6 rounded-3xl border border-[#1b2b4d] space-y-4">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Building2 className="w-4 h-4 text-emerald-400" />
                <span>Placement Cell Office</span>
              </h2>

              <div className="p-4 bg-[#080e1c] rounded-2xl border border-[#1b2b4d] space-y-3 text-xs">
                <div>
                  <span className="text-xs font-bold text-white block">{overview.officer_contact.name}</span>
                  <span className="text-[11px] text-emerald-400">{overview.officer_contact.title}</span>
                </div>

                <div className="space-y-1.5 pt-2 border-t border-[#1b2b4d] text-slate-300">
                  <div className="flex items-center gap-2">
                    <Mail className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                    <span>{overview.officer_contact.email}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Phone className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>{overview.officer_contact.phone}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <MapPin className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <span>{overview.officer_contact.office}</span>
                  </div>
                </div>
              </div>

              <div className="p-3 bg-blue-950/40 rounded-xl border border-blue-800/40 text-[11px] text-blue-300 leading-relaxed">
                Need extra panels, adjustments to timing, or candidate status clarifications? Submit an inquiry and our team will update your drive parameters immediately.
              </div>
            </div>

            {/* Right: Submit Request & Inquiries History */}
            <div className="lg:col-span-2 space-y-6">
              {/* Submission Form */}
              <div className="bg-[#0d1527] p-6 rounded-3xl border border-[#1b2b4d] space-y-4">
                <h2 className="text-sm font-bold text-white flex items-center gap-2">
                  <Send className="w-4 h-4 text-emerald-400" />
                  <span>Submit Inquiry or Request to Placement Officer</span>
                </h2>

                {inquirySuccess && <AlertBanner type="success" message={inquirySuccess} onClose={() => setInquirySuccess(null)} />}
                {inquiryError && <AlertBanner type="danger" message={inquiryError} onClose={() => setInquiryError(null)} />}

                <form onSubmit={handleInquirySubmit} className="space-y-3.5 text-xs">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="font-bold text-slate-300 uppercase tracking-wider block mb-1">
                        Category <span className="text-rose-500">*</span>
                      </label>
                      <select
                        value={inquiryCategory}
                        onChange={(e) => setInquiryCategory(e.target.value)}
                        className="w-full px-3 py-2 bg-[#080e1c] border border-[#1b2b4d] rounded-xl text-white cursor-pointer"
                      >
                        <option value="schedule_change">Schedule / Timing Adjustment</option>
                        <option value="logistics">Additional Interview Panel / Room</option>
                        <option value="candidate_inquiry">Question About Specific Candidate</option>
                        <option value="rule_feedback">Rule or Cut-off Clarification</option>
                      </select>
                    </div>

                    <div>
                      <label className="font-bold text-slate-300 uppercase tracking-wider block mb-1">
                        Candidate Roll No (Optional)
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. BT210001 (if regarding student)"
                        value={inquiryCandidateRoll}
                        onChange={(e) => setInquiryCandidateRoll(e.target.value)}
                        className="w-full px-3 py-2 bg-[#080e1c] border border-[#1b2b4d] rounded-xl text-white"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="font-bold text-slate-300 uppercase tracking-wider block mb-1">
                      Subject <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Need one more interview panel starting at 11:00 AM..."
                      value={inquirySubject}
                      onChange={(e) => setInquirySubject(e.target.value)}
                      className="w-full px-3 py-2 bg-[#080e1c] border border-[#1b2b4d] rounded-xl text-white"
                    />
                  </div>

                  <div>
                    <label className="font-bold text-slate-300 uppercase tracking-wider block mb-1">
                      Detailed Instructions / Message <span className="text-rose-500">*</span>
                    </label>
                    <textarea
                      rows={3}
                      required
                      placeholder="Provide specific details so our placement coordinators can assist you..."
                      value={inquiryMessage}
                      onChange={(e) => setInquiryMessage(e.target.value)}
                      className="w-full px-3 py-2 bg-[#080e1c] border border-[#1b2b4d] rounded-xl text-white"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={inquirySubmitting}
                    className="px-5 py-2.5 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white font-bold text-xs rounded-xl shadow-md transition-all cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>{inquirySubmitting ? "Sending..." : "Submit Inquiry to Officer"}</span>
                  </button>
                </form>
              </div>

              {/* Inquiries Thread History */}
              <div className="bg-[#0d1527] p-6 rounded-3xl border border-[#1b2b4d] space-y-4">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-emerald-400" />
                  <span>Previous Requests & Official Responses ({inquiries.length})</span>
                </h3>

                {inquiries.length === 0 ? (
                  <div className="p-6 bg-[#080e1c] rounded-2xl text-center text-xs text-slate-400">
                    No requests submitted yet.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {inquiries.map((inq) => (
                      <div key={inq.id} className="p-4 bg-[#080e1c] rounded-2xl border border-[#1b2b4d] space-y-2 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-white">{inq.title}</span>
                          <Badge
                            variant={inq.status === "answered" || inq.status === "approved" ? "success" : "warning"}
                            size="sm"
                          >
                            {inq.status.toUpperCase()}
                          </Badge>
                        </div>
                        <p className="text-slate-300">{inq.description}</p>
                        <div className="text-[10px] text-slate-400">Submitted on {new Date(inq.submitted_at).toLocaleString()}</div>

                        {inq.officer_response && (
                          <div className="mt-2 p-3 bg-emerald-950/40 border border-emerald-800/40 rounded-xl space-y-1">
                            <span className="text-[10px] uppercase font-bold text-emerald-400 block">
                              Officer Response ({inq.officer_name || "Head T&P"})
                            </span>
                            <p className="text-emerald-200">{inq.officer_response}</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODULE 9: ON-THE-DAY ATTENDANCE VIEW
      ========================================================================= */}
      {activeTab === "ontheday" && (
        <div className="space-y-6">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-emerald-400" />
              <span>On-The-Day Candidate Floor Attendance</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Live updates recorded by student coordinators stationed outside interview cabins.
            </p>
          </div>

          {attendance && attendance.enabled ? (
            <div className="space-y-6">
              {/* Counters */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-[#0d1527] p-4 rounded-2xl border border-[#1b2b4d] space-y-1">
                  <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider block">Present</span>
                  <div className="text-2xl font-black text-emerald-400 font-mono">{attendance.present_count}</div>
                  <span className="text-[11px] text-slate-400">Checked into room</span>
                </div>

                <div className="bg-[#0d1527] p-4 rounded-2xl border border-[#1b2b4d] space-y-1">
                  <span className="text-[10px] font-bold text-rose-400 uppercase tracking-wider block">Absent</span>
                  <div className="text-2xl font-black text-rose-400 font-mono">{attendance.absent_count}</div>
                  <span className="text-[11px] text-slate-400">Marked absent</span>
                </div>

                <div className="bg-[#0d1527] p-4 rounded-2xl border border-[#1b2b4d] space-y-1">
                  <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider block">Late / In Transit</span>
                  <div className="text-2xl font-black text-amber-400 font-mono">{attendance.late_count}</div>
                  <span className="text-[11px] text-slate-400">Arriving shortly</span>
                </div>

                <div className="bg-[#0d1527] p-4 rounded-2xl border border-[#1b2b4d] space-y-1">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Pending Slot</span>
                  <div className="text-2xl font-black text-slate-300 font-mono">{attendance.pending_count}</div>
                  <span className="text-[11px] text-slate-400">Awaiting slot time</span>
                </div>
              </div>

              {/* Room Breakdown Grid */}
              <div className="bg-[#0d1527] p-6 rounded-3xl border border-[#1b2b4d] space-y-4">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">Interview Cabin Breakdown</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {Object.entries(attendance.rooms || {}).map(([room, counts]) => (
                    <div key={room} className="p-4 bg-[#080e1c] rounded-2xl border border-[#1b2b4d] space-y-2 text-xs">
                      <div className="flex items-center justify-between pb-2 border-b border-[#1b2b4d]">
                        <span className="font-bold text-white">{room}</span>
                        <span className="font-mono text-emerald-400 font-bold">{counts.total} Candidates</span>
                      </div>
                      <div className="flex justify-between text-[11px]">
                        <span className="text-slate-400">Present:</span>
                        <span className="font-bold text-emerald-400">{counts.present}</span>
                      </div>
                      <div className="flex justify-between text-[11px]">
                        <span className="text-slate-400">Absent:</span>
                        <span className="font-bold text-rose-400">{counts.absent}</span>
                      </div>
                      <div className="flex justify-between text-[11px]">
                        <span className="text-slate-400">Late / Rescheduling:</span>
                        <span className="font-bold text-amber-400">{counts.late}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 bg-[#0d1527] border border-[#1b2b4d] rounded-3xl text-center text-xs text-slate-400">
              Live floor attendance is not active for this drive. Contact the Placement Officer if you require check-in tracking.
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          MODULE 10: CONFIRMED SELECTIONS / RESULTS
      ========================================================================= */}
      {activeTab === "results" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Confirmed Selected Candidates ({resultsList.length})</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Official offer extensions recorded and confirmed by the Placement Officer.
              </p>
            </div>
          </div>

          {resultsList.length === 0 ? (
            <div className="p-12 bg-[#0d1527] border border-[#1b2b4d] rounded-3xl text-center text-xs text-slate-400">
              Final selection results have not yet been released by the Placement Officer. Once interviews conclude and offers are confirmed, the official roster will be displayed here.
            </div>
          ) : (
            <div className="bg-[#0d1527] rounded-3xl border border-[#1b2b4d] shadow-md overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#080e1c] border-b border-[#1b2b4d] text-slate-400 font-bold uppercase tracking-wider">
                    <th className="px-5 py-3">Roll No</th>
                    <th className="px-5 py-3">Selected Candidate</th>
                    <th className="px-5 py-3">Branch</th>
                    <th className="px-5 py-3 text-right">Offered CTC</th>
                    <th className="px-5 py-3 text-center">Status</th>
                    <th className="px-5 py-3 text-right">Confirmed Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1b2b4d]">
                  {resultsList.map((c) => (
                    <tr key={c.roll_no} className="hover:bg-[#111d38] transition-colors">
                      <td className="px-5 py-3 font-mono font-bold text-emerald-400">{c.roll_no}</td>
                      <td className="px-5 py-3 font-bold text-white">{c.name}</td>
                      <td className="px-5 py-3 text-slate-300">{c.branch}</td>
                      <td className="px-5 py-3 font-mono font-bold text-emerald-300 text-right">{c.ctc_lpa} LPA</td>
                      <td className="px-5 py-3 text-center">
                        <Badge variant="success" size="sm">{c.status}</Badge>
                      </td>
                      <td className="px-5 py-3 text-slate-400 text-right font-mono">{c.confirmed_date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
      </main>
    </div>
  );
};
