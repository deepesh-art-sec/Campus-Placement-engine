import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Drive, EligibilityDecisionItem } from "../../types";
import { Badge } from "../../components/common/Badge";
import { Drawer } from "../../components/common/Drawer";
import { Modal } from "../../components/common/Modal";
import {
  CheckCircle,
  XCircle,
  Search,
  Filter,
  Clock,
  Download,
  Eye,
  HelpCircle,
  FileCheck,
  ChevronRight,
  Shield,
  Layers,
  Sparkles,
} from "lucide-react";

interface CoordinatorEligibilityViewProps {
  initialDriveId?: string;
}

export const CoordinatorEligibilityView: React.FC<CoordinatorEligibilityViewProps> = ({
  initialDriveId,
}) => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<string>(initialDriveId || "");
  const [decisions, setDecisions] = useState<EligibilityDecisionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");

  // Explanation Reader Modal (To show or read to students)
  const [explainingStudent, setExplainingStudent] = useState<EligibilityDecisionItem | null>(null);

  useEffect(() => {
    const fetchDrives = async () => {
      try {
        const res = await api.get<Drive[]>("/api/drives");
        setDrives(res || []);
        if (res.length > 0 && !selectedDriveId) {
          setSelectedDriveId(initialDriveId || res[0].id);
        }
      } catch {
        // Fallback
      }
    };
    fetchDrives();
  }, [initialDriveId]);

  const fetchDecisions = async (driveId: string) => {
    if (!driveId) return;
    try {
      setLoading(true);
      const res = await api.get<EligibilityDecisionItem[]>(`/api/eligibility/decisions/${driveId}`);
      setDecisions(res || []);
    } catch {
      setDecisions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDriveId) fetchDecisions(selectedDriveId);
  }, [selectedDriveId]);

  const handleExportCsv = () => {
    window.open(`/api/export/shortlist/${selectedDriveId}?as_csv=true`, "_blank");
  };

  const selectedDrive = drives.find((d) => d.id === selectedDriveId);

  const filtered = decisions.filter((d) => {
    const matchesSearch =
      d.student_name.toLowerCase().includes(search.toLowerCase()) ||
      d.roll_no.toLowerCase().includes(search.toLowerCase()) ||
      d.branch.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "all" || d.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const eligibleCount = decisions.filter((d) => d.status === "eligible").length;
  const ineligibleCount = decisions.filter((d) => d.status === "ineligible").length;
  const policyBlockedCount = decisions.filter((d) => d.status === "policy_blocked").length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Eligibility Explainer List</h1>
            <Badge variant="brand">Student Inquiries Desk</Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Read-only evaluation records. Use the one-line plain language explanations to answer candidate inquiries at the placement desk.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={selectedDriveId}
            onChange={(e) => setSelectedDriveId(e.target.value)}
            className="px-3.5 py-2 bg-white border border-slate-200 rounded-xl text-xs font-bold text-slate-800 shadow-xs cursor-pointer"
          >
            {drives.map((d) => (
              <option key={d.id} value={d.id}>
                {d.company_name} ({d.ctc_lpa} LPA)
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={handleExportCsv}
            disabled={!selectedDriveId}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold rounded-xl shadow-xs transition-colors cursor-pointer disabled:opacity-50"
            title="Download shortlist CSV"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase">Total Evaluated</span>
          <span className="text-2xl font-black text-slate-900 block mt-1">{decisions.length}</span>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-emerald-600 uppercase">Eligible</span>
          <span className="text-2xl font-black text-emerald-700 block mt-1">{eligibleCount}</span>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-rose-600 uppercase">Academically Ineligible</span>
          <span className="text-2xl font-black text-rose-700 block mt-1">{ineligibleCount}</span>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-amber-600 uppercase">Policy Blocked</span>
          <span className="text-2xl font-black text-amber-700 block mt-1">{policyBlockedCount}</span>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search candidate name, roll no, or branch..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium focus:bg-white"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {["all", "eligible", "ineligible", "policy_blocked"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold capitalize transition-colors cursor-pointer ${
                statusFilter === st ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {st.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500 text-sm animate-pulse">
          Loading candidate eligibility records...
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500 text-sm">
          No candidate evaluations match your filter criteria.
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
                <th className="px-5 py-3.5">Candidate</th>
                <th className="px-5 py-3.5">Branch & CGPA</th>
                <th className="px-5 py-3.5">Verdict Status</th>
                <th className="px-5 py-3.5">One-Line Headline Explanation</th>
                <th className="px-5 py-3.5 text-right">Inquiry Card</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((d) => (
                <tr
                  key={d.student_id}
                  onClick={() => setExplainingStudent(d)}
                  className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                >
                  <td className="px-5 py-3.5">
                    <span className="font-bold text-slate-900 block group-hover:text-brand-600">{d.student_name}</span>
                    <span className="text-[11px] font-mono text-slate-400">{d.roll_no}</span>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="text-slate-700 block">{d.branch}</span>
                    <span className="font-mono text-slate-500">CGPA: {d.cgpa.toFixed(2)}</span>
                  </td>
                  <td className="px-5 py-3.5">
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
                  <td className="px-5 py-3.5 text-slate-700 font-medium max-w-md truncate">
                    {d.reason}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <span className="font-bold text-brand-600 hover:text-brand-800 flex items-center justify-end gap-1">
                      Show Explanation <ChevronRight className="w-3.5 h-3.5" />
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* One-Line Explanation Modal (Show to Student) */}
      {explainingStudent && (
        <Modal
          isOpen={!!explainingStudent}
          onClose={() => setExplainingStudent(null)}
          title={`Student Inquiry Explanation: ${explainingStudent.student_name}`}
        >
          <div className="space-y-5 text-xs">
            {/* Student Badge Card */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-black text-slate-900 text-sm">{explainingStudent.student_name}</h4>
                  <span className="text-slate-500 font-mono">Roll: {explainingStudent.roll_no} • {explainingStudent.branch}</span>
                </div>
                <Badge
                  variant={
                    explainingStudent.status === "eligible"
                      ? "success"
                      : explainingStudent.status === "ineligible"
                      ? "danger"
                      : "warning"
                  }
                  size="md"
                >
                  {explainingStudent.status.replace("_", " ").toUpperCase()}
                </Badge>
              </div>
              <div className="text-[11px] text-slate-500 font-mono">
                B.Tech CGPA: {explainingStudent.cgpa.toFixed(2)} • Drive: {selectedDrive?.company_name}
              </div>
            </div>

            {/* Read to Student Card */}
            <div className="p-4 bg-emerald-50/70 border border-emerald-300 rounded-xl space-y-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 block">
                Official Placement Cell Explanation (Read to Student):
              </span>
              <p className="text-sm font-semibold text-emerald-950 leading-relaxed italic">
                "{explainingStudent.reason}"
              </p>
            </div>

            {/* Rule-by-rule checks */}
            <div className="space-y-2">
              <h5 className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Criteria Breakdown:</h5>
              {explainingStudent.passed_rules.map((r, i) => (
                <div key={i} className="p-2 bg-emerald-50 text-emerald-900 border border-emerald-200 rounded-lg flex items-center gap-2">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <span>{r} (Satisfied)</span>
                </div>
              ))}
              {explainingStudent.failed_rules.map((r, i) => (
                <div key={i} className="p-2 bg-rose-50 text-rose-900 border border-rose-200 rounded-lg flex items-center gap-2">
                  <XCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                  <span>{r} (Failed Requirement)</span>
                </div>
              ))}
            </div>

            <div className="pt-2 flex justify-end border-t border-slate-100">
              <button
                type="button"
                onClick={() => setExplainingStudent(null)}
                className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-xl cursor-pointer"
              >
                Close Inquiry Card
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
