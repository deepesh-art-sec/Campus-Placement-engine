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
  Edit3,
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
  has_applied?: boolean;
  applied_at?: string | null;
  application_status?: string;
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
  const [exportingCsv, setExportingCsv] = useState(false);

  // Student Detail Drawer State
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [studentDriveStatuses, setStudentDriveStatuses] = useState<DriveStatusItem[]>([]);
  const [loadingStatuses, setLoadingStatuses] = useState(false);
  const [drawerTab, setDrawerTab] = useState<"academics" | "drives" | "edit" | "corrections">("academics");

  // Dedicated Edit Student Modal & Form State
  const [editingStudent, setEditingStudent] = useState<Student | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editForm, setEditForm] = useState({
    roll_no: "",
    name: "",
    email: "",
    branch: "CSE",
    program: "B.Tech",
    cgpa: 0,
    tenth_percentage: 0,
    twelfth_percentage: 0,
    diploma_percentage: 0,
    date_of_birth: "2002-01-01",
    gender: "",
    category: "",
    active_backlogs: 0,
    history_backlogs: 0,
    reason: "",
  });
  const [savingEdit, setSavingEdit] = useState(false);
  const [editSuccess, setEditSuccess] = useState<string | null>(null);
  const [editError, setEditError] = useState<string | null>(null);

  const populateEditForm = (student: Student) => {
    setEditForm({
      roll_no: student.roll_no || "",
      name: student.name || "",
      email: student.email || "",
      branch: student.branch || "CSE",
      program: student.program || "B.Tech",
      cgpa: student.cgpa ?? 0,
      tenth_percentage: student.tenth_percentage ?? 0,
      twelfth_percentage: student.twelfth_percentage ?? 0,
      diploma_percentage: student.diploma_percentage ?? 0,
      date_of_birth: student.date_of_birth ? student.date_of_birth.slice(0, 10) : "2002-01-01",
      gender: (student as any).gender || "",
      category: (student as any).category || "",
      active_backlogs: student.active_backlogs ?? 0,
      history_backlogs: student.history_backlogs ?? 0,
      reason: "",
    });
    setEditSuccess(null);
    setEditError(null);
  };

  const handleOpenEditModal = (student: Student, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setEditingStudent(student);
    populateEditForm(student);
    setIsEditModalOpen(true);
  };

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
    populateEditForm(student);
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

  const handleSaveStudentEdit = async (e: React.FormEvent, targetStudent?: Student) => {
    e.preventDefault();
    const studentToUpdate = targetStudent || editingStudent || selectedStudent;
    if (!studentToUpdate) return;

    if (!editForm.reason.trim()) {
      setEditError("Mandatory justification reason required for modifying institutional student records.");
      return;
    }
    if (!editForm.name.trim()) {
      setEditError("Candidate name cannot be empty.");
      return;
    }
    if (!editForm.roll_no.trim()) {
      setEditError("Roll number cannot be empty.");
      return;
    }
    if (!editForm.email.trim() || !editForm.email.includes("@")) {
      setEditError("A valid email address is required.");
      return;
    }
    if (Number(editForm.cgpa) < 0 || Number(editForm.cgpa) > 10) {
      setEditError("CGPA must be between 0.0 and 10.0.");
      return;
    }
    if (Number(editForm.tenth_percentage) < 0 || Number(editForm.tenth_percentage) > 100) {
      setEditError("10th percentage must be between 0.0 and 100.0.");
      return;
    }

    try {
      setSavingEdit(true);
      setEditError(null);
      const payload = {
        roll_no: editForm.roll_no.trim(),
        name: editForm.name.trim(),
        email: editForm.email.trim(),
        branch: editForm.branch.trim(),
        program: editForm.program.trim(),
        cgpa: Number(Number(editForm.cgpa).toFixed(2)),
        tenth_percentage: Number(Number(editForm.tenth_percentage).toFixed(2)),
        twelfth_percentage: Number(editForm.twelfth_percentage) > 0 ? Number(Number(editForm.twelfth_percentage).toFixed(2)) : null,
        diploma_percentage: Number(editForm.diploma_percentage) > 0 ? Number(Number(editForm.diploma_percentage).toFixed(2)) : null,
        date_of_birth: editForm.date_of_birth,
        active_backlogs: parseInt(String(editForm.active_backlogs), 10) || 0,
        history_backlogs: parseInt(String(editForm.history_backlogs), 10) || 0,
        gender: editForm.gender.trim() || null,
        category: editForm.category.trim() || null,
        reason: editForm.reason.trim(),
      };

      const res = await api.put<{ id: string; message: string; student?: any }>(
        `/api/students/${studentToUpdate.id}`,
        payload
      );

      const successMsg = res.message || "Student record updated and committed to backend audit log.";
      setEditSuccess(successMsg);

      // Instantly update candidate list in memory
      setStudents((prev) =>
        prev.map((s) => (s.id === studentToUpdate.id ? { ...s, ...payload } : s))
      );

      if (selectedStudent && selectedStudent.id === studentToUpdate.id) {
        setSelectedStudent((prev) => (prev ? { ...prev, ...payload } : null));
      }

      // Re-fetch to keep everything in sync
      fetchStudents();

      if (isEditModalOpen) {
        setTimeout(() => {
          setIsEditModalOpen(false);
          setEditingStudent(null);
        }, 1100);
      }
    } catch (err: any) {
      setEditError(err.message || "Failed to update student.");
    } finally {
      setSavingEdit(false);
    }
  };

  const handleExportCsv = async () => {
    try {
      setExportingCsv(true);
      const url = branchFilter && branchFilter !== "all"
        ? `/api/students/export/csv?branch=${encodeURIComponent(branchFilter)}`
        : "/api/students/export/csv";
      await api.download(url, `student_academic_roster_${new Date().toISOString().slice(0, 10)}.csv`);
    } catch (err: any) {
      console.error("Export error:", err);
    } finally {
      setExportingCsv(false);
    }
  };

  const renderStudentFormFields = (isModal: boolean = false) => (
    <div className="space-y-4 text-xs">
      {editError && <AlertBanner type="danger" message={editError} onClose={() => setEditError(null)} />}
      {editSuccess && <AlertBanner type="success" message={editSuccess} onClose={() => setEditSuccess(null)} />}

      {/* Group 1: Identity & Roll */}
      <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 space-y-3">
        <h4 className="font-bold text-slate-800 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
          <GraduationCap className="w-4 h-4 text-brand-600" />
          Candidate Identity & Institutional Profile
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="font-bold text-slate-700 block mb-1">
              Full Name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              value={editForm.name}
              onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl font-medium focus:ring-2 focus:ring-brand-500 focus:outline-none"
              placeholder="e.g. John Doe"
            />
          </div>
          <div>
            <label className="font-bold text-slate-700 block mb-1">
              Roll / Registration Number <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              value={editForm.roll_no}
              onChange={(e) => setEditForm({ ...editForm, roll_no: e.target.value })}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl font-mono font-bold focus:ring-2 focus:ring-brand-500 focus:outline-none"
              placeholder="e.g. 21CS01"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="font-bold text-slate-700 block mb-1">
              Email Address <span className="text-rose-500">*</span>
            </label>
            <input
              type="email"
              required
              value={editForm.email}
              onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl font-medium focus:ring-2 focus:ring-brand-500 focus:outline-none"
              placeholder="e.g. student@college.edu"
            />
          </div>
          <div>
            <label className="font-bold text-slate-700 block mb-1">
              Date of Birth <span className="text-rose-500">*</span>
            </label>
            <input
              type="date"
              required
              value={editForm.date_of_birth}
              onChange={(e) => setEditForm({ ...editForm, date_of_birth: e.target.value })}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl font-medium focus:ring-2 focus:ring-brand-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="font-bold text-slate-700 block mb-1">Gender (Optional)</label>
            <select
              value={editForm.gender}
              onChange={(e) => setEditForm({ ...editForm, gender: e.target.value })}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl font-medium cursor-pointer"
            >
              <option value="">Unspecified</option>
              <option value="Male">Male</option>
              <option value="Female">Female</option>
              <option value="Other">Other</option>
            </select>
          </div>
          <div>
            <label className="font-bold text-slate-700 block mb-1">Category (Optional)</label>
            <select
              value={editForm.category}
              onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl font-medium cursor-pointer"
            >
              <option value="">Unspecified</option>
              <option value="General">General</option>
              <option value="OBC">OBC</option>
              <option value="SC">SC</option>
              <option value="ST">ST</option>
              <option value="EWS">EWS</option>
            </select>
          </div>
        </div>
      </div>

      {/* Group 2: Academics & Department */}
      <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 space-y-3">
        <h4 className="font-bold text-slate-800 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
          <Layers className="w-4 h-4 text-brand-600" />
          Academic Program & Scores
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="font-bold text-slate-700 block mb-1">Program</label>
            <select
              value={editForm.program}
              onChange={(e) => setEditForm({ ...editForm, program: e.target.value })}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl font-medium cursor-pointer"
            >
              <option value="B.Tech">B.Tech</option>
              <option value="M.Tech">M.Tech</option>
              <option value="MCA">MCA</option>
              <option value="B.Sc">B.Sc</option>
              <option value="Dual Degree">Dual Degree</option>
            </select>
          </div>
          <div>
            <label className="font-bold text-slate-700 block mb-1">Branch / Dept</label>
            <select
              value={editForm.branch}
              onChange={(e) => setEditForm({ ...editForm, branch: e.target.value })}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl font-semibold cursor-pointer"
            >
              <option value="CSE">CSE — Computer Science</option>
              <option value="IT">IT — Information Tech</option>
              <option value="ECE">ECE — Electronics & Comm</option>
              <option value="EEE">EEE — Electrical & Electronics</option>
              <option value="ME">ME — Mechanical</option>
              <option value="CE">CE — Civil</option>
              <option value="CHE">CHE — Chemical</option>
              <option value="BT">BT — Biotechnology</option>
              <option value="DS">DS — Data Science</option>
            </select>
          </div>
          <div>
            <label className="font-bold text-slate-700 block mb-1">
              Cumulative CGPA (0-10) <span className="text-rose-500">*</span>
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="10"
              required
              value={editForm.cgpa}
              onChange={(e) => setEditForm({ ...editForm, cgpa: parseFloat(e.target.value) || 0 })}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl font-mono font-bold text-brand-700 focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="font-bold text-slate-700 block mb-1">
              10th Standard % <span className="text-rose-500">*</span>
            </label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="100"
              required
              value={editForm.tenth_percentage}
              onChange={(e) => setEditForm({ ...editForm, tenth_percentage: parseFloat(e.target.value) || 0 })}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl font-mono"
            />
          </div>
          <div>
            <label className="font-bold text-slate-700 block mb-1">12th Standard %</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="100"
              value={editForm.twelfth_percentage || ""}
              onChange={(e) => setEditForm({ ...editForm, twelfth_percentage: parseFloat(e.target.value) || 0 })}
              placeholder="e.g. 85.5 (or blank for Dip)"
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl font-mono"
            />
          </div>
          <div>
            <label className="font-bold text-slate-700 block mb-1">Diploma % (Optional)</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="100"
              value={editForm.diploma_percentage || ""}
              onChange={(e) => setEditForm({ ...editForm, diploma_percentage: parseFloat(e.target.value) || 0 })}
              placeholder="e.g. 78.2"
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl font-mono"
            />
          </div>
        </div>
      </div>

      {/* Group 3: Backlogs */}
      <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 space-y-3">
        <h4 className="font-bold text-slate-800 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
          <FileCheck className="w-4 h-4 text-brand-600" />
          Backlog Records
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="font-bold text-slate-700 block mb-1">Active Backlogs Count</label>
            <input
              type="number"
              min="0"
              max="20"
              value={editForm.active_backlogs}
              onChange={(e) => setEditForm({ ...editForm, active_backlogs: parseInt(e.target.value) || 0 })}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl font-mono font-bold text-rose-600"
            />
            <span className="text-[10px] text-slate-400 mt-0.5 block">Un-cleared backlogs currently pending</span>
          </div>
          <div>
            <label className="font-bold text-slate-700 block mb-1">Cleared / History Backlogs</label>
            <input
              type="number"
              min="0"
              max="20"
              value={editForm.history_backlogs}
              onChange={(e) => setEditForm({ ...editForm, history_backlogs: parseInt(e.target.value) || 0 })}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl font-mono font-bold text-slate-700"
            />
            <span className="text-[10px] text-slate-400 mt-0.5 block">Historical backlogs cleared in prior terms</span>
          </div>
        </div>
      </div>

      {/* Group 4: Mandatory Audit Reason */}
      <div className="bg-amber-50/60 p-3.5 rounded-xl border border-amber-200/70 space-y-2">
        <label className="font-bold text-slate-800 block text-[11px] uppercase tracking-wider">
          Mandatory Reason for Modification <span className="text-rose-500">*</span>
        </label>
        <textarea
          rows={isModal ? 2 : 3}
          required
          placeholder="e.g. Approved re-evaluation result in Math-III; updated CGPA per Controller of Examinations notification..."
          value={editForm.reason}
          onChange={(e) => setEditForm({ ...editForm, reason: e.target.value })}
          className="w-full px-3 py-2 bg-white border border-amber-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-brand-500 font-medium text-xs text-slate-800"
        />
        <div className="text-[10px] text-amber-800 flex items-center gap-1 font-medium">
          <Shield className="w-3 h-3 text-amber-600 shrink-0" />
          <span>Institutional compliance rule: Every student modification is permanently logged with your Officer identity and timestamp.</span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="pt-3 border-t border-slate-200 flex items-center justify-end gap-2">
        {isModal && (
          <button
            type="button"
            disabled={savingEdit}
            onClick={() => {
              setIsEditModalOpen(false);
              setEditingStudent(null);
            }}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl transition-colors cursor-pointer"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={savingEdit || !editForm.reason.trim()}
          className="px-5 py-2 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
        >
          {savingEdit ? (
            <>
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>Saving Changes...</span>
            </>
          ) : (
            <>
              <Check className="w-3.5 h-3.5" />
              <span>Commit & Save Student Record</span>
            </>
          )}
        </button>
      </div>
    </div>
  );

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
            disabled={exportingCsv}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold rounded-xl shadow-xs transition-colors cursor-pointer disabled:opacity-50"
            title="Download full candidate roster as CSV"
          >
            <Download className="w-3.5 h-3.5" />
            <span>{exportingCsv ? "Exporting..." : "Export CSV"}</span>
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
                  <td className="px-5 py-3.5 text-right whitespace-nowrap">
                    <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        onClick={() => handleOpenEditModal(s)}
                        className="px-2.5 py-1 text-xs font-semibold text-brand-700 bg-brand-50 hover:bg-brand-100 border border-brand-200/60 rounded-lg transition-colors inline-flex items-center gap-1 cursor-pointer shadow-2xs"
                        title="Edit student academic details & marks"
                      >
                        <Edit3 className="w-3 h-3" />
                        <span>Edit</span>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => handleIssueAccessCode(s.roll_no, e)}
                        className="px-2.5 py-1 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-lg transition-colors inline-flex items-center gap-1 cursor-pointer"
                        title="Generate student portal login code"
                      >
                        <Key className="w-3 h-3" />
                        <span>Code</span>
                      </button>
                    </div>
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
                <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                  <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">Candidate Academic File</span>
                  <button
                    type="button"
                    onClick={() => {
                      populateEditForm(selectedStudent);
                      setDrawerTab("edit");
                    }}
                    className="flex items-center gap-1.5 px-3 py-1 bg-brand-50 hover:bg-brand-100 text-brand-700 text-xs font-bold rounded-lg border border-brand-200/80 cursor-pointer transition-colors shadow-2xs"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    <span>Edit Profile Data</span>
                  </button>
                </div>
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
                          <div className="flex items-center gap-1.5">
                            {ds.has_applied && (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                                Applied
                              </span>
                            )}
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
              <form onSubmit={(e) => handleSaveStudentEdit(e, selectedStudent)} className="space-y-4">
                {renderStudentFormFields(false)}
              </form>
            )}
          </div>
        )}
      </Drawer>

      {/* Edit Student Record Modal Dialog */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => {
          if (!savingEdit) {
            setIsEditModalOpen(false);
            setEditingStudent(null);
          }
        }}
        title={`Edit Student Academic Record — ${editingStudent?.name || "Student"} (${editingStudent?.roll_no || ""})`}
        maxWidth="2xl"
      >
        <form onSubmit={(e) => handleSaveStudentEdit(e, editingStudent || undefined)} className="space-y-4">
          {renderStudentFormFields(true)}
        </form>
      </Modal>
    </div>
  );
};
