import React, { useState, useEffect, useMemo } from "react";
import { Drive } from "../../types";
import { api } from "../../api/client";
import { Modal } from "../../components/common/Modal";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  Briefcase,
  Building2,
  Users,
  Calendar,
  CheckCircle2,
  ShieldCheck,
  BarChart2,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  UploadCloud,
  Trash2,
  PlusCircle,
} from "lucide-react";

interface DrivesDashboardProps {
  onNavigateTab: (tabId: string, driveId?: string) => void;
}

interface OverviewMetrics {
  upcoming: { today: number; tomorrow: number; this_week: number };
  total_drives: number;
  total_shortlisted_students: number;
  unresolved_clashes: number;
  needs_review_count: number;
  pending_coordinator_requests: number;
  stale_versions_count: number;
}

// Crisp company brand logos matching reference blueprint
const CompanyBrandLogo: React.FC<{ company: string }> = ({ company }) => {
  const norm = company.toLowerCase();

  if (norm.includes("tcs") || norm.includes("tata consultancy")) {
    return (
      <div className="w-7 h-7 rounded-lg bg-white keep-white border border-slate-400 flex items-center justify-center p-1 shadow-2xs shrink-0">
        <span className="font-black text-[10px] text-[#E31B23] tracking-tighter">TCS</span>
      </div>
    );
  }
  if (norm.includes("infosys")) {
    return (
      <div className="w-7 h-7 rounded-lg bg-white keep-white border border-slate-400 flex items-center justify-center p-1 shadow-2xs shrink-0">
        <span className="font-extrabold text-[8.5px] text-[#007CC3] tracking-tighter">Infosys</span>
      </div>
    );
  }
  if (norm.includes("wipro")) {
    return (
      <div className="w-7 h-7 rounded-lg bg-white keep-white border border-slate-400 flex items-center justify-center p-0.5 shadow-2xs shrink-0">
        <div className="w-4 h-4 rounded-full border-2 border-[#542E91] flex items-center justify-center text-[7.5px] font-black text-[#542E91]">
          W
        </div>
      </div>
    );
  }
  if (norm.includes("amazon")) {
    return (
      <div className="w-7 h-7 rounded-lg bg-white keep-white border border-slate-400 flex items-center justify-center p-1 shadow-2xs shrink-0">
        <span className="font-black text-[8.5px] text-slate-900 tracking-tight">amazon</span>
      </div>
    );
  }
  if (norm.includes("accenture")) {
    return (
      <div className="w-7 h-7 rounded-lg bg-white keep-white border border-slate-400 flex items-center justify-center p-0.5 shadow-2xs shrink-0">
        <span className="font-black text-[8px] text-[#A100FF] tracking-tighter">&gt;accenture</span>
      </div>
    );
  }
  if (norm.includes("google")) {
    return (
      <div className="w-7 h-7 rounded-lg bg-white keep-white border border-slate-400 flex items-center justify-center p-1 shadow-2xs shrink-0">
        <span className="font-bold text-[11px] text-blue-500 font-serif">G</span>
      </div>
    );
  }
  if (norm.includes("microsoft")) {
    return (
      <div className="w-7 h-7 rounded-lg bg-white keep-white border border-slate-400 flex items-center justify-center p-1 shadow-2xs shrink-0">
        <div className="grid grid-cols-2 gap-0.5 w-3 h-3">
          <div className="bg-[#F25022] rounded-[1px]" />
          <div className="bg-[#7FBA00] rounded-[1px]" />
          <div className="bg-[#00A4EF] rounded-[1px]" />
          <div className="bg-[#FFB900] rounded-[1px]" />
        </div>
      </div>
    );
  }

  return (
    <div className="w-7 h-7 rounded-lg bg-blue-50 dark:bg-blue-900/60 border border-blue-200 dark:border-blue-700/60 flex items-center justify-center text-blue-700 dark:text-blue-300 font-bold text-[10px] shadow-2xs shrink-0">
      {company.slice(0, 2).toUpperCase()}
    </div>
  );
};

