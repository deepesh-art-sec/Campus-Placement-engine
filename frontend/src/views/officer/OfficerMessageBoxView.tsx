import React, { useState, useEffect, useCallback } from "react";
import { api } from "../../api/client";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  Inbox,
  Send,
  CheckCircle2,
  XCircle,
  Clock,
  MessageSquare,
  Search,
  RefreshCw,
  UserCheck,
  GraduationCap,
  Building2,
  Filter,
  ShieldCheck,
  AlertTriangle,
  ArrowRight,
  Sparkles,
  ChevronRight,
  Layers,
  FileText,
  User,
  Briefcase,
  Bell,
  Check,
  X,
} from "lucide-react";

export interface CommentItem {
  author: string;
  role: string;
  text: string;
  timestamp: string;
}

export interface InboxItem {
  id: string;
  source_type: "coordinator_request" | "pending_result" | "student_correction" | "recruiter_inquiry" | "placement_request";
  request_type: string;
  source_dashboard: string;
  source_role: "coordinator" | "student" | "recruiter" | "officer" | string;
  sender_name: string;
  title: string;
  description: string;
  status: "pending" | "approved" | "rejected" | "answered" | string;
  is_pending: boolean;
  target_id: string | null;
  target_name: string | null;
  payload: Record<string, any>;
  officer_response: string | null;
  officer_name: string | null;
  submitted_at: string | null;
  resolved_at: string | null;
  comments: CommentItem[];
}

export interface InboxSummary {
  total_pending: number;
  coordinator_requests_pending: number;
  pending_results_pending: number;
  student_corrections_pending: number;
  recruiter_inquiries_pending: number;
  placement_requests_pending: number;
  total_items: number;
}

