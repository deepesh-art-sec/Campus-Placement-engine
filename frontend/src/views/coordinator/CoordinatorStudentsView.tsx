import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Student } from "../../types";
import { Badge } from "../../components/common/Badge";
import { Drawer } from "../../components/common/Drawer";
import { Modal } from "../../components/common/Modal";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  Users,
  Search,
  RefreshCw,
  Edit2,
  FileText,
  Mail,
  Phone,
  CheckCircle,
  Clock,
  Briefcase,
  AlertTriangle,
  Info,
  ChevronRight,
  Shield,
  Layers,
  Send,
  Download,
} from "lucide-react";

interface DriveStatusItem {
  drive_id: string;
  company_name: string;
  ctc_lpa: number;
  drive_date: string;
  mode: string;
  status: "eligible" | "ineligible" | "policy_blocked" | "needs_review";
  headline_reason: string;
}

const CANONICAL_BRANCH_MAP: Record<string, string> = {
  CSE: "Computer Science and Engineering",
  IT: "Information Technology",
  ECE: "Electronics and Communication Engineering",
  EEE: "Electrical and Electronics Engineering",
  ME: "Mechanical Engineering",
  CE: "Civil Engineering",
  CHE: "Chemical Engineering",
  BT: "Biotechnology",
  DS: "Data Science",
};

