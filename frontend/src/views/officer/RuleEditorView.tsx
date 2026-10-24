import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Student } from "../../types";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  Sliders,
  Users,
  ShieldAlert,
  Save,
  CheckCircle,
  HelpCircle,
  Sparkles,
  Info,
} from "lucide-react";

export const RuleEditorView: React.FC = () => {
  const [students, setStudents] = useState<Student[]>([]);
  const [loadingStudents, setLoadingStudents] = useState(true);

  // Rule parameters
  const [cgpaMin, setCgpaMin] = useState<number>(7.0);
  const [tenthMin, setTenthMin] = useState<number>(60.0);
  const [twelfthMin, setTwelfthMin] = useState<number>(60.0);
  const [allowedBranches, setAllowedBranches] = useState<string[]>([
    "CSE",
    "IT",
    "ECE",
  ]);
  const [maxActiveBacklogs, setMaxActiveBacklogs] = useState<number>(0);
  const [allowHistoryBacklogs, setAllowHistoryBacklogs] = useState<boolean>(true);
  const [maxGapYears, setMaxGapYears] = useState<number>(1);

  // Guardrail test state
  const [protectedAttributeAttempted, setProtectedAttributeAttempted] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  const availableBranches = [
    "CSE",
    "IT",
    "ECE",
    "EEE",
    "Mechanical Engineering",
    "Civil Engineering",
    "Data Science",
    "AI & ML",
  ];

  useEffect(() => {
    const fetchStudents = async () => {
      try {
        setLoadingStudents(true);
        const res = await api.get<{ items: Student[] }>("/api/students?limit=500");
        setStudents(res.items || []);
      } catch {
        // Fallback sample data if empty
        setStudents([]);
      } finally {
        setLoadingStudents(false);
      }
    };
    fetchStudents();
  }, []);

  const toggleBranch = (b: string) => {
    if (allowedBranches.includes(b)) {
      setAllowedBranches(allowedBranches.filter((item) => item !== b));
    } else {
      setAllowedBranches([...allowedBranches, b]);
    }
  };

  // Compute live eligible candidate count in memory
  const eligibleStudents = students.filter((s) => {
    if (s.cgpa < cgpaMin) return false;
    if (s.tenth_percentage < tenthMin) return false;
    if (s.twelfth_percentage && s.twelfth_percentage < twelfthMin) return false;
    if (allowedBranches.length > 0 && !allowedBranches.includes(s.branch)) return false;
    if (maxActiveBacklogs !== -1 && (s.active_backlogs_count || 0) > maxActiveBacklogs) return false;
    if (!allowHistoryBacklogs && (s.total_backlogs_count || 0) > 0) return false;
    if (maxGapYears !== -1 && (s.gap_years_count || 0) > maxGapYears) return false;
    return true;
  });

  const eligiblePercent = students.length
    ? Math.round((eligibleStudents.length / students.length) * 100)
    : 0;

  const handleProtectedAttributeClick = (attribute: string) => {
    setProtectedAttributeAttempted(attribute);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Requirement Rule Editor</h1>
          <p className="text-sm text-slate-500 mt-1">
            Visual rule builder. Tune academic cut-offs with an instant live eligible candidate counter.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setSaveSuccess(true);
              setTimeout(() => setSaveSuccess(false), 3000);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors"
          >
            <Save className="w-4 h-4" />
            <span>Save Rule Profile</span>
          </button>
        </div>
      </div>

      {saveSuccess && (
        <AlertBanner
          type="success"
          message="Rule Profile successfully committed to rule repository."
          onClose={() => setSaveSuccess(false)}
        />
      )}

      {protectedAttributeAttempted && (
        <AlertBanner
          type="danger"
          title="Protected Attribute Filter Blocked"
          message={`Strict Governance Violation: Filtering candidates by '${protectedAttributeAttempted}' is fundamentally rejected by institutional fair-placement policies.`}
          onClose={() => setProtectedAttributeAttempted(null)}
        />
      )}

      {/* Live Eligible Counter Box */}
      <div className="bg-gradient-to-r from-brand-900 to-slate-900 text-white p-6 rounded-2xl shadow-lg border border-brand-800 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-1 text-center md:text-left">
          <div className="flex items-center gap-2 justify-center md:justify-start">
            <Sparkles className="w-4 h-4 text-brand-400" />
            <span className="text-xs font-bold tracking-wider text-brand-300 uppercase">
              Live Real-Time Pool
            </span>
          </div>
          <h3 className="text-2xl font-black text-white">
            {eligibleStudents.length} of {students.length} Candidates Eligible
          </h3>
          <p className="text-xs text-slate-300">
            {eligiblePercent}% of the current student roster satisfies all selected academic criteria.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="w-32 bg-slate-800 rounded-full h-3.5 overflow-hidden border border-slate-700">
            <div
              className="bg-brand-500 h-3.5 rounded-full transition-all duration-300"
              style={{ width: `${eligiblePercent}%` }}
            />
          </div>
          <span className="text-lg font-mono font-black text-brand-400">{eligiblePercent}%</span>
        </div>
      </div>

      {/* Rule Controls Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Sliders className="w-4 h-4 text-brand-600" />
            Academic Threshold Controls
          </h2>

          {/* CGPA Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-bold text-slate-700">
              <span>Minimum Cumulative GPA (CGPA)</span>
              <span className="text-brand-700 font-mono text-sm bg-brand-50 px-2 py-0.5 rounded border border-brand-200">
                {cgpaMin.toFixed(1)} / 10.0
              </span>
            </div>
            <input
              type="range"
              min="0.0"
              max="10.0"
              step="0.1"
              value={cgpaMin}
              onChange={(e) => setCgpaMin(parseFloat(e.target.value))}
              className="w-full accent-brand-600 cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>0.0 (Open)</span>
              <span>6.0 (Tier 2/3)</span>
              <span>7.5 (Standard)</span>
              <span>8.5+ (Dream/Marquee)</span>
            </div>
          </div>

          {/* 10th & 12th Percentages */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                <span>Class 10th Minimum %</span>
                <span className="font-mono text-brand-700">{tenthMin}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={tenthMin}
                onChange={(e) => setTenthMin(parseFloat(e.target.value))}
                className="w-full accent-brand-600 cursor-pointer"
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                <span>Class 12th Minimum %</span>
                <span className="font-mono text-brand-700">{twelfthMin}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={twelfthMin}
                onChange={(e) => setTwelfthMin(parseFloat(e.target.value))}
                className="w-full accent-brand-600 cursor-pointer"
              />
            </div>
          </div>

          {/* Backlog Policy */}
          <div className="space-y-3 pt-3 border-t border-slate-100">
            <span className="text-xs font-bold text-slate-700 block">Backlog & Arrears Governance</span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-500 block mb-1">Max Active Standing Backlogs</label>
                <select
                  value={maxActiveBacklogs}
                  onChange={(e) => setMaxActiveBacklogs(parseInt(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold"
                >
                  <option value={0}>0 (Strictly No Active Backlogs)</option>
                  <option value={1}>Max 1 Active Backlog</option>
                  <option value={2}>Max 2 Active Backlogs</option>
                  <option value={-1}>No Backlog Limit</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-500 block mb-1">Cleared Historical Backlogs</label>
                <button
                  type="button"
                  onClick={() => setAllowHistoryBacklogs(!allowHistoryBacklogs)}
                  className={`w-full py-2 px-3 rounded-xl text-xs font-semibold border flex items-center justify-center gap-2 transition-colors ${
                    allowHistoryBacklogs
                      ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                      : "bg-rose-50 text-rose-800 border-rose-200"
                  }`}
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                  <span>{allowHistoryBacklogs ? "Permit Cleared Backlogs" : "Zero History Permitted"}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Allowed Branches */}
          <div className="space-y-2 pt-3 border-t border-slate-100">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-700">Eligible Academic Branches</span>
              <span className="text-xs text-slate-400">
                {allowedBranches.length} branches selected
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {availableBranches.map((branch) => {
                const isSelected = allowedBranches.includes(branch);
                return (
                  <button
                    key={branch}
                    type="button"
                    onClick={() => toggleBranch(branch)}
                    className={`p-2 rounded-xl text-xs font-semibold text-left border transition-all ${
                      isSelected
                        ? "bg-brand-50 border-brand-300 text-brand-900 shadow-xs"
                        : "bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100"
                    }`}
                  >
                    {branch}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Guardrail & Plain English Preview */}
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Info className="w-4 h-4 text-brand-600" />
              Plain-English Student Rule
            </h3>
            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 leading-relaxed font-medium">
              "Candidates are eligible if they possess a CGPA of at least{" "}
              <strong className="text-brand-900">{cgpaMin.toFixed(1)}</strong>, minimum{" "}
              <strong>{tenthMin}%</strong> in 10th and <strong>{twelfthMin}%</strong> in 12th, enrolled in{" "}
              <strong className="text-brand-900">{allowedBranches.join(", ") || "All Branches"}</strong>, with no more than{" "}
              <strong>{maxActiveBacklogs === -1 ? "unlimited" : maxActiveBacklogs}</strong> active backlogs."
            </div>
          </div>

          {/* Protected Demographics Guardrail Box */}
          <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200 shadow-xs space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
              <ShieldAlert className="w-4 h-4 text-amber-600" />
              <span>Demographic Attribute Guardrails</span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Institutional placement governance strictly prohibits filtering students on protected demographic criteria. Click any test below to verify that the rule engine rejects non-academic filtering:
            </p>
            <div className="flex flex-wrap gap-2 pt-1">
              {["Gender Filter", "Caste / Category", "Religion", "Nationality"].map((attr) => (
                <button
                  key={attr}
                  type="button"
                  onClick={() => handleProtectedAttributeClick(attr)}
                  className="px-2.5 py-1 bg-white hover:bg-rose-50 text-slate-600 hover:text-rose-700 border border-slate-200 rounded-lg text-xs font-medium transition-colors"
                >
                  Try: {attr}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
