import React, { useState, useEffect } from "react";
import { Drive, DriveStatus } from "../../types";
import { api } from "../../api/client";
import { Badge } from "../../components/common/Badge";
import { EmptyState } from "../../components/common/EmptyState";
import { Modal } from "../../components/common/Modal";
import { AlertBanner } from "../../components/common/AlertBanner";
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
  Copy,
  Ban,
  Users,
  AlertTriangle,
  History,
  FileCheck,
  Play,
  Trash2,
} from "lucide-react";

interface DrivesDashboardProps {
  onNavigateTab: (tabId: string, driveId?: string) => void;
}

interface OverviewMetrics {
  upcoming: { today: number; tomorrow: number; this_week: number };
  total_drives: number;
  total_shortlisted_students: number;
  unresolved_clashes: number;
  needs_review_count: number;
  pending_coordinator_requests: number;
  stale_versions_count: number;
}

export const DrivesDashboard: React.FC<DrivesDashboardProps> = ({ onNavigateTab }) => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");

  // Cancel drive modal state
  const [cancelModalDrive, setCancelModalDrive] = useState<Drive | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelling, setCancelling] = useState(false);

  // Remove drive modal state
  const [deleteModalDrive, setDeleteModalDrive] = useState<Drive | null>(null);
  const [deleteReason, setDeleteReason] = useState("");
  const [deleting, setDeleting] = useState(false);

  const fetchDrivesAndMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      const [drivesRes, metricsRes] = await Promise.all([
        api.get<Drive[]>("/api/drives"),
        api.get<OverviewMetrics>("/api/drives/overview-metrics").catch(() => null),
      ]);
      setDrives(drivesRes || []);
      if (metricsRes) setMetrics(metricsRes);
    } catch (err: any) {
      setError(err.message || "Failed to load recruitment drives.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDrivesAndMetrics();
  }, []);



  const handleConfirmCancelDrive = async () => {
    if (!cancelModalDrive) return;
    if (!cancelReason.trim()) {
      setError("Please provide a mandatory reason for cancelling the drive.");
      return;
    }
    try {
      setCancelling(true);
      setError(null);
      await api.post(`/api/drives/${cancelModalDrive.id}/cancel`, {
        reason: cancelReason,
      });
      setSuccess(`Drive for ${cancelModalDrive.company_name} cancelled.`);
      setCancelModalDrive(null);
      setCancelReason("");
      fetchDrivesAndMetrics();
    } catch (err: any) {
      setError(err.message || "Failed to cancel drive.");
    } finally {
      setCancelling(false);
    }
  };

  const handleConfirmDeleteDrive = async () => {
    if (!deleteModalDrive) return;
    if (!deleteReason.trim()) {
      setError("Please provide a mandatory reason for removing the drive.");
      return;
    }
    try {
      setDeleting(true);
      setError(null);
      await api.delete(`/api/drives/${deleteModalDrive.id}?reason=${encodeURIComponent(deleteReason)}`);
      setSuccess(`Company '${deleteModalDrive.company_name}' and all associated records permanently removed across all dashboards.`);
      setDeleteModalDrive(null);
      setDeleteReason("");
      fetchDrivesAndMetrics();
    } catch (err: any) {
      setError(err.message || "Failed to remove drive.");
    } finally {
      setDeleting(false);
    }
  };

  const filteredDrives = drives.filter((d) => {
    const matchesSearch =
      d.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (d.job_role && d.job_role.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesStatus = statusFilter === "all" || d.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusBadgeVariant = (status: DriveStatus | string) => {
    switch (status) {
      case "published":
        return "success";
      case "ready":
        return "brand";
      case "needs_review":
        return "warning";
      case "completed":
        return "info";
      case "cancelled":
        return "danger";
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
            <span className="text-xs font-bold px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full font-mono">
              {drives.length} Total
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Institutional overview of active, scheduled, and published campus placement drives.
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
            onClick={fetchDrivesAndMetrics}
            className="p-2 text-slate-600 hover:text-slate-900 bg-white border border-slate-200/80 rounded-xl hover:bg-slate-50 shadow-2xs transition-all cursor-pointer"
            title="Refresh drives and metrics"
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

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {success && <AlertBanner type="success" message={success} onClose={() => setSuccess(null)} />}

      {/* Module 1: 6 Overview Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {/* Card 1: Upcoming Drives */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs relative overflow-hidden group hover:border-blue-300 transition-all flex flex-col justify-between min-h-[140px]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-blue-500" />
          <div className="flex items-center justify-between text-blue-600">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Upcoming Drives
            </span>
            <Calendar className="w-4 h-4 text-blue-500" />
          </div>
          <div className="my-1">
            <div className="text-xl font-black text-slate-900 tracking-tight">
              {metrics ? metrics.upcoming.this_week : 0}{" "}
              <span className="text-xs font-semibold text-slate-400">This Wk</span>
            </div>
            <div className="text-[11px] text-slate-500 font-medium mt-0.5 flex items-center gap-2">
              <span>Today: <strong>{metrics ? metrics.upcoming.today : 0}</strong></span>
              <span>•</span>
              <span>Tmrw: <strong>{metrics ? metrics.upcoming.tomorrow : 0}</strong></span>
            </div>
          </div>
          <span className="text-[10px] text-blue-600 font-semibold block">Campus schedule active</span>
        </div>

        {/* Card 2: Shortlisted Students */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs relative overflow-hidden group hover:border-emerald-300 transition-all flex flex-col justify-between min-h-[140px]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-emerald-500" />
          <div className="flex items-center justify-between text-emerald-600">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Shortlisted
            </span>
            <Users className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="my-1">
            <div className="text-2xl font-black text-emerald-700 tracking-tight">
              {metrics ? metrics.total_shortlisted_students : 0}
            </div>
            <div className="text-[11px] text-slate-500 font-medium">Eligible Candidates</div>
          </div>
          <span className="text-[10px] text-emerald-600 font-semibold block">Passed academic cutoffs</span>
        </div>

        {/* Card 3: Unresolved Clashes */}
        <div
          onClick={() => onNavigateTab("schedule")}
          className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs relative overflow-hidden group hover:border-purple-300 transition-all flex flex-col justify-between min-h-[140px] cursor-pointer"
        >
          <div className="absolute top-0 left-0 right-0 h-1 bg-purple-500" />
          <div className="flex items-center justify-between text-purple-600">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Clash Status
            </span>
            <ShieldCheck className="w-4 h-4 text-purple-500" />
          </div>
          <div className="my-1">
            <div className="text-2xl font-black text-slate-900 tracking-tight">
              {metrics ? metrics.unresolved_clashes : 0}
            </div>
            <div className="text-[11px] text-slate-500 font-medium">Unresolved Clashes</div>
          </div>
          {metrics && metrics.unresolved_clashes > 0 ? (
            <span className="text-[10px] text-amber-600 font-bold block flex items-center gap-1">
              <AlertTriangle className="w-3 h-3 text-amber-500" />
              {metrics.unresolved_clashes} Clashes Requiring Action
            </span>
          ) : (
            <span className="text-[10px] text-emerald-600 font-bold block flex items-center gap-1">
              <CheckCircle className="w-3 h-3 text-emerald-500" />
              0 Clashes Verified
            </span>
          )}
        </div>

        {/* Card 4: Needs-Review Items */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs relative overflow-hidden group hover:border-amber-300 transition-all flex flex-col justify-between min-h-[140px]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-amber-500" />
          <div className="flex items-center justify-between text-amber-600">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Needs Review
            </span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <div className="my-1">
            <div className="text-2xl font-black text-amber-700 tracking-tight">
              {metrics ? metrics.needs_review_count : 0}
            </div>
            <div className="text-[11px] text-slate-500 font-medium">Extraction Flags</div>
          </div>
          <span className="text-[10px] text-amber-600 font-semibold block">Requires officer sign-off</span>
        </div>

        {/* Card 5: Pending Coordinator Requests */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs relative overflow-hidden group hover:border-indigo-300 transition-all flex flex-col justify-between min-h-[140px]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-indigo-500" />
          <div className="flex items-center justify-between text-indigo-600">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Pending Requests
            </span>
            <FileCheck className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="my-1">
            <div className="text-2xl font-black text-indigo-700 tracking-tight">
              {metrics ? metrics.pending_coordinator_requests : 0}
            </div>
            <div className="text-[11px] text-slate-500 font-medium">Data Corrections</div>
          </div>
          <span className="text-[10px] text-indigo-600 font-semibold block">From batch coordinators</span>
        </div>

        {/* Card 6: Stale Versions */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs relative overflow-hidden group hover:border-rose-300 transition-all flex flex-col justify-between min-h-[140px]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-rose-500" />
          <div className="flex items-center justify-between text-rose-600">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Stale Versions
            </span>
            <History className="w-4 h-4 text-rose-500" />
          </div>
          <div className="my-1">
            <div className="text-2xl font-black text-rose-700 tracking-tight">
              {metrics ? metrics.stale_versions_count : 0}
            </div>
            <div className="text-[11px] text-slate-500 font-medium">Unpublished Updates</div>
          </div>
          <span className="text-[10px] text-slate-400 font-medium block">Audit trace preserved</span>
        </div>
      </div>

      {/* Quick Actions Bar */}
      <div className="p-4 bg-gradient-to-r from-[#0d1527] to-[#111e3b] rounded-2xl border border-[#1b2b4d] shadow-md flex flex-wrap items-center justify-between gap-3 text-slate-100">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-black uppercase tracking-wider text-white">
            Quick Actions
          </span>
          <span className="text-xs text-slate-400 hidden sm:inline">
            Direct operational shortcuts
          </span>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => onNavigateTab("create_drive")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-500 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New drive</span>
          </button>
          <button
            type="button"
            onClick={() => onNavigateTab("students")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1b2b4d] hover:bg-[#253966] text-slate-200 font-bold text-xs rounded-xl transition-colors cursor-pointer"
          >
            <Users className="w-3.5 h-3.5 text-blue-400" />
            <span>Import students</span>
          </button>
          <button
            type="button"
            onClick={() => onNavigateTab("eligibility")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1b2b4d] hover:bg-[#253966] text-slate-200 font-bold text-xs rounded-xl transition-colors cursor-pointer"
          >
            <Play className="w-3.5 h-3.5 text-emerald-400 fill-current" />
            <span>Run eligibility</span>
          </button>
          <button
            type="button"
            onClick={() => onNavigateTab("schedule")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1b2b4d] hover:bg-[#253966] text-slate-200 font-bold text-xs rounded-xl transition-colors cursor-pointer"
          >
            <Calendar className="w-3.5 h-3.5 text-purple-400" />
            <span>Open schedule</span>
          </button>
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
          {["all", "draft", "needs_review", "ready", "published", "completed", "cancelled"].map((st) => (
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
          Loading active drives roster...
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
                    onClick={() => setCancelModalDrive(d)}
                    className="p-1.5 text-amber-600 hover:text-amber-800 bg-amber-50 hover:bg-amber-100 rounded-lg transition-colors cursor-pointer"
                    title="Cancel recruitment drive"
                  >
                    <Ban className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeleteModalDrive(d)}
                    className="p-1.5 text-rose-600 hover:text-rose-800 bg-rose-50 hover:bg-rose-100 rounded-lg transition-colors cursor-pointer"
                    title="Remove recruitment drive"
                    aria-label={`Remove drive for ${d.company_name}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
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
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-x-auto">
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
                        onClick={() => setCancelModalDrive(d)}
                        className="p-1.5 text-amber-600 hover:text-amber-800 bg-amber-50 hover:bg-amber-100 rounded-lg transition-colors cursor-pointer"
                        title="Cancel recruitment drive"
                      >
                        <Ban className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleteModalDrive(d)}
                        className="p-1.5 text-rose-600 hover:text-rose-800 bg-rose-50 hover:bg-rose-100 rounded-lg transition-colors cursor-pointer"
                        title="Remove recruitment drive"
                        aria-label={`Remove drive for ${d.company_name}`}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
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

      {/* Cancel Drive Mandatory Reason Modal */}
      {cancelModalDrive && (
        <Modal
          isOpen={!!cancelModalDrive}
          onClose={() => setCancelModalDrive(null)}
          title={`Cancel Recruitment Drive: ${cancelModalDrive.company_name}`}
        >
          <div className="space-y-4">
            <p className="text-xs text-slate-600">
              Cancelling this drive will notify shortlisted candidates, release reserved interview cabins, and mark the status as cancelled. This action requires a mandatory justification written to the backend audit log.
            </p>

            <div>
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
                Mandatory Cancellation Reason <span className="text-rose-500">*</span>
              </label>
              <textarea
                rows={3}
                required
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="e.g. Recruiter postponed on-campus visit due to corporate hiring freeze..."
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium focus:bg-white focus:ring-2 focus:ring-rose-500"
              />
            </div>

            <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setCancelModalDrive(null)}
                className="px-3 py-1.5 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
              >
                Nevermind
              </button>
              <button
                type="button"
                disabled={cancelling || !cancelReason.trim()}
                onClick={handleConfirmCancelDrive}
                className="px-4 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer disabled:opacity-50"
              >
                {cancelling ? "Cancelling..." : "Confirm Cancellation"}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Remove Drive Mandatory Reason & Confirmation Modal */}
      {deleteModalDrive && (
        <Modal
          isOpen={!!deleteModalDrive}
          onClose={() => setDeleteModalDrive(null)}
          title={`Remove Recruitment Drive: ${deleteModalDrive.company_name}`}
        >
          <div className="space-y-4">
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <div>
                <strong className="block font-bold">Irreversible Administrative Action:</strong>
                Permanently deleting this drive will completely remove the company, its drives, applications, offers, eligibility evaluations, interview schedules, and requests across all dashboards (Officer, Coordinator, Student, and Recruiter). An immutable audit record will be logged with your justification.
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
                Mandatory Reason for Removal <span className="text-rose-500">*</span>
              </label>
              <textarea
                rows={3}
                required
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
                placeholder="e.g. Duplicate drive created by error / Recruiter cancelled campus season before registration..."
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium focus:bg-white focus:ring-2 focus:ring-rose-500"
              />
            </div>

            <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setDeleteModalDrive(null)}
                className="px-3 py-1.5 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleting || !deleteReason.trim()}
                onClick={handleConfirmDeleteDrive}
                className="px-4 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{deleting ? "Removing..." : "Confirm Permanent Removal"}</span>
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
