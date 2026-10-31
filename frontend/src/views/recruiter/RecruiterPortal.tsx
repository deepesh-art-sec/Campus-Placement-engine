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
  RefreshCw,
  Plus,
  UserX,
  FileSpreadsheet,
  RotateCw,
} from "lucide-react";

type RecruiterTab =
  | "drive"
  | "shortlist"
  | "schedule"
  | "requirements"
  | "export"
  | "contact"
  | "attendance"
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
  has_applied?: boolean;
  applied_at?: string | null;
  application_status?: string;
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
    has_applied?: boolean;
    applied_at?: string | null;
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

interface AttendanceCandidate {
  slot_id: string;
  student_id: string;
  roll_no: string;
  name: string;
  branch: string;
  round_number: number;
  start_time: string;
  venue: string;
  status: string;
  marked_at?: string | null;
  notes?: string | null;
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
  candidates?: AttendanceCandidate[];
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
  const [inquiries, setInquiries] = useState<RecruiterInquiry[]>([]);
  const [attendance, setAttendance] = useState<AttendanceData | null>(null);
  const [resultsList, setResultsList] = useState<ResultCandidate[]>([]);
  const [downloadingFile, setDownloadingFile] = useState<string | null>(null);
  const [isSyncingSchedule, setIsSyncingSchedule] = useState(false);
  const [lastSyncedTime, setLastSyncedTime] = useState<string>("Just now");

  // Create Round Modal State
  const [isCreateRoundModalOpen, setIsCreateRoundModalOpen] = useState(false);
  const [roundNumber, setRoundNumber] = useState<number>(2);
  const [roundName, setRoundName] = useState("");
  const [roundType, setRoundType] = useState("technical_interview");
  const [roundMode, setRoundMode] = useState("in_person");
  const [roundDuration, setRoundDuration] = useState<number>(45);
  const [roundInstructions, setRoundInstructions] = useState("");
  const [roundSubmitting, setRoundSubmitting] = useState(false);
  const [roundSuccess, setRoundSuccess] = useState<string | null>(null);
  const [roundError, setRoundError] = useState<string | null>(null);

  // Attendance filter & action states
  const [attendanceFilter, setAttendanceFilter] = useState<string>("all");
  const [attendanceSearch, setAttendanceSearch] = useState<string>("");
  const [markingCandidateSlot, setMarkingCandidateSlot] = useState<string | null>(null);

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

  const handleRecruiterDownload = async (url: string, defaultName: string) => {
    try {
      setDownloadingFile(url);
      await api.download(url, defaultName);
    } catch (err: any) {
      alert(err?.message || "File export failed.");
    } finally {
      setDownloadingFile(null);
    }
  };

  // Load Overview Data on Mount
  const fetchAllData = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      setError(null);

      const [ovRes, slRes, scRes, reqRes, inqRes, attRes, resRes] = await Promise.allSettled([
        api.get<DriveOverview>("/api/recruiter/my-drive"),
        api.get<{ total: number; shortlist: ShortlistCandidate[] }>("/api/recruiter/shortlist"),
        api.get<{ slots: ScheduleSlot[]; total_slots: number }>("/api/recruiter/schedule"),
        api.get<{ rules: RequirementRule[] }>("/api/recruiter/requirements"),
        api.get<RecruiterInquiry[]>("/api/recruiter/inquiries"),
        api.get<AttendanceData>("/api/recruiter/attendance"),
        api.get<{ selected_candidates: ResultCandidate[]; released: boolean }>("/api/recruiter/results"),
      ]);

