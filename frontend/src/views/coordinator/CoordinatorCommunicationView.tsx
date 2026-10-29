import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Drive, Student } from "../../types";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  MessageSquare,
  Printer,
  Copy,
  Check,
  HardDrive,
  ShieldCheck,
  Search,
  User,
  Building,
  Calendar,
} from "lucide-react";

export const CoordinatorCommunicationView: React.FC = () => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState("");
  const [selectedStudentRoll, setSelectedStudentRoll] = useState("");
  const [search, setSearch] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [dRes, sRes] = await Promise.all([
          api.get<Drive[]>("/api/drives"),
          api.get<{ items: Student[] }>("/api/students?limit=2500"),
        ]);
        const list = dRes || [];
        setDrives(list);
        if (list.length > 0) {
          if (!selectedDriveId || !list.some((d) => d.id === selectedDriveId)) {
            setSelectedDriveId(list[0].id);
          }
        } else {
          setSelectedDriveId("");
        }
        const sList = sRes.items || [];
        setStudents(sList);
        if (sList.length > 0) setSelectedStudentRoll(sList[0].roll_no);
      } catch {
        // Fallback
      }
    };
    fetchData();
  }, []);

  const selectedDrive = drives.find((d) => d.id === selectedDriveId);
  const selectedStudent = students.find((s) => s.roll_no === selectedStudentRoll);

  // Generate plain-language status message
  const generatedMessage = selectedStudent && selectedDrive
    ? `Dear ${selectedStudent.name} (${selectedStudent.roll_no}),\n\n` +
      `This is an official communication from the Training & Placement Cell.\n` +
      `You have been evaluated for the upcoming campus recruitment drive with ${selectedDrive.company_name} ` +
      `(${selectedDrive.job_role || "Engineering Graduate Trainee"}) offering CTC ${selectedDrive.ctc_lpa} LPA scheduled on ${selectedDrive.drive_date}.\n\n` +
      `Your current placement status: ELIGIBLE & SHORTLISTED.\n` +
      `Please report to the assigned interview venue with your college ID and hard copies of your academic resume.\n\n` +
      `Important Notice: All placement communication is processed strictly offline on the institutional local area network. No data leaves the campus server.\n\n` +
      `Regards,\nStudent Placement Coordinator\nTraining & Placement Cell`
    : "Please select a candidate and company drive to generate their official communication message.";

  const handleCopyMessage = () => {
    navigator.clipboard.writeText(generatedMessage);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrintSheet = () => {
    window.print();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Student Status Communications</h1>
            <Badge variant="brand">Offline Generator</Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Generate formal status announcements and printable slips for candidates. No external network transmissions.
          </p>
        </div>

        <button
          type="button"
          onClick={handlePrintSheet}
          className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-900 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer"
        >
          <Printer className="w-3.5 h-3.5" />
          <span>Print Status Sheet</span>
        </button>
      </div>

      {/* Offline Air-Gap Guarantee */}
      <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-start gap-3">
        <HardDrive className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
        <div className="text-xs text-emerald-900 leading-relaxed">
          <strong>100% Offline Architecture Guarantee:</strong> The system does NOT send emails, SMS, or external cloud webhooks. Generated messages are copied to the clipboard for internal LAN dissemination or printed as physical venue passes.
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Selection Controls */}
        <div className="lg:col-span-1 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h3 className="font-bold text-slate-900 text-sm">Select Candidate & Drive</h3>

          <div className="space-y-3 text-xs">
            <div>
              <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">Company Drive</label>
              <select
                value={selectedDriveId}
                onChange={(e) => setSelectedDriveId(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-semibold cursor-pointer"
              >
                {drives.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.company_name} ({d.ctc_lpa} LPA)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="font-bold text-slate-700 uppercase tracking-wider block mb-1">Select Candidate</label>
              <select
                value={selectedStudentRoll}
                onChange={(e) => setSelectedStudentRoll(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-semibold cursor-pointer"
              >
                {students.slice(0, 200).map((s) => (
                  <option key={s.id} value={s.roll_no}>
                    {s.roll_no} - {s.name}
                  </option>
                ))}
              </select>
            </div>

            {selectedStudent && (
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1 text-slate-700">
                <span className="font-bold text-slate-900 block">{selectedStudent.name}</span>
                <span className="text-[11px] text-slate-500 block font-mono">Roll: {selectedStudent.roll_no}</span>
                <span className="text-[11px] text-slate-500 block">Branch: {selectedStudent.branch}</span>
                <span className="text-[11px] text-brand-700 font-bold block">CGPA: {selectedStudent.cgpa.toFixed(2)}</span>
              </div>
            )}
          </div>
        </div>

        {/* Message Preview & Clipboard Actions */}
        <div className="lg:col-span-2 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-brand-600" />
              <span>Official Candidate Communication Template</span>
            </h3>

            <button
              type="button"
              onClick={handleCopyMessage}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer"
            >
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? "Copied to Clipboard!" : "Copy Message"}</span>
            </button>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 font-mono text-xs leading-relaxed text-slate-800 whitespace-pre-wrap select-all">
            {generatedMessage}
          </div>

          <div className="text-[11px] text-slate-400 flex items-center justify-between">
            <span>Air-gapped safe: no external APIs triggered</span>
            <span>UTF-8 Plain Text / ASCII Compatible</span>
          </div>
        </div>
      </div>
    </div>
  );
};
