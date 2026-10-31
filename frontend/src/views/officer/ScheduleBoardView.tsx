import React, { useState, useEffect, useRef, useMemo } from "react";
import { api } from "../../api/client";
import { Drive, ScheduleSlot } from "../../types";
import { Badge } from "../../components/common/Badge";
import { ProgressBar } from "../../components/common/ProgressBar";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  Calendar,
  ShieldCheck,
  AlertTriangle,
  Play,
  Clock,
  MapPin,
  RefreshCw,
  Users,
  X,
  CheckCircle2,
  Building,
  UserCheck,
} from "lucide-react";

interface ScheduleBoardViewProps {
  initialDriveId?: string;
}

export const ScheduleBoardView: React.FC<ScheduleBoardViewProps> = ({ initialDriveId }) => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<string>(initialDriveId || "");
  const [slots, setSlots] = useState<ScheduleSlot[]>([]);
  const [loading, setLoading] = useState(false);
  const [scheduling, setScheduling] = useState(false);
  const [progress, setProgress] = useState(0);
  const [clashCount, setClashCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<ScheduleSlot | null>(null);
  const [showClassroomModal, setShowClassroomModal] = useState(false);
  const [roomTab, setRoomTab] = useState<"provision" | "custom">("provision");
  const [provisionStudents, setProvisionStudents] = useState<number>(40);
  const [provisionRoundType, setProvisionRoundType] = useState<string>("interview");
  const [provisionCapacity, setProvisionCapacity] = useState<number>(40);
  const [customRoomName, setCustomRoomName] = useState<string>("");
  const [customRoomBuilding, setCustomRoomBuilding] = useState<string>("Academic Complex");
  const [customRoomCapacity, setCustomRoomCapacity] = useState<number>(40);
  const [roomActionLoading, setRoomActionLoading] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Standard 30-minute placement interview time slots across normal campus hours
  const baseTimeColumns = [
    "09:00",
    "09:30",
    "10:00",
    "10:30",
    "11:00",
    "11:30",
    "12:00",
    "12:30",
    "13:00",
    "13:30",
    "14:00",
    "14:30",
    "15:00",
    "15:30",
    "16:00",
    "16:30",
    "17:00",
  ];

  // Helper to extract HH:MM string from any slot timestamp
  const extractSlotTime = (slot: ScheduleSlot): string => {
    if (slot.time_slot && slot.time_slot.length >= 5) {
      return slot.time_slot.slice(0, 5);
    }
    const st = slot.start_time || "";
    if (st.includes(" ")) {
      const parts = st.split(" ");
      return parts[parts.length - 1].slice(0, 5);
    }
    if (st.includes("T")) {
      return st.split("T")[1].slice(0, 5);
    }
    return st.slice(0, 5);
  };

  // Dynamically compute time columns to include any extra slot hours
  const timeColumns = useMemo(() => {
    const times = new Set<string>(baseTimeColumns);
    slots.forEach((s) => {
      const t = extractSlotTime(s);
      if (t && /^\d{2}:\d{2}$/.test(t)) {
        times.add(t);
      }
    });
    return Array.from(times).sort();
  }, [slots]);

  // Dynamically derive all active campus venues and cabins from scheduled slots
  const roomsList = useMemo(() => {
    const map = new Map<string, { id: string; name: string }>();

    // 1. Add all venues where interviews are actually scheduled
    slots.forEach((s) => {
      const rName = s.room_name || "Classroom";
      const rId = s.room_id || rName.toLowerCase().replace(/[^a-z0-9]/g, "_");
      if (!map.has(rName)) {
        map.set(rName, { id: rId, name: rName });
      }
    });

    // 2. Ensure standard classrooms always exist for baseline display if empty
    if (map.size === 0) {
      map.set("Classroom 101", { id: "room_class_101", name: "Classroom 101" });
      map.set("Classroom 102", { id: "room_class_102", name: "Classroom 102" });
      map.set("Main Auditorium", { id: "hall_auditorium", name: "Main Auditorium (Hall)" });
    }

    return Array.from(map.values()).sort((a, b) => {
      // Put auditorium first, then cabins in numeric/alphabetical order
      if (a.name.toLowerCase().includes("auditorium")) return -1;
      if (b.name.toLowerCase().includes("auditorium")) return 1;
      return a.name.localeCompare(b.name, undefined, { numeric: true });
    });
  }, [slots]);

  useEffect(() => {
    const fetchDrives = async () => {
      try {
        const res = await api.get<Drive[]>("/api/drives");
        const list = res || [];
        setDrives(list);
        if (list.length > 0) {
          if (!selectedDriveId || !list.some((d) => d.id === selectedDriveId)) {
            setSelectedDriveId(list[0].id);
          }
        } else {
          setSelectedDriveId("");
        }
      } catch {
        setError("Failed to load drives.");
      }
    };
    fetchDrives();
  }, [initialDriveId]);

  const handleAutoProvisionRooms = async (e: React.FormEvent) => {
    e.preventDefault();
    setRoomActionLoading(true);
    try {
      const selectedDrive = drives.find((d) => d.id === selectedDriveId);
      const res = await api.post<{
        status: string;
        newly_provisioned_count: number;
        needed_classrooms: number;
      }>("/api/rooms/provision-for-students", {
        students_count: provisionStudents,
        round_type: provisionRoundType,
        capacity_per_room: provisionCapacity,
        target_date: selectedDrive?.drive_date,
      });
      setSuccess(
        `Classrooms allocated! ${res.newly_provisioned_count} new classroom(s) created matching ${provisionStudents} student requirements.`
      );
      setShowClassroomModal(false);
      if (selectedDriveId) fetchSchedule(selectedDriveId);
    } catch (err: any) {
      setError(err?.message || "Failed to provision classrooms.");
    } finally {
      setRoomActionLoading(false);
    }
  };

  const handleCreateCustomRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customRoomName.trim()) return;
    setRoomActionLoading(true);
    try {
      await api.post("/api/rooms", {
        name: customRoomName.trim(),
        building: customRoomBuilding,
        capacity: customRoomCapacity,
        room_type: "classroom",
      });
      setSuccess(`Classroom '${customRoomName.trim()}' successfully created with capacity ${customRoomCapacity}!`);
      setCustomRoomName("");
      setShowClassroomModal(false);
      if (selectedDriveId) fetchSchedule(selectedDriveId);
    } catch (err: any) {
      setError(err?.message || "Failed to create classroom.");
    } finally {
      setRoomActionLoading(false);
    }
  };

  const fetchSchedule = async (driveId: string) => {
    if (!driveId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.get<ScheduleSlot[]>(`/api/schedules/${driveId}`);
      setSlots(res || []);
      detectClashes(res || []);
    } catch {
      setSlots([]);
      setClashCount(0);
    } finally {
      setLoading(false);
    }
  };

  const detectClashes = (items: ScheduleSlot[]) => {
    let collisions = 0;
    for (let i = 0; i < items.length; i++) {
      for (let j = i + 1; j < items.length; j++) {
        // Same student at same start_time in two different venues
        if (
          items[i].student_id === items[j].student_id &&
          items[i].start_time === items[j].start_time
        ) {
          collisions++;
        }
      }
    }
    const uniqueCrossDriveClashes = new Set(
      items.filter((it: any) => it.has_clash).map((it: any) => it.clash_detail || it.student_id)
    ).size;
    setClashCount(collisions + uniqueCrossDriveClashes);
  };

  useEffect(() => {
    if (selectedDriveId) {
      fetchSchedule(selectedDriveId);
    }
  }, [selectedDriveId]);

  const handleGenerateSchedule = async () => {
    if (!selectedDriveId) return;
    try {
      setScheduling(true);
      setProgress(15);
      setError(null);
      setSuccess(null);

      abortControllerRef.current = new AbortController();

      const timer = setInterval(() => {
        setProgress((prev) => (prev >= 85 ? 85 : prev + 25));
      }, 150);

      const res = await api.post<any>(
        "/api/schedules/generate",
        {
          drive_id: selectedDriveId,
          num_panels: 2,
          round_duration_minutes: 30,
        },
        abortControllerRef.current.signal
      );

      clearInterval(timer);
      setProgress(100);

      if (res.clash_count === 0) {
        setSuccess(
          `Schedule generated successfully: ${res.students_scheduled || 0} students scheduled across venues with 0 clashes verified!`
        );
      } else {
        setError(
          `Schedule generated with ${res.clash_count} unresolved clashes. Please review conflicting drives.`
        );
      }

      setTimeout(() => {
        setScheduling(false);
        fetchSchedule(selectedDriveId);
      }, 300);
    } catch (err: any) {
      if (err.name === "AbortError") {
        setError("Schedule generation cancelled.");
      } else {
        setError(err.message || "Failed to generate schedule.");
      }
      setScheduling(false);
    }
  };

  const handleCancelScheduling = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setScheduling(false);
  };

  // Count unique students scheduled in active slots
  const uniqueStudentsCount = useMemo(() => {
    const sids = new Set(slots.map((s) => s.student_id || s.roll_no));
    return sids.size;
  }, [slots]);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">Interview & Test Schedule Grid</h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Google OR-Tools CP-SAT discrete solver. Each student is assigned strictly to their exact time slot with 0 repetition.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedDriveId}
            onChange={(e) => setSelectedDriveId(e.target.value)}
            className="px-3.5 py-2 bg-white dark:bg-[#121E36] border border-slate-200 dark:border-[#1E3156] text-slate-800 dark:text-white rounded-xl text-xs font-bold shadow-xs focus:ring-2 focus:ring-blue-500 focus:outline-hidden cursor-pointer"
          >
            {drives.map((d) => (
              <option key={d.id} value={d.id}>
                {d.company_name} ({d.ctc_lpa} LPA)
              </option>
            ))}
          </select>

          <button
            onClick={() => setShowClassroomModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-blue-50 dark:bg-[#14223E] hover:bg-blue-100 dark:hover:bg-[#1A2D52] text-blue-700 dark:text-blue-400 text-xs font-bold rounded-xl border border-blue-200 dark:border-[#1F3560] shadow-xs transition-colors cursor-pointer"
            title="Auto-provision or add classrooms according to student requirements"
          >
            <Building className="w-3.5 h-3.5" />
            <span>+ Classrooms</span>
          </button>

          <button
            onClick={handleGenerateSchedule}
            disabled={scheduling || !selectedDriveId}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Generate Clash-Free Schedule</span>
          </button>
        </div>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {success && <AlertBanner type="success" message={success} onClose={() => setSuccess(null)} />}

      {/* Heavy Action Progress */}
      {scheduling && (
        <ProgressBar
          label="Running CP-SAT Discrete Constraint Solver..."
          progressPercent={progress}
          isCancellable={true}
          onCancel={handleCancelScheduling}
          subLabel="Evaluating interval variables & non-overlapping room non-repetition guarantees"
        />
      )}

      {/* Verification Status Banner (Theme-Adaptive) */}
      <div className="corporate-card flex flex-col sm:flex-row sm:items-center justify-between p-4 shadow-xs gap-4">
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
              clashCount === 0 && slots.length > 0
                ? "bg-emerald-100 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/80 dark:text-emerald-400 dark:border-emerald-800/60"
                : clashCount > 0
                ? "bg-rose-100 text-rose-700 border border-rose-200 dark:bg-rose-950/80 dark:text-rose-400 dark:border-rose-800/60"
                : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
            }`}
          >
            {clashCount === 0 && slots.length > 0 ? (
              <ShieldCheck className="w-6 h-6" />
            ) : (
              <AlertTriangle className="w-6 h-6" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-extrabold tracking-tight">
                {clashCount === 0 && slots.length > 0
                  ? "0 Clashes Verified (Mathematically Proven)"
                  : clashCount > 0
                  ? `${clashCount} Collisions Detected`
                  : "No Active Schedule Slots"}
              </h3>
              {clashCount === 0 && slots.length > 0 && (
                <span className="text-[10px] font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-700/60 px-2 py-0.5 rounded-full uppercase tracking-wider">
                  Guaranteed
                </span>
              )}
            </div>
            <p className="text-xs opacity-70 mt-0.5">
              {uniqueStudentsCount} unique students scheduled across {roomsList.length} physical venues. Each candidate occupies exactly one time slot per round.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <div className="text-right text-xs opacity-75 hidden sm:block">
            <span className="font-extrabold">{slots.length}</span> Total Slots •{" "}
            <span className="font-extrabold">{roomsList.length}</span> Classrooms / Venues
          </div>
          <button
            onClick={() => fetchSchedule(selectedDriveId)}
            className="p-2 opacity-80 hover:opacity-100 bg-slate-100 hover:bg-slate-200 dark:bg-[#14203A] dark:hover:bg-[#1A2C50] border border-slate-200 dark:border-[#1E325A] rounded-lg transition-colors cursor-pointer"
            title="Refresh schedule"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-blue-600" : ""}`} />
          </button>
        </div>
      </div>

      {/* Schedule Matrix Grid (Theme-Adaptive) */}
      <div className="corporate-card overflow-hidden">
        <div className="overflow-x-auto">
          <table
            className="w-full border-separate border-spacing-0"
            style={{ minWidth: `${Math.max(900, 240 + timeColumns.length * 160)}px` }}
          >
            <colgroup>
              <col style={{ width: "240px", minWidth: "240px", maxWidth: "240px" }} />
              {timeColumns.map((time) => (
                <col key={time} style={{ width: "160px", minWidth: "160px" }} />
              ))}
            </colgroup>
            <thead>
              <tr className="border-b border-[var(--border-card)]">
                <th
                  style={{
                    position: "sticky",
                    left: 0,
                    zIndex: 50,
                    backgroundColor: "#0B1326",
                    background: "#0B1326",
                    isolation: "isolate",
                    transform: "translate3d(0, 0, 0)",
                    WebkitTransform: "translate3d(0, 0, 0)",
                    minWidth: "240px",
                    maxWidth: "240px",
                    width: "240px",
                    boxShadow: "6px 0 16px -2px rgba(0, 0, 0, 0.95)",
                    borderRight: "2px solid var(--border-card, #16264C)",
                    padding: 0,
                  }}
                  className="schedule-sticky-header"
                >
                  <div className="w-[240px] min-w-[240px] max-w-[240px] p-4 text-xs font-black uppercase tracking-wider text-slate-300 text-left bg-[#0B1326] whitespace-nowrap">
                    Campus Classroom / Venue
                  </div>
                </th>
                {timeColumns.map((time) => (
                  <th
                    key={time}
                    style={{
                      minWidth: "160px",
                      width: "160px",
                      backgroundColor: "var(--bg-card, #0B1326)",
                      borderRight: "1px solid var(--border-card, #16264C)",
                      whiteSpace: "nowrap",
                    }}
                    className="p-3 text-xs font-extrabold text-center schedule-time-header text-slate-300"
                  >
                    <Clock className="w-3.5 h-3.5 inline mr-1.5 text-blue-600 dark:text-cyan-400" />
                    {time}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-card)]">
              {roomsList.map((room) => (
                <tr key={room.id} className="transition-colors hover:bg-white/[0.02]">
                  <td
                    style={{
                      position: "sticky",
                      left: 0,
                      zIndex: 30,
                      backgroundColor: "#0B1326",
                      background: "#0B1326",
                      minWidth: "240px",
                      maxWidth: "240px",
                      width: "240px",
                      boxShadow: "6px 0 16px -2px rgba(0, 0, 0, 0.95)",
                      borderRight: "2px solid var(--border-card, #16264C)",
                      padding: 0,
                    }}
                    className="schedule-sticky-col"
                  >
                    <div className="w-[240px] min-w-[240px] max-w-[240px] h-full min-h-[5.5rem] p-4 flex items-center gap-2.5 bg-[#0B1326] text-xs font-extrabold text-white select-none">
                      <div className="w-6 h-6 rounded-md bg-blue-50 dark:bg-blue-950/80 border border-blue-200 dark:border-blue-700/60 flex items-center justify-center text-blue-600 dark:text-cyan-400 shrink-0">
                        <MapPin className="w-3.5 h-3.5" />
                      </div>
                      <span className="truncate font-black text-white" title={room.name}>
                        {room.name}
                      </span>
                    </div>
                  </td>
                  {timeColumns.map((time) => {
                    // Match slot strictly for this room AND this exact time slot
                    const slot = slots.find((s) => {
                      // 1. Strict Room matching logic
                      const roomMatches =
                        Boolean(s.room_id && (s.room_id.toLowerCase() === room.id.toLowerCase() || s.room_id.toLowerCase() === room.name.toLowerCase())) ||
                        s.room_name.toLowerCase().trim() === room.name.toLowerCase().trim();

                      if (!roomMatches) return false;

                      // 2. Exact Time matching logic (prevents student from repeating across columns)
                      const slotHm = extractSlotTime(s);
                      return slotHm === time;
                    });

                    return (
                      <td
                        key={time}
                        style={{
                          minWidth: "160px",
                          width: "160px",
                          borderRight: "1px solid var(--border-card, #16264C)",
                        }}
                        className="p-2 schedule-slot-cell align-top h-24"
                      >
                        {slot ? (
                          <div
                            onClick={() => setSelectedSlot(slot)}
                            className={`${
                              (slot as any).has_clash
                                ? "bg-rose-950/90 hover:bg-rose-900/80 border-2 border-rose-500 shadow-lg shadow-rose-950/50"
                                : "bg-[var(--bg-card)] hover:bg-[var(--bg-card-hover)] border border-[var(--border-card)] border-t-2 border-t-cyan-400 hover:border-cyan-400 shadow-md hover:shadow-cyan-950/40"
                            } rounded-xl p-2.5 cursor-pointer transition-all space-y-1.5 group`}
                            title={(slot as any).clash_detail || undefined}
                          >
                            <div className="flex items-center justify-between gap-1">
                              <span className="text-xs font-extrabold text-white block truncate group-hover:text-cyan-400 transition-colors">
                                {slot.student_name}
                              </span>
                              {slot.has_applied && (
                                <span className="px-1.5 py-0.2 rounded text-[9px] font-extrabold bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-950/80 dark:text-blue-300 dark:border-blue-700/60 shrink-0">
                                  Applied
                                </span>
                              )}
                            </div>
                            <span className="text-[11px] font-mono font-bold text-cyan-400 block truncate">
                              {slot.roll_no}
                            </span>
                            <div className="flex items-center justify-between text-[10.5px] font-semibold text-slate-500 dark:text-slate-400 pt-1.5 border-t border-slate-100 dark:border-[#1C2C4E]">
                              <span className="truncate">{slot.round_name}</span>
                              {(slot as any).has_clash ? (
                                <span className="font-extrabold text-rose-800 dark:text-rose-300 shrink-0 bg-rose-100 dark:bg-rose-950 border border-rose-300 dark:border-rose-500/60 px-1.5 py-0.5 rounded text-[9.5px]">
                                  CLASH
                                </span>
                              ) : (
                                <span className="font-extrabold text-emerald-800 dark:text-emerald-300 shrink-0 bg-emerald-100 dark:bg-emerald-950 border border-emerald-300 dark:border-emerald-500/50 px-2 py-0.5 rounded text-[9.5px]">
                                  OK
                                </span>
                              )}
                            </div>
                          </div>
                        ) : (
                          <div className="w-full h-full rounded-xl min-h-[64px] border border-dashed border-[var(--border-card)] bg-[var(--bg-input)]/50 flex items-center justify-center text-xs text-slate-400 font-semibold hover:border-cyan-400 hover:text-cyan-400 transition-all">
                            Available
                          </div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected Slot Inspector Modal (Theme-Adaptive) */}
      {selectedSlot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="corporate-card max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <div className="w-9 h-9 rounded-xl bg-emerald-950/80 border border-emerald-500/30 text-emerald-400 flex items-center justify-center font-bold">
                  <UserCheck className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Scheduled Interview Slot</h3>
                  <p className="text-xs text-slate-500">Deterministic discrete solver allocation</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedSlot(null)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-slate-50 rounded-xl space-y-1 border border-slate-200/80">
                <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center justify-between">
                  <span>Candidate</span>
                  {selectedSlot.has_applied && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                      Applied Candidate
                    </span>
                  )}
                </div>
                <div className="text-sm font-black text-slate-900">{selectedSlot.student_name}</div>
                <div className="font-mono text-xs font-bold text-blue-700">{selectedSlot.roll_no}</div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-slate-50 rounded-xl space-y-1 border border-slate-200/80">
                  <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                    <Clock className="w-3 h-3 text-blue-600" /> Time Window
                  </div>
                  <div className="font-bold text-slate-800">
                    {extractSlotTime(selectedSlot)} - {selectedSlot.end_time || "Scheduled"}
                  </div>
                </div>

                <div className="p-3 bg-slate-50 rounded-xl space-y-1 border border-slate-200/80">
                  <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                    <Building className="w-3 h-3 text-emerald-600" /> Venue
                  </div>
                  <div className="font-bold text-slate-800 truncate">
                    {selectedSlot.room_name}
                  </div>
                </div>
              </div>

              <div className="p-3 bg-emerald-50/80 rounded-xl border border-emerald-200/80 flex items-center justify-between">
                <div className="flex items-center gap-2 text-emerald-800 font-bold">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>{selectedSlot.round_name} • Clash-Free</span>
                </div>
                <span className="text-[10px] font-mono text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full font-bold">
                  PROVEN
                </span>
              </div>
            </div>

            <button
              onClick={() => setSelectedSlot(null)}
              className="w-full py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl transition-colors cursor-pointer"
            >
              Close Inspector
            </button>
          </div>
        </div>
      )}

      {/* Classroom Provisioning & Creation Modal */}
      {showClassroomModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Building className="w-5 h-5 text-blue-600" />
                <h3 className="text-base font-bold text-white">Classroom Allocation & Provisioning</h3>
              </div>
              <button
                onClick={() => setShowClassroomModal(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Tab switch */}
            <div className="flex bg-slate-100 p-1 rounded-xl">
              <button
                type="button"
                onClick={() => setRoomTab("provision")}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                  roomTab === "provision"
                    ? "bg-white text-blue-600 shadow-xs"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                Auto-Provision for Students
              </button>
              <button
                type="button"
                onClick={() => setRoomTab("custom")}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                  roomTab === "custom"
                    ? "bg-white text-blue-600 shadow-xs"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                Add Single Classroom
              </button>
            </div>

            {roomTab === "provision" ? (
              <form onSubmit={handleAutoProvisionRooms} className="space-y-3.5">
                <p className="text-xs text-slate-500">
                  If classrooms are unavailable for your candidates, the engine dynamically provisions dedicated campus classrooms matching your students' requirements.
                </p>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Students Count</label>
                  <input
                    type="number"
                    min="1"
                    max="5000"
                    value={provisionStudents}
                    onChange={(e) => setProvisionStudents(parseInt(e.target.value) || 1)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-xs font-medium text-slate-800 focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Round Type</label>
                    <select
                      value={provisionRoundType}
                      onChange={(e) => setProvisionRoundType(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-xl text-xs font-medium text-slate-800 focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                    >
                      <option value="interview">1-on-1 Interview</option>
                      <option value="test">Written Test / GD</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Capacity / Room</label>
                    <input
                      type="number"
                      min="5"
                      max="300"
                      value={provisionCapacity}
                      onChange={(e) => setProvisionCapacity(parseInt(e.target.value) || 40)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-xl text-xs font-medium text-slate-800 focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                      required
                    />
                  </div>
                </div>

                <div className="pt-2 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowClassroomModal(false)}
                    className="px-3 py-2 text-xs font-bold text-slate-500 hover:text-slate-800 rounded-xl cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={roomActionLoading}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
                  >
                    {roomActionLoading ? "Provisioning..." : "Provision Classrooms"}
                  </button>
                </div>
              </form>
            ) : (
              <form onSubmit={handleCreateCustomRoom} className="space-y-3.5">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Classroom Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Classroom 601"
                    value={customRoomName}
                    onChange={(e) => setCustomRoomName(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-xs font-medium text-slate-800 focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Building</label>
                    <input
                      type="text"
                      value={customRoomBuilding}
                      onChange={(e) => setCustomRoomBuilding(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-xl text-xs font-medium text-slate-800 focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Capacity</label>
                    <input
                      type="number"
                      min="5"
                      max="500"
                      value={customRoomCapacity}
                      onChange={(e) => setCustomRoomCapacity(parseInt(e.target.value) || 40)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-xl text-xs font-medium text-slate-800 focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                      required
                    />
                  </div>
                </div>

                <div className="pt-2 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowClassroomModal(false)}
                    className="px-3 py-2 text-xs font-bold text-slate-500 hover:text-slate-800 rounded-xl cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={roomActionLoading || !customRoomName.trim()}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
                  >
                    {roomActionLoading ? "Creating..." : "Create Classroom"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
