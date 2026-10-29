import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Table, Column } from "../../components/common/Table";
import { Card, CardHeader, CardBody } from "../../components/common/Card";
import { Button } from "../../components/common/Button";
import { StatusPill } from "../../components/domain/StatusPill";
import { DiffView } from "../../components/common/DiffView";
import { Modal } from "../../components/common/Modal";
import {
  Inbox,
  CheckCircle2,
  XCircle,
  Clock,
  User,
  ShieldCheck,
  Send,
  Eye,
  AlertCircle,
  FileCheck,
} from "lucide-react";

interface RequestItem {
  id: string;
  request_type: string;
  target_entity: string;
  target_id: string;
  requester_role: string;
  requester_name?: string;
  status: string;
  reason: string;
  requested_changes_json?: string;
  review_notes?: string;
  created_at: string;
}

export const RequestsManagerView: React.FC = () => {
  const [requests, setRequests] = useState<RequestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [selectedRequest, setSelectedRequest] = useState<RequestItem | null>(null);
  const [reviewNotes, setReviewNotes] = useState("");
  const [autoApply, setAutoApply] = useState(true);
  const [submittingAction, setSubmittingAction] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 3500);
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const fetchRequests = async () => {
    try {
      setLoading(true);
      const res = await api.get<any>("/api/requests");
      const list = Array.isArray(res) ? res : res.requests || [];
      setRequests(list);
    } catch (err: any) {
      console.error("Failed to load requests", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (action: "APPROVE" | "REJECT") => {
    if (!selectedRequest) return;
    try {
      setSubmittingAction(true);
      await api.post(`/api/requests/${selectedRequest.id}/action`, {
        action,
        review_notes: reviewNotes,
        apply_changes: autoApply,
      });

      showToast(`Request #${selectedRequest.id.slice(0, 8)} ${action === "APPROVE" ? "Approved & Applied" : "Rejected"}`);
      setSelectedRequest(null);
      setReviewNotes("");
      fetchRequests();
    } catch (err: any) {
      alert(`Action failed: ${err.message}`);
    } finally {
      setSubmittingAction(false);
    }
  };

  const filteredRequests = requests.filter((r) => {
    if (filterStatus === "ALL") return true;
    return r.status === filterStatus;
  });

  const parseChanges = (jsonStr?: string) => {
    if (!jsonStr) return {};
    try {
      return JSON.parse(jsonStr);
    } catch {
      return { raw: jsonStr };
    }
  };

  const pendingCount = requests.filter((r) => r.status === "PENDING_REVIEW").length;

  const columns: Column<RequestItem>[] = [
    {
      key: "id",
      header: "Request ID",
      sortable: true,
      render: (item) => <span className="font-mono text-cyan-400 font-bold">#{item.id.slice(0, 8)}</span>,
    },
    {
      key: "request_type",
      header: "Type",
      sortable: true,
      render: (item) => (
        <span className="font-mono text-[11px] bg-[#111d38] text-slate-200 px-2 py-0.5 rounded border border-[#1e3258]">
          {item.request_type.replace(/_/g, " ")}
        </span>
      ),
    },
    {
      key: "requester_role",
      header: "Requester",
      sortable: true,
      render: (item) => (
        <div className="flex items-center gap-1.5 font-mono text-xs">
          <User className="w-3.5 h-3.5 text-slate-400" />
          <span className="capitalize text-slate-200">{item.requester_role}</span>
        </div>
      ),
    },
    {
      key: "target_id",
      header: "Target Entity",
      sortable: true,
      render: (item) => (
        <span className="font-mono text-xs text-white">
          {item.target_entity}: <strong className="text-cyan-300">{item.target_id}</strong>
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      sortable: true,
      render: (item) => <StatusPill status={item.status} size="sm" />,
    },
    {
      key: "created_at",
      header: "Submitted",
      sortable: true,
      render: (item) => (
        <span className="text-slate-400 font-mono text-[11px]">
          {new Date(item.created_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: "actions",
      header: "Action",
      render: (item) => (
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            setSelectedRequest(item);
            setReviewNotes("");
          }}
        >
          <Eye className="w-3 h-3 mr-1" />
          Review Diff
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6 pb-16">
      {/* Toast Notification */}
      {notification && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#0d1527] border border-emerald-500/50 text-emerald-300 px-4 py-3 rounded-2xl shadow-2xl flex items-center gap-2 text-xs font-bold animate-in fade-in slide-in-from-bottom-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{notification}</span>
        </div>
      )}

      {/* Header */}
      <div className="bg-[#0d1527] p-6 rounded-3xl border border-[#1e3258] shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-700/60 flex items-center gap-1.5">
              <Inbox className="w-3.5 h-3.5 text-cyan-400" />
              Governance & Oversight
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Deterministic Change Control
            </span>
          </div>
          <h2 className="text-2xl font-black text-white">
            Requests & Corrections Inbox
          </h2>
          <p className="text-xs text-slate-300 mt-1">
            Review and approve candidate record corrections submitted by Coordinators and Students with live before/after diffs.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 bg-[#080e1c] p-1.5 rounded-2xl border border-[#1e3258]">
          {[
            { id: "ALL", label: "All Requests", count: requests.length },
            { id: "PENDING_REVIEW", label: "Pending", count: pendingCount },
            { id: "APPROVED", label: "Approved" },
            { id: "REJECTED", label: "Rejected" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilterStatus(tab.id)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                filterStatus === tab.id
                  ? "bg-gradient-to-r from-blue-700 to-emerald-600 text-white shadow-md shadow-emerald-950"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span className="ml-1.5 font-mono text-[10px] opacity-80">
                  ({tab.count})
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Requests Table */}
      <Card>
        <CardHeader
          title={`Incoming Change Requests (${filteredRequests.length})`}
          subtitle="All modifications are tracked in the immutable placement engine audit log"
        />
        <CardBody>
          <Table
            data={filteredRequests}
            columns={columns}
            searchPlaceholder="Search by roll number, requester, or type..."
            pageSize={10}
            exportFilename="change_requests"
          />
        </CardBody>
      </Card>

      {/* REVIEW & DIFF MODAL */}
      <Modal
        isOpen={!!selectedRequest}
        onClose={() => setSelectedRequest(null)}
        title={`Review Change Request #${selectedRequest?.id.slice(0, 8)}`}
      >
        {selectedRequest && (
          <div className="space-y-5 text-xs">
            {/* Meta Strip */}
            <div className="p-3.5 bg-[#080e1c] rounded-xl border border-[#1e3258] grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div>
                <span className="text-[10px] uppercase font-mono text-slate-500 block">Requester</span>
                <span className="font-bold text-white capitalize">{selectedRequest.requester_role}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase font-mono text-slate-500 block">Target Entity</span>
                <span className="font-mono font-bold text-cyan-400">{selectedRequest.target_id}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase font-mono text-slate-500 block">Type</span>
                <span className="font-mono text-slate-300">{selectedRequest.request_type}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase font-mono text-slate-500 block">Current Status</span>
                <StatusPill status={selectedRequest.status} size="sm" />
              </div>
            </div>

            {/* Justification note */}
            <div className="p-3 bg-[#0c1830] rounded-xl border border-blue-900/40 text-slate-200">
              <span className="font-bold text-cyan-300 block mb-1">Reason / Justification:</span>
              <p className="text-slate-300 leading-relaxed">{selectedRequest.reason}</p>
            </div>

            {/* Diff View Comparison */}
            <div>
              <h4 className="text-xs font-mono font-bold uppercase text-slate-400 mb-2">
                Field-By-Field Diff Comparison:
              </h4>
              <DiffView
                before={{
                  field: parseChanges(selectedRequest.requested_changes_json).field || "current",
                  value: parseChanges(selectedRequest.requested_changes_json).current_value || "Prior recorded state",
                }}
                after={{
                  field: parseChanges(selectedRequest.requested_changes_json).field || "proposed",
                  value: parseChanges(selectedRequest.requested_changes_json).proposed_value || "Proposed change",
                }}
                title="Proposed Candidate Record State"
              />
            </div>

            {/* Officer Review Form (if pending) */}
            {selectedRequest.status === "PENDING_REVIEW" ? (
              <div className="space-y-3 pt-3 border-t border-[#1e3258]">
                <div>
                  <label className="block text-slate-300 font-bold uppercase mb-1">
                    Officer Decision Notes
                  </label>
                  <textarea
                    rows={2}
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    placeholder="Enter approval conditions or rejection grounds..."
                    className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white text-xs"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="autoApply"
                    checked={autoApply}
                    onChange={(e) => setAutoApply(e.target.checked)}
                    className="rounded text-emerald-500 focus:ring-emerald-500"
                  />
                  <label htmlFor="autoApply" className="text-slate-300 select-none cursor-pointer">
                    Automatically update student database record upon approval
                  </label>
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <Button
                    variant="outline"
                    type="button"
                    onClick={() => setSelectedRequest(null)}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="danger"
                    type="button"
                    loading={submittingAction}
                    onClick={() => handleAction("REJECT")}
                  >
                    <XCircle className="w-3.5 h-3.5 mr-1.5" />
                    Reject Request
                  </Button>
                  <Button
                    variant="primary"
                    type="button"
                    loading={submittingAction}
                    onClick={() => handleAction("APPROVE")}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
                    Approve & Apply
                  </Button>
                </div>
              </div>
            ) : (
              <div className="p-3 bg-[#080e1c] rounded-xl border border-[#1e3258] text-slate-400 text-xs">
                This request was already reviewed ({selectedRequest.status}).
                {selectedRequest.review_notes && (
                  <div className="mt-1 text-slate-200">Notes: {selectedRequest.review_notes}</div>
                )}
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};
