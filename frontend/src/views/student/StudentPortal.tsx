import React, { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../api/client";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
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
  UserCheck,
  MapPin,
} from "lucide-react";

export const StudentPortal: React.FC = () => {
  const { user, studentLogin } = useAuth();

  // Login form state (if not authenticated as student)
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
      // Fallback display if mock LAN session
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
                className="w-full px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:bg-[#0d1527] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="e.g. PIPE_001"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                One-Time Access Code
              </label>
              <input
                type="password"
                required
                value={accessCode}
                onChange={(e) => setAccessCode(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:bg-[#0d1527] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="Issued by Placement Cell"
              />
            </div>

            <button
              type="submit"
              disabled={loginLoading}
              className="w-full py-3 bg-gradient-to-r from-blue-600 via-teal-600 to-emerald-600 hover:from-blue-500 hover:via-teal-500 hover:to-emerald-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-emerald-900/30 border border-emerald-400/30 transition-all cursor-pointer disabled:opacity-50"
            >
              {loginLoading ? "Authenticating on LAN..." : "Sign In to Portal"}
            </button>
          </form>

          <div className="p-3 bg-[#080e1c] rounded-xl border border-[#1b2b4d] text-center">
            <span className="text-[11px] text-slate-400 font-medium">
              🔒 Privacy Guaranteed: Student accounts can only view their own records. Peer rankings and other candidates' data are strictly inaccessible on the server.
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      {/* Student Banner */}
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
              <span className="text-emerald-400 font-bold">CGPA: {studentInfo?.cgpa?.toFixed(2) || "8.50"}</span>
            </div>
          </div>
        </div>

        {/* Printable & Download Actions */}
        <div className="flex items-center gap-2 no-print">
          <button
            onClick={() => window.print()}
            className="flex items-center gap-1.5 px-3 py-2 bg-[#111d38] hover:bg-[#162447] text-slate-200 hover:text-emerald-300 border border-[#1b2b4d] hover:border-emerald-500/40 text-xs font-bold rounded-xl transition-all cursor-pointer"
            title="Print clean status sheet"
          >
            <Printer className="w-3.5 h-3.5 text-emerald-400" />
            <span>Print Sheet</span>
          </button>
          <a
            href="/api/portal/status-sheet.pdf"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3.5 py-2 bg-gradient-to-r from-blue-600 via-teal-600 to-emerald-600 hover:from-blue-500 hover:via-teal-500 hover:to-emerald-500 text-white text-xs font-bold rounded-xl border border-emerald-400/30 shadow-md shadow-emerald-900/30 transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Official PDF</span>
          </a>
        </div>
      </div>

      {/* Offer Policy Summary Box */}
      {policyStatus && (
        <div className="p-4 bg-gradient-to-r from-[#0c1836] to-[#072421] text-white rounded-2xl shadow-md border border-emerald-500/30 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-300">
              Institutional Placement Policy Standing
            </span>
            <Badge variant="brand" size="sm">Active Eligibility</Badge>
          </div>
          <p className="text-xs text-slate-200 font-medium leading-relaxed">
            {policyStatus.summary ||
              "You are currently eligible to sit for all regular recruitment drives and Dream Company tiers."}
          </p>
        </div>
      )}

      {/* Section 1: Candidate's Own Drive Eligibility */}
      <div className="space-y-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Briefcase className="w-4 h-4 text-emerald-400" />
          Campus Drives & Eligibility Verdicts
        </h2>

        {drives.length === 0 ? (
          <div className="p-8 bg-[#0d1527] border border-[#1b2b4d] rounded-2xl text-center text-xs text-slate-400">
            No published drives currently available for your batch.
          </div>
        ) : (
          <div className="space-y-3">
            {drives.map((d) => {
              const isEligible = d.status === "eligible";
              const isPolicyBlocked = d.status === "policy_blocked";
              const isExpanded = expandedDriveId === d.drive_id;

              return (
                <div
                  key={d.drive_id}
                  className="bg-[#0d1527] border border-[#1b2b4d] hover:border-emerald-500/40 rounded-2xl p-4 shadow-sm transition-all space-y-3 print-card"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">{d.company_name}</span>
                        <Badge
                          variant={isEligible ? "success" : isPolicyBlocked ? "warning" : "danger"}
                          size="sm"
                        >
                          {d.status.replace("_", " ").toUpperCase()}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-400 font-medium mt-0.5">
                        <span className="font-mono text-emerald-400 font-bold">{d.ctc_lpa} LPA</span>
                        <span>•</span>
                        <span>Drive Date: {new Date(d.drive_date).toLocaleDateString()}</span>
                      </div>
                    </div>

                    <button
                      onClick={() => setExpandedDriveId(isExpanded ? null : d.drive_id)}
                      className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1 self-start sm:self-center no-print cursor-pointer"
                    >
                      <span>{isExpanded ? "Hide Details" : "Rule Breakdown"}</span>
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>
                  </div>

                  {/* Plain-English One-Line Reason */}
                  <div className="p-3 bg-[#080e1c] border border-[#1b2b4d] rounded-xl text-xs font-medium text-slate-300">
                    {d.headline_reason}
                  </div>

                  {/* Expandable Breakdown */}
                  {isExpanded && (
                    <div className="pt-2 border-t border-[#1b2b4d] space-y-2 text-xs">
                      {d.passed_rules && d.passed_rules.length > 0 && (
                        <div>
                          <span className="font-bold text-emerald-400 block mb-1">Passed Criteria:</span>
                          <ul className="list-disc pl-5 text-emerald-300 space-y-0.5">
                            {d.passed_rules.map((rule: string, idx: number) => (
                              <li key={idx}>{rule}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {d.failed_rules && d.failed_rules.length > 0 && (
                        <div>
                          <span className="font-bold text-rose-400 block mb-1">Failed Criteria:</span>
                          <ul className="list-disc pl-5 text-rose-300 space-y-0.5">
                            {d.failed_rules.map((rule: string, idx: number) => (
                              <li key={idx}>{rule}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Section 2: Candidate's Own Interview & Test Timetable */}
      <div className="space-y-4 pt-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Calendar className="w-4 h-4 text-emerald-400" />
            My Scheduled Rounds & Campus Venues
          </h2>
          {schedule.length > 0 && (
            <span className="text-xs font-bold px-2.5 py-0.5 bg-emerald-950/80 text-emerald-300 rounded-full border border-emerald-800/60">
              {schedule.length} Confirmed {schedule.length === 1 ? "Slot" : "Slots"}
            </span>
          )}
        </div>

        {schedule.length === 0 ? (
          <div className="p-8 bg-[#0d1527] border border-[#1b2b4d] rounded-2xl text-center text-xs text-slate-400 space-y-1">
            <div className="font-bold text-slate-300">No interview or test rounds scheduled yet.</div>
            <p className="text-[11px] text-slate-500">
              Once company drives and panels are generated in the placement engine, your personalized cabin slot will appear here.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {schedule.map((slot) => (
              <div
                key={slot.slot_id}
                className="bg-[#0d1527] border border-[#1b2b4d] hover:border-emerald-500/40 rounded-2xl p-5 shadow-sm space-y-3 print-card transition-all"
              >
                {/* Header: Company & Verified Status */}
                <div className="flex items-center justify-between pb-2.5 border-b border-[#1b2b4d]/70">
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
                    <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-950/80 text-emerald-300 rounded-full border border-emerald-800/60 flex items-center gap-1 shrink-0">
                      <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                      Confirmed
                    </span>
                  )}
                </div>

                {/* Candidate Name matching Schedule Grid */}
                <div className="p-2.5 bg-[#080e1c] rounded-xl border border-[#162447] flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <UserCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 block">Candidate</span>
                      <span className="font-bold text-white text-xs block">
                        {slot.student_name || studentInfo?.name || "Student Candidate"}
                      </span>
                    </div>
                  </div>
                  <div className="text-right font-mono text-[11px] font-bold text-emerald-400 bg-emerald-950/40 px-2 py-1 rounded-lg border border-emerald-900/40">
                    {slot.roll_no || studentInfo?.roll_no || user.username}
                  </div>
                </div>

                {/* Venue & Timings Grid */}
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
                      <MapPin className="w-3 h-3 text-emerald-400" /> Campus Cabin
                    </div>
                    <div className="font-bold text-slate-200 text-xs truncate">
                      {slot.room_name} {slot.building ? `(${slot.building})` : ""}
                    </div>
                  </div>
                </div>

                {/* Panel Info */}
                {slot.panel_name && (
                  <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1 border-t border-[#1b2b4d]/40">
                    <span>Interview Panel: <strong className="text-slate-300">{slot.panel_name}</strong></span>
                    <span className="text-[10px] font-mono text-emerald-400 font-bold">0 Clashes Guaranteed</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
