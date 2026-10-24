import React, { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Header } from "./components/layout/Header";
import { Navigation, NavTabId } from "./components/layout/Navigation";
import { GuidedTourModal } from "./components/layout/GuidedTourModal";
import { DrivesDashboard } from "./views/officer/DrivesDashboard";
import { DriveCreationReview } from "./views/officer/DriveCreationReview";
import { StudentRegistryView } from "./views/officer/StudentRegistryView";
import { RuleEditorView } from "./views/officer/RuleEditorView";
import { PolicyEditorView } from "./views/officer/PolicyEditorView";
import { PolicySimulatorView } from "./views/officer/PolicySimulatorView";
import { EligibilityTableView } from "./views/officer/EligibilityTableView";
import { ScheduleBoardView } from "./views/officer/ScheduleBoardView";
import { WhatIfPublishView } from "./views/officer/WhatIfPublishView";
import { ResultEntryView } from "./views/officer/ResultEntryView";
import { DisputeComparisonView } from "./views/officer/DisputeComparisonView";
import { CompanyExportView } from "./views/officer/CompanyExportView";
import { AuditHistoryView } from "./views/officer/AuditHistoryView";
import { OfflineSelfCheck } from "./views/audit/OfflineSelfCheck";
import { StudentPortal } from "./views/student/StudentPortal";
import { RecruiterPortal } from "./views/recruiter/RecruiterPortal";
import { AlertBanner } from "./components/common/AlertBanner";
import { api } from "./api/client";
import {
  WifiOff,
  CheckCircle2,
  Sparkles,
  Copy,
  Check,
  Radio,
} from "lucide-react";

