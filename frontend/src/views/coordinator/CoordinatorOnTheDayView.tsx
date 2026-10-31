import React, { useState, useEffect, useRef } from "react";
import { api } from "../../api/client";
import { Drive } from "../../types";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  UserCheck,
  CheckCircle,
  XCircle,
  Clock,
  MapPin,
  Calendar,
  Building,
  RefreshCw,
  Edit2,
  Users,
  Search,
  Download,
  Filter,
  CheckCheck,
} from "lucide-react";

interface AttendanceCandidate {
  slot_id?: string;
  student_id: string;
  roll_no: string;
  name: string;
  branch: string;
  start_time: string;
  room_name: string;
  attendance_status: "pending" | "present" | "absent" | "late";
  marked_at?: string;
  notes?: string;
}

interface DriveAttendanceData {
  drive_id: string;
  company_name: string;
  drive_date: string;
  total_scheduled: number;
  present_count: number;
  absent_count: number;
  late_count: number;
  pending_count: number;
  rooms: Record<string, AttendanceCandidate[]>;
}

interface CoordinatorOnTheDayViewProps {
  initialDriveId?: string;
}

const ATTENDANCE_SYNC_CHANNEL = "placement_engine_attendance_sync";

export const CoordinatorOnTheDayView: React.FC<CoordinatorOnTheDayViewProps> = ({
  initialDriveId,
}) => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<string>(initialDriveId || "");
  const [attendanceData, setAttendanceData] = useState<DriveAttendanceData | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeRoomTab, setActiveRoomTab] = useState<string>("");
  const [noteEditStudent, setNoteEditStudent] = useState<string | null>(null);
  const [candidateNote, setCandidateNote] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "present" | "absent" | "late" | "pending">("all");
  const [isExporting, setIsExporting] = useState(false);
  const [syncNotice, setSyncNotice] = useState<string | null>(null);

  const broadcastChannelRef = useRef<BroadcastChannel | null>(null);

  // Broadcast helper to notify other dashboards / tabs
  const broadcastChange = (driveId: string) => {
    try {
      if (broadcastChannelRef.current) {
        broadcastChannelRef.current.postMessage({
          type: "ATTENDANCE_UPDATED",
          driveId,
          timestamp: Date.now(),
        });
      }
    } catch {
      // BroadcastChannel not available in environment
    }
    window.dispatchEvent(new CustomEvent("attendance-updated", { detail: { driveId } }));
  };

  const fetchDrives = async () => {
    try {
      const res = await api.get<Drive[]>("/api/drives");
      const list = res || [];
      setDrives(list);
      if (list.length > 0) {
        if (!selectedDriveId || !list.some((d) => d.id === selectedDriveId)) {
          setSelectedDriveId(initialDriveId && list.some((d) => d.id === initialDriveId) ? initialDriveId : list[0].id);
        }
      } else {
        setSelectedDriveId("");
      }
    } catch {
      // Handled
    }
  };

  useEffect(() => {
    fetchDrives();
  }, [initialDriveId]);

  const fetchAttendance = async (driveId: string, showLoading = true) => {
    if (!driveId) return;
    try {
      if (showLoading) setLoading(true);
      const res = await api.get<DriveAttendanceData>(`/api/coordinator/attendance/${driveId}`);
      setAttendanceData(res);
      const roomKeys = Object.keys(res.rooms || {});
      if (roomKeys.length > 0 && (!activeRoomTab || !roomKeys.includes(activeRoomTab))) {
        setActiveRoomTab(roomKeys[0]);
      }
    } catch {
      setAttendanceData(null);
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDriveId) {
      fetchAttendance(selectedDriveId, true);
    }
  }, [selectedDriveId]);

  // Real-time synchronization setup: BroadcastChannel + Polling + CustomEvents
  useEffect(() => {
    if (!selectedDriveId) return;

    // 1. Setup BroadcastChannel for instant cross-tab sync
    try {
      if (typeof BroadcastChannel !== "undefined") {
        const bc = new BroadcastChannel(ATTENDANCE_SYNC_CHANNEL);
        broadcastChannelRef.current = bc;
        bc.onmessage = (event) => {
          if (event.data?.type === "ATTENDANCE_UPDATED" && event.data?.driveId === selectedDriveId) {
            fetchAttendance(selectedDriveId, false);
            setSyncNotice("Live attendance updated.");
            setTimeout(() => setSyncNotice(null), 2500);
          }
        };
      }
    } catch {
      // Ignore BroadcastChannel errors
    }

    // 2. Setup in-window custom event listener
    const handleLocalUpdate = (e: any) => {
      if (e.detail?.driveId === selectedDriveId) {
        fetchAttendance(selectedDriveId, false);
      }
    };
    window.addEventListener("attendance-updated", handleLocalUpdate);

    // 3. Setup periodic silent polling (every 3 seconds) for cross-session/cross-client sync
    const pollInterval = setInterval(() => {
      fetchAttendance(selectedDriveId, false);
    }, 3000);

    return () => {
      clearInterval(pollInterval);
      window.removeEventListener("attendance-updated", handleLocalUpdate);
      if (broadcastChannelRef.current) {
        broadcastChannelRef.current.close();
      }
    };
  }, [selectedDriveId, activeRoomTab]);

  const handleMarkStatus = async (
    candidate: AttendanceCandidate,
    newStatus: "present" | "absent" | "late" | "pending",
    notes?: string
  ) => {
    try {
      await api.post("/api/coordinator/attendance/mark", {
        drive_id: selectedDriveId,
        student_id: candidate.student_id,
        slot_id: candidate.slot_id,
        room_name: candidate.room_name,
        status: newStatus,
        notes: notes ?? candidate.notes,
      });

      // Update local state optimistically
      setAttendanceData((prev) => {
        if (!prev) return prev;
        const currentRoom = prev.rooms[candidate.room_name] || [];
        const updatedList = currentRoom.map((c) =>
          c.student_id === candidate.student_id
            ? { ...c, attendance_status: newStatus, notes: notes ?? c.notes }
            : c
        );

        let p = 0, a = 0, l = 0;
        Object.entries({ ...prev.rooms, [candidate.room_name]: updatedList }).forEach(([_, list]) => {
          list.forEach((item) => {
            if (item.attendance_status === "present") p++;
            else if (item.attendance_status === "absent") a++;
            else if (item.attendance_status === "late") l++;
          });
        });

        return {
          ...prev,
          present_count: p,
          absent_count: a,
          late_count: l,
          pending_count: Math.max(0, prev.total_scheduled - (p + a + l)),
          rooms: {
            ...prev.rooms,
            [candidate.room_name]: updatedList,
          },
        };
      });

      // Broadcast to other dashboard instances instantly
      broadcastChange(selectedDriveId);
    } catch {
      // Error handled
    }
  };

  const handleSaveNote = async (candidate: AttendanceCandidate) => {
    await handleMarkStatus(candidate, candidate.attendance_status, candidateNote);
    setNoteEditStudent(null);
    setCandidateNote("");
  };

  const handleBulkStatus = async (status: "present" | "absent") => {
    if (!selectedDriveId || !activeRoomTab || filteredCandidates.length === 0) return;
    try {
      const studentIds = filteredCandidates.map((c) => c.student_id);
      await api.post("/api/coordinator/attendance/bulk", {
        drive_id: selectedDriveId,
        room_name: activeRoomTab,
        status,
        student_ids: studentIds,
      });
      await fetchAttendance(selectedDriveId, false);
      broadcastChange(selectedDriveId);
    } catch {
      // Handled
    }
  };

  const handleExportCsv = async () => {
    if (!selectedDriveId) return;
    try {
      setIsExporting(true);
      const curDrive = drives.find((d) => d.id === selectedDriveId);
      const compName = curDrive ? curDrive.company_name.replace(/\s+/g, "_") : "drive";
      await api.download(
        `/api/exports/attendance/${selectedDriveId}/csv`,
        `${compName}_attendance.csv`
      );
    } catch {
      // Handled
    } finally {
      setIsExporting(false);
    }
  };

  const roomNames = Object.keys(attendanceData?.rooms || {});
  const activeCandidates = activeRoomTab && attendanceData?.rooms[activeRoomTab] ? attendanceData.rooms[activeRoomTab] : [];

  // Filter candidates by search query and status filter
  const filteredCandidates = activeCandidates.filter((c) => {
    const matchesSearch =
      !searchQuery.trim() ||
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.roll_no.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.branch.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus =
      statusFilter === "all" || c.attendance_status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Attendance Marking</h1>
            <Badge variant="brand">Live Sync</Badge>
            {syncNotice && (
              <span className="text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200 animate-pulse">
                {syncNotice}
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Real-time candidate attendance tracking synchronized across Officer and Coordinator dashboards.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={selectedDriveId}
            onChange={(e) => {
              setSelectedDriveId(e.target.value);
              setActiveRoomTab("");
            }}
            className="px-3.5 py-2 bg-white border border-slate-200 rounded-xl text-xs font-bold text-slate-800 shadow-xs cursor-pointer focus:ring-2 focus:ring-cyan-500"
          >
            {drives.map((d) => (
              <option key={d.id} value={d.id}>
                {d.company_name} ({d.drive_date})
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={handleExportCsv}
            disabled={isExporting || !selectedDriveId}
            className="flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer"
            title="Download attendance roster as CSV"
          >
            <Download className="w-3.5 h-3.5 text-indigo-600" />
            <span>{isExporting ? "Exporting..." : "Export CSV"}</span>
          </button>

          <button
            type="button"
            onClick={() => fetchAttendance(selectedDriveId, true)}
            className="p-2 text-slate-500 hover:text-slate-800 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 shadow-xs cursor-pointer"
            title="Refresh attendance counts"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-cyan-600" : ""}`} />
          </button>
        </div>
      </div>

      {/* Real-time Attendance Statistics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase">Total Scheduled</span>
          <span className="text-2xl font-black text-slate-900 block mt-1">{attendanceData?.total_scheduled ?? 0}</span>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-emerald-600 uppercase flex items-center gap-1">
            <CheckCircle className="w-3.5 h-3.5" /> Present
          </span>
          <span className="text-2xl font-black text-emerald-700 block mt-1">{attendanceData?.present_count ?? 0}</span>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-rose-600 uppercase flex items-center gap-1">
            <XCircle className="w-3.5 h-3.5" /> Absent
          </span>
          <span className="text-2xl font-black text-rose-700 block mt-1">{attendanceData?.absent_count ?? 0}</span>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-amber-600 uppercase flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" /> Late / Pending
          </span>
          <span className="text-2xl font-black text-amber-700 block mt-1">
            {(attendanceData?.late_count ?? 0) + (attendanceData?.pending_count ?? 0)}
          </span>
        </div>
      </div>

      {/* Room Tabs & Search/Filter Controls Bar */}
      <div className="space-y-3">
        {roomNames.length > 0 && (
          <div className="flex items-center gap-2 border-b border-slate-200 pb-2 overflow-x-auto no-scrollbar">
            {roomNames.map((rName) => (
              <button
                key={rName}
                type="button"
                onClick={() => setActiveRoomTab(rName)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
                  activeRoomTab === rName
                    ? "bg-slate-900 text-white shadow-2xs"
                    : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
                }`}
              >
                <MapPin className="w-3.5 h-3.5" />
                <span>{rName}</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-200 text-slate-700 font-mono">
                  {attendanceData?.rooms[rName]?.length ?? 0}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* Filter and Bulk Action Controls */}
        <div className="p-3 bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-1 max-w-md">
            <div className="relative w-full">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by student name, roll number, or branch..."
                className="w-full pl-9 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
            </div>
          </div>

          <div className="flex items-center gap-1.5 flex-wrap">
            <div className="flex items-center bg-slate-100 p-0.5 rounded-xl border border-slate-200 text-xs">
              {(["all", "present", "absent", "late", "pending"] as const).map((st) => (
                <button
                  key={st}
                  type="button"
                  onClick={() => setStatusFilter(st)}
                  className={`px-2.5 py-1 rounded-lg font-bold capitalize transition-all cursor-pointer ${
                    statusFilter === st
                      ? "bg-white text-slate-900 shadow-2xs"
                      : "text-slate-500 hover:text-slate-900"
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>

            <div className="h-4 w-px bg-slate-200 mx-1 hidden sm:block" />

            <button
              type="button"
              onClick={() => handleBulkStatus("present")}
              className="flex items-center gap-1 px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 font-bold text-xs rounded-xl border border-emerald-200 transition-colors cursor-pointer"
              title="Mark all visible candidates in this room as Present"
            >
              <CheckCheck className="w-3 h-3" />
              <span>All Present</span>
            </button>
            <button
              type="button"
              onClick={() => handleBulkStatus("absent")}
              className="flex items-center gap-1 px-2.5 py-1 bg-rose-50 hover:bg-rose-100 text-rose-800 font-bold text-xs rounded-xl border border-rose-200 transition-colors cursor-pointer"
              title="Mark all visible candidates in this room as Absent"
            >
              <XCircle className="w-3 h-3" />
              <span>All Absent</span>
            </button>
          </div>
        </div>
      </div>

      {/* Candidate Attendance Table */}
      {loading && !attendanceData ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500 text-sm animate-pulse">
          Loading candidate attendance...
        </div>
      ) : filteredCandidates.length === 0 ? (
        <div className="p-12 bg-white border border-slate-200 rounded-2xl text-center text-xs text-slate-500">
          No candidates matching current criteria in {activeRoomTab || "selected room"}.
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
                <th className="px-5 py-3.5">Reporting Time</th>
                <th className="px-5 py-3.5">Candidate</th>
                <th className="px-5 py-3.5">Branch</th>
                <th className="px-5 py-3.5">Attendance Status</th>
                <th className="px-5 py-3.5">Quick Notes</th>
                <th className="px-5 py-3.5 text-right">Floor Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredCandidates.map((c) => (
                <tr key={c.student_id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="px-5 py-3.5 font-mono font-bold text-slate-800">
                    {c.start_time.includes("T") ? c.start_time.split("T")[1].slice(0, 5) : c.start_time}
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="font-bold text-slate-900 block">{c.name}</span>
                    <span className="text-[11px] font-mono text-slate-400">Roll: {c.roll_no}</span>
                  </td>
                  <td className="px-5 py-3.5 text-slate-600">{c.branch}</td>
                  <td className="px-5 py-3.5">
                    <span
                      className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider inline-flex items-center gap-1 ${
                        c.attendance_status === "present"
                          ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                          : c.attendance_status === "absent"
                          ? "bg-rose-100 text-rose-800 border border-rose-300"
                          : c.attendance_status === "late"
                          ? "bg-amber-100 text-amber-800 border border-amber-300"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {c.attendance_status}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    {noteEditStudent === c.student_id ? (
                      <div className="flex items-center gap-1">
                        <input
                          type="text"
                          value={candidateNote}
                          onChange={(e) => setCandidateNote(e.target.value)}
                          placeholder="e.g. Arrived late..."
                          className="px-2 py-1 bg-white border border-slate-300 rounded text-xs w-44"
                        />
                        <button
                          type="button"
                          onClick={() => handleSaveNote(c)}
                          className="px-2 py-1 bg-slate-900 text-white rounded text-xs font-bold"
                        >
                          Save
                        </button>
                      </div>
                    ) : (
                      <div
                        onClick={() => {
                          setNoteEditStudent(c.student_id);
                          setCandidateNote(c.notes || "");
                        }}
                        className="text-slate-500 hover:text-slate-900 cursor-pointer flex items-center gap-1"
                        title="Click to edit floor note"
                      >
                        <span>{c.notes || "Click to add note..."}</span>
                        <Edit2 className="w-3 h-3 text-slate-400" />
                      </div>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        type="button"
                        onClick={() => handleMarkStatus(c, "present")}
                        className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                          c.attendance_status === "present"
                            ? "bg-emerald-600 text-white shadow-2xs"
                            : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200"
                        }`}
                      >
                        Present
                      </button>
                      <button
                        type="button"
                        onClick={() => handleMarkStatus(c, "late")}
                        className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                          c.attendance_status === "late"
                            ? "bg-amber-600 text-white shadow-2xs"
                            : "bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200"
                        }`}
                      >
                        Late
                      </button>
                      <button
                        type="button"
                        onClick={() => handleMarkStatus(c, "absent")}
                        className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                          c.attendance_status === "absent"
                            ? "bg-rose-600 text-white shadow-2xs"
                            : "bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200"
                        }`}
                      >
                        Absent
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