export const OfficerMessageBoxView: React.FC = () => {
  const [items, setItems] = useState<InboxItem[]>([]);
  const [summary, setSummary] = useState<InboxSummary>({
    total_pending: 0,
    coordinator_requests_pending: 0,
    pending_results_pending: 0,
    student_corrections_pending: 0,
    recruiter_inquiries_pending: 0,
    placement_requests_pending: 0,
    total_items: 0,
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Filters
  const [activeTab, setActiveTab] = useState<string>("pending");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Modals
  const [approveItem, setApproveItem] = useState<InboxItem | null>(null);
  const [approveNote, setApproveNote] = useState("");
  const [approving, setApproving] = useState(false);

  const [rejectItem, setRejectItem] = useState<InboxItem | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [rejecting, setRejecting] = useState(false);

  const [discussionItem, setDiscussionItem] = useState<InboxItem | null>(null);
  const [commentText, setCommentText] = useState("");
  const [submittingComment, setSubmittingComment] = useState(false);

  // Compose Modal
  const [showComposeModal, setShowComposeModal] = useState(false);
  const [composeTarget, setComposeTarget] = useState("all");
  const [composeRecipient, setComposeRecipient] = useState("");
  const [composeTitle, setComposeTitle] = useState("");
  const [composeMessage, setComposeMessage] = useState("");
  const [composeCategory, setComposeCategory] = useState("announcement");
  const [dispatching, setDispatching] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [sumRes, itemsRes] = await Promise.all([
        api.get<InboxSummary>("/api/officer/inbox/summary"),
        api.get<InboxItem[]>(
          `/api/officer/inbox/items?filter_tab=${activeTab}&status_filter=${statusFilter}${
            searchQuery ? `&search=${encodeURIComponent(searchQuery)}` : ""
          }`
        ),
      ]);

      if (sumRes) setSummary(sumRes);
      if (itemsRes) setItems(itemsRes);
    } catch (err: any) {
      setError(err?.message || "Failed to load Message Box data.");
    } finally {
      setLoading(false);
    }
  }, [activeTab, statusFilter, searchQuery]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle Approve
  const handleApprove = async () => {
    if (!approveItem) return;
    try {
      setApproving(true);
      await api.post("/api/officer/inbox/approve", {
        item_id: approveItem.id,
        source_type: approveItem.source_type,
        response_note: approveNote.trim() || "Approved by Placement Officer.",
      });

      setSuccessMsg(`Successfully approved: "${approveItem.title}"`);
      setApproveItem(null);
      setApproveNote("");
      fetchData();
    } catch (err: any) {
      setError(err?.message || "Failed to approve request.");
    } finally {
      setApproving(false);
    }
  };

  // Handle Reject
  const handleReject = async () => {
    if (!rejectItem || !rejectReason.trim()) return;
    try {
      setRejecting(true);
      await api.post("/api/officer/inbox/reject", {
        item_id: rejectItem.id,
        source_type: rejectItem.source_type,
        reason: rejectReason.trim(),
      });

      setSuccessMsg(`Request rejected: "${rejectItem.title}"`);
      setRejectItem(null);
      setRejectReason("");
      fetchData();
    } catch (err: any) {
      setError(err?.message || "Failed to reject request.");
    } finally {
      setRejecting(false);
    }
  };

  // Handle Add Thread Comment
  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!discussionItem || !commentText.trim()) return;
    try {
      setSubmittingComment(true);
      const res = await api.post<{ comments: CommentItem[] }>("/api/officer/inbox/comment", {
        item_id: discussionItem.id,
        source_type: discussionItem.source_type,
        text: commentText.trim(),
      });

      if (res && res.comments) {
        setDiscussionItem((prev) => (prev ? { ...prev, comments: res.comments } : null));
        setItems((prev) =>
          prev.map((it) => (it.id === discussionItem.id ? { ...it, comments: res.comments } : it))
        );
      }
      setCommentText("");
      setSuccessMsg("Reply posted to thread.");
    } catch (err: any) {
      setError(err?.message || "Failed to post comment.");
    } finally {
      setSubmittingComment(false);
    }
  };

  // Handle Dispatch Officer Message
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!composeTitle.trim() || !composeMessage.trim()) return;
    try {
      setDispatching(true);
      await api.post("/api/officer/inbox/send-message", {
        recipient_role: composeTarget,
        recipient_username: composeTarget === "individual" ? composeRecipient.trim() : null,
        title: composeTitle.trim(),
        message: composeMessage.trim(),
        category: composeCategory,
      });

      setSuccessMsg(`Official message dispatched to ${composeTarget}.`);
      setShowComposeModal(false);
      setComposeTitle("");
      setComposeMessage("");
      setComposeRecipient("");
      fetchData();
    } catch (err: any) {
      setError(err?.message || "Failed to send message.");
    } finally {
      setDispatching(false);
    }
  };

  const getDashboardIcon = (role: string) => {
    switch (role.toLowerCase()) {
      case "coordinator":
        return <UserCheck className="w-4 h-4 text-indigo-400" />;
      case "student":
        return <GraduationCap className="w-4 h-4 text-emerald-400" />;
      case "recruiter":
      case "recruiter_readonly":
        return <Building2 className="w-4 h-4 text-blue-400" />;
      default:
        return <Inbox className="w-4 h-4 text-amber-400" />;
    }
  };

  const getDashboardBadgeStyle = (role: string) => {
    switch (role.toLowerCase()) {
      case "coordinator":
        return "bg-indigo-950/80 text-indigo-300 border-indigo-800/60";
      case "student":
        return "bg-emerald-950/80 text-emerald-300 border-emerald-800/60";
      case "recruiter":
      case "recruiter_readonly":
        return "bg-blue-950/80 text-blue-300 border-blue-800/60";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  const getStatusBadge = (status: string, isPending: boolean) => {
    if (isPending || status === "pending" || status === "open") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-950/80 text-amber-300 border border-amber-800/60 animate-pulse">
          <Clock className="w-3 h-3 text-amber-400" />
          Awaiting Approval
        </span>
      );
    }
    if (status === "approved") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-800/60">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          Approved & Applied
        </span>
      );
    }
    if (status === "rejected") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-950/80 text-rose-300 border border-rose-800/60">
          <XCircle className="w-3 h-3 text-rose-400" />
          Rejected
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-950/80 text-purple-300 border border-purple-800/60">
        <MessageSquare className="w-3 h-3 text-purple-400" />
        {status.toUpperCase()}
      </span>
    );
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Banner & Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-[#0d1527] via-[#101b33] to-[#0a1426] p-5 sm:p-6 rounded-3xl border border-[#1b2b4d] shadow-xl">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-blue-700 via-teal-600 to-emerald-500 flex items-center justify-center text-white shadow-lg shadow-emerald-500/20 ring-2 ring-emerald-500/20">
              <Inbox className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                  Officer Message Box & Approval Hub
                </h1>
                <span className="px-2 py-0.5 bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 text-[10px] font-bold rounded-full">
                  Cross-Dashboard Hub
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Unified live inbox for coordinator operational requests, student data corrections, on-the-day result entries, and recruiter communications.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 shrink-0 self-start md:self-auto">
          <button
            type="button"
            onClick={() => setShowComposeModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-gradient-to-r from-blue-600 via-teal-600 to-emerald-600 hover:from-blue-500 hover:via-teal-500 hover:to-emerald-500 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-emerald-900/30 border border-emerald-400/30 cursor-pointer"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Compose Message / Broadcast</span>
          </button>

          <button
            type="button"
            onClick={fetchData}
            disabled={loading}
            className="p-2 bg-[#111d38] hover:bg-[#162447] text-slate-300 hover:text-white rounded-xl border border-[#1b2b4d] transition-all cursor-pointer disabled:opacity-50"
            title="Refresh inbox data"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-emerald-400" : ""}`} />
          </button>
        </div>
      </div>

      {/* Alerts */}
      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {successMsg && <AlertBanner type="success" message={successMsg} onClose={() => setSuccessMsg(null)} />}

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div
          onClick={() => setActiveTab("pending")}
          className={`p-3.5 rounded-2xl border transition-all cursor-pointer ${
            activeTab === "pending"
              ? "bg-[#111d38] border-amber-500/50 shadow-md shadow-amber-950/20"
              : "bg-[#0d1527]/90 border-[#1b2b4d] hover:border-slate-700"
          }`}
        >
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="font-bold">Pending Action</span>
            <Clock className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-2xl font-black text-amber-400">
            {summary.total_pending}
          </div>
          <span className="text-[10px] text-slate-500">Requires officer review</span>
        </div>

        <div
          onClick={() => setActiveTab("coordinator")}
          className={`p-3.5 rounded-2xl border transition-all cursor-pointer ${
            activeTab === "coordinator"
              ? "bg-[#111d38] border-indigo-500/50 shadow-md shadow-indigo-950/20"
              : "bg-[#0d1527]/90 border-[#1b2b4d] hover:border-slate-700"
          }`}
        >
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="font-bold">Coordinators</span>
            <UserCheck className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <div className="text-2xl font-black text-indigo-400">
            {summary.coordinator_requests_pending}
          </div>
          <span className="text-[10px] text-slate-500">Overrides & doubts</span>
        </div>

        <div
          onClick={() => setActiveTab("results")}
          className={`p-3.5 rounded-2xl border transition-all cursor-pointer ${
            activeTab === "results"
              ? "bg-[#111d38] border-emerald-500/50 shadow-md shadow-emerald-950/20"
              : "bg-[#0d1527]/90 border-[#1b2b4d] hover:border-slate-700"
          }`}
        >
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="font-bold">Drive Results</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-2xl font-black text-emerald-400">
            {summary.pending_results_pending}
          </div>
          <span className="text-[10px] text-slate-500">Awaiting offer sign-off</span>
        </div>

        <div
          onClick={() => setActiveTab("students")}
          className={`p-3.5 rounded-2xl border transition-all cursor-pointer ${
            activeTab === "students"
              ? "bg-[#111d38] border-teal-500/50 shadow-md shadow-teal-950/20"
              : "bg-[#0d1527]/90 border-[#1b2b4d] hover:border-slate-700"
          }`}
        >
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="font-bold">Student Fixes</span>
            <GraduationCap className="w-3.5 h-3.5 text-teal-400" />
          </div>
          <div className="text-2xl font-black text-teal-400">
            {summary.student_corrections_pending}
          </div>
          <span className="text-[10px] text-slate-500">Marks/CGPA dispute</span>
        </div>

        <div
          onClick={() => setActiveTab("recruiters")}
          className={`p-3.5 rounded-2xl border transition-all cursor-pointer ${
            activeTab === "recruiters"
              ? "bg-[#111d38] border-blue-500/50 shadow-md shadow-blue-950/20"
              : "bg-[#0d1527]/90 border-[#1b2b4d] hover:border-slate-700"
          }`}
        >
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="font-bold">Recruiter</span>
            <Building2 className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <div className="text-2xl font-black text-blue-400">
            {summary.recruiter_inquiries_pending}
          </div>
          <span className="text-[10px] text-slate-500">Inquiries & logistics</span>
        </div>

        <div
          onClick={() => setActiveTab("all")}
          className={`p-3.5 rounded-2xl border transition-all cursor-pointer ${
            activeTab === "all"
              ? "bg-[#111d38] border-slate-500/50 shadow-md"
              : "bg-[#0d1527]/90 border-[#1b2b4d] hover:border-slate-700"
          }`}
        >
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="font-bold">Total Feed</span>
            <Layers className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <div className="text-2xl font-black text-white">
            {summary.total_items}
          </div>
          <span className="text-[10px] text-slate-500">All inbound records</span>
        </div>
      </div>

      {/* Filter Tabs & Search Controls */}
      <div className="bg-[#0d1527] p-3.5 rounded-2xl border border-[#1b2b4d] flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 shadow-md">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
          {[
            { id: "pending", label: "Pending Approvals", count: summary.total_pending },
            { id: "all", label: "All Items", count: summary.total_items },
            { id: "coordinator", label: "Coordinator Requests", count: summary.coordinator_requests_pending },
            { id: "results", label: "Drive Results", count: summary.pending_results_pending },
            { id: "students", label: "Student Corrections", count: summary.student_corrections_pending },
            { id: "recruiters", label: "Recruiter Inquiries", count: summary.recruiter_inquiries_pending },
          ].map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setActiveTab(t.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all cursor-pointer ${
                activeTab === t.id
                  ? "bg-gradient-to-r from-blue-700 to-emerald-600 text-white shadow-xs"
                  : "text-slate-400 hover:text-white hover:bg-[#111d38]"
              }`}
            >
              <span>{t.label}</span>
              {t.count > 0 && (
                <span
                  className={`px-1.5 py-0.2 rounded-full text-[10px] font-black ${
                    activeTab === t.id
                      ? "bg-black/30 text-white"
                      : "bg-amber-950/80 text-amber-300 border border-amber-800/60"
                  }`}
                >
                  {t.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Search & Status Filter */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search sender, student, roll no..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2.5 py-1.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-semibold text-slate-300 focus:outline-none cursor-pointer"
          >
            <option value="all">Status: All</option>
            <option value="pending">Status: Pending</option>
            <option value="approved">Status: Approved</option>
            <option value="rejected">Status: Rejected</option>
          </select>
        </div>
      </div>

      {/* Main Items Feed */}
      <div className="space-y-3.5">
        {loading && items.length === 0 ? (
          <div className="p-12 text-center bg-[#0d1527] rounded-3xl border border-[#1b2b4d] text-slate-400">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3 text-emerald-400" />
            <p className="text-sm font-semibold">Loading Message Box items...</p>
          </div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center bg-[#0d1527] rounded-3xl border border-[#1b2b4d] text-slate-400 space-y-2">
            <Inbox className="w-10 h-10 mx-auto text-slate-600 mb-2" />
            <p className="text-base font-bold text-white">No requests or messages found</p>
            <p className="text-xs text-slate-500">
              {activeTab === "pending"
                ? "All inbound requests across coordinator, student, and recruiter portals have been resolved."
                : "No items match your active filters."}
            </p>
          </div>
        ) : (
          items.map((item) => (
            <div
              key={item.id}
              className={`p-5 rounded-2xl border transition-all duration-150 space-y-3.5 ${
                item.is_pending
                  ? "bg-[#0d1527] border-amber-500/40 shadow-lg shadow-amber-950/10 hover:border-amber-400/60"
                  : "bg-[#0a1222] border-[#1b2b4d] hover:border-slate-700"
              }`}
            >
              {/* Card Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Dashboard Source Badge */}
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-bold border ${getDashboardBadgeStyle(
                      item.source_role
                    )}`}
                  >
                    {getDashboardIcon(item.source_role)}
                    <span>{item.source_dashboard}</span>
                  </span>

                  {/* Requester Info */}
                  <span className="text-xs text-slate-400 font-medium">
                    from <strong className="text-slate-200">{item.sender_name}</strong>
                  </span>

                  {item.submitted_at && (
                    <span className="text-[11px] text-slate-500">
                      • {new Date(item.submitted_at).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  )}
                </div>

                {/* Status Badge */}
                <div className="shrink-0">{getStatusBadge(item.status, item.is_pending)}</div>
              </div>

              {/* Title & Description */}
              <div className="space-y-1">
                <h3 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                  <span>{item.title}</span>
                </h3>
                <p className="text-xs text-slate-300 leading-relaxed">{item.description}</p>
              </div>

              {/* Payload & Context Details Preview */}
              {item.payload && Object.keys(item.payload).length > 0 && (
                <div className="bg-[#060b14] p-3 rounded-xl border border-[#1b2b4d] text-xs space-y-1.5">
                  <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Operational Data & Criteria Payload:</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 pt-1 font-mono text-[11px]">
                    {Object.entries(item.payload).map(([k, v]) => (
                      <div key={k} className="bg-[#0b1325] px-2.5 py-1.5 rounded-lg border border-[#1e3258]">
                        <span className="text-slate-500 block text-[9px] uppercase">{k.replace(/_/g, " ")}</span>
                        <span className="font-bold text-slate-200 truncate block">
                          {typeof v === "object" ? JSON.stringify(v) : String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Officer Resolution Notes (if resolved) */}
              {item.officer_response && (
                <div className="bg-emerald-950/40 p-3 rounded-xl border border-emerald-800/40 text-xs text-emerald-300 space-y-1">
                  <div className="font-bold flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Officer Decision by {item.officer_name || "Placement Officer"}:</span>
                  </div>
                  <p className="text-slate-200">{item.officer_response}</p>
                </div>
              )}

              {/* Card Footer Actions */}
              <div className="pt-2 border-t border-[#1b2b4d] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-xs">
                  {item.target_name && (
                    <span className="px-2 py-0.5 bg-[#111d38] text-slate-300 rounded-lg border border-[#1e3258] font-mono text-[11px]">
                      Target: {item.target_name}
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => setDiscussionItem(item)}
                    className="flex items-center gap-1.5 text-xs font-bold text-indigo-400 hover:text-indigo-300 transition cursor-pointer"
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    <span>Thread Discussion ({item.comments?.length || 0})</span>
                  </button>
                </div>

                {/* Primary Action Buttons */}
                <div className="flex items-center gap-2 shrink-0">
                  {item.is_pending && (
                    <>
                      <button
                        type="button"
                        onClick={() => {
                          setRejectItem(item);
                          setRejectReason("");
                        }}
                        className="flex items-center gap-1 px-3 py-1.5 bg-rose-950/80 hover:bg-rose-900 text-rose-300 hover:text-rose-100 rounded-xl text-xs font-bold border border-rose-800/60 transition cursor-pointer"
                      >
                        <X className="w-3.5 h-3.5" />
                        <span>Reject</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          setApproveItem(item);
                          setApproveNote("");
                        }}
                        className="flex items-center gap-1 px-3.5 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-950/40 border border-emerald-400/30 transition cursor-pointer"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Approve & Enforce</span>
                      </button>
                    </>
                  )}

                  <button
                    type="button"
                    onClick={() => setDiscussionItem(item)}
                    className="flex items-center gap-1 px-3 py-1.5 bg-[#111d38] hover:bg-[#162447] text-slate-300 hover:text-white rounded-xl text-xs font-bold border border-[#1b2b4d] transition cursor-pointer"
                  >
                    <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Reply</span>
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* APPROVE CONFIRMATION MODAL */}
      {approveItem && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0d1527] border border-[#1b2b4d] rounded-3xl max-w-lg w-full p-6 text-slate-100 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#1b2b4d]">
              <div className="flex items-center gap-2 text-emerald-400 font-bold text-base">
                <CheckCircle2 className="w-5 h-5" />
                <span>Confirm Officer Approval</span>
              </div>
              <button
                type="button"
                onClick={() => setApproveItem(null)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                &times;
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <p className="font-semibold text-slate-300">
                You are approving the following inbound request from <strong className="text-white">{approveItem.sender_name}</strong>:
              </p>
              <div className="p-3 bg-[#080e1c] rounded-xl border border-[#1e3258] space-y-1">
                <div className="font-bold text-white text-sm">{approveItem.title}</div>
                <div className="text-slate-400">{approveItem.description}</div>
              </div>

              {approveItem.source_type === "pending_result" && (
                <div className="p-3 bg-emerald-950/40 border border-emerald-800/40 rounded-xl text-emerald-300 text-[11px] leading-relaxed">
                  <strong>Policy Action:</strong> Approving will officially commit this offer in SQLite, update the candidate's offer count, and evaluate 1-student-1-offer institutional policies.
                </div>
              )}

              {approveItem.request_type === "student_data_correction" && (
                <div className="p-3 bg-teal-950/40 border border-teal-800/40 rounded-xl text-teal-300 text-[11px] leading-relaxed">
                  <strong>Database Mutation:</strong> Approving will immediately update the student's verified academic fields (CGPA / Marks / Backlogs) in SQLite and increment the record version.
                </div>
              )}
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider">
                Officer Endorsement / Instruction Notes:
              </label>
              <input
                type="text"
                value={approveNote}
                onChange={(e) => setApproveNote(e.target.value)}
                placeholder="e.g. Verified with marksheet; approved and enforced."
                className="w-full px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#1b2b4d]">
              <button
                type="button"
                onClick={() => setApproveItem(null)}
                className="px-4 py-2 bg-[#111d38] hover:bg-[#162447] text-slate-300 rounded-xl text-xs font-bold transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApprove}
                disabled={approving}
                className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-950/40 border border-emerald-400/30 transition cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
              >
                <Check className="w-3.5 h-3.5" />
                <span>{approving ? "Applying & Enforcing..." : "Confirm & Approve"}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* REJECT MODAL */}
      {rejectItem && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0d1527] border border-[#1b2b4d] rounded-3xl max-w-lg w-full p-6 text-slate-100 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#1b2b4d]">
              <div className="flex items-center gap-2 text-rose-400 font-bold text-base">
                <XCircle className="w-5 h-5" />
                <span>Reject Inbound Request</span>
              </div>
              <button
                type="button"
                onClick={() => setRejectItem(null)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                &times;
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <p className="font-semibold text-slate-300">
                Provide a reason for rejecting <strong className="text-white">"{rejectItem.title}"</strong>. This note will be dispatched to the requester's portal.
              </p>
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider">
                Mandatory Rejection Reason <span className="text-rose-400">*</span>:
              </label>
              <textarea
                rows={3}
                required
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g. Grade sheet verification failed; cutoff criteria not fulfilled."
                className="w-full px-3.5 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-rose-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#1b2b4d]">
              <button
                type="button"
                onClick={() => setRejectItem(null)}
                className="px-4 py-2 bg-[#111d38] hover:bg-[#162447] text-slate-300 rounded-xl text-xs font-bold transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleReject}
                disabled={rejecting || !rejectReason.trim()}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold shadow-md shadow-rose-950/40 border border-rose-400/30 transition cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
              >
                <X className="w-3.5 h-3.5" />
                <span>{rejecting ? "Rejecting..." : "Confirm Rejection"}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* THREAD DISCUSSION MODAL */}
      {discussionItem && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0d1527] border border-[#1b2b4d] rounded-3xl max-w-xl w-full max-h-[85vh] flex flex-col overflow-hidden text-slate-100 shadow-2xl">
            <div className="p-5 border-b border-[#1b2b4d] flex items-center justify-between bg-[#080e1c]">
              <div>
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-indigo-400" />
                  <span>Discussion & Communication Thread</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5 truncate">{discussionItem.title}</p>
              </div>
              <button
                type="button"
                onClick={() => setDiscussionItem(null)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                &times;
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-3.5 flex-1">
              {/* Original Item Box */}
              <div className="bg-[#080e1c] p-3.5 rounded-2xl border border-[#1b2b4d] space-y-1.5 text-xs">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="font-bold text-white">Initial Request:</span>
                  <span>from {discussionItem.sender_name} ({discussionItem.source_dashboard})</span>
                </div>
                <p className="text-slate-300">{discussionItem.description}</p>
              </div>

              {/* Comments History */}
              <div className="space-y-2.5">
                {discussionItem.comments && discussionItem.comments.length > 0 ? (
                  discussionItem.comments.map((c, i) => (
                    <div
                      key={i}
                      className={`p-3 rounded-xl border text-xs space-y-1 ${
                        c.role === "officer"
                          ? "bg-indigo-950/40 border-indigo-800/40 ml-4"
                          : "bg-[#0b1325] border-[#1e3258] mr-4"
                      }`}
                    >
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span className="font-bold text-slate-200">
                          {c.author} ({c.role})
                        </span>
                        <span>{new Date(c.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                      </div>
                      <p className="text-slate-200">{c.text}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-500 text-center py-4">No responses or comments posted yet.</p>
                )}
              </div>
            </div>

            <form onSubmit={handleAddComment} className="p-4 border-t border-[#1b2b4d] bg-[#080e1c] flex gap-2">
              <input
                type="text"
                placeholder="Type officer response or instruction note..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                className="flex-1 px-3.5 py-2 text-xs bg-[#0b1325] border border-[#1e3258] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <button
                type="submit"
                disabled={submittingComment || !commentText.trim()}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 transition cursor-pointer"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Reply</span>
              </button>
            </form>
          </div>
        </div>
      )}

      {/* COMPOSE & BROADCAST MODAL */}
      {showComposeModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0d1527] border border-[#1b2b4d] rounded-3xl max-w-lg w-full p-6 text-slate-100 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#1b2b4d]">
              <div className="flex items-center gap-2 text-emerald-400 font-bold text-base">
                <Send className="w-5 h-5" />
                <span>Compose Official Message / Notice</span>
              </div>
              <button
                type="button"
                onClick={() => setShowComposeModal(false)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleSendMessage} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                  Recipient Dashboard Target:
                </label>
                <select
                  value={composeTarget}
                  onChange={(e) => setComposeTarget(e.target.value)}
                  className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs text-white focus:outline-none cursor-pointer"
                >
                  <option value="all">All Portals (Campus-wide Announcement)</option>
                  <option value="students">Student Portal (All Registered Candidates)</option>
                  <option value="coordinators">Coordinator Dashboard (Student Coordinators)</option>
                  <option value="recruiters">Recruiter Portal (Corporate Hiring Partners)</option>
                  <option value="individual">Single Candidate (Specific Roll Number)</option>
                </select>
              </div>

              {composeTarget === "individual" && (
                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                    Candidate Roll Number <span className="text-rose-400">*</span>:
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. BT210001"
                    value={composeRecipient}
                    onChange={(e) => setComposeRecipient(e.target.value)}
                    className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                  Category:
                </label>
                <select
                  value={composeCategory}
                  onChange={(e) => setComposeCategory(e.target.value)}
                  className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs text-white focus:outline-none cursor-pointer"
                >
                  <option value="announcement">Official Announcement</option>
                  <option value="urgent_alert">Urgent Placement Alert</option>
                  <option value="direct_message">Direct Operational Message</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                  Subject / Title <span className="text-rose-400">*</span>:
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Important instructions regarding Day 1 interview cabins"
                  value={composeTitle}
                  onChange={(e) => setComposeTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                  Message Body <span className="text-rose-400">*</span>:
                </label>
                <textarea
                  rows={4}
                  required
                  placeholder="Type official notice details, venue instructions, or operational announcements..."
                  value={composeMessage}
                  onChange={(e) => setComposeMessage(e.target.value)}
                  className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#1b2b4d]">
                <button
                  type="button"
                  onClick={() => setShowComposeModal(false)}
                  className="px-4 py-2 bg-[#111d38] hover:bg-[#162447] text-slate-300 rounded-xl text-xs font-bold transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={dispatching || !composeTitle.trim() || !composeMessage.trim()}
                  className="px-4 py-2 bg-gradient-to-r from-blue-600 via-teal-600 to-emerald-600 hover:from-blue-500 hover:via-teal-500 hover:to-emerald-500 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-950/40 border border-emerald-400/30 transition cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{dispatching ? "Dispatching..." : "Send / Broadcast"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