const MainContent: React.FC = () => {
  const { user, login, studentLogin, error, clearError } = useAuth();
  const [activeTab, setActiveTab] = useState<NavTabId>("drives");
  const [activeDriveId, setActiveDriveId] = useState<string | undefined>();
  const [isTourOpen, setIsTourOpen] = useState(false);

  // Unauthenticated Login Form State
  const [authRole, setAuthRole] = useState<"officer" | "student" | "recruiter">("officer");
  const [username, setUsername] = useState("officer");
  const [password, setPassword] = useState("officer123");
  const [studentRoll, setStudentRoll] = useState("PIPE_001");
  const [studentCode, setStudentCode] = useState("123456");
  const [authLoading, setAuthLoading] = useState(false);

  // LAN Access Link
  const [lanUrl, setLanUrl] = useState<string>(() => {
    if (typeof window !== "undefined") {
      if (window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
        return `${window.location.protocol}//${window.location.hostname}:8000`;
      }
    }
    return "http://localhost:8000";
  });
  const [lanCopied, setLanCopied] = useState(false);

  useEffect(() => {
    api.get<any>("/api/lan-info").then((res) => {
      if (res?.primary_url) {
        setLanUrl(res.primary_url);
      }
    }).catch(() => {});
  }, []);

  const handleCopyLan = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(lanUrl);
      setLanCopied(true);
      setTimeout(() => setLanCopied(false), 2000);
    }
  };

  const handleTabSelect = (tab: string, driveId?: string) => {
    setActiveTab(tab as NavTabId);
    if (driveId) setActiveDriveId(driveId);
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    try {
      if (authRole === "officer" || authRole === "recruiter") {
        await login(username, password);
      } else {
        await studentLogin(studentRoll, studentCode);
      }
    } catch {
      // Error handled by AuthContext
    } finally {
      setAuthLoading(false);
    }
  };

  // Quick Preset Helper
  const setDemoPersona = (
    role: "officer" | "student" | "recruiter",
    userOrRoll: string,
    passOrCode: string
  ) => {
    setAuthRole(role);
    if (role === "student") {
      setStudentRoll(userOrRoll);
      setStudentCode(passOrCode);
    } else {
      setUsername(userOrRoll);
      setPassword(passOrCode);
    }
  };

  // If not logged in, render role-specific login portal
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#040810] via-[#070e1c] to-[#0a162d] flex flex-col justify-between text-slate-100 selection:bg-emerald-500 selection:text-white relative overflow-hidden">
        {/* Subtle Ambient Background Orbs */}
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

        {/* Top Status Bar */}
        <div className="bg-[#040810]/90 backdrop-blur-md px-4 py-2 text-xs font-medium text-center border-b border-[#1b2b4d] flex items-center justify-center gap-3">
          <span className="flex items-center gap-1.5 text-emerald-400 font-mono text-[11px] font-bold">
            <WifiOff className="w-3.5 h-3.5" />
            100% AIR-GAPPED OFFLINE LAN RUNTIME
          </span>
          <span className="text-slate-600 hidden sm:inline">•</span>
          <span className="text-slate-400 text-[11px] hidden sm:inline">
            Local SQLite WAL Engine • External Calls: 0
          </span>
          <span className="text-slate-600 hidden md:inline">•</span>
          <span className="text-emerald-300 text-[11px] font-mono font-bold hidden md:inline">
            LAN Host: {lanUrl}
          </span>
        </div>

        {/* Main Card Container */}
        <div className="flex-1 flex items-center justify-center p-4 sm:p-6 my-auto">
          <div className="w-full max-w-lg bg-[#0d1527]/95 backdrop-blur-xl rounded-3xl p-8 sm:p-10 shadow-2xl border border-[#1b2b4d] text-slate-100 space-y-6">
            {/* Header Branding */}
            <div className="text-center space-y-2">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-700 via-teal-600 to-emerald-500 flex items-center justify-center text-white font-black text-2xl mx-auto shadow-xl shadow-emerald-500/20 ring-4 ring-emerald-500/20">PE</div>
              <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
                Placement Engine
              </h2>
              <div className="flex items-center justify-center gap-2">
                <span className="text-[11px] font-bold uppercase tracking-wider px-2.5 py-0.5 bg-blue-950/80 text-blue-300 rounded-full border border-blue-800/60">
                  Eligibility & Scheduling Engine
                </span>
                <span className="text-[11px] font-bold px-2.5 py-0.5 bg-emerald-950/80 text-emerald-300 rounded-full border border-emerald-800/60 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  0 Clashes Verified
                </span>
              </div>
              <p className="text-xs text-slate-400 pt-1">
                One student, three drives, one Tuesday. Complete deterministic eligibility & constraint scheduling.
              </p>

              {/* Shareable LAN Pill */}
              <div className="pt-1 flex items-center justify-center">
                <button
                  type="button"
                  onClick={handleCopyLan}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#080e1c] hover:bg-[#111d38] border border-[#1b2b4d] hover:border-emerald-500/40 text-slate-300 text-[11px] font-mono transition-all cursor-pointer shadow-xs"
                  title="Click to copy Wi-Fi / LAN link"
                >
                  <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
                  <span className="text-slate-400">LAN Host:</span>
                  <span className="text-emerald-300 font-bold">{lanUrl}</span>
                  {lanCopied ? (
                    <Check className="w-3 h-3 text-emerald-400 ml-0.5" />
                  ) : (
                    <Copy className="w-3 h-3 text-slate-400 hover:text-white ml-0.5" />
                  )}
                </button>
              </div>
            </div>

            {/* Quick Demo Persona Shortcuts */}
            <div className="space-y-2 bg-[#080e1c] p-3.5 rounded-2xl border border-[#1b2b4d]">
              <div className="flex items-center justify-between text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                <span className="flex items-center gap-1 text-emerald-400">
                  <Sparkles className="w-3 h-3 text-emerald-400" />
                  1-Click Demo Personas
                </span>
                <span className="text-[10px] text-slate-500 font-normal">Auto-fills credentials</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 text-[11px] font-semibold">
                <button
                  type="button"
                  onClick={() => setDemoPersona("officer", "officer", "officer123")}
                  className={`p-1.5 rounded-lg border text-left transition-all cursor-pointer ${
                    authRole === "officer" && username === "officer"
                      ? "bg-gradient-to-r from-blue-900/60 to-emerald-950/60 text-emerald-200 border-emerald-500/80 shadow-xs"
                      : "bg-[#0d1527] text-slate-300 hover:bg-[#111d38] border-[#1b2b4d]"
                  }`}
                >
                  <div className="font-bold">TPO Officer</div>
                  <div className="text-[9px] opacity-75 font-mono text-emerald-400">officer123</div>
                </button>
                <button
                  type="button"
                  onClick={() => setDemoPersona("officer", "coordinator", "coord123")}
                  className={`p-1.5 rounded-lg border text-left transition-all cursor-pointer ${
                    authRole === "officer" && username === "coordinator"
                      ? "bg-gradient-to-r from-blue-900/60 to-emerald-950/60 text-emerald-200 border-emerald-500/80 shadow-xs"
                      : "bg-[#0d1527] text-slate-300 hover:bg-[#111d38] border-[#1b2b4d]"
                  }`}
                >
                  <div className="font-bold">Coordinator</div>
                  <div className="text-[9px] opacity-75 font-mono text-emerald-400">coord123</div>
                </button>
                <button
                  type="button"
                  onClick={() => setDemoPersona("student", "PIPE_001", "123456")}
                  className={`p-1.5 rounded-lg border text-left transition-all cursor-pointer ${
                    authRole === "student" && studentRoll === "PIPE_001"
                      ? "bg-gradient-to-r from-blue-900/60 to-emerald-950/60 text-emerald-200 border-emerald-500/80 shadow-xs"
                      : "bg-[#0d1527] text-slate-300 hover:bg-[#111d38] border-[#1b2b4d]"
                  }`}
                >
                  <div className="font-bold">Aryan (Eligible)</div>
                  <div className="text-[9px] opacity-75 font-mono text-emerald-400">PIPE_001</div>
                </button>
                <button
                  type="button"
                  onClick={() => setDemoPersona("student", "PIPE_002", "123456")}
                  className={`p-1.5 rounded-lg border text-left transition-all cursor-pointer ${
                    authRole === "student" && studentRoll === "PIPE_002"
                      ? "bg-gradient-to-r from-blue-900/60 to-emerald-950/60 text-emerald-200 border-emerald-500/80 shadow-xs"
                      : "bg-[#0d1527] text-slate-300 hover:bg-[#111d38] border-[#1b2b4d]"
                  }`}
                >
                  <div className="font-bold">Priya (Lateral)</div>
                  <div className="text-[9px] opacity-75 font-mono text-emerald-400">PIPE_002</div>
                </button>
                <button
                  type="button"
                  onClick={() => setDemoPersona("student", "PIPE_003", "123456")}
                  className={`p-1.5 rounded-lg border text-left transition-all cursor-pointer ${
                    authRole === "student" && studentRoll === "PIPE_003"
                      ? "bg-gradient-to-r from-blue-900/60 to-emerald-950/60 text-emerald-200 border-emerald-500/80 shadow-xs"
                      : "bg-[#0d1527] text-slate-300 hover:bg-[#111d38] border-[#1b2b4d]"
                  }`}
                >
                  <div className="font-bold">Rohan (Blocked)</div>
                  <div className="text-[9px] opacity-75 font-mono text-emerald-400">PIPE_003</div>
                </button>
                <button
                  type="button"
                  onClick={() => setDemoPersona("recruiter", "recruiter_google", "recruiter123")}
                  className={`p-1.5 rounded-lg border text-left transition-all cursor-pointer ${
                    authRole === "recruiter" && username === "recruiter_google"
                      ? "bg-gradient-to-r from-blue-900/60 to-emerald-950/60 text-emerald-200 border-emerald-500/80 shadow-xs"
                      : "bg-[#0d1527] text-slate-300 hover:bg-[#111d38] border-[#1b2b4d]"
                  }`}
                >
                  <div className="font-bold">Google Recruiter</div>
                  <div className="text-[9px] opacity-75 font-mono text-emerald-400">recruiter123</div>
                </button>
              </div>
            </div>

            {/* Role Switcher Tabs */}
            <div className="grid grid-cols-3 gap-1 bg-[#080e1c] p-1.5 rounded-2xl border border-[#1b2b4d]">
              <button
                type="button"
                onClick={() => {
                  setAuthRole("officer");
                  setUsername("officer");
                  setPassword("officer123");
                }}
                className={`py-2 text-xs font-bold rounded-xl transition-all cursor-pointer ${
                  authRole === "officer"
                    ? "bg-gradient-to-r from-blue-700 to-emerald-600 text-white shadow-sm shadow-emerald-900/40"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Officer
              </button>
              <button
                type="button"
                onClick={() => {
                  setAuthRole("student");
                  setStudentRoll("PIPE_001");
                  setStudentCode("123456");
                }}
                className={`py-2 text-xs font-bold rounded-xl transition-all cursor-pointer ${
                  authRole === "student"
                    ? "bg-gradient-to-r from-blue-700 to-emerald-600 text-white shadow-sm shadow-emerald-900/40"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Student
              </button>
              <button
                type="button"
                onClick={() => {
                  setAuthRole("recruiter");
                  setUsername("recruiter_google");
                  setPassword("recruiter123");
                }}
                className={`py-2 text-xs font-bold rounded-xl transition-all cursor-pointer ${
                  authRole === "recruiter"
                    ? "bg-gradient-to-r from-blue-700 to-emerald-600 text-white shadow-sm shadow-emerald-900/40"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Recruiter
              </button>
            </div>

            {error && <AlertBanner type="danger" message={error} onClose={clearError} />}

            <form onSubmit={handleLoginSubmit} className="space-y-4">
              {authRole === "student" ? (
                <>
                  <div>
                    <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                      Roll Number
                    </label>
                    <input
                      type="text"
                      required
                      value={studentRoll}
                      onChange={(e) => setStudentRoll(e.target.value)}
                      className="w-full px-4 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:bg-[#0d1527] focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                      placeholder="e.g. PIPE_001"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                      One-Time Access Code
                    </label>
                    <input
                      type="password"
                      required
                      value={studentCode}
                      onChange={(e) => setStudentCode(e.target.value)}
                      className="w-full px-4 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:bg-[#0d1527] focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                      placeholder="Default: 123456"
                    />
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                      Username
                    </label>
                    <input
                      type="text"
                      required
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="w-full px-4 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:bg-[#0d1527] focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                      Password
                    </label>
                    <input
                      type="password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full px-4 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:bg-[#0d1527] focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                    />
                  </div>
                </>
              )}

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-3 bg-gradient-to-r from-blue-600 via-teal-600 to-emerald-600 hover:from-blue-500 hover:via-teal-500 hover:to-emerald-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-emerald-900/30 border border-emerald-400/30 transition-all cursor-pointer disabled:opacity-50"
              >
                {authLoading ? "Authenticating on Local LAN..." : `Sign in as ${authRole}`}
              </button>
            </form>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 text-center text-xs text-slate-500 border-t border-[#1b2b4d] bg-[#040810]/80 backdrop-blur-md">
          Institutional Campus Placement Engine • 100% Offline SQLite + FastAPI Runtime
        </div>
      </div>
    );
  }

  // If candidate logged in
  if (user.role === "student") {
    return (
      <div className="min-h-screen bg-[#060b14] text-slate-100 flex flex-col">
        <Header onNavigateToAudit={() => {}} />
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
          <StudentPortal />
        </main>
      </div>
    );
  }

  // If recruiter logged in
  if (user.role === "recruiter_readonly") {
    return (
      <div className="min-h-screen bg-[#060b14] text-slate-100 flex flex-col">
        <Header onNavigateToAudit={() => {}} />
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
          <RecruiterPortal />
        </main>
      </div>
    );
  }

  // Officer / Coordinator Workspace
  return (
    <div className="min-h-screen bg-[#060b14] text-slate-100 flex flex-col">
      <Header
        onOpenTour={() => setIsTourOpen(true)}
        onNavigateToAudit={() => setActiveTab("offline_audit")}
      />
      <Navigation
        activeTab={activeTab}
        onSelectTab={handleTabSelect}
        userRole={user.role}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {activeTab === "drives" && (
          <DrivesDashboard onNavigateTab={handleTabSelect} />
        )}
        {activeTab === "create_drive" && (
          <DriveCreationReview
            onSuccess={(driveId) => handleTabSelect("eligibility", driveId)}
          />
        )}
        {activeTab === "students" && <StudentRegistryView />}
        {activeTab === "rule_editor" && <RuleEditorView />}
        {activeTab === "policies" && <PolicyEditorView />}
        {activeTab === "policy_simulator" && <PolicySimulatorView />}
        {activeTab === "eligibility" && (
          <EligibilityTableView initialDriveId={activeDriveId} />
        )}
        {activeTab === "schedule" && (
          <ScheduleBoardView initialDriveId={activeDriveId} />
        )}
        {activeTab === "what_if" && (
          <WhatIfPublishView initialDriveId={activeDriveId} />
        )}
        {activeTab === "results" && <ResultEntryView />}
        {activeTab === "dispute" && <DisputeComparisonView />}
        {activeTab === "export" && <CompanyExportView />}
        {activeTab === "audit" && <AuditHistoryView />}
        {activeTab === "offline_audit" && <OfflineSelfCheck />}
      </main>

      <GuidedTourModal
        isOpen={isTourOpen}
        onClose={() => setIsTourOpen(false)}
        onNavigateToTab={(tabId) => setActiveTab(tabId as NavTabId)}
      />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MainContent />
    </AuthProvider>
  );
};

export default App;
