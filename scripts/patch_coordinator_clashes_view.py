file_path = "frontend/src/views/coordinator/CoordinatorClashesView.tsx"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add RefreshCw to imports
import_target = '''  Clock,
  ArrowRight,'''

import_replacement = '''  Clock,
  ArrowRight,
  RefreshCw,'''

assert import_target in content, "import target not found"
content = content.replace(import_target, import_replacement, 1)

# Replace mock baseline clashes
mock_target = '''  // Mock baseline clashes if none currently colliding in database
  useEffect(() => {
    setClashes([
      {
        id: "clash_1",
        student_roll: "BT210005",
        student_name: "Rahul Verma",
        branch: "Computer Science and Engineering",
        drive_a_id: "drv_1",
        drive_a_company: "Google",
        drive_a_time: "10:00 AM - 10:30 AM",
        drive_b_id: "drv_2",
        drive_b_company: "Microsoft",
        drive_b_time: "10:15 AM - 10:45 AM",
        status: "unresolved",
      },
      {
        id: "clash_2",
        student_roll: "BT210012",
        student_name: "Pooja Sharma",
        branch: "Information Technology",
        drive_a_id: "drv_3",
        drive_a_company: "Amazon",
        drive_a_time: "11:30 AM - 12:00 PM",
        drive_b_id: "drv_4",
        drive_b_company: "Goldman Sachs",
        drive_b_time: "11:45 AM - 12:15 PM",
        status: "unresolved",
      },
    ]);
  }, []);'''

fetch_replacement = '''  const fetchClashes = async () => {
    try {
      setLoading(true);
      const res = await api.get<ClashItem[]>("/api/coordinator/clashes");
      setClashes(res || []);
    } catch {
      setClashes([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClashes();
  }, []);'''

assert mock_target in content, "mock target not found"
content = content.replace(mock_target, fetch_replacement, 1)

# Update header with refresh button and dynamic badge
header_target = '''      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Student Clash Centre</h1>
            <Badge variant="warning">{clashes.filter((c) => c.status === "unresolved").length} Overlapping Windows</Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Detect students shortlisted by two companies with overlapping interview windows. Record candidate stated preferences and notify the Officer.
          </p>
        </div>
      </div>'''

header_replacement = '''      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Student Clash Centre</h1>
            <Badge variant={clashes.filter((c) => c.status === "unresolved").length === 0 ? "success" : "warning"}>
              {clashes.filter((c) => c.status === "unresolved").length === 0
                ? "0 Clashes Active"
                : `${clashes.filter((c) => c.status === "unresolved").length} Overlapping Windows`}
            </Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Detect students shortlisted by two companies with overlapping interview windows. Record candidate stated preferences and notify the Officer.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={fetchClashes}
            className="p-2 text-slate-600 hover:text-slate-900 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 shadow-2xs transition-all cursor-pointer"
            title="Refresh clash detections"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-purple-600" : ""}`} />
          </button>
        </div>
      </div>'''

assert header_target in content, "header target not found"
content = content.replace(header_target, header_replacement, 1)

# Update clashes list to include loading & empty state
list_target = '''      {/* Clashes List */}
      <div className="space-y-4">
        {clashes.map((c) => ('''

list_replacement = '''      {/* Clashes List */}
      <div className="space-y-4">
        {loading ? (
          <div className="p-8 text-center bg-white rounded-2xl border border-slate-200 shadow-xs flex items-center justify-center gap-2 text-slate-500 text-xs">
            <RefreshCw className="w-4 h-4 animate-spin text-purple-600" />
            <span>Scanning published schedules for candidate conflicts...</span>
          </div>
        ) : clashes.length === 0 ? (
          <div className="p-8 text-center bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col items-center justify-center">
            <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mb-3">
              <CheckCircle className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-800">Zero Schedule Clashes Detected</h3>
            <p className="text-xs text-slate-500 max-w-md mt-1">
              All published drive slots are fully coordinated and non-overlapping. No student is currently double-booked.
            </p>
          </div>
        ) : (
          clashes.map((c) => ('''

assert list_target in content, "list target not found"
content = content.replace(list_target, list_replacement, 1)

# Close parentheses of conditional
footer_target = '''            </div>
          </div>
        ))}
      </div>'''

footer_replacement = '''            </div>
          </div>
        )))}
      </div>'''

assert footer_target in content, "footer target not found"
content = content.replace(footer_target, footer_replacement, 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("CoordinatorClashesView.tsx successfully patched!")