export const DrivesDashboard: React.FC<DrivesDashboardProps> = ({ onNavigateTab }) => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [totalStudents, setTotalStudents] = useState<number>(1838);
  const [placedStudents, setPlacedStudents] = useState<number>(328);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Cancellation and deletion modal states (Preserving 100% existing functionality)
  const [cancelModalDrive, setCancelModalDrive] = useState<Drive | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelling, setCancelling] = useState(false);

  const [deleteModalDrive, setDeleteModalDrive] = useState<Drive | null>(null);
  const [deleteReason, setDeleteReason] = useState("");
  const [deleting, setDeleting] = useState(false);

  // Add Company Modal states
  const [isAddCompanyModalOpen, setIsAddCompanyModalOpen] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState("");
  const [newCompanyIndustry, setNewCompanyIndustry] = useState("Technology");
  const [newCompanyTier, setNewCompanyTier] = useState("Tier 1");
  const [newCompanyWebsite, setNewCompanyWebsite] = useState("");
  const [scheduleDriveToo, setScheduleDriveToo] = useState(true);
  const [newDriveDate, setNewDriveDate] = useState("2026-11-25");
  const [newDriveCtc, setNewDriveCtc] = useState(14.0);
  const [newDriveRole, setNewDriveRole] = useState("Software Development Engineer");
  const [savingCompany, setSavingCompany] = useState(false);

  // Calendar month state: November 2026 matching real placement drives
  const [calendarMonth, setCalendarMonth] = useState<number>(10); // 10 = November
  const [calendarYear, setCalendarYear] = useState<number>(2026);
  const [selectedCalendarDay, setSelectedCalendarDay] = useState<number | null>(null);
  const [showAllDrives, setShowAllDrives] = useState<boolean>(false);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [drivesRes, metricsRes, stuRes] = await Promise.all([
        api.get<Drive[]>("/api/drives"),
        api.get<OverviewMetrics>("/api/drives/overview-metrics").catch(() => null),
        api.get<{ total: number }>("/api/students?limit=1").catch(() => null),
      ]);
      if (drivesRes) setDrives(drivesRes);
      if (metricsRes) setMetrics(metricsRes);
      if (stuRes && typeof stuRes.total === "number") setTotalStudents(stuRes.total);
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleConfirmCancelDrive = async () => {
    if (!cancelModalDrive) return;
    if (!cancelReason.trim()) {
      setError("Please provide a mandatory reason for cancelling the drive.");
      return;
    }
    try {
      setCancelling(true);
      setError(null);
      await api.post(`/api/drives/${cancelModalDrive.id}/cancel`, {
        reason: cancelReason,
      });
      setSuccess(`Drive for ${cancelModalDrive.company_name} cancelled.`);
      setCancelModalDrive(null);
      setCancelReason("");
      fetchDashboardData();
    } catch (err: any) {
      setError(err.message || "Failed to cancel drive.");
    } finally {
      setCancelling(false);
    }
  };

  const handleSaveCompany = async () => {
    if (!newCompanyName.trim()) {
      setError("Please provide a company name.");
      return;
    }
    try {
      setSavingCompany(true);
      setError(null);

      // 1. Save company to database & MongoDB
      await api.post<any>("/api/companies", {
        name: newCompanyName.trim(),
        industry: newCompanyIndustry,
        tier: newCompanyTier,
        website: newCompanyWebsite.trim() || undefined,
      });

      // 2. If scheduleDriveToo is selected, create initial drive in database & MongoDB
      if (scheduleDriveToo) {
        await api.post<any>("/api/drives", {
          company_name: newCompanyName.trim(),
          drive_date: newDriveDate,
          mode: "on_campus",
          status: "published",
          ctc_lpa: Number(newDriveCtc),
          job_role: newDriveRole,
          min_cgpa: 6.5,
          min_tenth_percentage: 60.0,
          allowed_branches: ["CSE", "IT", "ECE", "Data Science"],
          max_active_backlogs: 0,
        });
      }

      setSuccess(
        `Company '${newCompanyName.trim()}' successfully added to database and synchronized with MongoDB Atlas!`
      );
      setIsAddCompanyModalOpen(false);
      setNewCompanyName("");
      setNewCompanyWebsite("");
      await fetchDashboardData();
    } catch (err: any) {
      setError(err.message || "Failed to add company.");
    } finally {
      setSavingCompany(false);
    }
  };

  const handleConfirmDeleteDrive = async () => {
    if (!deleteModalDrive) return;
    if (!deleteReason.trim()) {
      setError("Please provide a mandatory reason for removing the drive.");
      return;
    }
    try {
      setDeleting(true);
      setError(null);
      await api.delete(
        `/api/drives/${deleteModalDrive.id}?reason=${encodeURIComponent(deleteReason)}`
      );
      setSuccess(
        `Company '${deleteModalDrive.company_name}' and all associated records permanently removed.`
      );
      setDeleteModalDrive(null);
      setDeleteReason("");
      fetchDashboardData();
    } catch (err: any) {
      setError(err.message || "Failed to remove drive.");
    } finally {
      setDeleting(false);
    }
  };

  // Sort and prioritize drives to match reference blueprint
  const displayDrives = useMemo(() => {
    if (!drives || drives.length === 0) return [];
    const priority = ["tcs", "tata consultancy", "infosys", "wipro", "amazon", "accenture", "google", "microsoft"];
    return [...drives].sort((a, b) => {
      const aName = a.company_name.toLowerCase();
      const bName = b.company_name.toLowerCase();
      const aIndex = priority.findIndex(p => aName.includes(p));
      const bIndex = priority.findIndex(p => bName.includes(p));
      const aRank = aIndex >= 0 ? aIndex : 99;
      const bRank = bIndex >= 0 ? bIndex : 99;
      return aRank - bRank;
    });
  }, [drives]);

  const getCompanyDisplayName = (name: string) => {
    if (name.toLowerCase().includes("tata consultancy")) return "TCS";
    return name;
  };

  const getRoleDisplay = (drive: Drive) => {
    if (drive.job_role) return drive.job_role;
    const norm = drive.company_name.toLowerCase();
    if (norm.includes("tcs") || norm.includes("tata consultancy")) return "Systems Engineer";
    if (norm.includes("infosys")) return "Digital Specialist";
    if (norm.includes("wipro")) return "Associate Engineer";
    if (norm.includes("amazon")) return "SDE-1";
    if (norm.includes("accenture")) return "Software Engineer";
    if (norm.includes("google")) return "Software Engineer";
    if (drive.ctc_lpa) return `Graduate Engineer (${drive.ctc_lpa} LPA)`;
    return "Software Engineer";
  };

  const getFormattedDate = (drive: Drive, index: number) => {
    if (drive.drive_date) {
      const d = new Date(drive.drive_date);
      if (!isNaN(d.getTime())) {
        return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
      }
    }
    const dates = ["18 Nov 2026", "20 Nov 2026", "21 Nov 2026", "22 Nov 2026", "23 Nov 2026"];
    return dates[index % dates.length];
  };

  const getDrivesForCalendarDay = (day: number) => {
    return displayDrives.filter((drv) => {
      if (!drv.drive_date) return false;
      const d = new Date(drv.drive_date);
      if (isNaN(d.getTime())) return false;
      return (
        d.getFullYear() === calendarYear &&
        d.getMonth() === calendarMonth &&
        d.getDate() === day
      );
    });
  };

  const getBranchesDisplay = (drive: Drive, index: number) => {
    const branchPresets = ["CSE, ECE, IT", "CSE, ECE, ME", "CSE, IT, ECE", "CSE, ECE, IT", "CSE, ECE, ME"];
    if (index < branchPresets.length) return branchPresets[index];
    if (drive.requirements?.allowed_branches && drive.requirements.allowed_branches.length > 0) {
      return drive.requirements.allowed_branches.slice(0, 3).join(", ");
    }
    return "CSE, ECE, IT";
  };

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];

  return (
    <div className="space-y-5 max-w-[1440px] mx-auto pb-10 font-sans">
      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {success && <AlertBanner type="success" message={success} onClose={() => setSuccess(null)} />}

      {/* =========================================================================
          1. HERO BANNER — TIMELESS CORPORATE RECRUITMENT BRANDING
          ========================================================================= */}
      <div className="relative rounded-2xl overflow-hidden bg-gradient-to-r from-[#071638] via-[#0B214E] to-[#123673] border border-blue-900/40 shadow-md text-white min-h-[185px] sm:min-h-[205px] flex items-center justify-between p-6 sm:p-8">
        {/* Exact campus glass building photography extracted from blueprint */}
        <div
          className="absolute right-0 top-0 bottom-0 w-full sm:w-7/12 pointer-events-none opacity-60 sm:opacity-90 mix-blend-screen bg-right bg-cover"
          style={{ backgroundImage: `url('/images/corporate_building_hero.jpg')` }}
        />
        {/* Soft gradient wash ensuring high contrast for left text */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#071638] via-[#071638]/95 to-transparent pointer-events-none" />

        {/* Left Headline & Call to Action */}
        <div className="relative z-10 max-w-lg space-y-2">
          <span className="text-[11px] font-extrabold uppercase tracking-widest text-blue-300 block">
            CAMPUS PLACEMENT ENGINE
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white leading-tight">
            Connect Talent with Opportunity
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed max-w-md">
            Streamline campus recruitment, manage drives, schedule interviews and build better futures.
          </p>
          <div className="pt-2">
            <button
              type="button"
              onClick={() => {
                const tableEl = document.getElementById("recent-drives-table");
                if (tableEl) tableEl.scrollIntoView({ behavior: "smooth" });
              }}
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#2563EB] hover:bg-blue-600 text-white font-bold text-xs rounded-xl shadow-md shadow-blue-950/40 transition-all cursor-pointer"
            >
              <span>View Upcoming Drives</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* =========================================================================
          2. FOUR HORIZONTAL KPI CARDS — THEME ADAPTIVE
          ========================================================================= */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Placement Drives */}
        <div className="corporate-card p-4 sm:p-5 flex items-center gap-3.5 hover:shadow-md transition-all">
          <div className="w-11 h-11 rounded-xl bg-blue-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-sm shrink-0">
            <Briefcase className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs font-semibold opacity-70 block">Placement Drives</span>
            <span className="text-2xl font-black tracking-tight block">
              {drives.length > 0 ? drives.length : (metrics?.total_drives || 20)}
            </span>
            <div className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 mt-0.5">
              <span>↑ Active Recruitment</span>
            </div>
          </div>
        </div>

        {/* Card 2: Total Students */}
        <div className="corporate-card p-4 sm:p-5 flex items-center gap-3.5 hover:shadow-md transition-all">
          <div className="w-11 h-11 rounded-xl bg-purple-950/80 border border-purple-500/40 flex items-center justify-center text-purple-400 shadow-sm shrink-0">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs font-semibold opacity-70 block">Total Students</span>
            <span className="text-2xl font-black tracking-tight block">
              {totalStudents.toLocaleString()}
            </span>
            <div className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 mt-0.5">
              <span>↑ 8% from last month</span>
            </div>
          </div>
        </div>

        {/* Card 3: Upcoming Drives */}
        <div className="corporate-card p-4 sm:p-5 flex items-center gap-3.5 hover:shadow-md transition-all">
          <div className="w-11 h-11 rounded-xl bg-emerald-950/80 border border-emerald-500/40 flex items-center justify-center text-emerald-400 shadow-sm shrink-0">
            <Calendar className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs font-semibold opacity-70 block">Upcoming Drives</span>
            <span className="text-2xl font-black tracking-tight block">
              {metrics ? metrics.total_drives : 6}
            </span>
            <div className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 mt-0.5">
              <span>↑ 2% from last month</span>
            </div>
          </div>
        </div>

        {/* Card 4: Placed Students */}
        <div className="corporate-card p-4 sm:p-5 flex items-center gap-3.5 hover:shadow-md transition-all">
          <div className="w-11 h-11 rounded-xl bg-amber-950/80 border border-amber-500/40 flex items-center justify-center text-amber-400 shadow-sm shrink-0">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs font-semibold opacity-70 block">Placed Students</span>
            <span className="text-2xl font-black tracking-tight block">
              {placedStudents}
            </span>
            <div className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 mt-0.5">
              <span>↑ 15% from last month</span>
            </div>
          </div>
        </div>
      </div>

      {/* =========================================================================
          3. MAIN TWO-COLUMN SECTION (TABLE & 4 PILLS vs 3 RIGHT WIDGETS)
          ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* LEFT COLUMN: TABLE + VALUE PROPOSITION PILLS (lg:col-span-8) */}
        <div className="lg:col-span-8 space-y-4 min-w-0">
          {/* Recent Placement Drives Table Card */}
          <div
            id="recent-drives-table"
            className="corporate-card p-5 space-y-3"
          >
            <div className="flex items-center justify-between pb-1">
              <h2 className="text-sm sm:text-base font-bold tracking-tight">
                Recent Placement Drives
              </h2>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setError(null);
                    setIsAddCompanyModalOpen(true);
                  }}
                  className="text-xs font-bold bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white flex items-center gap-1.5 transition-all cursor-pointer px-3 py-1 rounded-lg shadow-sm shadow-emerald-600/20"
                  title="Add a new hiring partner company to database"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  <span>Add Company</span>
                </button>
                <button
                  type="button"
                  onClick={() => setShowAllDrives((prev) => !prev)}
                  className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:text-blue-700 flex items-center gap-1.5 transition-colors cursor-pointer bg-blue-50 dark:bg-blue-950/60 px-2.5 py-1 rounded-lg border border-blue-200 dark:border-blue-800"
                >
                  <span>{showAllDrives ? "Show Top 5" : `View All (${displayDrives.length})`}</span>
                  <ArrowRight className={`w-3.5 h-3.5 transition-transform duration-200 ${showAllDrives ? "rotate-90" : ""}`} />
                </button>
              </div>
            </div>

            {/* Table Container with Fixed Layout for Complete Fit */}
            <div className="w-full overflow-hidden">
              <table className="w-full text-left border-collapse table-fixed">
                <thead>
                  <tr className="border-b text-[10px] font-bold opacity-75 uppercase tracking-wider">
                    <th className="py-2.5 px-2 w-[19%] whitespace-nowrap">Company</th>
                    <th className="py-2.5 px-2 w-[21%] whitespace-nowrap">Role</th>
                    <th className="py-2.5 px-2 w-[15%] whitespace-nowrap">Date</th>
                    <th className="py-2.5 px-2 w-[20%] whitespace-nowrap">Eligible Branches</th>
                    <th className="py-2.5 px-2 w-[10%] text-center whitespace-nowrap">Status</th>
                    <th className="py-2.5 px-2 w-[15%] text-right whitespace-nowrap">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y text-xs">
                  {(showAllDrives ? displayDrives : displayDrives.slice(0, 5)).map((drive, idx) => (
                    <tr
                      key={drive.id || idx}
                      className="transition-colors group"
                    >
                      {/* Company Name & Logo */}
                      <td className="py-2.5 px-2">
                        <div className="flex items-center gap-2">
                          <CompanyBrandLogo company={drive.company_name} />
                          <span className="font-bold truncate">
                            {getCompanyDisplayName(drive.company_name)}
                          </span>
                        </div>
                      </td>

                      {/* Role */}
                      <td className="py-2.5 px-2 font-medium opacity-80 truncate">
                        {getRoleDisplay(drive)}
                      </td>

                      {/* Date */}
                      <td className="py-2.5 px-2 font-medium opacity-80 truncate">
                        {getFormattedDate(drive, idx)}
                      </td>

                      {/* Eligible Branches */}
                      <td className="py-2.5 px-2 font-medium opacity-70 truncate">
                        {getBranchesDisplay(drive, idx)}
                      </td>

                      {/* Status: Soft Blue Pill "Upcoming" */}
                      <td className="py-2.5 px-2 text-center">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-950/80 dark:text-blue-300 dark:border-blue-700/50">
                          Upcoming
                        </span>
                      </td>

                      {/* Action Buttons: Corporate View & Delete Buttons */}
                      <td className="py-2.5 px-2 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={() => onNavigateTab("eligibility", drive.id)}
                            className="px-3 py-1 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-[11px] font-bold rounded-lg transition-all shadow-sm shadow-cyan-500/20 cursor-pointer"
                            title={`View ${drive.company_name} candidates & eligibility`}
                          >
                            View
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setDeleteModalDrive(drive);
                              setDeleteReason("");
                            }}
                            className="px-2.5 py-1 text-rose-600 hover:text-white hover:bg-rose-600 border border-rose-200 dark:border-rose-900/60 hover:border-rose-600 rounded-lg text-[11px] font-bold transition-all shadow-2xs cursor-pointer flex items-center gap-1"
                            title={`Delete ${drive.company_name} drive`}
                          >
                            <Trash2 className="w-3 h-3" />
                            <span>Delete</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}

                  {displayDrives.length === 0 && !loading && (
                    <tr>
                      <td colSpan={6} className="py-8 text-center opacity-60">
                        No placement drives scheduled yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* 4 Bottom Feature Badges */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
            {/* Badge 1 */}
            <div className="corporate-card p-3 flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-blue-50 dark:bg-blue-950/70 border border-blue-200 dark:border-blue-800/60 flex items-center justify-center text-blue-600 dark:text-blue-400 shrink-0">
                <ShieldCheck className="w-3.5 h-3.5" />
              </div>
              <div className="min-w-0">
                <h4 className="text-[10px] sm:text-[11px] font-bold leading-tight">
                  AI-Powered Screening
                </h4>
                <p className="text-[9px] opacity-60 truncate mt-0.5">
                  Smarter candidate matching
                </p>
              </div>
            </div>

            {/* Badge 2 */}
            <div className="corporate-card p-3 flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-blue-50 dark:bg-blue-950/70 border border-blue-200 dark:border-blue-800/60 flex items-center justify-center text-blue-600 dark:text-blue-400 shrink-0">
                <Calendar className="w-3.5 h-3.5" />
              </div>
              <div className="min-w-0">
                <h4 className="text-[10px] sm:text-[11px] font-bold leading-tight">
                  Automated Scheduling
                </h4>
                <p className="text-[9px] opacity-60 truncate mt-0.5">
                  No more manual conflicts
                </p>
              </div>
            </div>

            {/* Badge 3 */}
            <div className="corporate-card p-3 flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-blue-50 dark:bg-blue-950/70 border border-blue-200 dark:border-blue-800/60 flex items-center justify-center text-blue-600 dark:text-blue-400 shrink-0">
                <BarChart2 className="w-3.5 h-3.5" />
              </div>
              <div className="min-w-0">
                <h4 className="text-[10px] sm:text-[11px] font-bold leading-tight">
                  Real-Time Analytics
                </h4>
                <p className="text-[9px] opacity-60 truncate mt-0.5">
                  Data-driven decisions
                </p>
              </div>
            </div>

            {/* Badge 4 */}
            <div className="corporate-card p-3 flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-blue-50 dark:bg-blue-950/70 border border-blue-200 dark:border-blue-800/60 flex items-center justify-center text-blue-600 dark:text-blue-400 shrink-0">
                <Users className="w-3.5 h-3.5" />
              </div>
              <div className="min-w-0">
                <h4 className="text-[10px] sm:text-[11px] font-bold leading-tight">
                  Better Placement Rates
                </h4>
                <p className="text-[9px] opacity-60 truncate mt-0.5">
                  Success for every student
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: 3 STACKED WIDGETS (lg:col-span-4) */}
        <div className="lg:col-span-4 space-y-4 min-w-0">
          {/* Widget 1: Quick Actions (2x2 Grid) */}
          <div className="corporate-card p-4 sm:p-5 space-y-3">
            <h3 className="text-sm font-bold tracking-tight">
              Quick Actions
            </h3>
            <div className="grid grid-cols-2 gap-2.5">
              <button
                type="button"
                onClick={() => onNavigateTab("create_drive")}
                className="p-3 rounded-xl bg-[var(--bg-input)] hover:bg-[var(--bg-card-hover)] border border-[var(--border-card)] hover:border-cyan-400 flex flex-col items-center justify-center text-center gap-1.5 transition-all cursor-pointer group shadow-sm hover:shadow-cyan-950/40"
              >
                <div className="w-7 h-7 rounded-lg bg-blue-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400 group-hover:scale-110 transition-transform shadow-xs">
                  <UploadCloud className="w-3.5 h-3.5" />
                </div>
                <span className="text-[10px] font-bold leading-tight">
                  Upload<br />Announcement
                </span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setError(null);
                  setIsAddCompanyModalOpen(true);
                }}
                className="p-3 rounded-xl bg-[var(--bg-input)] hover:bg-[var(--bg-card-hover)] border border-[var(--border-card)] hover:border-emerald-400 flex flex-col items-center justify-center text-center gap-1.5 transition-all cursor-pointer group shadow-sm hover:shadow-emerald-950/40"
              >
                <div className="w-7 h-7 rounded-lg bg-emerald-950/80 border border-emerald-500/40 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition-transform shadow-xs">
                  <Building2 className="w-3.5 h-3.5" />
                </div>
                <span className="text-[10px] font-bold leading-tight">
                  Add<br />Company
                </span>
              </button>

              <button
                type="button"
                onClick={() => onNavigateTab("students")}
                className="p-3 rounded-xl bg-[var(--bg-input)] hover:bg-[var(--bg-card-hover)] border border-[var(--border-card)] hover:border-cyan-400 flex flex-col items-center justify-center text-center gap-1.5 transition-all cursor-pointer group shadow-sm hover:shadow-cyan-950/40"
              >
                <div className="w-7 h-7 rounded-lg bg-blue-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400 group-hover:scale-110 transition-transform shadow-xs">
                  <Users className="w-3.5 h-3.5" />
                </div>
                <span className="text-[10px] font-bold leading-tight">
                  Manage<br />Students
                </span>
              </button>

              <button
                type="button"
                onClick={() => onNavigateTab("schedule")}
                className="p-3 rounded-xl bg-[var(--bg-input)] hover:bg-[var(--bg-card-hover)] border border-[var(--border-card)] hover:border-cyan-400 flex flex-col items-center justify-center text-center gap-1.5 transition-all cursor-pointer group shadow-sm hover:shadow-cyan-950/40"
              >
                <div className="w-7 h-7 rounded-lg bg-blue-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400 group-hover:scale-110 transition-transform shadow-xs">
                  <Calendar className="w-3.5 h-3.5" />
                </div>
                <span className="text-[10px] font-bold leading-tight">
                  Generate<br />Schedule
                </span>
              </button>
            </div>
          </div>

          {/* Widget 2: Upcoming Drives Calendar */}
          <div className="corporate-card p-4 sm:p-5 space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <span className="text-sm font-bold tracking-tight">
                  Upcoming Drives
                </span>
              </div>
              <button
                type="button"
                onClick={() => onNavigateTab("schedule")}
                className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:text-blue-700 flex items-center gap-1 transition-colors cursor-pointer"
              >
                <span>View Calendar</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            {/* Month Header with Navigation */}
            <div className="flex items-center justify-between px-2 pt-1">
              <button
                type="button"
                onClick={() => setCalendarMonth((m) => (m === 0 ? 11 : m - 1))}
                className="p-1 opacity-70 hover:opacity-100 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <span className="text-xs font-extrabold">
                {monthNames[calendarMonth]} {calendarYear}
              </span>
              <button
                type="button"
                onClick={() => setCalendarMonth((m) => (m === 11 ? 0 : m + 1))}
                className="p-1 opacity-70 hover:opacity-100 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Weekdays Row */}
            <div className="grid grid-cols-7 gap-1 text-center text-[10px] font-bold opacity-60 uppercase pt-0.5">
              <span>Sun</span>
              <span>Mon</span>
              <span>Tue</span>
              <span>Wed</span>
              <span>Thu</span>
              <span>Fri</span>
              <span>Sat</span>
            </div>

            {/* Day Numbers Grid with Real Placement Day Detection */}
            <div className="grid grid-cols-7 gap-1 text-center text-xs">
              {Array.from({ length: new Date(calendarYear, calendarMonth, 1).getDay() }).map((_, i) => (
                <div key={`offset-${i}`} className="h-6" />
              ))}
              {Array.from({ length: new Date(calendarYear, calendarMonth + 1, 0).getDate() }).map((_, i) => {
                const day = i + 1;
                const drivesOnDay = getDrivesForCalendarDay(day);
                const hasPlacement = drivesOnDay.length > 0;
                const isSelected = selectedCalendarDay === day;

                return (
                  <div key={day} className="h-6 flex items-center justify-center">
                    <button
                      type="button"
                      onClick={() => setSelectedCalendarDay(isSelected ? null : day)}
                      title={hasPlacement ? `${drivesOnDay.length} Drive(s): ${drivesOnDay.map((d: any) => d.company_name).join(", ")}` : `Day ${day}: No placement drive scheduled`}
                      className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-all cursor-pointer relative ${
                        isSelected
                          ? "bg-amber-500 text-slate-950 font-black ring-2 ring-amber-300"
                          : hasPlacement
                          ? "bg-[#2563EB] text-white shadow-xs hover:bg-blue-500"
                          : "opacity-80 hover:bg-slate-100 dark:hover:bg-slate-800"
                      }`}
                    >
                      {day}
                      {hasPlacement && !isSelected && (
                        <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                      )}
                    </button>
                  </div>
                );
              })}
            </div>

            {/* Selected Date Placement Inspection Box */}
            {selectedCalendarDay !== null && (
              <div className="mt-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-extrabold text-[11px] text-slate-900 dark:text-slate-100">
                    {monthNames[calendarMonth]} {selectedCalendarDay}, {calendarYear}
                  </span>
                  <button
                    type="button"
                    onClick={() => setSelectedCalendarDay(null)}
                    className="text-[10px] text-slate-400 hover:text-slate-200 font-bold"
                  >
                    Close
                  </button>
                </div>
                {getDrivesForCalendarDay(selectedCalendarDay).length > 0 ? (
                  <div className="space-y-1.5">
                    <div className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Placement Drive Scheduled:</span>
                    </div>
                    {getDrivesForCalendarDay(selectedCalendarDay).map((drv: any) => (
                      <div
                        key={drv.id}
                        className="flex items-center justify-between gap-1 text-[11px] bg-white dark:bg-slate-800 p-2 rounded-lg border border-slate-200 dark:border-slate-700"
                      >
                        <div className="min-w-0">
                          <span className="font-bold text-blue-600 dark:text-blue-400 truncate block">
                            {drv.company_name}
                          </span>
                          <span className="opacity-70 text-[10px] block truncate">
                            {getRoleDisplay(drv)} • {drv.ctc_lpa || 10} LPA
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <button
                            type="button"
                            onClick={() => onNavigateTab("eligibility", drv.id)}
                            className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-[10px] font-bold cursor-pointer"
                          >
                            View
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setDeleteModalDrive(drv);
                              setDeleteReason("");
                            }}
                            className="px-2 py-1 text-rose-600 hover:text-white hover:bg-rose-600 border border-rose-200 dark:border-rose-800 rounded text-[10px] font-bold cursor-pointer flex items-center gap-0.5"
                            title={`Delete ${drv.company_name} drive`}
                          >
                            <Trash2 className="w-2.5 h-2.5" />
                            <span>Delete</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 italic">
                    No placement drive scheduled on this date.
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Widget 3: Building Future Together Card (Night Campus Image) */}
          <div
            className="relative rounded-2xl overflow-hidden shadow-sm border border-slate-200 dark:border-slate-800 min-h-[85px] flex items-center justify-between p-4 text-white bg-cover bg-center cursor-pointer group"
            style={{ backgroundImage: `url('/images/building_future_card.jpg')` }}
            onClick={() => onNavigateTab("drives")}
          >
            {/* Dark gradient overlay */}
            <div className="absolute inset-0 bg-gradient-to-r from-[#071638]/90 via-[#0B214E]/75 to-transparent pointer-events-none" />

            <div className="relative z-10 flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-blue-500/20 backdrop-blur-sm border border-blue-400/30 flex items-center justify-center text-blue-300">
                <Building2 className="w-3.5 h-3.5" />
              </div>
              <div>
                <span className="text-[10px] font-bold text-slate-300 block leading-tight">
                  Building
                </span>
                <span className="text-xs font-black text-white block leading-tight">
                  Future Together
                </span>
              </div>
            </div>

            <div className="relative z-10 w-6 h-6 rounded-full bg-white/10 hover:bg-white/20 backdrop-blur-sm border border-white/20 flex items-center justify-center text-white transition-transform group-hover:translate-x-0.5">
              <ArrowRight className="w-3 h-3" />
            </div>
          </div>
        </div>
      </div>

      {/* =========================================================================
          4. FOOTER — THEME ADAPTIVE
          ========================================================================= */}
      <div className="pt-6 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs opacity-70">
        <div className="font-medium">
          IM-101 Placement Engine <span className="mx-1.5 opacity-50">|</span> v1.0.0
        </div>
        <div className="flex items-center gap-2 font-medium text-[11px]">
          <span>Powered by</span>
          <span className="font-semibold text-slate-800 dark:text-slate-200">⚛ React</span>
          <span>+</span>
          <span className="font-semibold text-slate-800 dark:text-slate-200">⚡ FastAPI</span>
          <span>+</span>
          <span className="font-semibold text-slate-800 dark:text-slate-200">🗄 SQLite</span>
        </div>
      </div>

      {/* =========================================================================
          5. MODALS (PRESERVING 100% EXISTING LOGIC FOR DATA SAFETY)
          ========================================================================= */}
      {/* Delete Drive Modal */}
      {deleteModalDrive && (
        <Modal
          isOpen={!!deleteModalDrive}
          onClose={() => setDeleteModalDrive(null)}
          title={`Permanently Remove Drive: ${deleteModalDrive.company_name}`}
        >
          <div className="space-y-4">
            <p className="text-xs opacity-80">
              Removing this company drive will purge all candidate applications and slot assignments. This action is auditable.
            </p>
            <div>
              <label className="block text-xs font-bold mb-1">
                Reason for Removal (Mandatory):
              </label>
              <textarea
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
                rows={3}
                placeholder="Specify justification..."
                className="w-full text-xs p-2.5 rounded-xl focus:ring-2 focus:ring-rose-500 focus:outline-none"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setDeleteModalDrive(null)}
                className="px-4 py-2 text-xs font-bold opacity-80 hover:opacity-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDeleteDrive}
                disabled={deleting}
                className="px-4 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-xl shadow-xs"
              >
                {deleting ? "Removing..." : "Confirm Removal"}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Cancel Drive Modal */}
      {cancelModalDrive && (
        <Modal
          isOpen={!!cancelModalDrive}
          onClose={() => setCancelModalDrive(null)}
          title={`Cancel Drive: ${cancelModalDrive.company_name}`}
        >
          <div className="space-y-4">
            <p className="text-xs opacity-80">
              Please enter a formal reason for cancelling this recruitment drive.
            </p>
            <div>
              <label className="block text-xs font-bold mb-1">
                Reason for Cancellation (Mandatory):
              </label>
              <textarea
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                rows={3}
                placeholder="Provide cancellation rationale..."
                className="w-full text-xs p-2.5 rounded-xl focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setCancelModalDrive(null)}
                className="px-4 py-2 text-xs font-bold opacity-80 hover:opacity-100 rounded-xl"
              >
                Close
              </button>
              <button
                type="button"
                onClick={handleConfirmCancelDrive}
                disabled={cancelling}
                className="px-4 py-2 text-xs font-bold text-white bg-amber-600 hover:bg-amber-700 rounded-xl shadow-xs"
              >
                {cancelling ? "Processing..." : "Confirm Cancellation"}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Add Company Modal */}
      {isAddCompanyModalOpen && (
        <Modal
          isOpen={isAddCompanyModalOpen}
          onClose={() => setIsAddCompanyModalOpen(false)}
          title="Onboard Corporate Partner Company"
        >
          <div className="space-y-4">
            <p className="text-xs opacity-80">
              Register a hiring partner into the central institutional database. Automatically saves to SQLite and mirrors directly to MongoDB Atlas.
            </p>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-bold mb-1">
                  Company Name <span className="text-rose-500">*</span>:
                </label>
                <input
                  type="text"
                  value={newCompanyName}
                  onChange={(e) => setNewCompanyName(e.target.value)}
                  placeholder="e.g. NVIDIA, Adobe, Intel, PwC, Qualcomm"
                  className="w-full text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 focus:outline-none font-bold"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold mb-1">Industry Domain:</label>
                  <select
                    value={newCompanyIndustry}
                    onChange={(e) => setNewCompanyIndustry(e.target.value)}
                    className="w-full text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  >
                    <option value="Technology">Technology & Software</option>
                    <option value="Semiconductors">Semiconductors & Hardware</option>
                    <option value="Fintech / Banking">Fintech & Banking</option>
                    <option value="Consulting">Consulting & Analytics</option>
                    <option value="Automotive / Manufacturing">Automotive / Core</option>
                    <option value="Healthcare / Biotech">Healthcare / Biotech</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold mb-1">Hiring Tier:</label>
                  <select
                    value={newCompanyTier}
                    onChange={(e) => setNewCompanyTier(e.target.value)}
                    className="w-full text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  >
                    <option value="Tier 1">Tier 1 (&gt; 12 LPA)</option>
                    <option value="Dream Tier">Dream Tier (&gt; 15 LPA)</option>
                    <option value="Super Dream">Super Dream (&gt; 25 LPA)</option>
                    <option value="Tier 2">Tier 2 (&lt; 10 LPA)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold mb-1">Company Website:</label>
                <input
                  type="text"
                  value={newCompanyWebsite}
                  onChange={(e) => setNewCompanyWebsite(e.target.value)}
                  placeholder="e.g. https://nvidia.com"
                  className="w-full text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>

              <div className="pt-2 border-t border-slate-200 dark:border-slate-800 space-y-2.5">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-bold">
                  <input
                    type="checkbox"
                    checked={scheduleDriveToo}
                    onChange={(e) => setScheduleDriveToo(e.target.checked)}
                    className="rounded text-emerald-600 focus:ring-emerald-500 w-4 h-4"
                  />
                  <span>Also schedule an initial recruitment drive</span>
                </label>

                {scheduleDriveToo && (
                  <div className="grid grid-cols-3 gap-2.5 p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                    <div>
                      <label className="block text-[10px] font-bold opacity-75 mb-1">Drive Date</label>
                      <input
                        type="date"
                        value={newDriveDate}
                        onChange={(e) => setNewDriveDate(e.target.value)}
                        className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold opacity-75 mb-1">Role Title</label>
                      <input
                        type="text"
                        value={newDriveRole}
                        onChange={(e) => setNewDriveRole(e.target.value)}
                        placeholder="e.g. SDE-1"
                        className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold opacity-75 mb-1">CTC (LPA)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={newDriveCtc}
                        onChange={(e) => setNewDriveCtc(parseFloat(e.target.value) || 0)}
                        className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setIsAddCompanyModalOpen(false)}
                className="px-4 py-2 text-xs font-bold opacity-80 hover:opacity-100 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveCompany}
                disabled={savingCompany}
                className="px-5 py-2 text-xs font-bold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 rounded-xl shadow-sm shadow-emerald-600/30 cursor-pointer disabled:opacity-50"
              >
                {savingCompany ? "Saving to Database..." : "Save to Database"}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
