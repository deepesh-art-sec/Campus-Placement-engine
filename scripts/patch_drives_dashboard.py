file_path = "frontend/src/views/officer/DrivesDashboard.tsx"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = '''        {/* Card 3: Unresolved Clashes */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs relative overflow-hidden group hover:border-purple-300 transition-all flex flex-col justify-between min-h-[140px]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-purple-500" />
          <div className="flex items-center justify-between text-purple-600">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Clash Status
            </span>
            <ShieldCheck className="w-4 h-4 text-purple-500" />
          </div>
          <div className="my-1">
            <div className="text-2xl font-black text-slate-900 tracking-tight">
              {metrics ? metrics.unresolved_clashes : 0}
            </div>
            <div className="text-[11px] text-slate-500 font-medium">Unresolved Clashes</div>
          </div>
          <span className="text-[10px] text-emerald-600 font-bold block flex items-center gap-1">
            <CheckCircle className="w-3 h-3 text-emerald-500" />
            0 Clashes Verified
          </span>
        </div>'''

replacement = '''        {/* Card 3: Unresolved Clashes */}
        <div
          onClick={() => onNavigateTab("schedule")}
          className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs relative overflow-hidden group hover:border-purple-300 transition-all flex flex-col justify-between min-h-[140px] cursor-pointer"
        >
          <div className="absolute top-0 left-0 right-0 h-1 bg-purple-500" />
          <div className="flex items-center justify-between text-purple-600">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Clash Status
            </span>
            <ShieldCheck className="w-4 h-4 text-purple-500" />
          </div>
          <div className="my-1">
            <div className="text-2xl font-black text-slate-900 tracking-tight">
              {metrics ? metrics.unresolved_clashes : 0}
            </div>
            <div className="text-[11px] text-slate-500 font-medium">Unresolved Clashes</div>
          </div>
          {metrics && metrics.unresolved_clashes > 0 ? (
            <span className="text-[10px] text-amber-600 font-bold block flex items-center gap-1">
              <AlertTriangle className="w-3 h-3 text-amber-500" />
              {metrics.unresolved_clashes} Clashes Requiring Action
            </span>
          ) : (
            <span className="text-[10px] text-emerald-600 font-bold block flex items-center gap-1">
              <CheckCircle className="w-3 h-3 text-emerald-500" />
              0 Clashes Verified
            </span>
          )}
        </div>'''

assert target in content, "target not found in DrivesDashboard.tsx"
content = content.replace(target, replacement, 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("DrivesDashboard.tsx successfully patched!")
