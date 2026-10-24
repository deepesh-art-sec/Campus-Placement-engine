import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Student } from "../../types";
import { StudentImportWizard } from "./StudentImportWizard";
import { Badge } from "../../components/common/Badge";
import { EmptyState } from "../../components/common/EmptyState";
import { Users, Upload, Search, Plus, RefreshCw, Key } from "lucide-react";

export const StudentRegistryView: React.FC = () => {
  const [students, setStudents] = useState<Student[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [branchFilter, setBranchFilter] = useState("all");
  const [showWizard, setShowWizard] = useState(false);
  const [accessCodeStudent, setAccessCodeStudent] = useState<any | null>(null);
  const [codeGenerated, setCodeGenerated] = useState<string | null>(null);

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

  const handleIssueAccessCode = async (rollNo: string) => {
    try {
      const res = await api.post<any>("/api/auth/student-access-code", { roll_no: rollNo });
      setCodeGenerated(res.access_code);
      setAccessCodeStudent(rollNo);
    } catch {
      // Fallback
    }
  };

  const filtered = students.filter((s) => {
    const matchesSearch =
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.roll_no.toLowerCase().includes(search.toLowerCase());
    const matchesBranch = branchFilter === "all" || s.branch === branchFilter;
    return matchesSearch && matchesBranch;
  });

  if (showWizard) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => {
            setShowWizard(false);
            fetchStudents();
          }}
          className="text-xs font-bold text-brand-600 hover:underline"
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
            className="p-2 text-slate-500 hover:text-slate-800 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 shadow-xs"
            title="Refresh roster"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowWizard(true)}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors"
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
            className="text-xs text-emerald-700 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Filter and Search */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search student by name or roll number..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium focus:bg-white"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select
            value={branchFilter}
            onChange={(e) => setBranchFilter(e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold"
          >
            <option value="all">All Branches (9 Engineering Disciplines)</option>
            <option value="Computer Science and Engineering">Computer Science (CSE)</option>
            <option value="Information Technology">Information Technology (IT)</option>
            <option value="Electronics and Communication Engineering">Electronics & Comm (ECE)</option>
            <option value="Electrical and Electronics Engineering">Electrical & Electronics (EEE)</option>
            <option value="Mechanical Engineering">Mechanical Engineering</option>
            <option value="Civil Engineering">Civil Engineering</option>
            <option value="Chemical Engineering">Chemical Engineering</option>
            <option value="Biotechnology">Biotechnology</option>
            <option value="Data Science">Data Science</option>
          </select>
        </div>
      </div>

      {/* Roster Table */}
      {loading ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500 text-sm">
          Loading student roster...
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No student records found"
          description="Import your college batch roster using the Student Import Wizard."
          action={
            <button
              onClick={() => setShowWizard(true)}
              className="px-4 py-2 bg-brand-600 text-white text-xs font-semibold rounded-xl hover:bg-brand-700"
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
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
                <th className="px-5 py-3.5">Roll No</th>
                <th className="px-5 py-3.5">Candidate Name</th>
                <th className="px-5 py-3.5">Branch</th>
                <th className="px-5 py-3.5">CGPA</th>
                <th className="px-5 py-3.5">10th / 12th</th>
                <th className="px-5 py-3.5">Backlogs</th>
                <th className="px-5 py-3.5">Offers</th>
                <th className="px-5 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.slice(0, 100).map((s: any) => (
                <tr key={s.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="px-5 py-3.5 font-mono font-bold text-slate-900">{s.roll_no}</td>
                  <td className="px-5 py-3.5 font-semibold text-slate-800">{s.name}</td>
                  <td className="px-5 py-3.5 text-slate-600 font-medium">{s.branch}</td>
                  <td className="px-5 py-3.5 font-mono font-bold text-brand-700">{typeof s.cgpa === "number" ? s.cgpa.toFixed(2) : s.cgpa}</td>
                  <td className="px-5 py-3.5 text-slate-600">
                    {s.tenth_percentage}% / {s.twelfth_percentage ? `${s.twelfth_percentage}%` : (s.diploma_percentage ? `${s.diploma_percentage}% (Dip)` : "—")}
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
                      onClick={() => handleIssueAccessCode(s.roll_no)}
                      className="px-2.5 py-1 text-xs font-semibold text-brand-700 bg-brand-50 hover:bg-brand-100 rounded-lg transition-colors inline-flex items-center gap-1"
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
          {filtered.length > 100 && (
            <div className="p-3 bg-slate-50 border-t border-slate-200 text-center text-xs font-bold text-slate-500">
              Showing first 100 results for ultra-responsive rendering ({filtered.length} total matched). Use the search bar or branch filter above to narrow down instantly.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
