import React, { useState, useRef } from "react";
import { UploadCloud, FileText, CheckCircle2, ShieldCheck, X } from "lucide-react";

export interface FileDropzoneProps {
  accept?: string;
  maxSizeMB?: number;
  onFileSelect?: (file: File) => void;
  onFilesSelected?: (files: File[]) => void;
  label?: string;
  helperText?: string;
  disabled?: boolean;
}

export const FileDropzone: React.FC<FileDropzoneProps> = ({
  accept = ".csv,.xlsx,.pdf,.docx,.eml,.txt",
  maxSizeMB = 25,
  onFileSelect,
  onFilesSelected,
  label = "Upload or drag & drop file here",
  helperText = "Supported formats: CSV, XLSX, PDF, DOCX, EML, TXT",
  disabled = false,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      onFileSelect?.(file);
      onFilesSelected?.(Array.from(e.dataTransfer.files));
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile(file);
      onFileSelect?.(file);
      onFilesSelected?.(Array.from(e.target.files));
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`border-2 border-dashed rounded-2xl p-6 sm:p-8 text-center transition-all ${
        isDragging
          ? "border-emerald-400 bg-emerald-950/20 shadow-lg shadow-emerald-950/40"
          : "border-[#1e3258] hover:border-emerald-500/50 bg-[#080e1c]"
      } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
      onClick={() => !disabled && fileInputRef.current?.click()}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleChange}
        disabled={disabled}
        className="hidden"
      />

      <div className="flex flex-col items-center justify-center space-y-3">
        <div className="w-12 h-12 rounded-2xl bg-[#111d38] border border-[#1e3258] flex items-center justify-center text-emerald-400 shadow-inner">
          <UploadCloud className="w-6 h-6" />
        </div>

        <div>
          <h4 className="text-sm font-black text-white tracking-tight">{label}</h4>
          <p className="text-xs text-slate-400 mt-0.5">{helperText}</p>
        </div>

        <div className="flex items-center gap-2 text-[11px] font-mono text-emerald-400 bg-emerald-950/40 px-3 py-1 rounded-full border border-emerald-900/40">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Local Memory Stream • Zero Server Cloud Sync</span>
        </div>

        {selectedFile && (
          <div className="flex items-center gap-2 p-2 bg-[#0d1527] border border-[#1e3258] rounded-xl text-xs text-slate-200 mt-2">
            <FileText className="w-4 h-4 text-emerald-400" />
            <span className="font-mono truncate max-w-xs">{selectedFile.name}</span>
            <span className="text-[10px] text-slate-400">
              ({(selectedFile.size / 1024).toFixed(1)} KB)
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
