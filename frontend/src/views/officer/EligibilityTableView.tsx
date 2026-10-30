import React, { useState, useEffect, useRef } from "react";
import { api } from "../../api/client";
import { Drive, EligibilityDecisionItem } from "../../types";
import { Badge } from "../../components/common/Badge";
import { Drawer } from "../../components/common/Drawer";
import { ProgressBar } from "../../components/common/ProgressBar";
import { AlertBanner } from "../../components/common/AlertBanner";
import { Modal } from "../../components/common/Modal";
import {
  CheckCircle,
  XCircle,
  Search,
  Filter,
  Play,
  Clock,
  Briefcase,
  AlertTriangle,
  ChevronRight,
  Shield,
  FileCheck,
  Trash2,
} from "lucide-react";

interface EligibilityTableViewProps {
  initialDriveId?: string;
}

export const EligibilityTableView: React.FC<EligibilityTableViewProps> = ({ initialDriveId }) => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<string>(initialDriveId || "");
  const [decisions, setDecisions] = useState<EligibilityDecisionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStudent, setSelectedStudent] = useState<EligibilityDecisionItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteReason, setDeleteReason] = useState("");
  const [deleting, setDeleting] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const fetchDrives = async () => {
      try {
        const res = await api.get<Drive[]>("/api/drives");
        const list = res || [];
        setDrives(list);
        if (list.length > 0) {
          if (!selectedDriveId || !list.some((d) => d.id === selectedDriveId)) {
            setSelectedDriveId(list[0].id);
          }
        } else {
          setSelectedDriveId("");
        }
      } catch (err: any) {
        setError("Failed to load recruitment drives.");
      }
    };
    fetchDrives();
  }, [initialDriveId]);

  const fetchDecisions = async (driveId: string) => {
    if (!driveId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.get<EligibilityDecisionItem[]>(`/api/eligibility/decisions/${driveId}`);
      setDecisions(res || []);
    } catch {
      setDecisions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDriveId) {
      fetchDecisions(selectedDriveId);
    }
  }, [selectedDriveId]);

  const handleConfirmDeleteDrive = async () => {
    if (!selectedDriveId) return;
    if (!deleteReason.trim()) {
      setError("Please provide a mandatory reason for removing the drive.");
      return;
    }
    const drvToDelete = drives.find((d) => d.id === selectedDriveId);
    try {
      setDeleting(true);
      setError(null);
      await api.delete(
        `/api/drives/${selectedDriveId}?reason=${encodeURIComponent(deleteReason)}`
      );
      setSuccess(`Company '${drvToDelete?.company_name || "Drive"}' and all associated records permanently removed.`);
      setDeleteModalOpen(false);
      setDeleteReason("");
      const remaining = drives.filter((d) => d.id !== selectedDriveId);
      setDrives(remaining);
      if (remaining.length > 0) {
        setSelectedDriveId(remaining[0].id);
      } else {
        setSelectedDriveId("");
        setDecisions([]);
      }
    } catch (err: any) {
      setError(err.message || "Failed to remove drive.");
    } finally {
      setDeleting(false);
    }
  };

  const handleRunEvaluation = async () => {
    if (!selectedDriveId) return;
    try {
      setEvaluating(true);
      setProgress(10);
      setError(null);

      abortControllerRef.current = new AbortController();

      const timer = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(timer);
            return 90;
          }
          return prev + 25;
        });
      }, 150);

      const res = await api.post<any>(
        "/api/eligibility/run",
        { drive_id: selectedDriveId },
        abortControllerRef.current.signal
      );

      clearInterval(timer);
      setProgress(100);

      setTimeout(() => {
        setEvaluating(false);
        fetchDecisions(selectedDriveId);
      }, 300);
    } catch (err: any) {
      if (err.name === "AbortError") {
        setError("Evaluation was cancelled by user.");
      } else {
        setError(err.message || "Evaluation failed.");
      }
      setEvaluating(false);
    }
  };

  const handleCancelEvaluation = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setEvaluating(false);
  };

  const filteredDecisions = decisions.filter((d) => {
    const matchesSearch =
      d.student_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.roll_no.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.branch.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === "all"
        ? true
        : statusFilter === "applied"
        ? d.has_applied === true
        : d.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const appliedCount = decisions.filter((d) => d.has_applied).length;
  const eligibleCount = decisions.filter((d) => d.status === "eligible").length;
  const ineligibleCount = decisions.filter((d) => d.status === "ineligible").length;
  const policyBlockedCount = decisions.filter((d) => d.status === "policy_blocked").length;

  const currentDrive = drives.find((d) => d.id === selectedDriveId);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Eligibility Evaluation Engine</h1>
          <p className="text-sm text-slate-500 mt-1">
            Pure, deterministic candidate filtering against company Rule AST and college offer policies.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedDriveId}
            onChange={(e) => setSelectedDriveId(e.target.value)}
            className="px-3.5 py-2 bg-white border border-slate-200 rounded-xl text-xs font-bold text-slate-800 shadow-xs"
          >
            {drives.map((d) => (
              <option key={d.id} value={d.id}>
                {d.company_name} ({d.ctc_lpa} LPA)
              </option>
            ))}
          </select>

          <button
            onClick={handleRunEvaluation}
            disabled={evaluating || !selectedDriveId}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Evaluate Candidates</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setDeleteReason("");
              setDeleteModalOpen(true);
            }}
            disabled={!selectedDriveId || evaluating || deleting}
            className="flex items-center gap-1.5 px-3 py-2 bg-rose-50 hover:bg-rose-100 text-rose-600 dark:bg-rose-950/40 dark:hover:bg-rose-900/60 dark:text-rose-300 border border-rose-200 dark:border-rose-800 rounded-xl text-xs font-bold transition-colors disabled:opacity-50 cursor-pointer shadow-2xs"
            title={`Permanently delete ${currentDrive?.company_name || "selected"} drive`}
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Delete Drive</span>
          </button>
        </div>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {success && <AlertBanner type="success" message={success} onClose={() => setSuccess(null)} />}

      {/* Heavy Action Indicator */}
      {evaluating && (
        <ProgressBar
          label={`Evaluating candidates against ${currentDrive?.company_name || "Drive"} rules & offer policy...`}
          progressPercent={progress}
          isCancellable={true}
          onCancel={handleCancelEvaluation}
          subLabel="Evaluating Pure AST & College Dream Exceptions"
        />
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase">Total Evaluated</span>
          <span className="text-2xl font-black text-slate-900 block mt-1">{decisions.length}</span>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-emerald-200 bg-emerald-50/30 shadow-xs">
          <span className="text-xs font-semibold text-emerald-700 uppercase flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span> Applied
          </span>
          <span className="text-2xl font-black text-emerald-700 block mt-1">{appliedCount}</span>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-teal-600 uppercase">Eligible</span>
          <span className="text-2xl font-black text-teal-700 block mt-1">{eligibleCount}</span>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-rose-600 uppercase">Ineligible</span>
          <span className="text-2xl font-black text-rose-700 block mt-1">{ineligibleCount}</span>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-amber-600 uppercase">Policy Blocked</span>
          <span className="text-2xl font-black text-amber-700 block mt-1">{policyBlockedCount}</span>
        </div>
      </div>

      {/* Filters and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search by candidate name or roll no..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium focus:bg-white"
          />
        </div>

        <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto">
          {["all", "applied", "eligible", "ineligible", "policy_blocked"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold capitalize transition-colors ${
                statusFilter === st
                  ? "bg-slate-900 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {st === "applied" ? `Applied (${appliedCount})` : st.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Eligibility Table */}
      {loading ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500 text-sm">
          Loading evaluation decisions...
        </div>
      ) : filteredDecisions.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500 text-sm">
          No candidates evaluated yet for this drive. Click "Evaluate Candidates" above to compute live status.
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-600 uppercase tracking-wider">
                <th className="px-6 py-3.5">Candidate</th>
                <th className="px-6 py-3.5">Branch & CGPA</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5">Application</th>
                <th className="px-6 py-3.5">Headline Reason</th>
                <th className="px-6 py-3.5 text-right">Trace</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {filteredDecisions.map((d) => (
                <tr
                  key={d.student_id}
                  onClick={() => setSelectedStudent(d)}
                  className="hover:bg-slate-50/80 transition-colors cursor-pointer"
                >
                  <td className="px-6 py-4">
                    <span className="font-bold text-slate-900 block">{d.student_name}</span>
                    <span className="text-xs font-mono text-slate-400 block">{d.roll_no}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-xs font-semibold text-slate-700 block">{d.branch}</span>
                    <span className="text-xs font-mono text-slate-500 block">CGPA: {d.cgpa.toFixed(2)}</span>
                  </td>
                  <td className="px-6 py-4">
                    <Badge
                      variant={
                        d.status === "eligible"
                          ? "success"
                          : d.status === "ineligible"
                          ? "danger"
                          : "warning"
                      }
                    >
                      {d.status.replace("_", " ")}
                    </Badge>
                  </td>
                  <td className="px-6 py-4">
                    {d.has_applied ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                        <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Applied</span>
                      </span>
                    ) : (
                      <span className="text-xs text-slate-400 font-medium">Not Applied</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-xs text-slate-600 max-w-md truncate">
                    {d.reason}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span className="text-xs font-semibold text-brand-600 hover:text-brand-800 flex items-center justify-end gap-1">
                      Inspect Trace <ChevronRight className="w-3.5 h-3.5" />
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Trace Drawer */}
      <Drawer
        isOpen={!!selectedStudent}
        onClose={() => setSelectedStudent(null)}
        title={selectedStudent?.student_name || "Evaluation Trace"}
        subtitle={`Roll No: ${selectedStudent?.roll_no} | Branch: ${selectedStudent?.branch}`}
      >
        {selectedStudent && (
          <div className="space-y-6">
            <div>
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Final Eligibility Verdict
              </span>
              <div className="flex items-center gap-3">
                <Badge
                  variant={
                    selectedStudent.status === "eligible"
                      ? "success"
                      : selectedStudent.status === "ineligible"
                      ? "danger"
                      : "warning"
                  }
                  size="md"
                >
                  {selectedStudent.status.replace("_", " ").toUpperCase()}
                </Badge>
                <span className="text-xs text-slate-600 font-medium">{selectedStudent.reason}</span>
              </div>
            </div>

            <div>
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Drive Application Status
              </span>
              <div className="flex items-center gap-2">
                {selectedStudent.has_applied ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Applied {selectedStudent.applied_at ? `on ${new Date(selectedStudent.applied_at).toLocaleDateString()}` : "for Drive"}</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-xl text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
                    Not Applied
                  </span>
                )}
              </div>
            </div>

            {/* Academic Rule Check Breakdown */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-brand-600" />
                Company Academic Cut-Off Rules
              </h4>
              <div className="space-y-2">
                {selectedStudent.passed_rules.map((rule, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-emerald-50/70 border border-emerald-200 rounded-xl flex items-start gap-2.5 text-xs text-emerald-900"
                  >
                    <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold">{rule}</span>
                      <p className="text-[11px] text-emerald-700">Satisfies target threshold</p>
                    </div>
                  </div>
                ))}

                {selectedStudent.failed_rules.map((rule, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-rose-50/70 border border-rose-200 rounded-xl flex items-start gap-2.5 text-xs text-rose-900"
                  >
                    <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold">{rule}</span>
                      <p className="text-[11px] text-rose-700">Failed threshold criteria</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Policy Clause Citation */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                <Shield className="w-4 h-4 text-indigo-600" />
                Institutional Offer Policy Engine
              </h4>
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1.5 text-slate-700">
                <div className="flex items-center justify-between font-bold text-slate-900">
                  <span>Policy Clause 1.2: One Offer & Out</span>
                  <Badge variant="neutral" size="sm">Standard Rule</Badge>
                </div>
                <p className="text-slate-600 leading-relaxed">
                  "Students who hold an active offer are excluded from regular recruitment drives, unless the opportunity qualifies under the Dream Company exception (&gt; 15 LPA)."
                </p>
              </div>
            </div>
          </div>
        )}
      </Drawer>

      {/* Delete Drive Modal */}
      {deleteModalOpen && currentDrive && (
        <Modal
          isOpen={deleteModalOpen}
          onClose={() => setDeleteModalOpen(false)}
          title={`Permanently Remove Drive: ${currentDrive.company_name}`}
        >
          <div className="space-y-4">
            <p className="text-xs text-slate-600 dark:text-slate-300">
              Removing this company drive will permanently purge candidate applications, eligibility decisions, and slot assignments across all officer and coordinator dashboards.
            </p>
            <div>
              <label className="block text-xs font-bold mb-1 text-slate-800 dark:text-slate-200">
                Reason for Removal (Mandatory):
              </label>
              <textarea
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
                rows={3}
                placeholder="Specify justification for removing this drive..."
                className="w-full text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-rose-500 focus:outline-none"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setDeleteModalOpen(false)}
                className="px-4 py-2 text-xs font-bold text-slate-600 hover:text-slate-800 dark:text-slate-300 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDeleteDrive}
                disabled={deleting}
                className="px-4 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-xl shadow-xs disabled:opacity-50 cursor-pointer"
              >
                {deleting ? "Removing..." : "Confirm Removal"}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
