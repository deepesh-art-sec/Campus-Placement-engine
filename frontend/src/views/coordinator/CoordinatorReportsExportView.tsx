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
  UserCheck,
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
      const list = drivesRes || [];
      setDrives(list);
      setMappings(mappingsRes || []);
      if (list.length > 0) {
        if (!selectedDriveId || !list.some((d) => d.id === selectedDriveId)) {
          setSelectedDriveId(list[0].id);
        }
      } else {
        setSelectedDriveId("");
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
      setError(null);
      const filename = await api.download(
        "/api/exports/students/csv",
        `student_roster_${new Date().toISOString().slice(0, 10)}.csv`
      );
      setSuccessMsg(`Student Master Roster CSV exported successfully (${filename}). Audit log recorded.`);
    } catch (err: any) {
      setError(err?.message || "Failed to export student CSV.");
    } finally {
      setDownloading(null);
    }
  };

  const handleExportAttendanceCsv = async () => {
    if (!selectedDriveId) return;
    try {
      setDownloading("attendance_csv");
      setError(null);
      const curDrive = drives.find((d) => d.id === selectedDriveId);
      const compName = curDrive ? curDrive.company_name.replace(/\s+/g, "_") : "drive";
      const filename = await api.download(
        `/api/exports/attendance/${selectedDriveId}/csv`,
        `${compName}_attendance_roster.csv`
      );
      setSuccessMsg(`Drive Attendance Roster CSV exported successfully (${filename}). Audit log recorded.`);
    } catch (err: any) {
      setError(err?.message || "Failed to export attendance CSV.");
    } finally {
      setDownloading(null);
    }
  };

  const handleExportSchedule = async (asCsv: boolean) => {
    if (!selectedDriveId) return;
    try {
      setDownloading(asCsv ? "schedule_csv" : "schedule_xlsx");
      setError(null);
      const curDrive = drives.find((d) => d.id === selectedDriveId);
      const compName = curDrive ? curDrive.company_name.replace(/\s+/g, "_") : "drive";
      const defaultName = `${compName}_schedule.${asCsv ? "csv" : "xlsx"}`;
      const filename = await api.download(
        `/api/exports/schedule/${selectedDriveId}?as_csv=${asCsv}`,
        defaultName
      );
      setSuccessMsg(`Interview Schedule exported successfully (${filename}). Audit log recorded.`);
    } catch (err: any) {
      setError(err?.message || "Failed to export schedule.");
    } finally {
      setDownloading(null);
    }
  };

  const handleExportCompanyFormat = async (asCsv: boolean) => {
    if (!selectedDriveId) return;
    try {
      setDownloading(asCsv ? "company_csv" : "company_xlsx");
      setError(null);
      const curDrive = drives.find((d) => d.id === selectedDriveId);
      const compName = curDrive ? curDrive.company_name.replace(/\s+/g, "_") : "company";
      const defaultName = `${compName}_shortlist.${asCsv ? "csv" : "xlsx"}`;
      const filename = await api.download(
        `/api/exports/company/${selectedDriveId}?as_csv=${asCsv}`,
        defaultName
      );
      setSuccessMsg(
        `Shortlist exported in official ${asCsv ? "CSV" : "XLSX"} format (${filename}). Audit log recorded.`
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
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">Reports and Operational Export</h1>
            <Badge variant="brand">Operational Exports</Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Export candidate attendance rosters, interview schedules, company shortlists, and student master registries.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchData}
            className="p-2 border border-slate-200 rounded-xl hover:bg-slate-50 text-slate-600 shadow-2xs transition cursor-pointer"
            title="Refresh export layouts"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-indigo-600" : ""}`} />
          </button>
        </div>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {successMsg && <AlertBanner type="success" message={successMsg} onClose={() => setSuccessMsg(null)} />}

      {/* Drive Selector Bar for Targeted Exports */}
      <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Building className="w-4 h-4 text-brand-600" />
          <label className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            Select Active Drive:
          </label>
        </div>
        <select
          value={selectedDriveId}
          onChange={(e) => setSelectedDriveId(e.target.value)}
          className="px-3.5 py-2 border border-slate-200 rounded-xl text-xs font-bold bg-white text-slate-800 shadow-2xs cursor-pointer focus:ring-2 focus:ring-cyan-500 sm:w-96"
        >
          {drives.map((d) => (
            <option key={d.id} value={d.id}>
              {d.company_name} — {d.job_role || "Drive"} ({d.drive_date})
            </option>
          ))}
        </select>
      </div>

      {/* Grid: 4 Core Operational Export Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Card 1: Live Attendance Roster */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Day-of-Drive Live Ops</span>
              <Badge variant="brand">Attendance</Badge>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-2 flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-emerald-600" />
              Drive Attendance Roster CSV
            </h2>
            <p className="text-sm text-slate-500 mt-2">
              Exports the live candidate attendance log for {selectedDrive?.company_name || "the selected drive"}, including student status (Present, Absent, Late), reporting room, and floor notes.
            </p>

            <div className="mt-4 p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-600 space-y-1">
              <div className="flex justify-between">
                <span>Selected Drive:</span>
                <span className="font-semibold text-slate-800">{selectedDrive?.company_name || "None"}</span>
              </div>
              <div className="flex justify-between">
                <span>Export Format:</span>
                <span className="font-mono text-slate-800">CSV (Standard)</span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100">
            <button
              onClick={handleExportAttendanceCsv}
              disabled={downloading === "attendance_csv" || !selectedDriveId}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition shadow-xs cursor-pointer"
            >
              <Download className="w-4 h-4" />
              {downloading === "attendance_csv" ? "Generating CSV..." : "Export Drive Attendance (CSV)"}
            </button>
          </div>
        </div>

        {/* Card 2: Interview Schedule Export */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Logistics & Cabins</span>
              <Badge variant="brand">Schedule</Badge>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-2 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-indigo-600" />
              Interview Schedule Timetable
            </h2>
            <p className="text-sm text-slate-500 mt-2">
              Exports the full interview schedule matrix with allocated interview cabins, evaluation panels, time slots, and candidate details.
            </p>

            <div className="mt-4 p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-600 space-y-1">
              <div className="flex justify-between">
                <span>Selected Drive:</span>
                <span className="font-semibold text-slate-800">{selectedDrive?.company_name || "None"}</span>
              </div>
              <div className="flex justify-between">
                <span>Formats Available:</span>
                <span className="font-mono text-slate-800">Excel (XLSX) & CSV</span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100 flex gap-3">
            <button
              onClick={() => handleExportSchedule(false)}
              disabled={downloading !== null || !selectedDriveId}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition shadow-xs cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              {downloading === "schedule_xlsx" ? "Exporting..." : "Export Excel (XLSX)"}
            </button>
            <button
              onClick={() => handleExportSchedule(true)}
              disabled={downloading !== null || !selectedDriveId}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 border border-slate-200 hover:bg-slate-50 text-slate-700 disabled:opacity-50 rounded-xl text-xs font-bold transition cursor-pointer"
            >
              <FileText className="w-3.5 h-3.5" />
              {downloading === "schedule_csv" ? "Exporting..." : "Export CSV"}
            </button>
          </div>
        </div>

        {/* Card 3: Company Shortlist */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Recruiter Deliverable</span>
              <Badge variant="brand">Shortlist</Badge>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-2 flex items-center gap-2">
              <Building className="w-5 h-5 text-cyan-600" />
              Company Shortlist Roster
            </h2>
            <p className="text-sm text-slate-500 mt-2">
              Exports shortlisted candidates and assigned interview rounds according to Officer-approved column formatting.
            </p>

            <div className="mt-4 p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-600 space-y-1">
              <div className="flex justify-between">
                <span>Layout Template:</span>
                <span className="font-mono text-slate-800">
                  {activeMapping ? activeMapping.sheet_name : "Standard Roster"}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Columns:</span>
                <span className="text-slate-600">Roll No, Name, Branch, CGPA, Slot, Venue</span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100 flex gap-3">
            <button
              onClick={() => handleExportCompanyFormat(false)}
              disabled={downloading !== null || !selectedDriveId}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition shadow-xs cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              {downloading === "company_xlsx" ? "Exporting..." : "Export Excel (XLSX)"}
            </button>
            <button
              onClick={() => handleExportCompanyFormat(true)}
              disabled={downloading !== null || !selectedDriveId}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 border border-slate-200 hover:bg-slate-50 text-slate-700 disabled:opacity-50 rounded-xl text-xs font-bold transition cursor-pointer"
            >
              <FileText className="w-3.5 h-3.5" />
              {downloading === "company_csv" ? "Exporting..." : "Export CSV"}
            </button>
          </div>
        </div>

        {/* Card 4: Student Master Roster */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Institutional Registry</span>
              <Badge variant="brand">Master Data</Badge>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-2 flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5 text-indigo-600" />
              Student Master Registry CSV
            </h2>
            <p className="text-sm text-slate-500 mt-2">
              Exports the complete institutional candidate database with active CGPA, backlog tallies, and active job offer counts.
            </p>

            <div className="mt-4 p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-600 space-y-1">
              <div className="flex justify-between">
                <span>Roster Format:</span>
                <span className="font-mono text-slate-800">Standard CSV (UTF-8)</span>
              </div>
              <div className="flex justify-between">
                <span>Includes:</span>
                <span className="text-slate-600">Roll No, Name, Program, CGPA, Backlogs, Offers</span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100">
            <button
              onClick={handleExportStudentsCsv}
              disabled={downloading === "students_csv"}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition shadow-xs cursor-pointer"
            >
              <Download className="w-4 h-4" />
              {downloading === "students_csv" ? "Generating CSV..." : "Download Student Master Roster (CSV)"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
