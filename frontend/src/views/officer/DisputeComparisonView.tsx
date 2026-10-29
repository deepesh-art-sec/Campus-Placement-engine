import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Drive, Student } from "../../types";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import { GitCompare, Users, FileText, CheckCircle, XCircle } from "lucide-react";

export const DisputeComparisonView: React.FC = () => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<string>("");
  const [studentAId, setStudentAId] = useState<string>("");
  const [studentBId, setStudentBId] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [comparison, setComparison] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [drvRes, stuRes] = await Promise.all([
          api.get<Drive[]>("/api/drives"),
          api.get<{ items: Student[] }>("/api/students?limit=200"),
        ]);
        const drvList = Array.isArray(drvRes) ? drvRes : ((drvRes as any)?.items || []);
        setDrives(drvList);
        if (drvList.length > 0) setSelectedDriveId(drvList[0].id);

        const stuList = Array.isArray(stuRes) ? stuRes : ((stuRes as any)?.items || []);
        setStudents(stuList);
        if (stuList.length >= 2) {
          setStudentAId(stuList[0].id);
          setStudentBId(stuList[1].id);
        }
      } catch {
        setError("Failed to load candidate roster for comparison.");
      }
    };
    fetchData();
  }, []);

  const handleCompare = async () => {
    const effDriveId = selectedDriveId || (drives[0]?.id ?? "");
    const effStudentA = studentAId || (students[0]?.id ?? "");
    const effStudentB = studentBId || (students[1]?.id ?? students[0]?.id ?? "");
    if (!effDriveId || !effStudentA || !effStudentB) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.post<any>("/api/compare/students", {
        student_a_id: effStudentA,
        student_b_id: effStudentB,
        drive_id: effDriveId,
      });
      setComparison(res);
    } catch (err: any) {
      setError(err.message || "Failed to compare candidates.");
    } finally {
      setLoading(false);
    }
  };

  const studentA = students.find((s) => s.id === (studentAId || students[0]?.id));
  const studentB = students.find((s) => s.id === (studentBId || students[1]?.id));

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-black text-white tracking-tight">Student Dispute Comparison Explainer</h1>
        <p className="text-sm text-slate-400 mt-1">
          Objective side-by-side justification answering student eligibility disputes in writing, citing precise rule AST & policy clauses.
        </p>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}

      {/* Selectors */}
      <div className="bg-[#0d1527] p-6 rounded-2xl border border-[#1b2b4d] shadow-xl space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block mb-1">
              Recruitment Drive
            </label>
            <select
              value={selectedDriveId || drives[0]?.id || ""}
              onChange={(e) => setSelectedDriveId(e.target.value)}
              className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-semibold text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              {drives.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.company_name} ({d.ctc_lpa} LPA)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block mb-1">
              Candidate A
            </label>
            <select
              value={studentAId || students[0]?.id || ""}
              onChange={(e) => setStudentAId(e.target.value)}
              className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-semibold text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              {students.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.roll_no})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block mb-1">
              Candidate B (Disputing)
            </label>
            <select
              value={studentBId || students[1]?.id || ""}
              onChange={(e) => setStudentBId(e.target.value)}
              className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-semibold text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              {students.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.roll_no})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={handleCompare}
            disabled={loading || drives.length === 0 || students.length < 2}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 via-teal-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white text-xs font-bold rounded-xl shadow-lg transition-all cursor-pointer disabled:opacity-50"
          >
            <GitCompare className="w-4 h-4" />
            <span>{loading ? "Comparing..." : "Generate Dispute Explanation"}</span>
          </button>
        </div>
      </div>

      {/* Comparative Explainer Card */}
      {comparison && (
        <div className="bg-[#0d1527] p-6 rounded-2xl border border-[#1b2b4d] shadow-xl space-y-6">
          <div className="p-4 bg-emerald-950/40 border border-emerald-500/40 rounded-2xl">
            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 block mb-1 font-mono">
              Official Placement Cell Dispute Response
            </span>
            <p className="text-sm font-semibold text-slate-100 leading-relaxed">
              "{comparison.comparative_summary}"
            </p>
          </div>

          {/* Side-by-Side Comparison Table */}
          <div className="border border-[#1b2b4d] rounded-2xl overflow-x-auto bg-[#080e1c]">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#111d38] border-b border-[#1b2b4d] font-bold text-slate-300">
                  <th className="p-3 w-1/3">Evaluation Metric</th>
                  <th className="p-3 w-1/3 border-l border-[#1b2b4d] font-bold text-emerald-400">
                    Candidate A: {studentA?.name}
                  </th>
                  <th className="p-3 w-1/3 border-l border-[#1b2b4d] font-bold text-slate-200">
                    Candidate B: {studentB?.name}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1b2b4d]">
                <tr>
                  <td className="p-3 font-semibold text-slate-400">Roll Number</td>
                  <td className="p-3 font-mono border-l border-[#1b2b4d] text-slate-200">{studentA?.roll_no}</td>
                  <td className="p-3 font-mono border-l border-[#1b2b4d] text-slate-200">{studentB?.roll_no}</td>
                </tr>
                <tr>
                  <td className="p-3 font-semibold text-slate-400">Branch</td>
                  <td className="p-3 border-l border-[#1b2b4d] text-slate-200">{studentA?.branch}</td>
                  <td className="p-3 border-l border-[#1b2b4d] text-slate-200">{studentB?.branch}</td>
                </tr>
                <tr>
                  <td className="p-3 font-semibold text-slate-400">Cumulative GPA</td>
                  <td className="p-3 font-mono font-bold text-emerald-400 border-l border-[#1b2b4d]">
                    {studentA?.cgpa.toFixed(2)}
                  </td>
                  <td className="p-3 font-mono font-bold text-slate-300 border-l border-[#1b2b4d]">
                    {studentB?.cgpa.toFixed(2)}
                  </td>
                </tr>
                <tr>
                  <td className="p-3 font-semibold text-slate-400">Active Backlogs</td>
                  <td className="p-3 border-l border-[#1b2b4d] text-slate-200">{studentA?.active_backlogs_count || 0}</td>
                  <td className="p-3 border-l border-[#1b2b4d] text-slate-200">{studentB?.active_backlogs_count || 0}</td>
                </tr>
                <tr className="bg-[#111d38]/60">
                  <td className="p-3 font-bold text-white">Eligibility Verdict</td>
                  <td className="p-3 border-l border-[#1b2b4d] font-bold text-emerald-400">
                    {comparison.student_a_status || "Eligible"}
                  </td>
                  <td className="p-3 border-l border-[#1b2b4d] font-bold text-rose-400">
                    {comparison.student_b_status || "Ineligible"}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
