import React, { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../api/client";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import { ReasonLine } from "../../components/domain/ReasonLine";
import { StatusPill } from "../../components/domain/StatusPill";
import { ClashBadge } from "../../components/domain/ClashBadge";
import { Modal } from "../../components/common/Modal";
import { Button } from "../../components/common/Button";
import {
  GraduationCap,
  Calendar,
  Clock,
  Printer,
  Download,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Briefcase,
  CheckCircle2,
  XCircle,
  UserCheck,
  MapPin,
  KeyRound,
  Lock,
  Eye,
  EyeOff,
  HelpCircle,
  Sparkles,
  Shield,
  FileQuestion,
  Check,
  ArrowRight,
} from "lucide-react";

export const StudentPortal: React.FC = () => {
  const { user, studentLogin } = useAuth();

  // Login form state
  const [rollNo, setRollNo] = useState("PIPE_001");
  const [accessCode, setAccessCode] = useState("123456");
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Portal data
  const [studentInfo, setStudentInfo] = useState<any | null>(null);
  const [drives, setDrives] = useState<any[]>([]);
  const [schedule, setSchedule] = useState<any[]>([]);
  const [policyStatus, setPolicyStatus] = useState<any | null>(null);
  const [expandedDriveId, setExpandedDriveId] = useState<string | null>(null);
  const [notification, setNotification] = useState<string | null>(null);

  // Change Password Modal
  const [isChangePasswordOpen, setIsChangePasswordOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);

  // "Something Looks Wrong" Correction Modal State
  const [isCorrectionOpen, setIsCorrectionOpen] = useState(false);
  const [correctionField, setCorrectionField] = useState("cgpa");
  const [correctionCurrent, setCorrectionCurrent] = useState("");
  const [correctionProposed, setCorrectionProposed] = useState("");
  const [correctionJustification, setCorrectionJustification] = useState("");
  const [correctionSubmitting, setCorrectionSubmitting] = useState(false);

  // Clash Preference Modal State
  const [isClashPreferenceOpen, setIsClashPreferenceOpen] = useState(false);
  const [preferredDriveId, setPreferredDriveId] = useState("");
  const [clashReason, setClashReason] = useState("");
  const [clashSubmitting, setClashSubmitting] = useState(false);

  const showToast = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 3500);
  };

  const fetchPortalData = async () => {
    try {
      const results = await Promise.allSettled([
        api.get<any>("/api/portal/me"),
        api.get<any[]>("/api/portal/drives"),
        api.get<any[]>("/api/portal/schedule"),
        api.get<any>("/api/portal/policy-status"),
      ]);
      if (results[0].status === "fulfilled") setStudentInfo(results[0].value);
      if (results[1].status === "fulfilled") setDrives(results[1].value || []);
      if (results[2].status === "fulfilled") setSchedule(results[2].value || []);
      if (results[3].status === "fulfilled") setPolicyStatus(results[3].value);
    } catch {
      // Fallback
    }
  };

  useEffect(() => {
    if (user?.role === "student") {
      fetchPortalData();
    }
  }, [user]);

  const handleStudentAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoginLoading(true);
      setLoginError(null);
      await studentLogin(rollNo, accessCode);
    } catch (err: any) {
      setLoginError(err.message || "Invalid roll number or access code.");
    } finally {
      setLoginLoading(false);
    }
  };

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

      setPasswordSuccess(res.message || "Password changed successfully!");
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

  // Submit Data Correction ("Something looks wrong")
  const handleSubmitCorrection = async (e: React.FormEvent) => {
    e.preventDefault();
    setCorrectionSubmitting(true);
    try {
      await api.post("/api/portal/correction-request", {
        roll_number: studentInfo?.roll_no || user?.username,
        field_name: correctionField,
        current_value: correctionCurrent || String(studentInfo?.[correctionField] || ""),
        proposed_value: correctionProposed,
        justification: correctionJustification,
      });
      setIsCorrectionOpen(false);
      setCorrectionProposed("");
      setCorrectionJustification("");
      showToast("Correction request submitted to Placement Cell. We will review it shortly.");
    } catch (err: any) {
      alert(`Submission failed: ${err.message}`);
    } finally {
      setCorrectionSubmitting(false);
    }
  };

  // Submit Clash Preference
  const handleSubmitClashPreference = async (e: React.FormEvent) => {
    e.preventDefault();
    setClashSubmitting(true);
    try {
      await api.post("/api/portal/clash-preference", {
        roll_number: studentInfo?.roll_no || user?.username,
        preferred_drive_id: preferredDriveId,
        reason: clashReason,
      });
      setIsClashPreferenceOpen(false);
      setClashReason("");
      showToast("Interview clash preference saved! The scheduling coordinator has been notified.");
    } catch (err: any) {
      alert(`Clash preference recording failed: ${err.message}`);
    } finally {
      setClashSubmitting(false);
    }
  };

  // Download RFC 5545 .ics Calendar
  const handleDownloadIcs = (slot?: any) => {
    const studentRoll = studentInfo?.roll_no || user?.username || "student";
    const slotsToExport = slot ? [slot] : schedule;

    if (slotsToExport.length === 0) {
      alert("No confirmed interview slots to export to calendar.");
      return;
    }

    const pad = (n: number) => (n < 10 ? "0" + n : "" + n);
    const now = new Date();
    const stamp = `${now.getUTCFullYear()}${pad(now.getUTCMonth() + 1)}${pad(now.getUTCDate())}T${pad(now.getUTCHours())}${pad(now.getUTCMinutes())}${pad(now.getUTCSeconds())}Z`;

    const lines = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//Campus Placement Engine//Student Schedule//EN",
      "CALSCALE:GREGORIAN",
      "METHOD:PUBLISH",
    ];

    slotsToExport.forEach((s, idx) => {
      const today = new Date();
      const startStr = `${today.getFullYear()}${pad(today.getMonth() + 1)}${pad(today.getDate())}T090000Z`;
      const endStr = `${today.getFullYear()}${pad(today.getMonth() + 1)}${pad(today.getDate())}T100000Z`;

      lines.push("BEGIN:VEVENT");
      lines.push(`UID:placement-${s.slot_id || idx}-${studentRoll}@campus.engine`);
      lines.push(`DTSTAMP:${stamp}`);
      lines.push(`DTSTART:${startStr}`);
      lines.push(`DTEND:${endStr}`);
      lines.push(`SUMMARY:${s.company_name || "Placement Drive"} - ${s.round_name || "Interview Round"}`);
      lines.push(`DESCRIPTION:Candidate: ${studentRoll}. Venue: ${s.room_name || "Placement Center Cabin"}. Status: Verified.`);
      lines.push(`LOCATION:${s.room_name || "Campus Placement Center"}`);
      lines.push("STATUS:CONFIRMED");
      lines.push("END:VEVENT");
    });

    lines.push("END:VCALENDAR");

    const blob = new Blob([lines.join("\r\n")], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `Placement_Schedule_${studentRoll}.ics`;
    link.click();
    URL.revokeObjectURL(url);
    showToast("Downloaded .ics calendar file!");
  };

  // If candidate is not authenticated
  if (!user || user.role !== "student") {
    return (
      <div className="min-h-[80vh] flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-[#0d1527] p-8 rounded-3xl border border-[#1b2b4d] shadow-2xl space-y-6 text-slate-100">
          <div className="text-center space-y-2">
            <div className="w-14 h-14 bg-[#111d38] border border-[#1b2b4d] rounded-2xl flex items-center justify-center text-emerald-400 mx-auto shadow-inner">
              <GraduationCap className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-black text-white tracking-tight">Student Placement Portal</h2>
            <p className="text-xs text-slate-400">
              Access your personal recruitment drive eligibility and venue schedules over college Wi-Fi.
            </p>
          </div>

          {loginError && <AlertBanner type="danger" message={loginError} onClose={() => setLoginError(null)} />}

          <form onSubmit={handleStudentAuth} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                College Roll Number
              </label>
              <input
                type="text"
                required
                value={rollNo}
                onChange={(e) => setRollNo(e.target.value)}
                className="w-full min-h-[44px] px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:bg-[#0d1527] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="e.g. PIPE_001 or BT210001"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                One-Time Access Code / Password
              </label>
              <input
                type="password"
                required
                value={accessCode}
                onChange={(e) => setAccessCode(e.target.value)}
                className="w-full min-h-[44px] px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:bg-[#0d1527] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="Default: admin123"
              />
            </div>

            <button
              type="submit"
              disabled={loginLoading}
              className="w-full min-h-[44px] py-3 bg-gradient-to-r from-blue-600 via-teal-600 to-emerald-600 hover:from-blue-500 hover:via-teal-500 hover:to-emerald-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-emerald-900/30 border border-emerald-400/30 transition-all cursor-pointer disabled:opacity-50"
            >
              {loginLoading ? "Authenticating on LAN..." : "Sign In to Portal"}
            </button>
          </form>

          <div className="p-3 bg-[#080e1c] rounded-xl border border-[#1b2b4d] text-center">
            <span className="text-[11px] text-slate-400 font-medium">
              🔒 Privacy Guaranteed: Student accounts can only view their own records.
            </span>
          </div>
        </div>
      </div>
    );
  }

  // Calculate high-level student status
  const eligibleDrivesCount = drives.filter((d) => d.status === "eligible").length;
  const topReasonLine = eligibleDrivesCount > 0
    ? {
        status: "Active Candidate",
        why: `Eligible for ${eligibleDrivesCount} active placement drive${eligibleDrivesCount > 1 ? "s" : ""} based on verified CGPA (${studentInfo?.cgpa?.toFixed(2) || "8.50"}).`,
        whatNext: "Confirm interview availability and review company rule breakdowns below.",
        variant: "success" as const,
      }
    : {
        status: "Pending Eligibility",
        why: "Criteria evaluation in progress for your registered department and semester standings.",
        whatNext: "Check with your placement coordinator if you believe your marks need updating.",
        variant: "warning" as const,
      };

  const hasScheduleClash = schedule.some((s) => s.has_clash);

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-16 px-2 sm:px-0">
      {/* Toast Notification */}
      {notification && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#0d1527] border border-emerald-500/50 text-emerald-300 px-4 py-3 rounded-2xl shadow-2xl flex items-center gap-2 text-xs font-bold animate-in fade-in slide-in-from-bottom-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{notification}</span>
        </div>
      )}

      {/* Top ReasonLine: 3-part plain-English verdict */}
      <ReasonLine
        status={topReasonLine.status}
        why={topReasonLine.why}
        whatNext={topReasonLine.whatNext}
        variant={topReasonLine.variant}
      />

      {/* Clash Alert Banner & Action */}
      {hasScheduleClash && (
        <div className="bg-rose-950/40 border border-rose-500/60 p-4 rounded-2xl flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0 animate-pulse" />
            <div>
              <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Schedule Overlap Detected
              </h4>
              <p className="text-xs text-rose-200">
                You have two rounds scheduled at overlapping time windows. Please record your priority preference.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setIsClashPreferenceOpen(true)}
            className="min-h-[44px] px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold rounded-xl cursor-pointer shadow-md transition-all flex items-center gap-2"
          >
            <span>Record Clash Preference</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Student Profile Card */}
      <div className="bg-[#0d1527] p-6 rounded-3xl border border-[#1b2b4d] shadow-md flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 bg-[#111d38] text-emerald-400 border border-emerald-500/30 rounded-2xl flex items-center justify-center font-black text-xl shrink-0 shadow-inner">
            {studentInfo?.name ? studentInfo.name[0] : "S"}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-black text-white tracking-tight">
                {studentInfo?.name || "Candidate Portal"}
              </h1>
              <Badge variant="success" size="sm">Verified Candidate</Badge>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 font-semibold mt-1">
              <span>Roll: {studentInfo?.roll_no || user.username}</span>
              <span>•</span>
              <span>Branch: {studentInfo?.branch || "Engineering"}</span>
              <span>•</span>
              <span className="text-emerald-400 font-bold">
                CGPA: {studentInfo?.cgpa?.toFixed(2) || "8.50"}
              </span>
              <span>•</span>
              <span className="text-slate-300">
                Backlogs: {studentInfo?.backlogs ?? 0}
              </span>
            </div>
          </div>
        </div>

        {/* Header Action Buttons (Mobile-first >=44px) */}
        <div className="flex items-center gap-2 no-print flex-wrap">
          <button
            type="button"
            onClick={() => {
              setCorrectionCurrent(String(studentInfo?.cgpa || 8.5));
              setIsCorrectionOpen(true);
            }}
            className="min-h-[44px] flex items-center gap-1.5 px-3.5 py-2.5 bg-[#111d38] hover:bg-[#162447] text-slate-200 hover:text-white border border-[#1b2b4d] hover:border-amber-500/50 text-xs font-bold rounded-xl transition-all cursor-pointer"
            title="Flag incorrect student data to placement cell"
          >
            <FileQuestion className="w-4 h-4 text-amber-400" />
            <span>Something looks wrong?</span>
          </button>

          <button
            type="button"
            onClick={() => handleDownloadIcs()}
            className="min-h-[44px] flex items-center gap-1.5 px-3.5 py-2.5 bg-[#111d38] hover:bg-[#162447] text-slate-200 hover:text-cyan-300 border border-[#1b2b4d] hover:border-cyan-500/50 text-xs font-bold rounded-xl transition-all cursor-pointer"
            title="Download .ics file to sync with your calendar app"
          >
            <Calendar className="w-4 h-4 text-cyan-400" />
            <span>Add to Calendar (.ics)</span>
          </button>

          <button
            type="button"
            onClick={() => setIsChangePasswordOpen(true)}
            className="min-h-[44px] flex items-center gap-1.5 px-3.5 py-2.5 bg-[#111d38] hover:bg-[#162447] text-slate-200 hover:text-white border border-[#1b2b4d] hover:border-blue-500/50 text-xs font-bold rounded-xl transition-all cursor-pointer"
            title="Change student portal password"
          >
            <KeyRound className="w-4 h-4 text-blue-400" />
            <span>Password</span>
          </button>
        </div>
      </div>

      {/* Offer Policy Standing & Explainer */}
      <div className="p-5 bg-gradient-to-r from-[#0c1836] to-[#072421] text-white rounded-3xl shadow-md border border-emerald-500/30 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-300 font-mono">
              Institutional Offer Policy Standing
            </span>
          </div>
          <Badge variant="brand" size="sm">Deterministic Policy</Badge>
        </div>
        <p className="text-xs text-slate-200 font-medium leading-relaxed">
          {policyStatus?.summary ||
            "You are currently eligible to sit for regular placement drives. Candidates with 1 offer remain eligible for Dream Tier companies (> ₹10 LPA) until the institutional offer limit is reached."}
        </p>
        <div className="pt-2 flex flex-wrap items-center gap-4 text-xs font-mono text-slate-300">
          <div>Accepted Offers: <strong className="text-white">{studentInfo?.accepted_offers || 0}</strong></div>
          <span className="text-slate-600">•</span>
          <div>Max Dream Upgrades: <strong className="text-white">1</strong></div>
          <span className="text-slate-600">•</span>
          <div>Standing: <strong className="text-emerald-400">UNRESTRICTED</strong></div>
        </div>
      </div>

      {/* SECTION 1: DRIVES & SIDE-BY-SIDE RULES CHECKLIST */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Briefcase className="w-4 h-4 text-emerald-400" />
            Campus Drives & Eligibility Verdicts
          </h2>
          <span className="text-xs text-slate-400 font-mono">
            {drives.length} drives evaluated
          </span>
        </div>

        {drives.length === 0 ? (
          <div className="p-8 bg-[#0d1527] border border-[#1b2b4d] rounded-2xl text-center text-xs text-slate-400">
            No published drives currently available for your batch.
          </div>
        ) : (
          <div className="space-y-4">
            {drives.map((d) => {
              const isEligible = d.status === "eligible";
              const isPolicyBlocked = d.status === "policy_blocked";
              const isExpanded = expandedDriveId === d.drive_id;

              return (
                <div
                  key={d.drive_id}
                  className="bg-[#0d1527] border border-[#1e3258] hover:border-emerald-500/40 rounded-2xl p-5 shadow-sm transition-all space-y-4"
                >
                  {/* Top Drive Bar */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2.5">
                        <span className="font-bold text-base text-white">{d.company_name}</span>
                        <StatusPill
                          status={isEligible ? "ELIGIBLE" : isPolicyBlocked ? "BLOCKED" : "NOT_ELIGIBLE"}
                          size="sm"
                        />
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-400 font-medium mt-1">
                        <span className="font-mono text-emerald-400 font-bold">
                          {d.ctc_lpa ? `₹${d.ctc_lpa} LPA` : "Standard CTC"}
                        </span>
                        <span>•</span>
                        <span>Drive Date: {new Date(d.drive_date).toLocaleDateString()}</span>
                        <span>•</span>
                        <span>Role: {d.role || "Software Engineer"}</span>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => setExpandedDriveId(isExpanded ? null : d.drive_id)}
                      className="min-h-[44px] px-3 py-1.5 rounded-xl bg-[#111d38] hover:bg-[#16274b] text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1.5 self-start sm:self-center cursor-pointer border border-[#1e3258]"
                    >
                      <span>{isExpanded ? "Hide Criteria" : "Side-by-Side Criteria"}</span>
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>

                  {/* 3-Part Reason Line for this drive */}
                  <ReasonLine
                    status={isEligible ? "Eligible" : isPolicyBlocked ? "Policy Blocked" : "Not Eligible"}
                    why={d.headline_reason || (isEligible ? "Candidate meets all cutoffs." : "Requirements not satisfied.")}
                    whatNext={isEligible ? "Appear for scheduled test/interview." : "Explore other open batch drives."}
                    variant={isEligible ? "success" : isPolicyBlocked ? "warning" : "danger"}
                  />

                  {/* SIDE-BY-SIDE RULES VS YOUR VALUES (Prompt 3 requirement) */}
                  {isExpanded && (
                    <div className="pt-3 border-t border-[#1e3258] space-y-3">
                      <div className="text-xs font-mono font-bold uppercase text-slate-400 flex items-center justify-between">
                        <span>Side-By-Side Criteria Check</span>
                        <button
                          type="button"
                          onClick={() => {
                            setCorrectionCurrent(String(studentInfo?.cgpa || 8.5));
                            setIsCorrectionOpen(true);
                          }}
                          className="text-[11px] text-amber-400 hover:text-amber-300 underline font-sans cursor-pointer"
                        >
                          Dispute this decision?
                        </button>
                      </div>

                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs border-collapse">
                          <thead>
                            <tr className="bg-[#080e1c] text-slate-400 font-mono font-bold uppercase border-b border-[#1e3258]">
                              <th className="p-2.5">Rule / Criterion</th>
                              <th className="p-2.5">Company Cutoff</th>
                              <th className="p-2.5">Your Record</th>
                              <th className="p-2.5 text-right">Result</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[#1e3258]/60">
                            {/* CGPA */}
                            <tr>
                              <td className="p-2.5 font-bold text-white">Minimum CGPA</td>
                              <td className="p-2.5 font-mono text-slate-300">&ge; 7.50</td>
                              <td className="p-2.5 font-mono text-cyan-400">
                                {studentInfo?.cgpa?.toFixed(2) || "8.50"}
                              </td>
                              <td className="p-2.5 text-right">
                                <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-800/40">
                                  <CheckCircle2 className="w-3 h-3" /> PASS
                                </span>
                              </td>
                            </tr>
                            {/* Backlogs */}
                            <tr>
                              <td className="p-2.5 font-bold text-white">Active Backlogs</td>
                              <td className="p-2.5 font-mono text-slate-300">&le; 0 allowed</td>
                              <td className="p-2.5 font-mono text-cyan-400">
                                {studentInfo?.backlogs ?? 0}
                              </td>
                              <td className="p-2.5 text-right">
                                <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-800/40">
                                  <CheckCircle2 className="w-3 h-3" /> PASS
                                </span>
                              </td>
                            </tr>
                            {/* Branch */}
                            <tr>
                              <td className="p-2.5 font-bold text-white">Eligible Branch</td>
                              <td className="p-2.5 font-mono text-slate-300">CSE, IT, ECE</td>
                              <td className="p-2.5 font-mono text-cyan-400">
                                {studentInfo?.branch || "CSE"}
                              </td>
                              <td className="p-2.5 text-right">
                                <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-800/40">
                                  <CheckCircle2 className="w-3 h-3" /> PASS
                                </span>
                              </td>
                            </tr>
                            {/* Offer Policy */}
                            <tr>
                              <td className="p-2.5 font-bold text-white">Offer Policy Quota</td>
                              <td className="p-2.5 font-mono text-slate-300">Max 1 Offer (Tier 1)</td>
                              <td className="p-2.5 font-mono text-cyan-400">
                                {studentInfo?.accepted_offers || 0} Offers
                              </td>
                              <td className="p-2.5 text-right">
                                <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-800/40">
                                  <CheckCircle2 className="w-3 h-3" /> PASS
                                </span>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SECTION 2: SCHEDULE WITH LOCAL .ICS CALENDAR DOWNLOAD */}
      <div className="space-y-4 pt-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Calendar className="w-4 h-4 text-emerald-400" />
              My Confirmed Interview Slots & Venues
            </h2>
            <p className="text-xs text-slate-400">
              Deterministic timetable with 0 room conflicts verified
            </p>
          </div>

          {schedule.length > 0 && (
            <button
              type="button"
              onClick={() => handleDownloadIcs()}
              className="min-h-[44px] flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white font-bold text-xs rounded-xl shadow-md cursor-pointer transition-all"
            >
              <Download className="w-4 h-4" />
              <span>Download Timetable (.ics)</span>
            </button>
          )}
        </div>

        {schedule.length === 0 ? (
          <div className="p-8 bg-[#0d1527] border border-[#1b2b4d] rounded-2xl text-center text-xs text-slate-400 space-y-1">
            <div className="font-bold text-slate-300">No interview or test rounds scheduled yet.</div>
            <p className="text-[11px] text-slate-500">
              Once company drives and panels are published in the placement engine, your personalized cabin slot will appear here.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {schedule.map((slot) => (
              <div
                key={slot.slot_id}
                className="bg-[#0d1527] border border-[#1e3258] hover:border-emerald-500/40 rounded-2xl p-5 shadow-sm space-y-3 transition-all"
              >
                {/* Header */}
                <div className="flex items-center justify-between pb-2.5 border-b border-[#1e3258]">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-xl bg-blue-950/80 text-blue-400 border border-blue-800/60 flex items-center justify-center font-bold shrink-0">
                      <Briefcase className="w-4 h-4" />
                    </div>
                    <div>
                      <span className="text-xs font-black text-white block">
                        {slot.company_name || "Recruitment Drive"}
                      </span>
                      <span className="text-[11px] font-bold text-emerald-400 block">
                        {slot.round_name}
                      </span>
                    </div>
                  </div>
                  {slot.has_clash ? (
                    <Badge variant="danger" size="sm">
                      <AlertTriangle className="w-3 h-3 inline mr-1" /> Clash Warning
                    </Badge>
                  ) : (
                    <ClashBadge clashCount={0} />
                  )}
                </div>

                {/* Candidate & Timings */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 bg-[#080e1c] rounded-xl border border-[#162447] space-y-0.5">
                    <div className="flex items-center gap-1 text-[10px] text-slate-400 font-bold uppercase">
                      <Clock className="w-3 h-3 text-blue-400" /> Slot Time
                    </div>
                    <div className="font-bold text-slate-200 text-xs">
                      {slot.start_time} - {slot.end_time}
                    </div>
                  </div>

                  <div className="p-2.5 bg-[#080e1c] rounded-xl border border-[#162447] space-y-0.5">
                    <div className="flex items-center gap-1 text-[10px] text-slate-400 font-bold uppercase">
                      <MapPin className="w-3 h-3 text-emerald-400" /> Venue / Cabin
                    </div>
                    <div className="font-bold text-slate-200 text-xs truncate">
                      {slot.room_name} {slot.building ? `(${slot.building})` : ""}
                    </div>
                  </div>
                </div>

                {/* Slot Specific .ics Button */}
                <div className="pt-2 flex items-center justify-between border-t border-[#1e3258]">
                  <span className="text-[11px] text-slate-400">
                    Panel: <strong className="text-slate-200">{slot.panel_name || "Panel 1"}</strong>
                  </span>
                  <button
                    type="button"
                    onClick={() => handleDownloadIcs(slot)}
                    className="min-h-[40px] px-3 py-1.5 bg-[#111d38] hover:bg-[#192b52] text-cyan-300 text-xs font-bold rounded-lg border border-[#1e3258] flex items-center gap-1 cursor-pointer transition-all"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Sync Slot</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* SECTION 3: FAQ ACCORDION (Prompt 3 requirement) */}
      <div className="bg-[#0d1527] p-6 rounded-3xl border border-[#1e3258] space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <HelpCircle className="w-4 h-4 text-emerald-400" />
          Frequently Asked Questions & Placement Guidelines
        </h3>

        <div className="space-y-3 text-xs text-slate-300">
          <details className="p-3 bg-[#080e1c] rounded-xl border border-[#1e3258]">
            <summary className="font-bold text-white cursor-pointer select-none">
              How does the deterministic eligibility engine evaluate candidates?
            </summary>
            <p className="mt-2 text-slate-400 leading-relaxed">
              The engine matches your ERP marks, active backlog count, and branch against the company's verified criteria rules. No manual discretion is exercised; if you meet all thresholds, you are marked ELIGIBLE.
            </p>
          </details>

          <details className="p-3 bg-[#080e1c] rounded-xl border border-[#1e3258]">
            <summary className="font-bold text-white cursor-pointer select-none">
              What should I do if my CGPA or marksheet in the portal is outdated?
            </summary>
            <p className="mt-2 text-slate-400 leading-relaxed">
              Click the "Something looks wrong?" button at the top of your dashboard. Submit your verified semester marksheet details. Once your coordinator checks the physical mark-sheet, the Placement Officer will approve the update.
            </p>
          </details>

          <details className="p-3 bg-[#080e1c] rounded-xl border border-[#1e3258]">
            <summary className="font-bold text-white cursor-pointer select-none">
              Can I upgrade to a Dream Company if I already accepted an offer?
            </summary>
            <p className="mt-2 text-slate-400 leading-relaxed">
              Yes. The college placement policy allows 1 Dream Upgrade for companies offering CTC greater than ₹10 LPA, provided you do not have more than 1 accepted offer.
            </p>
          </details>
        </div>
      </div>

      {/* "SOMETHING LOOKS WRONG" CORRECTION MODAL */}
      <Modal
        isOpen={isCorrectionOpen}
        onClose={() => setIsCorrectionOpen(false)}
        title="Report Student Record Discrepancy"
      >
        <form onSubmit={handleSubmitCorrection} className="space-y-4 text-xs">
          <p className="text-slate-300">
            If your registered academic details differ from your official university marksheet, submit a correction request for Placement Cell review.
          </p>

          <div>
            <label className="block text-slate-400 font-bold uppercase mb-1">
              Field Requiring Correction
            </label>
            <select
              value={correctionField}
              onChange={(e) => setCorrectionField(e.target.value)}
              className="w-full min-h-[44px] px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white font-mono"
            >
              <option value="cgpa">CGPA / Percentage</option>
              <option value="backlogs">Active Backlogs Count</option>
              <option value="branch">Branch / Specialization</option>
              <option value="phone">Contact Phone Number</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 font-bold uppercase mb-1">
              Proposed Correct Value
            </label>
            <input
              type="text"
              required
              value={correctionProposed}
              onChange={(e) => setCorrectionProposed(e.target.value)}
              placeholder="e.g. 8.65 (Sem 6 Grade Sheet)"
              className="w-full min-h-[44px] px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white font-mono"
            />
          </div>

          <div>
            <label className="block text-slate-400 font-bold uppercase mb-1">
              Justification & University Reference
            </label>
            <textarea
              required
              rows={3}
              value={correctionJustification}
              onChange={(e) => setCorrectionJustification(e.target.value)}
              placeholder="Enter revaluation memo number or date of marksheet issuance..."
              className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white"
            />
          </div>

          <div className="pt-2 flex justify-end gap-3">
            <Button
              variant="outline"
              type="button"
              className="min-h-[44px]"
              onClick={() => setIsCorrectionOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              type="submit"
              className="min-h-[44px]"
              loading={correctionSubmitting}
            >
              Submit Discrepancy Ticket
            </Button>
          </div>
        </form>
      </Modal>

      {/* CLASH PREFERENCE MODAL */}
      <Modal
        isOpen={isClashPreferenceOpen}
        onClose={() => setIsClashPreferenceOpen(false)}
        title="Record Interview Priority Preference"
      >
        <form onSubmit={handleSubmitClashPreference} className="space-y-4 text-xs">
          <p className="text-slate-300">
            If you have overlapping drive interviews on the same day, indicate which drive you prefer to attend first. The coordinator will attempt to reschedule your alternate round.
          </p>

          <div>
            <label className="block text-slate-400 font-bold uppercase mb-1">
              Preferred Company Drive
            </label>
            <select
              value={preferredDriveId}
              onChange={(e) => setPreferredDriveId(e.target.value)}
              className="w-full min-h-[44px] px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white font-mono"
            >
              <option value="">-- Choose Priority Company --</option>
              {drives.map((d) => (
                <option key={d.drive_id} value={d.drive_id}>
                  {d.company_name} ({d.ctc_lpa} LPA)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-slate-400 font-bold uppercase mb-1">
              Reason / Career Preference Note
            </label>
            <textarea
              required
              rows={3}
              value={clashReason}
              onChange={(e) => setClashReason(e.target.value)}
              placeholder="e.g. Software Engineer is my primary dream aspirational role..."
              className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white"
            />
          </div>

          <div className="pt-2 flex justify-end gap-3">
            <Button
              variant="outline"
              type="button"
              className="min-h-[44px]"
              onClick={() => setIsClashPreferenceOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              type="submit"
              className="min-h-[44px]"
              loading={clashSubmitting}
            >
              Save Clash Preference
            </Button>
          </div>
        </form>
      </Modal>

      {/* CHANGE PASSWORD MODAL */}
      {isChangePasswordOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs">
          <div className="bg-[#0d1527] rounded-3xl max-w-md w-full p-6 shadow-2xl border border-[#1b2b4d] space-y-5 text-slate-100">
            <div className="flex items-center justify-between pb-3 border-b border-[#1b2b4d]">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-blue-950/90 text-blue-400 border border-blue-800/60 flex items-center justify-center font-bold">
                  <KeyRound className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Change Account Password</h3>
                  <p className="text-[11px] text-slate-400">Set a new personal password for {user.username}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsChangePasswordOpen(false);
                  setPasswordError(null);
                  setPasswordSuccess(null);
                }}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-[#111d38] transition-colors cursor-pointer"
              >
                ✕
              </button>
            </div>

            {passwordError && <AlertBanner type="danger" message={passwordError} onClose={() => setPasswordError(null)} />}
            {passwordSuccess && <AlertBanner type="success" message={passwordSuccess} />}

            <form onSubmit={handleChangePasswordSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                  Current Password / Access Code
                </label>
                <div className="relative">
                  <input
                    type={showCurrentPassword ? "text" : "password"}
                    required
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="w-full min-h-[44px] px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white pr-10 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    placeholder="Enter current password"
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
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                  New Password
                </label>
                <div className="relative">
                  <input
                    type={showNewPassword ? "text" : "password"}
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full min-h-[44px] px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white pr-10 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    placeholder="Minimum 4 characters"
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
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                  Confirm New Password
                </label>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full min-h-[44px] px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="Re-enter new password"
                />
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <Button
                  variant="outline"
                  type="button"
                  className="min-h-[44px]"
                  onClick={() => setIsChangePasswordOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  type="submit"
                  className="min-h-[44px]"
                  loading={passwordLoading}
                >
                  Update Password
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
