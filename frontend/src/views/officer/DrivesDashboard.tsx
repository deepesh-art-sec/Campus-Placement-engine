import React, { useState, useEffect } from "react";
import { Drive, DriveStatus } from "../../types";
import { api } from "../../api/client";
import { Badge } from "../../components/common/Badge";
import { EmptyState } from "../../components/common/EmptyState";
import {
  Briefcase,
  Plus,
  Search,
  Calendar,
  IndianRupee,
  Sliders,
  CheckCircle,
  Clock,
  Sparkles,
  RefreshCw,
  LayoutGrid,
  Table as TableIcon,
  ArrowRight,
  ShieldCheck,
  Building,
} from "lucide-react";

interface DrivesDashboardProps {
  onNavigateTab: (tabId: string, driveId?: string) => void;
}

export const DrivesDashboard: React.FC<DrivesDashboardProps> = ({ onNavigateTab }) => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");

  const fetchDrives = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get<Drive[]>("/api/drives");
      setDrives(res || []);
    } catch (err: any) {
      setError(err.message || "Failed to load recruitment drives.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDrives();
  }, []);

  const filteredDrives = drives.filter((d) => {
    const matchesSearch =
      d.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (d.job_role && d.job_role.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesStatus = statusFilter === "all" || d.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusBadgeVariant = (status: DriveStatus) => {
    switch (status) {
      case "published":
        return "success";
      case "ready":
        return "brand";
      case "needs_review":
        return "warning";
      case "completed":
        return "info";
      default:
        return "neutral";
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Summary */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Recruitment Drives</h1>
            <span className="text-xs font-bold px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full">
              {drives.length} Total
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Institutional overview of active, scheduled, and published campus drives.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex items-center bg-white p-1 rounded-xl border border-slate-200 shadow-2xs">
            <button
              type="button"
              onClick={() => setViewMode("grid")}
              className={`p-1.5 rounded-lg transition-all ${
                viewMode === "grid"
                  ? "bg-slate-900 text-white shadow-2xs"
                  : "text-slate-500 hover:text-slate-800"
              }`}
              title="Grid View"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode("table")}
              className={`p-1.5 rounded-lg transition-all ${
                viewMode === "table"
                  ? "bg-slate-900 text-white shadow-2xs"
                  : "text-slate-500 hover:text-slate-800"
              }`}
              title="Table View"
            >
              <TableIcon className="w-4 h-4" />
            </button>
          </div>

          <button
            type="button"
            onClick={fetchDrives}
            className="p-2 text-slate-600 hover:text-slate-900 bg-white border border-slate-200/80 rounded-xl hover:bg-slate-50 shadow-2xs transition-all cursor-pointer"
            title="Refresh drives"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => onNavigateTab("create_drive")}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-sm shadow-brand-500/25 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Drive / Extract</span>
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4.5 rounded-2xl border border-slate-200/80 shadow-xs relative overflow-hidden group hover:border-brand-300 transition-all">
          <div className="absolute top-0 left-0 right-0 h-1 bg-brand-500" />
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Total Drives</span>
            <div className="p-2 bg-brand-50 text-brand-700 rounded-xl">
              <Briefcase className="w-4 h-4" />
            </div>
          </div>
          <span className="text-3xl font-black text-slate-900 block mt-2">{drives.length}</span>
          <span className="text-[11px] text-slate-400 mt-1 block">Campus season roster</span>
        </div>

        <div className="bg-white p-4.5 rounded-2xl border border-slate-200/80 shadow-xs relative overflow-hidden group hover:border-emerald-300 transition-all">
          <div className="absolute top-0 left-0 right-0 h-1 bg-emerald-500" />
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Published</span>
            <div className="p-2 bg-emerald-50 text-emerald-700 rounded-xl">
              <CheckCircle className="w-4 h-4" />
            </div>
          </div>
          <span className="text-3xl font-black text-emerald-700 block mt-2">
            {drives.filter((d) => d.status === "published").length}
          </span>
          <span className="text-[11px] text-emerald-600 font-semibold mt-1 block">Active on Student LAN</span>
        </div>

        <div className="bg-white p-4.5 rounded-2xl border border-slate-200/80 shadow-xs relative overflow-hidden group hover:border-amber-300 transition-all">
          <div className="absolute top-0 left-0 right-0 h-1 bg-amber-500" />
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">In Draft / Review</span>
            <div className="p-2 bg-amber-50 text-amber-700 rounded-xl">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <span className="text-3xl font-black text-amber-700 block mt-2">
            {drives.filter((d) => d.status === "draft" || d.status === "needs_review").length}
          </span>
          <span className="text-[11px] text-slate-400 mt-1 block">Pending publication</span>
        </div>

        <div className="bg-white p-4.5 rounded-2xl border border-slate-200/80 shadow-xs relative overflow-hidden group hover:border-indigo-300 transition-all">
          <div className="absolute top-0 left-0 right-0 h-1 bg-indigo-500" />
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Avg Package</span>
            <div className="p-2 bg-indigo-50 text-indigo-700 rounded-xl">
              <IndianRupee className="w-4 h-4" />
            </div>
          </div>
          <span className="text-3xl font-black text-indigo-700 block mt-2">
            {drives.length
              ? (drives.reduce((acc, d) => acc + (d.ctc_lpa || 0), 0) / drives.length).toFixed(1)
              : "0.0"}{" "}
            <span className="text-xs font-bold text-slate-400">LPA</span>
          </span>
          <span className="text-[11px] text-slate-400 mt-1 block">Fixed + variable CTC</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Search by company or role..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 transition-all"
          />
        </div>
        <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto no-scrollbar py-0.5">
          {["all", "draft", "needs_review", "ready", "published", "completed"].map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold capitalize transition-all cursor-pointer whitespace-nowrap ${
                statusFilter === st
                  ? "bg-slate-900 text-white shadow-2xs"
                  : "bg-slate-100/80 text-slate-600 hover:bg-slate-200/80"
              }`}
            >
              {st.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Loading & Error States */}
      {loading ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500 text-sm animate-pulse">
          Loading placement drives roster...
        </div>
      ) : error ? (
        <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-rose-700 text-sm">
          {error}
        </div>
      ) : filteredDrives.length === 0 ? (
        <EmptyState
          title="No recruitment drives found"
          description="Create your first placement drive by extracting an announcement circular or pasting a JD."
          action={
            <button
              onClick={() => onNavigateTab("create_drive")}
              className="px-4 py-2 bg-brand-600 text-white text-xs font-semibold rounded-xl hover:bg-brand-700 transition-colors"
            >
              Extract First Announcement
            </button>
          }
        />
      ) : viewMode === "grid" ? (
        /* Card Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredDrives.map((d) => (
            <div
              key={d.id}
              className="bg-white rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md hover:border-brand-200 transition-all p-5 flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-slate-700 font-bold border border-slate-200">
                      <Building className="w-5 h-5 text-slate-500" />
                    </div>
                    <div>
                      <h3 className="font-black text-slate-900 text-base tracking-tight leading-tight">
                        {d.company_name}
                      </h3>
                      <span className="text-xs text-slate-500 font-medium">
                        {d.job_role || "Engineering Graduate Trainee"}
                      </span>
                    </div>
                  </div>
                  <Badge variant={getStatusBadgeVariant(d.status)}>
                    {d.status.replace("_", " ")}
                  </Badge>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Package</span>
                    <div className="font-mono font-black text-slate-900 text-sm">
                      {d.ctc_lpa ? `${d.ctc_lpa} LPA` : "Undisclosed"}
                      {d.is_dream && (
                        <span className="ml-1.5 px-1.5 py-0.2 bg-purple-100 text-purple-700 rounded text-[9px] font-bold uppercase">
                          Dream
                        </span>
                      )}
                    </div>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Drive Date</span>
                    <div className="flex items-center gap-1 text-slate-700 font-semibold text-xs mt-0.5">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>{new Date(d.drive_date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-1.5">
                <span className="text-[10px] font-mono font-bold text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                  v{d.version}
                </span>

                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => onNavigateTab("eligibility", d.id)}
                    className="px-2.5 py-1 text-xs font-bold text-brand-700 bg-brand-50 hover:bg-brand-100 rounded-lg transition-colors cursor-pointer"
                    title="Evaluate candidate eligibility"
                  >
                    Evaluate
                  </button>
                  <button
                    type="button"
                    onClick={() => onNavigateTab("schedule", d.id)}
                    className="px-2.5 py-1 text-xs font-bold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-lg transition-colors cursor-pointer"
                    title="Open schedule grid"
                  >
                    Schedule
                  </button>
                  <button
                    type="button"
                    onClick={() => onNavigateTab("what_if", d.id)}
                    className="px-2.5 py-1 text-xs font-bold text-amber-700 bg-amber-50 hover:bg-amber-100 rounded-lg transition-colors cursor-pointer"
                    title="What-if simulation before publish"
                  >
                    What-If
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Table View */
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-600 uppercase tracking-wider">
                <th className="px-6 py-3.5">Company & Role</th>
                <th className="px-6 py-3.5">Date & Mode</th>
                <th className="px-6 py-3.5">Package (CTC)</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5">Version</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {filteredDrives.map((d) => (
                <tr key={d.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="px-6 py-4">
                    <span className="font-bold text-slate-900 block">{d.company_name}</span>
                    <span className="text-xs text-slate-500 block">{d.job_role || "Software Engineering"}</span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1.5 text-slate-700">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>{new Date(d.drive_date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</span>
                    </div>
                    <span className="text-xs text-slate-400 capitalize block">{d.mode.replace("_", " ")}</span>
                  </td>
                  <td className="px-6 py-4 font-mono font-bold text-slate-800">
                    {d.ctc_lpa ? `${d.ctc_lpa} LPA` : "Not disclosed"}
                    {d.is_dream && (
                      <span className="ml-1.5 px-1.5 py-0.2 bg-purple-100 text-purple-700 rounded text-[9px] font-bold uppercase">
                        Dream
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <Badge variant={getStatusBadgeVariant(d.status)}>
                      {d.status.replace("_", " ")}
                    </Badge>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-xs font-mono font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                      v{d.version}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        type="button"
                        onClick={() => onNavigateTab("eligibility", d.id)}
                        className="px-2.5 py-1 text-xs font-semibold text-brand-700 bg-brand-50 hover:bg-brand-100 rounded-lg transition-colors cursor-pointer"
                        title="Evaluate candidate eligibility"
                      >
                        Evaluate
                      </button>
                      <button
                        type="button"
                        onClick={() => onNavigateTab("schedule", d.id)}
                        className="px-2.5 py-1 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-lg transition-colors cursor-pointer"
                        title="Open schedule grid"
                      >
                        Schedule
                      </button>
                      <button
                        type="button"
                        onClick={() => onNavigateTab("what_if", d.id)}
                        className="px-2.5 py-1 text-xs font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 rounded-lg transition-colors cursor-pointer"
                        title="What-if simulation before publish"
                      >
                        What-If
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
