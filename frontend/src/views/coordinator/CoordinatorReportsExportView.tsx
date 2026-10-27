import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Drive } from "../../types";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  FileSpreadsheet,
  Download,
  Lock,
  Building,
  Calendar,
  Users,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Layers,
  Search,
  RefreshCw,
  FileText,
  AlertCircle,
} from "lucide-react";

interface CompanyMapping {
  id: string;
  company_id: string;
  company_name: string;
  sheet_name: string;
  date_format: string;
  column_order: string[];
}

export const CoordinatorReportsExportView: React.FC = () => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [mappings, setMappings] = useState<CompanyMapping[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [drivesRes, mappingsRes] = await Promise.all([
        api.get<Drive[]>("/api/drives"),
        api.get<CompanyMapping[]>("/api/exports/company-mappings").catch(() => []),
      ]);
      setDrives(drivesRes || []);
      setMappings(mappingsRes || []);
      if (drivesRes && drivesRes.length > 0 && !selectedDriveId) {
        setSelectedDriveId(drivesRes[0].id);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load drive export data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleExportStudentsCsv = async () => {
    try {
      setDownloading("students_csv");
      const token = localStorage.getItem("token");
      const response = await fetch("/api/students/export/csv", {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) throw new Error("Failed to download student master CSV.");

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `student_roster_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      setSuccessMsg(`Student Master Roster CSV exported successfully. Audit log recorded.`);
    } catch (err: any) {
      setError(err?.message || "Failed to export student CSV.");
    } finally {
      setDownloading(null);
    }
  };

  const handleExportCompanyFormat = async (asCsv: boolean) => {
    if (!selectedDriveId) return;
    try {
      setDownloading(asCsv ? "company_csv" : "company_xlsx");
      const token = localStorage.getItem("token");
      const response = await fetch(`/api/exports/company-format/${selectedDriveId}?as_csv=${asCsv}`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (!response.ok) throw new Error("Failed to generate company-format export.");

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const curDrive = drives.find((d) => d.id === selectedDriveId);
      const compName = curDrive ? curDrive.company_name.replace(/\s+/g, "_") : "company";
      a.download = `${compName}_shortlist.${asCsv ? "csv" : "xlsx"}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      setSuccessMsg(
        `Shortlist exported in official ${asCsv ? "CSV" : "XLSX"} format. Audit log recorded.`
      );
    } catch (err: any) {
      setError(err?.message || "Failed to generate company format export.");
    } finally {
      setDownloading(null);
    }
  };

  const selectedDrive = drives.find((d) => d.id === selectedDriveId);
  const activeMapping = mappings.find(
    (m) =>
      selectedDrive &&
      (m.company_id === selectedDrive.company_id ||
        m.company_name.toLowerCase() === selectedDrive.company_name.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">Reports and Operational Export</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
              Module 11
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Generate student master rosters and company-tailored candidate shortlists using Officer-approved column mappings.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchData}
            className="p-2 border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-600 transition"
            title="Refresh export layouts"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-indigo-600" : ""}`} />
          </button>
        </div>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {successMsg && <AlertBanner type="success" message={successMsg} onClose={() => setSuccessMsg(null)} />}

      {/* FERPA / Compliance Notice */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-600 space-y-1">
          <span className="font-semibold text-slate-800">Compliance & Coordinator Scope:</span>
          <p>
            Coordinator permissions allow viewing and generating standard exports. Column header mappings, custom formulas, and company templates are strictly configured by the Placement Officer and cannot be altered by coordinators.
          </p>
        </div>
      </div>

      {/* Grid: Master Roster Export & Company Shortlist */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Card 1: Student Master Roster */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Institutional Registry</span>
              <Badge variant="info">Master Data</Badge>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-2 flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5 text-indigo-600" />
              Student Master Roster CSV
            </h2>
            <p className="text-sm text-slate-500 mt-2">
              Exports the complete institutional database of registered candidates with current CGPA, backlog counts, gap years, and active offer tallies.
            </p>

            <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-100 text-xs text-slate-600 space-y-1">
              <div className="flex justify-between">
                <span>Roster Format:</span>
                <span className="font-mono font-medium text-slate-800">Standard CSV (UTF-8)</span>
              </div>
              <div className="flex justify-between">
                <span>Total Candidates:</span>
                <span className="font-semibold text-slate-800">1,800 Registered</span>
              </div>
              <div className="flex justify-between">
                <span>Includes:</span>
                <span className="text-slate-700">Roll No, Name, Branch, CGPA, Backlogs, Offers</span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100">
            <button
              onClick={handleExportStudentsCsv}
              disabled={downloading === "students_csv"}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition shadow-sm"
            >
              <Download className="w-4 h-4" />
              {downloading === "students_csv" ? "Generating CSV..." : "Download Full Student Roster (CSV)"}
            </button>
            <p className="text-[11px] text-slate-400 text-center mt-2">
              Action is logged with your credentials in the institutional audit log.
            </p>
          </div>
        </div>

        {/* Card 2: Company-Tailored Shortlist & Schedule */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Recruiter Deliverable</span>
              <Badge variant="success">Officer-Approved Format</Badge>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-2 flex items-center gap-2">
              <Building className="w-5 h-5 text-indigo-600" />
              Company Shortlist & Schedule Export
            </h2>
            <p className="text-sm text-slate-500 mt-2">
              Exports shortlisted students and assigned interview slots directly conforming to the company's designated column schema.
            </p>

            {/* Drive Selection Dropdown */}
            <div className="mt-4">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Select Recruitment Drive:
              </label>
              <select
                value={selectedDriveId}
                onChange={(e) => setSelectedDriveId(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-indigo-500"
              >
                {drives.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.company_name} — {d.job_role || "Recruitment Drive"} ({d.drive_date})
                  </option>
                ))}
              </select>
            </div>

            {/* Read-Only Mapping Indicator */}
            <div className="mt-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="font-semibold text-slate-700 flex items-center gap-1">
                  <Lock className="w-3.5 h-3.5 text-amber-600" />
                  Template Mapping (Officer Managed):
                </span>
                <span className="text-slate-500 font-mono text-[11px]">
                  {activeMapping ? activeMapping.sheet_name : "Standard Roster"}
                </span>
              </div>
              <p className="text-[11px] text-slate-500">
                {activeMapping
                  ? `Using saved company mapping for "${activeMapping.company_name}". Columns: ${activeMapping.column_order.slice(0, 4).join(", ")}...`
                  : "Using standard institutional format: Roll Number, Candidate Name, Email, Branch, CGPA, Round, Slot Time, Venue."}
              </p>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100 flex gap-3">
            <button
              onClick={() => handleExportCompanyFormat(false)}
              disabled={downloading !== null || !selectedDriveId}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition shadow-sm"
            >
              <Download className="w-3.5 h-3.5" />
              {downloading === "company_xlsx" ? "Exporting..." : "Export Excel (XLSX)"}
            </button>
            <button
              onClick={() => handleExportCompanyFormat(true)}
              disabled={downloading !== null || !selectedDriveId}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 border border-slate-300 hover:bg-slate-50 text-slate-700 disabled:opacity-50 rounded-lg text-xs font-semibold transition"
            >
              <FileText className="w-3.5 h-3.5" />
              {downloading === "company_csv" ? "Exporting..." : "Export CSV"}
            </button>
          </div>
        </div>
      </div>

      {/* Saved Company Mappings Registry (Read-Only Table) */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-bold text-slate-900 text-base">Officer-Configured Company Mappings</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Approved header alignments ensuring zero data truncation during recruiter handoff. (Read-only for Coordinator).
            </p>
          </div>
          <div className="flex items-center gap-1 text-xs text-amber-700 bg-amber-50 px-2.5 py-1 rounded-md border border-amber-200">
            <Lock className="w-3.5 h-3.5" />
            Editing Locked (Officer privilege)
          </div>
        </div>

        {mappings.length === 0 ? (
          <div className="text-center py-8 text-slate-400 text-xs bg-slate-50 rounded-lg border border-slate-200">
            No custom company layouts uploaded yet. Standard institutional export format is active for all drives.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-600 uppercase border-y border-slate-200 font-semibold">
                <tr>
                  <th className="py-2.5 px-4">Company Name</th>
                  <th className="py-2.5 px-4">Sheet Name</th>
                  <th className="py-2.5 px-4">Date Format</th>
                  <th className="py-2.5 px-4">Mapped Column Sequence</th>
                  <th className="py-2.5 px-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {mappings.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-50">
                    <td className="py-3 px-4 font-semibold text-slate-800">{m.company_name}</td>
                    <td className="py-3 px-4 font-mono text-slate-600">{m.sheet_name}</td>
                    <td className="py-3 px-4 font-mono text-slate-600">{m.date_format}</td>
                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-1">
                        {m.column_order.map((col, idx) => (
                          <span
                            key={idx}
                            className="bg-slate-100 px-1.5 py-0.5 rounded text-[10px] text-slate-600 border border-slate-200"
                          >
                            {col}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Badge variant="success">Active</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
