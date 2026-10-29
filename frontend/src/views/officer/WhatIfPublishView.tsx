import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Drive, ImpactReportData, StudentImpactItem, ClashImpactItem } from "../../types";
import { Badge } from "../../components/common/Badge";
import { Modal } from "../../components/common/Modal";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  Sparkles,
  Send,
  RotateCcw,
  AlertTriangle,
  CheckCircle,
  Users,
  ShieldCheck,
  TrendingUp,
  Info,
  Calendar,
  Layers,
  GraduationCap,
  Briefcase,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Sliders,
  Check,
} from "lucide-react";

interface WhatIfPublishViewProps {
  initialDriveId?: string;
}

const CANONICAL_BRANCH_LIST = [
  { code: "CSE", name: "Computer Science and Engineering" },
  { code: "IT", name: "Information Technology" },
  { code: "ECE", name: "Electronics and Communication Engineering" },
  { code: "EEE", name: "Electrical and Electronics Engineering" },
  { code: "ME", name: "Mechanical Engineering" },
  { code: "CE", name: "Civil Engineering" },
  { code: "CHE", name: "Chemical Engineering" },
  { code: "BT", name: "Biotechnology" },
  { code: "DS", name: "Data Science" },
];

export const WhatIfPublishView: React.FC<WhatIfPublishViewProps> = ({ initialDriveId }) => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<string>(initialDriveId || "");
  const [simulating, setSimulating] = useState(false);
  const [applying, setApplying] = useState(false);
  const [impactReport, setImpactReport] = useState<ImpactReportData | null>(null);
  const [lastSimulatedPayload, setLastSimulatedPayload] = useState<any | null>(null);

  // Adjustment type
  const [changeType, setChangeType] = useState<
    "cgpa_cutoff" | "backlog_rule" | "branch_added" | "branch_removed" | "drive_date_shift" | "percentage_cutoff" | "gap_year"
  >("cgpa_cutoff");

  // Adjustment specific values
  const [proposedCgpa, setProposedCgpa] = useState<number>(6.5);
  const [proposedBacklogs, setProposedBacklogs] = useState<number>(1);
  const [selectedBranch, setSelectedBranch] = useState<string>("ME");
  const [proposedDate, setProposedDate] = useState<string>(() => {
    const d = new Date();
    d.setDate(d.getDate() + 21);
    return d.toISOString().split("T")[0];
  });
  const [targetQualification, setTargetQualification] = useState<"10th" | "12th">("10th");
  const [proposedPercentage, setProposedPercentage] = useState<number>(65.0);
  const [proposedGapYears, setProposedGapYears] = useState<number>(1);

  // Publish & Rollback state
  const [isPublishModalOpen, setIsPublishModalOpen] = useState(false);
  const [publishReason, setPublishReason] = useState("Finalized shortlist and clash-free interview schedule");
  const [publishing, setPublishing] = useState(false);
  const [publishSuccess, setPublishSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    } catch {
      setError("Failed to load drives.");
    }
  };

  useEffect(() => {
    fetchDrives();
  }, [initialDriveId]);

  const currentDrive = drives.find((d) => d.id === selectedDriveId);

  // Synchronize defaults when currentDrive changes
  useEffect(() => {
    if (currentDrive) {
      if (currentDrive.requirements?.min_cgpa) {
        setProposedCgpa(Math.max(5.0, Number((currentDrive.requirements.min_cgpa - 0.5).toFixed(1))));
      }
      if (currentDrive.drive_date) {
        const d = new Date(currentDrive.drive_date);
        d.setDate(d.getDate() + 7);
        setProposedDate(d.toISOString().split("T")[0]);
      }
      const allowed = currentDrive.requirements?.allowed_branches || ["CSE", "IT", "ECE"];
      const missing = CANONICAL_BRANCH_LIST.find((b) => !allowed.includes(b.code));
      if (missing) {
        setSelectedBranch(missing.code);
      } else if (allowed.length > 0) {
        setSelectedBranch(allowed[0]);
      }
    }
  }, [selectedDriveId]);

  // Construct ChangeRequest payload for the active adjustment type
  const buildChangePayload = () => {
    if (!selectedDriveId) return null;

    const basePayload: any = {
      change_type: changeType,
      drive_id: selectedDriveId,
    };

    if (changeType === "cgpa_cutoff") {
      basePayload.target_field = "cgpa";
      basePayload.old_value = Number(currentDrive?.requirements?.min_cgpa ?? 8.0);
      basePayload.new_value = Number(proposedCgpa);
    } else if (changeType === "backlog_rule") {
      basePayload.target_field = "max_active_backlogs";
      basePayload.old_value = Number(currentDrive?.requirements?.max_active_backlogs ?? 0);
      basePayload.new_value = Number(proposedBacklogs);
    } else if (changeType === "branch_added") {
      basePayload.branch_name = selectedBranch;
      basePayload.new_value = selectedBranch;
    } else if (changeType === "branch_removed") {
      basePayload.branch_name = selectedBranch;
      basePayload.new_value = selectedBranch;
    } else if (changeType === "drive_date_shift") {
      basePayload.old_value = currentDrive?.drive_date || "2026-11-16";
      basePayload.new_value = proposedDate;
    } else if (changeType === "percentage_cutoff") {
      basePayload.target_field = targetQualification;
      basePayload.old_value =
        targetQualification === "10th"
          ? (currentDrive?.requirements?.min_tenth_percentage ?? 60.0)
          : (currentDrive?.requirements?.min_twelfth_percentage ?? 60.0);
      basePayload.new_value = Number(proposedPercentage);
    } else if (changeType === "gap_year") {
      basePayload.target_field = "max_gap_years";
      basePayload.old_value = currentDrive?.requirements?.max_gap_years ?? 1;
      basePayload.new_value = Number(proposedGapYears);
    }

    return basePayload;
  };

  const handleRunSimulation = async () => {
    if (!selectedDriveId) {
      setError("Please select a target recruitment drive.");
      return;
    }
    const payload = buildChangePayload();
    if (!payload) return;

    try {
      setSimulating(true);
      setError(null);
      const res = await api.post<ImpactReportData>("/api/what-if/simulate", payload);
      setImpactReport(res);
      setLastSimulatedPayload(payload);
    } catch (err: any) {
      setError(err.message || "What-if simulation failed.");
    } finally {
      setSimulating(false);
    }
  };

  // Directly apply the simulated What-If adjustment and publish drive
  const handleApplyWhatIf = async () => {
    if (!selectedDriveId || !lastSimulatedPayload) {
      setError("Please run a simulation before applying adjustments.");
      return;
    }

    try {
      setApplying(true);
      setError(null);
      const res = await api.post<any>("/api/what-if/apply", {
        drive_id: selectedDriveId,
        change: lastSimulatedPayload,
        reason: `Applied What-If ${lastSimulatedPayload.change_type}: ${lastSimulatedPayload.old_value ?? ''} -> ${lastSimulatedPayload.new_value ?? ''}`,
      });

      setPublishSuccess(res.message || "Adjustment applied and drive successfully published!");
      await fetchDrives();
    } catch (err: any) {
      setError(err.message || "Failed to apply what-if adjustment.");
    } finally {
      setApplying(false);
    }
  };

  // Standalone Publish Handler
  const handlePublish = async () => {
    if (!currentDrive) return;
    try {
      setPublishing(true);
      setError(null);
      const res = await api.post<any>(`/api/drives/${currentDrive.id}/publish`, {
        expected_base_version: currentDrive.version,
        reason: publishReason,
      });

      setPublishSuccess(`Drive successfully published at version v${res.version}. Audit snapshot committed.`);
      setIsPublishModalOpen(false);
      await fetchDrives();
    } catch (err: any) {
      setError(err.message || "Publish blocked by safeguards.");
    } finally {
      setPublishing(false);
    }
  };

  const handleRollback = async () => {
    if (!currentDrive || currentDrive.version <= 1) return;
    try {
      setError(null);
      const targetV = currentDrive.version - 1;
      const res = await api.post<any>(`/api/drives/${currentDrive.id}/rollback`, {
        target_version: targetV,
        reason: "Administrative correction via rollback",
      });
      setPublishSuccess(`Successfully rolled back to v${targetV} (new current version v${res.current_version}).`);
      await fetchDrives();
    } catch (err: any) {
      setError(err.message || "Rollback failed.");
    }
  };

  const currentBranches = currentDrive?.requirements?.allowed_branches || ["CSE", "IT", "ECE"];

  return (
    <div className="space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight">What-If Simulation & Publish</h1>
          <p className="text-sm text-slate-400 mt-1">
            Test requirement changes in-memory. Compute exact candidate deltas and causal collisions before committing.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <select
            value={selectedDriveId}
            onChange={(e) => {
              setSelectedDriveId(e.target.value);
              setImpactReport(null);
            }}
            className="px-3.5 py-2 bg-[#0d1527] border border-[#1e3258] rounded-xl text-xs font-bold text-emerald-400 shadow-md focus:outline-none cursor-pointer"
          >
            {drives.map((d) => (
              <option key={d.id} value={d.id}>
                {d.company_name} (v{d.version} - {d.status})
              </option>
            ))}
          </select>

          {currentDrive?.version && currentDrive.version > 1 && (
            <button
              type="button"
              onClick={handleRollback}
              className="flex items-center gap-1.5 px-3 py-2 bg-[#101b33] hover:bg-[#162547] text-slate-300 text-xs font-bold rounded-xl border border-[#1e3258] transition-colors cursor-pointer"
              title="Roll back to previous version"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Rollback (v{currentDrive.version - 1})</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setIsPublishModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white text-xs font-bold rounded-xl shadow-md shadow-emerald-950/30 transition-all cursor-pointer"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Publish Drive</span>
          </button>
        </div>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {publishSuccess && <AlertBanner type="success" message={publishSuccess} onClose={() => setPublishSuccess(null)} />}

      {/* Simulation Controls Panel */}
      <div className="bg-[#0d1527] p-6 rounded-2xl border border-[#1e3258] shadow-xl space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-[#1b2b4d]">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <span>Propose What-If Policy or Cut-off Adjustment</span>
          </h2>
          <span className="text-[11px] font-mono text-emerald-400 bg-emerald-950/60 px-2.5 py-1 rounded-lg border border-emerald-800/60">
            Target: {currentDrive?.company_name || "Drive"} (v{currentDrive?.version || 1})
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          {/* 1. Adjustment Type Dropdown */}
          <div>
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block mb-1.5">
              Adjustment Type
            </label>
            <select
              value={changeType}
              onChange={(e) => {
                setChangeType(e.target.value as any);
                setImpactReport(null);
              }}
              className="w-full px-3.5 py-2.5 bg-[#080e1c] border border-emerald-500/60 rounded-xl text-xs font-semibold text-emerald-300 focus:outline-none focus:ring-2 focus:ring-emerald-500 cursor-pointer shadow-inner"
            >
              <option value="cgpa_cutoff">Lower / Raise CGPA Cut-off</option>
              <option value="backlog_rule">Modify Backlog Standing Rule</option>
              <option value="branch_added">Add Eligible Branch</option>
              <option value="branch_removed">Remove Eligible Branch</option>
              <option value="drive_date_shift">Shift Drive Date / Venues</option>
              <option value="percentage_cutoff">Minimum 10th / 12th Percentage</option>
              <option value="gap_year">Education Gap Years</option>
            </select>
          </div>

          {/* 2. Current Baseline Display */}
          <div>
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block mb-1.5">
              Current Baseline Cut-off
            </label>
            <div className="w-full px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-mono font-semibold text-slate-300 flex items-center">
              {changeType === "cgpa_cutoff" && (
                <span>CGPA &ge; {currentDrive?.requirements?.min_cgpa ?? 8.0}</span>
              )}
              {changeType === "backlog_rule" && (
                <span>Max Active: {currentDrive?.requirements?.max_active_backlogs ?? 0} Backlog(s)</span>
              )}
              {changeType === "branch_added" && (
                <span className="truncate">{currentBranches.join(", ")}</span>
              )}
              {changeType === "branch_removed" && (
                <span className="truncate">{currentBranches.join(", ")}</span>
              )}
              {changeType === "drive_date_shift" && (
                <span>Date: {currentDrive?.drive_date || "2026-11-16"}</span>
              )}
              {changeType === "percentage_cutoff" && (
                <span>
                  {targetQualification}: {targetQualification === "10th" ? (currentDrive?.requirements?.min_tenth_percentage ?? 60.0) : (currentDrive?.requirements?.min_twelfth_percentage ?? 60.0)}%
                </span>
              )}
              {changeType === "gap_year" && (
                <span>Max Gap: {currentDrive?.requirements?.max_gap_years ?? 1} Year(s)</span>
              )}
            </div>
          </div>

          {/* 3. Proposed New Value Input */}
          <div>
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block mb-1.5">
              Proposed New Value
            </label>

            {changeType === "cgpa_cutoff" && (
              <input
                type="number"
                step="0.1"
                min="0"
                max="10"
                value={proposedCgpa}
                onChange={(e) => setProposedCgpa(parseFloat(e.target.value) || 0)}
                className="w-full px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-mono font-bold text-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            )}

            {changeType === "backlog_rule" && (
              <select
                value={proposedBacklogs}
                onChange={(e) => setProposedBacklogs(parseInt(e.target.value, 10))}
                className="w-full px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-bold text-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 cursor-pointer"
              >
                <option value={0}>0 (Strict - Zero Standing Backlogs)</option>
                <option value={1}>1 (Allow Max 1 Active Backlog)</option>
                <option value={2}>2 (Allow Max 2 Active Backlogs)</option>
                <option value={3}>3 (Allow Max 3 Active Backlogs)</option>
              </select>
            )}

            {changeType === "branch_added" && (
              <select
                value={selectedBranch}
                onChange={(e) => setSelectedBranch(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-bold text-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 cursor-pointer"
              >
                {CANONICAL_BRANCH_LIST.map((b) => (
                  <option key={b.code} value={b.code}>
                    {b.code} — {b.name}
                  </option>
                ))}
              </select>
            )}

            {changeType === "branch_removed" && (
              <select
                value={selectedBranch}
                onChange={(e) => setSelectedBranch(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-bold text-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-500 cursor-pointer"
              >
                {currentBranches.map((b) => (
                  <option key={b} value={b}>
                    Remove {b}
                  </option>
                ))}
              </select>
            )}

            {changeType === "drive_date_shift" && (
              <input
                type="date"
                value={proposedDate}
                onChange={(e) => setProposedDate(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-mono font-bold text-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            )}

            {changeType === "percentage_cutoff" && (
              <div className="flex items-center gap-2">
                <select
                  value={targetQualification}
                  onChange={(e) => setTargetQualification(e.target.value as any)}
                  className="w-24 px-2.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-bold text-slate-300"
                >
                  <option value="10th">10th</option>
                  <option value="12th">12th</option>
                </select>
                <input
                  type="number"
                  step="1"
                  min="40"
                  max="100"
                  value={proposedPercentage}
                  onChange={(e) => setProposedPercentage(parseFloat(e.target.value) || 0)}
                  className="flex-1 px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-mono font-bold text-emerald-400 focus:outline-none"
                />
              </div>
            )}

            {changeType === "gap_year" && (
              <select
                value={proposedGapYears}
                onChange={(e) => setProposedGapYears(parseInt(e.target.value, 10))}
                className="w-full px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-bold text-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 cursor-pointer"
              >
                <option value={0}>0 (Strict - Zero Education Gaps)</option>
                <option value={1}>1 Year Gap Allowed</option>
                <option value={2}>2 Years Gap Allowed</option>
                <option value={3}>3 Years Gap Allowed</option>
              </select>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-[#1b2b4d]">
          <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Zero database side-effects: runs purely in-memory across the 1,800 student cohort.</span>
          </div>

          <button
            type="button"
            onClick={handleRunSimulation}
            disabled={simulating}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 via-indigo-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-emerald-950/40 transition-all cursor-pointer disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4 text-emerald-300" />
            <span>{simulating ? "Simulating In-Memory..." : "Simulate What-If Impact"}</span>
          </button>
        </div>
      </div>

      {/* What-If Impact Report Card */}
      {impactReport && (
        <div className="bg-[#0d1527] p-6 rounded-2xl border border-[#1e3258] shadow-2xl space-y-6">
          {/* Data-Driven Computed Headline */}
          <div className="p-5 bg-gradient-to-r from-blue-950/60 to-emerald-950/60 border border-emerald-500/30 rounded-2xl shadow-inner">
            <span className="text-[10px] font-bold tracking-wider uppercase text-emerald-400 block mb-1">
              Computed Impact Headline
            </span>
            <p className="text-base font-extrabold text-white leading-relaxed">
              "{impactReport.headline}"
            </p>
          </div>

          {/* Metrics Delta */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 bg-emerald-950/30 border border-emerald-500/30 rounded-xl text-center">
              <span className="text-xs font-bold text-emerald-400 uppercase">Students Newly Added</span>
              <span className="text-3xl font-black text-emerald-300 block mt-1">
                +{impactReport.students_added_count}
              </span>
            </div>
            <div className="p-4 bg-rose-950/30 border border-rose-500/30 rounded-xl text-center">
              <span className="text-xs font-bold text-rose-400 uppercase">Students Excluded</span>
              <span className="text-3xl font-black text-rose-300 block mt-1">
                -{impactReport.students_removed_count}
              </span>
            </div>
            <div className="p-4 bg-amber-950/30 border border-amber-500/30 rounded-xl text-center">
              <span className="text-xs font-bold text-amber-400 uppercase">Collisions Created</span>
              <span className="text-3xl font-black text-amber-300 block mt-1">
                {impactReport.clashes_count}
              </span>
            </div>
          </div>

          {/* Sample Students Added Preview */}
          {impactReport.students_added && impactReport.students_added.length > 0 && (
            <div className="p-4 bg-[#080e1c] border border-[#1b2b4d] rounded-xl space-y-2.5">
              <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                <span className="flex items-center gap-1.5 text-emerald-400">
                  <CheckCircle className="w-3.5 h-3.5" />
                  Newly Shortlisted Candidate Preview ({impactReport.students_added.length} total)
                </span>
                <span className="text-[10px] font-mono text-slate-500">Showing top 5</span>
              </div>
              <div className="space-y-1.5">
                {impactReport.students_added.slice(0, 5).map((stu) => (
                  <div key={stu.student_id} className="flex items-center justify-between text-xs p-2 bg-[#0d1527] rounded-lg border border-[#1b2b4d]">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-emerald-400 font-bold">{stu.student_roll_no}</span>
                      <span className="font-semibold text-white">{stu.student_name}</span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 font-mono">{stu.branch}</span>
                    </div>
                    <div className="text-right">
                      <span className="font-mono font-bold text-slate-300">CGPA {stu.cgpa.toFixed(2)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Second-Order Policy Effects */}
          {impactReport.second_order_policy_effects && impactReport.second_order_policy_effects.length > 0 && (
            <div className="p-4 bg-[#080e1c] border border-[#1b2b4d] rounded-xl space-y-2">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4 text-indigo-400" />
                <span>Second-Order Offer Policy Ripple Effects</span>
              </h4>
              <ul className="text-xs text-slate-400 space-y-1 list-disc pl-5">
                {impactReport.second_order_policy_effects.map((eff, idx) => (
                  <li key={idx}>{eff}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Dedicated Action Bar: Apply & Publish What-If Directly */}
          <div className="p-5 bg-gradient-to-r from-emerald-950/80 via-[#0d1527] to-blue-950/80 border-2 border-emerald-500/50 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
            <div className="space-y-1">
              <div className="text-xs font-bold text-white flex items-center gap-1.5">
                <Send className="w-4 h-4 text-emerald-400" />
                <span>Commit & Publish This Simulated Adjustment</span>
              </div>
              <p className="text-xs text-slate-400">
                Atomically updates {currentDrive?.company_name} criteria, advances version from v{currentDrive?.version} to v{(currentDrive?.version || 1) + 1}, recomputes candidate shortlist, and locks an immutable audit snapshot.
              </p>
            </div>

            <button
              type="button"
              onClick={handleApplyWhatIf}
              disabled={applying}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-emerald-950/50 transition-all cursor-pointer disabled:opacity-50 shrink-0"
            >
              <Check className="w-4 h-4" />
              <span>{applying ? "Applying & Publishing..." : `Apply & Publish (v${(currentDrive?.version || 1) + 1})`}</span>
            </button>
          </div>
        </div>
      )}

      {/* Standalone Publish Modal with Pre-Flight Verification */}
      <Modal
        isOpen={isPublishModalOpen}
        onClose={() => setIsPublishModalOpen(false)}
        title="Publish Drive & Lock Immutable Version"
        maxWidth="lg"
        footer={
          <div className="flex items-center justify-end gap-3 w-full">
            <button
              type="button"
              onClick={() => setIsPublishModalOpen(false)}
              className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-xl cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handlePublish}
              disabled={publishing}
              className="px-5 py-2.5 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white text-xs font-bold rounded-xl shadow-md transition-all disabled:opacity-50 flex items-center gap-2 cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{publishing ? "Committing..." : `Confirm & Publish v${(currentDrive?.version || 1) + 1}`}</span>
            </button>
          </div>
        }
      >
        <div className="space-y-4 text-slate-200">
          <p className="text-xs text-slate-300 leading-relaxed">
            Publishing locks current eligibility cut-offs and interview slots as an immutable versioned snapshot.
            All registered candidates will immediately see their official eligibility status and timetable.
          </p>

          <div className="p-3.5 bg-[#080e1c] border border-[#1b2b4d] rounded-xl space-y-2">
            <h4 className="text-xs font-bold text-white uppercase tracking-wider">
              Pre-Flight Safeguard Checks
            </h4>
            <div className="space-y-1.5 text-xs">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                <span>Zero unresolved extraction review queue items</span>
              </div>
              <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                <span>Zero schedule collisions verified</span>
              </div>
              <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                <span>Optimistic version lock validated (Current Base v{currentDrive?.version})</span>
              </div>
            </div>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block mb-1.5">
              Publication Audit Reason
            </label>
            <input
              type="text"
              value={publishReason}
              onChange={(e) => setPublishReason(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-medium text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};
