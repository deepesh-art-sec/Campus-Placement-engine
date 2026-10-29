import React, { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Header } from "./components/layout/Header";
import { Navigation, NavTabId } from "./components/layout/Navigation";
import { GuidedTourModal } from "./components/layout/GuidedTourModal";
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
import { AuditHistoryView } from "./views/officer/AuditHistoryView";
import { RequestsManagerView } from "./views/officer/RequestsManagerView";
import { UserManagementView } from "./views/officer/UserManagementView";
import { OfflineSelfCheck } from "./views/audit/OfflineSelfCheck";
import { StudentPortal } from "./views/student/StudentPortal";
import { RecruiterPortal } from "./views/recruiter/RecruiterPortal";
import { CoordinatorDashboard } from "./views/coordinator/CoordinatorDashboard";
import { ComponentsShowcaseView } from "./views/dev/ComponentsShowcaseView";
import { AlertBanner } from "./components/common/AlertBanner";
import { CheckCircle2, Shield, Users, Briefcase, GraduationCap } from "lucide-react";

const MainContent: React.FC = () => {
  const { user, login, studentLogin, error, clearError } = useAuth();
  const [activeTab, setActiveTab] = useState<NavTabId>("drives");
  const [activeDriveId, setActiveDriveId] = useState<string | undefined>();
  const [isTourOpen, setIsTourOpen] = useState(false);

  // Unauthenticated Login Form State
  const [authRole, setAuthRole] = useState<"officer" | "coordinator" | "student" | "recruiter">("officer");
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [studentRoll, setStudentRoll] = useState("BT210001");
  const [studentCode, setStudentCode] = useState("admin123");
  const [authLoading, setAuthLoading] = useState(false);

  const handleRoleSelect = (role: "officer" | "coordinator" | "student" | "recruiter") => {
    setAuthRole(role);
    clearError();
    if (role === "officer") {
      setUsername("admin");
      setPassword("admin123");
    } else if (role === "coordinator") {
      setUsername("coordinator");
      setPassword("admin123");
    } else if (role === "recruiter") {
      setUsername("recruiter");
      setPassword("admin123");
    } else if (role === "student") {
      setStudentRoll("BT210001");
      setStudentCode("admin123");
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
      if (authRole === "officer" || authRole === "coordinator" || authRole === "recruiter") {
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

  // If not logged in, render role-specific login portal
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#040810] via-[#070e1c] to-[#0a162d] flex flex-col justify-between text-slate-100 selection:bg-emerald-500 selection:text-white relative overflow-hidden">
        {/* Subtle Ambient Background Orbs */}
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

        {/* Main Card Container */}
        <div className="flex-1 flex items-center justify-center p-4 sm:p-6 my-auto">
          <div className="w-full max-w-md bg-[#0d1527]/95 backdrop-blur-xl rounded-3xl p-8 sm:p-10 shadow-2xl border border-[#1e3258] text-slate-100 space-y-6">
            {/* Header Branding */}
            <div className="text-center space-y-2">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-700 via-teal-600 to-emerald-500 flex items-center justify-center text-white font-black text-2xl mx-auto shadow-xl shadow-emerald-500/20 ring-4 ring-emerald-500/20">
                PE
              </div>
              <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
                Placement Engine
              </h2>
              <p className="text-xs text-slate-400 pt-1">
                Deterministic policy evaluation, on-the-day attendance, and automated constraint scheduling.
              </p>
            </div>

            {/* Role Switcher Tabs (4 Roles: Officer, Coordinator, Recruiter, Student) */}
            <div className="grid grid-cols-4 gap-1 bg-[#080e1c] p-1.5 rounded-2xl border border-[#1b2b4d]">
              <button
                type="button"
                onClick={() => handleRoleSelect("officer")}
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
                onClick={() => handleRoleSelect("coordinator")}
                className={`py-2 text-[11px] font-bold rounded-xl transition-all cursor-pointer ${
                  authRole === "coordinator"
                    ? "bg-gradient-to-r from-blue-700 to-emerald-600 text-white shadow-sm shadow-emerald-900/40"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Coord
              </button>
              <button
                type="button"
                onClick={() => handleRoleSelect("recruiter")}
                className={`py-2 text-[11px] font-bold rounded-xl transition-all cursor-pointer ${
                  authRole === "recruiter"
                    ? "bg-gradient-to-r from-blue-700 to-emerald-600 text-white shadow-sm shadow-emerald-900/40"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Recruiter
              </button>
              <button
                type="button"
                onClick={() => handleRoleSelect("student")}
                className={`py-2 text-[11px] font-bold rounded-xl transition-all cursor-pointer ${
                  authRole === "student"
                    ? "bg-gradient-to-r from-blue-700 to-emerald-600 text-white shadow-sm shadow-emerald-900/40"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Student
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
                      className="w-full px-4 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:bg-[#0d1527] focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all font-mono"
                      placeholder="e.g. BT210001 or PIPE_001"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                      One-Time Access Code / Password
                    </label>
                    <input
                      type="password"
                      required
                      value={studentCode}
                      onChange={(e) => setStudentCode(e.target.value)}
                      className="w-full px-4 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:bg-[#0d1527] focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all font-mono"
                      placeholder="Default: admin123"
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
                      className="w-full px-4 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:bg-[#0d1527] focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all font-mono"
                      placeholder={authRole === "officer" ? "admin" : authRole === "coordinator" ? "coordinator" : "recruiter"}
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
                      className="w-full px-4 py-2.5 bg-[#080e1c] border border-[#1e3258] rounded-xl text-sm font-semibold text-white focus:bg-[#0d1527] focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all font-mono"
                      placeholder="Default: admin123"
                    />
                  </div>
                </>
              )}

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-3 bg-gradient-to-r from-blue-600 via-teal-600 to-emerald-600 hover:from-blue-500 hover:via-teal-500 hover:to-emerald-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-emerald-900/30 border border-emerald-400/30 transition-all cursor-pointer disabled:opacity-50"
              >
                {authLoading
                  ? "Authenticating..."
                  : `Sign in as ${
                      authRole === "officer"
                        ? "Placement Officer"
                        : authRole === "coordinator"
                        ? "Placement Coordinator"
                        : authRole === "student"
                        ? "Student Candidate"
                        : "Corporate Recruiter"
                    }`}
              </button>

              <div className="pt-2 text-center text-xs text-slate-400 bg-[#080e1c] p-2.5 rounded-xl border border-[#1b2b4d]/60">
                <span className="font-semibold text-slate-300">Credentials for this role:</span>
                {authRole === "officer" && <div className="mt-1 font-mono text-emerald-400 font-bold">Username: admin | Password: admin123</div>}
                {authRole === "coordinator" && <div className="mt-1 font-mono text-emerald-400 font-bold">Username: coordinator | Password: admin123</div>}
                {authRole === "recruiter" && <div className="mt-1 font-mono text-emerald-400 font-bold">Username: recruiter | Password: admin123</div>}
                {authRole === "student" && <div className="mt-1 font-mono text-emerald-400 font-bold">Roll No: BT210001 | Code: admin123</div>}
              </div>
            </form>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 text-center text-xs text-slate-500 border-t border-[#1b2b4d] bg-[#040810]/80 backdrop-blur-md">
          Campus Placement Engine
        </div>
      </div>
    );
  }

  // 1. Candidate logged in
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

  // 2. Recruiter logged in (Prompt 4)
  if (user.role === "recruiter_readonly" || user.role === "recruiter") {
    return (
      <div className="min-h-screen bg-[#060b14] text-slate-100 flex flex-col">
        <Header onNavigateToAudit={() => {}} />
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
          <RecruiterPortal />
        </main>
      </div>
    );
  }

  // 3. Coordinator logged in (Prompt 2)
  if (user.role === "coordinator") {
    return (
      <div className="min-h-screen bg-[#060b14] text-slate-100 flex flex-col">
        <Header onNavigateToAudit={() => {}} />
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
          <CoordinatorDashboard />
        </main>
      </div>
    );
  }

  // 4. Officer Workspace (Prompt 1)
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
        {activeTab === "announcements" && (
          <AnnouncementsLibraryView
            onNavigateToExtract={(fn) => {
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
        {activeTab === "requests_manager" && <RequestsManagerView />}
        {activeTab === "user_management" && <UserManagementView />}
        {activeTab === "recruiter_portal" && <RecruiterPortal />}
        {activeTab === "audit" && <AuditHistoryView />}
        {activeTab === "offline_audit" && <OfflineSelfCheck />}
        {activeTab === "dev_components" && <ComponentsShowcaseView />}
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
