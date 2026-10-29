import React, { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../api/client";
import { Badge } from "../../components/common/Badge";
import {
  GraduationCap,
  Calendar,
  Clock,
  Printer,
  Download,
  ChevronDown,
  AlertTriangle,
  Briefcase,
  CheckCircle2,
  XCircle,
  UserCheck,
  MapPin,
  KeyRound,
  Eye,
  EyeOff,
  X,
  Bell,
  HelpCircle,
  FileText,
  AlertCircle,
  ArrowLeft,
  Sparkles,
  ShieldCheck,
  Filter,
  Users,
  ChevronLeft,
  ChevronRight,
  Shield,
} from "lucide-react";

export type StudentTabId =
  | "status"
  | "schedule"
  | "clashes"
  | "offers"
  | "policy"
  | "profile"
  | "corrections"
  | "notifications"
  | "print"
  | "faq";

export const StudentPortal: React.FC = () => {
  const { user, studentLogin, logout } = useAuth();

  // Active Screen / Tab
  const [activeTab, setActiveTab] = useState<StudentTabId>("status");
  const [selectedDriveDetail, setSelectedDriveDetail] = useState<any | null>(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => typeof window !== "undefined" && window.innerWidth < 1024);

  // Login form state (if not logged in)
  const [rollNo, setRollNo] = useState("BT210001");
  const [accessCode, setAccessCode] = useState("student123");
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Data state
  const [studentInfo, setStudentInfo] = useState<any | null>(null);
  const [drives, setDrives] = useState<any[]>([]);
  const [schedule, setSchedule] = useState<any[]>([]);
  const [clashData, setClashData] = useState<any | null>(null);
  const [offersData, setOffersData] = useState<any | null>(null);
  const [policyData, setPolicyData] = useState<any | null>(null);
  const [correctionsList, setCorrectionsList] = useState<any[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);

  // Status Filter state (Home)
  const [statusFilter, setStatusFilter] = useState<"all" | "eligible" | "ineligible" | "policy_blocked" | "needs_review">("all");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  // Correction Request Form state
  const [corrField, setCorrField] = useState("CGPA");
  const [corrProblem, setCorrProblem] = useState("");
  const [corrNote, setCorrNote] = useState("");
  const [corrSubmitting, setCorrSubmitting] = useState(false);
  const [corrFeedback, setCorrFeedback] = useState<string | null>(null);

  // Clash Preference Form state
  const [clashPreferredCompany, setClashPreferredCompany] = useState("");
  const [clashNote, setClashNote] = useState("");
  const [clashSubmitting, setClashSubmitting] = useState(false);
  const [clashFeedback, setClashFeedback] = useState<string | null>(null);

  // Change Password Modal state
  const [isChangePasswordOpen, setIsChangePasswordOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);

  // Fetch all candidate portal data
  const fetchAllData = async () => {
    try {
      const [meRes, drivesRes, schedRes, clashRes, offersRes, polRes, corrRes, notifRes] =
        await Promise.allSettled([
          api.get<any>("/api/portal/me"),
          api.get<any[]>("/api/portal/drives"),
          api.get<any[]>("/api/portal/schedule"),
          api.get<any>("/api/portal/clashes"),
          api.get<any>("/api/portal/offers"),
          api.get<any>("/api/portal/policy"),
          api.get<any[]>("/api/portal/corrections"),
          api.get<any[]>("/api/portal/notifications"),
        ]);

      if (meRes.status === "fulfilled") setStudentInfo(meRes.value);
      if (drivesRes.status === "fulfilled") setDrives(drivesRes.value || []);
      if (schedRes.status === "fulfilled") setSchedule(schedRes.value || []);
      if (clashRes.status === "fulfilled") setClashData(clashRes.value);
      if (offersRes.status === "fulfilled") setOffersData(offersRes.value);
      if (polRes.status === "fulfilled") setPolicyData(polRes.value);
      if (corrRes.status === "fulfilled") setCorrectionsList(corrRes.value || []);
      if (notifRes.status === "fulfilled") setNotifications(notifRes.value || []);
    } catch {
      // Offline graceful fallback
    }
  };

  useEffect(() => {
    if (user?.role === "student") {
      fetchAllData();
    }
  }, [user]);

  // Auth handler
  const handleStudentAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoginLoading(true);
      setLoginError(null);
      await studentLogin(rollNo, accessCode);
    } catch (err: any) {
      setLoginError(err.message || "Code expired - ask your placement officer for a new one.");
    } finally {
      setLoginLoading(false);
    }
  };

  // Submit data correction request
  const handleSubmitCorrection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!corrProblem.trim()) return;
    try {
      setCorrSubmitting(true);
      setCorrFeedback(null);
      const res = await api.post<any>("/api/portal/corrections", {
        field: corrField,
        problem_description: corrProblem,
        supporting_note: corrNote || undefined,
      });
      setCorrFeedback(res.message || "Your correction request has been sent to the placement officer.");
      setCorrProblem("");
      setCorrNote("");
      const updated = await api.get<any[]>("/api/portal/corrections");
      setCorrectionsList(updated || []);
    } catch (err: any) {
      setCorrFeedback(err.message || "Failed to submit correction request.");
    } finally {
      setCorrSubmitting(false);
    }
  };

  // Submit clash preference
  const handleSubmitClashPreference = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clashPreferredCompany.trim()) return;
    try {
      setClashSubmitting(true);
      setClashFeedback(null);
      const res = await api.post<any>("/api/portal/clash-preference", {
        preferred_company: clashPreferredCompany,
        student_note: clashNote || undefined,
      });
      setClashFeedback(res.message || "Your preference has been submitted to the placement officer.");
      setClashPreferredCompany("");
      setClashNote("");
      const updatedClashes = await api.get<any>("/api/portal/clashes");
      setClashData(updatedClashes);
    } catch (err: any) {
      setClashFeedback(err.message || "Failed to submit preference.");
    } finally {
      setClashSubmitting(false);
    }
  };

  // Change password handler
  const handleChangePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match. Please verify.");
      return;
    }
    if (newPassword.length < 4) {
      setPasswordError("New password must be at least 4 characters long.");
      return;
    }

    try {
      setPasswordLoading(true);
      setPasswordError(null);
      setPasswordSuccess(null);
      const res = await api.post<any>("/api/portal/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordSuccess(res.message || "Password updated successfully!");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => {
        setIsChangePasswordOpen(false);
        setPasswordSuccess(null);
      }, 1500);
    } catch (err: any) {
      setPasswordError(err.message || "Failed to update password. Please check your current password.");
    } finally {
      setPasswordLoading(false);
    }
  };

  // Generate .ics calendar download
  const handleDownloadCalendar = () => {
    const slots = schedule.length > 0 ? schedule : [];
    if (slots.length === 0) return;

    const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`);
    const formatIcsDate = (d: Date) =>
      `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}T${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}00Z`;

    const icsLines = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//Campus Placement Engine//IM-101//EN",
      "CALSCALE:GREGORIAN",
      "METHOD:PUBLISH",
    ];

    slots.forEach((s) => {
      const now = new Date();
      const start = s.start_iso ? new Date(s.start_iso) : new Date(now.getTime() + 86400000);
      const end = s.end_iso ? new Date(s.end_iso) : new Date(start.getTime() + 3600000);

      icsLines.push("BEGIN:VEVENT");
      icsLines.push(`UID:placement_${s.slot_id || Math.random().toString(36).substring(7)}@college.edu`);
      icsLines.push(`DTSTAMP:${formatIcsDate(now)}`);
      icsLines.push(`DTSTART:${formatIcsDate(start)}`);
      icsLines.push(`DTEND:${formatIcsDate(end)}`);
      icsLines.push(`SUMMARY:${s.company_name} - ${s.round_name}`);
      icsLines.push(`DESCRIPTION:Placement test/interview for ${studentInfo?.name || "Student"}. Room: ${s.room_name} (${s.building || "Campus"}). Panel: ${s.panel_name || "Panel"}`);
      icsLines.push(`LOCATION:${s.room_name}, ${s.building || "Campus Venue"}`);
      icsLines.push("STATUS:CONFIRMED");
      icsLines.push("END:VEVENT");
    });

    icsLines.push("END:VCALENDAR");

    const blob = new Blob([icsLines.join("\r\n")], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `placement_schedule_${studentInfo?.roll_no || "candidate"}.ics`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Generate Schedule CSV download
  const handleDownloadScheduleCsv = () => {
    const slots = schedule.length > 0 ? schedule : [];
    const headers = ["Company", "Round", "Date", "Start Time", "End Time", "Venue", "Mode", "Status"];
    const rows = slots.map((s) => [
      `"${(s.company_name || "").replace(/"/g, '""')}"`,
      `"${(s.round_name || "").replace(/"/g, '""')}"`,
      `"${(s.drive_date || "").replace(/"/g, '""')}"`,
      `"${(s.start_time || "").replace(/"/g, '""')}"`,
      `"${(s.end_time || "").replace(/"/g, '""')}"`,
      `"${(s.venue || s.room_name || "").replace(/"/g, '""')}"`,
      `"${(s.mode || "in-person").replace(/"/g, '""')}"`,
      `"${(s.status || "SCHEDULED").replace(/"/g, '""')}"`,
    ]);
    const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `placement_schedule_${studentInfo?.roll_no || "candidate"}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Generate Drives CSV download
  const handleDownloadDrivesCsv = () => {
    const list = drives.length > 0 ? drives : [];
    const headers = ["Company Name", "Role", "CTC (LPA)", "Drive Date", "Eligibility Status", "Verdict Reason"];
    const rows = list.map((d) => [
      `"${(d.company_name || "").replace(/"/g, '""')}"`,
      `"${(d.role || "Software Engineer").replace(/"/g, '""')}"`,
      `"${d.ctc_lpa || ""}"`,
      `"${(d.drive_date || "").replace(/"/g, '""')}"`,
      `"${(d.status || "").toUpperCase()}"`,
      `"${(d.headline_reason || "").replace(/"/g, '""')}"`,
    ]);
    const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `placement_drives_${studentInfo?.roll_no || "candidate"}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Filter and sort drives
  const filteredDrives = drives
    .filter((d) => (statusFilter === "all" ? true : d.status === statusFilter))
    .sort((a, b) => {
      const d1 = new Date(a.drive_date).getTime();
      const d2 = new Date(b.drive_date).getTime();
      return sortOrder === "asc" ? d1 - d2 : d2 - d1;
    });

  // SCREEN 1: LOGIN (Unauthenticated)
  if (!user || user.role !== "student") {
    return (
      <div className="min-h-[85vh] flex items-center justify-center p-4">
        <div className="w-full max-w-sm bg-[#0d1527] p-6 sm:p-8 rounded-3xl border border-[#1b2b4d] shadow-2xl space-y-6 text-slate-100">
          <div className="text-center space-y-2">
            <div className="w-14 h-14 bg-[#111d38] border border-emerald-500/30 rounded-2xl flex items-center justify-center text-emerald-400 mx-auto shadow-inner">
              <GraduationCap className="w-8 h-8" />
            </div>
            <h1 className="text-xl font-black text-white tracking-tight">Student Placement Portal</h1>
            <p className="text-xs text-slate-400 leading-relaxed">
              Sign in with your roll number and the one-time access code issued by your placement officer.
            </p>
          </div>

          {loginError && (
            <div className="p-3.5 bg-rose-950/80 border border-rose-800 text-rose-300 rounded-2xl text-xs font-semibold flex items-center gap-2.5">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{loginError}</span>
            </div>
          )}

          <form onSubmit={handleStudentAuth} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
                College Roll Number
              </label>
              <input
                type="text"
                required
                value={rollNo}
                onChange={(e) => setRollNo(e.target.value)}
                className="w-full min-h-[44px] px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:bg-[#0d1527] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="e.g. BT210001"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
                One-Time Access Code
              </label>
              <input
                type="password"
                required
                value={accessCode}
                onChange={(e) => setAccessCode(e.target.value)}
                className="w-full min-h-[44px] px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:bg-[#0d1527] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="Code from placement officer"
              />
            </div>

            <button
              type="submit"
              disabled={loginLoading}
              className="w-full min-h-[48px] py-3 bg-gradient-to-r from-blue-600 via-teal-600 to-emerald-600 hover:from-blue-500 hover:via-teal-500 hover:to-emerald-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-emerald-900/30 border border-emerald-400/30 transition-all cursor-pointer disabled:opacity-50"
            >
              {loginLoading ? "Checking Access Code..." : "Sign In to Portal"}
            </button>
          </form>

          <div className="p-3 bg-[#080e1c] rounded-2xl border border-[#1b2b4d] text-center space-y-1">
            <div className="flex items-center justify-center gap-1.5 text-emerald-400 text-[11px] font-bold">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Your data stays on the college computer</span>
            </div>
            <p className="text-[10px] text-slate-500">
              Only you can see your data. Peer rankings and other students' marks are strictly blocked.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const navItems = [
    {
      num: "01",
      id: "status" as StudentTabId,
      label: "My Status",
      icon: Briefcase,
      badge: drives.length > 0 ? String(drives.length) : undefined,
    },
    {
      num: "02",
      id: "schedule" as StudentTabId,
      label: "Schedule",
      icon: Calendar,
      badge: schedule.length > 0 ? String(schedule.length) : undefined,
    },
    {
      num: "03",
      id: "clashes" as StudentTabId,
      label: "Clashes",
      icon: AlertTriangle,
      badge: clashData?.has_clash ? "Clash" : undefined,
      badgeVariant: "amber" as const,
    },
    {
      num: "04",
      id: "offers" as StudentTabId,
      label: "Offers",
      icon: Sparkles,
      badge: offersData?.offers?.length ? String(offersData.offers.length) : undefined,
      badgeVariant: "brand" as const,
    },
    {
      num: "05",
      id: "policy" as StudentTabId,
      label: "College Policy",
      icon: Shield,
    },
    {
      num: "06",
      id: "profile" as StudentTabId,
      label: "My Profile",
      icon: Users,
    },
    {
      num: "07",
      id: "corrections" as StudentTabId,
      label: "Fix Mistakes",
      icon: FileText,
      badge: correctionsList.length > 0 ? String(correctionsList.length) : undefined,
    },
    {
      num: "08",
      id: "notifications" as StudentTabId,
      label: "Alerts",
      icon: Bell,
      badge: notifications.filter((n) => !n.is_read).length > 0 ? String(notifications.filter((n) => !n.is_read).length) : undefined,
      badgeVariant: "rose" as const,
    },
    {
      num: "09",
      id: "print" as StudentTabId,
      label: "Printable Sheet",
      icon: Printer,
    },
    {
      num: "10",
      id: "faq" as StudentTabId,
      label: "Help / FAQ",
      icon: HelpCircle,
    },
  ];

  return (
    <div className="flex-1 flex overflow-hidden w-full h-full min-h-0 min-w-0">
      {/* Left Vertical Navigation Sidebar (Identical to Coordinator and Officer) */}
      <aside
        className={`bg-[#080e1c] border-r border-[#1b2b4d] shrink-0 flex flex-col h-full max-h-full overflow-hidden sticky top-0 transition-all duration-200 select-none z-20 ${
          isSidebarCollapsed ? "w-16" : "w-52 sm:w-64"
        }`}
        aria-label="Student Dashboard Left Navigation"
      >
        {/* Sidebar Header with Module Index and Collapse Toggle */}
        <div className="p-3.5 border-b border-[#1b2b4d] flex items-center justify-between text-slate-300 shrink-0 sticky top-0 bg-[#080e1c] z-10">
          {!isSidebarCollapsed && (
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
                <span className="text-[10px] font-black tracking-widest text-emerald-400 uppercase font-mono">
                  STUDENT SUITE
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-semibold truncate mt-0.5">
                Roll: {studentInfo?.roll_no || user.username} • Verified
              </p>
            </div>
          )}
          <button
            type="button"
            onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#111d38] transition-colors cursor-pointer ml-auto"
            title={isSidebarCollapsed ? "Expand sidebar navigation" : "Collapse sidebar navigation"}
            aria-label={isSidebarCollapsed ? "Expand sidebar navigation" : "Collapse sidebar navigation"}
          >
            {isSidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Vertical Nav List */}
        <nav className="flex-1 min-h-0 overflow-y-auto px-2 py-3 space-y-1 custom-scrollbar">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id && !selectedDriveDetail;
            return (
              <button
                key={item.id}
                type="button"
                aria-label={item.label}
                onClick={() => {
                  setActiveTab(item.id);
                  setSelectedDriveDetail(null);
                }}
                title={item.label}
                className={`w-full min-h-[44px] flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all duration-150 cursor-pointer ${
                  isActive
                    ? "bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-md shadow-emerald-950/40 ring-1 ring-emerald-400/40 font-bold"
                    : "text-slate-300 hover:text-white hover:bg-[#111d38]/80"
                }`}
              >
                <div className="flex items-center justify-center shrink-0">
                  <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-emerald-400"}`} />
                </div>
                {!isSidebarCollapsed && (
                  <div className="flex-1 flex items-center justify-between min-w-0">
                    <span className="truncate">{item.label}</span>
                    {item.badge && (
                      <span
                        className={`text-[10px] px-1.5 py-0.2 rounded-md font-mono font-bold ${
                          item.badgeVariant === "amber"
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                            : item.badgeVariant === "rose"
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                            : "bg-[#111d38] border border-[#1b2b4d] text-emerald-300"
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

        {/* Sidebar Footer */}
        {!isSidebarCollapsed && (
          <div className="p-3 border-t border-[#1b2b4d] bg-[#050a14]/95 text-[10px] text-slate-500 text-center font-mono shrink-0 sticky bottom-0 z-10">
            100% Offline • College Computer
          </div>
        )}
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8 overflow-y-auto space-y-4">
        {selectedDriveDetail ? (
          <div className="space-y-5 pb-16 max-w-4xl">
            {/* Back Button (>= 44px) */}
            <button
              onClick={() => setSelectedDriveDetail(null)}
              className="min-h-[44px] px-4 py-2 bg-[#0d1527] hover:bg-[#111d38] text-slate-200 hover:text-white border border-[#1b2b4d] rounded-2xl text-xs font-bold flex items-center gap-2 transition-all cursor-pointer w-full"
            >
              <ArrowLeft className="w-4 h-4 text-emerald-400" />
              <span>Back to All Drives</span>
            </button>

            {/* Company Card Header */}
            <div className="bg-[#0d1527] p-5 rounded-3xl border border-[#1b2b4d] shadow-md space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-black text-white">{selectedDriveDetail.company_name}</h2>
                <Badge
                  variant={selectedDriveDetail.status === "eligible" ? "success" : selectedDriveDetail.status === "policy_blocked" ? "warning" : "danger"}
                  size="md"
                >
                  {selectedDriveDetail.status === "policy_blocked" ? "BLOCKED BY POLICY" : selectedDriveDetail.status.replace("_", " ").toUpperCase()}
                </Badge>
              </div>

              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 font-semibold">
                <span className="font-mono text-emerald-400 font-bold">{selectedDriveDetail.ctc_lpa} LPA</span>
                <span>•</span>
                <span>Date: {new Date(selectedDriveDetail.drive_date).toLocaleDateString()}</span>
                <span>•</span>
                <span className="capitalize">{selectedDriveDetail.mode || "On-Campus"}</span>
              </div>

              {/* Headline 3-Part Status Explanation */}
              <div className="p-3.5 bg-[#080e1c] border border-[#1b2b4d] rounded-2xl text-xs font-medium text-slate-200 leading-relaxed">
                {selectedDriveDetail.headline_reason}
              </div>
            </div>

            {/* Section A: Company Rules (Side-by-Side Comparison) */}
            <div className="bg-[#0d1527] p-5 rounded-3xl border border-[#1b2b4d] shadow-md space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-[#1b2b4d]">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  1. Company Academic Rules
                </h3>
                <span className="text-[11px] text-slate-400 font-medium">Required vs Your Value</span>
              </div>

              <div className="space-y-2.5">
                {selectedDriveDetail.company_rules_checks?.map((rule: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-3 bg-[#080e1c] rounded-2xl border border-[#162447] flex items-center justify-between gap-3 text-xs"
                  >
                    <div className="space-y-0.5">
                      <span className="font-bold text-white block">{rule.rule_name}</span>
                      <span className="text-[11px] text-slate-400 block">
                        Company needs: <strong className="text-slate-300">{rule.required}</strong>
                      </span>
                      <span className="text-[11px] text-slate-400 block">
                        Your record: <strong className="text-slate-200">{rule.your_value}</strong>
                      </span>
                    </div>

                    <div className="shrink-0 flex items-center gap-1.5 font-bold">
                      {rule.passed ? (
                        <span className="text-emerald-400 flex items-center gap-1 bg-emerald-950/60 px-2 py-1 rounded-xl border border-emerald-900/60 text-xs">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Meets
                        </span>
                      ) : (
                        <span className="text-rose-400 flex items-center gap-1 bg-rose-950/60 px-2 py-1 rounded-xl border border-rose-900/60 text-xs">
                          <XCircle className="w-3.5 h-3.5" /> Below
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Section B: College Offer Policy */}
            <div className="bg-[#0d1527] p-5 rounded-3xl border border-[#1b2b4d] shadow-md space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-[#1b2b4d]">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  2. College Offer Policy Rules
                </h3>
                <Badge variant={selectedDriveDetail.status === "policy_blocked" ? "warning" : "brand"} size="sm">
                  {selectedDriveDetail.status === "policy_blocked" ? "Action Blocked" : "Policy Allowed"}
                </Badge>
              </div>

              <div className="space-y-2.5">
                {selectedDriveDetail.policy_rules_checks?.map((pol: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-3 bg-[#080e1c] rounded-2xl border border-[#162447] flex items-center justify-between gap-3 text-xs"
                  >
                    <div className="space-y-0.5">
                      <span className="font-bold text-white block">{pol.rule_name}</span>
                      <span className="text-[11px] text-slate-400 block">
                        Policy standard: <strong className="text-slate-300">{pol.required}</strong>
                      </span>
                      <span className="text-[11px] text-slate-400 block">
                        Your status: <strong className="text-slate-200">{pol.your_value}</strong>
                      </span>
                    </div>

                    <div className="shrink-0 font-bold">
                      {pol.passed ? (
                        <span className="text-emerald-400 flex items-center gap-1 bg-emerald-950/60 px-2 py-1 rounded-xl border border-emerald-900/60 text-xs">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Allowed
                        </span>
                      ) : (
                        <span className="text-amber-400 flex items-center gap-1 bg-amber-950/60 px-2 py-1 rounded-xl border border-amber-900/60 text-xs">
                          <AlertTriangle className="w-3.5 h-3.5" /> Blocked
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* "What would change this" box */}
            {selectedDriveDetail.what_would_change_this && (
              <div className="p-4 bg-gradient-to-r from-blue-950/50 to-indigo-950/50 border border-blue-800/60 rounded-3xl space-y-1.5">
                <div className="flex items-center gap-2 text-blue-300 text-xs font-bold">
                  <Sparkles className="w-4 h-4 text-blue-400" />
                  <span>What would change this?</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed font-medium">
                  {selectedDriveDetail.what_would_change_this}
                </p>
              </div>
            )}

            {/* Action: Something looks wrong */}
            <button
              onClick={() => {
                const comp = selectedDriveDetail.company_name;
                setSelectedDriveDetail(null);
                setActiveTab("corrections");
                setCorrProblem(`Discrepancy observed regarding eligibility criteria for ${comp}`);
              }}
              className="min-h-[44px] w-full py-2.5 bg-[#111d38] hover:bg-[#162447] text-slate-300 hover:text-white border border-[#1b2b4d] rounded-2xl text-xs font-bold transition-all cursor-pointer flex items-center justify-center gap-2"
            >
              <AlertCircle className="w-4 h-4 text-amber-400" />
              <span>Notice an error in your criteria? Submit a Correction</span>
            </button>
          </div>
        ) : (
          <div className="space-y-4 pb-20">
            {/* Offline Privacy Guarantee Banner */}
            <div className="p-2.5 bg-[#0d1527] border border-emerald-500/30 rounded-2xl flex items-center justify-between text-xs text-emerald-300">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="font-semibold text-[11px]">Your data stays on the college computer</span>
              </div>
              <span className="text-[10px] text-slate-400 font-mono">100% Offline</span>
            </div>

            {/* Student Profile Snapshot Card */}
            <div className="bg-[#0d1527] p-5 rounded-3xl border border-[#1b2b4d] shadow-md space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-[#111d38] text-emerald-400 border border-emerald-500/30 rounded-2xl flex items-center justify-center font-black text-lg shrink-0 shadow-inner">
                    {studentInfo?.name ? studentInfo.name[0] : "S"}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h1 className="text-base font-black text-white">{studentInfo?.name || "Candidate"}</h1>
                      <Badge variant="success" size="sm">Verified Candidate</Badge>
                    </div>
                    <div className="text-xs text-slate-400 font-medium mt-0.5">
                      <span>Roll: <strong>{studentInfo?.roll_no || user.username}</strong></span>
                      <span className="mx-1.5">•</span>
                      <span>CGPA: <strong className="text-emerald-400">{studentInfo?.cgpa?.toFixed(2) || "8.50"}</strong></span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 no-print flex-wrap">
                  <button
                    onClick={() => setActiveTab("print")}
                    className="min-h-[44px] px-3 py-2 bg-[#111d38] hover:bg-[#162447] text-slate-200 hover:text-white border border-[#1b2b4d] rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5"
                    title="Print clean status sheet"
                  >
                    <Printer className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Print Sheet</span>
                  </button>
                  <a
                    href="/api/portal/status-sheet-pdf"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="min-h-[44px] px-3 py-2 bg-gradient-to-r from-blue-600 via-teal-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 border border-emerald-400/30 shadow-sm"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Official PDF</span>
                  </a>
                  <a
                    href="/api/portal/status-sheet-csv"
                    download={`placement_status_${studentInfo?.roll_no || "candidate"}.csv`}
                    className="min-h-[44px] px-3 py-2 bg-[#111d38] hover:bg-[#162447] text-emerald-300 border border-emerald-500/30 hover:border-emerald-500/60 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 shadow-sm"
                    title="Export personal placement status & schedule as CSV"
                  >
                    <Download className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Export CSV</span>
                  </a>
                  <button
                    onClick={logout}
                    className="min-h-[44px] px-3 py-2 bg-[#111d38] hover:bg-rose-950/60 text-slate-400 hover:text-rose-300 border border-[#1b2b4d] rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center justify-center"
                    title="Sign out & clear cached session"
                  >
                    Logout
                  </button>
                </div>
              </div>
            </div>

      {/* SCREEN 2: HOME / MY STATUS */}
      {activeTab === "status" && (
        <div className="space-y-4">
          {/* Filter & Sort Controls */}
          <div className="bg-[#0d1527] p-3.5 rounded-2xl border border-[#1b2b4d] space-y-2.5">
            <div className="flex items-center justify-between text-xs font-bold text-slate-300">
              <span className="flex items-center gap-1.5">
                <Filter className="w-3.5 h-3.5 text-emerald-400" /> Filter Drives:
              </span>
              <button
                onClick={() => setSortOrder(sortOrder === "asc" ? "desc" : "asc")}
                className="text-emerald-400 hover:text-emerald-300 font-semibold cursor-pointer"
              >
                Date: {sortOrder === "asc" ? "Earliest First" : "Latest First"}
              </button>
            </div>

            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
              {(["all", "eligible", "ineligible", "policy_blocked"] as const).map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`min-h-[44px] px-3 py-1.5 rounded-xl font-bold whitespace-nowrap cursor-pointer transition-all border ${
                    statusFilter === st
                      ? "bg-emerald-950 text-emerald-300 border-emerald-500"
                      : "bg-[#080e1c] text-slate-400 border-[#1b2b4d] hover:text-white"
                  }`}
                >
                  {st === "all" ? "All Drives" : st === "policy_blocked" ? "Policy Blocked" : st.replace("_", " ").toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-emerald-400" />
              <span>Campus Drives & Eligibility Verdicts</span>
            </h2>
            <button
              onClick={handleDownloadDrivesCsv}
              className="min-h-[36px] px-3 py-1.5 bg-[#0d1527] hover:bg-[#1b2b4d] text-emerald-300 text-xs font-bold rounded-xl border border-emerald-500/30 hover:border-emerald-500/60 flex items-center gap-1.5 transition-all cursor-pointer"
              title="Download personal drives and verdicts as CSV"
            >
              <Download className="w-3.5 h-3.5 text-emerald-400" />
              <span>Export Drives (CSV)</span>
            </button>
          </div>

          {/* Drive Cards List */}
          {filteredDrives.length === 0 ? (
            <div className="p-8 bg-[#0d1527] border border-[#1b2b4d] rounded-3xl text-center text-xs text-slate-400">
              No campus drives match this filter.
            </div>
          ) : (
            <div className="space-y-3">
              {filteredDrives.map((d) => {
                const isEligible = d.status === "eligible";
                const isBlocked = d.status === "policy_blocked";

                return (
                  <div
                    key={d.drive_id}
                    onClick={() => setSelectedDriveDetail(d)}
                    className="bg-[#0d1527] border border-[#1b2b4d] hover:border-emerald-500/50 rounded-3xl p-4 shadow-sm transition-all space-y-3 cursor-pointer"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h2 className="font-bold text-white text-base">{d.company_name}</h2>
                        <div className="flex items-center gap-2 text-xs text-slate-400 font-medium mt-0.5">
                          <span className="font-mono text-emerald-400 font-bold">{d.ctc_lpa} LPA</span>
                          <span>•</span>
                          <span>{new Date(d.drive_date).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <Badge
                        variant={isEligible ? "success" : isBlocked ? "warning" : "danger"}
                        size="sm"
                      >
                        {d.status === "policy_blocked" ? "POLICY BLOCKED" : d.status.replace("_", " ").toUpperCase()}
                      </Badge>
                    </div>

                    {/* Single 3-Part Plain-English Line */}
                    <div className="p-3 bg-[#080e1c] border border-[#1b2b4d] rounded-2xl text-xs font-medium text-slate-200 leading-relaxed">
                      {d.headline_reason}
                    </div>

                    <div className="flex items-center justify-between text-xs text-emerald-400 font-semibold pt-1">
                      <span>Tap to inspect side-by-side criteria</span>
                      <ChevronDown className="w-4 h-4" />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Home Schedule Stream */}
          <div className="pt-4 border-t border-[#1b2b4d] space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Calendar className="w-4 h-4 text-emerald-400" />
                <span>My Scheduled Rounds & Campus Venues</span>
              </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={handleDownloadCalendar}
                className="min-h-[44px] px-3.5 py-1.5 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white text-xs font-bold rounded-2xl border border-emerald-400/30 flex items-center gap-1.5 transition-all cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Add to Calendar (.ics)</span>
              </button>
              <button
                onClick={handleDownloadScheduleCsv}
                className="min-h-[44px] px-3.5 py-1.5 bg-[#111d38] hover:bg-[#1b2b4d] text-emerald-300 text-xs font-bold rounded-2xl border border-emerald-500/30 hover:border-emerald-500/60 flex items-center gap-1.5 transition-all cursor-pointer"
                title="Download personal interview schedule as CSV"
              >
                <Download className="w-3.5 h-3.5 text-emerald-400" />
                <span>Export CSV</span>
              </button>
            </div>
            </div>

            {schedule.length === 0 ? (
              <div className="p-6 bg-[#0d1527] border border-[#1b2b4d] rounded-2xl text-center text-xs text-slate-400">
                No interview or test rounds scheduled yet.
              </div>
            ) : (
              <div className="space-y-3">
                {schedule.slice(0, 3).map((slot) => (
                  <div
                    key={slot.slot_id}
                    className="bg-[#0d1527] border border-[#1b2b4d] rounded-2xl p-4 shadow-sm space-y-2.5 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-bold text-white text-sm block">{slot.company_name}</span>
                        <span className="text-emerald-400 font-bold block">{slot.round_name}</span>
                      </div>
                      <Badge variant="success" size="sm">Confirmed</Badge>
                    </div>
                    <div className="flex items-center justify-between text-slate-300">
                      <span>Room: <strong className="text-white">{slot.room_name} ({slot.building})</strong></span>
                      <span className="font-mono text-emerald-400 font-bold">{slot.start_time}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* SCREEN 4: MY SCHEDULE */}
      {activeTab === "schedule" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Calendar className="w-4 h-4 text-emerald-400" />
              <span>My Scheduled Rounds & Campus Venues</span>
            </h2>
            <button
              onClick={handleDownloadCalendar}
              className="min-h-[44px] px-3.5 py-1.5 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white text-xs font-bold rounded-2xl border border-emerald-400/30 flex items-center gap-1.5 transition-all cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Add to Calendar (.ics)</span>
            </button>
          </div>

          {schedule.length === 0 ? (
            <div className="p-8 bg-[#0d1527] border border-[#1b2b4d] rounded-3xl text-center text-xs text-slate-400 space-y-1">
              <span className="font-bold text-slate-300 block">No rounds scheduled yet</span>
              <p className="text-[11px] text-slate-500">
                When the placement officer allocates your test lab or interview cabin, it will appear here.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {schedule.map((slot) => (
                <div
                  key={slot.slot_id}
                  className={`bg-[#0d1527] border rounded-3xl p-4 shadow-sm space-y-3 transition-all ${
                    slot.is_next_upcoming
                      ? "border-emerald-500/80 ring-2 ring-emerald-500/20"
                      : "border-[#1b2b4d]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-sm font-black text-white block">{slot.company_name}</span>
                      <span className="text-xs font-bold text-emerald-400 block">{slot.round_name}</span>
                    </div>

                    {slot.is_next_upcoming ? (
                      <span className="text-[11px] font-bold px-2.5 py-1 bg-emerald-950 text-emerald-300 rounded-xl border border-emerald-800 flex items-center gap-1">
                        <Sparkles className="w-3 h-3 text-emerald-400" /> Next Upcoming
                      </span>
                    ) : slot.has_clash ? (
                      <Badge variant="danger" size="sm">
                        <AlertTriangle className="w-3 h-3 inline mr-1" /> Clash Warning
                      </Badge>
                    ) : (
                      <Badge variant="success" size="sm">Confirmed</Badge>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2.5 bg-[#080e1c] rounded-2xl border border-[#162447] space-y-0.5">
                      <span className="text-[10px] text-slate-400 uppercase font-bold flex items-center gap-1">
                        <Clock className="w-3 h-3 text-blue-400" /> Slot Time
                      </span>
                      <span className="font-bold text-slate-200 block text-xs">
                        {slot.start_time} - {slot.end_time}
                      </span>
                    </div>

                    <div className="p-2.5 bg-[#080e1c] rounded-2xl border border-[#162447] space-y-0.5">
                      <span className="text-[10px] text-slate-400 uppercase font-bold flex items-center gap-1">
                        <MapPin className="w-3 h-3 text-emerald-400" /> Room / Venue
                      </span>
                      <span className="font-bold text-slate-200 block text-xs truncate">
                        {slot.room_name} ({slot.building || "Campus"})
                      </span>
                    </div>
                  </div>

                  <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1 border-t border-[#1b2b4d]/50">
                    <span>Interview Panel: <strong className="text-slate-300">{slot.panel_name}</strong></span>
                    <span className="text-emerald-400 font-mono font-bold">0 Clashes Verified</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Home Schedule Stream */}
          <div className="pt-4 border-t border-[#1b2b4d] space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Calendar className="w-4 h-4 text-emerald-400" />
                <span>My Scheduled Rounds & Campus Venues</span>
              </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={handleDownloadCalendar}
                className="min-h-[44px] px-3.5 py-1.5 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white text-xs font-bold rounded-2xl border border-emerald-400/30 flex items-center gap-1.5 transition-all cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Add to Calendar (.ics)</span>
              </button>
              <button
                onClick={handleDownloadScheduleCsv}
                className="min-h-[44px] px-3.5 py-1.5 bg-[#111d38] hover:bg-[#1b2b4d] text-emerald-300 text-xs font-bold rounded-2xl border border-emerald-500/30 hover:border-emerald-500/60 flex items-center gap-1.5 transition-all cursor-pointer"
                title="Download personal interview schedule as CSV"
              >
                <Download className="w-3.5 h-3.5 text-emerald-400" />
                <span>Export CSV</span>
              </button>
            </div>
            </div>

            {schedule.length === 0 ? (
              <div className="p-6 bg-[#0d1527] border border-[#1b2b4d] rounded-2xl text-center text-xs text-slate-400">
                No interview or test rounds scheduled yet.
              </div>
            ) : (
              <div className="space-y-3">
                {schedule.slice(0, 3).map((slot) => (
                  <div
                    key={slot.slot_id}
                    className="bg-[#0d1527] border border-[#1b2b4d] rounded-2xl p-4 shadow-sm space-y-2.5 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-bold text-white text-sm block">{slot.company_name}</span>
                        <span className="text-emerald-400 font-bold block">{slot.round_name}</span>
                      </div>
                      <Badge variant="success" size="sm">Confirmed</Badge>
                    </div>
                    <div className="flex items-center justify-between text-slate-300">
                      <span>Room: <strong className="text-white">{slot.room_name} ({slot.building})</strong></span>
                      <span className="font-mono text-emerald-400 font-bold">{slot.start_time}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* SCREEN 5: CLASH WARNINGS */}
      {activeTab === "clashes" && (
        <div className="space-y-4">
          <div className="bg-[#0d1527] p-5 rounded-3xl border border-[#1b2b4d] shadow-md space-y-3">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>Drive & Round Clash Management</span>
            </h2>

            {clashData?.has_clash ? (
              <div className="p-3.5 bg-amber-950/70 border border-amber-800 text-amber-200 rounded-2xl text-xs space-y-1.5">
                <span className="font-bold text-sm block">⚠️ Potential Schedule Conflict Detected</span>
                <p className="leading-relaxed">
                  {clashData.instruction || "If two drives overlap, please contact the placement officer immediately to resolve the schedule conflict."}
                </p>
              </div>
            ) : (
              <div className="p-3.5 bg-emerald-950/60 border border-emerald-800 text-emerald-200 rounded-2xl text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>0 Clashes Verified. You have no overlapping test or interview rounds.</span>
              </div>
            )}

            {/* Clash Preference Recording Form */}
            <form onSubmit={handleSubmitClashPreference} className="space-y-3 pt-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-300 block">
                Record Your Company Preference for Officer
              </span>

              {clashFeedback && (
                <div className="p-3 bg-emerald-950/80 border border-emerald-700 text-emerald-300 rounded-xl text-xs">
                  {clashFeedback}
                </div>
              )}

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                  Which company drive do you prioritize?
                </label>
                <input
                  type="text"
                  required
                  value={clashPreferredCompany}
                  onChange={(e) => setClashPreferredCompany(e.target.value)}
                  className="w-full min-h-[44px] px-3.5 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-semibold text-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  placeholder="e.g. Google or Microsoft"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                  Supporting Note for Officer (Optional)
                </label>
                <textarea
                  rows={2}
                  value={clashNote}
                  onChange={(e) => setClashNote(e.target.value)}
                  className="w-full px-3.5 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs text-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  placeholder="e.g. Role aligns directly with my major project"
                />
              </div>

              <button
                type="submit"
                disabled={clashSubmitting}
                className="w-full min-h-[44px] py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs rounded-2xl transition-all cursor-pointer disabled:opacity-50"
              >
                {clashSubmitting ? "Submitting Preference..." : "Send Preference to Placement Officer"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* SCREEN 6: MY OFFERS */}
      {activeTab === "offers" && (
        <div className="space-y-4">
          <div className="bg-[#0d1527] p-5 rounded-3xl border border-[#1b2b4d] shadow-md space-y-3">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              <span>My Job Offers & Placement Status</span>
            </h2>

            {offersData?.policy_impact && (
              <div className="p-3.5 bg-gradient-to-r from-[#0c1836] to-[#072421] border border-emerald-500/40 rounded-2xl text-xs text-slate-200 leading-relaxed font-medium">
                {offersData.policy_impact}
              </div>
            )}

            {offersData?.offers?.length === 0 ? (
              <div className="p-8 bg-[#080e1c] rounded-2xl text-center text-xs text-slate-400">
                You currently have 0 job offers. You are eligible to participate in all campus drives where you meet academic criteria.
              </div>
            ) : (
              <div className="space-y-2.5">
                {offersData?.offers?.map((off: any) => (
                  <div
                    key={off.id}
                    className="p-3.5 bg-[#080e1c] rounded-2xl border border-[#1b2b4d] flex items-center justify-between text-xs"
                  >
                    <div>
                      <span className="font-bold text-white text-sm block">{off.company}</span>
                      <span className="text-[11px] text-slate-400 block mt-0.5">
                        Offered on {new Date(off.offer_date).toLocaleDateString()}
                      </span>
                    </div>

                    <div className="text-right">
                      <span className="font-mono text-emerald-400 font-black text-sm block">
                        {off.ctc_lpa} LPA
                      </span>
                      <Badge variant={off.is_dream ? "brand" : "success"} size="sm">
                        {off.is_dream ? "DREAM OFFER" : "ACCEPTED"}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* SCREEN 7: COLLEGE POLICY EXPLAINED */}
      {activeTab === "policy" && (
        <div className="space-y-4">
          <div className="bg-[#0d1527] p-5 rounded-3xl border border-[#1b2b4d] shadow-md space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-[#1b2b4d]">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-400" />
                <span>College Offer Policy Explained</span>
              </h2>
              <Badge variant="brand" size="sm">Active Rule</Badge>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed font-medium">
              {policyData?.plain_english_summary ||
                "Every student can accept at most one regular job offer. If you receive an offer below 10.0 LPA, you are still allowed to sit for Dream companies offering 10.0 LPA or higher."}
            </p>

            <span className="text-xs font-bold uppercase tracking-wider text-slate-300 block pt-2">
              Worked Examples
            </span>

            <div className="space-y-2.5">
              {policyData?.worked_examples?.map((ex: any, idx: number) => (
                <div key={idx} className="p-3.5 bg-[#080e1c] rounded-2xl border border-[#162447] space-y-1 text-xs">
                  <span className="font-bold text-indigo-300 block">{ex.title}</span>
                  <span className="text-slate-400 block font-semibold">{ex.scenario}</span>
                  <p className="text-slate-300 leading-relaxed font-medium">{ex.explanation}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* SCREEN 8: MY PROFILE (Read-Only) */}
      {activeTab === "profile" && (
        <div className="space-y-4">
          <div className="bg-[#0d1527] p-5 rounded-3xl border border-[#1b2b4d] shadow-md space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-[#1b2b4d]">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-emerald-400" />
                <span>Verified Academic Profile</span>
              </h2>
              <span className="text-[11px] text-slate-400">Read-Only</span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-3 bg-[#080e1c] rounded-2xl border border-[#162447]">
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Full Name</span>
                <span className="font-bold text-white block mt-0.5">{studentInfo?.name || "Student"}</span>
              </div>
              <div className="p-3 bg-[#080e1c] rounded-2xl border border-[#162447]">
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Roll Number</span>
                <span className="font-mono font-bold text-emerald-400 block mt-0.5">{studentInfo?.roll_no || user.username}</span>
              </div>
              <div className="p-3 bg-[#080e1c] rounded-2xl border border-[#162447]">
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Branch</span>
                <span className="font-bold text-slate-200 block mt-0.5">{studentInfo?.branch || "Engineering"}</span>
              </div>
              <div className="p-3 bg-[#080e1c] rounded-2xl border border-[#162447]">
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Cumulative CGPA</span>
                <span className="font-mono font-black text-emerald-400 block mt-0.5">{studentInfo?.cgpa?.toFixed(2) || "8.50"}</span>
              </div>
              <div className="p-3 bg-[#080e1c] rounded-2xl border border-[#162447]">
                <span className="text-[10px] text-slate-400 uppercase font-bold block">10th Percentage</span>
                <span className="font-bold text-slate-200 block mt-0.5">{studentInfo?.tenth_percentage?.toFixed(1) || "85.0"}%</span>
              </div>
              <div className="p-3 bg-[#080e1c] rounded-2xl border border-[#162447]">
                <span className="text-[10px] text-slate-400 uppercase font-bold block">12th Percentage</span>
                <span className="font-bold text-slate-200 block mt-0.5">
                  {studentInfo?.twelfth_percentage ? `${studentInfo.twelfth_percentage.toFixed(1)}%` : "N/A (Diploma)"}
                </span>
              </div>
            </div>

            {/* Semester-wise SGPA Breakdown */}
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300 block pt-1">
              Semester-wise SGPA Marks
            </span>
            <div className="grid grid-cols-4 gap-1.5 text-center text-xs">
              {studentInfo?.semester_records?.map((rec: any) => (
                <div key={rec.semester} className="p-2 bg-[#080e1c] rounded-xl border border-[#162447]">
                  <span className="text-[10px] text-slate-400 uppercase font-bold block">Sem {rec.semester}</span>
                  <span className="font-mono font-bold text-emerald-400 block mt-0.5">{rec.sgpa.toFixed(2)}</span>
                </div>
              ))}
            </div>

            {/* Backlogs & Gap Years */}
            <div className="grid grid-cols-2 gap-2 text-xs pt-1">
              <div className="p-3 bg-[#080e1c] rounded-2xl border border-[#162447]">
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Active Backlogs</span>
                <span className="font-bold text-rose-400 block mt-0.5">{studentInfo?.active_backlogs_count || 0} active</span>
              </div>
              <div className="p-3 bg-[#080e1c] rounded-2xl border border-[#162447]">
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Education Gap Years</span>
                <span className="font-bold text-slate-200 block mt-0.5">{studentInfo?.gap_years_count || 0} years</span>
              </div>
            </div>

            <button
              onClick={() => setActiveTab("corrections")}
              className="min-h-[44px] w-full py-2.5 bg-[#111d38] hover:bg-[#162447] text-amber-300 hover:text-amber-200 border border-amber-500/30 rounded-2xl text-xs font-bold transition-all cursor-pointer flex items-center justify-center gap-2 mt-2"
            >
              <AlertCircle className="w-4 h-4 text-amber-400" />
              <span>Found a mistake in your marks? Submit a Correction</span>
            </button>
          </div>
        </div>
      )}

      {/* SCREEN 9: "SOMETHING LOOKS WRONG" (Data Correction Request) */}
      {activeTab === "corrections" && (
        <div className="space-y-4">
          <div className="bg-[#0d1527] p-5 rounded-3xl border border-[#1b2b4d] shadow-md space-y-3">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-400" />
              <span>Report a Mistake in Your Data</span>
            </h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              If your CGPA, marks, or backlogs differ from your official mark sheet, submit an official correction request to the placement officer.
            </p>

            {corrFeedback && (
              <div className="p-3 bg-emerald-950/80 border border-emerald-700 text-emerald-300 rounded-2xl text-xs">
                {corrFeedback}
              </div>
            )}

            <form onSubmit={handleSubmitCorrection} className="space-y-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                  Which field needs correction?
                </label>
                <select
                  value={corrField}
                  onChange={(e) => setCorrField(e.target.value)}
                  className="w-full min-h-[44px] px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-semibold text-white focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer"
                >
                  <option value="CGPA">CGPA Grade</option>
                  <option value="Active Backlogs">Active Backlogs (Mark as Cleared)</option>
                  <option value="10th Marks">10th Percentage</option>
                  <option value="12th Marks">12th Percentage</option>
                  <option value="Gap Years">Gap Years</option>
                  <option value="Contact Info">Phone Number / Email</option>
                  <option value="Other">Other Information</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                  Describe what is wrong and what the correct value should be
                </label>
                <textarea
                  required
                  rows={3}
                  value={corrProblem}
                  onChange={(e) => setCorrProblem(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs text-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  placeholder="e.g. My Sem 6 re-evaluation was approved, raising CGPA from 7.56 to 7.82"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                  Supporting Note / Proof Details (Optional)
                </label>
                <input
                  type="text"
                  value={corrNote}
                  onChange={(e) => setCorrNote(e.target.value)}
                  className="w-full min-h-[44px] px-3.5 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs text-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  placeholder="e.g. Physical grade card signed by Exam Controller"
                />
              </div>

              <button
                type="submit"
                disabled={corrSubmitting}
                className="w-full min-h-[48px] py-2.5 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white font-bold text-xs rounded-2xl shadow-md transition-all cursor-pointer disabled:opacity-50"
              >
                {corrSubmitting ? "Submitting Request..." : "Submit Correction to Officer"}
              </button>
            </form>
          </div>

          {/* Past Requests History */}
          <div className="space-y-2.5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Submitted Correction Requests
            </h3>

            {correctionsList.length === 0 ? (
              <div className="p-6 bg-[#0d1527] border border-[#1b2b4d] rounded-2xl text-center text-xs text-slate-400">
                You have not submitted any data correction requests.
              </div>
            ) : (
              <div className="space-y-2">
                {correctionsList.map((req) => (
                  <div
                    key={req.id}
                    className="p-3.5 bg-[#0d1527] border border-[#1b2b4d] rounded-2xl space-y-1.5 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white">{req.field}</span>
                      <Badge
                        variant={
                          req.status === "fixed"
                            ? "success"
                            : req.status === "rejected"
                            ? "danger"
                            : "brand"
                        }
                        size="sm"
                      >
                        {req.status_label || req.status}
                      </Badge>
                    </div>

                    <p className="text-slate-300 leading-relaxed">{req.problem}</p>

                    {req.officer_response && (
                      <div className="p-2 bg-[#080e1c] rounded-xl border border-[#162447] text-[11px] text-emerald-300">
                        Officer note: {req.officer_response}
                      </div>
                    )}

                    <span className="text-[10px] text-slate-500 block">
                      Submitted on {req.submitted_at}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* SCREEN 10: NOTIFICATIONS */}
      {activeTab === "notifications" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Bell className="w-4 h-4 text-purple-400" />
              <span>Status & Schedule Notifications</span>
            </h2>
          </div>

          <div className="space-y-2.5">
            {notifications.map((n) => (
              <div
                key={n.id}
                className="p-3.5 bg-[#0d1527] border border-[#1b2b4d] rounded-2xl space-y-1 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white">{n.title}</span>
                  <span className="text-[10px] text-slate-500">{n.created_at}</span>
                </div>
                <p className="text-slate-300 leading-relaxed font-medium">{n.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SCREEN 11: PRINTABLE STATUS SHEET */}
      {activeTab === "print" && (
        <div className="space-y-4">
          <div className="bg-[#0d1527] p-5 rounded-3xl border border-[#1b2b4d] shadow-md space-y-3 no-print">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Printer className="w-4 h-4 text-emerald-400" />
              <span>Printable Status Sheet</span>
            </h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              Generate a clean, single-page printable status sheet showing all your drives, verdicts, and schedule.
            </p>

            <div className="flex items-center gap-2.5 pt-1">
              <button
                onClick={() => window.print()}
                className="min-h-[44px] flex-1 py-2.5 bg-[#111d38] hover:bg-[#162447] text-white border border-[#1b2b4d] rounded-2xl text-xs font-bold transition-all cursor-pointer flex items-center justify-center gap-2"
              >
                <Printer className="w-4 h-4 text-emerald-400" />
                <span>Print Clean Sheet</span>
              </button>

              <a
                href="/api/portal/status-sheet-pdf"
                target="_blank"
                rel="noopener noreferrer"
                className="min-h-[44px] flex-1 py-2.5 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white rounded-2xl text-xs font-bold transition-all flex items-center justify-center gap-2 border border-emerald-400/30"
              >
                <Download className="w-4 h-4" />
                <span>Official PDF</span>
              </a>

              <a
                href="/api/portal/status-sheet-csv"
                download={`placement_status_${studentInfo?.roll_no || "candidate"}.csv`}
                className="min-h-[44px] flex-1 py-2.5 bg-[#111d38] hover:bg-[#162447] text-emerald-300 rounded-2xl text-xs font-bold transition-all flex items-center justify-center gap-2 border border-emerald-500/30 hover:border-emerald-500/60"
                title="Download personal status and eligibility records as CSV"
              >
                <Download className="w-4 h-4 text-emerald-400" />
                <span>Export CSV</span>
              </a>
            </div>
          </div>

          {/* Clean Printable Canvas */}
          <div className="p-6 bg-white text-slate-900 rounded-3xl space-y-4 print-container shadow-md">
            <div className="border-b pb-3 space-y-1">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
                Office of Training and Placement • Institutional Status Sheet
              </span>
              <h3 className="text-base font-black text-slate-900">{studentInfo?.name} ({studentInfo?.roll_no})</h3>
              <div className="text-xs text-slate-600">
                <span>Branch: {studentInfo?.branch}</span> • <span>CGPA: {studentInfo?.cgpa?.toFixed(2)}</span> • <span>Active Backlogs: {studentInfo?.active_backlogs_count || 0}</span>
              </div>
            </div>

            <div className="space-y-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
                Campus Recruitment Drives & Verdicts
              </span>
              <div className="space-y-2 text-xs">
                {drives.map((d) => (
                  <div key={d.drive_id} className="p-2 border rounded-xl flex items-center justify-between">
                    <div>
                      <span className="font-bold text-slate-900 block">{d.company_name} ({d.ctc_lpa} LPA)</span>
                      <span className="text-slate-600 text-[11px] block">{d.headline_reason}</span>
                    </div>
                    <span className="font-bold uppercase text-[10px] px-2 py-0.5 bg-slate-100 rounded">
                      {d.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-2 pt-2 border-t">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
                Confirmed Schedule Slots
              </span>
              {schedule.length === 0 ? (
                <div className="text-xs text-slate-500">No interview or test rounds scheduled.</div>
              ) : (
                <div className="space-y-1.5 text-xs">
                  {schedule.map((sl) => (
                    <div key={sl.slot_id} className="p-2 border rounded-xl flex items-center justify-between">
                      <div>
                        <span className="font-bold text-slate-900">{sl.company_name} - {sl.round_name}</span>
                        <span className="text-slate-600 text-[11px] block">{sl.room_name} ({sl.building})</span>
                      </div>
                      <span className="font-mono text-xs font-semibold">{sl.start_time}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* SCREEN 12: HELP / FAQ */}
      {activeTab === "faq" && (
        <div className="space-y-4">
          <div className="bg-[#0d1527] p-5 rounded-3xl border border-[#1b2b4d] shadow-md space-y-3">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <HelpCircle className="w-4 h-4 text-emerald-400" />
              <span>Placement Portal Help & FAQ</span>
            </h2>

            <div className="space-y-3 text-xs">
              <div className="p-3.5 bg-[#080e1c] rounded-2xl border border-[#162447] space-y-1">
                <span className="font-bold text-emerald-300 block">
                  1. What is the difference between active backlogs and history of backlogs?
                </span>
                <p className="text-slate-300 leading-relaxed font-medium">
                  An active backlog is a subject you have not yet passed. A history backlog is a subject you previously failed but have now cleared. Many companies accept candidates with history backlogs as long as they currently have zero active backlogs.
                </p>
              </div>

              <div className="p-3.5 bg-[#080e1c] rounded-2xl border border-[#162447] space-y-1">
                <span className="font-bold text-emerald-300 block">
                  2. What is a Dream Company?
                </span>
                <p className="text-slate-300 leading-relaxed font-medium">
                  Under college placement rules, a Dream company offers a salary of 10.0 LPA or above. Even if you already hold one regular job offer, you are permitted to sit for Dream company drives to upgrade your placement.
                </p>
              </div>

              <div className="p-3.5 bg-[#080e1c] rounded-2xl border border-[#162447] space-y-1">
                <span className="font-bold text-emerald-300 block">
                  3. Why is my CGPA shown this way?
                </span>
                <p className="text-slate-300 leading-relaxed font-medium">
                  Your CGPA is calculated from your semester mark sheets recorded in the institutional database. If your latest grade revision or re-evaluation result has not yet been updated, use "Fix Mistakes" to notify the placement officer.
                </p>
              </div>

              <div className="p-3.5 bg-[#080e1c] rounded-2xl border border-[#162447] space-y-1">
                <span className="font-bold text-emerald-300 block">
                  4. Who do I contact if I have a schedule clash?
                </span>
                <p className="text-slate-300 leading-relaxed font-medium">
                  Contact the Training and Placement Cell in Room 204 or submit your preference in the "Clashes" tab. The placement officer will review and adjust slot timings.
                </p>
              </div>
            </div>

            <button
              onClick={() => setIsChangePasswordOpen(true)}
              className="min-h-[44px] w-full py-2.5 bg-[#111d38] hover:bg-[#162447] text-slate-200 hover:text-white border border-[#1b2b4d] rounded-2xl text-xs font-bold transition-all cursor-pointer flex items-center justify-center gap-2 mt-2"
            >
              <KeyRound className="w-4 h-4 text-blue-400" />
              <span>Change Portal Login Password</span>
            </button>
          </div>
        </div>
      )}
          </div>
        )}
      </main>

      {/* Change Password Modal */}
      {isChangePasswordOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs">
          <div className="bg-[#0d1527] rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-[#1b2b4d] space-y-4 text-slate-100">
            <div className="flex items-center justify-between pb-2 border-b border-[#1b2b4d]">
              <div className="flex items-center gap-2">
                <KeyRound className="w-4 h-4 text-blue-400" />
                <h3 className="text-sm font-bold text-white">Change Portal Password</h3>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsChangePasswordOpen(false);
                  setPasswordError(null);
                  setPasswordSuccess(null);
                }}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-[#111d38] cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {passwordError && (
              <div className="p-3 bg-rose-950/70 border border-rose-800 text-rose-300 rounded-xl text-xs">
                {passwordError}
              </div>
            )}
            {passwordSuccess && (
              <div className="p-3 bg-emerald-950/70 border border-emerald-800 text-emerald-300 rounded-xl text-xs">
                {passwordSuccess}
              </div>
            )}

            <form onSubmit={handleChangePasswordSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1">
                  Current Password
                </label>
                <div className="relative">
                  <input
                    type={showCurrentPassword ? "text" : "password"}
                    required
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="Enter current password"
                    className="w-full min-h-[44px] pl-3 pr-10 py-2 bg-[#080e1c] border border-[#1b2b4d] rounded-xl text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    className="absolute right-3 top-3 text-slate-400 hover:text-white cursor-pointer"
                  >
                    {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1">
                  New Password
                </label>
                <div className="relative">
                  <input
                    type={showNewPassword ? "text" : "password"}
                    required
                    minLength={4}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Minimum 4 characters"
                    className="w-full min-h-[44px] pl-3 pr-10 py-2 bg-[#080e1c] border border-[#1b2b4d] rounded-xl text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-3 top-3 text-slate-400 hover:text-white cursor-pointer"
                  >
                    {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1">
                  Confirm New Password
                </label>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-type new password"
                  className="w-full min-h-[44px] px-3 py-2 bg-[#080e1c] border border-[#1b2b4d] rounded-xl text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setIsChangePasswordOpen(false)}
                  className="min-h-[44px] px-4 py-2 text-xs font-bold text-slate-400 hover:text-white bg-[#111d38] rounded-xl cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={passwordLoading}
                  className="min-h-[44px] px-5 py-2 bg-gradient-to-r from-blue-600 to-emerald-600 text-white font-bold text-xs rounded-xl shadow-md cursor-pointer disabled:opacity-50"
                >
                  {passwordLoading ? "Saving..." : "Save Password"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
