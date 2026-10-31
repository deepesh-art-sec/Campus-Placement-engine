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
          ? "border-blue-500 bg-blue-50/50 shadow-md"
          : "border-slate-300 hover:border-blue-500 bg-slate-50 hover:bg-blue-50/20"
      } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
      onClick={() => {
        if (!disabled && fileInputRef.current) {
          fileInputRef.current.value = "";
          fileInputRef.current.click();
        }
      }}
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
        <div className="w-12 h-12 rounded-2xl bg-white border border-slate-200 flex items-center justify-center text-blue-600 shadow-sm">
          <UploadCloud className="w-6 h-6" />
        </div>

        <div>
          <h4 className="text-sm font-bold text-slate-900 tracking-tight">{label}</h4>
          <p className="text-xs text-slate-500 mt-0.5">{helperText}</p>
        </div>

        <div className="flex items-center gap-2 text-[11px] font-mono text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>Local Memory Stream • Zero Server Cloud Sync</span>
        </div>

        {selectedFile && (
          <div
            className="flex items-center justify-between gap-3 p-2.5 bg-white border border-slate-200 rounded-xl text-xs text-slate-800 mt-2 max-w-md w-full shadow-xs"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 min-w-0">
              <FileText className="w-4 h-4 text-blue-600 shrink-0" />
              <span className="font-mono font-medium truncate">{selectedFile.name}</span>
              <span className="text-[10px] text-slate-400 shrink-0">
                ({(selectedFile.size / 1024).toFixed(1)} KB)
              </span>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <button
                type="button"
                onClick={() => {
                  if (fileInputRef.current) {
                    fileInputRef.current.value = "";
                    fileInputRef.current.click();
                  }
                }}
                className="px-2.5 py-1 text-[11px] font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
              >
                Change File
              </button>
              <button
                type="button"
                onClick={() => {
                  setSelectedFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = "";
                }}
                className="p-1 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors cursor-pointer"
                title="Remove file"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