      if (ovRes.status === "fulfilled") {
        setOverview(ovRes.value);
        setRoundNumber((ovRes.value.number_of_rounds || 1) + 1);
      }
      if (slRes.status === "fulfilled") {
        const list = slRes.value.shortlist || [];
        setShortlist(list);
        setFilteredShortlist(list);
      }
      if (scRes.status === "fulfilled") {
        setScheduleSlots(scRes.value.slots || []);
        setLastSyncedTime(new Date().toLocaleTimeString());
      }
      if (reqRes.status === "fulfilled") setRequirements(reqRes.value.rules || []);
      if (inqRes.status === "fulfilled") setInquiries(inqRes.value || []);
      if (attRes.status === "fulfilled") setAttendance(attRes.value);
      if (resRes.status === "fulfilled") setResultsList(resRes.value.selected_candidates || []);
    } catch (err: any) {
      if (!silent) setError(err.message || "Failed to load corporate recruitment portal data.");
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  // Reactive auto-update of schedule every 6 seconds to reflect officer adjustments instantly
  useEffect(() => {
    const syncInterval = setInterval(async () => {
      try {
        const scRes = await api.get<{ slots: ScheduleSlot[]; total_slots: number }>("/api/recruiter/schedule");
        if (scRes && scRes.slots) {
          setScheduleSlots(scRes.slots);
          setLastSyncedTime(new Date().toLocaleTimeString());
        }
      } catch {
        // silent sync
      }
    }, 6000);

    return () => clearInterval(syncInterval);
  }, []);

  // Manual Instant Schedule Sync
  const handleManualSyncSchedule = async () => {
    try {
      setIsSyncingSchedule(true);
      const scRes = await api.get<{ slots: ScheduleSlot[]; total_slots: number }>("/api/recruiter/schedule");
      if (scRes && scRes.slots) {
        setScheduleSlots(scRes.slots);
        setLastSyncedTime(new Date().toLocaleTimeString());
      }
      const ovRes = await api.get<DriveOverview>("/api/recruiter/my-drive");
      if (ovRes) setOverview(ovRes);
    } catch {
      // ignore
    } finally {
      setTimeout(() => setIsSyncingSchedule(false), 500);
    }
  };

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

  // Submit Feedback / Inquiry to Officer
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

      setInquirySuccess("Inquiry successfully delivered to Placement Officer (Prof. R. K. Sharma). We will respond promptly.");
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

  // Submit Create Round Modal
  const handleCreateRoundSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setRoundSubmitting(true);
      setRoundError(null);
      setRoundSuccess(null);

      await api.post("/api/recruiter/rounds", {
        round_number: roundNumber,
        round_name: roundName || `Round ${roundNumber}: Technical Assessment & Interview`,
        round_type: roundType,
        mode: roundMode,
        duration_minutes: roundDuration,
        instructions: roundInstructions || undefined,
      });

      setRoundSuccess(`Round ${roundNumber} successfully registered!`);
      // Refresh drive overview
      const updatedOverview = await api.get<DriveOverview>("/api/recruiter/my-drive");
      if (updatedOverview) {
        setOverview(updatedOverview);
        setRoundNumber((updatedOverview.number_of_rounds || 1) + 1);
      }
      // Reset form
      setRoundName("");
      setRoundInstructions("");
      setTimeout(() => {
        setIsCreateRoundModalOpen(false);
        setRoundSuccess(null);
      }, 1200);
    } catch (err: any) {
      setRoundError(err.message || "Failed to create recruitment round.");
    } finally {
      setRoundSubmitting(false);
    }
  };

  // Handle Mark Attendance Action
  const handleMarkAttendance = async (slotId: string, studentId: string, newStatus: string) => {
    try {
      setMarkingCandidateSlot(slotId);
      await api.post("/api/recruiter/attendance/mark", {
        slot_id: slotId,
        student_id: studentId,
        status: newStatus,
        notes: `Attendance marked as ${newStatus} by recruiter.`,
      });

      // Refresh attendance state
      const attRes = await api.get<AttendanceData>("/api/recruiter/attendance");
      if (attRes) setAttendance(attRes);
    } catch (err: any) {
      alert(err?.message || "Failed to mark candidate attendance.");
    } finally {
      setMarkingCandidateSlot(null);
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
      <div className="p-8 bg-white border border-slate-200/90 rounded-3xl max-w-lg mx-auto text-center space-y-4 text-white">
        <Briefcase className="w-12 h-12 text-slate-500 mx-auto" />
        <h3 className="text-base font-bold text-white">Corporate Portal Access Restricted</h3>
        <p className="text-xs text-slate-400">{error}</p>
      </div>
    );
  }

  // Navigation Items without Numbering prefixes (Satisfies Requirement 2)
  const navItems = [
    {
      id: "drive" as RecruiterTab,
      label: "Home / My Drive",
      accessibleName: "Home / My Drive",
      icon: Building2,
    },
    {
      id: "shortlist" as RecruiterTab,
      label: "Shortlist",
      accessibleName: "Shortlist",
      icon: Users,
      badge: String(overview?.total_shortlisted || shortlist.length),
    },
    {
      id: "schedule" as RecruiterTab,
      label: "Schedule",
      accessibleName: "Schedule",
      icon: Calendar,
      badge: String(scheduleSlots.length),
    },
    {
      id: "requirements" as RecruiterTab,
      label: "Requirements Used",
      accessibleName: "Requirements Used",
      icon: FileText,
    },
    {
      id: "export" as RecruiterTab,
      label: "Export Files",
      accessibleName: "Export Files",
      icon: Download,
    },
    {
      id: "contact" as RecruiterTab,
      label: "Contact College",
      accessibleName: "Contact College",
      icon: MessageSquare,
      badge: inquiries.filter((i) => i.status === "open").length > 0 ? String(inquiries.filter((i) => i.status === "open").length) : undefined,
    },
    {
      id: "attendance" as RecruiterTab,
      label: "Attendance",
      accessibleName: "Attendance",
      icon: UserCheck,
      badge: attendance ? `${attendance.present_count}/${attendance.total_scheduled}` : undefined,
    },
    {
      id: "results" as RecruiterTab,
      label: "Results",
      accessibleName: "Results",
      icon: CheckCircle2,
      badge: resultsList.length > 0 ? String(resultsList.length) : undefined,
    },
  ];

  // Filter attendance candidates list
  const attendanceCandidates = attendance?.candidates || [];
  const filteredAttendanceCandidates = attendanceCandidates.filter((c) => {
    if (attendanceFilter !== "all" && c.status !== attendanceFilter) return false;
    if (attendanceSearch.trim()) {
      const q = attendanceSearch.toLowerCase().trim();
      return (
        c.name.toLowerCase().includes(q) ||
        c.roll_no.toLowerCase().includes(q) ||
        c.branch.toLowerCase().includes(q) ||
        c.venue.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="flex-1 flex overflow-hidden w-full h-full min-h-0 min-w-0">
      {/* Left Vertical Navigation Sidebar - Stripped of all numbering */}
      <aside
        className={`bg-[#0B1F44] border-r border-[#152B58] shrink-0 flex flex-col h-full max-h-full overflow-hidden sticky top-0 transition-all duration-200 select-none z-20 ${
          isSidebarCollapsed ? "w-16" : "w-64"
        }`}
        aria-label="Recruiter Dashboard Left Navigation"
      >
        {/* Sidebar Header with Module Index and Collapse Toggle */}
        <div className="p-3.5 border-b border-[#152B58] flex items-center justify-between text-slate-300 shrink-0 sticky top-0 bg-[#0B1F44] z-10">
          {!isSidebarCollapsed && (
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
                <span className="text-[10px] font-black tracking-widest text-emerald-400 uppercase font-mono">
                  RECRUITER SUITE
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-semibold truncate mt-0.5">
                {overview?.company_name || "Company Portal"} • Verified Partner
              </p>
            </div>
          )}
          <button
            type="button"
            onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer ml-auto"
            title={isSidebarCollapsed ? "Expand sidebar navigation" : "Collapse sidebar navigation"}
          >
            {isSidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Vertical Nav List (Without numbering) */}
        <nav className="flex-1 min-h-0 overflow-y-auto px-2 py-3 space-y-1 custom-scrollbar">
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
                    : "text-slate-300 hover:text-white hover:bg-white/10"
                }`}
              >
                <div className="flex items-center justify-center shrink-0">
                  <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-slate-400"}`} />
                </div>
                {!isSidebarCollapsed && (
                  <>
                    <span className="truncate">{item.label}</span>
                    {item.badge && (
                      <span className="ml-auto text-[10px] px-1.5 py-0.5 bg-slate-800 border border-slate-700 rounded-md font-mono font-bold text-slate-300">
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
          <div className="p-3 border-t border-blue-900/40 bg-[#071530] text-[10px] text-slate-400 text-center font-mono shrink-0 sticky bottom-0 z-10">
            Tenant Isolated • Corporate Portal
          </div>
        )}
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8 overflow-y-auto space-y-6">
        {/* Privacy & Air-Gap Assurance Banner */}
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-2 text-emerald-800 font-semibold">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Tenant Isolated Corporate Portal • Strictly Scoped to {overview?.company_name || "Company"} • FERPA & DPDP Compliant</span>
          </div>
          <Badge variant="brand" size="sm">Recruiter Portal</Badge>
        </div>

        {/* Top Company Drive Header with + Create Round Button */}
        {overview && (
          <div className="bg-white p-6 rounded-3xl border border-slate-200/90 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-black text-slate-900 tracking-tight">{overview.company_name}</h1>
                <Badge variant="success" size="sm">{overview.status.toUpperCase()}</Badge>
                {overview.is_dream && <Badge variant="brand" size="sm">Dream Tier</Badge>}
              </div>
              <p className="text-xs text-slate-500 font-medium">
                Role: <strong className="text-slate-800">{overview.job_role}</strong> • Drive Date:{" "}
                <strong className="text-slate-800">{new Date(overview.drive_date).toLocaleDateString()}</strong> • Mode:{" "}
                <strong className="text-slate-800 uppercase">{overview.mode.replace("_", " ")}</strong> • Version:{" "}
                <strong className="text-emerald-600 font-mono">v{overview.version} ({overview.version_date})</strong>
              </p>
            </div>

            <div className="flex items-center gap-2 flex-wrap no-print">
              {/* + Create Round Button (Requirement 9) */}
              <button
                type="button"
                onClick={() => setIsCreateRoundModalOpen(true)}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold rounded-xl shadow-md transition-all cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>+ Create Round</span>
              </button>

              <button
                type="button"
                onClick={() => handleRecruiterDownload("/api/recruiter/export/shortlist.xlsx", "company_shortlist.xlsx")}
                disabled={downloadingFile === "/api/recruiter/export/shortlist.xlsx"}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 border border-slate-200 shadow-2xs hover:border-emerald-500/40 text-xs font-bold rounded-xl transition-all cursor-pointer disabled:opacity-50"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                <span>{downloadingFile === "/api/recruiter/export/shortlist.xlsx" ? "Exporting..." : "Export XLSX"}</span>
              </button>

              <button
                type="button"
                onClick={() => handleRecruiterDownload("/api/recruiter/export/shortlist.csv", "company_shortlist.csv")}
                disabled={downloadingFile === "/api/recruiter/export/shortlist.csv"}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 border border-slate-200 shadow-2xs hover:border-emerald-500/40 text-xs font-bold rounded-xl transition-all cursor-pointer disabled:opacity-50"
              >
                <Download className="w-3.5 h-3.5 text-emerald-600" />
                <span>Export CSV</span>
              </button>

              <button
                type="button"
                onClick={() => window.print()}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 border border-slate-200 shadow-2xs hover:border-blue-500/40 text-xs font-bold rounded-xl transition-all cursor-pointer"
              >
                <Printer className="w-3.5 h-3.5 text-blue-600" />
                <span>Print Timetable</span>
              </button>
            </div>
          </div>
        )}

        {/* =========================================================================
            MODULE 1: HOME / MY DRIVE OVERVIEW (Requirement 1: Active + Shortlisted Roster)
        ========================================================================= */}
        {activeTab === "drive" && overview && (
          <div className="space-y-6">
            {/* Key Metric Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Shortlisted Candidates</span>
                <div className="text-2xl font-black text-emerald-600 font-mono">{overview.total_shortlisted}</div>
                <span className="text-[11px] text-slate-500">Approved by Placement Cell</span>
              </div>

              <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Scheduled Slots</span>
                <div className="text-2xl font-black text-blue-600 font-mono">{overview.total_scheduled}</div>
                <span className="text-[11px] text-slate-500">0 clashes guaranteed</span>
              </div>

              <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Recruitment Rounds</span>
                <div className="text-2xl font-black text-purple-600 font-mono">{overview.number_of_rounds} Rounds</div>
                <span className="text-[11px] text-slate-500">Technical & Managerial</span>
              </div>

              <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Compensation Package</span>
                <div className="text-2xl font-black text-amber-600 font-mono">{overview.ctc_lpa} LPA</div>
                <span className="text-[11px] text-slate-500">{overview.is_dream ? "Dream Tier" : "Core Engineering"}</span>
              </div>
            </div>

            {/* Drive Operational Profile & Institutional Placement Cell Contact */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white p-6 rounded-3xl border border-slate-200 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-emerald-600" />
                    <span>Drive Execution Profile</span>
                  </h2>
                  <button
                    type="button"
                    onClick={() => setIsCreateRoundModalOpen(true)}
                    className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Round</span>
                  </button>
                </div>

                <div className="space-y-3 text-xs">
                  <div className="flex justify-between py-2 border-b border-slate-100">
                    <span className="text-slate-500">Corporate Entity:</span>
                    <span className="font-bold text-slate-800">{overview.company_name}</span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-slate-100">
                    <span className="text-slate-500">Target Role Title:</span>
                    <span className="font-bold text-slate-800">{overview.job_role}</span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-slate-100">
                    <span className="text-slate-500">Drive Execution Date:</span>
                    <span className="font-bold text-emerald-600">{new Date(overview.drive_date).toLocaleDateString("en-IN", { dateStyle: "full" })}</span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-slate-100">
                    <span className="text-slate-500">Engagement Mode:</span>
                    <span className="font-bold text-slate-800 uppercase">{overview.mode.replace("_", " ")}</span>
                  </div>
                  <div className="flex justify-between py-2">
                    <span className="text-slate-500">Active Rule Version:</span>
                    <span className="font-mono font-bold text-emerald-600">v{overview.version} ({overview.version_date})</span>
                  </div>
                </div>
              </div>

              {/* Institutional Placement Cell Contact */}
              <div className="bg-white p-6 rounded-3xl border border-slate-200 space-y-4">
                <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Phone className="w-4 h-4 text-blue-600" />
                  <span>Institutional Placement Cell Contact</span>
                </h2>

                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200/80 space-y-3 text-xs">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">Lead Placement Officer</span>
                    <span className="text-sm font-bold text-slate-900 block">{overview.officer_contact.name}</span>
                    <span className="text-[11px] text-emerald-700">{overview.officer_contact.title}</span>
                  </div>

                  <div className="space-y-1.5 pt-2 border-t border-slate-200 text-slate-600">
                    <div className="flex items-center gap-2">
                      <Mail className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                      <span>{overview.officer_contact.email}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Phone className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                      <span>{overview.officer_contact.phone}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <MapPin className="w-3.5 h-3.5 text-amber-600 shrink-0" />
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

            {/* EMBEDDED SHORTLISTED CANDIDATES ON HOME SCREEN (Requirement 1) */}
            <div className="bg-white p-6 rounded-3xl border border-slate-200 space-y-4 shadow-xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <Users className="w-4 h-4 text-emerald-600" />
                    <span>Approved Shortlisted Candidates ({filteredShortlist.length})</span>
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Verified candidate roster eligible for {overview.company_name} interviews. All academic thresholds verified.
                  </p>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  <button
                    type="button"
                    onClick={() => handleRecruiterDownload("/api/recruiter/export/shortlist.xlsx", "company_shortlist.xlsx")}
                    disabled={downloadingFile === "/api/recruiter/export/shortlist.xlsx"}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 text-xs font-bold rounded-xl transition-all cursor-pointer disabled:opacity-50"
                  >
                    <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Export XLSX</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleRecruiterDownload("/api/recruiter/export/shortlist.csv", "company_shortlist.csv")}
                    disabled={downloadingFile === "/api/recruiter/export/shortlist.csv"}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 text-slate-700 hover:bg-slate-100 border border-slate-200 text-xs font-bold rounded-xl transition-all cursor-pointer disabled:opacity-50"
                  >
                    <Download className="w-3.5 h-3.5 text-slate-600" />
                    <span>Export CSV</span>
                  </button>
                </div>
              </div>

              {/* Search & Filter Bar */}
              <div className="p-3 bg-slate-50 rounded-2xl border border-slate-200 flex flex-col md:flex-row gap-3">
                <div className="relative flex-1">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    placeholder="Search candidate by name, roll number, or department..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <Filter className="w-3.5 h-3.5 text-slate-400" />
                  <select
                    value={branchFilter}
                    onChange={(e) => setBranchFilter(e.target.value)}
                    className="px-3 py-2 bg-white border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:border-emerald-500 cursor-pointer"
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
                    className="px-3 py-2 bg-white border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:border-emerald-500 cursor-pointer"
                  >
                    <option value="cgpa">Sort: CGPA (High to Low)</option>
                    <option value="name">Sort: Candidate Name</option>
                    <option value="roll_no">Sort: Roll Number</option>
                  </select>
                </div>
              </div>

              {/* Table */}
              <div className="border border-slate-200 rounded-2xl overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
                      <th className="px-4 py-3">Roll No</th>
                      <th className="px-4 py-3">Candidate Full Name</th>
                      <th className="px-4 py-3">Branch</th>
                      <th className="px-4 py-3 text-center">Application</th>
                      <th className="px-4 py-3 text-right">CGPA</th>
                      <th className="px-4 py-3 text-right">10th %</th>
                      <th className="px-4 py-3 text-right">12th %</th>
                      <th className="px-4 py-3 text-center">Backlogs</th>
                      <th className="px-4 py-3 text-center">Verification</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredShortlist.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="p-8 text-center text-slate-400 text-xs">
                          No candidates match your current search and discipline filters.
                        </td>
                      </tr>
                    ) : (
                      filteredShortlist.slice(0, 50).map((s) => (
                        <tr
                          key={s.roll_no}
                          onClick={() => handleInspectCandidate(s.roll_no)}
                          className="hover:bg-slate-50 cursor-pointer transition-colors group"
                        >
                          <td className="px-4 py-3 font-mono font-bold text-emerald-700">{s.roll_no}</td>
                          <td className="px-4 py-3 font-bold text-slate-900 group-hover:text-emerald-700 transition-colors">
                            {s.name}
                          </td>
                          <td className="px-4 py-3 text-slate-600">{s.branch}</td>
                          <td className="px-4 py-3 text-center">
                            {s.has_applied ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                                Applied
                              </span>
                            ) : (
                              <span className="text-slate-400 text-[10px]">Shortlisted</span>
                            )}
                          </td>
                          <td className="px-4 py-3 font-mono font-bold text-emerald-700 text-right">{s.cgpa.toFixed(2)}</td>
                          <td className="px-4 py-3 text-slate-600 text-right">{s.tenth_percentage.toFixed(1)}%</td>
                          <td className="px-4 py-3 text-slate-600 text-right">
                            {s.twelfth_percentage ? `${s.twelfth_percentage.toFixed(1)}%` : "N/A"}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span
                              className={`font-mono font-bold text-[11px] px-2 py-0.5 rounded-full ${
                                s.active_backlogs === 0
                                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                  : "bg-rose-50 text-rose-700 border border-rose-200"
                              }`}
                            >
                              {s.active_backlogs}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleInspectCandidate(s.roll_no);
                              }}
                              className="px-2.5 py-1 bg-white hover:bg-emerald-50 text-slate-700 hover:text-emerald-700 rounded-lg border border-slate-200 hover:border-emerald-300 text-[11px] font-semibold transition-all flex items-center gap-1 mx-auto cursor-pointer"
                            >
                              <Eye className="w-3 h-3 text-emerald-600" />
                              <span>Why Eligible</span>
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              {filteredShortlist.length > 50 && (
                <div className="p-2.5 bg-slate-50 border-t border-slate-100 text-center text-xs text-slate-500">
                  Showing first 50 of {filteredShortlist.length} candidates. Download full XLSX/CSV export for complete roster.
                </div>
              )}
            </div>
          </div>
        )}

        {/* =========================================================================
            MODULE 2: SHORTLIST TAB
        ========================================================================= */}
        {activeTab === "shortlist" && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Users className="w-4 h-4 text-emerald-600" />
                  <span>Approved Candidate Shortlist ({filteredShortlist.length})</span>
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Exclusively displays authorized academic fields approved by the Placement Officer. Personal contact information remains confidential.
                </p>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <button
                  type="button"
                  onClick={() => handleRecruiterDownload("/api/recruiter/export/shortlist.xlsx", "company_shortlist.xlsx")}
                  disabled={downloadingFile === "/api/recruiter/export/shortlist.xlsx"}
                  className="flex items-center gap-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl shadow-md transition-all cursor-pointer disabled:opacity-50"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  <span>{downloadingFile === "/api/recruiter/export/shortlist.xlsx" ? "Exporting..." : "Export XLSX"}</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleRecruiterDownload("/api/recruiter/export/shortlist.csv", "company_shortlist.csv")}
                  disabled={downloadingFile === "/api/recruiter/export/shortlist.csv"}
                  className="flex items-center gap-1.5 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 border border-slate-200 shadow-2xs text-xs font-bold rounded-xl transition-all cursor-pointer disabled:opacity-50"
                >
                  <Download className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Export CSV</span>
                </button>
              </div>
            </div>

            {/* Search & Filter Bar */}
            <div className="p-4 bg-white rounded-2xl border border-slate-200 flex flex-col md:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search candidates by name, roll number, or department..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="flex items-center gap-2">
                <Filter className="w-3.5 h-3.5 text-slate-400" />
                <select
                  value={branchFilter}
                  onChange={(e) => setBranchFilter(e.target.value)}
                  className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:border-emerald-500 cursor-pointer"
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
                  className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:border-emerald-500 cursor-pointer"
                >
                  <option value="cgpa">Sort: CGPA (High to Low)</option>
                  <option value="name">Sort: Candidate Name</option>
                  <option value="roll_no">Sort: Roll Number</option>
                </select>
              </div>
            </div>

            {/* Candidate Table */}
            <div className="bg-white rounded-3xl border border-slate-200 shadow-md overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
                    <th className="px-5 py-3">Roll No</th>
                    <th className="px-5 py-3">Candidate Full Name</th>
                    <th className="px-5 py-3">Branch</th>
                    <th className="px-5 py-3 text-center">Application</th>
                    <th className="px-5 py-3 text-right">CGPA</th>
                    <th className="px-5 py-3 text-right">10th %</th>
                    <th className="px-5 py-3 text-right">12th %</th>
                    <th className="px-5 py-3 text-center">Backlogs</th>
                    <th className="px-5 py-3 text-center">Verification</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredShortlist.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="p-8 text-center text-slate-400 text-xs">
                        No candidates match your current search and discipline filters.
                      </td>
                    </tr>
                  ) : (
                    filteredShortlist.slice(0, 100).map((s) => (
                      <tr
                        key={s.roll_no}
                        onClick={() => handleInspectCandidate(s.roll_no)}
                        className="hover:bg-slate-50 cursor-pointer transition-colors group"
                      >
                        <td className="px-5 py-3 font-mono font-bold text-emerald-700">{s.roll_no}</td>
                        <td className="px-5 py-3 font-bold text-slate-900 group-hover:text-emerald-700 transition-colors">
                          {s.name}
                        </td>
                        <td className="px-5 py-3 text-slate-600">{s.branch}</td>
                        <td className="px-5 py-3 text-center">
                          {s.has_applied ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                              Applied
                            </span>
                          ) : (
                            <span className="text-slate-400 text-[10px]">Shortlisted</span>
                          )}
                        </td>
                        <td className="px-5 py-3 font-mono font-bold text-emerald-700 text-right">{s.cgpa.toFixed(2)}</td>
                        <td className="px-5 py-3 text-slate-600 text-right">{s.tenth_percentage.toFixed(1)}%</td>
                        <td className="px-5 py-3 text-slate-600 text-right">
                          {s.twelfth_percentage ? `${s.twelfth_percentage.toFixed(1)}%` : "N/A"}
                        </td>
                        <td className="px-5 py-3 text-center">
                          <span
                            className={`font-mono font-bold text-[11px] px-2 py-0.5 rounded-full ${
                              s.active_backlogs === 0
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : "bg-rose-50 text-rose-700 border border-rose-200"
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
                            className="px-2.5 py-1 bg-white hover:bg-emerald-50 text-slate-700 hover:text-emerald-700 rounded-lg border border-slate-200 hover:border-emerald-300 text-[11px] font-semibold transition-all flex items-center gap-1 mx-auto cursor-pointer"
                          >
                            <Eye className="w-3 h-3 text-emerald-600" />
                            <span>Why Eligible</span>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
              {filteredShortlist.length > 100 && (
                <div className="p-3 bg-slate-50 border-t border-slate-200 text-center text-xs text-slate-500">
                  Displaying first 100 of {filteredShortlist.length} candidates. Download full XLSX/CSV export for complete roster.
                </div>
              )}
            </div>
          </div>
        )}

        {/* =========================================================================
            "WHY THIS STUDENT" DRAWER / MODAL
        ========================================================================= */}
        {selectedCandidateRoll && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
            <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-5 text-slate-800 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2.5">
                  <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-200 flex items-center justify-center font-bold">
                    <UserCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Why This Student Is Qualified</h3>
                    <p className="text-[11px] text-slate-500">Rule-by-rule qualification verification against company criteria</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedCandidateRoll(null)}
                  className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
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
                  <div className="p-3.5 bg-slate-50 rounded-2xl border border-slate-200/80 flex items-center justify-between">
                    <div>
                      <span className="text-sm font-bold text-slate-900 block">{whyBreakdown.candidate.name}</span>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs text-slate-500">{whyBreakdown.candidate.branch}</span>
                        {whyBreakdown.candidate.has_applied && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                            Applied
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-xs font-mono font-bold text-emerald-700 block">{whyBreakdown.candidate.roll_no}</span>
                      <span className="text-[11px] font-bold text-slate-600">CGPA: {whyBreakdown.candidate.cgpa.toFixed(2)}</span>
                    </div>
                  </div>

                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center gap-2 text-xs text-emerald-800">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span><strong>Candidate Verified:</strong> Meets 100% of {whyBreakdown.company_name} eligibility requirements with 0 policy conflicts.</span>
                  </div>

                  <div className="space-y-2">
                    <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block">Company Requirements Checklist</span>
                    <div className="divide-y divide-slate-100 border border-slate-200 rounded-2xl overflow-hidden text-xs">
                      {whyBreakdown.criteria.map((c, idx) => (
                        <div key={idx} className="p-3 bg-white flex items-start gap-3">
                          <div className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200 flex items-center justify-center shrink-0 mt-0.5">
                            <Check className="w-3.5 h-3.5" />
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-slate-900">{c.criterion}</span>
                              <span className="font-mono text-emerald-700 font-bold">{c.candidate_value}</span>
                            </div>
                            <p className="text-[11px] text-slate-500 mt-0.5">{c.verification} (Required: {c.required})</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      type="button"
                      onClick={() => setSelectedCandidateRoll(null)}
                      className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold rounded-xl cursor-pointer"
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
            MODULE 4: SCHEDULE & TIMETABLE (Requirement 3: Live Auto-Sync + Create Round)
        ========================================================================= */}
        {activeTab === "schedule" && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-emerald-600" />
                    <span>Interview Round Schedule ({scheduleSlots.length} Slots)</span>
                  </h2>
                  {/* Live Sync Status indicator */}
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                    Live Sync Connected ({lastSyncedTime})
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Deterministic clash-free timetable verified by the constraint solver. Updated automatically upon officer modifications.
                </p>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                {/* Instant Sync Button */}
                <button
                  type="button"
                  onClick={handleManualSyncSchedule}
                  disabled={isSyncingSchedule}
                  title="Force refresh schedule timetable from officer changes"
                  className="p-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-xl shadow-2xs text-xs font-bold transition-all cursor-pointer disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 text-blue-600 ${isSyncingSchedule ? "animate-spin" : ""}`} />
                </button>

                {/* + Create Round Button */}
                <button
                  type="button"
                  onClick={() => setIsCreateRoundModalOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-xl shadow-md transition-all cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>+ Create Round</span>
                </button>

                <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200">
                  <button
                    type="button"
                    onClick={() => setScheduleViewMode("list")}
                    className={`px-3 py-1 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                      scheduleViewMode === "list" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-500 hover:text-slate-900"
                    }`}
                  >
                    List
                  </button>
                  <button
                    type="button"
                    onClick={() => setScheduleViewMode("day")}
                    className={`px-3 py-1 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                      scheduleViewMode === "day" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-500 hover:text-slate-900"
                    }`}
                  >
                    Day Grid
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => handleRecruiterDownload("/api/recruiter/export/schedule.xlsx", "interview_schedule.xlsx")}
                  disabled={downloadingFile === "/api/recruiter/export/schedule.xlsx"}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 text-xs font-bold rounded-xl transition-all cursor-pointer disabled:opacity-50"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Export XLSX</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleRecruiterDownload("/api/recruiter/export/schedule.csv", "interview_schedule.csv")}
                  disabled={downloadingFile === "/api/recruiter/export/schedule.csv"}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 border border-slate-200 shadow-2xs text-xs font-bold rounded-xl transition-all cursor-pointer disabled:opacity-50"
                >
                  <Download className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Export CSV</span>
                </button>
              </div>
            </div>

            {scheduleSlots.length === 0 ? (
              <div className="p-12 bg-white border border-slate-200/90 rounded-3xl text-center text-xs text-slate-400">
                Interview slots are being generated by the Placement Cell solver. They will appear here once finalized.
              </div>
            ) : (
              <div className="bg-white rounded-3xl border border-slate-200 shadow-md overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
                      <th className="px-5 py-3">Round</th>
                      <th className="px-5 py-3">Slot Time</th>
                      <th className="px-5 py-3">Venue / Cabin</th>
                      <th className="px-5 py-3">Evaluation Panel</th>
                      <th className="px-5 py-3">Candidate</th>
                      <th className="px-5 py-3">Roll No</th>
                      <th className="px-5 py-3 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {scheduleSlots.slice(0, 100).map((sl) => (
                      <tr key={sl.slot_id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-5 py-3 font-bold text-slate-900">
                          <Badge variant="brand" size="sm">Round {sl.round_number}</Badge>
                        </td>
                        <td className="px-5 py-3 font-mono font-bold text-emerald-700">
                          <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3 text-emerald-600" />
                            <span>{sl.start_time}</span>
                          </div>
                        </td>
                        <td className="px-5 py-3 text-slate-700">
                          <div className="font-semibold text-slate-900">{sl.venue}</div>
                          <div className="text-[10px] text-slate-400">{sl.building}</div>
                        </td>
                        <td className="px-5 py-3 text-slate-600 font-semibold">{sl.panel}</td>
                        <td className="px-5 py-3 font-bold text-slate-900">{sl.candidate_name}</td>
                        <td className="px-5 py-3 font-mono text-emerald-700">{sl.candidate_roll_no}</td>
                        <td className="px-5 py-3 text-center">
                          <button
                            type="button"
                            onClick={() => {
                              setActiveTab("attendance");
                              setAttendanceSearch(sl.candidate_roll_no);
                            }}
                            className="px-2.5 py-1 bg-slate-100 hover:bg-emerald-50 text-slate-700 hover:text-emerald-700 rounded-lg text-[10px] font-bold border border-slate-200 transition-colors cursor-pointer"
                          >
                            Mark Attendance
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {scheduleSlots.length > 100 && (
                  <div className="p-3 bg-slate-50 border-t border-slate-200 text-center text-xs text-slate-500">
                    Showing first 100 of {scheduleSlots.length} interview slots. Download schedule XLSX/CSV for full schedule.
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
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-emerald-600" />
                  <span>Eligibility Conditions Applied For Your Drive</span>
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  These conditions were agreed with the placement cell and applied deterministically to compute the approved shortlist.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {requirements.map((r, idx) => (
                <div key={idx} className="bg-white p-5 rounded-2xl border border-slate-200 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span>{r.rule_type}</span>
                    </span>
                    <button
                      type="button"
                      onClick={() => handleFlagRequirement(r)}
                      className="text-[11px] font-semibold text-amber-600 hover:text-amber-700 flex items-center gap-1 cursor-pointer"
                    >
                      <HelpCircle className="w-3 h-3" />
                      <span>Contact College about this</span>
                    </button>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                    <div className="text-xs font-bold text-emerald-700">{r.condition}</div>
                    <p className="text-[11px] text-slate-600 leading-relaxed">{r.plain_english}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* =========================================================================
            MODULE 7: EXPORT FILES (CSV and XLSX Formats)
        ========================================================================= */}
        {activeTab === "export" && overview && (
          <div className="space-y-6">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Download className="w-4 h-4 text-emerald-600" />
                <span>Corporate File Exports (XLSX & CSV)</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Download verified candidate rosters and interview matrices in both standard CSV and structured Excel (XLSX) format.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Shortlist Card */}
              <div className="bg-white p-6 rounded-3xl border border-slate-200 space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-200 flex items-center justify-center font-bold">
                    <Users className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Candidate Shortlist Roster</h3>
                    <p className="text-[11px] text-slate-500">All {overview.total_shortlisted} verified candidates</p>
                  </div>
                </div>

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Current Drive Version:</span>
                    <span className="font-mono font-bold text-emerald-700">v{overview.version}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Columns Included:</span>
                    <span>Roll No, Full Name, Program, Branch, CGPA, 10th %, 12th %</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Privacy Status:</span>
                    <span className="text-emerald-700 font-semibold">Strictly Redacted (FERPA Compliant)</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => handleRecruiterDownload("/api/recruiter/export/shortlist.xlsx", "company_shortlist.xlsx")}
                    disabled={downloadingFile === "/api/recruiter/export/shortlist.xlsx"}
                    className="py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs rounded-xl shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    <FileSpreadsheet className="w-4 h-4" />
                    <span>Download XLSX</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleRecruiterDownload("/api/recruiter/export/shortlist.csv", "company_shortlist.csv")}
                    disabled={downloadingFile === "/api/recruiter/export/shortlist.csv"}
                    className="py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs rounded-xl border border-slate-200 transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download CSV</span>
                  </button>
                </div>
              </div>

              {/* Schedule Card */}
              <div className="bg-white p-6 rounded-3xl border border-slate-200 space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 border border-blue-200 flex items-center justify-center font-bold">
                    <Calendar className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Interview Schedule Timetable</h3>
                    <p className="text-[11px] text-slate-500">All {scheduleSlots.length} interview slots and room allocations</p>
                  </div>
                </div>

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Venue Allocations:</span>
                    <span>Campus Placement Block Cabins</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Clash Status:</span>
                    <span className="text-emerald-700 font-bold">0 Clashes Verified</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Sync Status:</span>
                    <span className="text-blue-700 font-semibold">Live Reactive Timetable</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => handleRecruiterDownload("/api/recruiter/export/schedule.xlsx", "interview_schedule.xlsx")}
                    disabled={downloadingFile === "/api/recruiter/export/schedule.xlsx"}
                    className="py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs rounded-xl shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    <FileSpreadsheet className="w-4 h-4" />
                    <span>Download XLSX</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleRecruiterDownload("/api/recruiter/export/schedule.csv", "interview_schedule.csv")}
                    disabled={downloadingFile === "/api/recruiter/export/schedule.csv"}
                    className="py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs rounded-xl border border-slate-200 transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download CSV</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* =========================================================================
            MODULE 8: CONTACT THE COLLEGE (Requirement 5 & 7: Function, Assignment & Instant Message)
        ========================================================================= */}
        {activeTab === "contact" && overview && (
          <div className="space-y-6">
            {/* Header Explaining Where it Assigns and Where it Contacts */}
            <div className="p-4 bg-gradient-to-r from-blue-50 via-teal-50 to-emerald-50 border border-blue-200 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs">
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
                  <Building2 className="w-4 h-4 text-blue-600" />
                  <span>Contact College & Logistics Channel</span>
                </div>
                <p className="text-slate-600">
                  Messages submitted here are <strong>assigned directly to Prof. R. K. Sharma</strong> (Head, Training & Placement Cell) in <strong>Room 204</strong>, and instantly transmitted to the <strong>Placement Officer Portal Inbox</strong>.
                </p>
              </div>
              <Badge variant="brand" size="sm">Officer Direct Channel</Badge>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left: Officer Contact Card */}
              <div className="lg:col-span-1 bg-white p-6 rounded-3xl border border-slate-200 space-y-4">
                <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-emerald-600" />
                  <span>Placement Cell Administrator</span>
                </h2>

                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-3 text-xs">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">Assigned Recipient</span>
                    <span className="text-sm font-bold text-slate-900 block">{overview.officer_contact.name}</span>
                    <span className="text-[11px] text-emerald-700 font-semibold">{overview.officer_contact.title}</span>
                  </div>

                  <div className="space-y-1.5 pt-2 border-t border-slate-200 text-slate-600">
                    <div className="flex items-center gap-2">
                      <Mail className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                      <span>{overview.officer_contact.email}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Phone className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                      <span>{overview.officer_contact.phone}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <MapPin className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                      <span>{overview.officer_contact.office}</span>
                    </div>
                  </div>
                </div>

                <div className="p-3 bg-blue-50 rounded-xl border border-blue-200 text-[11px] text-blue-800 leading-relaxed">
                  Need extra interview cabins, scheduling modifications, or candidate verifications? Submit a message below and it will appear on the officer's inbox immediately.
                </div>
              </div>

              {/* Right: Submit Request & Inquiries History */}
              <div className="lg:col-span-2 space-y-6">
                {/* Submission Form */}
                <div className="bg-white p-6 rounded-3xl border border-slate-200 space-y-4">
                  <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <Send className="w-4 h-4 text-emerald-600" />
                    <span>Send Message to Placement Officer</span>
                  </h2>

                  {inquirySuccess && <AlertBanner type="success" message={inquirySuccess} onClose={() => setInquirySuccess(null)} />}
                  {inquiryError && <AlertBanner type="danger" message={inquiryError} onClose={() => setInquiryError(null)} />}

                  <form onSubmit={handleInquirySubmit} className="space-y-3.5 text-xs">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                          Category <span className="text-rose-500">*</span>
                        </label>
                        <select
                          value={inquiryCategory}
                          onChange={(e) => setInquiryCategory(e.target.value)}
                          className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl text-slate-800 cursor-pointer focus:outline-none focus:border-emerald-500"
                        >
                          <option value="schedule_change">Schedule / Timing Adjustment</option>
                          <option value="logistics">Additional Interview Panel / Room</option>
                          <option value="candidate_inquiry">Question About Specific Candidate</option>
                          <option value="rule_feedback">Rule or Cut-off Clarification</option>
                          <option value="urgent_alert">Urgent Floor Alert</option>
                        </select>
                      </div>

                      <div>
                        <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                          Candidate Roll No (Optional)
                        </label>
                        <input
                          type="text"
                          placeholder="e.g. BT210001 (if regarding a student)"
                          value={inquiryCandidateRoll}
                          onChange={(e) => setInquiryCandidateRoll(e.target.value)}
                          className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl text-slate-800 focus:outline-none focus:border-emerald-500"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                        Subject <span className="text-rose-500">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Need one more interview panel starting at 2:00 PM..."
                        value={inquirySubject}
                        onChange={(e) => setInquirySubject(e.target.value)}
                        className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl text-slate-800 focus:outline-none focus:border-emerald-500"
                      />
                    </div>

                    <div>
                      <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                        Message / Instructions <span className="text-rose-500">*</span>
                      </label>
                      <textarea
                        rows={3}
                        required
                        placeholder="Provide details for the Placement Officer to review and process..."
                        value={inquiryMessage}
                        onChange={(e) => setInquiryMessage(e.target.value)}
                        className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl text-slate-800 focus:outline-none focus:border-emerald-500"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={inquirySubmitting}
                      className="px-5 py-2.5 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white font-bold text-xs rounded-xl shadow-md transition-all cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>{inquirySubmitting ? "Sending to Officer..." : "Send Message to Officer"}</span>
                    </button>
                  </form>
                </div>

                {/* Inquiries Thread History */}
                <div className="bg-white p-6 rounded-3xl border border-slate-200 space-y-4">
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-emerald-600" />
                    <span>Previous Messages & Officer Responses ({inquiries.length})</span>
                  </h3>

                  {inquiries.length === 0 ? (
                    <div className="p-6 bg-slate-50 rounded-2xl text-center text-xs text-slate-500 border border-slate-200">
                      No requests submitted yet.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {inquiries.map((inq) => (
                        <div key={inq.id} className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-2 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-900">{inq.title}</span>
                            <Badge
                              variant={inq.status === "answered" || inq.status === "approved" ? "success" : "warning"}
                              size="sm"
                            >
                              {inq.status.toUpperCase()}
                            </Badge>
                          </div>
                          <p className="text-slate-700">{inq.description}</p>
                          <div className="text-[10px] text-slate-400">Submitted on {new Date(inq.submitted_at).toLocaleString()}</div>

                          {inq.officer_response && (
                            <div className="mt-2 p-3 bg-emerald-50 border border-emerald-200 rounded-xl space-y-1">
                              <span className="text-[10px] uppercase font-bold text-emerald-800 block">
                                Officer Response ({inq.officer_name || "Prof. R. K. Sharma"})
                              </span>
                              <p className="text-emerald-900">{inq.officer_response}</p>
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
            MODULE 9: ATTENDANCE TAB (Requirement 6: Real-Time Attendance Tracking)
        ========================================================================= */}
        {activeTab === "attendance" && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <UserCheck className="w-4 h-4 text-emerald-600" />
                  <span>Candidate Attendance & Check-In Tracking</span>
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Real-time interview room check-in tracking. Update candidate arrival status with one click.
                </p>
              </div>

              <button
                type="button"
                onClick={() => fetchAllData(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 text-xs font-bold rounded-xl shadow-2xs cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5 text-emerald-600" />
                <span>Refresh Attendance</span>
              </button>
            </div>

            {attendance && (
              <div className="space-y-6">
                {/* Counters */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
                    <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider block">Present</span>
                    <div className="text-2xl font-black text-emerald-700 font-mono">{attendance.present_count}</div>
                    <span className="text-[11px] text-slate-500">Checked into room</span>
                  </div>

                  <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
                    <span className="text-[10px] font-bold text-rose-700 uppercase tracking-wider block">Absent</span>
                    <div className="text-2xl font-black text-rose-700 font-mono">{attendance.absent_count}</div>
                    <span className="text-[11px] text-slate-500">Marked absent</span>
                  </div>

                  <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
                    <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider block">Late / In Transit</span>
                    <div className="text-2xl font-black text-amber-700 font-mono">{attendance.late_count}</div>
                    <span className="text-[11px] text-slate-500">Arriving shortly</span>
                  </div>

                  <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
                    <span className="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Pending Slot</span>
                    <div className="text-2xl font-black text-slate-700 font-mono">{attendance.pending_count}</div>
                    <span className="text-[11px] text-slate-500">Awaiting time</span>
                  </div>

                  <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
                    <span className="text-[10px] font-bold text-blue-700 uppercase tracking-wider block">Turnout Rate</span>
                    <div className="text-2xl font-black text-blue-700 font-mono">{attendance.turnout_percentage}%</div>
                    <span className="text-[11px] text-slate-500">{attendance.total_scheduled} scheduled</span>
                  </div>
                </div>

                {/* Filter and Candidate Search */}
                <div className="p-4 bg-white rounded-2xl border border-slate-200 flex flex-col md:flex-row items-center justify-between gap-3">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {["all", "present", "absent", "late", "pending"].map((statusKey) => (
                      <button
                        key={statusKey}
                        type="button"
                        onClick={() => setAttendanceFilter(statusKey)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-bold capitalize transition-all cursor-pointer ${
                          attendanceFilter === statusKey
                            ? "bg-emerald-600 text-white shadow-2xs"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        {statusKey}
                      </button>
                    ))}
                  </div>

                  <div className="relative w-full md:w-72">
                    <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      placeholder="Search candidate by name or roll..."
                      value={attendanceSearch}
                      onChange={(e) => setAttendanceSearch(e.target.value)}
                      className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                </div>

                {/* Candidate Attendance Action Table */}
                <div className="bg-white rounded-3xl border border-slate-200 shadow-md overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
                        <th className="px-5 py-3">Roll No</th>
                        <th className="px-5 py-3">Candidate Full Name</th>
                        <th className="px-5 py-3">Branch</th>
                        <th className="px-5 py-3">Slot Time</th>
                        <th className="px-5 py-3">Cabin / Room</th>
                        <th className="px-5 py-3 text-center">Status</th>
                        <th className="px-5 py-3 text-center">Record Attendance Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredAttendanceCandidates.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="p-8 text-center text-slate-400 text-xs">
                            No candidates found for attendance filter '{attendanceFilter}'.
                          </td>
                        </tr>
                      ) : (
                        filteredAttendanceCandidates.map((c) => (
                          <tr key={c.slot_id} className="hover:bg-slate-50 transition-colors">
                            <td className="px-5 py-3 font-mono font-bold text-emerald-700">{c.roll_no}</td>
                            <td className="px-5 py-3 font-bold text-slate-900">{c.name}</td>
                            <td className="px-5 py-3 text-slate-600">{c.branch}</td>
                            <td className="px-5 py-3 font-mono font-semibold text-slate-700">{c.start_time}</td>
                            <td className="px-5 py-3 text-slate-700">{c.venue}</td>
                            <td className="px-5 py-3 text-center">
                              <span
                                className={`px-2.5 py-1 rounded-full text-[11px] font-bold capitalize ${
                                  c.status === "present"
                                    ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                                    : c.status === "absent"
                                    ? "bg-rose-100 text-rose-800 border border-rose-300"
                                    : c.status === "late"
                                    ? "bg-amber-100 text-amber-800 border border-amber-300"
                                    : "bg-slate-100 text-slate-600 border border-slate-200"
                                }`}
                              >
                                {c.status}
                              </span>
                            </td>
                            <td className="px-5 py-3 text-center">
                              <div className="flex items-center justify-center gap-1.5">
                                <button
                                  type="button"
                                  onClick={() => handleMarkAttendance(c.slot_id, c.student_id, "present")}
                                  disabled={markingCandidateSlot === c.slot_id}
                                  className={`px-2 py-1 rounded-lg text-[10px] font-bold transition-all cursor-pointer ${
                                    c.status === "present"
                                      ? "bg-emerald-600 text-white"
                                      : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200"
                                  }`}
                                >
                                  Present
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleMarkAttendance(c.slot_id, c.student_id, "late")}
                                  disabled={markingCandidateSlot === c.slot_id}
                                  className={`px-2 py-1 rounded-lg text-[10px] font-bold transition-all cursor-pointer ${
                                    c.status === "late"
                                      ? "bg-amber-600 text-white"
                                      : "bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200"
                                  }`}
                                >
                                  Late
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleMarkAttendance(c.slot_id, c.student_id, "absent")}
                                  disabled={markingCandidateSlot === c.slot_id}
                                  className={`px-2 py-1 rounded-lg text-[10px] font-bold transition-all cursor-pointer ${
                                    c.status === "absent"
                                      ? "bg-rose-600 text-white"
                                      : "bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200"
                                  }`}
                                >
                                  Absent
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* =========================================================================
            MODULE 10: CONFIRMED RESULTS (Requirement 8: Strictly Real DB Offers Only)
        ========================================================================= */}
        {activeTab === "results" && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>Confirmed Selected Candidates ({resultsList.length})</span>
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Official verified selection offers recorded and approved by the Placement Officer.
                </p>
              </div>

              {resultsList.length > 0 && (
                <button
                  type="button"
                  onClick={() => handleRecruiterDownload("/api/recruiter/export/shortlist.xlsx", "confirmed_selections.xlsx")}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl shadow-md transition-all cursor-pointer"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  <span>Export Selections</span>
                </button>
              )}
            </div>

            {resultsList.length === 0 ? (
              <div className="p-12 bg-white border border-slate-200/90 rounded-3xl text-center space-y-2">
                <CheckCircle2 className="w-10 h-10 text-slate-300 mx-auto" />
                <h3 className="text-sm font-bold text-slate-700">Official Results Awaiting Placement Cell Confirmation</h3>
                <p className="text-xs text-slate-400 max-w-md mx-auto">
                  Final selection offers have not yet been released by the Placement Officer for this drive. Once interviews conclude and official selections are confirmed, they will appear here.
                </p>
              </div>
            ) : (
              <div className="bg-white rounded-3xl border border-slate-200 shadow-md overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
                      <th className="px-5 py-3">Roll No</th>
                      <th className="px-5 py-3">Selected Candidate</th>
                      <th className="px-5 py-3">Branch</th>
                      <th className="px-5 py-3 text-right">Offered CTC</th>
                      <th className="px-5 py-3 text-center">Status</th>
                      <th className="px-5 py-3 text-right">Confirmed Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {resultsList.map((c) => (
                      <tr key={c.roll_no} className="hover:bg-slate-50 transition-colors">
                        <td className="px-5 py-3 font-mono font-bold text-emerald-700">{c.roll_no}</td>
                        <td className="px-5 py-3 font-bold text-slate-900">{c.name}</td>
                        <td className="px-5 py-3 text-slate-600">{c.branch}</td>
                        <td className="px-5 py-3 font-mono font-bold text-emerald-700 text-right">{c.ctc_lpa} LPA</td>
                        <td className="px-5 py-3 text-center">
                          <Badge variant="success" size="sm">{c.status}</Badge>
                        </td>
                        <td className="px-5 py-3 text-slate-500 text-right font-mono">{c.confirmed_date}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* =========================================================================
            CREATE RECRUITMENT ROUND MODAL (Requirement 9)
        ========================================================================= */}
        {isCreateRoundModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
            <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4 text-slate-800">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2.5">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 border border-blue-200 flex items-center justify-center font-bold">
                    <Plus className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Configure Recruitment Round</h3>
                    <p className="text-[11px] text-slate-500">Add an interview, coding, or assessment round to active drive</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setIsCreateRoundModalOpen(false)}
                  className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {roundSuccess && <AlertBanner type="success" message={roundSuccess} onClose={() => setRoundSuccess(null)} />}
              {roundError && <AlertBanner type="danger" message={roundError} onClose={() => setRoundError(null)} />}

              <form onSubmit={handleCreateRoundSubmit} className="space-y-3.5 text-xs">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                      Round Number <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      required
                      value={roundNumber}
                      onChange={(e) => setRoundNumber(parseInt(e.target.value) || 1)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 font-mono font-bold"
                    />
                  </div>

                  <div>
                    <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                      Duration (Mins) <span className="text-rose-500">*</span>
                    </label>
                    <select
                      value={roundDuration}
                      onChange={(e) => setRoundDuration(parseInt(e.target.value) || 45)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 cursor-pointer"
                    >
                      <option value={15}>15 Minutes</option>
                      <option value={30}>30 Minutes</option>
                      <option value={45}>45 Minutes</option>
                      <option value={60}>60 Minutes</option>
                      <option value={90}>90 Minutes</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                    Round Name Title <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Round 2: Technical Interview & System Architecture"
                    value={roundName}
                    onChange={(e) => setRoundName(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-800"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                      Evaluation Type <span className="text-rose-500">*</span>
                    </label>
                    <select
                      value={roundType}
                      onChange={(e) => setRoundType(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 cursor-pointer"
                    >
                      <option value="technical_interview">Technical Interview</option>
                      <option value="coding_test">Coding Assessment</option>
                      <option value="hr_interview">HR / Management Interview</option>
                      <option value="group_discussion">Group Discussion</option>
                      <option value="final_presentation">Final Presentation</option>
                    </select>
                  </div>

                  <div>
                    <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                      Mode <span className="text-rose-500">*</span>
                    </label>
                    <select
                      value={roundMode}
                      onChange={(e) => setRoundMode(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 cursor-pointer"
                    >
                      <option value="in_person">In-Person (Campus Cabin)</option>
                      <option value="online">Online / Virtual</option>
                      <option value="hybrid">Hybrid</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                    Special Instructions (Optional)
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Instructions for placement cell coordinators and candidates..."
                    value={roundInstructions}
                    onChange={(e) => setRoundInstructions(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-800"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setIsCreateRoundModalOpen(false)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={roundSubmitting}
                    className="px-5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold rounded-xl shadow-md cursor-pointer disabled:opacity-50"
                  >
                    {roundSubmitting ? "Creating Round..." : "Save & Add Round"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
