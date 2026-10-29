import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Button } from "../../components/common/Button";
import { Input } from "../../components/common/Input";
import { Select } from "../../components/common/Select";
import { Table, Column } from "../../components/common/Table";
import { Card, CardHeader, CardBody } from "../../components/common/Card";
import { Modal } from "../../components/common/Modal";
import { StatusPill } from "../../components/domain/StatusPill";
import { ClashBadge } from "../../components/domain/ClashBadge";
import { ReasonLine } from "../../components/domain/ReasonLine";
import { ScheduleGrid, ScheduleAllocation } from "../../components/domain/ScheduleGrid";
import {
  Users,
  CheckCircle,
  Clock,
  AlertCircle,
  Briefcase,
  Calendar,
  Send,
  FileEdit,
  ClipboardList,
  ShieldCheck,
  RefreshCw,
  Search,
  UserCheck,
  UserX,
  Hourglass,
} from "lucide-react";

interface DriveSummary {
  id: string;
  company_name: string;
  role: string;
  status: string;
  date?: string;
  venue?: string;
  ctc_lpa?: number;
}

interface StudentItem {
  id: string;
  roll_number: string;
  name: string;
  branch: string;
  cgpa: number;
  backlogs: number;
  is_placed?: boolean;
}

interface AttendanceItem {
  id?: string;
  drive_id: string;
  student_roll: string;
  student_name?: string;
  time_slot: string;
  room: string;
  status: "PRESENT" | "ABSENT" | "LATE";
  marked_at?: string;
  remarks?: string;
}

interface CorrectionRequest {
  id: string;
  request_type: string;
  target_id: string;
  requester_role: string;
  status: string;
  reason: string;
  review_notes?: string;
  created_at: string;
}

