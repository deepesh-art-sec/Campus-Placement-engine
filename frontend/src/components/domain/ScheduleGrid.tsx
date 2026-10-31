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
    <div className={`corporate-card overflow-hidden shadow-lg ${className}`}>
      {/* Matrix Header */}
      <div className="p-4 bg-[#070D1A] border-b border-[#152445] flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-extrabold text-white flex items-center gap-2">
            <Clock className="w-4 h-4 text-cyan-400" />
            Interview Schedule Matrix
          </h3>
          <p className="text-xs text-slate-400">
            Room allocations and interview time windows across active placement drives
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ClashBadge clashCount={totalClashes} />
          <span className="text-xs text-slate-400 font-mono font-semibold">
            {allocations.length} total scheduled
          </span>
        </div>
      </div>

      {/* Grid container with horizontal scroll */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-xs">
          <thead>
            <tr className="bg-[#070D1A] border-b border-[#152445]">
              <th className="p-3 font-mono font-bold text-slate-400 uppercase tracking-wider w-36 sticky left-0 bg-[#070D1A] z-10 border-r border-[#152445]">
                Time Window
              </th>
              {rooms.map((room) => (
                <th key={room} className="p-3 font-semibold text-slate-200 min-w-[200px] border-r border-[#152445] last:border-r-0">
                  <div className="flex items-center gap-1.5 text-slate-200 font-bold">
                    <MapPin className="w-3.5 h-3.5 text-cyan-400" />
                    <span>{room}</span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#152445]">
            {slots.map((slot) => (
              <tr key={slot} className="hover:bg-white/[0.02] transition-colors">
                {/* Time slot column */}
                <td className="p-3 font-mono text-slate-300 font-semibold sticky left-0 bg-[#0B1326] border-r border-[#152445] z-10 whitespace-nowrap">
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
                      className="p-2 border-r border-[#152445] last:border-r-0 align-top min-w-[200px]"
                    >
                      {matchAllocations.length === 0 ? (
                        <div className="h-14 border border-dashed border-[#16264C] rounded-xl flex items-center justify-center text-[11px] text-slate-500 font-mono bg-[#070D1A]/50">
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
                                    ? "bg-rose-950/90 border-rose-500 text-rose-200 shadow-sm"
                                    : "bg-[#0B1326] border-[#16264C] border-t-2 border-t-cyan-400 text-white hover:border-cyan-400 hover:bg-[#101C38] shadow-sm"
                                } ${onSelectAllocation ? "cursor-pointer" : ""}`}
                              >
                                <div className="flex items-center justify-between gap-1">
                                  <span className="font-extrabold text-white text-[12px] truncate">
                                    {item.studentName}
                                  </span>
                                  {isClashed ? (
                                    <AlertCircle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0 animate-pulse" />
                                  ) : (
                                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                                  )}
                                </div>
                                <div className="text-[10px] font-mono text-cyan-400 font-semibold mt-0.5">
                                  {item.rollNumber}
                                </div>
                                <div className="text-[11px] text-slate-400 truncate mt-0.5 flex items-center gap-1">
                                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
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
