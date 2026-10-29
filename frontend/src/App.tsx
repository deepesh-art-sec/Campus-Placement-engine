import React, { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Header } from "./components/layout/Header";
import { Navigation, NavTabId } from "./components/layout/Navigation";
import { CoordinatorNavigation, CoordinatorTabId } from "./components/layout/CoordinatorNavigation";
import { GuidedTourModal } from "./components/layout/GuidedTourModal";

// Officer Views
import { DrivesDashboard } from "./views/officer/DrivesDashboard";
import { DriveCreationReview } from "./views/officer/DriveCreationReview";
import { AnnouncementsLibraryView } from "./views/officer/AnnouncementsLibraryView";
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
import { CheckCircle2 } from "lucide-react";

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
    setCoordTab(tab as CoordinatorTabId);
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

  // If not logged in, render role-specific login portal
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#040810] via-[#070e1c] to-[#0a162d] flex flex-col justify-between text-slate-100 selection:bg-emerald-500 selection:text-white relative overflow-hidden">
        {/* Ambient Glow */}
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

        {/* Top Status Bar */}
        <div className="bg-[#040810]/90 backdrop-blur-md px-4 py-2 text-xs font-medium text-center border-b border-[#1b2b4d] flex items-center justify-center gap-3">
          <span className="flex items-center gap-1.5 text-emerald-400 font-mono text-[11px] font-bold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            CAMPUS PLACEMENT ENGINE
          </span>
          <span className="text-slate-600 hidden sm:inline">•</span>
          <span className="text-slate-400 text-[11px] hidden sm:inline">
            Deterministic Eligibility & Constraint Scheduling
          </span>
        </div>

        {/* Main Card Container */}
        <div className="flex-1 flex items-center justify-center p-4 sm:p-6 my-auto">
          <div className="w-full max-w-md bg-[#0d1527]/95 backdrop-blur-xl rounded-3xl p-8 sm:p-10 shadow-2xl border border-[#1b2b4d] text-slate-100 space-y-6">
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
            </div>

            {/* Role Switcher Tabs */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 bg-[#080e1c] p-1.5 rounded-2xl border border-[#1b2b4d]">
              <button
                type="button"
                onClick={() => handleRoleSwitch("officer")}
                className={`py-2 text-[11px] font-bold rounded-xl transition-all cursor-pointer ${
                  authRole === "officer"
                    ? "bg-gradient-to-r from-blue-700 to-emerald-600 text-white shadow-sm shadow-emerald-900/40"
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
                    ? "bg-gradient-to-r from-indigo-700 to-purple-600 text-white shadow-sm shadow-purple-900/40"
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
                    ? "bg-gradient-to-r from-blue-700 to-emerald-600 text-white shadow-sm shadow-emerald-900/40"
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
                      placeholder="e.g. BT210001"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                      Access Code / Password
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
                      className="w-full px-4 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:bg-[#0d1527] focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                      placeholder={`e.g. ${authRole}`}
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
                      className="w-full px-4 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:bg-[#0d1527] focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                    />
                  </div>
                </>
              )}

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-3 bg-gradient-to-r from-blue-600 via-teal-600 to-emerald-600 hover:from-blue-500 hover:via-teal-500 hover:to-emerald-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-emerald-900/30 border border-emerald-400/30 transition-all cursor-pointer disabled:opacity-50"
              >
                {authLoading ? "Authenticating..." : `Sign in as ${authRole}`}
              </button>
            </form>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 text-center text-xs text-slate-500 border-t border-[#1b2b4d] bg-[#040810]/80 backdrop-blur-md">
          Institutional Campus Placement Engine • High-Performance Deterministic Scheduling
        </div>
      </div>
    );
  }

  // 1. Candidate Portal
  if (user.role === "student") {
    return (
      <div className="min-h-screen bg-[#060b14] text-slate-100 flex flex-col">
        <Header onNavigateToAudit={() => {}} />
        <div className="flex-1 flex overflow-hidden">
          <StudentPortal />
        </div>
      </div>
    );
  }

  // 2. Recruiter Portal
  if (user.role === "recruiter_readonly" || user.role === "recruiter") {
    return (
      <div className="min-h-screen bg-[#060b14] text-slate-100 flex flex-col">
        <Header onNavigateToAudit={() => {}} />
        <div className="flex-1 flex overflow-hidden">
          <RecruiterPortal />
        </div>
      </div>
    );
  }

  // 3. Coordinator Dashboard (Modules 1 - 12)
  if (user.role === "coordinator") {
    return (
      <div className="min-h-screen bg-[#060b14] text-slate-100 flex flex-col">
        <Header
          onOpenTour={() => setIsTourOpen(true)}
          onNavigateToAudit={() => setCoordTab("notifications")}
        />
        <div className="flex-1 flex overflow-hidden">
          <CoordinatorNavigation
            activeTab={coordTab}
            onSelectTab={setCoordTab}
          />
          <main className="flex-1 min-w-0 p-2.5 sm:p-4 md:p-6 lg:p-8 overflow-y-auto max-w-full">
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
            {coordTab === "ontheday" && (
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
    <div className="min-h-screen bg-[#060b14] text-slate-100 flex flex-col">
      <Header
        onOpenTour={() => setIsTourOpen(true)}
        onNavigateToAudit={() => setActiveTab("offline_audit")}
      />
      <div className="flex-1 flex overflow-hidden">
        <Navigation
          activeTab={activeTab}
          onSelectTab={handleTabSelect}
          userRole={user.role}
        />

        <main className="flex-1 min-w-0 p-2.5 sm:p-4 md:p-6 lg:p-8 overflow-y-auto max-w-full">
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
    <AuthProvider>
      <MainContent />
    </AuthProvider>
  );
};

export default App;
