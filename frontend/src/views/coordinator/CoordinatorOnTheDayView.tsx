import React, { useState, useEffect } from "react";
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

  const fetchDrives = async () => {
    try {
      const res = await api.get<Drive[]>("/api/drives");
      setDrives(res || []);
      if (res && res.length > 0 && !selectedDriveId) {
        setSelectedDriveId(initialDriveId || res[0].id);
      }
    } catch {
      // Handled
    }
  };

  useEffect(() => {
    fetchDrives();
  }, [initialDriveId]);

  const fetchAttendance = async (driveId: string) => {
    if (!driveId) return;
    try {
      setLoading(true);
      const res = await api.get<DriveAttendanceData>(`/api/coordinator/attendance/${driveId}`);
      setAttendanceData(res);
      const roomKeys = Object.keys(res.rooms || {});
      if (roomKeys.length > 0 && !activeRoomTab) {
        setActiveRoomTab(roomKeys[0]);
      }
    } catch {
      setAttendanceData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDriveId) fetchAttendance(selectedDriveId);
  }, [selectedDriveId]);

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

        // Recalculate counts
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
    } catch {
      // Error handled
    }
  };

  const handleSaveNote = async (candidate: AttendanceCandidate) => {
    await handleMarkStatus(candidate, candidate.attendance_status, candidateNote);
    setNoteEditStudent(null);
    setCandidateNote("");
  };

  const roomNames = Object.keys(attendanceData?.rooms || {});
  const activeCandidates = activeRoomTab && attendanceData?.rooms[activeRoomTab] ? attendanceData.rooms[activeRoomTab] : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">On-The-Day Drive Attendance</h1>
            <Badge variant="brand">Campus Floor Dispatch</Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Real-time candidate reporting per interview cabin. Mark candidates present, absent, or late to feed the officer's live operational view.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={selectedDriveId}
            onChange={(e) => {
              setSelectedDriveId(e.target.value);
              setActiveRoomTab("");
            }}
            className="px-3.5 py-2 bg-white border border-slate-200 rounded-xl text-xs font-bold text-slate-800 shadow-xs cursor-pointer"
          >
            {drives.map((d) => (
              <option key={d.id} value={d.id}>
                {d.company_name} ({d.drive_date})
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => fetchAttendance(selectedDriveId)}
            className="p-2 text-slate-500 hover:text-slate-800 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 shadow-xs cursor-pointer"
            title="Refresh attendance counts"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Real-time Running Attendance Counter Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase">Total Scheduled</span>
          <span className="text-2xl font-black text-slate-900 block mt-1">{attendanceData?.total_scheduled ?? 0}</span>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-emerald-600 uppercase flex items-center gap-1">
            <CheckCircle className="w-3.5 h-3.5" /> Present (Reported)
          </span>
          <span className="text-2xl font-black text-emerald-700 block mt-1">{attendanceData?.present_count ?? 0}</span>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-rose-600 uppercase flex items-center gap-1">
            <XCircle className="w-3.5 h-3.5" /> Absent (No-Show)
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

      {/* Room Tabs */}
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

      {/* Candidate Attendance Table */}
      {loading ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500 text-sm animate-pulse">
          Loading cabin candidate attendance...
        </div>
      ) : activeCandidates.length === 0 ? (
        <div className="p-12 bg-white border border-slate-200 rounded-2xl text-center text-xs text-slate-500">
          No candidates scheduled in physical venue {activeRoomTab || "selected"} for this drive.
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
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
              {activeCandidates.map((c) => (
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
                            ? "bg-emerald-600 text-white"
                            : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                        }`}
                      >
                        Present
                      </button>
                      <button
                        type="button"
                        onClick={() => handleMarkStatus(c, "late")}
                        className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                          c.attendance_status === "late"
                            ? "bg-amber-600 text-white"
                            : "bg-amber-50 text-amber-700 hover:bg-amber-100"
                        }`}
                      >
                        Late
                      </button>
                      <button
                        type="button"
                        onClick={() => handleMarkStatus(c, "absent")}
                        className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                          c.attendance_status === "absent"
                            ? "bg-rose-600 text-white"
                            : "bg-rose-50 text-rose-700 hover:bg-rose-100"
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
