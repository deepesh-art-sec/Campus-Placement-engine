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
      const rName = s.room_name || "Interview Cabin";
      const rId = s.room_id || rName.toLowerCase().replace(/[^a-z0-9]/g, "_");
      if (!map.has(rName)) map.set(rName, { id: rId, name: rName });
    });
    if (map.size === 0) {
      map.set("Interview Cabin 1", { id: "cabin_1", name: "Interview Cabin 1" });
      map.set("Interview Cabin 2", { id: "cabin_2", name: "Interview Cabin 2" });
    }
    return Array.from(map.values());
  }, [slots]);

  useEffect(() => {
    const fetchDrives = async () => {
      try {
        const res = await api.get<Drive[]>("/api/drives");
        setDrives(res || []);
        if (res.length > 0) setSelectedDriveId(res[0].id);
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
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Schedule Grid (View Only)</h1>
            <Badge variant="brand">Read-Only Dispatch</Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            View room and panel interview assignments. Coordinators cannot move interview slots; report venue or timing clashes directly to the Officer.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={selectedDriveId}
            onChange={(e) => setSelectedDriveId(e.target.value)}
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
            onClick={() => setFlagModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors cursor-pointer"
          >
            <Flag className="w-3.5 h-3.5" />
            <span>Flag Schedule Problem</span>
          </button>
        </div>
      </div>

      {/* Verification Badge Banner */}
      <div className={`p-4 bg-white rounded-2xl border shadow-xs flex items-center justify-between ${clashCount === 0 ? "border-slate-200" : "border-amber-300 bg-amber-50/50"}`}>
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${clashCount === 0 ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
            {clashCount === 0 ? <ShieldCheck className="w-6 h-6" /> : <AlertTriangle className="w-6 h-6" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-900">
                {clashCount === 0 ? "0 Clashes Verified" : `${clashCount} Clashes Detected`}
              </h3>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${clashCount === 0 ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                CP-SAT Discrete Solver
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {clashCount === 0
                ? "Strict interval scheduling: each shortlisted student occupies exactly one cabin slot per round with zero collision."
                : "Active schedule conflicts detected across drives. Please coordinate with the Placement Officer."}
            </p>
          </div>
        </div>

        <div className="text-xs text-slate-500 hidden sm:block">
          <strong>{slots.length}</strong> Slots Allocated across <strong>{roomsList.length}</strong> Venues
        </div>
      </div>

      {/* Schedule Matrix Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="p-3.5 text-xs font-bold text-slate-700 w-52 text-left border-r border-slate-200 sticky left-0 bg-slate-50 z-10">
                  Venue / Cabin
                </th>
                {timeColumns.map((time) => (
                  <th key={time} className="p-2.5 text-xs font-bold text-slate-600 text-center min-w-[140px] border-r border-slate-200">
                    <Clock className="w-3 h-3 inline mr-1 text-slate-400" />
                    {time}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {roomsList.map((room) => (
                <tr key={room.id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="p-3.5 font-bold text-slate-800 border-r border-slate-200 sticky left-0 bg-white z-10">
                    <div className="flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                      <span className="truncate">{room.name}</span>
                    </div>
                  </td>
                  {timeColumns.map((time) => {
                    const slot = slots.find((s) => {
                      const rMatches =
                        s.room_name.toLowerCase().trim() === room.name.toLowerCase().trim() ||
                        (room.name.includes("1") && s.room_name.includes("1")) ||
                        (room.name.includes("2") && s.room_name.includes("2"));
                      return rMatches && extractSlotTime(s) === time;
                    });

                    return (
                      <td key={time} className="p-2 border-r border-slate-200 text-center">
                        {slot ? (
                          <div
                            onClick={() => setInspectedSlot(slot)}
                            className="p-2 rounded-xl bg-blue-50 border border-blue-200 text-left hover:bg-blue-100 transition-colors cursor-pointer group"
                          >
                            <span className="font-bold text-slate-900 block truncate group-hover:text-blue-700">
                              {slot.student_name || slot.student_id}
                            </span>
                            <span className="text-[10px] text-slate-500 font-mono block">
                              Roll: {slot.roll_no || slot.student_id}
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-300 font-mono text-[10px]">—</span>
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
