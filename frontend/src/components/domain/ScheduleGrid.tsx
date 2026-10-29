import React from "react";
import { Clock, MapPin, AlertCircle, User, CheckCircle2 } from "lucide-react";
import { ClashBadge } from "./ClashBadge";

export interface ScheduleAllocation {
  id: string;
  studentName: string;
  rollNumber: string;
  companyName: string;
  room: string;
  timeSlot: string; // e.g. "09:00 - 09:30"
  status?: "scheduled" | "in_progress" | "completed" | "absent";
  isClash?: boolean;
}

interface ScheduleGridProps {
  slots?: string[];
  rooms?: string[];
  allocations: ScheduleAllocation[];
  onSelectAllocation?: (allocation: ScheduleAllocation) => void;
  className?: string;
}

const DEFAULT_SLOTS = [
  "09:00 - 09:45",
  "09:45 - 10:30",
  "10:45 - 11:30",
  "11:30 - 12:15",
  "13:30 - 14:15",
  "14:15 - 15:00",
  "15:15 - 16:00",
];

const DEFAULT_ROOMS = ["Interview Lab 101", "Lab 102", "Conference Room A", "Boardroom B"];

export const ScheduleGrid: React.FC<ScheduleGridProps> = ({
  slots = DEFAULT_SLOTS,
  rooms = DEFAULT_ROOMS,
  allocations,
  onSelectAllocation,
  className = "",
}) => {
  // Check for clashes: student scheduled in >1 room at same time slot
  const slotStudentCount: Record<string, string[]> = {};
  allocations.forEach((a) => {
    const key = `${a.timeSlot}_${a.rollNumber}`;
    slotStudentCount[key] = slotStudentCount[key] || [];
    slotStudentCount[key].push(a.id);
  });

  const totalClashes = Object.values(slotStudentCount).filter((ids) => ids.length > 1).length;

  return (
    <div className={`bg-[#0d1527] border border-[#1e3258] rounded-2xl overflow-hidden shadow-xl ${className}`}>
      {/* Matrix Header */}
      <div className="p-4 bg-[#080e1c] border-b border-[#1e3258] flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Clock className="w-4 h-4 text-emerald-400" />
            Interview Schedule Matrix
          </h3>
          <p className="text-xs text-slate-400">
            Room allocations and interview time windows across active placement drives
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ClashBadge clashCount={totalClashes} />
          <span className="text-xs text-slate-400 font-mono">
            {allocations.length} total scheduled
          </span>
        </div>
      </div>

      {/* Grid container with horizontal scroll */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-xs">
          <thead>
            <tr className="bg-[#0a1224] border-b border-[#1e3258]">
              <th className="p-3 font-mono font-bold text-slate-400 uppercase tracking-wider w-36 sticky left-0 bg-[#0a1224] z-10 border-r border-[#1e3258]">
                Time Window
              </th>
              {rooms.map((room) => (
                <th key={room} className="p-3 font-semibold text-slate-200 min-w-[200px] border-r border-[#1e3258] last:border-r-0">
                  <div className="flex items-center gap-1.5 text-white">
                    <MapPin className="w-3.5 h-3.5 text-cyan-400" />
                    <span>{room}</span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1e3258]/60">
            {slots.map((slot) => (
              <tr key={slot} className="hover:bg-[#0f1b33]/40 transition-colors">
                {/* Time slot column */}
                <td className="p-3 font-mono text-slate-300 font-semibold sticky left-0 bg-[#0d1527] border-r border-[#1e3258] z-10 whitespace-nowrap">
                  {slot}
                </td>

                {/* Rooms columns */}
                {rooms.map((room) => {
                  const matchAllocations = allocations.filter(
                    (a) => a.timeSlot === slot && a.room === room
                  );

                  return (
                    <td
                      key={room}
                      className="p-2 border-r border-[#1e3258] last:border-r-0 align-top min-w-[200px]"
                    >
                      {matchAllocations.length === 0 ? (
                        <div className="h-14 border border-dashed border-[#1e3258]/50 rounded-xl flex items-center justify-center text-[11px] text-slate-600 font-mono">
                          Vacant
                        </div>
                      ) : (
                        <div className="space-y-1.5">
                          {matchAllocations.map((item) => {
                            const isClashed =
                              item.isClash ||
                              (slotStudentCount[`${item.timeSlot}_${item.rollNumber}`]?.length || 0) > 1;

                            return (
                              <div
                                key={item.id}
                                onClick={() => onSelectAllocation?.(item)}
                                className={`p-2 rounded-xl border transition-all text-left ${
                                  isClashed
                                    ? "bg-rose-950/40 border-rose-500/70 text-rose-200 shadow-sm shadow-rose-950"
                                    : "bg-[#111d38] border-[#223a66] text-slate-200 hover:border-emerald-500/50 hover:bg-[#16274b]"
                                } ${onSelectAllocation ? "cursor-pointer" : ""}`}
                              >
                                <div className="flex items-center justify-between gap-1">
                                  <span className="font-bold text-white text-[12px] truncate">
                                    {item.studentName}
                                  </span>
                                  {isClashed ? (
                                    <AlertCircle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0 animate-pulse" />
                                  ) : (
                                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                                  )}
                                </div>
                                <div className="text-[10px] font-mono text-cyan-400 mt-0.5">
                                  {item.rollNumber}
                                </div>
                                <div className="text-[11px] text-slate-400 truncate mt-0.5 flex items-center gap-1">
                                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                                  <span>{item.companyName}</span>
                                </div>
                              </div>
                            );
                          })}
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
  );
};
