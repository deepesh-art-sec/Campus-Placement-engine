import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Drive } from "../../types";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  Calendar,
  Users,
  ShieldCheck,
  AlertTriangle,
  FileCheck,
  Clock,
  Sparkles,
  ArrowRight,
  Building,
  RefreshCw,
  PlusCircle,
  UserCheck,
  Eye,
  Info,
  Layers,
} from "lucide-react";

interface OverviewMetrics {
  today_drives_count: number;
  upcoming_drives_count: number;
  total_shortlisted_students: number;
  unresolved_clashes: number;
  needs_review_count: number;
  requests: {
    waiting_for_officer: number;
    answered: number;
    approved: number;
    rejected: number;
    total: number;
  };
}

interface CoordinatorOverviewViewProps {
  onNavigateTab: (tabId: string, driveId?: string) => void;
}

export const CoordinatorOverviewView: React.FC<CoordinatorOverviewViewProps> = ({
  onNavigateTab,
}) => {
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [drives, setDrives] = useState<Drive[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = async () => {
    try {
      setLoading(true);
      setError(null);
      const [mRes, dRes] = await Promise.all([
        api.get<OverviewMetrics>("/api/coordinator/overview-metrics"),
        api.get<Drive[]>("/api/drives"),
      ]);
      setMetrics(mRes);
      setDrives(dRes || []);
    } catch (err: any) {
      setError(err.message || "Failed to load coordinator overview.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  const getSourceBadge = (drive: Drive) => {
    if (drive.company_name.toLowerCase().includes("imats")) {
      return (
        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-950 text-blue-300 border border-blue-800">
          IMATS Synced
        </span>
      );
    }
    if (drive.version > 1) {
      return (
        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-950 text-purple-300 border border-purple-800">
          NLP Extracted
        </span>
      );
    }
    return (
      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-300">
        Manual Entry
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Coordinator Operations Overview</h1>
            <Badge variant="brand">Student Placement Coordinator (Read & Prepare)</Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Daily campus drive roster, candidate attendance dispatch, student inquiries, and officer approval requests.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={fetchOverview}
            className="p-2 text-slate-600 hover:text-slate-900 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 shadow-2xs transition-all cursor-pointer"
            title="Refresh overview metrics"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => onNavigateTab("requests")}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer"
          >
            <PlusCircle className="w-4 h-4" />
            <span>New Request to Officer</span>
          </button>
        </div>
      </div>

      {/* Coordinator Read & Prepare Principle Banner */}
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-2xl flex items-start gap-3">
        <Info className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
        <div className="text-xs text-blue-900 leading-relaxed">
          <strong>Coordinator Operating Rule:</strong> You can inspect student academics, prepare candidate rosters, record attendance, and log drive results. Any policy amendments, cut-off alterations, or drive publications are strictly governed by the Placement Officer and require raising a formal request.
        </div>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}

      {/* 6 Key Coordinator Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {/* Card 1: Today's Drives */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs relative overflow-hidden flex flex-col justify-between min-h-[140px]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-blue-500" />
          <div className="flex items-center justify-between text-blue-600">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Today's Drives</span>
            <Calendar className="w-4 h-4" />
          </div>
          <div className="my-1">
            <div className="text-2xl font-black text-slate-900">{metrics?.today_drives_count ?? 0}</div>
            <div className="text-[11px] text-slate-500 font-medium">On-Campus Today</div>
          </div>
          <button
            type="button"
            onClick={() => onNavigateTab("on_the_day")}
            className="text-[10px] text-blue-600 font-bold hover:underline flex items-center gap-1 cursor-pointer"
          >
            <span>Mark Attendance</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        {/* Card 2: Upcoming Drives */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs relative overflow-hidden flex flex-col justify-between min-h-[140px]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-indigo-500" />
          <div className="flex items-center justify-between text-indigo-600">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Upcoming Drives</span>
            <Clock className="w-4 h-4" />
          </div>
          <div className="my-1">
            <div className="text-2xl font-black text-slate-900">{metrics?.upcoming_drives_count ?? 0}</div>
            <div className="text-[11px] text-slate-500 font-medium">Active Roster</div>
          </div>
          <button
            type="button"
            onClick={() => onNavigateTab("drives")}
            className="text-[10px] text-indigo-600 font-bold hover:underline flex items-center gap-1 cursor-pointer"
          >
            <span>View Drives</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        {/* Card 3: Shortlisted Candidates */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs relative overflow-hidden flex flex-col justify-between min-h-[140px]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-emerald-500" />
          <div className="flex items-center justify-between text-emerald-600">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Shortlisted</span>
            <Users className="w-4 h-4" />
          </div>
          <div className="my-1">
            <div className="text-2xl font-black text-emerald-700">{metrics?.total_shortlisted_students ?? 0}</div>
            <div className="text-[11px] text-slate-500 font-medium">Eligible Students</div>
          </div>
          <button
            type="button"
            onClick={() => onNavigateTab("eligibility")}
            className="text-[10px] text-emerald-600 font-bold hover:underline flex items-center gap-1 cursor-pointer"
          >
            <span>Eligibility Table</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        {/* Card 4: Unresolved Clashes */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs relative overflow-hidden flex flex-col justify-between min-h-[140px]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-purple-500" />
          <div className="flex items-center justify-between text-purple-600">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Clashes</span>
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div className="my-1">
            <div className="text-2xl font-black text-slate-900">{metrics?.unresolved_clashes ?? 0}</div>
            <div className="text-[11px] text-slate-500 font-medium">Unresolved Clashes</div>
          </div>
          <button
            type="button"
            onClick={() => onNavigateTab("clashes")}
            className="text-[10px] text-purple-600 font-bold hover:underline flex items-center gap-1 cursor-pointer"
          >
            <span>Record Preferences</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        {/* Card 5: Needs-Review Items */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs relative overflow-hidden flex flex-col justify-between min-h-[140px]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-amber-500" />
          <div className="flex items-center justify-between text-amber-600">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Needs Review</span>
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div className="my-1">
            <div className="text-2xl font-black text-amber-700">{metrics?.needs_review_count ?? 0}</div>
            <div className="text-[11px] text-slate-500 font-medium">Extraction Items</div>
          </div>
          <span className="text-[10px] text-amber-600 font-semibold block">Officer Review Req.</span>
        </div>

        {/* Card 6: Open Requests to Officer */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs relative overflow-hidden flex flex-col justify-between min-h-[140px]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-teal-500" />
          <div className="flex items-center justify-between text-teal-600">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Open Requests</span>
            <FileCheck className="w-4 h-4" />
          </div>
          <div className="my-1">
            <div className="text-xl font-black text-teal-700">
              {metrics?.requests.waiting_for_officer ?? 0}{" "}
              <span className="text-xs font-semibold text-slate-400">Waiting</span>
            </div>
            <div className="text-[11px] text-slate-500 font-medium mt-0.5 flex items-center gap-1.5">
              <span>Ans: <strong>{metrics?.requests.answered ?? 0}</strong></span>
              <span>•</span>
              <span>Rej: <strong>{metrics?.requests.rejected ?? 0}</strong></span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => onNavigateTab("requests")}
            className="text-[10px] text-teal-600 font-bold hover:underline flex items-center gap-1 cursor-pointer"
          >
            <span>Track Requests</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Quick Action Buttons Bar */}
      <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-brand-600" />
          <span className="text-xs font-black uppercase tracking-wider text-slate-900">Coordinator Quick Tools:</span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => onNavigateTab("requests")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Submit Correction Request</span>
          </button>
          <button
            type="button"
            onClick={() => onNavigateTab("on_the_day")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-50 hover:bg-brand-100 text-brand-800 font-bold text-xs rounded-xl border border-brand-200 transition-colors cursor-pointer"
          >
            <UserCheck className="w-3.5 h-3.5" />
            <span>Drive Day Attendance</span>
          </button>
          <button
            type="button"
            onClick={() => onNavigateTab("eligibility")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 font-bold text-xs rounded-xl border border-emerald-200 transition-colors cursor-pointer"
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Eligibility Explainer</span>
          </button>
          <button
            type="button"
            onClick={() => onNavigateTab("results")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-50 hover:bg-purple-100 text-purple-800 font-bold text-xs rounded-xl border border-purple-200 transition-colors cursor-pointer"
          >
            <FileCheck className="w-3.5 h-3.5" />
            <span>Log Pending Results</span>
          </button>
        </div>
      </div>

      {/* Active Campus Drives Table (Read-Only) */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="font-black text-slate-900 text-sm tracking-tight">Active Recruitment Drives Roster</h3>
            <p className="text-xs text-slate-500 mt-0.5">Read-only operational status. Source badges verified from corporate announcement feeds.</p>
          </div>
          <span className="text-xs font-mono font-bold text-slate-400 bg-slate-100 px-2.5 py-1 rounded-lg">
            {drives.length} Drives Registered
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
                <th className="px-6 py-3.5">Company & Role</th>
                <th className="px-6 py-3.5">Source Badge</th>
                <th className="px-6 py-3.5">Drive Date & Mode</th>
                <th className="px-6 py-3.5">Package</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5 text-right">Coordinator Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {drives.map((d) => (
                <tr key={d.id} className="hover:bg-slate-50/60 transition-colors">
                  <td className="px-6 py-4">
                    <span className="font-bold text-slate-900 block">{d.company_name}</span>
                    <span className="text-[11px] text-slate-500">{d.job_role || "Graduate Trainee"}</span>
                  </td>
                  <td className="px-6 py-4">{getSourceBadge(d)}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1.5 text-slate-700">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>{new Date(d.drive_date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</span>
                    </div>
                    <span className="text-[10px] text-slate-400 capitalize block mt-0.5">{d.mode.replace("_", " ")}</span>
                  </td>
                  <td className="px-6 py-4 font-mono font-bold text-slate-800">
                    {d.ctc_lpa ? `${d.ctc_lpa} LPA` : "Undisclosed"}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full capitalize ${
                        d.status === "published"
                          ? "bg-emerald-100 text-emerald-800"
                          : d.status === "ready"
                          ? "bg-blue-100 text-blue-800"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {d.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        type="button"
                        onClick={() => onNavigateTab("eligibility", d.id)}
                        className="px-2.5 py-1 text-xs font-bold text-brand-700 bg-brand-50 hover:bg-brand-100 rounded-lg transition-colors cursor-pointer"
                        title="Inspect shortlisted candidates"
                      >
                        Eligibility
                      </button>
                      <button
                        type="button"
                        onClick={() => onNavigateTab("schedule", d.id)}
                        className="px-2.5 py-1 text-xs font-bold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-lg transition-colors cursor-pointer"
                        title="View schedule grid"
                      >
                        Schedule
                      </button>
                      <button
                        type="button"
                        onClick={() => onNavigateTab("drives", d.id)}
                        className="px-2.5 py-1 text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
                        title="Prepare draft notes & flag doubts"
                      >
                        Inspect
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
