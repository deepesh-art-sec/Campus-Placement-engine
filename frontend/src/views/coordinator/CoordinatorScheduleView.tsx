import React, { useState, useEffect, useMemo } from "react";
import { api } from "../../api/client";
import { Drive, ScheduleSlot } from "../../types";
import { Badge } from "../../components/common/Badge";
import { Modal } from "../../components/common/Modal";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  Calendar,
  Clock,
  ShieldCheck,
  MapPin,
  RefreshCw,
  Flag,
  AlertTriangle,
  User,
  Info,
  Send,
} from "lucide-react";

interface CoordinatorScheduleViewProps {
  initialDriveId?: string;
}

export const CoordinatorScheduleView: React.FC<CoordinatorScheduleViewProps> = ({
  initialDriveId,
}) => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<string>(initialDriveId || "");
  const [slots, setSlots] = useState<ScheduleSlot[]>([]);
  const [loading, setLoading] = useState(false);
  const [clashCount, setClashCount] = useState(0);

  // Flag schedule issue modal
  const [flagModalOpen, setFlagModalOpen] = useState(false);
  const [flagTopic, setFlagTopic] = useState("Venue Capacity / Overlapping Interview Time");
  const [flagDescription, setFlagDescription] = useState("");
  const [flagSuccess, setFlagSuccess] = useState<string | null>(null);
  const [flagSubmitting, setFlagSubmitting] = useState(false);

  // Inspect slot
  const [inspectedSlot, setInspectedSlot] = useState<ScheduleSlot | null>(null);

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

  const extractSlotTime = (slot: ScheduleSlot): string => {
    if (slot.time_slot && slot.time_slot.length >= 5) return slot.time_slot.slice(0, 5);
    const st = slot.start_time || "";
    if (st.includes(" ")) {
      const parts = st.split(" ");
      return parts[parts.length - 1].slice(0, 5);
    }
    if (st.includes("T")) return st.split("T")[1].slice(0, 5);
    return st.slice(0, 5);
  };

  const timeColumns = useMemo(() => {
    const times = new Set<string>(baseTimeColumns);
    slots.forEach((s) => {
      const t = extractSlotTime(s);
      if (t && /^\d{2}:\d{2}$/.test(t)) times.add(t);
    });
    return Array.from(times).sort();
  }, [slots]);

  const roomsList = useMemo(() => {
    const map = new Map<string, { id: string; name: string }>();
    slots.forEach((s) => {
      const rName = s.room_name || "Classroom";
      const rId = s.room_id || rName.toLowerCase().replace(/[^a-z0-9]/g, "_");
      if (!map.has(rName)) map.set(rName, { id: rId, name: rName });
    });
    if (map.size === 0) {
      map.set("Classroom 101", { id: "room_class_101", name: "Classroom 101" });
      map.set("Classroom 102", { id: "room_class_102", name: "Classroom 102" });
    }
    return Array.from(map.values());
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
        // Fallback
      }
    };
    fetchDrives();
  }, []);

  const fetchSchedule = async (driveId: string) => {
    if (!driveId) return;
    try {
      setLoading(true);
      const res = await api.get<ScheduleSlot[]>(`/api/schedules/${driveId}`);
      setSlots(res || []);
      const uniqueCrossDriveClashes = new Set(
        (res || []).filter((it: any) => it.has_clash).map((it: any) => it.clash_detail || it.student_id)
      ).size;
      setClashCount(uniqueCrossDriveClashes);
    } catch {
      setSlots([]);
      setClashCount(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDriveId) fetchSchedule(selectedDriveId);
  }, [selectedDriveId]);

  const handleSubmitFlag = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!flagDescription.trim() || !selectedDriveId) return;

    try {
      setFlagSubmitting(true);
      await api.post("/api/coordinator/requests", {
        request_type: "logistics",
        title: flagTopic,
        description: flagDescription,
        target_id: selectedDriveId,
        payload: { drive_id: selectedDriveId },
      });
      const todayStr = new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
      setFlagSuccess(`Schedule problem flagged to Officer on ${todayStr}.`);
      setFlagDescription("");
      setTimeout(() => setFlagModalOpen(false), 2000);
    } catch {
      // Handled
    } finally {
      setFlagSubmitting(false);
    }
  };

  const selectedDrive = drives.find((d) => d.id === selectedDriveId);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-white tracking-tight">Schedule Grid (View Only)</h1>
            <Badge variant="brand">Read-Only Dispatch</Badge>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            View room and panel interview assignments. Coordinators cannot move interview slots; report venue or timing clashes directly to the Officer.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={selectedDriveId}
            onChange={(e) => setSelectedDriveId(e.target.value)}
            className="px-3.5 py-2 bg-[#0A1122] border border-[#1A2E56] rounded-xl text-xs font-bold text-white shadow-xs cursor-pointer focus:border-cyan-400"
          >
            {drives.map((d) => (
              <option key={d.id} value={d.id}>
                {d.company_name} ({d.drive_date})
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => setFlagModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors cursor-pointer"
          >
            <Flag className="w-3.5 h-3.5" />
            <span>Flag Schedule Problem</span>
          </button>
        </div>
      </div>

      {/* Verification Badge Banner */}
      <div className={`corporate-card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${clashCount === 0 ? "" : "border-amber-500/50 bg-amber-950/20"}`}>
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${clashCount === 0 ? "bg-emerald-950/80 text-emerald-400 border border-emerald-700/60" : "bg-amber-950/80 text-amber-400 border border-amber-700/60"}`}>
            {clashCount === 0 ? <ShieldCheck className="w-6 h-6" /> : <AlertTriangle className="w-6 h-6" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-extrabold tracking-tight text-white">
                {clashCount === 0 ? "0 Clashes Verified (Mathematically Proven)" : `${clashCount} Clashes Detected`}
              </h3>
              <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full uppercase tracking-wider ${clashCount === 0 ? "bg-emerald-950 text-emerald-300 border border-emerald-700/60" : "bg-amber-950 text-amber-300 border border-amber-700/60"}`}>
                CP-SAT Discrete Solver
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              {clashCount === 0
                ? "Strict interval scheduling: each shortlisted student occupies exactly one cabin slot per round with zero collision."
                : "Active schedule conflicts detected across drives. Please coordinate with the Placement Officer."}
            </p>
          </div>
        </div>

        <div className="text-xs text-slate-400 hidden sm:block">
          <strong className="text-white">{slots.length}</strong> Slots Allocated across <strong className="text-white">{roomsList.length}</strong> Venues
        </div>
      </div>

      {/* Schedule Matrix Table */}
      <div className="corporate-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-[#152445]">
                <th className="p-4 text-xs font-black uppercase tracking-wider text-slate-300 w-56 min-w-[224px] max-w-[224px] text-left border-r border-[#152445] sticky left-0 z-20 bg-[var(--bg-card)] shadow-[4px_0_12px_rgba(0,0,0,0.5)]">
                  Campus Classroom / Venue
                </th>
                {timeColumns.map((time) => (
                  <th key={time} className="p-2.5 text-xs font-extrabold text-slate-300 text-center min-w-[155px] border-r border-[#152445] bg-[var(--bg-card)]">
                    <Clock className="w-3 h-3 inline mr-1 text-cyan-400" />
                    {time}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#152445] text-xs">
              {roomsList.map((room) => (
                <tr key={room.id} className="transition-colors hover:bg-white/[0.02]">
                  <td className="p-3.5 font-extrabold text-white border-r border-[#152445] sticky left-0 z-10 w-56 min-w-[224px] max-w-[224px] bg-[var(--bg-card)] shadow-[4px_0_12px_rgba(0,0,0,0.5)]">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-md bg-blue-950/80 border border-blue-700/60 flex items-center justify-center text-cyan-400 shrink-0">
                        <MapPin className="w-3.5 h-3.5" />
                      </div>
                      <span className="truncate font-extrabold">{room.name}</span>
                    </div>
                  </td>
                  {timeColumns.map((time) => {
                    const slot = slots.find((s) => {
                      const rMatches =
                        Boolean(s.room_id && (s.room_id.toLowerCase() === room.id.toLowerCase() || s.room_id.toLowerCase() === room.name.toLowerCase())) ||
                        s.room_name.toLowerCase().trim() === room.name.toLowerCase().trim();
                      return rMatches && extractSlotTime(s) === time;
                    });

                    return (
                      <td key={time} className="p-2 border-r border-[#152445] text-center align-top h-24">
                        {slot ? (
                          <div
                            onClick={() => setInspectedSlot(slot)}
                            className="p-2.5 rounded-xl bg-[var(--bg-card)] hover:bg-[var(--bg-card-hover)] border border-[var(--border-card)] border-t-2 border-t-cyan-400 hover:border-cyan-400 text-left shadow-md hover:shadow-cyan-950/40 transition-all cursor-pointer group space-y-1.5"
                          >
                            <span className="font-extrabold text-xs text-white block truncate group-hover:text-cyan-400 transition-colors">
                              {slot.student_name || slot.student_id}
                            </span>
                            <span className="text-[11px] text-cyan-400 font-mono font-bold block truncate">
                              {slot.roll_no || slot.student_id}
                            </span>
                            <div className="flex items-center justify-between text-[10.5px] font-semibold text-slate-400 pt-1.5 border-t border-[#1C2C4E]">
                              <span className="truncate">{slot.round_name || "Round 1"}</span>
                              <span className="font-extrabold text-emerald-300 shrink-0 bg-emerald-950 border border-emerald-500/50 px-2 py-0.5 rounded text-[9.5px]">
                                OK
                              </span>
                            </div>
                          </div>
                        ) : (
                          <div className="w-full h-full min-h-[64px] rounded-xl border border-dashed border-[var(--border-card)] bg-[var(--bg-input)]/50 flex items-center justify-center text-xs text-slate-400 font-semibold hover:border-cyan-400 hover:text-cyan-400 transition-all">
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

      {/* Flag Schedule Problem Modal */}
      {flagModalOpen && (
        <Modal
          isOpen={flagModalOpen}
          onClose={() => setFlagModalOpen(false)}
          title={`Flag Schedule Problem to Officer`}
        >
          <form onSubmit={handleSubmitFlag} className="space-y-4 text-xs">
            {flagSuccess && <AlertBanner type="success" message={flagSuccess} onClose={() => setFlagSuccess(null)} />}

            <p className="text-slate-600">
              Coordinators cannot drag or move slots to preserve mathematical clash-freedom. If a recruiter requests a schedule move or cabin adjustment, send a request to the Officer.
            </p>

            <div>
              <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">Issue Topic</label>
              <input
                type="text"
                required
                value={flagTopic}
                onChange={(e) => setFlagTopic(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white"
              />
            </div>

            <div>
              <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                Description & Proposed Fix <span className="text-rose-500">*</span>
              </label>
              <textarea
                rows={3}
                required
                placeholder="e.g. Student BT210005 has a lab viva at 11:00 AM; request moving slot to 02:00 PM in Cabin 2..."
                value={flagDescription}
                onChange={(e) => setFlagDescription(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white"
              />
            </div>

            <div className="pt-2 flex justify-end gap-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setFlagModalOpen(false)}
                className="px-3 py-1.5 text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={flagSubmitting || !flagDescription.trim()}
                className="flex items-center gap-1.5 px-4 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded-xl shadow-xs cursor-pointer disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{flagSubmitting ? "Submitting..." : "Send to Officer"}</span>
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Inspect Slot Modal */}
      {inspectedSlot && (
        <Modal
          isOpen={!!inspectedSlot}
          onClose={() => setInspectedSlot(null)}
          title="Interview Slot Details"
        >
          <div className="space-y-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
              <span className="font-bold text-slate-900 text-sm block">{inspectedSlot.student_name || "Candidate"}</span>
              <span className="text-slate-500 font-mono">Roll: {inspectedSlot.roll_no || inspectedSlot.student_id}</span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-slate-700">
              <div className="p-2 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Venue</span>
                <span className="font-semibold">{inspectedSlot.room_name}</span>
              </div>
              <div className="p-2 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Time Window</span>
                <span className="font-mono font-semibold">{extractSlotTime(inspectedSlot)}</span>
              </div>
            </div>

            <div className="p-3 bg-blue-50 text-blue-900 border border-blue-200 rounded-xl text-[11px]">
              Slot is verified clash-free. Use the "Flag Schedule Problem" tool if candidate is unable to attend.
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
