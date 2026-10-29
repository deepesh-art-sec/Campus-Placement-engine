import React, { useState, useEffect, useRef } from "react";
import { api } from "../../api/client";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  FileText,
  Download,
  Eye,
  Sparkles,
  Search,
  Filter,
  CheckCircle2,
  Calendar,
  DollarSign,
  GraduationCap,
  Layers,
  ArrowRight,
  Mail,
  FileCode,
  X,
  Copy,
  Check,
  Upload,
} from "lucide-react";

interface AnnouncementItem {
  index: number;
  filename: string;
  company_name: string;
  label: string;
  format: "EML" | "PDF" | "DOCX" | "TXT" | string;
  file_type_label: string;
  size_bytes: number;
  ctc_lpa: number;
  cgpa_min: number;
  drive_date: string;
  mode: string;
  allowed_branches: string[];
  active_backlogs_max: number;
  rounds_count: number;
  snippet: string;
  download_url: string;
}

interface AnnouncementsLibraryViewProps {
  onNavigateToExtract?: (filename: string) => void;
  onNavigateToDrive?: (driveId: string) => void;
}

export const AnnouncementsLibraryView: React.FC<AnnouncementsLibraryViewProps> = ({
  onNavigateToExtract,
  onNavigateToDrive,
}) => {
  const [announcements, setAnnouncements] = useState<AnnouncementItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Filter & Search State
  const [searchQuery, setSearchQuery] = useState("");
  const [formatFilter, setFormatFilter] = useState<string>("ALL");
  const [sortBy, setSortBy] = useState<"index" | "ctc_desc" | "ctc_asc" | "name">("index");

  // Preview Modal State
  const [previewItem, setPreviewItem] = useState<{ filename: string; text: string; label: string } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [creatingDriveId, setCreatingDriveId] = useState<string | null>(null);

  // Upload Modal State
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleModalDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleModalDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleModalDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setUploadFile(e.dataTransfer.files[0]);
    }
  };

  useEffect(() => {
    fetchAnnouncements();
  }, []);

  const fetchAnnouncements = async () => {
    try {
      setLoading(true);
      const res = await api.get<AnnouncementItem[]>("/api/announcements");
      setAnnouncements(res || []);
    } catch (err: any) {
      setError(err.message || "Failed to load announcements repository.");
    } finally {
      setLoading(false);
    }
  };

  const handleUploadAnnouncement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;

    try {
      setUploading(true);
      setError(null);
      const formData = new FormData();
      formData.append("file", uploadFile);

      const res = await api.post<any>("/api/announcements/upload", formData);
      setSuccess(`Announcement '${res.filename}' ingested and parsed! Extracted ${res.extracted?.company_name || 'criteria'} successfully.`);
      setIsUploadModalOpen(false);
      setUploadFile(null);
      await fetchAnnouncements();
    } catch (err: any) {
      setError(err.message || "Failed to upload and extract announcement.");
    } finally {
      setUploading(false);
    }
  };

  const handleOpenPreview = async (filename: string, label: string) => {
    try {
      setPreviewLoading(true);
      const res = await api.get<any>(`/api/announcements/${filename}`);
      setPreviewItem({
        filename,
        label,
        text: res.full_text || "No preview content available.",
      });
    } catch (err: any) {
      setError(err.message || "Failed to load announcement preview.");
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleCopyText = (text: string) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleInstantCreateDrive = async (filename: string) => {
    try {
      setCreatingDriveId(filename);
      setError(null);
      const res = await api.post<any>(`/api/announcements/${filename}/instant-drive`, {});
      setSuccess(res.message || "Drive created successfully!");
      if (onNavigateToDrive && res.drive_id) {
        setTimeout(() => onNavigateToDrive(res.drive_id), 1200);
      }
    } catch (err: any) {
      setError(err.message || "Failed to create drive from announcement.");
    } finally {
      setCreatingDriveId(null);
    }
  };

  // Filtered & Sorted items
  const filteredItems = announcements
    .filter((item) => {
      const matchesSearch =
        item.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.snippet.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesFormat = formatFilter === "ALL" || item.format === formatFilter;
      return matchesSearch && matchesFormat;
    })
    .sort((a, b) => {
      if (sortBy === "ctc_desc") return b.ctc_lpa - a.ctc_lpa;
      if (sortBy === "ctc_asc") return a.ctc_lpa - b.ctc_lpa;
      if (sortBy === "name") return a.company_name.localeCompare(b.company_name);
      return a.index - b.index;
    });

  const getFormatBadge = (fmt: string) => {
    switch (fmt) {
      case "EML":
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-950/90 text-indigo-300 border border-indigo-700/60 flex items-center gap-1"><Mail className="w-3 h-3" /> EML Email</span>;
      case "PDF":
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-950/90 text-rose-300 border border-rose-700/60 flex items-center gap-1"><FileText className="w-3 h-3" /> PDF Spec</span>;
      case "DOCX":
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-950/90 text-blue-300 border border-blue-700/60 flex items-center gap-1"><FileCode className="w-3 h-3" /> DOCX JD</span>;
      default:
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-950/90 text-emerald-300 border border-emerald-700/60 flex items-center gap-1"><FileText className="w-3 h-3" /> TXT Notice</span>;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-[#0d1527] via-[#101b33] to-[#072421] p-6 sm:p-8 rounded-3xl border border-emerald-500/30 shadow-xl text-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              <Layers className="w-5 h-5" />
            </span>
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 font-mono">
              Institutional Recruitment Corpus
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            25 Real-Format Drive Announcements
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 max-w-2xl leading-relaxed">
            Anonymised company emails, corporate PDF specifications, and official job descriptions received by college placement cells. Download raw files, run deterministic AST extraction, or 1-click instantiate live placement drives.
          </p>
          <div className="pt-2">
            <button
              type="button"
              onClick={() => setIsUploadModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-emerald-950/40 transition-all cursor-pointer"
            >
              <Upload className="w-4 h-4" />
              <span>Upload New Announcement (PDF, DOCX, EML, TXT)</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 shrink-0">
          <div className="bg-[#080e1c]/80 border border-[#1b2b4d] rounded-2xl p-3 text-center">
            <div className="text-xl font-black text-white font-mono">{announcements.length}</div>
            <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Documents</div>
          </div>
          <div className="bg-[#080e1c]/80 border border-[#1b2b4d] rounded-2xl p-3 text-center">
            <div className="text-xl font-black text-emerald-400 font-mono">4 Formats</div>
            <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">EML, PDF, DOCX, TXT</div>
          </div>
          <div className="bg-[#080e1c]/80 border border-[#1b2b4d] rounded-2xl p-3 text-center col-span-2 sm:col-span-1">
            <div className="text-xl font-black text-teal-300 font-mono">100%</div>
            <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Ground Truth Labeled</div>
          </div>
        </div>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {success && <AlertBanner type="success" message={success} onClose={() => setSuccess(null)} />}

      {/* Filter and Search Bar */}
      <div className="bg-[#0d1527] border border-[#1b2b4d] rounded-2xl p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by company or filename..."
            className="w-full pl-10 pr-4 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-semibold text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        {/* Format Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full md:w-auto">
          {["ALL", "EML", "PDF", "DOCX", "TXT"].map((fmt) => (
            <button
              key={fmt}
              type="button"
              onClick={() => setFormatFilter(fmt)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
                formatFilter === fmt
                  ? "bg-gradient-to-r from-blue-700 to-emerald-600 text-white shadow-xs"
                  : "bg-[#080e1c] text-slate-400 hover:text-white border border-[#1b2b4d]"
              }`}
            >
              {fmt === "ALL" ? `All (${announcements.length})` : fmt}
            </button>
          ))}
        </div>

        {/* Sort Select */}
        <div className="flex items-center gap-2 self-end md:self-auto shrink-0">
          <span className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider">Sort:</span>
          <select
            value={sortBy}
            onChange={(e: any) => setSortBy(e.target.value)}
            className="px-3 py-1.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-xs font-semibold text-white focus:outline-none cursor-pointer"
          >
            <option value="index">Corpus Order (#01 - #25)</option>
            <option value="ctc_desc">Highest CTC (LPA)</option>
            <option value="ctc_asc">Lowest CTC (LPA)</option>
            <option value="name">Company Name (A-Z)</option>
          </select>
        </div>
      </div>

      {/* Grid of Announcements */}
      {loading ? (
        <div className="p-12 text-center text-slate-400 text-sm">
          Loading 25 real-format drive announcements...
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="p-12 bg-[#0d1527] border border-[#1b2b4d] rounded-2xl text-center text-slate-400 text-sm">
          No announcements matched your search query.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredItems.map((item) => (
            <div
              key={item.filename}
              className="bg-[#0d1527] border border-[#1b2b4d] hover:border-emerald-500/50 rounded-2xl p-5 shadow-sm transition-all flex flex-col justify-between space-y-4 text-slate-100 group"
            >
              <div className="space-y-3">
                {/* Header Line */}
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-mono font-bold text-slate-500">#{String(item.index).padStart(2, "0")}</span>
                    <h3 className="font-black text-white text-base group-hover:text-emerald-300 transition-colors">
                      {item.company_name}
                    </h3>
                  </div>
                  {getFormatBadge(item.format)}
                </div>

                {/* Subtitle / File type */}
                <div className="text-[11px] text-slate-400 font-medium truncate" title={item.filename}>
                  {item.filename} • {(item.size_bytes / 1024).toFixed(1)} KB
                </div>

                {/* Key Ground Truth Criteria Grid */}
                <div className="grid grid-cols-2 gap-2 bg-[#080e1c] p-3 rounded-xl border border-[#172642] text-xs">
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase font-bold block">Package (CTC)</span>
                    <span className="text-emerald-400 font-mono font-bold">{item.ctc_lpa} LPA</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase font-bold block">Cut-Off CGPA</span>
                    <span className="text-white font-mono font-bold">{item.cgpa_min} / 10.0</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase font-bold block">Drive Date</span>
                    <span className="text-slate-300 font-mono text-[11px]">{item.drive_date}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase font-bold block">Selection Rounds</span>
                    <span className="text-teal-300 font-mono font-bold">{item.rounds_count} Rounds</span>
                  </div>
                </div>

                {/* Snippet Preview */}
                <p className="text-[11px] text-slate-400 line-clamp-3 leading-relaxed italic bg-[#090f1d] p-2.5 rounded-lg border border-[#14223d]">
                  "{item.snippet}"
                </p>
              </div>

              {/* Actions Footer */}
              <div className="space-y-2 pt-2 border-t border-[#172642]">
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => handleOpenPreview(item.filename, item.label)}
                    className="flex items-center justify-center gap-1.5 py-2 px-3 bg-[#111d38] hover:bg-[#18284d] text-slate-200 hover:text-white border border-[#1e3258] rounded-xl text-xs font-bold transition-all cursor-pointer"
                    title="View raw document content"
                  >
                    <Eye className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Preview</span>
                  </button>

                  <a
                    href={item.download_url}
                    download={item.filename}
                    className="flex items-center justify-center gap-1.5 py-2 px-3 bg-[#111d38] hover:bg-[#18284d] text-slate-200 hover:text-white border border-[#1e3258] rounded-xl text-xs font-bold transition-all"
                    title="Download original raw document file"
                  >
                    <Download className="w-3.5 h-3.5 text-blue-400" />
                    <span>Download</span>
                  </a>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => onNavigateToExtract && onNavigateToExtract(item.filename)}
                    className="flex items-center justify-center gap-1 py-2 px-2.5 bg-gradient-to-r from-blue-700 to-teal-700 hover:from-blue-600 hover:to-teal-600 text-white rounded-xl text-[11px] font-bold shadow-xs transition-all cursor-pointer"
                    title="Run offline AST requirement extraction"
                  >
                    <Sparkles className="w-3 h-3" />
                    <span>Extract NLP</span>
                  </button>

                  <button
                    type="button"
                    disabled={creatingDriveId === item.filename}
                    onClick={() => handleInstantCreateDrive(item.filename)}
                    className="flex items-center justify-center gap-1 py-2 px-2.5 bg-gradient-to-r from-teal-700 to-emerald-700 hover:from-teal-600 hover:to-emerald-600 text-white rounded-xl text-[11px] font-bold shadow-xs transition-all cursor-pointer disabled:opacity-50"
                    title="1-Click create live recruitment drive from this document"
                  >
                    <CheckCircle2 className="w-3 h-3" />
                    <span>{creatingDriveId === item.filename ? "Creating..." : "Create Drive"}</span>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Document Raw Preview Modal */}
      {previewItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#0d1527] border border-[#1b2b4d] rounded-3xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden text-slate-100">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-[#1b2b4d] flex items-center justify-between bg-[#080e1c]">
              <div>
                <h3 className="text-base font-black text-white">{previewItem.label}</h3>
                <span className="text-xs text-slate-400 font-mono">{previewItem.filename}</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleCopyText(previewItem.text)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-[#111d38] hover:bg-[#18284d] text-slate-200 text-xs font-bold rounded-xl border border-[#1b2b4d] transition-all cursor-pointer"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
                  <span>{copied ? "Copied" : "Copy Content"}</span>
                </button>
                <a
                  href={`/api/announcements/${previewItem.filename}/download`}
                  download={previewItem.filename}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-blue-600 to-emerald-600 text-white text-xs font-bold rounded-xl transition-all"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download Original</span>
                </a>
                <button
                  type="button"
                  onClick={() => setPreviewItem(null)}
                  className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto flex-1 font-mono text-xs text-slate-300 leading-relaxed bg-[#050914] whitespace-pre-wrap select-text">
              {previewItem.text}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-[#1b2b4d] bg-[#080e1c] flex items-center justify-between text-xs text-slate-400">
              <span>Authentic anonymised placement announcement received by institutional cell</span>
              <button
                type="button"
                onClick={() => {
                  const fname = previewItem.filename;
                  setPreviewItem(null);
                  if (onNavigateToExtract) onNavigateToExtract(fname);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl transition-all cursor-pointer"
              >
                <span>Extract with NLP</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Announcement Modal */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#0d1527] border border-[#1b2b4d] rounded-3xl w-full max-w-xl shadow-2xl overflow-hidden text-slate-100">
            <div className="px-6 py-4 border-b border-[#1b2b4d] flex items-center justify-between bg-[#080e1c]">
              <div className="flex items-center gap-2.5">
                <span className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  <Upload className="w-4 h-4" />
                </span>
                <div>
                  <h3 className="text-base font-black text-white">Upload New Drive Announcement</h3>
                  <p className="text-[11px] text-slate-400">Supported formats: PDF, DOCX, EML, and TXT</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsUploadModalOpen(false);
                  setUploadFile(null);
                }}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUploadAnnouncement} className="p-6 space-y-5">
              <div
                onDragOver={handleModalDragOver}
                onDragLeave={handleModalDragLeave}
                onDrop={handleModalDrop}
                onClick={() => {
                  if (fileInputRef.current) {
                    fileInputRef.current.value = "";
                    fileInputRef.current.click();
                  }
                }}
                className={`border-2 border-dashed rounded-2xl p-6 text-center space-y-3 transition-all cursor-pointer ${
                  isDragging
                    ? "border-emerald-400 bg-emerald-950/40 ring-4 ring-emerald-500/20 scale-[1.01]"
                    : "border-[#1e3258] hover:border-emerald-500/50 bg-[#080e1c]"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  required={!uploadFile}
                  accept=".pdf,.docx,.eml,.txt"
                  onChange={(e) => setUploadFile(e.target.files ? e.target.files[0] : null)}
                  className="hidden"
                />
                {uploadFile ? (
                  <div
                    className="flex items-center justify-between p-3.5 bg-emerald-950/60 border border-emerald-500/40 rounded-xl text-left"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <FileText className="w-5 h-5 text-emerald-400 shrink-0" />
                      <div className="min-w-0">
                        <div className="text-xs font-bold text-white truncate max-w-xs">{uploadFile.name}</div>
                        <div className="text-[10px] text-emerald-400 font-mono">{(uploadFile.size / 1024).toFixed(1)} KB • Ready to upload</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => {
                          if (fileInputRef.current) {
                            fileInputRef.current.value = "";
                            fileInputRef.current.click();
                          }
                        }}
                        className="px-2.5 py-1 text-xs font-bold text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors cursor-pointer"
                      >
                        Change File
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setUploadFile(null);
                          if (fileInputRef.current) fileInputRef.current.value = "";
                        }}
                        className="p-1 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-rose-950/30 transition-colors cursor-pointer"
                        title="Remove file"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <Upload className="w-8 h-8 text-emerald-400 mx-auto" />
                    <div className="text-xs text-slate-300">
                      <span className="font-bold text-emerald-400 hover:underline">
                        {isDragging ? "Drop your file here" : "Click to select file"}
                      </span>{" "}
                      or drag and drop document here
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono">
                      PDF specs, DOCX JDs, EML emails, or TXT notices
                    </div>
                  </>
                )}
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setIsUploadModalOpen(false);
                    setUploadFile(null);
                  }}
                  className="px-4 py-2 text-xs font-bold text-slate-400 hover:text-white rounded-xl transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!uploadFile || uploading}
                  className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs rounded-xl shadow-md transition-all cursor-pointer disabled:opacity-50"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>{uploading ? "Ingesting & Parsing..." : "Upload & Parse Document"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
