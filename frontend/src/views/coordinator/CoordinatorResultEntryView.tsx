import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Drive, Student } from "../../types";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  Award,
  Clock,
  CheckCircle,
  XCircle,
  Building,
  User,
  PlusCircle,
  Send,
  FileCheck,
  ShieldAlert,
  Info,
} from "lucide-react";

interface PendingResultItem {
  id: string;
  drive_id: string;
  company_name: string;
  student_id: string;
  student_name: string;
  roll_no: string;
  event_type: string;
  ctc_lpa: number;
  fixed_pay_lpa?: number;
  is_dream: boolean;
  reason: string;
  submitted_by: string;
  submitted_at: string;
  status: "pending" | "approved" | "rejected";
  officer_name?: string;
  resolved_at?: string;
  resolution_notes?: string;
}

export const CoordinatorResultEntryView: React.FC = () => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [pendingResults, setPendingResults] = useState<PendingResultItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Form State
  const [selectedDriveId, setSelectedDriveId] = useState("");
  const [selectedStudentId, setSelectedStudentId] = useState("");
  const [eventType, setEventType] = useState("offered");
  const [ctcLpa, setCtcLpa] = useState<number>(14.0);
  const [fixedPayLpa, setFixedPayLpa] = useState<number | undefined>(12.0);
  const [isDream, setIsDream] = useState(false);
  const [reason, setReason] = useState("Cleared Round 3 technical interview and HR evaluation.");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [dRes, sRes, pRes] = await Promise.all([
        api.get<Drive[]>("/api/drives"),
        api.get<{ items: Student[] }>("/api/students?limit=2500"),
        api.get<PendingResultItem[]>("/api/coordinator/pending-results"),
      ]);
      const drvList = Array.isArray(dRes) ? dRes : ((dRes as any)?.items || []);
      setDrives(drvList);
      if (drvList.length > 0) {
        setSelectedDriveId((prev) => (!prev || !drvList.some((d: any) => d.id === prev) ? drvList[0].id : prev));
        setCtcLpa((prev) => (prev ? prev : (drvList[0].ctc_lpa || 14.0)));
      } else {
        setSelectedDriveId("");
      }
      const sList = Array.isArray(sRes) ? sRes : ((sRes as any)?.items || []);
      setStudents(sList);
      if (sList.length > 0) {
        setSelectedStudentId((prev) => prev || sList[0].id);
      }
      setPendingResults(pRes || []);
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSubmitResult = async (e: React.FormEvent) => {
    e.preventDefault();
    const driveIdToUse = selectedDriveId || (drives.length > 0 ? drives[0].id : "");
    const studentIdToUse = selectedStudentId || (students.length > 0 ? students[0].id : "");
    if (!driveIdToUse || !studentIdToUse) {
      setError("Please select both a company drive and candidate.");
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      const res = await api.post<any>("/api/coordinator/pending-results", {
        drive_id: driveIdToUse,
        student_id: studentIdToUse,
        event_type: eventType,
        ctc_lpa: ctcLpa,
        fixed_pay_lpa: fixedPayLpa,
        is_dream: isDream,
        reason: reason,
      });

      const todayStr = new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
      setSuccess(`Result saved as PENDING on ${todayStr}. Forwarded to Placement Officer for confirmation & ChangeSet policy enforcement.`);
      fetchData();
    } catch (err: any) {
      setError(err.message || "Failed to log result.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Result Entry (Pending Officer Approval)</h1>
            <Badge variant="brand">Two-Man Rule Protocol</Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Student coordinators can submit selection & offer records. Entries are saved as PENDING until approved by the Placement Officer to trigger policy enforcement.
          </p>
        </div>
      </div>

      {/* Protocol Banner */}
      <div className="p-4 bg-purple-50 border border-purple-200 rounded-2xl flex items-start gap-3">
        <Info className="w-5 h-5 text-purple-600 shrink-0 mt-0.5" />
        <div className="text-xs text-purple-900 leading-relaxed">
          <strong>Institutional Governance Safeguard:</strong> Result outcomes directly influence candidate dream-tier eligibility and automatic drive exclusions. Therefore, coordinator entries enter an Officer Approval Queue where the downstream ChangeSet is reviewed before applying.
        </div>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {success && <AlertBanner type="success" message={success} onClose={() => setSuccess(null)} />}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Entry Form */}
        <div className="lg:col-span-1 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Award className="w-4 h-4 text-brand-600" />
            <span>Record Candidate Outcome</span>
          </h2>

          <form onSubmit={handleSubmitResult} className="space-y-3.5 text-xs">
            <div>
              <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">Company Drive</label>
              <select
                value={selectedDriveId}
                onChange={(e) => {
                  setSelectedDriveId(e.target.value);
                  const d = drives.find((item) => item.id === e.target.value);
                  if (d) setCtcLpa(d.ctc_lpa || 14.0);
                }}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-semibold cursor-pointer"
              >
                {drives.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.company_name} ({d.ctc_lpa} LPA)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">Candidate</label>
              <select
                value={selectedStudentId}
                onChange={(e) => setSelectedStudentId(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-semibold cursor-pointer"
              >
                {students.slice(0, 150).map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.roll_no} - {s.name} ({s.branch.slice(0, 15)}...)
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">Outcome</label>
                <select
                  value={eventType}
                  onChange={(e) => setEventType(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-semibold cursor-pointer"
                >
                  <option value="shortlisted">Shortlisted</option>
                  <option value="selected">Selected</option>
                  <option value="offered">Offered</option>
                  <option value="accepted">Accepted</option>
                  <option value="declined">Declined</option>
                  <option value="revoked">Revoked</option>
                </select>
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">CTC (LPA)</label>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  value={ctcLpa}
                  onChange={(e) => setCtcLpa(parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-mono"
                />
              </div>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="coord_dream_check"
                checked={isDream}
                onChange={(e) => setIsDream(e.target.checked)}
                className="accent-brand-600 rounded cursor-pointer"
              />
              <label htmlFor="coord_dream_check" className="font-semibold text-slate-700 cursor-pointer">
                Classify as Dream Company Tier
              </label>
            </div>

            <div>
              <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                Evaluation Notes / Justification <span className="text-rose-500">*</span>
              </label>
              <textarea
                rows={3}
                required
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g. Cleared all 3 interview cabins; HR confirmed offer letter handed over..."
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white"
              />
            </div>

            <button
              type="submit"
              disabled={submitting || loading || drives.length === 0 || students.length === 0}
              className="w-full py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-bold rounded-xl shadow-xs transition-colors cursor-pointer disabled:opacity-50 flex items-center justify-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{submitting ? "Submitting..." : "Log Result as Pending"}</span>
            </button>
          </form>
        </div>

        {/* Pending & Approved Results Stream */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
              <Clock className="w-4 h-4 text-purple-600" />
              <span>Coordinator Submissions Log ({pendingResults.length})</span>
            </h3>
            <span className="text-xs text-slate-500">Live Status Stream</span>
          </div>

          {pendingResults.length === 0 ? (
            <div className="p-8 bg-white border border-slate-200 rounded-2xl text-center text-xs text-slate-500">
              No results logged yet. Use the form on the left to record candidate outcomes from today's recruitment rounds.
            </div>
          ) : (
            <div className="space-y-3 max-h-[560px] overflow-y-auto custom-scrollbar">
              {pendingResults.map((pr) => (
                <div
                  key={pr.id}
                  className="p-4 bg-white rounded-2xl border border-slate-200 shadow-2xs space-y-2 hover:border-brand-200 transition-all"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900 text-sm">{pr.student_name}</span>
                        <span className="text-xs font-mono text-slate-500">({pr.roll_no})</span>
                      </div>
                      <span className="text-xs text-slate-500">
                        {pr.company_name} • <strong className="text-slate-800 capitalize">{pr.event_type}</strong> @ {pr.ctc_lpa} LPA
                      </span>
                    </div>

                    <span
                      className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${
                        pr.status === "approved"
                          ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                          : pr.status === "rejected"
                          ? "bg-rose-100 text-rose-800 border border-rose-300"
                          : "bg-amber-100 text-amber-800 border border-amber-300 animate-pulse"
                      }`}
                    >
                      {pr.status === "pending" ? "Awaiting Officer Approval" : pr.status.toUpperCase()}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                    "{pr.reason}"
                  </p>

                  <div className="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-slate-100">
                    <span>
                      Requested by <strong>{pr.submitted_by}</strong> on{" "}
                      {new Date(pr.submitted_at).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                    {pr.officer_name && (
                      <span className="text-emerald-700 font-semibold">
                        Reviewed by Officer {pr.officer_name}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
