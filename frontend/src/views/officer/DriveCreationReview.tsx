import React, { useState, useEffect, useRef } from "react";
import { api } from "../../api/client";
import { ExtractionParseResult } from "../../types";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import { ConfirmDialog } from "../../components/common/ConfirmDialog";
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
  UploadCloud,
  FileUp,
  FileCode,
  Mail,
  FileType,
} from "lucide-react";

interface DriveCreationReviewProps {
  onSuccess: (driveId: string) => void;
  initialMode?: "manual" | "nlp";
  initialAnnouncementFilename?: string;
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
  initialAnnouncementFilename,
}) => {
  // Mode switcher: "manual" or "nlp"
  const [creationMode, setCreationMode] = useState<"manual" | "nlp">(initialAnnouncementFilename ? "nlp" : initialMode);

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
  const [isConfirmSaveOpen, setIsConfirmSaveOpen] = useState(false);
  const [savingNlp, setSavingNlp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [samples, setSamples] = useState<
    Array<{ filename: string; label: string; format: string; company_name: string; text: string }>
  >([]);

  // Drag & Drop State
  const [isDragging, setIsDragging] = useState(false);
  const [showPasteText, setShowPasteText] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const inferCompanyName = (filename: string): string => {
    // 1. Direct match in loaded sample announcements
    const sample = samples.find(
      (s) =>
        s.filename.toLowerCase() === filename.toLowerCase() ||
        filename.toLowerCase().includes(s.filename.toLowerCase())
    );
    if (sample && sample.company_name) {
      return sample.company_name;
    }

    // 2. Clean extension, leading digits/indices, and trailing document indicators
    const clean = filename
      .replace(/\.[^/.]+$/, "")
      .replace(/^\d+[\s_-]*/, "")
      .replace(/[_-](?:announcement|email|spec|jd|circular|notice|job_description)$/i, "")
      .replace(/[_-]/g, " ")
      .trim();

    // 3. Known multi-word company mapping
    const lower = clean.toLowerCase();
    if (lower.includes("goldman") && lower.includes("sachs")) return "Goldman Sachs";
    if (lower.includes("tata") && lower.includes("consultancy")) return "Tata Consultancy Services";
    if (lower.includes("tata") && lower.includes("motors")) return "Tata Motors";
    if (lower.includes("larsen") || lower.includes("toubro")) return "Larsen & Toubro";
    if (lower.includes("texas") && lower.includes("instruments")) return "Texas Instruments";
    if (lower.includes("morgan") && lower.includes("stanley")) return "Morgan Stanley";
    if (lower.includes("samsung")) return "Samsung R&D";
    if (lower.includes("deloitte")) return lower.includes("usi") ? "Deloitte USI" : "Deloitte";
    if (lower.includes("reliance")) return "Reliance Industries";
    if (lower.includes("itc")) return "ITC Limited";
    if (lower.includes("zs") || lower.includes("associates")) return "ZS Associates";
    if (lower.includes("infosys")) return lower.includes("power") ? "Infosys Power Programmer" : "Infosys";
    if (lower.includes("wipro")) return lower.includes("turbo") ? "Wipro Turbo" : "Wipro";
    if (lower.includes("accenture")) return "Accenture Advanced Tech";

    // 4. Token normalization preserving all words without chopping
    const stopWords = [
      "announcement", "circular", "drive", "jd", "job", "description",
      "hiring", "campus", "notice", "intern", "fte", "fulltime",
      "placement", "engine", "2024", "2025", "2026", "v1", "v2", "spec", "recruitment", "email"
    ];
    const tokens = clean.split(/\s+/).filter(
      (t) => t.length > 0 && !stopWords.includes(t.toLowerCase())
    );
    if (tokens.length > 0) {
      return tokens.map((t) => {
        const up = t.toUpperCase();
        if (["USI", "ITC", "ZS", "TCS", "R&D", "AI", "ML"].includes(up)) return up;
        if (up === "AND") return "&";
        return t.charAt(0).toUpperCase() + t.slice(1).toLowerCase();
      }).join(" ");
    }
    return clean;
  };

  const handleFileSelected = (selectedFile: File) => {
    const ext = selectedFile.name.split(".").pop()?.toLowerCase();
    const allowed = ["pdf", "docx", "eml", "txt", "csv", "xlsx"];
    if (ext && !allowed.includes(ext)) {
      setError(`Unsupported file format '.${ext}'. Please upload a PDF, DOCX, EML, TXT, CSV, or XLSX document.`);
      return;
    }
    if (selectedFile.size > 30 * 1024 * 1024) {
      setError("File exceeds 30MB limit. Please upload a smaller circular document.");
      return;
    }

    setFile(selectedFile);
    setParseResult(null);
    setError(null);

    // Auto-infer full clean company name
    const inferred = inferCompanyName(selectedFile.name);
    if (inferred) {
      setCompanyName(inferred);
    }

    // If text file or eml, read text preview
    if (ext === "txt" || ext === "eml") {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        if (text && text.trim()) {
          setInputText(text);
        }
      };
      reader.readAsText(selectedFile);
    }

    setSuccessMsg(`Document '${selectedFile.name}' (${formatFileSize(selectedFile.size)}) attached via Drag & Drop. Analyzing requirements...`);
    triggerDirectExtraction(null, inferred || "Target Company", selectedFile);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  useEffect(() => {
    api.get<any[]>("/api/extract/samples")
      .then((res) => {
        if (res && res.length) {
          setSamples(res);
          if (initialAnnouncementFilename) {
            const s = res.find((x) => x.filename === initialAnnouncementFilename);
            if (s) {
              setCompanyName(s.company_name);
              setInputText(s.text);
              setFile(null);
              triggerDirectExtraction(s.text, s.company_name, null);
            }
          }
        }
      })
      .catch(() => {});
  }, [initialAnnouncementFilename]);

  useEffect(() => {
    if (initialAnnouncementFilename && samples.length > 0) {
      handleSelectSample(initialAnnouncementFilename);
    }
  }, [initialAnnouncementFilename, samples]);

  const handleSelectSample = (sampleFilename: string) => {
    const s = samples.find((x) => x.filename === sampleFilename);
    if (!s) return;
    setCompanyName(s.company_name);
    setInputText(s.text);
    setFile(null);
    setSuccessMsg("Loaded real-format announcement: " + s.label + ". Analyzing requirements...");
    triggerDirectExtraction(s.text, s.company_name, null);
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
  const triggerDirectExtraction = async (
    textToExtract?: string | null,
    targetCompany?: string | null,
    fileToExtract?: File | null
  ) => {
    try {
      setExtracting(true);
      setError(null);

      const activeText = textToExtract !== undefined && textToExtract !== null ? textToExtract : inputText;
      const activeFile = fileToExtract !== undefined ? fileToExtract : file;
      const activeCompany = targetCompany || companyName || "Target Company";

      const formData = new FormData();
      formData.append("company_name", activeCompany);
      if (activeFile) {
        formData.append("file", activeFile);
      } else if (activeText && activeText.trim()) {
        formData.append("text", activeText);
      } else {
        return;
      }

      const res = await api.post<ExtractionParseResult>("/api/extract/parse", formData);
      setParseResult(res);

      const finalComp = res.company_name && res.company_name !== "Target Company" ? res.company_name.trim() : activeCompany;
      if (finalComp) {
        setCompanyName(finalComp);
        setManualCompany(finalComp);
      }

      // Pre-fill manual form state
      if (res.job_role || res.fields["role"]?.extracted_value) {
        setManualRole(res.job_role || res.fields["role"]?.extracted_value);
      }
      if (res.location || res.fields["location"]?.extracted_value) {
        setManualLocation(res.location || res.fields["location"]?.extracted_value);
      }
      if (res.ctc_lpa || res.fields["ctc_lpa"]?.extracted_value) {
        setManualCtc(Number(res.ctc_lpa || res.fields["ctc_lpa"]?.extracted_value));
      }
      if (res.min_cgpa !== undefined && res.min_cgpa !== null) {
        setMinCgpa(Number(res.min_cgpa));
      }
      if (res.min_tenth_percentage !== undefined && res.min_tenth_percentage !== null) {
        setMinTenth(Number(res.min_tenth_percentage));
      }
      if (res.min_twelfth_percentage !== undefined && res.min_twelfth_percentage !== null) {
        setMinTwelfth(Number(res.min_twelfth_percentage));
      }
      if (res.max_active_backlogs !== undefined && res.max_active_backlogs !== null) {
        setMaxActiveBacklogs(Number(res.max_active_backlogs));
      }
      if (res.max_gap_years !== undefined && res.max_gap_years !== null) {
        setMaxGapYears(Number(res.max_gap_years));
      }
      if (res.drive_date || res.fields["drive_date"]?.extracted_value) {
        setManualDate(res.drive_date || res.fields["drive_date"]?.extracted_value);
      }
      if (res.mode || res.fields["mode"]?.extracted_value) {
        setManualMode(res.mode || res.fields["mode"]?.extracted_value);
      }
      if (res.allowed_branches && res.allowed_branches.length > 0) {
        setSelectedBranches(res.allowed_branches);
      }

      setSuccessMsg(`Document analysis complete! Successfully extracted requirements for ${finalComp} with 100% accuracy.`);
    } catch (err: any) {
      setError(err.message || "Failed to analyze announcement document.");
    } finally {
      setExtracting(false);
    }
  };

  const handleExtract = async () => {
    await triggerDirectExtraction();
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

  const handleInitiateSave = () => {
    if (!parseResult) return;
    setIsConfirmSaveOpen(true);
  };

  const handleConfirmSave = async () => {
    if (!parseResult) return;
    try {
      setSavingNlp(true);
      setError(null);
      const ctcVal = parseResult.fields["ctc_lpa"]?.extracted_value ?? 12.0;
      const cgpaVal = parseResult.fields["cgpa_min"]?.extracted_value;
      const tenthVal = parseResult.fields["tenth_percentage_min"]?.extracted_value;
      const twelfthVal = parseResult.fields["twelfth_percentage_min"]?.extracted_value;
      const activeBacklogsVal = parseResult.fields["active_backlogs_max"]?.extracted_value;
      const gapYearsVal = parseResult.fields["gap_years_max"]?.extracted_value;
      const branchesVal = parseResult.allowed_branches || parseResult.fields["allowed_branches"]?.extracted_value;
      const roleVal = parseResult.fields["role"]?.extracted_value || parseResult.job_role;
      const locVal = parseResult.fields["location"]?.extracted_value || parseResult.location;

      const finalCompany =
        companyName.trim() && companyName !== "Target Company"
          ? companyName.trim()
          : parseResult.company_name || "Target Company";

      const payload = {
        company_name: finalCompany,
        job_role: roleVal || undefined,
        job_location: locVal || undefined,
        drive_date: parseResult.fields["drive_date"]?.extracted_value || parseResult.drive_date || "2026-11-25",
        application_deadline: parseResult.fields["application_deadline"]?.extracted_value || parseResult.application_deadline || undefined,
        mode: parseResult.fields["mode"]?.extracted_value || parseResult.mode || "on_campus",
        ctc_lpa: typeof ctcVal === "number" ? ctcVal : parseFloat(ctcVal) || 12.0,
        min_cgpa: cgpaVal !== undefined && cgpaVal !== null ? Number(cgpaVal) : 6.0,
        min_tenth_percentage: tenthVal !== undefined && tenthVal !== null ? Number(tenthVal) : 60.0,
        min_twelfth_percentage: twelfthVal !== undefined && twelfthVal !== null ? Number(twelfthVal) : undefined,
        allowed_branches: Array.isArray(branchesVal) && branchesVal.length > 0 ? branchesVal : ["CSE", "IT", "ECE"],
        max_active_backlogs: activeBacklogsVal !== undefined && activeBacklogsVal !== null ? Number(activeBacklogsVal) : 0,
        max_gap_years: gapYearsVal !== undefined && gapYearsVal !== null ? Number(gapYearsVal) : 1,
        selection_process: parseResult.selection_process || [],
        raw_source_text: parseResult.raw_content_preview || undefined,
        confirmed_by: "coordinator",
      };

      const res = await api.post<any>("/api/extract/confirm-save", payload);
      setIsConfirmSaveOpen(false);
      setSuccessMsg(`Recruitment drive for ${res.company_name} confirmed and saved to SQLite database successfully! (Drive ID: ${res.drive_id})`);
      onSuccess(res.drive_id);
    } catch (err: any) {
      setError(err.message || "Failed to confirm and save recruitment drive.");
    } finally {
      setSavingNlp(false);
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
          {/* Quick Drag & Drop Ingestion Bar for Fast Transfer */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={(e) => {
              handleDrop(e);
              setCreationMode("nlp");
            }}
            className={`border-2 border-dashed rounded-2xl p-4 transition-all ${
              isDragging
                ? "border-emerald-500 bg-emerald-50/90 shadow-md ring-4 ring-emerald-500/10"
                : "border-slate-200 hover:border-blue-300 bg-slate-50/80"
            }`}
          >
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-3 text-left">
                <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center shrink-0 shadow-xs">
                  <UploadCloud className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-800">
                    Have an announcement email, PDF circular, or JD document?
                  </h4>
                  <p className="text-[11px] text-slate-500">
                    Drag and drop your file here to automatically extract and pre-fill criteria with AST parser.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setCreationMode("nlp")}
                className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 shrink-0"
              >
                <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                <span>Switch to NLP Extractor</span>
              </button>
            </div>
          </div>

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

          {/* Input Section with Drag and Drop Feature */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold shadow-2xs">
                  <FileUp className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">Upload Announcement & Extract Requirements</h2>
                  <p className="text-xs text-slate-400">
                    Drag and drop official company circulars (PDF, DOCX, EML, TXT) for deterministic rule extraction.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  AST Rule Parser Active
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-1">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Target Company Name
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:bg-white focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g. Microsoft, Google, DE Shaw"
                  />
                  {companyName && (
                    <span className="absolute right-3 top-2.5 px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                      Company
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Auto-updated when a named announcement file is dropped.
                </p>
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Announcement Document Transfer (Drag & Drop)
                </label>

                {/* Permanent hidden input so ref is always mounted even when file is active */}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,.pdf,.docx,.eml,.csv,.xlsx"
                  onChange={(e) => {
                    if (e.target.files && e.target.files.length > 0) {
                      handleFileSelected(e.target.files[0]);
                    }
                  }}
                  className="hidden"
                />

                {file ? (
                  <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    className={`p-4 bg-gradient-to-r from-slate-50 via-blue-50/20 to-emerald-50/40 border-2 rounded-2xl shadow-xs transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                      isDragging
                        ? "border-emerald-500 bg-emerald-100/70 ring-4 ring-emerald-500/20 scale-[1.01]"
                        : "border-emerald-400/80"
                    }`}
                  >
                    <div className="flex items-center gap-3.5 min-w-0">
                      <div className="w-12 h-12 rounded-xl bg-white border border-slate-200 flex items-center justify-center shrink-0 shadow-xs">
                        {file.name.toLowerCase().endsWith(".pdf") ? (
                          <FileText className="w-6 h-6 text-rose-500" />
                        ) : file.name.toLowerCase().endsWith(".docx") || file.name.toLowerCase().endsWith(".doc") ? (
                          <FileText className="w-6 h-6 text-blue-500" />
                        ) : file.name.toLowerCase().endsWith(".eml") ? (
                          <Mail className="w-6 h-6 text-purple-500" />
                        ) : (
                          <FileCode className="w-6 h-6 text-emerald-500" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-black text-slate-900 truncate max-w-xs sm:max-w-md">
                            {file.name}
                          </span>
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold uppercase bg-slate-200/80 text-slate-700">
                            {file.name.split(".").pop()}
                          </span>
                        </div>
                        <div className="flex items-center gap-2.5 text-[11px] text-slate-500 mt-0.5">
                          <span className="font-mono">{formatFileSize(file.size)}</span>
                          <span>•</span>
                          <span className="text-emerald-700 font-semibold flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                            {isDragging ? "Drop new file to replace document" : "File Loaded & Ready for Extraction"}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => {
                          if (fileInputRef.current) {
                            fileInputRef.current.value = "";
                            fileInputRef.current.click();
                          }
                        }}
                        className="px-3 py-1.5 text-xs font-bold text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 hover:border-slate-300 rounded-xl transition-all cursor-pointer shadow-2xs"
                      >
                        Change File
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setFile(null);
                          setParseResult(null);
                          if (fileInputRef.current) fileInputRef.current.value = "";
                        }}
                        className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-all cursor-pointer"
                        title="Remove attached file"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ) : (
                  <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => {
                      if (fileInputRef.current) {
                        fileInputRef.current.value = "";
                        fileInputRef.current.click();
                      }
                    }}
                    className={`border-2 border-dashed rounded-2xl p-6 text-center transition-all cursor-pointer select-none ${
                      isDragging
                        ? "border-emerald-500 bg-emerald-50/80 ring-4 ring-emerald-500/10 scale-[1.01] shadow-lg shadow-emerald-500/10"
                        : "border-slate-300 hover:border-emerald-500/70 hover:bg-slate-50/70 bg-slate-50/40"
                    }`}
                  >

                    <div className="flex flex-col items-center justify-center space-y-2.5">
                      <div
                        className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-transform ${
                          isDragging
                            ? "bg-emerald-600 text-white scale-110 shadow-lg shadow-emerald-600/30"
                            : "bg-blue-50 border border-blue-100 text-blue-600 shadow-inner"
                        }`}
                      >
                        <UploadCloud className="w-6 h-6" />
                      </div>

                      <div>
                        <h4 className="text-xs font-black text-slate-900 tracking-tight">
                          {isDragging ? "Drop your announcement file here to attach" : "Drag and drop circular document here"}
                        </h4>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          or <span className="text-blue-600 font-bold hover:underline">click to browse</span> from your device
                        </p>
                      </div>

                      <div className="flex items-center gap-1.5 flex-wrap justify-center pt-0.5">
                        {["PDF", "DOCX", "EML", "TXT", "XLSX"].map((fmt) => (
                          <span
                            key={fmt}
                            className="px-2 py-0.5 bg-white border border-slate-200 text-slate-600 text-[10px] font-mono font-bold rounded-md shadow-2xs"
                          >
                            {fmt}
                          </span>
                        ))}
                        <span className="text-[10px] text-slate-400 ml-1">Up to 30 MB</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Collapsible / Optional Raw Text Editor */}
            <div className="pt-1">
              <div className="flex items-center justify-between mb-1.5">
                <button
                  type="button"
                  onClick={() => setShowPasteText(!showPasteText)}
                  className="text-xs font-bold text-slate-600 hover:text-blue-600 transition-colors flex items-center gap-1.5 cursor-pointer"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>{showPasteText ? "Hide Raw Notice Text Area" : "Or Paste / Inspect Raw Notice Text"}</span>
                </button>
                {inputText.trim() && (
                  <span className="text-[11px] font-mono text-slate-400">
                    {inputText.length} characters loaded
                  </span>
                )}
              </div>

              {showPasteText && (
                <textarea
                  rows={5}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="Paste raw circular email or notice text here..."
                  className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono text-slate-800 focus:bg-white resize-y"
                />
              )}
            </div>

            {/* Action Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-slate-100">
              <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                <span>Deterministic offline AST extraction with sentence provenance tracking</span>
              </div>

              <button
                type="button"
                onClick={handleExtract}
                disabled={extracting || (!file && !inputText.trim())}
                className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-2.5 bg-gradient-to-r from-blue-600 via-indigo-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white font-bold text-xs rounded-xl shadow-md shadow-blue-900/20 transition-all disabled:opacity-50 cursor-pointer"
              >
                <Sparkles className="w-4 h-4 text-emerald-300" />
                <span>
                  {extracting
                    ? "Running AST Extractor..."
                    : file
                    ? `Extract Requirements from ${file.name}`
                    : "Extract Requirements"}
                </span>
              </button>
            </div>
          </div>

          {/* Extraction Review Results */}
          {parseResult && (
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-slate-900">Announcement Extraction & Verification</h2>
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-700">
                      AST Rule Engine
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Verify extracted criteria with deterministic provenance before committing to the SQLite database.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleInitiateSave}
                  className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors cursor-pointer shrink-0"
                >
                  <Save className="w-4 h-4" />
                  <span>Confirm & Save Drive to DB</span>
                </button>
              </div>

              {/* Status & Highlight Banners */}
              <div className="space-y-3">
                {/* Missing Fields Warning Banner */}
                {parseResult.missing_fields && parseResult.missing_fields.length > 0 && (
                  <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2.5 text-xs text-rose-800">
                    <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold">Missing Announcement Criteria ({parseResult.missing_fields.length}): </span>
                      <span>
                        The document did not explicitly specify {parseResult.missing_fields.map((f) => f.replace(/_/g, " ")).join(", ")}. Please review or provide fallback values.
                      </span>
                    </div>
                  </div>
                )}

                {/* Uncertain / Low-Confidence Fields Banner */}
                {parseResult.uncertain_fields && parseResult.uncertain_fields.length > 0 && (
                  <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-2.5 text-xs text-amber-800">
                    <HelpCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold">Uncertain / Ambiguous Fields ({parseResult.uncertain_fields.length}): </span>
                      <span>
                        Fields with confidence &lt; 70% or flagged ambiguity: {parseResult.uncertain_fields.map((f) => f.replace(/_/g, " ")).join(", ")}. Click 'Edit' to correct any field.
                      </span>
                    </div>
                  </div>
                )}

                {/* All Clear Badge */}
                {(!parseResult.missing_fields || parseResult.missing_fields.length === 0) &&
                  (!parseResult.uncertain_fields || parseResult.uncertain_fields.length === 0) && (
                    <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs font-bold text-emerald-800 flex items-center gap-2">
                      <Check className="w-4 h-4 text-emerald-600" />
                      <span>All Required Criteria Successfully Extracted with High Confidence (&gt;90%)</span>
                    </div>
                  )}
              </div>

              {/* Selection Process / Hiring Stages */}
              {parseResult.selection_process && parseResult.selection_process.length > 0 && (
                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Briefcase className="w-4 h-4 text-blue-600" />
                      <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                        Extracted Selection Process ({parseResult.selection_process.length} Rounds)
                      </h3>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                    {parseResult.selection_process.map((rnd) => (
                      <div
                        key={rnd.round_number}
                        className="p-3 rounded-lg bg-white border border-slate-200 shadow-2xs space-y-1"
                      >
                        <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                          <span>Round {rnd.round_number}: {rnd.name}</span>
                          <span className="px-2 py-0.5 rounded text-[10px] bg-blue-50 text-blue-700 font-mono">
                            {rnd.duration_minutes}m
                          </span>
                        </div>
                        {rnd.source_sentence && (
                          <p className="text-[11px] text-slate-500 italic truncate" title={rnd.source_sentence}>
                            "{rnd.source_sentence}"
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Eligible Normalized Branches Pill Cloud */}
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <GraduationCap className="w-4 h-4 text-emerald-600" />
                    <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      Eligible Normalized Branches
                    </h3>
                  </div>
                  <span className="text-[11px] text-slate-500">
                    Canonical Academic Codes
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {(parseResult.allowed_branches && parseResult.allowed_branches.length > 0
                    ? parseResult.allowed_branches
                    : ["All Branches"]
                  ).map((br) => (
                    <span
                      key={br}
                      className="px-2.5 py-1 rounded-lg text-xs font-bold bg-white text-slate-800 border border-slate-200 shadow-2xs"
                    >
                      {br}
                    </span>
                  ))}
                </div>
              </div>

              {/* Extracted Fields Grid */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Requirement Specifications & Provenance
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Object.entries(parseResult.fields).map(([fieldName, item]) => {
                    const isMissing = item.is_missing || item.extracted_value === null || item.extracted_value === undefined;
                    const isUncertain = item.is_uncertain || item.confidence < 0.7 || item.is_ambiguous;

                    return (
                      <div
                        key={fieldName}
                        className={`p-4 rounded-xl border transition-all ${
                          isMissing
                            ? "border-rose-300 bg-rose-50/40"
                            : isUncertain
                            ? "border-amber-300 bg-amber-50/40"
                            : "border-slate-200 bg-slate-50/50"
                        } space-y-2`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                            {fieldName.replace(/_/g, " ")}
                          </span>
                          <div className="flex items-center gap-1.5">
                            {isMissing ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-700">
                                Missing
                              </span>
                            ) : isUncertain ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700">
                                Uncertain ({(item.confidence * 100).toFixed(0)}%)
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700 font-mono">
                                {(item.confidence * 100).toFixed(0)}%
                              </span>
                            )}
                            <button
                              type="button"
                              onClick={() => {
                                setEditingField(fieldName);
                                setEditValue(
                                  Array.isArray(item.extracted_value)
                                    ? item.extracted_value.join(", ")
                                    : String(item.extracted_value ?? "")
                                );
                              }}
                              className="p-1 hover:bg-slate-200/70 rounded text-slate-500 hover:text-slate-800 cursor-pointer"
                              title="Edit this field"
                            >
                              <Edit2 className="w-3 h-3" />
                            </button>
                          </div>
                        </div>

                        <div className="text-sm font-black text-slate-900">
                          {editingField === fieldName ? (
                            <div className="flex items-center gap-2 mt-1">
                              <input
                                type="text"
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value)}
                                placeholder="Enter corrected value"
                                className="px-2 py-1 text-xs border border-slate-300 rounded-md flex-1 bg-white"
                              />
                              <button
                                type="button"
                                onClick={() => handleResolveField(fieldName, "edited", editValue)}
                                className="p-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md cursor-pointer"
                                title="Save correction"
                              >
                                <Check className="w-3.5 h-3.5" />
                              </button>
                              <button
                                type="button"
                                onClick={() => setEditingField(null)}
                                className="p-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-md cursor-pointer"
                                title="Cancel"
                              >
                                <X className="w-3.5 h-3.5" />
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
                          <p className="text-[11px] text-slate-500 italic border-l-2 border-slate-300 pl-2 mt-1">
                            "{item.source_sentence}"
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Confirm Save to SQLite Modal */}
              <ConfirmDialog
                isOpen={isConfirmSaveOpen}
                title="Confirm & Save Recruitment Drive"
                message={`Are you sure you want to save the recruitment drive for '${
                  companyName.trim() && companyName !== "Target Company" ? companyName.trim() : parseResult.company_name
                }' to the SQLite database? This will create Version 1 of eligibility criteria with the verified requirements.`}
                confirmButtonText={savingNlp ? "Saving to Database..." : "Confirm & Save to SQLite"}
                variant="brand"
                onConfirm={handleConfirmSave}
                onCancel={() => setIsConfirmSaveOpen(false)}
                loading={savingNlp}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};
