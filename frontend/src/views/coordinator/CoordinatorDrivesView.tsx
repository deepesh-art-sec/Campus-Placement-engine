import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Drive } from "../../types";
import { Badge } from "../../components/common/Badge";
import { Modal } from "../../components/common/Modal";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  Briefcase,
  Calendar,
  Building,
  Flag,
  MessageSquare,
  Clock,
  Layers,
  Search,
  CheckCircle,
  AlertTriangle,
  Info,
  Send,
  Eye,
} from "lucide-react";

export const CoordinatorDrivesView: React.FC = () => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Flag Problem / Doubt Modal State
  const [flagModalDrive, setFlagModalDrive] = useState<Drive | null>(null);
  const [flagTitle, setFlagTitle] = useState("Rule Ambiguity: CGPA Cutoff Discrepancy");
  const [flagDescription, setFlagDescription] = useState("");
  const [flagSuccess, setFlagSuccess] = useState<string | null>(null);
  const [flagSubmitting, setFlagSubmitting] = useState(false);

  // Drive Detail Inspection Modal
  const [inspectDrive, setInspectDrive] = useState<Drive | null>(null);
  const [draftNote, setDraftNote] = useState("");
  const [notesList, setNotesList] = useState<string[]>([
    "Recruiter confirmed 2 interview panels required for Round 2.",
    "Draft circular sent to batch WhatsApp group for preliminary visibility.",
  ]);

  const fetchDrives = async () => {
    try {
      setLoading(true);
      const res = await api.get<Drive[]>("/api/drives");
      setDrives(res || []);
    } catch (err: any) {
      setError("Failed to load drives.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDrives();
  }, []);

  const handleOpenFlagModal = (drive: Drive) => {
    setFlagModalDrive(drive);
    setFlagTitle(`Cut-off / Rule Doubt for ${drive.company_name}`);
    setFlagDescription("");
    setFlagSuccess(null);
  };

  const handleSubmitFlag = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!flagModalDrive || !flagDescription.trim()) return;

    try {
      setFlagSubmitting(true);
      await api.post("/api/coordinator/requests", {
        request_type: "rule_doubt",
        title: flagTitle,
        description: flagDescription,
        target_id: flagModalDrive.id,
        payload: {
          company_name: flagModalDrive.company_name,
          drive_date: flagModalDrive.drive_date,
        },
      });

      const todayStr = new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
      setFlagSuccess(`Problem flagged to Officer on ${todayStr}. Awaiting clarification.`);
      setFlagDescription("");
      setTimeout(() => {
        setFlagModalDrive(null);
      }, 2000);
    } catch (err: any) {
      setError(err.message || "Failed to flag problem.");
    } finally {
      setFlagSubmitting(false);
    }
  };

  const handleAddDraftNote = (e: React.FormEvent) => {
    e.preventDefault();
    if (!draftNote.trim()) return;
    setNotesList((prev) => [draftNote.trim(), ...prev]);
    setDraftNote("");
  };

  const getSourceBadge = (drive: Drive) => {
    if (drive.company_name.toLowerCase().includes("imats")) {
      return (
        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-950 text-blue-300 border border-blue-800">
          Source: IMATS Synced
        </span>
      );
    }
    if (drive.version > 1) {
      return (
        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-950 text-purple-300 border border-purple-800">
          Source: NLP Extracted
        </span>
      );
    }
    return (
      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-300">
        Source: Manual Entry
      </span>
    );
  };

  const filtered = drives.filter(
    (d) =>
      d.company_name.toLowerCase().includes(search.toLowerCase()) ||
      (d.job_role && d.job_role.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Recruitment Drives (Read & Prepare)</h1>
            <Badge variant="brand">View & Flag Authority</Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Inspect drive criteria, verify source provenance badges, add draft notes, and flag doubts to the Officer.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold text-slate-400 bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200">
            Rule Editing & Publishing Locked
          </span>
        </div>
      </div>

      {/* Warning on restricted action */}
      <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl flex items-center justify-between text-xs text-amber-900">
        <div className="flex items-center gap-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            <strong>Read & Prepare Zone:</strong> Publishing drives or modifying cut-off AST rules is strictly locked to Officer roles. If a requirement looks inconsistent, use the "Flag Problem" tool.
          </span>
        </div>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}

      {/* Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search drives by company or role..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium focus:bg-white"
          />
        </div>

        <span className="text-xs text-slate-500 font-medium">
          Showing {filtered.length} of {drives.length} drives
        </span>
      </div>

      {/* Drive Grid */}
      {loading ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500 text-sm animate-pulse">
          Loading drives...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map((d) => (
            <div
              key={d.id}
              className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5 flex flex-col justify-between space-y-4 hover:border-brand-300 transition-all"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center text-slate-600">
                      <Building className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-900 text-sm leading-tight">{d.company_name}</h3>
                      <span className="text-xs text-slate-500">{d.job_role || "Engineering Trainee"}</span>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-bold">
                    v{d.version}
                  </span>
                </div>

                <div className="mt-3 flex items-center justify-between">
                  {getSourceBadge(d)}
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full capitalize ${
                      d.status === "published"
                        ? "bg-emerald-100 text-emerald-800"
                        : d.status === "ready"
                        ? "bg-blue-100 text-blue-800"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {d.status.replace("_", " ")}
                  </span>
                </div>

                <div className="mt-3 pt-3 border-t border-slate-100 grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-[10px] font-bold uppercase text-slate-400 block">Package</span>
                    <span className="font-mono font-bold text-slate-900">{d.ctc_lpa ? `${d.ctc_lpa} LPA` : "Undisclosed"}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold uppercase text-slate-400 block">Date</span>
                    <span className="font-medium text-slate-700">{new Date(d.drive_date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons for Coordinator */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={() => setInspectDrive(d)}
                  className="flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg cursor-pointer"
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>Inspect</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleOpenFlagModal(d)}
                  className="flex items-center gap-1 px-2.5 py-1 text-xs font-bold text-amber-800 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-lg cursor-pointer"
                  title="Flag a problem or rule inconsistency to the Officer"
                >
                  <Flag className="w-3.5 h-3.5 text-amber-600" />
                  <span>Flag Problem</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Flag Problem / Doubt Modal */}
      {flagModalDrive && (
        <Modal
          isOpen={!!flagModalDrive}
          onClose={() => setFlagModalDrive(null)}
          title={`Flag Problem to Officer: ${flagModalDrive.company_name}`}
        >
          <form onSubmit={handleSubmitFlag} className="space-y-4 text-xs">
            {flagSuccess && <AlertBanner type="success" message={flagSuccess} onClose={() => setFlagSuccess(null)} />}

            <p className="text-slate-600">
              Coordinators can flag cut-off inconsistencies, ambiguous JD sentences, or round conflicts. The Placement Officer will review and respond directly.
            </p>

            <div>
              <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">Inquiry / Problem Title</label>
              <input
                type="text"
                required
                value={flagTitle}
                onChange={(e) => setFlagTitle(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-medium focus:bg-white"
              />
            </div>

            <div>
              <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                Detailed Concern <span className="text-rose-500">*</span>
              </label>
              <textarea
                rows={3}
                required
                placeholder="e.g. Cut-off states 7.5 CGPA in JD circular but company email says 7.0 for CSE. Please verify with recruiter..."
                value={flagDescription}
                onChange={(e) => setFlagDescription(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white"
              />
            </div>

            <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setFlagModalDrive(null)}
                className="px-3 py-1.5 text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={flagSubmitting || !flagDescription.trim()}
                className="flex items-center gap-1.5 px-4 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded-xl shadow-xs cursor-pointer disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{flagSubmitting ? "Flagging..." : "Submit to Officer"}</span>
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Inspect Drive & Draft Notes Modal */}
      {inspectDrive && (
        <Modal
          isOpen={!!inspectDrive}
          onClose={() => setInspectDrive(null)}
          title={`Drive Inspection: ${inspectDrive.company_name}`}
        >
          <div className="space-y-5 text-xs">
            <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div>
                <span className="text-[10px] font-bold uppercase text-slate-400 block">Job Role</span>
                <span className="font-semibold text-slate-900">{inspectDrive.job_role || "Engineering Graduate Trainee"}</span>
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase text-slate-400 block">Package CTC</span>
                <span className="font-mono font-bold text-slate-900">{inspectDrive.ctc_lpa} LPA</span>
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase text-slate-400 block">Drive Date</span>
                <span className="font-medium text-slate-700">{inspectDrive.drive_date}</span>
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase text-slate-400 block">Mode</span>
                <span className="capitalize text-slate-700">{inspectDrive.mode.replace("_", " ")}</span>
              </div>
            </div>

            {/* Coordinator Draft Notes */}
            <div className="space-y-3 pt-2 border-t border-slate-100">
              <h4 className="font-bold text-slate-900 flex items-center gap-1.5">
                <MessageSquare className="w-4 h-4 text-brand-600" />
                Operational Notes & Preparation Log
              </h4>

              <form onSubmit={handleAddDraftNote} className="flex gap-2">
                <input
                  type="text"
                  placeholder="Add a preparation note for this drive..."
                  value={draftNote}
                  onChange={(e) => setDraftNote(e.target.value)}
                  className="flex-1 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white text-xs"
                />
                <button
                  type="submit"
                  className="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white font-bold rounded-xl cursor-pointer shrink-0"
                >
                  Add Note
                </button>
              </form>

              <div className="space-y-1.5 max-h-40 overflow-y-auto custom-scrollbar">
                {notesList.map((note, idx) => (
                  <div key={idx} className="p-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 text-[11px]">
                    {note}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