export const CoordinatorDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"overview" | "attendance" | "students" | "drives" | "schedule" | "requests">("overview");
  const [drives, setDrives] = useState<DriveSummary[]>([]);
  const [students, setStudents] = useState<StudentItem[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<string>("");
  const [attendanceRecords, setAttendanceRecords] = useState<AttendanceItem[]>([]);
  const [requests, setRequests] = useState<CorrectionRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  // Correction Request Modal
  const [isCorrectionModalOpen, setIsCorrectionModalOpen] = useState(false);
  const [correctionRoll, setCorrectionRoll] = useState("");
  const [correctionField, setCorrectionField] = useState("cgpa");
  const [correctionCurrent, setCorrectionCurrent] = useState("");
  const [correctionProposed, setCorrectionProposed] = useState("");
  const [correctionReason, setCorrectionReason] = useState("");
  const [submittingReq, setSubmittingReq] = useState(false);

  // Clash Flag Modal
  const [isClashModalOpen, setIsClashModalOpen] = useState(false);
  const [clashNote, setClashNote] = useState("");

  const showToast = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 3500);
  };

  // Load Initial Data
  useEffect(() => {
    fetchDrives();
    fetchRequests();
  }, []);

  const fetchDrives = async () => {
    try {
      const data = await api.get<any>("/api/drives");
      const list = Array.isArray(data) ? data : data.drives || [];
      setDrives(list);
      if (list.length > 0) {
        if (!selectedDriveId || !list.some((d: any) => d.id === selectedDriveId)) {
          setSelectedDriveId(list[0].id);
          fetchDriveDetails(list[0].id);
        }
      } else {
        setSelectedDriveId("");
      }
    } catch (err) {
      console.error("Failed to load drives", err);
    }
  };

  const fetchDriveDetails = async (driveId: string) => {
    try {
      setLoading(true);
      // Fetch attendance
      const attData = await api.get<any>(`/api/attendance/${driveId}`);
      if (attData && attData.records) {
        setAttendanceRecords(attData.records);
      } else {
        setAttendanceRecords([]);
      }

      // Fetch candidates roster
      const candData = await api.get<any>(`/api/eligibility/${driveId}`);
      if (candData && candData.candidates) {
        setStudents(
          candData.candidates.map((c: any) => ({
            id: c.roll_number,
            roll_number: c.roll_number,
            name: c.name || c.student_name || "Candidate",
            branch: c.branch || "CSE",
            cgpa: c.cgpa || 8.0,
            backlogs: c.backlogs || 0,
            is_placed: c.is_placed || false,
          }))
        );
      }
    } catch (err) {
      console.error("Failed to fetch drive details", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchRequests = async () => {
    try {
      const reqData = await api.get<any>("/api/requests");
      const list = Array.isArray(reqData) ? reqData : reqData.requests || [];
      setRequests(list);
    } catch (err) {
      console.error("Failed to load requests", err);
    }
  };

  // Handle Drive Change
  const handleDriveChange = (driveId: string) => {
    setSelectedDriveId(driveId);
    fetchDriveDetails(driveId);
  };

  // Mark Attendance
  const handleMarkAttendance = async (
    roll: string,
    timeSlot: string,
    room: string,
    status: "PRESENT" | "ABSENT" | "LATE"
  ) => {
    if (!selectedDriveId) return;
    try {
      await api.post("/api/attendance/mark", {
        drive_id: selectedDriveId,
        student_roll: roll,
        time_slot: timeSlot,
        room: room,
        status: status,
        remarks: `Marked by coordinator at ${new Date().toLocaleTimeString()}`,
      });

      // Update state locally for instant snappy feedback
      setAttendanceRecords((prev) => {
        const existingIdx = prev.findIndex((r) => r.student_roll === roll);
        if (existingIdx >= 0) {
          const updated = [...prev];
          updated[existingIdx] = { ...updated[existingIdx], status };
          return updated;
        } else {
          return [
            ...prev,
            {
              drive_id: selectedDriveId,
              student_roll: roll,
              time_slot: timeSlot,
              room: room,
              status: status,
              marked_at: new Date().toISOString(),
            },
          ];
        }
      });
      showToast(`Marked ${roll} as ${status}`);
    } catch (err: any) {
      alert(`Error marking attendance: ${err.message}`);
    }
  };

  // Submit Correction Request to Officer
  const handleSubmitCorrection = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingReq(true);
    try {
      await api.post("/api/requests", {
        request_type: "STUDENT_DATA_CORRECTION",
        target_entity: "student",
        target_id: correctionRoll,
        requested_changes: {
          field: correctionField,
          current_value: correctionCurrent,
          proposed_value: correctionProposed,
        },
        reason: correctionReason,
        requester_role: "coordinator",
      });

      setIsCorrectionModalOpen(false);
      setCorrectionRoll("");
      setCorrectionReason("");
      setCorrectionCurrent("");
      setCorrectionProposed("");
      showToast("Data correction request dispatched to Officer");
      fetchRequests();
    } catch (err: any) {
      alert(`Failed to submit request: ${err.message}`);
    } finally {
      setSubmittingReq(false);
    }
  };

  // Flag Clash to Officer
  const handleFlagClash = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/api/requests", {
        request_type: "SCHEDULE_CLASH_FLAG",
        target_entity: "drive",
        target_id: selectedDriveId,
        requested_changes: {
          flag: "UNRESOLVED_TIME_OVERLAP",
          details: clashNote,
        },
        reason: clashNote,
        requester_role: "coordinator",
      });
      setIsClashModalOpen(false);
      setClashNote("");
      showToast("Clash notification dispatched to Placement Officer");
      fetchRequests();
    } catch (err: any) {
      alert(`Failed to flag clash: ${err.message}`);
    }
  };

  // Attendance Statistics
  const presentCount = attendanceRecords.filter((r) => r.status === "PRESENT").length;
  const absentCount = attendanceRecords.filter((r) => r.status === "ABSENT").length;
  const lateCount = attendanceRecords.filter((r) => r.status === "LATE").length;
  const totalRoster = students.length > 0 ? students.length : attendanceRecords.length;

  return (
    <div className="space-y-6 pb-12">
      {/* Toast Notification */}
      {notification && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#0d1527] border border-emerald-500/50 text-emerald-300 px-4 py-3 rounded-2xl shadow-2xl flex items-center gap-2 text-xs font-bold animate-in fade-in slide-in-from-bottom-2">
          <CheckCircle className="w-4 h-4 text-emerald-400" />
          <span>{notification}</span>
        </div>
      )}

      {/* Top Coordinator Banner */}
      <div className="bg-[#0d1527] border border-[#1e3258] rounded-2xl p-6 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-700/60 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
              Coordinator Workspace
            </span>
            <span className="text-xs text-slate-400 font-mono">
              View & Prepare Mode • Policy Locked
            </span>
          </div>
          <h2 className="text-2xl font-black text-white">
            Placement Operations & Attendance Desk
          </h2>
          <p className="text-xs text-slate-300 mt-1">
            Conduct on-the-day attendance, monitor schedule clashes, and submit candidate record correction requests to the Officer.
          </p>
        </div>

        {/* Drive Selector */}
        <div className="w-full sm:w-72">
          <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">
            Active Placement Drive
          </label>
          <select
            value={selectedDriveId}
            onChange={(e) => handleDriveChange(e.target.value)}
            className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-semibold text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            {drives.map((d) => (
              <option key={d.id} value={d.id}>
                {d.company_name} - {d.role} ({d.status})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex items-center gap-1.5 bg-[#080e1c] p-1.5 rounded-2xl border border-[#1e3258] overflow-x-auto no-scrollbar">
        {[
          { id: "overview", label: "Overview", icon: ClipboardList },
          { id: "attendance", label: "On-the-Day Attendance", icon: CheckCircle, badge: `${presentCount} Present` },
          { id: "students", label: "Student Roster", icon: Users },
          { id: "drives", label: "Drive Details", icon: Briefcase },
          { id: "schedule", label: "Schedule & Clashes", icon: Calendar },
          { id: "requests", label: "Requests to Officer", icon: Send, badge: `${requests.length}` },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
                isActive
                  ? "bg-gradient-to-r from-blue-700 to-emerald-600 text-white shadow-md shadow-emerald-950"
                  : "text-slate-400 hover:text-white hover:bg-[#111d38]"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
              {tab.badge && (
                <span
                  className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full ${
                    isActive ? "bg-white/20 text-white" : "bg-[#1e3258] text-slate-300"
                  }`}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Quick Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardBody className="p-4 flex items-center justify-between">
                <div>
                  <div className="text-xs font-mono uppercase text-slate-400">Total Roster</div>
                  <div className="text-2xl font-black text-white mt-1">{totalRoster}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">Candidates in drive</div>
                </div>
                <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
                  <Users className="w-5 h-5" />
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardBody className="p-4 flex items-center justify-between">
                <div>
                  <div className="text-xs font-mono uppercase text-slate-400">Present Today</div>
                  <div className="text-2xl font-black text-emerald-400 mt-1">{presentCount}</div>
                  <div className="text-[11px] text-emerald-400/80 mt-0.5">
                    {totalRoster > 0 ? `${Math.round((presentCount / totalRoster) * 100)}% turnout` : "0%"}
                  </div>
                </div>
                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                  <UserCheck className="w-5 h-5" />
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardBody className="p-4 flex items-center justify-between">
                <div>
                  <div className="text-xs font-mono uppercase text-slate-400">Absent / Late</div>
                  <div className="text-2xl font-black text-amber-400 mt-1">
                    {absentCount + lateCount}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {absentCount} Absent, {lateCount} Late
                  </div>
                </div>
                <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
                  <UserX className="w-5 h-5" />
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardBody className="p-4 flex items-center justify-between">
                <div>
                  <div className="text-xs font-mono uppercase text-slate-400">Requests to Officer</div>
                  <div className="text-2xl font-black text-cyan-400 mt-1">{requests.length}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {requests.filter((r) => r.status === "PENDING_REVIEW").length} pending review
                  </div>
                </div>
                <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                  <Send className="w-5 h-5" />
                </div>
              </CardBody>
            </Card>
          </div>

          {/* Quick Action Strip */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader
                title="Operational Guidelines for Coordinators"
                subtitle="Rules governing on-campus verification & role scope"
              />
              <CardBody className="space-y-3 text-xs text-slate-300">
                <div className="flex items-start gap-2.5 p-3 rounded-xl bg-[#080e1c] border border-[#1e3258]">
                  <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <span>
                    <strong>Mark Attendance in Real-Time:</strong> Interview panels rely on the live roster to call in candidates. Toggle status as students enter the interview lab.
                  </span>
                </div>
                <div className="flex items-start gap-2.5 p-3 rounded-xl bg-[#080e1c] border border-[#1e3258]">
                  <FileEdit className="w-4 h-4 text-cyan-400 flex-shrink-0 mt-0.5" />
                  <span>
                    <strong>Candidate Data Discrepancies:</strong> You cannot modify CGPA, backlogs, or offer policy directly. Submit a formal change request to the Placement Officer.
                  </span>
                </div>
                <div className="flex items-start gap-2.5 p-3 rounded-xl bg-[#080e1c] border border-[#1e3258]">
                  <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                  <span>
                    <strong>Schedule Clashes:</strong> If a student has back-to-back or overlapping rounds with another company, flag the clash immediately.
                  </span>
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardHeader
                title="Quick Operations"
                subtitle="Shortcuts for frequent day-of-drive tasks"
              />
              <CardBody className="space-y-3">
                <Button
                  variant="primary"
                  className="w-full justify-center"
                  onClick={() => setActiveTab("attendance")}
                >
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Start On-The-Day Attendance
                </Button>
                <Button
                  variant="secondary"
                  className="w-full justify-center"
                  onClick={() => setIsCorrectionModalOpen(true)}
                >
                  <FileEdit className="w-4 h-4 mr-2 text-cyan-400" />
                  Request Student Record Correction
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-center"
                  onClick={() => setIsClashModalOpen(true)}
                >
                  <AlertCircle className="w-4 h-4 mr-2 text-amber-400" />
                  Flag Schedule Conflict to Officer
                </Button>
              </CardBody>
            </Card>
          </div>
        </div>
      )}

      {/* TAB 2: ON-THE-DAY ATTENDANCE */}
      {activeTab === "attendance" && (
        <Card>
          <CardHeader
            title="On-The-Day Attendance Marking"
            subtitle="Click once to mark candidate attendance. Changes sync directly to the scheduler & recruiter dashboard."
          />
          <CardBody className="space-y-4">
            {/* Quick Filter Header */}
            <div className="flex flex-wrap items-center justify-between gap-4 p-3 bg-[#080e1c] rounded-xl border border-[#1e3258]">
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono uppercase text-slate-400 font-bold">Live Status:</span>
                <span className="text-xs font-mono text-emerald-400 font-bold">{presentCount} Present</span>
                <span className="text-slate-600">•</span>
                <span className="text-xs font-mono text-rose-400 font-bold">{absentCount} Absent</span>
                <span className="text-slate-600">•</span>
                <span className="text-xs font-mono text-amber-400 font-bold">{lateCount} Late</span>
              </div>
              <div className="text-xs text-slate-400 font-mono">
                Auto-saved to central engine audit log
              </div>
            </div>

            {/* Attendance Roster Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-[#080e1c] text-slate-400 font-mono font-bold uppercase tracking-wider border-b border-[#1e3258]">
                    <th className="p-3">Roll Number</th>
                    <th className="p-3">Candidate Name</th>
                    <th className="p-3">Branch</th>
                    <th className="p-3">Time Window</th>
                    <th className="p-3">Venue / Room</th>
                    <th className="p-3">Current Status</th>
                    <th className="p-3 text-right">Quick Mark Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e3258]/60">
                  {students.slice(0, 50).map((s, idx) => {
                    const existingAtt = attendanceRecords.find((r) => r.student_roll === s.roll_number);
                    const currentStatus = existingAtt?.status || "PENDING";
                    const slot = "09:00 - 09:45";
                    const room = idx % 2 === 0 ? "Interview Lab 101" : "Interview Lab 102";

                    return (
                      <tr key={s.roll_number} className="hover:bg-[#111d38]/50 transition-colors">
                        <td className="p-3 font-mono font-bold text-cyan-400">{s.roll_number}</td>
                        <td className="p-3 font-semibold text-white">{s.name}</td>
                        <td className="p-3 font-mono text-slate-300">{s.branch}</td>
                        <td className="p-3 font-mono text-slate-400">{slot}</td>
                        <td className="p-3 text-slate-300">{room}</td>
                        <td className="p-3">
                          <StatusPill status={currentStatus} size="sm" />
                        </td>
                        <td className="p-3 text-right">
                          <div className="inline-flex items-center gap-1.5 bg-[#080e1c] p-1 rounded-xl border border-[#1e3258]">
                            <button
                              type="button"
                              onClick={() => handleMarkAttendance(s.roll_number, slot, room, "PRESENT")}
                              className={`px-2.5 py-1 rounded-lg font-mono text-[11px] font-bold cursor-pointer transition-all ${
                                currentStatus === "PRESENT"
                                  ? "bg-emerald-600 text-white shadow-sm shadow-emerald-950"
                                  : "text-slate-400 hover:text-emerald-300 hover:bg-emerald-950/40"
                              }`}
                            >
                              Present
                            </button>
                            <button
                              type="button"
                              onClick={() => handleMarkAttendance(s.roll_number, slot, room, "LATE")}
                              className={`px-2.5 py-1 rounded-lg font-mono text-[11px] font-bold cursor-pointer transition-all ${
                                currentStatus === "LATE"
                                  ? "bg-amber-600 text-white shadow-sm shadow-amber-950"
                                  : "text-slate-400 hover:text-amber-300 hover:bg-amber-950/40"
                              }`}
                            >
                              Late
                            </button>
                            <button
                              type="button"
                              onClick={() => handleMarkAttendance(s.roll_number, slot, room, "ABSENT")}
                              className={`px-2.5 py-1 rounded-lg font-mono text-[11px] font-bold cursor-pointer transition-all ${
                                currentStatus === "ABSENT"
                                  ? "bg-rose-600 text-white shadow-sm shadow-rose-950"
                                  : "text-slate-400 hover:text-rose-300 hover:bg-rose-950/40"
                              }`}
                            >
                              Absent
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardBody>
        </Card>
      )}

      {/* TAB 3: STUDENT ROSTER WITH CORRECTION REQUEST TRIGGER */}
      {activeTab === "students" && (
        <Card>
          <CardHeader
            title="Candidate Roster (Read-Only)"
            subtitle="Verified student records. Coordinators can submit correction requests if discrepancies are spotted."
            action={
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setIsCorrectionModalOpen(true)}
              >
                <FileEdit className="w-3.5 h-3.5 mr-1.5 text-cyan-400" />
                Request Correction
              </Button>
            }
          />
          <CardBody>
            <Table
              data={students}
              columns={[
                { key: "roll_number", header: "Roll Number", sortable: true },
                { key: "name", header: "Candidate Name", sortable: true },
                { key: "branch", header: "Branch", sortable: true },
                { key: "cgpa", header: "CGPA", sortable: true },
                { key: "backlogs", header: "Backlogs", sortable: true },
                {
                  key: "actions",
                  header: "Correction",
                  render: (item) => (
                    <button
                      type="button"
                      onClick={() => {
                        setCorrectionRoll(item.roll_number);
                        setCorrectionCurrent(String(item.cgpa));
                        setIsCorrectionModalOpen(true);
                      }}
                      className="text-xs text-cyan-400 hover:text-cyan-300 underline font-mono cursor-pointer"
                    >
                      Report issue
                    </button>
                  ),
                },
              ]}
              searchPlaceholder="Filter by roll or student name..."
              pageSize={15}
            />
          </CardBody>
        </Card>
      )}

      {/* TAB 4: DRIVES DETAILS */}
      {activeTab === "drives" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {drives.map((d) => (
            <Card key={d.id}>
              <CardHeader
                title={d.company_name}
                subtitle={d.role}
                action={<StatusPill status={d.status} size="sm" />}
              />
              <CardBody className="space-y-3 text-xs">
                <div className="flex justify-between py-1 border-b border-[#1e3258]/60">
                  <span className="text-slate-400">Package (CTC):</span>
                  <span className="font-mono font-bold text-white">
                    {d.ctc_lpa ? `₹${d.ctc_lpa} LPA` : "Not specified"}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1e3258]/60">
                  <span className="text-slate-400">Venue:</span>
                  <span className="text-slate-200">{d.venue || "Placement Center Block A"}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1e3258]/60">
                  <span className="text-slate-400">Interview Mode:</span>
                  <span className="text-emerald-400 font-semibold">In-Person Panel</span>
                </div>
                <div className="pt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-center"
                    onClick={() => {
                      handleDriveChange(d.id);
                      setActiveTab("attendance");
                    }}
                  >
                    View Attendance for this Drive
                  </Button>
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {/* TAB 5: SCHEDULE & CLASHES */}
      {activeTab === "schedule" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              Live Room Matrix & Clash Surveillance
            </h3>
            <Button
              variant="danger"
              size="sm"
              onClick={() => setIsClashModalOpen(true)}
            >
              <AlertCircle className="w-3.5 h-3.5 mr-1.5" />
              Flag Schedule Clash to Officer
            </Button>
          </div>

          <ScheduleGrid
            allocations={students.slice(0, 16).map((s, idx) => ({
              id: `alloc-${idx}`,
              studentName: s.name,
              rollNumber: s.roll_number,
              companyName: drives.find((d) => d.id === selectedDriveId)?.company_name || "Assigned Company",
              room: idx % 2 === 0 ? "Interview Lab 101" : "Interview Lab 102",
              timeSlot: idx < 4 ? "09:00 - 09:45" : idx < 8 ? "09:45 - 10:30" : "10:45 - 11:30",
              status: "scheduled",
            }))}
          />
        </div>
      )}

      {/* TAB 6: REQUESTS DISPATCHED TO OFFICER */}
      {activeTab === "requests" && (
        <Card>
          <CardHeader
            title="Dispatched Change Requests"
            subtitle="Status of data corrections and clash flags submitted to the Placement Officer"
            action={
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsCorrectionModalOpen(true)}
              >
                <FileEdit className="w-3.5 h-3.5 mr-1.5" />
                New Request
              </Button>
            }
          />
          <CardBody>
            {requests.length === 0 ? (
              <div className="text-center py-12 text-slate-400 text-xs">
                No active change requests submitted yet.
              </div>
            ) : (
              <div className="divide-y divide-[#1e3258]/60">
                {requests.map((r) => (
                  <div key={r.id} className="p-4 flex flex-wrap items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono font-bold text-xs text-white">
                          #{r.id.slice(0, 8)}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded bg-[#111d38] text-cyan-300 font-mono border border-[#1e3258]">
                          {r.request_type}
                        </span>
                        <StatusPill status={r.status} size="sm" />
                      </div>
                      <div className="text-xs text-slate-300">
                        Target: <span className="font-mono text-cyan-400">{r.target_id}</span> • Reason:{" "}
                        <span className="text-slate-400">{r.reason}</span>
                      </div>
                      {r.review_notes && (
                        <div className="mt-1 text-xs text-emerald-400 bg-emerald-950/30 px-2.5 py-1 rounded-lg border border-emerald-800/40">
                          Officer Note: {r.review_notes}
                        </div>
                      )}
                    </div>
                    <div className="text-right text-[11px] font-mono text-slate-500">
                      {new Date(r.created_at).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      )}

      {/* CORRECTION REQUEST MODAL */}
      <Modal
        isOpen={isCorrectionModalOpen}
        onClose={() => setIsCorrectionModalOpen(false)}
        title="Submit Candidate Record Correction"
      >
        <form onSubmit={handleSubmitCorrection} className="space-y-4 text-xs">
          <div>
            <label className="block text-slate-400 font-bold uppercase mb-1">
              Student Roll Number
            </label>
            <input
              type="text"
              required
              value={correctionRoll}
              onChange={(e) => setCorrectionRoll(e.target.value)}
              placeholder="e.g. BT21001"
              className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white font-mono"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-400 font-bold uppercase mb-1">
                Field to Correct
              </label>
              <select
                value={correctionField}
                onChange={(e) => setCorrectionField(e.target.value)}
                className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white font-mono"
              >
                <option value="cgpa">CGPA</option>
                <option value="backlogs">Active Backlogs</option>
                <option value="branch">Branch / Department</option>
                <option value="attendance">Drive Attendance</option>
              </select>
            </div>
            <div>
              <label className="block text-slate-400 font-bold uppercase mb-1">
                Current Value
              </label>
              <input
                type="text"
                value={correctionCurrent}
                onChange={(e) => setCorrectionCurrent(e.target.value)}
                placeholder="e.g. 7.1"
                className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-slate-400 font-bold uppercase mb-1">
              Proposed / Verified Value
            </label>
            <input
              type="text"
              required
              value={correctionProposed}
              onChange={(e) => setCorrectionProposed(e.target.value)}
              placeholder="e.g. 7.85 (Semester 6 marksheet verified)"
              className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white font-mono"
            />
          </div>

          <div>
            <label className="block text-slate-400 font-bold uppercase mb-1">
              Justification & Verification Note
            </label>
            <textarea
              required
              rows={3}
              value={correctionReason}
              onChange={(e) => setCorrectionReason(e.target.value)}
              placeholder="Explain physical verification details or marksheet reference for the officer..."
              className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white"
            />
          </div>

          <div className="pt-2 flex justify-end gap-3">
            <Button
              variant="outline"
              type="button"
              onClick={() => setIsCorrectionModalOpen(false)}
            >
              Cancel
            </Button>
            <Button variant="primary" type="submit" loading={submittingReq}>
              Submit Request to Officer
            </Button>
          </div>
        </form>
      </Modal>

      {/* CLASH FLAG MODAL */}
      <Modal
        isOpen={isClashModalOpen}
        onClose={() => setIsClashModalOpen(false)}
        title="Flag Interview Schedule Conflict"
      >
        <form onSubmit={handleFlagClash} className="space-y-4 text-xs">
          <p className="text-slate-300">
            Send an immediate priority flag to the Placement Officer if a candidate or interview room has an unresolved clash.
          </p>
          <div>
            <label className="block text-slate-400 font-bold uppercase mb-1">
              Clash Description & Candidate / Room Details
            </label>
            <textarea
              required
              rows={4}
              value={clashNote}
              onChange={(e) => setClashNote(e.target.value)}
              placeholder="e.g. Student BT21045 is scheduled for Round 2 at 11:00 in Lab 101, but is also shortlisted for Amazon panel at 11:15 in Lab 102."
              className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white"
            />
          </div>
          <div className="pt-2 flex justify-end gap-3">
            <Button
              variant="outline"
              type="button"
              onClick={() => setIsClashModalOpen(false)}
            >
              Cancel
            </Button>
            <Button variant="danger" type="submit">
              Flag to Officer
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
