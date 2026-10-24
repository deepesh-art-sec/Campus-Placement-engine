import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Badge } from "../../components/common/Badge";
import { Briefcase, Calendar, Clock, Users, Download } from "lucide-react";

export const RecruiterPortal: React.FC = () => {
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRecruiterData = async () => {
      try {
        setLoading(true);
        const res = await api.get<any>("/api/recruiter/my-drive");
        setData(res);
      } catch (err: any) {
        setError(err.message || "Failed to load corporate recruitment dashboard.");
      } finally {
        setLoading(false);
      }
    };
    fetchRecruiterData();
  }, []);

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-400 text-sm">
        Loading corporate partner dashboard...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 bg-[#0d1527] border border-[#1b2b4d] rounded-3xl max-w-lg mx-auto text-center space-y-4 text-white">
        <Briefcase className="w-12 h-12 text-slate-500 mx-auto" />
        <h3 className="text-base font-bold text-white">Recruiter Portal Access Restricted</h3>
        <p className="text-xs text-slate-400">{error || "No authorized drives found for your corporate account."}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div className="bg-[#0d1527] p-6 rounded-3xl border border-[#1b2b4d] shadow-md flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-black text-white tracking-tight">{data.company_name}</h1>
            <Badge variant="brand" size="sm">Recruiter Read-Only</Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-medium">
            Campus Drive Date: {new Date(data.drive_date).toLocaleDateString()} | Total Shortlisted: {data.total_shortlisted}
          </p>
        </div>

        <button
          onClick={() => window.print()}
          className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 via-teal-600 to-emerald-600 hover:from-blue-500 hover:via-teal-500 hover:to-emerald-500 text-white text-xs font-bold rounded-xl border border-emerald-400/30 shadow-md shadow-emerald-900/30 transition-all self-start sm:self-center cursor-pointer"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Print Shortlist</span>
        </button>
      </div>

      {/* Candidate Shortlist */}
      <div className="bg-[#0d1527] rounded-3xl border border-[#1b2b4d] shadow-md overflow-hidden">
        <div className="p-4 bg-[#080e1c] border-b border-[#1b2b4d] flex items-center justify-between">
          <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Users className="w-4 h-4 text-emerald-400" />
            Approved Candidate Shortlist ({data.shortlist?.length || 0})
          </span>
          <Badge variant="success" size="sm">Officer Approved</Badge>
        </div>

        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-[#080e1c] border-b border-[#1b2b4d] text-slate-400 font-bold uppercase">
              <th className="px-6 py-3">Roll No</th>
              <th className="px-6 py-3">Candidate Name</th>
              <th className="px-6 py-3">Branch</th>
              <th className="px-6 py-3">CGPA</th>
              <th className="px-6 py-3">10th %</th>
              <th className="px-6 py-3">12th %</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1b2b4d]">
            {data.shortlist?.map((s: any, idx: number) => (
              <tr key={idx} className="hover:bg-[#111d38] transition-colors">
                <td className="px-6 py-3 font-mono font-bold text-emerald-400">{s.roll_no}</td>
                <td className="px-6 py-3 font-semibold text-white">{s.name}</td>
                <td className="px-6 py-3 text-slate-300">{s.branch}</td>
                <td className="px-6 py-3 font-mono font-bold text-emerald-300">{s.cgpa.toFixed(2)}</td>
                <td className="px-6 py-3 text-slate-300">{s.tenth_percentage}%</td>
                <td className="px-6 py-3 text-slate-300">{s.twelfth_percentage ? `${s.twelfth_percentage}%` : "N/A"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Recruiter Schedule */}
      <div className="bg-[#0d1527] rounded-3xl border border-[#1b2b4d] shadow-md overflow-hidden">
        <div className="p-4 bg-[#080e1c] border-b border-[#1b2b4d] flex items-center justify-between">
          <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Calendar className="w-4 h-4 text-emerald-400" />
            Interview Slot Timetable
          </span>
          <Badge variant="brand" size="sm">Live Day Grid</Badge>
        </div>

        <div className="divide-y divide-[#1b2b4d] text-xs">
          {data.schedule?.map((sl: any, idx: number) => (
            <div key={idx} className="p-4 flex items-center justify-between hover:bg-[#111d38] transition-colors">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1.5 font-mono font-bold text-emerald-300 bg-[#111d38] border border-[#1b2b4d] px-2.5 py-1 rounded-lg">
                  <Clock className="w-3.5 h-3.5 text-emerald-400" />
                  <span>{sl.slot_time}</span>
                </div>
                <div>
                  <span className="font-bold text-white block">{sl.candidate_name}</span>
                  <span className="text-[11px] font-mono text-slate-400">{sl.candidate_roll_no}</span>
                </div>
              </div>

              <div className="text-right">
                <span className="font-semibold text-emerald-300 block">{sl.venue}</span>
                <span className="text-[11px] text-slate-400">{sl.panel}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
