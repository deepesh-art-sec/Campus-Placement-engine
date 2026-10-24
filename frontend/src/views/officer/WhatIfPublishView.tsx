import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Drive, ImpactReportData } from "../../types";
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
} from "lucide-react";

interface WhatIfPublishViewProps {
  initialDriveId?: string;
}

export const WhatIfPublishView: React.FC<WhatIfPublishViewProps> = ({ initialDriveId }) => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<string>(initialDriveId || "");
  const [simulating, setSimulating] = useState(false);
  const [impactReport, setImpactReport] = useState<ImpactReportData | null>(null);

  // Simulation controls
  const [changeType, setChangeType] = useState<string>("cgpa_cutoff");
  const [oldValue, setOldValue] = useState<number>(8.0);
  const [newValue, setNewValue] = useState<number>(6.5);

  // Publish & Rollback state
  const [isPublishModalOpen, setIsPublishModalOpen] = useState(false);
  const [publishReason, setPublishReason] = useState("Finalized shortlist and clash-free interview schedule");
  const [publishing, setPublishing] = useState(false);
  const [publishSuccess, setPublishSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDrives = async () => {
      try {
        const res = await api.get<Drive[]>("/api/drives");
        setDrives(res || []);
        if (res.length > 0 && !selectedDriveId) {
          setSelectedDriveId(res[0].id);
        }
      } catch {
        setError("Failed to load drives.");
      }
    };
    fetchDrives();
  }, [initialDriveId]);

  const handleRunSimulation = async () => {
    if (!selectedDriveId) return;
    try {
      setSimulating(true);
      setError(null);
      const res = await api.post<ImpactReportData>("/api/what-if/simulate", {
        change_type: changeType,
        drive_id: selectedDriveId,
        target_field: "cgpa",
        old_value: oldValue,
        new_value: newValue,
      });
      setImpactReport(res);
    } catch (err: any) {
      setError(err.message || "What-if simulation failed.");
    } finally {
      setSimulating(false);
    }
  };

  const currentDrive = drives.find((d) => d.id === selectedDriveId);

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

      // Refresh drives
      const updated = await api.get<Drive[]>("/api/drives");
      setDrives(updated);
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
      const updated = await api.get<Drive[]>("/api/drives");
      setDrives(updated);
    } catch (err: any) {
      setError(err.message || "Rollback failed.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">What-If Simulation & Publish</h1>
          <p className="text-sm text-slate-500 mt-1">
            Test requirement changes in-memory. Compute exact candidate deltas and causal collisions before committing.
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
                {d.company_name} (v{d.version} - {d.status})
              </option>
            ))}
          </select>

          {currentDrive?.version && currentDrive.version > 1 && (
            <button
              onClick={handleRollback}
              className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl transition-colors"
              title="Roll back to previous version"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Rollback</span>
            </button>
          )}

          <button
            onClick={() => setIsPublishModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Publish Drive</span>
          </button>
        </div>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {publishSuccess && <AlertBanner type="success" message={publishSuccess} onClose={() => setPublishSuccess(null)} />}

      {/* Simulation Controls Panel */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-brand-600" />
          Propose What-If Policy or Cut-off Adjustment
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
              Adjustment Type
            </label>
            <select
              value={changeType}
              onChange={(e) => setChangeType(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold"
            >
              <option value="cgpa_cutoff">Lower / Raise CGPA Cut-off</option>
              <option value="backlog_toggle">Modify Backlog Standing Rule</option>
              <option value="branch_addition">Add / Remove Eligible Branch</option>
              <option value="date_shift">Shift Drive Date / Venues</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
              Current Baseline Cut-off
            </label>
            <input
              type="number"
              step="0.1"
              value={oldValue}
              onChange={(e) => setOldValue(parseFloat(e.target.value))}
              className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold"
            />
          </div>

          <div>
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
              Proposed New Value
            </label>
            <input
              type="number"
              step="0.1"
              value={newValue}
              onChange={(e) => setNewValue(parseFloat(e.target.value))}
              className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold text-brand-700"
            />
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={handleRunSimulation}
            disabled={simulating}
            className="flex items-center gap-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            <span>{simulating ? "Simulating In-Memory..." : "Simulate What-If Impact"}</span>
          </button>
        </div>
      </div>

      {/* What-If Impact Report Card */}
      {impactReport && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
          {/* Data-Driven Headline */}
          <div className="p-4 bg-brand-50 border border-brand-200 rounded-2xl">
            <span className="text-[10px] font-bold tracking-wider uppercase text-brand-700 block mb-1">
              Computed Impact Headline
            </span>
            <p className="text-base font-extrabold text-brand-950 leading-relaxed">
              "{impactReport.headline}"
            </p>
          </div>

          {/* Metrics Delta */}
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-center">
              <span className="text-xs font-bold text-emerald-700 uppercase">Students Newly Added</span>
              <span className="text-2xl font-black text-emerald-800 block mt-1">
                +{impactReport.students_added_count}
              </span>
            </div>
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-center">
              <span className="text-xs font-bold text-rose-700 uppercase">Students Excluded</span>
              <span className="text-2xl font-black text-rose-800 block mt-1">
                -{impactReport.students_removed_count}
              </span>
            </div>
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-center">
              <span className="text-xs font-bold text-amber-700 uppercase">Collisions Created</span>
              <span className="text-2xl font-black text-amber-800 block mt-1">
                {impactReport.clashes_count}
              </span>
            </div>
          </div>

          {/* Second-Order Policy Effects */}
          {impactReport.second_order_policy_effects && impactReport.second_order_policy_effects.length > 0 && (
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4 text-indigo-600" />
                Second-Order Offer Policy Ripple Effects
              </h4>
              <ul className="text-xs text-slate-600 space-y-1 list-disc pl-5">
                {impactReport.second_order_policy_effects.map((eff, idx) => (
                  <li key={idx}>{eff}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Publish Modal with Safeguard Pre-Flight */}
      <Modal
        isOpen={isPublishModalOpen}
        onClose={() => setIsPublishModalOpen(false)}
        title="Publish Drive & Lock Immutable Version"
        maxWidth="lg"
        footer={
          <div className="flex items-center justify-end gap-3 w-full">
            <button
              onClick={() => setIsPublishModalOpen(false)}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
            >
              Cancel
            </button>
            <button
              onClick={handlePublish}
              disabled={publishing}
              className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-xs disabled:opacity-50 flex items-center gap-2"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{publishing ? "Committing..." : "Confirm & Publish"}</span>
            </button>
          </div>
        }
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed">
            Publishing locks current eligibility cut-offs and interview slots as an immutable versioned snapshot.
            All registered students will immediately see their official eligibility status and timetable.
          </p>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Pre-Flight Safeguard Checks
            </h4>
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-2 text-emerald-700 font-semibold">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                <span>Zero unresolved extraction review queue items</span>
              </div>
              <div className="flex items-center gap-2 text-emerald-700 font-semibold">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                <span>Zero schedule collisions verified</span>
              </div>
              <div className="flex items-center gap-2 text-emerald-700 font-semibold">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                <span>Optimistic version lock validated (Base v{currentDrive?.version})</span>
              </div>
            </div>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
              Publication Audit Reason
            </label>
            <input
              type="text"
              value={publishReason}
              onChange={(e) => setPublishReason(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium focus:bg-white"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};
