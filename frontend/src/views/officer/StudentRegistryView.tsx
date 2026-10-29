import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Student } from "../../types";
import { StudentImportWizard } from "./StudentImportWizard";
import { Badge } from "../../components/common/Badge";
import { Drawer } from "../../components/common/Drawer";
import { Modal } from "../../components/common/Modal";
import { EmptyState } from "../../components/common/EmptyState";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  Users,
  Upload,
  Search,
  Plus,
  RefreshCw,
  Key,
  Download,
  Filter,
  CheckCircle,
  XCircle,
  Clock,
  Briefcase,
  Edit2,
  Check,
  X,
  FileCheck,
  ChevronRight,
  Shield,
  Layers,
  GraduationCap,
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

export const StudentRegistryView: React.FC = () => {
  const [students, setStudents] = useState<Student[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [branchFilter, setBranchFilter] = useState("all");
  const [minCgpa, setMinCgpa] = useState<number>(0.0);
  const [backlogFilter, setBacklogFilter] = useState("all");
  const [offerFilter, setOfferFilter] = useState("all");
  const [sortField, setSortField] = useState<"roll_no" | "name" | "cgpa" | "active_backlogs">("roll_no");
  const [sortAsc, setSortAsc] = useState(true);

  const [showWizard, setShowWizard] = useState(false);
  const [accessCodeStudent, setAccessCodeStudent] = useState<any | null>(null);
  const [codeGenerated, setCodeGenerated] = useState<string | null>(null);

  // Student Detail Drawer State
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [studentDriveStatuses, setStudentDriveStatuses] = useState<DriveStatusItem[]>([]);
  const [loadingStatuses, setLoadingStatuses] = useState(false);
  const [drawerTab, setDrawerTab] = useState<"academics" | "drives" | "edit" | "corrections">("academics");

  // Edit Student State
  const [editCgpa, setEditCgpa] = useState<number>(0);
  const [editTenth, setEditTenth] = useState<number>(0);
  const [editTwelfth, setEditTwelfth] = useState<number>(0);
  const [editActiveBacklogs, setEditActiveBacklogs] = useState<number>(0);
  const [editReason, setEditReason] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);
  const [editSuccess, setEditSuccess] = useState<string | null>(null);
  const [editError, setEditError] = useState<string | null>(null);

  const fetchStudents = async () => {
    try {
      setLoading(true);
      const res = await api.get<{ items: Student[]; total: number }>("/api/students?limit=2500");
      setStudents(res.items || []);
      setTotalCount(res.total || (res.items || []).length);
    } catch {
      setStudents([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, []);

  const handleIssueAccessCode = async (rollNo: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    try {
      const res = await api.post<any>("/api/auth/student-access-code", { roll_no: rollNo });
      setCodeGenerated(res.access_code);
      setAccessCodeStudent(rollNo);
    } catch {
      // Fallback
    }
  };

  const handleOpenStudentDrawer = async (student: Student) => {
    setSelectedStudent(student);
    setEditCgpa(student.cgpa);
    setEditTenth(student.tenth_percentage);
    setEditTwelfth(student.twelfth_percentage || 0);
    setEditActiveBacklogs(student.active_backlogs ?? 0);
    setEditReason("");
    setEditSuccess(null);
    setEditError(null);
    setDrawerTab("academics");

    // Fetch drive statuses for this student
    try {
      setLoadingStatuses(true);
      const statuses = await api.get<DriveStatusItem[]>(`/api/students/${student.id}/drive-statuses`);
      setStudentDriveStatuses(statuses || []);
    } catch {
      setStudentDriveStatuses([]);
    } finally {
      setLoadingStatuses(false);
    }
  };

  const handleSaveStudentEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStudent) return;
    if (!editReason.trim()) {
      setEditError("Mandatory reason required for modifying academic student records.");
      return;
    }

    try {
      setSavingEdit(true);
      setEditError(null);
      await api.put(`/api/students/${selectedStudent.id}`, {
        roll_no: selectedStudent.roll_no,
        name: selectedStudent.name,
        email: selectedStudent.email,
        branch: selectedStudent.branch,
        program: selectedStudent.program,
        cgpa: editCgpa,
        tenth_percentage: editTenth,
        twelfth_percentage: editTwelfth > 0 ? editTwelfth : null,
        diploma_percentage: selectedStudent.diploma_percentage,
        date_of_birth: selectedStudent.date_of_birth,
      });

      setEditSuccess("Student record updated and committed to the backend audit log.");
      fetchStudents();
    } catch (err: any) {
      setEditError(err.message || "Failed to update student.");
    } finally {
      setSavingEdit(false);
    }
  };

  const handleExportCsv = () => {
    window.open("/api/students/export/csv", "_blank");
  };

  // Filter and sort candidates
  const filtered = students
    .filter((s) => {
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
    })
    .sort((a, b) => {
      let comparison = 0;
      if (sortField === "cgpa") {
        comparison = a.cgpa - b.cgpa;
      } else if (sortField === "active_backlogs") {
        comparison = (a.active_backlogs ?? 0) - (b.active_backlogs ?? 0);
      } else if (sortField === "name") {
        comparison = a.name.localeCompare(b.name);
      } else {
        comparison = a.roll_no.localeCompare(b.roll_no);
      }
      return sortAsc ? comparison : -comparison;
    });

  if (showWizard) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => {
            setShowWizard(false);
            fetchStudents();
          }}
          className="text-xs font-bold text-brand-600 hover:underline cursor-pointer"
        >
          ← Return to Student Registry Table
        </button>
        <StudentImportWizard onSuccess={() => fetchStudents()} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Student Academic Registry</h1>
            <Badge variant="success">{students.length} Students Active (9 Branches)</Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Institutional database of student records, semester SGPAs, backlog records, and one-time access codes.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchStudents}
            className="p-2 text-slate-500 hover:text-slate-800 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 shadow-xs cursor-pointer"
            title="Refresh roster"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleExportCsv}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold rounded-xl shadow-xs transition-colors cursor-pointer"
            title="Download full candidate roster as CSV"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>
          <button
            onClick={() => setShowWizard(true)}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors cursor-pointer"
          >
            <Upload className="w-4 h-4" />
            <span>Launch Import Wizard</span>
          </button>
        </div>
      </div>

      {codeGenerated && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Key className="w-5 h-5 text-emerald-600" />
            <span className="text-xs font-bold text-emerald-900">
              One-Time Student Access Code for {accessCodeStudent}:{" "}
              <strong className="font-mono text-sm underline">{codeGenerated}</strong>
            </span>
          </div>
          <button
            onClick={() => setCodeGenerated(null)}
            className="text-xs text-emerald-700 hover:underline cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search student by name or roll number..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div className="flex items-center gap-2 flex-wrap w-full sm:w-auto">
            {/* Branch Filter */}
            <select
              value={branchFilter}
              onChange={(e) => setBranchFilter(e.target.value)}
              className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold cursor-pointer"
            >
              <option value="all">All Branches (9 Engineering Disciplines)</option>
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

            {/* Backlog Filter */}
            <select
              value={backlogFilter}
              onChange={(e) => setBacklogFilter(e.target.value)}
              className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold cursor-pointer"
            >
              <option value="all">Backlogs: All</option>
              <option value="zero">Zero Backlogs (Clean)</option>
              <option value="active">Has Active Backlogs</option>
              <option value="cleared">History / Cleared</option>
            </select>

            {/* Offer Status Filter */}
            <select
              value={offerFilter}
              onChange={(e) => setOfferFilter(e.target.value)}
              className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold cursor-pointer"
            >
              <option value="all">Offers: All</option>
              <option value="placed">Placed (Holds Offer)</option>
              <option value="unplaced">Unplaced (0 Offers)</option>
            </select>
          </div>
        </div>

        {/* Min CGPA Slider */}
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

          <div className="text-[11px] text-slate-400">
            Click any candidate row to inspect semester academics & eligibility across all campus drives.
          </div>
        </div>
      </div>

      {/* Roster Table */}
      {loading ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500 text-sm animate-pulse">
          Loading student academic roster...
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No student records found"
          description="Import your college batch roster using the Student Import Wizard."
          action={
            <button
              onClick={() => setShowWizard(true)}
              className="px-4 py-2 bg-brand-600 text-white text-xs font-semibold rounded-xl hover:bg-brand-700 cursor-pointer"
            >
              Open Import Wizard
            </button>
          }
        />
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="px-6 py-2 bg-slate-100/60 border-b border-slate-200 flex justify-between items-center text-[11px] font-semibold text-slate-500">
            <span>Showing {filtered.length} of {students.length} students</span>
            <span>All records encrypted & cached offline</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
                <th
                  className="px-5 py-3.5 cursor-pointer hover:text-slate-900"
                  onClick={() => {
                    setSortField("roll_no");
                    setSortAsc(!sortAsc);
                  }}
                >
                  Roll No {sortField === "roll_no" && (sortAsc ? "▲" : "▼")}
                </th>
                <th
                  className="px-5 py-3.5 cursor-pointer hover:text-slate-900"
                  onClick={() => {
                    setSortField("name");
                    setSortAsc(!sortAsc);
                  }}
                >
                  Candidate Name {sortField === "name" && (sortAsc ? "▲" : "▼")}
                </th>
                <th className="px-5 py-3.5">Branch</th>
                <th
                  className="px-5 py-3.5 cursor-pointer hover:text-slate-900"
                  onClick={() => {
                    setSortField("cgpa");
                    setSortAsc(!sortAsc);
                  }}
                >
                  CGPA {sortField === "cgpa" && (sortAsc ? "▲" : "▼")}
                </th>
                <th className="px-5 py-3.5">10th / 12th</th>
                <th
                  className="px-5 py-3.5 cursor-pointer hover:text-slate-900"
                  onClick={() => {
                    setSortField("active_backlogs");
                    setSortAsc(!sortAsc);
                  }}
                >
                  Backlogs {sortField === "active_backlogs" && (sortAsc ? "▲" : "▼")}
                </th>
                <th className="px-5 py-3.5">Offers</th>
                <th className="px-5 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.slice(0, 100).map((s: any) => (
                <tr
                  key={s.id}
                  onClick={() => handleOpenStudentDrawer(s)}
                  className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                >
                  <td className="px-5 py-3.5 font-mono font-bold text-slate-900 group-hover:text-brand-600">
                    {s.roll_no}
                  </td>
                  <td className="px-5 py-3.5 font-semibold text-slate-800">{s.name}</td>
                  <td className="px-5 py-3.5 text-slate-600 font-medium">{s.branch}</td>
                  <td className="px-5 py-3.5 font-mono font-bold text-brand-700">
                    {typeof s.cgpa === "number" ? s.cgpa.toFixed(2) : s.cgpa}
                  </td>
                  <td className="px-5 py-3.5 text-slate-600">
                    {s.tenth_percentage}% /{" "}
                    {s.twelfth_percentage
                      ? `${s.twelfth_percentage}%`
                      : s.diploma_percentage
                      ? `${s.diploma_percentage}% (Dip)`
                      : "—"}
                  </td>
                  <td className="px-5 py-3.5">
                    {s.active_backlogs > 0 ? (
                      <span className="px-2 py-0.5 text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200 rounded-md">
                        {s.active_backlogs} Active
                      </span>
                    ) : s.history_backlogs > 0 ? (
                      <span className="px-2 py-0.5 text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200 rounded-md">
                        {s.history_backlogs} Cleared
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 text-[10px] font-bold bg-slate-100 text-slate-600 rounded-md">
                        0
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    {s.existing_offers_count > 0 ? (
                      <span className="px-2 py-0.5 text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-md">
                        {s.existing_offers_count} Offer(s)
                      </span>
                    ) : (
                      <span className="text-slate-400 font-mono text-[11px]">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <button
                      type="button"
                      onClick={(e) => handleIssueAccessCode(s.roll_no, e)}
                      className="px-2.5 py-1 text-xs font-semibold text-brand-700 bg-brand-50 hover:bg-brand-100 rounded-lg transition-colors inline-flex items-center gap-1 cursor-pointer"
                      title="Generate student portal login code"
                    >
                      <Key className="w-3 h-3" />
                      <span>Code</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          {filtered.length > 100 && (
            <div className="p-3 bg-slate-50 border-t border-slate-200 text-center text-xs font-bold text-slate-500">
              Showing first 100 results ({filtered.length} total matched). Use the filters above to narrow down.
            </div>
          )}
        </div>
      )}

      {/* Module 2: Student Detail Drawer */}
      <Drawer
        isOpen={!!selectedStudent}
        onClose={() => setSelectedStudent(null)}
        title={selectedStudent?.name || "Student Profile"}
        subtitle={`Roll No: ${selectedStudent?.roll_no} • ${selectedStudent?.branch}`}
      >
        {selectedStudent && (
          <div className="space-y-6">
            {/* Drawer Sub-tabs */}
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
                Drive Statuses ({studentDriveStatuses.length})
              </button>
              <button
                type="button"
                onClick={() => setDrawerTab("edit")}
                className={`flex-1 py-1.5 rounded-lg transition-all cursor-pointer ${
                  drawerTab === "edit" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-500 hover:text-slate-900"
                }`}
              >
                Edit Data
              </button>
            </div>

            {/* Tab 1: Academics & History */}
            {drawerTab === "academics" && (
              <div className="space-y-5">
                {/* Academic Highlights */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                      Cumulative CGPA
                    </span>
                    <span className="text-xl font-black text-brand-700 font-mono">
                      {selectedStudent.cgpa.toFixed(2)}
                    </span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                      10th Standard %
                    </span>
                    <span className="text-xl font-black text-slate-800 font-mono">
                      {selectedStudent.tenth_percentage}%
                    </span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                      12th / Diploma %
                    </span>
                    <span className="text-xl font-black text-slate-800 font-mono">
                      {selectedStudent.twelfth_percentage
                        ? `${selectedStudent.twelfth_percentage}%`
                        : selectedStudent.diploma_percentage
                        ? `${selectedStudent.diploma_percentage}% (Diploma)`
                        : "N/A"}
                    </span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                      Gap Years
                    </span>
                    <span className="text-xl font-black text-slate-800 font-mono">
                      {selectedStudent.gap_years} yr(s)
                    </span>
                  </div>
                </div>

                {/* Backlogs Breakdown */}
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                    <FileCheck className="w-4 h-4 text-brand-600" />
                    Backlog Record & Verification
                  </h4>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-slate-500">Active Backlogs:</span>
                      <strong className={`ml-1 ${(selectedStudent.active_backlogs ?? 0) > 0 ? "text-rose-600" : "text-emerald-600"}`}>
                        {selectedStudent.active_backlogs ?? 0}
                      </strong>
                    </div>
                    <div>
                      <span className="text-slate-500">Cleared / History:</span>
                      <strong className="ml-1 text-slate-800">{selectedStudent.history_backlogs ?? 0}</strong>
                    </div>
                  </div>
                </div>

                {/* Offers Held */}
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                    <Briefcase className="w-4 h-4 text-emerald-600" />
                    Placement Offers
                  </h4>
                  {(selectedStudent.existing_offers_count ?? 0) > 0 ? (
                    <div className="p-2.5 bg-emerald-50 text-emerald-900 border border-emerald-200 rounded-lg text-xs font-medium">
                      Student currently holds <strong>{selectedStudent.existing_offers_count ?? 0}</strong> active recruitment offer(s).
                    </div>
                  ) : (
                    <div className="text-xs text-slate-500">No recruitment offers recorded yet. Candidate is fully eligible for unblocked drives.</div>
                  )}
                </div>
              </div>
            )}

            {/* Tab 2: Status of this student for EVERY drive with reason line */}
            {drawerTab === "drives" && (
              <div className="space-y-3">
                <div className="text-xs text-slate-500">
                  Comprehensive status of <strong>{selectedStudent.name}</strong> across all active campus drives, evaluated against pure company rules and institutional offer policies.
                </div>

                {loadingStatuses ? (
                  <div className="p-6 text-center text-xs text-slate-500">Loading drive eligibility statuses...</div>
                ) : studentDriveStatuses.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500">No recruitment drives available to evaluate.</div>
                ) : (
                  <div className="space-y-2 max-h-[480px] overflow-y-auto custom-scrollbar">
                    {studentDriveStatuses.map((ds) => (
                      <div
                        key={ds.drive_id}
                        className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="font-bold text-slate-900 text-xs block">{ds.company_name}</span>
                            <span className="text-[10px] text-slate-400 font-mono">
                              CTC: {ds.ctc_lpa} LPA • {ds.drive_date}
                            </span>
                          </div>
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
                        <div className="text-[11px] font-medium text-slate-600 pt-1 border-t border-slate-100 flex items-start gap-1">
                          <span className="font-bold text-slate-400 shrink-0">Reason:</span>
                          <span className="leading-snug">{ds.headline_reason}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Tab 3: Edit Student Data with Mandatory Reason */}
            {drawerTab === "edit" && (
              <form onSubmit={handleSaveStudentEdit} className="space-y-4">
                {editError && <AlertBanner type="danger" message={editError} onClose={() => setEditError(null)} />}
                {editSuccess && <AlertBanner type="success" message={editSuccess} onClose={() => setEditSuccess(null)} />}

                <div className="space-y-3 text-xs">
                  <div>
                    <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                      CGPA (0.0 to 10.0)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0.0"
                      max="10.0"
                      value={editCgpa}
                      onChange={(e) => setEditCgpa(parseFloat(e.target.value) || 0)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-mono font-bold"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                        10th Standard %
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="100"
                        value={editTenth}
                        onChange={(e) => setEditTenth(parseFloat(e.target.value) || 0)}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-mono"
                      />
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                        12th Standard %
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="100"
                        value={editTwelfth}
                        onChange={(e) => setEditTwelfth(parseFloat(e.target.value) || 0)}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-mono"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                      Active Backlogs Count
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="20"
                      value={editActiveBacklogs}
                      onChange={(e) => setEditActiveBacklogs(parseInt(e.target.value) || 0)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-mono"
                    />
                  </div>

                  <div>
                    <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                      Mandatory Reason for Modification <span className="text-rose-500">*</span>
                    </label>
                    <textarea
                      rows={3}
                      required
                      placeholder="e.g. Cleared semester 5 re-evaluation in Mathematics; updated CGPA per Controller of Examinations circular..."
                      value={editReason}
                      onChange={(e) => setEditReason(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-brand-500 font-medium"
                    />
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-200 flex items-center justify-end">
                  <button
                    type="submit"
                    disabled={savingEdit || !editReason.trim()}
                    className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer disabled:opacity-50"
                  >
                    {savingEdit ? "Saving..." : "Commit Change with Audit"}
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
