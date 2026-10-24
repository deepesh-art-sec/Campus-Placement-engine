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
} from "lucide-react";

interface DriveCreationReviewProps {
  onSuccess: (driveId: string) => void;
}

export const DriveCreationReview: React.FC<DriveCreationReviewProps> = ({ onSuccess }) => {
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
  const [samples, setSamples] = useState<Array<{ filename: string; label: string; format: string; company_name: string; text: string }>>([]);

  useEffect(() => {
    api.get<any[]>("/api/extract/samples").then((res) => {
      if (res && res.length) setSamples(res);
    }).catch(() => {});
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

  const handleResolveField = async (fieldName: string, status: "accepted" | "edited" | "rejected", correctedValue?: any) => {
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

      // Update local state
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

  const handleSaveDrive = async () => {
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
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Requirement Extraction & Review</h1>
        <p className="text-sm text-slate-500 mt-1">
          Zero manual re-typing. Paste messy company emails, JDs, or upload PDFs/DOCXs for deterministic AST extraction.
        </p>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {successMsg && <AlertBanner type="success" message={successMsg} onClose={() => setSuccessMsg(null)} />}

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
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold text-slate-800 focus:bg-white"
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
                  onClick={() => setFile(null)}
                  className="text-xs text-rose-600 hover:underline"
                >
                  Clear file
                </button>
              )}
            </div>
          </div>
        </div>

        {!file && (
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Or Paste Announcement Email / Notice Text
            </label>
            <textarea
              rows={5}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              className="w-full p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono text-slate-800 focus:bg-white leading-relaxed"
              placeholder="Paste email content with eligibility criteria..."
            />
          </div>
        )}

        <div className="flex items-center justify-end">
          <button
            onClick={handleExtract}
            disabled={extracting}
            className="flex items-center gap-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold rounded-xl shadow-xs transition-colors disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            <span>{extracting ? "Extracting Offline..." : "Extract Requirements"}</span>
          </button>
        </div>
      </div>

      {/* Side-by-Side Review Section */}
      {parseResult && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Panel: Raw Source Text */}
          <div className="lg:col-span-5 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
              <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                <FileText className="w-4 h-4 text-brand-600" />
                Raw Announcement Source
              </h2>
              <span className="text-xs text-slate-400 font-mono">Normalized sentences</span>
            </div>
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs font-mono text-slate-700 leading-relaxed overflow-y-auto max-h-[550px] whitespace-pre-wrap">
              {inputText}
            </div>
          </div>

          {/* Right Panel: Structured Review & Provenance */}
          <div className="lg:col-span-7 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h2 className="text-sm font-bold text-slate-800">Side-by-Side Field Provenance</h2>
                <p className="text-xs text-slate-500">
                  Accept, edit, or reject each extracted field. Unresolved ambiguity items require review.
                </p>
              </div>
              <Badge variant={parseResult.requires_review ? "warning" : "success"}>
                {parseResult.requires_review ? "Requires Officer Review" : "All Fields Validated"}
              </Badge>
            </div>

            {/* Extracted Fields Table */}
            <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden">
              {Object.entries(parseResult.fields).map(([fieldName, item]) => {
                const isEditing = editingField === fieldName;
                const displayVal =
                  Array.isArray(item.extracted_value)
                    ? item.extracted_value.join(", ")
                    : String(item.extracted_value ?? "Not specified");

                return (
                  <div key={fieldName} className="p-3.5 bg-white hover:bg-slate-50/60 transition-colors">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <span className="text-xs font-bold text-slate-900 capitalize block">
                          {fieldName.replace(/_/g, " ")}
                        </span>
                        {isEditing ? (
                          <div className="flex items-center gap-2 mt-1.5">
                            <input
                              type="text"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              className="px-2.5 py-1 text-xs border border-slate-300 rounded-lg focus:outline-none"
                            />
                            <button
                              onClick={() => handleResolveField(fieldName, "edited", editValue)}
                              className="p-1 bg-emerald-600 text-white rounded hover:bg-emerald-700"
                            >
                              <Check className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => setEditingField(null)}
                              className="p-1 bg-slate-200 text-slate-600 rounded hover:bg-slate-300"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ) : (
                          <span className="text-sm font-semibold text-brand-900 mt-0.5 block">
                            {displayVal}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <Badge variant={item.confidence >= 0.8 ? "success" : "warning"} size="sm">
                          {Math.round(item.confidence * 100)}% Confidence
                        </Badge>
                        {!isEditing && (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleResolveField(fieldName, "accepted")}
                              className="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg"
                              title="Accept extracted value"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => {
                                setEditingField(fieldName);
                                setEditValue(displayVal);
                              }}
                              className="p-1.5 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg"
                              title="Edit value manually"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleResolveField(fieldName, "rejected")}
                              className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg"
                              title="Reject value"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>

                    {item.source_sentence && (
                      <p className="text-[11px] text-slate-400 italic mt-1.5 border-l-2 border-brand-200 pl-2">
                        "{item.source_sentence}"
                      </p>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Ambiguities Warning */}
            {parseResult.ambiguities.length > 0 && (
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-amber-800">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  <span>Detected Ambiguities</span>
                </div>
                {parseResult.ambiguities.map((a, i) => (
                  <div key={i} className="text-xs text-amber-900 pl-6 space-y-0.5">
                    <p className="font-semibold">"{a.raw_snippet}"</p>
                    <p className="text-amber-700">{a.reason}</p>
                    <p className="text-amber-800 font-medium">Recommendation: {a.suggested_action}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="pt-2 flex items-center justify-between">
              <span className="text-xs text-slate-500 font-medium">
                Translated into {parseResult.rule_count} Rule AST nodes ready for evaluation.
              </span>
              <button
                onClick={handleSaveDrive}
                className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl shadow-xs transition-colors"
              >
                <Save className="w-4 h-4" />
                <span>Save & Create Drive</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
