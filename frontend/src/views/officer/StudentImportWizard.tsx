import React, { useState } from "react";
import { api } from "../../api/client";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  Upload,
  FileSpreadsheet,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  Database,
  RefreshCw,
} from "lucide-react";

interface StudentImportWizardProps {
  onSuccess?: () => void;
}

export const StudentImportWizard: React.FC<StudentImportWizardProps> = ({ onSuccess }) => {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [report, setReport] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Default detected mapping
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({
    "Roll No": "roll_no",
    "Candidate Name": "name",
    "Email Address": "email",
    "Engineering Branch": "branch",
    "Cumulative GPA": "cgpa",
    "Class 10 %": "tenth_percentage",
    "Class 12 %": "twelfth_percentage",
    "Date of Birth": "date_of_birth",
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleDryRun = async () => {
    if (!file) return;
    try {
      setUploading(true);
      setError(null);
      const formData = new FormData();
      formData.append("file", file);
      // dry_run=true
      const res = await api.post<any>("/api/students/import?dry_run=true", formData);
      setReport(res);
      setStep(3);
    } catch (err: any) {
      setError(err.message || "Failed to process dry-run import.");
    } finally {
      setUploading(false);
    }
  };

  const handleFinalImport = async () => {
    if (!file) return;
    try {
      setUploading(true);
      setError(null);
      const formData = new FormData();
      formData.append("file", file);
      // dry_run=false
      const res = await api.post<any>("/api/students/import?dry_run=false", formData);
      setReport(res);
      setStep(4);
      setSuccessMsg(`Successfully committed ${res.imported_count} student records to local database.`);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setError(err.message || "Failed to commit student records.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Student Roster Import Wizard</h1>
        <p className="text-sm text-slate-500 mt-1">
          Bulk import student academic records with column auto-mapping, dry-run simulation, and row error reporting.
        </p>
      </div>

      {/* Stepper Header */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between">
        {[
          { num: 1, label: "Upload File" },
          { num: 2, label: "Column Mapping" },
          { num: 3, label: "Dry-Run Simulation" },
          { num: 4, label: "Database Commit" },
        ].map((s) => (
          <div key={s.num} className="flex items-center gap-2">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                step === s.num
                  ? "bg-brand-600 text-white shadow-xs"
                  : step > s.num
                  ? "bg-emerald-100 text-emerald-800"
                  : "bg-slate-100 text-slate-400"
              }`}
            >
              {step > s.num ? <CheckCircle className="w-4 h-4" /> : s.num}
            </div>
            <span
              className={`text-xs font-semibold hidden sm:inline ${
                step === s.num ? "text-slate-900" : "text-slate-400"
              }`}
            >
              {s.label}
            </span>
          </div>
        ))}
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {successMsg && <AlertBanner type="success" message={successMsg} onClose={() => setSuccessMsg(null)} />}

      {/* Step 1: Upload */}
      {step === 1 && (
        <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-xs text-center space-y-6">
          <div className="max-w-md mx-auto border-2 border-dashed border-slate-300 rounded-2xl p-8 hover:border-brand-500 transition-colors bg-slate-50">
            <FileSpreadsheet className="w-12 h-12 text-slate-400 mx-auto mb-3" />
            <h3 className="text-sm font-bold text-slate-800">Drop student spreadsheet here</h3>
            <p className="text-xs text-slate-500 mt-1 mb-4">Accepts .xlsx, .xls, or .csv roster files</p>
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={handleFileChange}
              className="text-xs text-slate-500 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100 cursor-pointer"
            />
          </div>

          {file && (
            <div className="flex items-center justify-between p-3 bg-emerald-50 border border-emerald-200 rounded-xl max-w-md mx-auto">
              <span className="text-xs font-bold text-emerald-900 truncate">{file.name}</span>
              <button
                onClick={() => setStep(2)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold rounded-lg shadow-xs"
              >
                Next <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* Step 2: Mapping */}
      {step === 2 && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
          <div>
            <h3 className="text-base font-bold text-slate-900">Verify Header Column Alignment</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              The engine automatically aligns your spreadsheet columns to canonical academic fields.
            </p>
          </div>

          <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden">
            {Object.entries(columnMapping).map(([fileHeader, domainField]) => (
              <div key={fileHeader} className="p-3.5 flex items-center justify-between bg-white hover:bg-slate-50">
                <span className="text-xs font-semibold text-slate-700 font-mono">{fileHeader}</span>
                <span className="text-xs text-slate-400">maps to</span>
                <span className="text-xs font-bold text-brand-700 bg-brand-50 px-2.5 py-1 rounded-md border border-brand-200">
                  {domainField}
                </span>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between">
            <button
              onClick={() => setStep(1)}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
            >
              <ArrowLeft className="w-4 h-4" /> Back
            </button>
            <button
              onClick={handleDryRun}
              disabled={uploading}
              className="flex items-center gap-1.5 px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-xl shadow-xs disabled:opacity-50"
            >
              {uploading ? "Running Dry-Run Simulation..." : "Run Dry-Run Simulation"} <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Dry-Run Simulation Report */}
      {step === 3 && report && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
          <div>
            <h3 className="text-base font-bold text-slate-900">Dry-Run Simulation Report</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Simulated {report.total_rows} records. No changes have been written to the persistent database.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-center">
              <span className="text-xs font-bold text-slate-500 uppercase">Total Rows</span>
              <span className="text-2xl font-black text-slate-900 block mt-1">{report.total_rows}</span>
            </div>
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-center">
              <span className="text-xs font-bold text-emerald-700 uppercase">Valid Candidates</span>
              <span className="text-2xl font-black text-emerald-800 block mt-1">{report.imported_count}</span>
            </div>
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-center">
              <span className="text-xs font-bold text-rose-700 uppercase">Error Rows</span>
              <span className="text-2xl font-black text-rose-800 block mt-1">{report.error_rows}</span>
            </div>
          </div>

          {report.errors && report.errors.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-rose-800 uppercase tracking-wider flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-rose-600" />
                Row Errors ({report.errors.length})
              </h4>
              <div className="max-h-60 overflow-y-auto divide-y divide-slate-100 border border-rose-200 rounded-xl text-xs">
                {report.errors.map((err: any, idx: number) => (
                  <div key={idx} className="p-3 bg-rose-50/50 flex items-start justify-between gap-3">
                    <div>
                      <span className="font-bold text-slate-800">
                        Row {err.row_index} {err.roll_no ? `(${err.roll_no})` : ""}:
                      </span>
                      <span className="text-slate-600 ml-1.5">{err.message}</span>
                    </div>
                    <Badge variant="danger" size="sm">{err.field}</Badge>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => setStep(2)}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
            >
              <ArrowLeft className="w-4 h-4" /> Re-map Columns
            </button>
            <button
              onClick={handleFinalImport}
              disabled={uploading || report.imported_count === 0}
              className="flex items-center gap-1.5 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-xs disabled:opacity-50"
            >
              <Database className="w-4 h-4" />
              <span>{uploading ? "Committing..." : `Commit ${report.imported_count} Records`}</span>
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Completed */}
      {step === 4 && (
        <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-xs text-center space-y-4">
          <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center text-emerald-600 mx-auto">
            <CheckCircle className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-bold text-slate-900">Student Roster Successfully Imported</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto">
            All validated student records are now indexed in SQLite and available for immediate eligibility evaluation.
          </p>
          <div className="pt-4 flex items-center justify-center gap-3">
            <button
              onClick={() => {
                setFile(null);
                setStep(1);
              }}
              className="px-4 py-2 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl"
            >
              Import Another File
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
