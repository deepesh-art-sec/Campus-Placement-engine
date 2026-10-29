file_path = "frontend/src/views/officer/ScheduleBoardView.tsx"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Update detectClashes
detect_target = '''  const detectClashes = (items: ScheduleSlot[]) => {
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
    setClashCount(collisions);
  };'''

detect_replacement = '''  const detectClashes = (items: ScheduleSlot[]) => {
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
    const crossDriveClashes = items.filter((it: any) => it.has_clash).length;
    setClashCount(collisions + crossDriveClashes);
  };'''

assert detect_target in content, "detectClashes target not found"
content = content.replace(detect_target, detect_replacement, 1)

# Update slot rendering with clash styling
slot_render_target = '''                        {slot ? (
                          <div
                            onClick={() => setSelectedSlot(slot)}
                            className="bg-[#111e38]/90 hover:bg-[#16274a] border border-[#1e3258] hover:border-emerald-500/60 rounded-xl p-2.5 shadow-sm hover:shadow-emerald-950/30 cursor-pointer transition-all space-y-1.5 group"
                          >
                            <span className="text-[11.5px] font-bold text-slate-100 block truncate group-hover:text-emerald-300 transition-colors">
                              {slot.student_name}
                            </span>
                            <span className="text-[10.5px] font-mono font-semibold text-cyan-400 block truncate">
                              {slot.roll_no}
                            </span>
                            <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-[#1a2c50]">
                              <span className="truncate">{slot.round_name}</span>
                              <span className="font-bold text-emerald-300 shrink-0 bg-emerald-950/80 border border-emerald-500/30 px-1.5 py-0.5 rounded text-[9.5px]">
                                OK
                              </span>
                            </div>
                          </div>
                        ) : ('''

slot_render_replacement = '''                        {slot ? (
                          <div
                            onClick={() => setSelectedSlot(slot)}
                            className={`${
                              (slot as any).has_clash
                                ? "bg-rose-950/80 hover:bg-rose-900 border border-rose-500/80"
                                : "bg-[#111e38]/90 hover:bg-[#16274a] border border-[#1e3258] hover:border-emerald-500/60"
                            } rounded-xl p-2.5 shadow-sm hover:shadow-emerald-950/30 cursor-pointer transition-all space-y-1.5 group`}
                            title={(slot as any).clash_detail || undefined}
                          >
                            <span className="text-[11.5px] font-bold text-slate-100 block truncate group-hover:text-emerald-300 transition-colors">
                              {slot.student_name}
                            </span>
                            <span className="text-[10.5px] font-mono font-semibold text-cyan-400 block truncate">
                              {slot.roll_no}
                            </span>
                            <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-[#1a2c50]">
                              <span className="truncate">{slot.round_name}</span>
                              {(slot as any).has_clash ? (
                                <span className="font-bold text-rose-300 shrink-0 bg-rose-950/80 border border-rose-500/50 px-1.5 py-0.5 rounded text-[9.5px]">
                                  CLASH
                                </span>
                              ) : (
                                <span className="font-bold text-emerald-300 shrink-0 bg-emerald-950/80 border border-emerald-500/30 px-1.5 py-0.5 rounded text-[9.5px]">
                                  OK
                                </span>
                              )}
                            </div>
                          </div>
                        ) : ('''

assert slot_render_target in content, "slot_render_target not found"
content = content.replace(slot_render_target, slot_render_replacement, 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("ScheduleBoardView.tsx successfully patched!")