export const CoordinatorStudentsView: React.FC = () => {
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [branchFilter, setBranchFilter] = useState("all");
  const [minCgpa, setMinCgpa] = useState<number>(0.0);
  const [backlogFilter, setBacklogFilter] = useState("all");
  const [offerFilter, setOfferFilter] = useState("all");
  const [exportingCsv, setExportingCsv] = useState(false);

  // Detail Drawer State
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [driveStatuses, setDriveStatuses] = useState<DriveStatusItem[]>([]);
  const [loadingStatuses, setLoadingStatuses] = useState(false);
  const [drawerTab, setDrawerTab] = useState<"academics" | "drives" | "contact" | "correction">("academics");

  // Contact Direct Edit State
  const [contactEmail, setContactEmail] = useState("");
  const [contactPhone, setContactPhone] = useState("+91 9876543210");
  const [savingContact, setSavingContact] = useState(false);
  const [contactSuccess, setContactSuccess] = useState<string | null>(null);

  // Correction Request State
  const [reqField, setReqField] = useState("cgpa");
  const [reqNewValue, setReqNewValue] = useState("");
  const [reqReason, setReqReason] = useState("");
  const [reqSupportingNote, setReqSupportingNote] = useState("");
  const [submittingReq, setSubmittingReq] = useState(false);
  const [reqSuccess, setReqSuccess] = useState<string | null>(null);
  const [reqError, setReqError] = useState<string | null>(null);

  const fetchStudents = async () => {
    try {
      setLoading(true);
      const res = await api.get<{ items: Student[]; total: number }>("/api/students?limit=2500");
      setStudents(res.items || []);
    } catch {
      setStudents([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, []);

  const handleOpenStudent = async (student: Student) => {
    setSelectedStudent(student);
    setContactEmail(student.email || "");
    setContactSuccess(null);
    setReqSuccess(null);
    setReqError(null);
    setReqNewValue("");
    setReqReason("");
    setReqSupportingNote("");
    setDrawerTab("academics");

    try {
      setLoadingStatuses(true);
      const res = await api.get<DriveStatusItem[]>(`/api/students/${student.id}/drive-statuses`);
      setDriveStatuses(res || []);
    } catch {
      setDriveStatuses([]);
    } finally {
      setLoadingStatuses(false);
    }
  };

  // Direct Contact Update (Allowed for Coordinator)
  const handleSaveContact = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStudent) return;
    try {
      setSavingContact(true);
      setContactSuccess(null);
      await api.patch(`/api/students/${selectedStudent.id}/contact`, {
        email: contactEmail,
        phone: contactPhone,
      });
      setContactSuccess("Contact details updated directly.");
      fetchStudents();
    } catch (err: any) {
      // Error handled
    } finally {
      setSavingContact(false);
    }
  };

  // Raise Correction Request to Officer (for Marks, Backlogs, Gaps, Offers)
  const handleRaiseCorrectionRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStudent) return;
    if (!reqReason.trim() || !reqNewValue.trim()) {
      setReqError("Please specify the requested new value and mandatory justification reason.");
      return;
    }

    try {
      setSubmittingReq(true);
      setReqError(null);
      const payload: Record<string, any> = {};
      payload[reqField] = reqNewValue;
      payload["old_value"] = (selectedStudent as any)[reqField] ?? "N/A";
      payload["supporting_note"] = reqSupportingNote;

      const res = await api.post<any>("/api/coordinator/requests", {
        request_type: "student_data_correction",
        title: `Data Correction: ${selectedStudent.roll_no} (${reqField.toUpperCase()})`,
        description: reqReason,
        target_id: selectedStudent.id,
        payload: payload,
      });

      const todayStr = new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
      setReqSuccess(`Requested by you on ${todayStr}. Forwarded to the Placement Officer for verification & approval.`);
      setReqReason("");
      setReqSupportingNote("");
      setReqNewValue("");
    } catch (err: any) {
      setReqError(err.message || "Failed to submit correction request.");
    } finally {
      setSubmittingReq(false);
    }
  };

  const handleExportCsv = async () => {
    try {
      setExportingCsv(true);
      const url = branchFilter && branchFilter !== "all"
        ? `/api/students/export/csv?branch=${encodeURIComponent(branchFilter)}`
        : "/api/students/export/csv";
      const response = await fetch(url, {
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error(`Failed to export student CSV (HTTP ${response.status})`);
      }
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = `student_academic_roster_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch {
      window.open("/api/students/export/csv", "_blank");
    } finally {
      setExportingCsv(false);
    }
  };

  const filtered = students.filter((s) => {
    const matchesSearch =
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.roll_no.toLowerCase().includes(search.toLowerCase());
    const matchesBranch =
      branchFilter === "all" ||
      s.branch === branchFilter ||
      CANONICAL_BRANCH_MAP[s.branch] === branchFilter ||
      (CANONICAL_BRANCH_MAP[branchFilter] && s.branch === CANONICAL_BRANCH_MAP[branchFilter]);
    const matchesCgpa = s.cgpa >= minCgpa;
    const activeBacklogs = s.active_backlogs ?? 0;
    const historyBacklogs = s.history_backlogs ?? 0;
    const existingOffers = s.existing_offers_count ?? 0;

    const matchesBacklog =
      backlogFilter === "all" ||
      (backlogFilter === "zero" && activeBacklogs === 0 && historyBacklogs === 0) ||
      (backlogFilter === "active" && activeBacklogs > 0) ||
      (backlogFilter === "cleared" && historyBacklogs > 0);
    const matchesOffer =
      offerFilter === "all" ||
      (offerFilter === "placed" && existingOffers > 0) ||
      (offerFilter === "unplaced" && existingOffers === 0);

    return matchesSearch && matchesBranch && matchesCgpa && matchesBacklog && matchesOffer;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Student Academic Roster</h1>
            <Badge variant="brand">{students.length} Candidates Active</Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Browse candidate academic profiles, inspect drive verdicts, update contact fields directly, or submit mark corrections to the officer.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={fetchStudents}
            className="p-2 text-slate-500 hover:text-slate-800 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 shadow-xs cursor-pointer"
            title="Refresh roster"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={handleExportCsv}
            disabled={exportingCsv}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold rounded-xl shadow-xs transition-colors cursor-pointer disabled:opacity-50"
            title="Download full candidate roster as CSV"
          >
            <Download className="w-3.5 h-3.5" />
            <span>{exportingCsv ? "Exporting..." : "Export CSV"}</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search candidate name or roll number..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div className="flex items-center gap-2 flex-wrap w-full sm:w-auto">
            <select
              value={branchFilter}
              onChange={(e) => setBranchFilter(e.target.value)}
              className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold cursor-pointer"
            >
              <option value="all">All Disciplines (9 Branches)</option>
              <option value="CSE">CSE — Computer Science and Engineering</option>
              <option value="IT">IT — Information Technology</option>
              <option value="ECE">ECE — Electronics & Communication</option>
              <option value="EEE">EEE — Electrical & Electronics</option>
              <option value="ME">ME — Mechanical Engineering</option>
              <option value="CE">CE — Civil Engineering</option>
              <option value="CHE">CHE — Chemical Engineering</option>
              <option value="BT">BT — Biotechnology</option>
              <option value="DS">DS — Data Science</option>
            </select>

            <select
              value={backlogFilter}
              onChange={(e) => setBacklogFilter(e.target.value)}
              className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold cursor-pointer"
            >
              <option value="all">Backlogs: All</option>
              <option value="zero">Zero Backlogs</option>
              <option value="active">Active Standing Backlog</option>
              <option value="cleared">Cleared History</option>
            </select>

            <select
              value={offerFilter}
              onChange={(e) => setOfferFilter(e.target.value)}
              className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold cursor-pointer"
            >
              <option value="all">Offers: All</option>
              <option value="placed">Placed</option>
              <option value="unplaced">Unplaced</option>
            </select>
          </div>
        </div>

        {/* CGPA Slider */}
        <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
          <div className="flex items-center gap-3">
            <span className="font-bold text-slate-700">Min CGPA Filter:</span>
            <input
              type="range"
              min="0.0"
              max="10.0"
              step="0.5"
              value={minCgpa}
              onChange={(e) => setMinCgpa(parseFloat(e.target.value))}
              className="w-36 accent-brand-600 cursor-pointer"
            />
            <span className="font-mono font-bold text-brand-700 bg-brand-50 px-2 py-0.5 rounded border border-brand-200">
              ≥ {minCgpa.toFixed(1)}
            </span>
          </div>

          <span className="text-[11px] text-slate-400">
            Click candidate to view full semester details, reason lines, or raise correction requests.
          </span>
        </div>
      </div>

      {/* Roster Table */}
      {loading ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500 text-sm animate-pulse">
          Loading student roster...
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
                <th className="px-5 py-3.5">Roll No</th>
                <th className="px-5 py-3.5">Candidate Name</th>
                <th className="px-5 py-3.5">Branch</th>
                <th className="px-5 py-3.5">CGPA</th>
                <th className="px-5 py-3.5">Backlogs</th>
                <th className="px-5 py-3.5">Offers</th>
                <th className="px-5 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.slice(0, 100).map((s) => (
                <tr
                  key={s.id}
                  onClick={() => handleOpenStudent(s)}
                  className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                >
                  <td className="px-5 py-3.5 font-mono font-bold text-slate-900 group-hover:text-brand-600">
                    {s.roll_no}
                  </td>
                  <td className="px-5 py-3.5 font-semibold text-slate-800">{s.name}</td>
                  <td className="px-5 py-3.5 text-slate-600">{s.branch}</td>
                  <td className="px-5 py-3.5 font-mono font-bold text-brand-700">
                    {s.cgpa.toFixed(2)}
                  </td>
                  <td className="px-5 py-3.5">
                    {(s.active_backlogs ?? 0) > 0 ? (
                      <span className="px-2 py-0.5 text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200 rounded-md">
                        {s.active_backlogs} Active
                      </span>
                    ) : (s.history_backlogs ?? 0) > 0 ? (
                      <span className="px-2 py-0.5 text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200 rounded-md">
                        {s.history_backlogs} Cleared
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 text-[10px] font-bold bg-slate-100 text-slate-600 rounded-md">0</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 font-mono">
                    {(s.existing_offers_count ?? 0) > 0 ? (
                      <span className="px-2 py-0.5 text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-md">
                        {s.existing_offers_count} Offer(s)
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenStudent(s);
                      }}
                      className="text-xs font-bold text-brand-600 hover:text-brand-800 flex items-center justify-end gap-1 cursor-pointer"
                    >
                      Inspect <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length > 100 && (
            <div className="p-3 bg-slate-50 border-t border-slate-200 text-center text-xs font-bold text-slate-500">
              Showing first 100 results ({filtered.length} total matched).
            </div>
          )}
        </div>
      )}

      {/* Student Detail Drawer */}
      <Drawer
        isOpen={!!selectedStudent}
        onClose={() => setSelectedStudent(null)}
        title={selectedStudent?.name || "Student Profile"}
        subtitle={`Roll No: ${selectedStudent?.roll_no} • ${selectedStudent?.branch}`}
      >
        {selectedStudent && (
          <div className="space-y-6">
            {/* Drawer Tabs */}
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-xs font-bold">
              <button
                type="button"
                onClick={() => setDrawerTab("academics")}
                className={`flex-1 py-1.5 rounded-lg transition-all cursor-pointer ${
                  drawerTab === "academics" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-500 hover:text-slate-900"
                }`}
              >
                Academics
              </button>
              <button
                type="button"
                onClick={() => setDrawerTab("drives")}
                className={`flex-1 py-1.5 rounded-lg transition-all cursor-pointer ${
                  drawerTab === "drives" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-500 hover:text-slate-900"
                }`}
              >
                Drive Statuses ({driveStatuses.length})
              </button>
              <button
                type="button"
                onClick={() => setDrawerTab("contact")}
                className={`flex-1 py-1.5 rounded-lg transition-all cursor-pointer ${
                  drawerTab === "contact" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-500 hover:text-slate-900"
                }`}
              >
                Edit Contact
              </button>
              <button
                type="button"
                onClick={() => setDrawerTab("correction")}
                className={`flex-1 py-1.5 rounded-lg transition-all cursor-pointer ${
                  drawerTab === "correction" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-500 hover:text-slate-900"
                }`}
              >
                Request Correction
              </button>
            </div>

            {/* Tab 1: Academics */}
            {drawerTab === "academics" && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">CGPA</span>
                    <span className="text-xl font-black text-brand-700 font-mono">{selectedStudent.cgpa.toFixed(2)}</span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">10th Std %</span>
                    <span className="text-xl font-black text-slate-800 font-mono">{selectedStudent.tenth_percentage}%</span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">12th / Diploma</span>
                    <span className="text-xl font-black text-slate-800 font-mono">
                      {selectedStudent.twelfth_percentage ? `${selectedStudent.twelfth_percentage}%` : "Diploma / N/A"}
                    </span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Gap Years</span>
                    <span className="text-xl font-black text-slate-800 font-mono">{selectedStudent.gap_years ?? 0} yr(s)</span>
                  </div>
                </div>

                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1">
                  <span className="font-bold text-slate-700 block">Backlog Status:</span>
                  <div className="flex items-center gap-4 text-slate-600">
                    <span>Active: <strong>{selectedStudent.active_backlogs ?? 0}</strong></span>
                    <span>Cleared: <strong>{selectedStudent.history_backlogs ?? 0}</strong></span>
                  </div>
                </div>
              </div>
            )}

            {/* Tab 2: Drive Statuses with Headline Reason */}
            {drawerTab === "drives" && (
              <div className="space-y-3">
                <p className="text-xs text-slate-500">
                  Real-time status for every active recruitment drive. Use this to explain criteria outcomes to students:
                </p>
                {loadingStatuses ? (
                  <div className="p-6 text-center text-xs text-slate-500">Loading drive verdicts...</div>
                ) : driveStatuses.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500">No drives evaluated yet.</div>
                ) : (
                  <div className="space-y-2 max-h-[450px] overflow-y-auto custom-scrollbar">
                    {driveStatuses.map((ds) => (
                      <div key={ds.drive_id} className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-900 text-xs">{ds.company_name}</span>
                          <Badge
                            variant={
                              ds.status === "eligible"
                                ? "success"
                                : ds.status === "policy_blocked"
                                ? "warning"
                                : "danger"
                            }
                          >
                            {ds.status.replace("_", " ")}
                          </Badge>
                        </div>
                        <div className="text-[11px] text-slate-600 flex items-start gap-1 pt-1 border-t border-slate-100">
                          <span className="font-bold text-slate-400 shrink-0">Reason:</span>
                          <span>{ds.headline_reason}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Tab 3: Limited Edit: Contact Fields Directly */}
            {drawerTab === "contact" && (
              <form onSubmit={handleSaveContact} className="space-y-4 text-xs">
                {contactSuccess && <AlertBanner type="success" message={contactSuccess} onClose={() => setContactSuccess(null)} />}

                <div className="p-3 bg-emerald-50 text-emerald-900 border border-emerald-200 rounded-xl">
                  <strong>Direct Edit Permitted:</strong> Coordinators are authorized to update candidate contact and dispatch details directly.
                </div>

                <div>
                  <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">Email Address</label>
                  <input
                    type="email"
                    required
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-medium focus:bg-white"
                  />
                </div>

                <div>
                  <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">Phone Number</label>
                  <input
                    type="text"
                    required
                    value={contactPhone}
                    onChange={(e) => setContactPhone(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-medium focus:bg-white"
                  />
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    type="submit"
                    disabled={savingContact}
                    className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-xs cursor-pointer disabled:opacity-50"
                  >
                    {savingContact ? "Saving..." : "Save Contact Info"}
                  </button>
                </div>
              </form>
            )}

            {/* Tab 4: Submit Correction Request to Officer */}
            {drawerTab === "correction" && (
              <form onSubmit={handleRaiseCorrectionRequest} className="space-y-4 text-xs">
                {reqError && <AlertBanner type="danger" message={reqError} onClose={() => setReqError(null)} />}
                {reqSuccess && <AlertBanner type="success" message={reqSuccess} onClose={() => setReqSuccess(null)} />}

                <div className="p-3 bg-blue-50 text-blue-900 border border-blue-200 rounded-xl">
                  <strong>Approval Required:</strong> Any changes to marks, standing backlogs, gap years, or existing offers must be submitted as a formal correction request to the Placement Officer.
                </div>

                <div>
                  <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">Target Academic Field</label>
                  <select
                    value={reqField}
                    onChange={(e) => setReqField(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-semibold cursor-pointer"
                  >
                    <option value="cgpa">Cumulative CGPA</option>
                    <option value="active_backlogs">Active Backlogs Count</option>
                    <option value="history_backlogs">History / Cleared Backlogs</option>
                    <option value="tenth_percentage">10th Standard %</option>
                    <option value="twelfth_percentage">12th Standard %</option>
                    <option value="gap_years">Gap Years</option>
                  </select>
                </div>

                <div>
                  <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">Requested New Value</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 8.25 or 0"
                    value={reqNewValue}
                    onChange={(e) => setReqNewValue(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-mono focus:bg-white"
                  />
                </div>

                <div>
                  <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                    Mandatory Reason <span className="text-rose-500">*</span>
                  </label>
                  <textarea
                    rows={2}
                    required
                    placeholder="e.g. Candidate submitted university re-evaluation grade card for Semester 5..."
                    value={reqReason}
                    onChange={(e) => setReqReason(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white"
                  />
                </div>

                <div>
                  <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">Supporting Note / Document Ref</label>
                  <input
                    type="text"
                    placeholder="e.g. Memo #COE/2026/894 verified by HOD"
                    value={reqSupportingNote}
                    onChange={(e) => setReqSupportingNote(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white"
                  />
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    type="submit"
                    disabled={submittingReq || !reqReason.trim()}
                    className="flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl shadow-xs cursor-pointer disabled:opacity-50"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>{submittingReq ? "Submitting..." : "Submit Request to Officer"}</span>
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
};
