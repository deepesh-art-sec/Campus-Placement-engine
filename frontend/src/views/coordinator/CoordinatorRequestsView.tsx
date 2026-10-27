import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  FileQuestion,
  PlusCircle,
  Clock,
  CheckCircle2,
  XCircle,
  MessageSquare,
  Search,
  RefreshCw,
  Send,
  UserCheck,
  Building,
  HelpCircle,
  ArrowRight,
} from "lucide-react";

interface CommentItem {
  author: string;
  role: string;
  text: string;
  timestamp: string;
}

interface CoordinatorRequest {
  id: string;
  request_type: string;
  title: string;
  description: string;
  submitted_by: string;
  submitted_at: string;
  status: "open" | "answered" | "approved" | "rejected";
  target_id: string | null;
  payload: Record<string, any>;
  officer_response: string | null;
  officer_name: string | null;
  resolved_at: string | null;
  comments: CommentItem[];
}

export const CoordinatorRequestsView: React.FC = () => {
  const [requests, setRequests] = useState<CoordinatorRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Modal State for New Request
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newType, setNewType] = useState<string>("shortlist_override");
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newTargetId, setNewTargetId] = useState("");
  const [newReason, setNewReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Thread comment state
  const [selectedReqForComment, setSelectedReqForComment] = useState<CoordinatorRequest | null>(null);
  const [commentText, setCommentText] = useState("");
  const [submittingComment, setSubmittingComment] = useState(false);

  const fetchRequests = async () => {
    try {
      setLoading(true);
      setError(null);
      const queryParams = new URLSearchParams();
      if (statusFilter !== "all") queryParams.append("status_filter", statusFilter);
      if (typeFilter !== "all") queryParams.append("request_type", typeFilter);

      const res = await api.get<CoordinatorRequest[]>(
        `/api/coordinator/requests${queryParams.toString() ? `?${queryParams.toString()}` : ""}`
      );
      setRequests(res || []);
    } catch (err: any) {
      setError(err?.message || "Failed to load coordinator requests.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, [statusFilter, typeFilter]);

  const handleCreateRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newDescription.trim()) {
      setError("Please provide a title and detailed description.");
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const payload: Record<string, any> = {
        reason: newReason || newDescription,
      };

      if (newType === "shortlist_override") {
        payload.action = "add";
        payload.drive_id = newTargetId;
      }

      await api.post("/api/coordinator/requests", {
        request_type: newType,
        title: newTitle,
        description: newDescription,
        target_id: newTargetId || null,
        payload,
      });

      setSuccessMsg(`Request "${newTitle}" successfully submitted to Officer.`);
      setShowCreateModal(false);
      setNewTitle("");
      setNewDescription("");
      setNewTargetId("");
      setNewReason("");
      fetchRequests();
    } catch (err: any) {
      setError(err?.message || "Failed to submit request.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedReqForComment || !commentText.trim()) return;

    try {
      setSubmittingComment(true);
      await api.post(`/api/coordinator/requests/${selectedReqForComment.id}/comments`, {
        text: commentText,
      });

      setCommentText("");
      // Update local comments
      const updatedReqs = await api.get<CoordinatorRequest[]>("/api/coordinator/requests");
      setRequests(updatedReqs || []);
      const updatedSelected = updatedReqs?.find((r) => r.id === selectedReqForComment.id);
      if (updatedSelected) setSelectedReqForComment(updatedSelected);
    } catch (err: any) {
      setError(err?.message || "Failed to submit comment.");
    } finally {
      setSubmittingComment(false);
    }
  };

  const filteredRequests = requests.filter((r) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      r.title.toLowerCase().includes(q) ||
      r.description.toLowerCase().includes(q) ||
      (r.target_id && r.target_id.toLowerCase().includes(q)) ||
      (r.officer_name && r.officer_name.toLowerCase().includes(q))
    );
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "approved":
        return <Badge variant="success">Approved by Officer</Badge>;
      case "rejected":
        return <Badge variant="danger">Rejected by Officer</Badge>;
      case "answered":
        return <Badge variant="info">Answered</Badge>;
      case "open":
      default:
        return <Badge variant="warning">Waiting for Officer</Badge>;
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case "student_data_correction":
        return "Student Data Correction";
      case "shortlist_override":
        return "Shortlist Override";
      case "rule_doubt":
        return "Rule Doubt / Query";
      case "clash_preference":
        return "Clash Preference";
      case "logistics":
        return "Room & Logistics Need";
      default:
        return type.replace(/_/g, " ");
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">Requests to Placement Officer</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
              Module 10
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Create, track, and discuss operational requests (shortlist changes, marks corrections, rule doubts, logistics) requiring Officer sign-off.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchRequests}
            className="p-2 border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-600 transition"
            title="Refresh requests"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-indigo-600" : ""}`} />
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition shadow-sm"
          >
            <PlusCircle className="w-4 h-4" />
            New Request to Officer
          </button>
        </div>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {successMsg && <AlertBanner type="success" message={successMsg} onClose={() => setSuccessMsg(null)} />}

      {/* Summary KPI Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-amber-50/60 border border-amber-200 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-amber-800 uppercase tracking-wide">Waiting for Officer</p>
            <p className="text-2xl font-bold text-amber-900 mt-1">
              {requests.filter((r) => r.status === "open").length}
            </p>
          </div>
          <Clock className="w-8 h-8 text-amber-500 opacity-60" />
        </div>
        <div className="bg-sky-50/60 border border-sky-200 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-sky-800 uppercase tracking-wide">Answered Inquiries</p>
            <p className="text-2xl font-bold text-sky-900 mt-1">
              {requests.filter((r) => r.status === "answered").length}
            </p>
          </div>
          <HelpCircle className="w-8 h-8 text-sky-500 opacity-60" />
        </div>
        <div className="bg-emerald-50/60 border border-emerald-200 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-emerald-800 uppercase tracking-wide">Approved by Officer</p>
            <p className="text-2xl font-bold text-emerald-900 mt-1">
              {requests.filter((r) => r.status === "approved").length}
            </p>
          </div>
          <CheckCircle2 className="w-8 h-8 text-emerald-500 opacity-60" />
        </div>
        <div className="bg-rose-50/60 border border-rose-200 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-rose-800 uppercase tracking-wide">Rejected</p>
            <p className="text-2xl font-bold text-rose-900 mt-1">
              {requests.filter((r) => r.status === "rejected").length}
            </p>
          </div>
          <XCircle className="w-8 h-8 text-rose-500 opacity-60" />
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="relative w-full md:w-96">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Search by title, target ID, description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Statuses</option>
            <option value="open">Waiting for Officer (Open)</option>
            <option value="answered">Answered</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Categories</option>
            <option value="shortlist_override">Shortlist Override</option>
            <option value="student_data_correction">Student Data Correction</option>
            <option value="rule_doubt">Rule Doubt / Query</option>
            <option value="clash_preference">Clash Preference</option>
            <option value="logistics">Room & Logistics</option>
          </select>
        </div>
      </div>

      {/* Requests List */}
      <div className="space-y-4">
        {loading && requests.length === 0 ? (
          <div className="p-12 text-center text-slate-500 bg-white rounded-xl border border-slate-200">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-indigo-600 mb-2" />
            Loading coordinator requests...
          </div>
        ) : filteredRequests.length === 0 ? (
          <div className="p-12 text-center text-slate-500 bg-white rounded-xl border border-slate-200">
            <FileQuestion className="w-10 h-10 mx-auto text-slate-300 mb-2" />
            <p className="font-medium text-slate-700">No requests found</p>
            <p className="text-xs text-slate-400 mt-1">
              Submit a new request to escalate student changes, shortlist additions, or logistics queries.
            </p>
          </div>
        ) : (
          filteredRequests.map((req) => (
            <div
              key={req.id}
              className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:border-slate-300 transition"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 pb-3 border-b border-slate-100">
                <div className="flex flex-wrap items-center gap-2">
                  {getStatusBadge(req.status)}
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                    {getTypeLabel(req.request_type)}
                  </span>
                  {req.target_id && (
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                      Target: {req.target_id}
                    </span>
                  )}
                </div>

                <div className="text-xs text-slate-400">
                  Requested by you on {new Date(req.submitted_at).toLocaleDateString()} at{" "}
                  {new Date(req.submitted_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>

              <div className="mt-3">
                <h3 className="text-base font-semibold text-slate-900">{req.title}</h3>
                <p className="text-sm text-slate-600 mt-1 whitespace-pre-wrap">{req.description}</p>
              </div>

              {/* Payload Details if any */}
              {Object.keys(req.payload || {}).length > 0 && (
                <div className="mt-3 bg-slate-50 rounded-lg p-3 border border-slate-200 text-xs">
                  <span className="font-semibold text-slate-700 uppercase tracking-wide">Request Details / Payload:</span>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-1.5 font-mono text-slate-600">
                    {Object.entries(req.payload).map(([k, v]) => (
                      <div key={k} className="bg-white px-2 py-1 rounded border border-slate-200">
                        <span className="text-slate-400">{k}:</span> {String(v)}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Officer Resolution Banner */}
              {req.officer_response && (
                <div
                  className={`mt-4 rounded-lg p-3 border text-sm ${
                    req.status === "approved"
                      ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                      : req.status === "rejected"
                      ? "bg-rose-50 border-rose-200 text-rose-900"
                      : "bg-sky-50 border-sky-200 text-sky-900"
                  }`}
                >
                  <div className="flex items-center justify-between text-xs font-semibold mb-1">
                    <span className="flex items-center gap-1.5">
                      <UserCheck className="w-3.5 h-3.5" />
                      Officer Response ({req.officer_name || "Placement Officer"}):
                    </span>
                    {req.resolved_at && (
                      <span>{new Date(req.resolved_at).toLocaleString()}</span>
                    )}
                  </div>
                  <p className="font-medium">{req.officer_response}</p>
                </div>
              )}

              {/* Footer Actions & Comments Thread */}
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                <button
                  onClick={() => setSelectedReqForComment(req)}
                  className="flex items-center gap-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-800 transition"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  Discussion Thread ({req.comments ? req.comments.length : 0})
                </button>

                <div className="text-xs text-slate-400 font-mono">
                  ID: {req.id}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Threaded Discussion Modal */}
      {selectedReqForComment && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-xl w-full max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div>
                <h3 className="font-bold text-slate-900 text-base">Threaded Inquiry Discussion</h3>
                <p className="text-xs text-slate-500 mt-0.5">{selectedReqForComment.title}</p>
              </div>
              <button
                onClick={() => setSelectedReqForComment(null)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                &times;
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4 flex-1">
              <div className="bg-slate-50 rounded-lg p-3 border border-slate-200 text-xs text-slate-600">
                <span className="font-semibold text-slate-800">Original Request:</span> {selectedReqForComment.description}
              </div>

              <div className="space-y-3">
                {selectedReqForComment.comments && selectedReqForComment.comments.length > 0 ? (
                  selectedReqForComment.comments.map((c, i) => (
                    <div
                      key={i}
                      className={`p-3 rounded-lg border text-xs ${
                        c.role === "officer"
                          ? "bg-indigo-50 border-indigo-200 ml-4"
                          : "bg-white border-slate-200 mr-4"
                      }`}
                    >
                      <div className="flex items-center justify-between text-slate-500 mb-1">
                        <span className="font-bold text-slate-800">
                          {c.author} ({c.role})
                        </span>
                        <span>{new Date(c.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                      </div>
                      <p className="text-slate-700">{c.text}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 text-center py-4">No comments posted yet.</p>
                )}
              </div>
            </div>

            <form onSubmit={handleAddComment} className="p-4 border-t border-slate-200 bg-slate-50 flex gap-2">
              <input
                type="text"
                placeholder="Type note or response..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                className="flex-1 px-3 py-2 text-xs border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                type="submit"
                disabled={submittingComment || !commentText.trim()}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
              >
                <Send className="w-3.5 h-3.5" />
                Reply
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Create New Request Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div>
                <h3 className="font-bold text-slate-900 text-base">New Request to Officer</h3>
                <p className="text-xs text-slate-500 mt-0.5">Submit operational changes requiring Placement Officer approval.</p>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateRequest} className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Request Category <span className="text-rose-500">*</span>
                </label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="shortlist_override">Shortlist Override (Add/Remove Student)</option>
                  <option value="student_data_correction">Student Data Correction (Marks/Backlogs)</option>
                  <option value="rule_doubt">Doubt about a Rule / Cut-off</option>
                  <option value="logistics">Logistics / Extra Room or Panel Needed</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Title / Subject <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Request to include candidate John Doe in drive shortlist"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Target ID (Student Roll No or Drive ID)
                </label>
                <input
                  type="text"
                  placeholder="e.g. 21CS101 or drive_alpha_1"
                  value={newTargetId}
                  onChange={(e) => setNewTargetId(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Detailed Explanation / Justification <span className="text-rose-500">*</span>
                </label>
                <textarea
                  rows={3}
                  placeholder="Provide supporting note and reason why this requires Officer approval..."
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                  required
                />
              </div>

              <div className="bg-amber-50 p-3 rounded-lg border border-amber-200 text-xs text-amber-900">
                <span className="font-semibold">Audit Notice:</span> This action will be logged in the permanent audit trail with your username and timestamp. The change will take effect only once the Officer explicitly approves it.
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-sm text-slate-700 hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-sm font-semibold flex items-center gap-2 transition"
                >
                  {submitting ? "Submitting..." : "Submit to Officer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
