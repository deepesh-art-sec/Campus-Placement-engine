import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Drive, Student } from "../../types";
import { Badge } from "../../components/common/Badge";
import { Modal } from "../../components/common/Modal";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  ShieldAlert,
  Users,
  CheckCircle,
  Building,
  Calendar,
  Send,
  Sparkles,
  Info,
  Clock,
  ArrowRight,
  RefreshCw,
} from "lucide-react";

interface ClashItem {
  id: string;
  student_roll: string;
  student_name: string;
  branch: string;
  drive_a_id: string;
  drive_a_company: string;
  drive_a_time: string;
  drive_b_id: string;
  drive_b_company: string;
  drive_b_time: string;
  status: "unresolved" | "preference_recorded" | "resolved";
  recorded_preference?: string;
}

export const CoordinatorClashesView: React.FC = () => {
  const [clashes, setClashes] = useState<ClashItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedClash, setSelectedClash] = useState<ClashItem | null>(null);
  const [chosenDriveId, setChosenDriveId] = useState<string>("");
  const [preferenceReason, setPreferenceReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchClashes = async () => {
    try {
      setLoading(true);
      const res = await api.get<ClashItem[]>("/api/coordinator/clashes");
      setClashes(res || []);
    } catch {
      setClashes([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClashes();
  }, []);

  const handleOpenPreferenceModal = (clash: ClashItem) => {
    setSelectedClash(clash);
    setChosenDriveId(clash.drive_a_id);
    setPreferenceReason("Candidate communicated preference for Technical SDE Track");
    setSuccess(null);
  };

  const handleSubmitPreference = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClash || !chosenDriveId) return;

    try {
      setSubmitting(true);
      const preferredCompany =
        chosenDriveId === selectedClash.drive_a_id
          ? selectedClash.drive_a_company
          : selectedClash.drive_b_company;
      const conflictingCompany =
        chosenDriveId === selectedClash.drive_a_id
          ? selectedClash.drive_b_company
          : selectedClash.drive_a_company;

      await api.post("/api/coordinator/clashes/preference", {
        student_id: selectedClash.student_roll,
        preferred_drive_id: chosenDriveId,
        conflicting_drive_id:
          chosenDriveId === selectedClash.drive_a_id
            ? selectedClash.drive_b_id
            : selectedClash.drive_a_id,
        reason: preferenceReason,
      });

      // Update local state
      setClashes((prev) =>
        prev.map((c) =>
          c.id === selectedClash.id
            ? { ...c, status: "preference_recorded", recorded_preference: preferredCompany }
            : c
        )
      );

      const todayStr = new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
      setSuccess(`Preference recorded on ${todayStr} for ${selectedClash.student_name}: Prefers ${preferredCompany} over ${conflictingCompany}. Sent to Officer.`);
      setSelectedClash(null);
    } catch {
      // Handled
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Student Clash Centre</h1>
            <Badge variant={clashes.filter((c) => c.status === "unresolved").length === 0 ? "success" : "warning"}>
              {clashes.filter((c) => c.status === "unresolved").length === 0
                ? "0 Clashes Active"
                : `${clashes.filter((c) => c.status === "unresolved").length} Overlapping Windows`}
            </Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Detect students shortlisted by two companies with overlapping interview windows. Record candidate stated preferences and notify the Officer.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={fetchClashes}
            className="p-2 text-slate-600 hover:text-slate-900 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 shadow-2xs transition-all cursor-pointer"
            title="Refresh clash detections"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-purple-600" : ""}`} />
          </button>
        </div>
      </div>

      {success && <AlertBanner type="success" message={success} onClose={() => setSuccess(null)} />}

      <div className="p-4 bg-purple-50 border border-purple-200 rounded-2xl flex items-start gap-3">
        <Info className="w-5 h-5 text-purple-600 shrink-0 mt-0.5" />
        <div className="text-xs text-purple-900 leading-relaxed">
          <strong>Coordinator Operating Rule:</strong> Coordinators are not permitted to silently drop students from shortlists. When two companies conflict on the same Tuesday morning, contact the candidate to record their preference, which logs into the Officer's clash resolution queue.
        </div>
      </div>

      {/* Clashes List */}
      <div className="space-y-4">
        {loading ? (
          <div className="p-8 text-center bg-white rounded-2xl border border-slate-200 shadow-xs flex items-center justify-center gap-2 text-slate-500 text-xs">
            <RefreshCw className="w-4 h-4 animate-spin text-purple-600" />
            <span>Scanning published schedules for candidate conflicts...</span>
          </div>
        ) : clashes.length === 0 ? (
          <div className="p-8 text-center bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col items-center justify-center">
            <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mb-3">
              <CheckCircle className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-800">Zero Schedule Clashes Detected</h3>
            <p className="text-xs text-slate-500 max-w-md mt-1">
              All published drive slots are fully coordinated and non-overlapping. No student is currently double-booked.
            </p>
          </div>
        ) : (
          clashes.map((c) => (
          <div
            key={c.id}
            className="p-5 bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-brand-200 transition-all"
          >
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <span className="font-bold text-slate-900 text-sm">{c.student_name}</span>
                <span className="text-xs font-mono text-slate-500">Roll: {c.student_roll}</span>
                <span className="text-xs text-slate-400">• {c.branch}</span>
              </div>

              {/* Conflict Comparison Pills */}
              <div className="flex items-center gap-2 flex-wrap text-xs">
                <div className="p-2.5 bg-blue-50 border border-blue-200 rounded-xl flex items-center gap-2">
                  <Building className="w-3.5 h-3.5 text-blue-600" />
                  <span className="font-bold text-blue-900">{c.drive_a_company}</span>
                  <span className="text-slate-500 font-mono text-[11px] font-semibold">{c.drive_a_time}</span>
                </div>

                <span className="text-rose-500 font-black text-xs">VS</span>

                <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-xl flex items-center gap-2">
                  <Building className="w-3.5 h-3.5 text-amber-600" />
                  <span className="font-bold text-amber-900">{c.drive_b_company}</span>
                  <span className="text-slate-500 font-mono text-[11px] font-semibold">{c.drive_b_time}</span>
                </div>
              </div>

              {c.recorded_preference && (
                <div className="text-xs text-emerald-700 font-semibold flex items-center gap-1.5">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Stated Preference Recorded: <strong>{c.recorded_preference}</strong></span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 shrink-0">
              {c.status === "unresolved" ? (
                <button
                  type="button"
                  onClick={() => handleOpenPreferenceModal(c)}
                  className="flex items-center gap-1.5 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Record Student Choice</span>
                </button>
              ) : (
                <Badge variant="success">Preference Sent to Officer</Badge>
              )}
            </div>
          </div>
        )))}
      </div>

      {/* Record Preference Modal */}
      {selectedClash && (
        <Modal
          isOpen={!!selectedClash}
          onClose={() => setSelectedClash(null)}
          title={`Record Candidate Stated Preference`}
        >
          <form onSubmit={handleSubmitPreference} className="space-y-4 text-xs">
            <p className="text-slate-600">
              Ask candidate <strong>{selectedClash.student_name}</strong> ({selectedClash.student_roll}) which company interview they prefer to attend first.
            </p>

            <div>
              <label className="font-bold text-slate-700 uppercase tracking-wider block mb-2">
                Candidate's Stated Preference:
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setChosenDriveId(selectedClash.drive_a_id)}
                  className={`p-3 rounded-xl border text-left cursor-pointer transition-all ${
                    chosenDriveId === selectedClash.drive_a_id
                      ? "border-purple-600 bg-purple-50 ring-2 ring-purple-500/20"
                      : "border-slate-200 bg-white hover:bg-slate-50"
                  }`}
                >
                  <span className="font-bold text-slate-900 block text-xs">{selectedClash.drive_a_company}</span>
                  <span className="text-[11px] text-slate-500 font-mono">{selectedClash.drive_a_time}</span>
                </button>

                <button
                  type="button"
                  onClick={() => setChosenDriveId(selectedClash.drive_b_id)}
                  className={`p-3 rounded-xl border text-left cursor-pointer transition-all ${
                    chosenDriveId === selectedClash.drive_b_id
                      ? "border-purple-600 bg-purple-50 ring-2 ring-purple-500/20"
                      : "border-slate-200 bg-white hover:bg-slate-50"
                  }`}
                >
                  <span className="font-bold text-slate-900 block text-xs">{selectedClash.drive_b_company}</span>
                  <span className="text-[11px] text-slate-500 font-mono">{selectedClash.drive_b_time}</span>
                </button>
              </div>
            </div>

            <div>
              <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                Candidate's Stated Justification:
              </label>
              <textarea
                rows={3}
                required
                value={preferenceReason}
                onChange={(e) => setPreferenceReason(e.target.value)}
                placeholder="e.g. Student prefers SDE role at Google and will attend Microsoft round in afternoon slot if rescheduled..."
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white"
              />
            </div>

            <div className="pt-2 flex justify-end gap-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setSelectedClash(null)}
                className="px-3 py-1.5 text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting || !preferenceReason.trim()}
                className="flex items-center gap-1.5 px-4 py-1.5 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-xl shadow-xs cursor-pointer disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{submitting ? "Forwarding..." : "Submit to Officer"}</span>
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};
