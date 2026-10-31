import React, { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { Header } from "./components/layout/Header";
import { Navigation, NavTabId } from "./components/layout/Navigation";
import { CoordinatorNavigation, CoordinatorTabId } from "./components/layout/CoordinatorNavigation";
import { GuidedTourModal } from "./components/layout/GuidedTourModal";

// Officer Views
import { DrivesDashboard } from "./views/officer/DrivesDashboard";
import { DriveCreationReview } from "./views/officer/DriveCreationReview";
import { AnnouncementsLibraryView } from "./views/officer/AnnouncementsLibraryView";
import { StudentRegistryView } from "./views/officer/StudentRegistryView";
import { PolicyEditorView } from "./views/officer/PolicyEditorView";
import { PolicySimulatorView } from "./views/officer/PolicySimulatorView";
import { EligibilityTableView } from "./views/officer/EligibilityTableView";
import { ScheduleBoardView } from "./views/officer/ScheduleBoardView";
import { WhatIfPublishView } from "./views/officer/WhatIfPublishView";
import { ResultEntryView } from "./views/officer/ResultEntryView";
import { CompanyExportView } from "./views/officer/CompanyExportView";
import { OfficerMessageBoxView } from "./views/officer/OfficerMessageBoxView";
import { UsersRolesView } from "./views/officer/UsersRolesView";
import { AuditBackupSettingsView } from "./views/officer/AuditBackupSettingsView";
import { AuditHistoryView } from "./views/officer/AuditHistoryView";
import { OfflineSelfCheck } from "./views/audit/OfflineSelfCheck";

// Coordinator Views (Modules 1-12)
import { CoordinatorOverviewView } from "./views/coordinator/CoordinatorOverviewView";
import { CoordinatorStudentsView } from "./views/coordinator/CoordinatorStudentsView";
import { CoordinatorDrivesView } from "./views/coordinator/CoordinatorDrivesView";
import { CoordinatorEligibilityView } from "./views/coordinator/CoordinatorEligibilityView";
import { CoordinatorScheduleView } from "./views/coordinator/CoordinatorScheduleView";
import { CoordinatorClashesView } from "./views/coordinator/CoordinatorClashesView";
import { CoordinatorResultEntryView } from "./views/coordinator/CoordinatorResultEntryView";
import { CoordinatorCommunicationView } from "./views/coordinator/CoordinatorCommunicationView";
import { CoordinatorOnTheDayView } from "./views/coordinator/CoordinatorOnTheDayView";
import { CoordinatorRequestsView } from "./views/coordinator/CoordinatorRequestsView";
import { CoordinatorReportsExportView } from "./views/coordinator/CoordinatorReportsExportView";
import { CoordinatorNotificationsView } from "./views/coordinator/CoordinatorNotificationsView";

// Candidate & Recruiter Views
import { StudentPortal } from "./views/student/StudentPortal";
import { RecruiterPortal } from "./views/recruiter/RecruiterPortal";
import { AlertBanner } from "./components/common/AlertBanner";
import { Watermark } from "./components/common/Watermark";
import { CheckCircle2, ShieldCheck, Building2, Sparkles } from "lucide-react";

const MainContent: React.FC = () => {
  const { user, login, studentLogin, error, clearError } = useAuth();

  // Officer Navigation
  const [activeTab, setActiveTab] = useState<NavTabId>("drives");
  const [activeDriveId, setActiveDriveId] = useState<string | undefined>();
  const [selectedAnnouncementFilename, setSelectedAnnouncementFilename] = useState<string | undefined>();
  const [isTourOpen, setIsTourOpen] = useState(false);

  // Coordinator Navigation (Modules 1-12)
  const [coordTab, setCoordTab] = useState<CoordinatorTabId>("overview");
  const [coordDriveId, setCoordDriveId] = useState<string | undefined>();

  // Unauthenticated Login Form State
  const [authRole, setAuthRole] = useState<"officer" | "coordinator" | "student" | "recruiter">("officer");
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [studentRoll, setStudentRoll] = useState("BT210001");
  const [studentCode, setStudentCode] = useState("123456");
  const [authLoading, setAuthLoading] = useState(false);

  const handleTabSelect = (tab: string, driveId?: string) => {
    setActiveTab(tab as NavTabId);
    if (driveId) setActiveDriveId(driveId);
  };

  const handleCoordTabSelect = (tab: string, driveId?: string) => {
    const normalized = (tab === "on_the_day" || tab === "attendance") ? "ontheday" : (tab as CoordinatorTabId);
    setCoordTab(normalized);
    if (driveId) setCoordDriveId(driveId);
  };

  const handleRoleSwitch = (role: "officer" | "coordinator" | "student" | "recruiter") => {
    setAuthRole(role);
    if (role === "officer") {
      setUsername("admin");
      setPassword("admin123");
    } else if (role === "coordinator") {
      setUsername("coordinator");
      setPassword("coord123");
    } else if (role === "recruiter") {
      setUsername("recruiter_google");
      setPassword("recruiter123");
    } else {
      setStudentRoll("BT210001");
      setStudentCode("123456");
    }
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    try {
      if (authRole === "student") {
        await studentLogin(studentRoll, studentCode);
      } else {
        await login(username, password);
        setActiveTab("drives");
      }
    } catch {
      // Error handled by AuthContext
    } finally {
      setAuthLoading(false);
    }
  };

  // If not logged in, render cyber recruitment SaaS login portal
  if (!user) {
    return (
      <div className="min-h-screen bg-[#060B16] flex flex-col justify-between text-slate-100 selection:bg-cyan-500 selection:text-black relative overflow-hidden font-sans">
        {/* Subtle Cyber Neon Lighting Motif */}
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

        {/* Top Institutional Header */}
        <div className="bg-[#080E1C]/90 backdrop-blur-md px-4 py-2.5 text-xs font-medium text-center border-b border-[#142242] flex items-center justify-between max-w-7xl mx-auto w-full">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center text-white font-black text-xs shadow-md shadow-cyan-500/30">
              PE
            </div>
            <span className="font-bold tracking-tight text-white text-xs">
              Placement Engine <span className="text-cyan-400 font-normal">| Cyber Recruitment Platform</span>
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-300 bg-emerald-950/80 border border-emerald-700/60 px-2 py-0.5 rounded-full">
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              100% Deterministic Engine
            </span>
            <span className="text-[11px] text-slate-400 hidden md:inline">
              ISO / DPDP Institutional Compliant
            </span>
          </div>
        </div>

        {/* Main Login Card Container */}
        <div className="flex-1 flex items-center justify-center p-4 sm:p-6 my-auto z-10">
          <div className="w-full max-w-md corporate-card rounded-3xl p-8 sm:p-10 shadow-2xl border border-[var(--border-card)] text-white space-y-6">
            {/* Header Branding */}
            <div className="text-center space-y-2">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-cyan-500 text-white flex items-center justify-center font-black text-2xl mx-auto shadow-lg shadow-cyan-500/30 ring-4 ring-cyan-500/20">
                PE
              </div>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                Placement Engine
              </h2>
              <div className="flex items-center justify-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 bg-blue-950/80 text-cyan-300 rounded-full border border-cyan-500/40">
                  Cyber SaaS Suite
                </span>
                <span className="text-[10px] font-bold px-2.5 py-0.5 bg-emerald-950/80 text-emerald-300 rounded-full border border-emerald-700/60 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-emerald-400" />
                  0 Clashes Verified
                </span>
              </div>
              <p className="text-xs text-slate-400 pt-1">
                Unified institutional placement, deterministic eligibility evaluation & conflict-free scheduling.
              </p>
            </div>

            {/* Role Switcher Tabs */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-1 bg-[#0A1122] p-1.5 rounded-2xl border border-[#16264C]">
              <button
                type="button"
                onClick={() => handleRoleSwitch("officer")}
                className={`py-2 text-[11px] font-bold rounded-xl transition-all cursor-pointer ${
                  authRole === "officer"
                    ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-md shadow-cyan-500/20"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Officer
              </button>
              <button
                type="button"
                onClick={() => handleRoleSwitch("coordinator")}
                className={`py-2 text-[11px] font-bold rounded-xl transition-all cursor-pointer ${
                  authRole === "coordinator"
                    ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-md shadow-cyan-500/20"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Coordinator
              </button>
              <button
                type="button"
                onClick={() => handleRoleSwitch("student")}
                className={`py-2 text-[11px] font-bold rounded-xl transition-all cursor-pointer ${
                  authRole === "student"
                    ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-md shadow-cyan-500/20"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Student
              </button>
              <button
                type="button"
                onClick={() => handleRoleSwitch("recruiter")}
                className={`py-2 text-[11px] font-bold rounded-xl transition-all cursor-pointer ${
                  authRole === "recruiter"
                    ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-md shadow-cyan-500/20"
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
                    <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
                      Roll Number
                    </label>
                    <input
                      type="text"
                      required
                      value={studentRoll}
                      onChange={(e) => setStudentRoll(e.target.value)}
                      className="w-full px-4 py-2.5 bg-[#0A1122] border border-[#1A2E56] rounded-xl text-sm font-semibold text-white focus:outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-500/20 transition-all placeholder-slate-500"
                      placeholder="e.g. BT210001"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
                      Access Code / PIN
                    </label>
                    <input
                      type="password"
                      required
                      value={studentCode}
                      onChange={(e) => setStudentCode(e.target.value)}
                      className="w-full px-4 py-2.5 bg-[#0A1122] border border-[#1A2E56] rounded-xl text-sm font-semibold text-white focus:outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-500/20 transition-all placeholder-slate-500"
                      placeholder="Default: 123456"
                    />
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
                      Username / Email
                    </label>
                    <input
                      type="text"
                      required
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="w-full px-4 py-2.5 bg-[#0A1122] border border-[#1A2E56] rounded-xl text-sm font-semibold text-white focus:outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-500/20 transition-all placeholder-slate-500"
                      placeholder={`e.g. ${authRole}`}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
                      Password
                    </label>
                    <input
                      type="password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full px-4 py-2.5 bg-[#0A1122] border border-[#1A2E56] rounded-xl text-sm font-semibold text-white focus:outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-500/20 transition-all placeholder-slate-500"
                    />
                  </div>
                </>
              )}

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 active:from-blue-700 active:to-cyan-700 text-white font-bold text-sm rounded-xl shadow-lg shadow-cyan-500/25 transition-all cursor-pointer disabled:opacity-50"
              >
                {authLoading ? "Authenticating..." : `Sign in as ${authRole}`}
              </button>
            </form>
          </div>
        </div>

        {/* Footer with Author Watermark */}
        <div className="p-4 text-center text-xs text-slate-400 border-t border-[#142242] bg-[#080E1C]/80 backdrop-blur-md flex flex-col sm:flex-row items-center justify-center gap-2">
          <span>Institutional Campus Placement Engine • Cyber Recruitment Platform</span>
          <span className="hidden sm:inline text-slate-600">•</span>
          <a
            href="https://github.com/deepesh-art-sec"
            target="_blank"
            rel="noopener noreferrer"
            title="Repository Author"
            className="text-cyan-400 hover:text-cyan-300 font-mono font-bold inline-flex items-center gap-1.5 transition-colors"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            Made by Deepesh-art-sec
          </a>
        </div>
      </div>
    );
  }

  // 1. Candidate Portal
  if (user.role === "student") {
    return (
      <div className="h-screen h-[100dvh] max-h-screen overflow-hidden corporate-canvas flex flex-col font-sans">
        <Header
          onNavigateToAudit={() => {
            window.dispatchEvent(new CustomEvent("navigate-student-tab", { detail: "notifications" }));
          }}
          onOpenAlerts={() => {
            window.dispatchEvent(new CustomEvent("navigate-student-tab", { detail: "notifications" }));
          }}
          onOpenMessageBox={() => {
            window.dispatchEvent(new CustomEvent("navigate-student-tab", { detail: "notifications" }));
          }}
        />
        <div className="flex-1 flex overflow-hidden min-h-0 min-w-0 w-full relative">
          <StudentPortal />
        </div>
      </div>
    );
  }

  // 2. Recruiter Portal
  if (user.role === "recruiter_readonly" || user.role === "recruiter") {
    return (
      <div className="h-screen h-[100dvh] max-h-screen overflow-hidden corporate-canvas flex flex-col font-sans">
        <Header onNavigateToAudit={() => {}} />
        <div className="flex-1 flex overflow-hidden min-h-0 min-w-0 w-full relative">
          <RecruiterPortal />
        </div>
      </div>
    );
  }

  // 3. Coordinator Dashboard (Modules 1 - 12)
  if (user.role === "coordinator") {
    return (
      <div className="h-screen h-[100dvh] max-h-screen overflow-hidden corporate-canvas flex flex-row font-sans">
        <CoordinatorNavigation
          activeTab={coordTab}
          onSelectTab={setCoordTab}
        />
        <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
          <Header
            onOpenTour={() => setIsTourOpen(true)}
            onNavigateToAudit={() => setCoordTab("notifications")}
            onOpenAlerts={() => setCoordTab("notifications")}
            onOpenMessageBox={() => setCoordTab("notifications")}
          />
          <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-7 overflow-y-auto max-w-full corporate-canvas">
            {coordTab === "overview" && (
              <CoordinatorOverviewView onNavigateTab={handleCoordTabSelect} />
            )}
            {coordTab === "students" && <CoordinatorStudentsView />}
            {coordTab === "drives" && <CoordinatorDrivesView />}
            {coordTab === "eligibility" && (
              <CoordinatorEligibilityView initialDriveId={coordDriveId} />
            )}
            {coordTab === "schedule" && (
              <CoordinatorScheduleView initialDriveId={coordDriveId} />
            )}
            {coordTab === "clashes" && <CoordinatorClashesView />}
            {coordTab === "results" && <CoordinatorResultEntryView />}
            {coordTab === "communication" && <CoordinatorCommunicationView />}
            {(coordTab === "ontheday" || (coordTab as string) === "attendance") && (
              <CoordinatorOnTheDayView initialDriveId={coordDriveId} />
            )}
            {coordTab === "requests" && <CoordinatorRequestsView />}
            {coordTab === "reports" && <CoordinatorReportsExportView />}
            {coordTab === "notifications" && (
              <CoordinatorNotificationsView
                onNavigateTab={(tab) => setCoordTab(tab as CoordinatorTabId)}
              />
            )}
          </main>
        </div>

        <GuidedTourModal
          isOpen={isTourOpen}
          onClose={() => setIsTourOpen(false)}
          onNavigateToTab={(tabId) => setCoordTab(tabId as CoordinatorTabId)}
        />
      </div>
    );
  }

  // 4. Officer Workspace (Full Executive Authority)
  return (
    <div className="h-screen h-[100dvh] max-h-screen overflow-hidden corporate-canvas flex flex-row font-sans">
      <Navigation
        activeTab={activeTab}
        onSelectTab={handleTabSelect}
        userRole={user.role}
      />

      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <Header
          onOpenTour={() => setIsTourOpen(true)}
          onNavigateToAudit={() => setActiveTab("offline_audit")}
          onOpenAlerts={() => setActiveTab("message_box")}
          onOpenMessageBox={() => setActiveTab("message_box")}
        />

        <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-7 overflow-y-auto max-w-full corporate-canvas">
          {activeTab === "message_box" && <OfficerMessageBoxView />}
          {activeTab === "attendance" && (
            <CoordinatorOnTheDayView initialDriveId={activeDriveId} />
          )}
          {activeTab === "drives" && (
            <DrivesDashboard onNavigateTab={handleTabSelect} />
          )}
          {activeTab === "create_drive" && (
            <DriveCreationReview
              initialAnnouncementFilename={selectedAnnouncementFilename}
              onSuccess={(driveId) => handleTabSelect("eligibility", driveId)}
            />
          )}
          {activeTab === "announcements" && (
            <AnnouncementsLibraryView
              onNavigateToExtract={(filename) => {
                setSelectedAnnouncementFilename(filename);
                setActiveTab("create_drive");
              }}
              onNavigateToDrive={(id) => {
                setActiveDriveId(id);
                setActiveTab("drives");
              }}
            />
          )}
          {activeTab === "students" && <StudentRegistryView />}
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
          {activeTab === "export" && <CompanyExportView />}
          {activeTab === "users_roles" && <UsersRolesView />}
          {activeTab === "audit_backup" && <AuditBackupSettingsView />}
          {activeTab === "audit" && <AuditHistoryView />}
          {activeTab === "offline_audit" && <OfflineSelfCheck />}
        </main>
      </div>

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
    <ThemeProvider>
      <AuthProvider>
        <MainContent />
        <Watermark />
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;
