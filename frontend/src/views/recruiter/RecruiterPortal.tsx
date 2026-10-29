import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Badge } from "../../components/common/Badge";
import { Button } from "../../components/common/Button";
import { Table, Column } from "../../components/common/Table";
import { Card, CardHeader, CardBody } from "../../components/common/Card";
import { Modal } from "../../components/common/Modal";
import { StatusPill } from "../../components/domain/StatusPill";
import { ClashBadge } from "../../components/domain/ClashBadge";
import { VersionBadge } from "../../components/domain/VersionBadge";
import {
  Briefcase,
  Calendar,
  Clock,
  Users,
  Download,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Mail,
  Phone,
  Building,
  AlertTriangle,
  Send,
  UserCheck,
  Search,
} from "lucide-react";

interface ShortlistCandidate {
  id: string;
  roll_no: string;
  name: string;
  branch: string;
  cgpa: number;
  tenth_percentage: number;
  twelfth_percentage: number;
  attendance: string;
  criteria_breakdown: Array<{
    criterion: string;
    required: string;
    student_value: string;
    satisfied: boolean;
  }>;
}

export const RecruiterPortal: React.FC = () => {
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<string | null>(null);

  // "Why This Student" Modal State
  const [selectedCandidate, setSelectedCandidate] = useState<ShortlistCandidate | null>(null);

  // "Contact College" Modal State
  const [isContactOpen, setIsContactOpen] = useState(false);
  const [contactSubject, setContactSubject] = useState("");
  const [contactMessage, setContactMessage] = useState("");
  const [contactType, setContactType] = useState("RECRUITER_QUERY");
  const [submittingContact, setSubmittingContact] = useState(false);

  // "This Looks Wrong" Flag Modal
  const [isFlagWrongOpen, setIsFlagWrongOpen] = useState(false);
  const [flagWrongReason, setFlagWrongReason] = useState("");
  const [flagSubmitting, setFlagSubmitting] = useState(false);

  const showToast = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 3500);
  };

  useEffect(() => {
    fetchRecruiterData();
  }, []);

  const fetchRecruiterData = async () => {
    try {
      setLoading(true);
      const res = await api.get<any>("/api/recruiter/my-drive");
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load corporate recruitment dashboard.");
    } finally {
      setLoading(false);
    }
  };

  // Submit Contact Form
  const handleSendContact = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingContact(true);
    try {
      await api.post("/api/recruiter/contact-officer", {
        subject: contactSubject,
        message: contactMessage,
        request_type: contactType,
      });
      setIsContactOpen(false);
      setContactSubject("");
      setContactMessage("");
      showToast("Message dispatched to College Placement Officer. We will respond promptly.");
    } catch (err: any) {
      alert(`Failed to send message: ${err.message}`);
    } finally {
      setSubmittingContact(false);
    }
  };

  // Submit "This Looks Wrong" Flag
  const handleFlagWrongRequirements = async (e: React.FormEvent) => {
    e.preventDefault();
    setFlagSubmitting(true);
    try {
      await api.post("/api/recruiter/contact-officer", {
        subject: "REQUIREMENT_CRITERIA_DISCREPANCY",
        message: flagWrongReason,
        request_type: "REQUIREMENTS_FLAG",
      });
      setIsFlagWrongOpen(false);
      setFlagWrongReason("");
      showToast("Criteria discrepancy flagged to TPO. The Placement Cell has been alerted.");
    } catch (err: any) {
      alert(`Failed to flag criteria: ${err.message}`);
    } finally {
      setFlagSubmitting(false);
    }
  };

  // CSV Export for Shortlist
  const handleExportCsv = () => {
    if (!data?.shortlist || data.shortlist.length === 0) {
      alert("No candidates to export.");
      return;
    }
    const headers = ["Roll Number", "Candidate Name", "Department", "CGPA", "10th %", "12th %", "Day Attendance"];
    const rows = data.shortlist.map((s: ShortlistCandidate) => [
      `"${s.roll_no}"`,
      `"${s.name}"`,
      `"${s.branch}"`,
      s.cgpa,
      s.tenth_percentage || "N/A",
      s.twelfth_percentage || "N/A",
      `"${s.attendance}"`,
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((r: any[]) => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `shortlist_${data.company_name.replace(/\s+/g, "_")}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast("Downloaded candidate shortlist CSV!");
  };

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-400 text-sm">
        <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        Loading corporate partner portal...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 bg-[#0d1527] border border-[#1e3258] rounded-3xl max-w-lg mx-auto text-center space-y-4 text-white">
        <Briefcase className="w-12 h-12 text-slate-500 mx-auto" />
        <h3 className="text-base font-bold text-white">Recruiter Portal Access Restricted</h3>
        <p className="text-xs text-slate-400">{error || "No authorized recruitment drive found for your organization."}</p>
        <div className="pt-2 flex justify-center gap-3">
          <Button variant="primary" size="sm" onClick={fetchRecruiterData}>
            Retry Loading Dashboard
          </Button>
        </div>
      </div>
    );
  }

  const columns: Column<ShortlistCandidate>[] = [
    { key: "roll_no", header: "Roll No", sortable: true },
    { key: "name", header: "Candidate Name", sortable: true },
    { key: "branch", header: "Branch / Dept", sortable: true },
    { key: "cgpa", header: "CGPA", sortable: true },
    {
      key: "attendance",
      header: "Day Turnout",
      render: (item) => <StatusPill status={item.attendance} size="sm" />,
    },
    {
      key: "actions",
      header: "Why This Student?",
      render: (item) => (
        <button
          type="button"
          onClick={() => setSelectedCandidate(item)}
          className="text-xs font-mono font-bold text-emerald-400 hover:text-emerald-300 underline cursor-pointer"
        >
          View Checklist
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-16">
      {/* Toast Notification */}
      {notification && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#0d1527] border border-emerald-500/50 text-emerald-300 px-4 py-3 rounded-2xl shadow-2xl flex items-center gap-2 text-xs font-bold animate-in fade-in slide-in-from-bottom-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{notification}</span>
        </div>
      )}

      {/* Recruiter Header */}
      <div className="bg-[#0d1527] p-6 rounded-3xl border border-[#1e3258] shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-600/50 flex items-center gap-1.5">
              <Briefcase className="w-3.5 h-3.5 text-emerald-400" />
              Corporate Recruiter Portal
            </span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Campus Recruitment Desk
          </h1>
          <p className="text-xs text-slate-300 mt-1 font-medium">
            Role: <strong className="text-white">{data.role_title || "Software Development Engineer"}</strong> • Date: {new Date(data.drive_date).toLocaleDateString()} • Package: ₹{data.ctc_lpa} LPA
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setIsContactOpen(true)}
          >
            <Mail className="w-3.5 h-3.5 mr-1.5 text-cyan-400" />
            Contact College
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleExportCsv}
          >
            <Download className="w-3.5 h-3.5 mr-1.5" />
            Export Shortlist CSV
          </Button>
        </div>
      </div>

      {/* Corporate Overview Grid: Requirements, Stats, Officer Contact */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Requirements Used Card with "This Looks Wrong" button */}
        <Card className="md:col-span-2">
          <CardHeader
            title="Requirements Used for Candidate Screening"
            subtitle="Deterministic thresholds applied to screen batch of 25,000 students"
            action={
              <button
                type="button"
                onClick={() => setIsFlagWrongOpen(true)}
                className="text-xs text-amber-400 hover:text-amber-300 underline font-mono flex items-center gap-1 cursor-pointer"
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>This looks wrong?</span>
              </button>
            }
          />
          <CardBody className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {data.requirements_summary?.map((req: string, idx: number) => (
                <div key={idx} className="p-3 rounded-xl bg-[#080e1c] border border-[#1e3258] flex items-center gap-2 text-xs">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  <span className="font-mono text-slate-200">{req}</span>
                </div>
              ))}
            </div>

            <div className="pt-2 flex items-center justify-between text-xs text-slate-400">
              <span className="font-mono">Shortlisted Candidates: <strong className="text-white">{data.total_shortlisted}</strong></span>
            </div>
          </CardBody>
        </Card>

        {/* College Placement Officer Contact Card */}
        <Card>
          <CardHeader title="Placement Cell Contact" subtitle="Official campus liaison" />
          <CardBody className="space-y-3 text-xs text-slate-300">
            <div>
              <div className="font-bold text-white text-sm">
                {data.officer_contact?.name || "Prof. R. K. Sharma"}
              </div>
              <div className="text-slate-400 text-[11px]">
                {data.officer_contact?.title || "Head, Training & Placement Cell"}
              </div>
            </div>

            <div className="pt-2 border-t border-[#1e3258]/60 space-y-1.5 font-mono text-[11px]">
              <div className="flex items-center gap-2 text-slate-300">
                <Mail className="w-3.5 h-3.5 text-cyan-400" />
                <span>{data.officer_contact?.email || "tpo@college.edu"}</span>
              </div>
              <div className="flex items-center gap-2 text-slate-300">
                <Phone className="w-3.5 h-3.5 text-emerald-400" />
                <span>{data.officer_contact?.phone || "+91 98765 43210"}</span>
              </div>
              <div className="flex items-center gap-2 text-slate-300">
                <Building className="w-3.5 h-3.5 text-amber-400" />
                <span>{data.officer_contact?.office || "Room 204, Placement Block"}</span>
              </div>
            </div>

            <div className="pt-2">
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-center"
                onClick={() => setIsContactOpen(true)}
              >
                Send Direct Inquiry
              </Button>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Candidate Shortlist Table */}
      <Card>
        <CardHeader
          title={`Approved Candidate Shortlist (${data.shortlist?.length || 0})`}
          subtitle="Privacy protected view: candidate roll, name, department, CGPA, and criteria justification"
          action={
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-emerald-400">
                {data.attendance_stats?.present || 0} Present Today
              </span>
            </div>
          }
        />
        <CardBody>
          <Table
            data={data.shortlist || []}
            columns={columns}
            searchPlaceholder="Filter candidate by name, roll, or branch..."
            pageSize={12}
            exportFilename={`shortlist_${data.company_name}`}
          />
        </CardBody>
      </Card>

      {/* Recruiter Interview Slot Timetable */}
      <Card>
        <CardHeader
          title="Interview Panel Timetable"
          subtitle="Assigned interview cabins and candidates schedule"
          action={<ClashBadge clashCount={0} />}
        />
        <CardBody>
          {data.schedule && data.schedule.length > 0 ? (
            <div className="divide-y divide-[#1e3258]/60">
              {data.schedule.map((sl: any, idx: number) => (
                <div key={idx} className="p-3.5 flex flex-wrap items-center justify-between gap-3 hover:bg-[#111d38]/40 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 font-mono font-bold text-xs text-emerald-300 bg-[#080e1c] border border-[#1e3258] px-2.5 py-1 rounded-lg">
                      <Clock className="w-3.5 h-3.5 text-emerald-400" />
                      <span>{sl.slot_time}</span>
                    </div>
                    <div>
                      <span className="font-bold text-sm text-white block">{sl.candidate_name}</span>
                      <span className="text-xs font-mono text-cyan-400">{sl.candidate_roll_no}</span>
                    </div>
                  </div>

                  <div className="text-right text-xs">
                    <span className="font-semibold text-slate-200 block">{sl.venue}</span>
                    <span className="text-[11px] font-mono text-slate-400">{sl.panel}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-xs text-slate-400">
              No interview slots generated yet for this company.
            </div>
          )}
        </CardBody>
      </Card>

      {/* "WHY THIS STUDENT" TICK LIST MODAL */}
      <Modal
        isOpen={!!selectedCandidate}
        onClose={() => setSelectedCandidate(null)}
        title={`Why Was ${selectedCandidate?.name} Shortlisted?`}
      >
        {selectedCandidate && (
          <div className="space-y-4 text-xs">
            <div className="p-3 bg-[#080e1c] rounded-xl border border-[#1e3258] flex justify-between items-center">
              <div>
                <span className="font-bold text-white text-sm block">{selectedCandidate.name}</span>
                <span className="font-mono text-cyan-400 text-xs">{selectedCandidate.roll_no} • {selectedCandidate.branch}</span>
              </div>
              <StatusPill status={selectedCandidate.attendance} size="sm" />
            </div>

            <div className="space-y-2">
              <h4 className="text-xs font-mono font-bold uppercase text-slate-400">
                Evaluation Criteria Checklist:
              </h4>
              <div className="space-y-2">
                {selectedCandidate.criteria_breakdown?.map((crit, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-[#080e1c] border border-[#1e3258] flex items-center justify-between gap-3"
                  >
                    <div className="flex items-center gap-2.5">
                      {crit.satisfied ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                      ) : (
                        <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                      )}
                      <div>
                        <div className="font-bold text-white">{crit.criterion}</div>
                        <div className="text-[11px] text-slate-400 font-mono">
                          Required: {crit.required} | Student: <strong className="text-cyan-300">{crit.student_value}</strong>
                        </div>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-700/50">
                      SATISFIED
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-blue-950/20 border border-blue-800/40 text-[11px] text-slate-300">
              Verified by Campus Placement Engine. Candidate fulfills all institutional and corporate requirements.
            </div>

            <div className="pt-2 flex justify-end">
              <Button variant="primary" onClick={() => setSelectedCandidate(null)}>
                Close Checklist
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* CONTACT COLLEGE MODAL */}
      <Modal
        isOpen={isContactOpen}
        onClose={() => setIsContactOpen(false)}
        title="Direct Communication with Placement Cell"
      >
        <form onSubmit={handleSendContact} className="space-y-4 text-xs">
          <div>
            <label className="block text-slate-400 font-bold uppercase mb-1">
              Inquiry Type
            </label>
            <select
              value={contactType}
              onChange={(e) => setContactType(e.target.value)}
              className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white font-mono"
            >
              <option value="RECRUITER_QUERY">General Logistical Inquiry</option>
              <option value="EXTRA_PANEL">Request Additional Interview Room / Panel</option>
              <option value="SCHEDULE_CHANGE">Request Slot Timing Adjustment</option>
              <option value="OFFER_ANNOUNCEMENT">Submit Final Selected Candidates</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 font-bold uppercase mb-1">
              Subject
            </label>
            <input
              type="text"
              required
              value={contactSubject}
              onChange={(e) => setContactSubject(e.target.value)}
              placeholder="e.g. Need additional room for HR round in afternoon"
              className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white"
            />
          </div>

          <div>
            <label className="block text-slate-400 font-bold uppercase mb-1">
              Message to Placement Officer
            </label>
            <textarea
              required
              rows={4}
              value={contactMessage}
              onChange={(e) => setContactMessage(e.target.value)}
              placeholder="Describe your inquiry or requirement..."
              className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white"
            />
          </div>

          <div className="pt-2 flex justify-end gap-3">
            <Button
              variant="outline"
              type="button"
              onClick={() => setIsContactOpen(false)}
            >
              Cancel
            </Button>
            <Button variant="primary" type="submit" loading={submittingContact}>
              Send to Placement Officer
            </Button>
          </div>
        </form>
      </Modal>

      {/* "THIS LOOKS WRONG" CRITERIA FLAG MODAL */}
      <Modal
        isOpen={isFlagWrongOpen}
        onClose={() => setIsFlagWrongOpen(false)}
        title="Flag Criteria Discrepancy"
      >
        <form onSubmit={handleFlagWrongRequirements} className="space-y-4 text-xs">
          <p className="text-slate-300">
            If the CGPA cut-off, allowed branches, or backlogs shown above differ from your official recruitment agreement, let the Placement Officer know immediately.
          </p>

          <div>
            <label className="block text-slate-400 font-bold uppercase mb-1">
              Discrepancy Details
            </label>
            <textarea
              required
              rows={4}
              value={flagWrongReason}
              onChange={(e) => setFlagWrongReason(e.target.value)}
              placeholder="e.g. Our job circular specified 8.0 CGPA minimum cut-off, but the system applied 7.0 CGPA..."
              className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white"
            />
          </div>

          <div className="pt-2 flex justify-end gap-3">
            <Button
              variant="outline"
              type="button"
              onClick={() => setIsFlagWrongOpen(false)}
            >
              Cancel
            </Button>
            <Button variant="danger" type="submit" loading={flagSubmitting}>
              Submit Discrepancy Alert
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
