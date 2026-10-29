import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { ExtractionParseResult } from "../../types";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  FileText,
  Upload,
  Check,
  Edit2,
  X,
  AlertTriangle,
  ArrowRight,
  Sparkles,
  Save,
  HelpCircle,
  PlusCircle,
  Sliders,
  Building,
  Briefcase,
  GraduationCap,
  Calendar,
  DollarSign,
  ShieldAlert,
  CheckCircle2,
  MapPin,
  Layers,
} from "lucide-react";

interface DriveCreationReviewProps {
  onSuccess: (driveId: string) => void;
  initialMode?: "manual" | "nlp";
}

const ALL_CAMPUS_BRANCHES = [
  "Computer Science and Engineering",
  "Information Technology",
  "Data Science",
  "Electronics and Communication Engineering",
  "Electrical and Electronics Engineering",
  "Mechanical Engineering",
  "Civil Engineering",
  "Chemical Engineering",
  "Biotechnology",
];

export const DriveCreationReview: React.FC<DriveCreationReviewProps> = ({
  onSuccess,
  initialMode = "nlp",
}) => {
  // Mode switcher: "manual" or "nlp"
  const [creationMode, setCreationMode] = useState<"manual" | "nlp">(initialMode);

  // -------------------------------------------------------------
  // Manual Drive Creation State
  // -------------------------------------------------------------
  const [manualCompany, setManualCompany] = useState("");
  const [manualRole, setManualRole] = useState("Software Development Engineer");
  const [manualCtc, setManualCtc] = useState<number>(14.0);
  const [manualFixedPay, setManualFixedPay] = useState<number | undefined>(12.0);
  const [manualDate, setManualDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 14);
    return d.toISOString().split("T")[0];
  });
  const [manualMode, setManualMode] = useState<"on_campus" | "virtual" | "hybrid">("on_campus");
  const [manualStatus, setManualStatus] = useState<"published" | "draft">("published");
  const [manualLocation, setManualLocation] = useState("Bangalore / Hyderabad");

  // Academic Criteria
  const [minCgpa, setMinCgpa] = useState<number>(7.0);
  const [minTenth, setMinTenth] = useState<number>(60.0);
  const [minTwelfth, setMinTwelfth] = useState<number>(60.0);
  const [minDiploma, setMinDiploma] = useState<number | undefined>(60.0);

  // Branch Selection
  const [selectedBranches, setSelectedBranches] = useState<string[]>([
    "Computer Science and Engineering",
    "Information Technology",
    "Data Science",
    "Electronics and Communication Engineering",
  ]);

  // Backlogs & Gaps
  const [maxActiveBacklogs, setMaxActiveBacklogs] = useState<number>(0);
  const [maxHistoryBacklogs, setMaxHistoryBacklogs] = useState<number | null>(0);
  const [maxGapYears, setMaxGapYears] = useState<number | null>(1);
  const [allowGapDuringDegree, setAllowGapDuringDegree] = useState<boolean>(false);

  const [savingManual, setSavingManual] = useState(false);

  // -------------------------------------------------------------
  // NLP Extraction State
  // -------------------------------------------------------------
  const [inputText, setInputText] = useState(
    "Google is hiring Software Engineering Interns & FTE for Campus 2026.\n" +
    "Compensation: CTC 35 LPA. Drive Date: 2026-11-25. Mode: On-Campus.\n" +
    "Eligibility Criteria:\n" +
    "- Minimum CGPA required is 8.0 with no standing backlogs.\n" +
    "- Minimum 70% in 10th and 12th standard.\n" +
    "- Eligible branches: Computer Science, IT, and Electronics.\n" +
    "- Maximum 1 year education gap allowed."
  );
  const [companyName, setCompanyName] = useState("Google");
  const [file, setFile] = useState<File | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [parseResult, setParseResult] = useState<ExtractionParseResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [samples, setSamples] = useState<
    Array<{ filename: string; label: string; format: string; company_name: string; text: string }>
  >([]);

  useEffect(() => {
    api.get<any[]>("/api/extract/samples")
      .then((res) => {
        if (res && res.length) setSamples(res);
      })
      .catch(() => {});
  }, []);

  const handleSelectSample = (sampleFilename: string) => {
    const s = samples.find((x) => x.filename === sampleFilename);
    if (!s) return;
    setCompanyName(s.company_name);
    setInputText(s.text);
    setFile(null);
    setParseResult(null);
    setSuccessMsg("Loaded real-format announcement: " + s.label);
  };

  // Branch Preset Helpers
  const handleSelectAllBranches = () => setSelectedBranches([...ALL_CAMPUS_BRANCHES]);
  const handleSelectCircuitsOnly = () =>
    setSelectedBranches([
      "Computer Science and Engineering",
      "Information Technology",
      "Data Science",
      "Electronics and Communication Engineering",
      "Electrical and Electronics Engineering",
    ]);
  const handleSelectCoreTechOnly = () =>
    setSelectedBranches([
      "Computer Science and Engineering",
      "Information Technology",
      "Data Science",
    ]);
  const handleClearBranches = () => setSelectedBranches([]);

  const toggleBranch = (b: string) => {
    if (selectedBranches.includes(b)) {
      setSelectedBranches(selectedBranches.filter((x) => x !== b));
    } else {
      setSelectedBranches([...selectedBranches, b]);
    }
  };

  // -------------------------------------------------------------
  // Manual Drive Submission
  // -------------------------------------------------------------
  const handleSubmitManualDrive = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualCompany.trim()) {
      setError("Please specify a target company name.");
      return;
    }
    if (selectedBranches.length === 0) {
      setError("Please select at least one eligible branch.");
      return;
    }

    try {
      setSavingManual(true);
      setError(null);

      const payload = {
        company_name: manualCompany.trim(),
        drive_date: manualDate,
        mode: manualMode,
        status: manualStatus,
        ctc_lpa: Number(manualCtc),
        fixed_pay_lpa: manualFixedPay ? Number(manualFixedPay) : undefined,
        job_role: manualRole.trim() || undefined,
        job_location: manualLocation.trim() || undefined,
        min_cgpa: Number(minCgpa),
        min_tenth_percentage: Number(minTenth),
        min_twelfth_percentage: Number(minTwelfth),
        min_diploma_percentage: minDiploma ? Number(minDiploma) : undefined,
        allowed_branches: selectedBranches,
        max_active_backlogs: Number(maxActiveBacklogs),
        max_history_backlogs: maxHistoryBacklogs !== null ? Number(maxHistoryBacklogs) : null,
        max_gap_years: maxGapYears !== null ? Number(maxGapYears) : null,
        allow_gap_during_degree: allowGapDuringDegree,
      };

      const res = await api.post<any>("/api/drives", payload);
      setSuccessMsg(`Recruitment drive for ${res.company_name} registered successfully with exact criteria!`);
      setTimeout(() => {
        onSuccess(res.id);
      }, 700);
    } catch (err: any) {
      setError(err.message || "Failed to create manual recruitment drive.");
    } finally {
      setSavingManual(false);
    }
  };

  // -------------------------------------------------------------
  // NLP Extraction Handlers
  // -------------------------------------------------------------
  const handleExtract = async () => {
    try {
      setExtracting(true);
      setError(null);

      const formData = new FormData();
      formData.append("company_name", companyName);
      if (file) {
        formData.append("file", file);
      } else {
        formData.append("text", inputText);
      }

      const res = await api.post<ExtractionParseResult>("/api/extract/parse", formData);
      setParseResult(res);
      setSuccessMsg("Requirements deterministically extracted with exact sentence provenance.");
    } catch (err: any) {
      setError(err.message || "Failed to parse announcement.");
    } finally {
      setExtracting(false);
    }
  };

  const handleResolveField = async (
    fieldName: string,
    status: "accepted" | "edited" | "rejected",
    correctedValue?: any
  ) => {
    if (!parseResult) return;
    try {
      await api.post("/api/extract/review/resolve", {
        announcement_id: parseResult.announcement_id,
        field_name: fieldName,
        status: status,
        corrected_value: correctedValue,
        source_text: parseResult.fields[fieldName]?.source_sentence || "",
        extracted_value: parseResult.fields[fieldName]?.extracted_value,
      });

      setParseResult((prev) => {
        if (!prev) return null;
        const updatedFields = { ...prev.fields };
        if (updatedFields[fieldName]) {
          if (status === "edited") {
            updatedFields[fieldName].extracted_value = correctedValue;
          }
        }
        return {
          ...prev,
          fields: updatedFields,
          review_queue: prev.review_queue.filter((q) => q.field_name !== fieldName),
        };
      });

      setEditingField(null);
    } catch (err: any) {
      setError(err.message || "Failed to record review decision.");
    }
  };

  const handleSaveNlpDrive = async () => {
    if (!parseResult) return;
    try {
      setError(null);
      const ctcVal = parseResult.fields["ctc_lpa"]?.extracted_value || 12.0;
      const res = await api.post<any>("/api/drives", {
        company_name: parseResult.company_name || companyName,
        drive_date: parseResult.fields["drive_date"]?.extracted_value || "2026-11-25",
        mode: parseResult.fields["mode"]?.extracted_value || "on_campus",
        ctc_lpa: typeof ctcVal === "number" ? ctcVal : parseFloat(ctcVal) || 12.0,
      });

      setSuccessMsg(`Recruitment drive for ${res.company_name} created successfully!`);
      onSuccess(res.id);
    } catch (err: any) {
      setError(err.message || "Failed to create recruitment drive.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header & Mode Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Requirement Extraction & Review</h1>
          <p className="text-sm text-slate-500 mt-1">
            Configure recruitment drives manually with exact eligibility criteria or extract automatically from circulars.
          </p>
        </div>

        {/* Tab Switcher: Manual vs NLP */}
        <div className="flex items-center bg-white p-1 rounded-2xl border border-slate-200/80 shadow-xs self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setCreationMode("manual")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              creationMode === "manual"
                ? "bg-slate-900 text-white shadow-2xs"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Manual Drive Entry</span>
          </button>
          <button
            type="button"
            onClick={() => setCreationMode("nlp")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              creationMode === "nlp"
                ? "bg-slate-900 text-white shadow-2xs"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            <span>Extract from Notice (NLP)</span>
          </button>
        </div>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {successMsg && <AlertBanner type="success" message={successMsg} onClose={() => setSuccessMsg(null)} />}

      {/* ========================================================= */}
      {/* MODE 1: MANUAL DRIVE CREATION WITH ELIGIBILITY CRITERIA  */}
      {/* ========================================================= */}
      {creationMode === "manual" && (
        <form onSubmit={handleSubmitManualDrive} className="space-y-6">
          {/* Card 1: Company & Job Profile */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
            <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100">
              <div className="w-8 h-8 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
                <Building className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-900">Company & Drive Profile</h2>
                <p className="text-xs text-slate-400">Core organizational information and compensation package.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Target Company Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={manualCompany}
                  onChange={(e) => setManualCompany(e.target.value)}
                  placeholder="e.g. Oracle, Microsoft, DE Shaw"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:bg-white focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Job Role / Title
                </label>
                <input
                  type="text"
                  value={manualRole}
                  onChange={(e) => setManualRole(e.target.value)}
                  placeholder="e.g. Software Development Engineer"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:bg-white focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Job Location(s)
                </label>
                <input
                  type="text"
                  value={manualLocation}
                  onChange={(e) => setManualLocation(e.target.value)}
                  placeholder="e.g. Bangalore / Hyderabad / Pune"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:bg-white focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Total CTC Package (LPA) <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    required
                    value={manualCtc}
                    onChange={(e) => setManualCtc(parseFloat(e.target.value) || 0)}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:bg-white focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="absolute right-3.5 top-2.5 text-xs font-bold text-slate-400">LPA</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Fixed Component (LPA)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={manualFixedPay || ""}
                    onChange={(e) => setManualFixedPay(e.target.value ? parseFloat(e.target.value) : undefined)}
                    placeholder="Optional"
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:bg-white focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="absolute right-3.5 top-2.5 text-xs font-bold text-slate-400">LPA</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Drive Scheduled Date <span className="text-rose-500">*</span>
                </label>
                <input
                  type="date"
                  required
                  value={manualDate}
                  onChange={(e) => setManualDate(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:bg-white focus:ring-2 focus:ring-blue-500 cursor-pointer"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Drive Mode
                </label>
                <select
                  value={manualMode}
                  onChange={(e) => setManualMode(e.target.value as any)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:bg-white focus:ring-2 focus:ring-blue-500 cursor-pointer"
                >
                  <option value="on_campus">On-Campus Physical</option>
                  <option value="virtual">Virtual / Remote</option>
                  <option value="hybrid">Hybrid (Online Test + In-Person Interviews)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Initial Publication Status
                </label>
                <select
                  value={manualStatus}
                  onChange={(e) => setManualStatus(e.target.value as any)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:bg-white focus:ring-2 focus:ring-blue-500 cursor-pointer"
                >
                  <option value="published">Published (Visible immediately on Student Portal)</option>
                  <option value="draft">Draft (Private to Placement Cell)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Card 2: Academic Eligibility Cutoffs */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
            <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100">
              <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
                <GraduationCap className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-900">Academic & Marks Eligibility Criteria</h2>
                <p className="text-xs text-slate-400">Strict cutoff thresholds evaluated deterministically per student.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-5">
              {/* CGPA */}
              <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-700">Min CGPA</span>
                  <span className="text-sm font-black text-emerald-700 font-mono">{minCgpa.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="5.0"
                  max="10.0"
                  step="0.05"
                  value={minCgpa}
                  onChange={(e) => setMinCgpa(parseFloat(e.target.value))}
                  className="w-full accent-emerald-600 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>5.0</span>
                  <span>7.0</span>
                  <span>10.0</span>
                </div>
              </div>

              {/* 10th Standard */}
              <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-700">Min 10th Standard</span>
                  <span className="text-sm font-black text-blue-700 font-mono">{minTenth.toFixed(1)}%</span>
                </div>
                <input
                  type="range"
                  min="40"
                  max="100"
                  step="1"
                  value={minTenth}
                  onChange={(e) => setMinTenth(parseFloat(e.target.value))}
                  className="w-full accent-blue-600 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>40%</span>
                  <span>60%</span>
                  <span>100%</span>
                </div>
              </div>

              {/* 12th Standard */}
              <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-700">Min 12th Standard</span>
                  <span className="text-sm font-black text-indigo-700 font-mono">{minTwelfth.toFixed(1)}%</span>
                </div>
                <input
                  type="range"
                  min="40"
                  max="100"
                  step="1"
                  value={minTwelfth}
                  onChange={(e) => setMinTwelfth(parseFloat(e.target.value))}
                  className="w-full accent-indigo-600 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>40%</span>
                  <span>60%</span>
                  <span>100%</span>
                </div>
              </div>

              {/* Diploma Lateral */}
              <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-700">Min Diploma %</span>
                  <span className="text-sm font-black text-purple-700 font-mono">
                    {minDiploma !== undefined ? `${minDiploma.toFixed(1)}%` : "N/A"}
                  </span>
                </div>
                <input
                  type="range"
                  min="40"
                  max="100"
                  step="1"
                  value={minDiploma || 60}
                  onChange={(e) => setMinDiploma(parseFloat(e.target.value))}
                  className="w-full accent-purple-600 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>40%</span>
                  <span>60%</span>
                  <span>100%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Card 3: Eligible Academic Branches */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-purple-100 text-purple-700 flex items-center justify-center font-bold">
                  <Layers className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">Allowed Engineering Branches</h2>
                  <p className="text-xs text-slate-400">
                    {selectedBranches.length} of {ALL_CAMPUS_BRANCHES.length} branches selected for eligibility.
                  </p>
                </div>
              </div>

              {/* Quick Presets */}
              <div className="flex items-center gap-1.5 flex-wrap">
                <button
                  type="button"
                  onClick={handleSelectAllBranches}
                  className="px-2.5 py-1 text-[11px] font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors cursor-pointer"
                >
                  All Branches
                </button>
                <button
                  type="button"
                  onClick={handleSelectCircuitsOnly}
                  className="px-2.5 py-1 text-[11px] font-bold bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg transition-colors cursor-pointer"
                >
                  Circuits & Tech (CSE, IT, DS, ECE, EEE)
                </button>
                <button
                  type="button"
                  onClick={handleSelectCoreTechOnly}
                  className="px-2.5 py-1 text-[11px] font-bold bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-lg transition-colors cursor-pointer"
                >
                  Core Tech (CSE, IT, DS)
                </button>
                <button
                  type="button"
                  onClick={handleClearBranches}
                  className="px-2.5 py-1 text-[11px] font-bold bg-slate-100 hover:bg-rose-100 text-slate-500 hover:text-rose-700 rounded-lg transition-colors cursor-pointer"
                >
                  Clear All
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {ALL_CAMPUS_BRANCHES.map((branch) => {
                const isSelected = selectedBranches.includes(branch);
                return (
                  <button
                    key={branch}
                    type="button"
                    onClick={() => toggleBranch(branch)}
                    className={`p-3 rounded-xl border text-left text-xs font-bold transition-all flex items-center justify-between cursor-pointer ${
                      isSelected
                        ? "bg-blue-50/80 border-blue-400 text-blue-900 shadow-2xs"
                        : "bg-slate-50 border-slate-200 text-slate-500 hover:border-slate-300"
                    }`}
                  >
                    <span className="truncate pr-2">{branch}</span>
                    <div
                      className={`w-5 h-5 rounded-md flex items-center justify-center shrink-0 ${
                        isSelected ? "bg-blue-600 text-white" : "border border-slate-300"
                      }`}
                    >
                      {isSelected && <Check className="w-3.5 h-3.5" />}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Card 4: Backlog Cutoffs & Education Gap Rules */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
            <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100">
              <div className="w-8 h-8 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center font-bold">
                <ShieldAlert className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-900">Backlogs & Education Gap Guardrails</h2>
                <p className="text-xs text-slate-400">Company policy on standing backlogs, cleared backlogs, and academic gaps.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {/* Active Backlogs */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Active (Standing) Backlogs Allowed
                </label>
                <div className="grid grid-cols-4 gap-1.5">
                  {[
                    { label: "0 (Strict)", val: 0 },
                    { label: "Max 1", val: 1 },
                    { label: "Max 2", val: 2 },
                    { label: "Any", val: 99 },
                  ].map((opt) => (
                    <button
                      key={opt.val}
                      type="button"
                      onClick={() => setMaxActiveBacklogs(opt.val)}
                      className={`py-2 px-1 text-center rounded-xl text-xs font-bold transition-all cursor-pointer ${
                        maxActiveBacklogs === opt.val
                          ? "bg-amber-600 text-white shadow-2xs"
                          : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* History Backlogs */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Cleared (History) Backlogs Allowed
                </label>
                <div className="grid grid-cols-4 gap-1.5">
                  {[
                    { label: "0 History", val: 0 },
                    { label: "Max 1", val: 1 },
                    { label: "Max 2", val: 2 },
                    { label: "No Limit", val: null },
                  ].map((opt, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setMaxHistoryBacklogs(opt.val)}
                      className={`py-2 px-1 text-center rounded-xl text-xs font-bold transition-all cursor-pointer ${
                        maxHistoryBacklogs === opt.val
                          ? "bg-amber-600 text-white shadow-2xs"
                          : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Gap Years */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Max Education Gap Years
                </label>
                <div className="grid grid-cols-4 gap-1.5">
                  {[
                    { label: "0 Gaps", val: 0 },
                    { label: "1 Year", val: 1 },
                    { label: "2 Years", val: 2 },
                    { label: "No Limit", val: null },
                  ].map((opt, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setMaxGapYears(opt.val)}
                      className={`py-2 px-1 text-center rounded-xl text-xs font-bold transition-all cursor-pointer ${
                        maxGapYears === opt.val
                          ? "bg-amber-600 text-white shadow-2xs"
                          : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="pt-2">
              <label className="flex items-center gap-2 cursor-pointer text-xs font-bold text-slate-700">
                <input
                  type="checkbox"
                  checked={allowGapDuringDegree}
                  onChange={(e) => setAllowGapDuringDegree(e.target.checked)}
                  className="rounded-md border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <span>Allow education gap during college degree (e.g. medical leave or semester drop)</span>
              </label>
            </div>
          </div>

          {/* Card 5: Summary Preview & Action Button */}
          <div className="p-5 bg-gradient-to-r from-blue-900/20 via-slate-900/30 to-emerald-900/20 rounded-2xl border border-blue-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="text-xs font-bold text-white flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Deterministic Criteria Preview</span>
              </div>
              <p className="text-xs text-slate-400">
                {manualCompany ? manualCompany : "Target Company"} • {manualCtc} LPA • CGPA &ge; {minCgpa} • 10th &ge; {minTenth}% • 12th &ge; {minTwelfth}% • Max {maxActiveBacklogs} Backlogs • {selectedBranches.length} Branches
              </p>
            </div>

            <button
              type="submit"
              disabled={savingManual}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-emerald-900/30 transition-all cursor-pointer disabled:opacity-50 shrink-0"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>{savingManual ? "Registering Drive..." : "Register & Publish Recruitment Drive"}</span>
            </button>
          </div>
        </form>
      )}

      {/* ========================================================= */}
      {/* MODE 2: NLP CIRCULAR & DOCUMENT EXTRACTION                */}
      {/* ========================================================= */}
      {creationMode === "nlp" && (
        <div className="space-y-6">
          {/* 25 Real-Format Drive Announcements Sample Selector */}
          {samples.length > 0 && (
            <div className="bg-gradient-to-r from-[#0d1527] to-[#121e38] border border-[#1b2b4d] rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-slate-100 shadow-md">
              <div className="flex items-center gap-2.5">
                <Sparkles className="w-4 h-4 text-emerald-400 shrink-0" />
                <div>
                  <div className="text-xs font-bold text-white">25 Real-Format Drive Announcements (Emails, PDFs, DOCXs)</div>
                  <div className="text-[11px] text-slate-400">Anonymised company emails, PDFs & specifications received by placement cells.</div>
                </div>
              </div>
              <select
                onChange={(e) => e.target.value && handleSelectSample(e.target.value)}
                defaultValue=""
                className="px-3 py-1.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-semibold text-emerald-300 focus:outline-none cursor-pointer max-w-xs"
              >
                <option value="" disabled>Choose Announcement (1 of 25)...</option>
                {samples.map((s) => (
                  <option key={s.filename} value={s.filename}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Input Section */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-1">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Target Company Name
                </label>
                <input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:bg-white"
                  placeholder="e.g. Microsoft, Google, DE Shaw"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Upload Announcement Document (PDF, DOCX, EML, TXT)
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="file"
                    accept=".txt,.pdf,.docx,.eml"
                    onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
                    className="text-xs text-slate-500 file:mr-3 file:py-2 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 cursor-pointer"
                  />
                  {file && (
                    <button
                      type="button"
                      onClick={() => setFile(null)}
                      className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 cursor-pointer"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Paste Announcement Email, Notice, or JD
              </label>
              <textarea
                rows={5}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Paste the raw circular text here..."
                className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono text-slate-800 focus:bg-white resize-y"
              />
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={handleExtract}
                disabled={extracting}
                className="flex items-center gap-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
              >
                <Sparkles className="w-4 h-4" />
                <span>{extracting ? "Running Deterministic AST Extractor..." : "Extract Requirements"}</span>
              </button>
            </div>
          </div>

          {/* Extraction Review Results */}
          {parseResult && (
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                <div>
                  <h2 className="text-base font-bold text-slate-900">Side-by-Side Field Provenance</h2>
                  <p className="text-xs text-slate-500">Every requirement maps to a verified AST condition.</p>
                </div>
                <button
                  type="button"
                  onClick={handleSaveNlpDrive}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors cursor-pointer"
                >
                  <Save className="w-4 h-4" />
                  <span>Save & Create Drive</span>
                </button>
              </div>

              {/* Review Queue Alerts */}
              {(!parseResult.review_queue || parseResult.review_queue.length === 0) && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs font-bold text-emerald-800 flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600" />
                  <span>All Fields Validated</span>
                </div>
              )}
              {parseResult.review_queue && parseResult.review_queue.length > 0 && (
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-amber-800">
                    <AlertTriangle className="w-4 h-4 text-amber-600" />
                    <span>Requires Officer Review ({parseResult.review_queue.length} ambiguous items)</span>
                  </div>
                  <div className="space-y-1.5 pl-6">
                    {parseResult.review_queue.map((q) => (
                      <div key={q.field_name} className="text-xs text-amber-700 flex items-center justify-between">
                        <span>
                          <strong className="capitalize">{q.field_name.replace(/_/g, " ")}</strong>: "{q.source_sentence}"
                        </span>
                        <div className="flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => handleResolveField(q.field_name, "accepted")}
                            className="px-2 py-0.5 bg-emerald-600 text-white rounded-md text-[10px] font-bold"
                          >
                            Accept
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingField(q.field_name)}
                            className="px-2 py-0.5 bg-slate-200 text-slate-800 rounded-md text-[10px] font-bold"
                          >
                            Edit
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Extracted Fields Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(parseResult.fields).map(([fieldName, item]) => (
                  <div
                    key={fieldName}
                    className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                        {fieldName.replace(/_/g, " ")}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        Confidence: {(item.confidence * 100).toFixed(0)}%
                      </span>
                    </div>

                    <div className="text-sm font-black text-slate-900">
                      {editingField === fieldName ? (
                        <div className="flex items-center gap-2 mt-1">
                          <input
                            type="text"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            placeholder="Corrected value"
                            className="px-2 py-1 text-xs border border-slate-300 rounded-md flex-1"
                          />
                          <button
                            type="button"
                            onClick={() => handleResolveField(fieldName, "edited", editValue)}
                            className="p-1 bg-emerald-600 text-white rounded-md"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ) : (
                        <span>
                          {Array.isArray(item.extracted_value)
                            ? item.extracted_value.join(", ")
                            : String(item.extracted_value ?? "Not specified")}
                        </span>
                      )}
                    </div>

                    {item.source_sentence && (
                      <p className="text-[11px] text-slate-500 italic border-l-2 border-slate-200 pl-2 mt-1">
                        "{item.source_sentence}"
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
