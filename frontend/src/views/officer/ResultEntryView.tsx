import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Drive, Student } from "../../types";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import { Award, ShieldAlert, CheckCircle, ArrowRight, TrendingDown } from "lucide-react";

export const ResultEntryView: React.FC = () => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<string>("");
  const [selectedStudentId, setSelectedStudentId] = useState<string>("");
  const [eventType, setEventType] = useState<string>("offered");
  const [ctcLpa, setCtcLpa] = useState<number>(14.0);
  const [reason, setReason] = useState<string>("Cleared final technical and managerial rounds");
  const [loading, setLoading] = useState<boolean>(false);
  const [changeSet, setChangeSet] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [drvRes, stuRes] = await Promise.all([
          api.get<Drive[]>("/api/drives"),
          api.get<{ items: Student[] }>("/api/students?limit=200"),
        ]);
        const drvList = Array.isArray(drvRes) ? drvRes : ((drvRes as any)?.items || []);
        setDrives(drvList);
        if (drvList.length > 0) {
          setSelectedDriveId(drvList[0].id);
          setCtcLpa(drvList[0].ctc_lpa || 14.0);
        }
        const stuList = Array.isArray(stuRes) ? stuRes : ((stuRes as any)?.items || []);
        setStudents(stuList);
        if (stuList.length > 0) {
          setSelectedStudentId(stuList[0].id);
        }
      } catch {
        setError("Failed to load drives and candidate roster.");
      }
    };
    fetchData();
  }, []);

  const handleRecordResult = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDriveId || !selectedStudentId) return;

    try {
      setLoading(true);
      setError(null);
      setChangeSet(null);

      const res = await api.post<any>("/api/events/record-result", {
        student_id: selectedStudentId,
        drive_id: selectedDriveId,
        event_type: eventType,
        ctc_lpa: ctcLpa,
        reason: reason,
      });

      setSuccess(`Result recorded. Offer policy engine evaluated downstream impacts.`);
      setChangeSet(res.policy_changeset);
    } catch (err: any) {
      setError(err.message || "Failed to record drive result.");
    } finally {
      setLoading(false);
    }
  };

  const selectedDrive = drives.find((d) => d.id === selectedDriveId);
  const selectedStudent = students.find((s) => s.id === selectedStudentId);

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Result Entry & Policy Enforcement</h1>
        <p className="text-sm text-slate-500 mt-1">
          Recording recruitment offers triggers the college offer policy engine and computes a live ChangeSet of downstream drive blockages.
        </p>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {success && <AlertBanner type="success" message={success} onClose={() => setSuccess(null)} />}

      {/* Entry Form */}
      <form onSubmit={handleRecordResult} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <Award className="w-4 h-4 text-brand-600" />
          Record Drive Selection / Outcome
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
              Select Company Drive
            </label>
            <select
              value={selectedDriveId}
              onChange={(e) => {
                setSelectedDriveId(e.target.value);
                const d = drives.find((item) => item.id === e.target.value);
                if (d && d.ctc_lpa) setCtcLpa(d.ctc_lpa);
              }}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold"
            >
              {drives.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.company_name} ({d.ctc_lpa} LPA)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
              Select Candidate
            </label>
            <select
              value={selectedStudentId}
              onChange={(e) => setSelectedStudentId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold"
            >
              {students.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.roll_no} - {s.branch})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
              Outcome Event
            </label>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold"
            >
              <option value="offered">Offered (Final Selection)</option>
              <option value="rejected">Rejected in Final Round</option>
              <option value="attended">Attended Round</option>
              <option value="absent">Absent / Withdrawn</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
              Offered CTC (LPA)
            </label>
            <input
              type="number"
              step="0.5"
              value={ctcLpa}
              onChange={(e) => setCtcLpa(parseFloat(e.target.value))}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold"
            />
          </div>
        </div>

        <div>
          <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
            Recruiter Remarks / Reason
          </label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium"
          />
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors disabled:opacity-50"
          >
            <Award className="w-4 h-4" />
            <span>{loading ? "Recording..." : "Record Outcome & Enforce Policy"}</span>
          </button>
        </div>
      </form>

      {/* Downstream Policy Enforcement ChangeSet */}
      {changeSet && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-600" />
              Downstream Enforcement ChangeSet
            </h3>
            <Badge variant="warning">Automated Offer Policy Live Action</Badge>
          </div>

          <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 leading-relaxed">
            Candidate <strong className="font-bold">{selectedStudent?.name}</strong> has received an offer of{" "}
            <strong>{ctcLpa} LPA</strong> from {selectedDrive?.company_name}. Under institutional Policy Clause 2.1 ("One Offer & Out"):
          </div>

          <div className="space-y-2">
            {changeSet.drives_blocked && changeSet.drives_blocked.length > 0 ? (
              changeSet.drives_blocked.map((item: any, idx: number) => (
                <div
                  key={idx}
                  className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-2">
                    <TrendingDown className="w-4 h-4 text-rose-600" />
                    <span className="font-bold text-slate-800">{item.company_name}</span>
                    <span className="text-slate-500">({item.ctc_lpa} LPA)</span>
                  </div>
                  <Badge variant="danger" size="sm">Blocked from Sitting</Badge>
                </div>
              ))
            ) : (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-600" />
                <span>No subsequent drives blocked (offer qualifies for Dream Company exemption).</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
