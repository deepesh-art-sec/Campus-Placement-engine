import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import { Modal } from "../../components/common/Modal";
import {
  Users,
  UserPlus,
  Key,
  Shield,
  Building,
  CheckCircle2,
  XCircle,
  Printer,
  Copy,
  RefreshCw,
  Search,
  Filter,
  Check,
  Lock,
  AlertTriangle,
  FileSpreadsheet,
} from "lucide-react";

interface UserItem {
  id: string;
  username: string;
  email: string;
  role: "officer" | "coordinator" | "recruiter_readonly";
  is_active: boolean;
  company_id?: string;
  company_name?: string;
  created_at?: string;
}

interface CompanyOption {
  id: string;
  name: string;
  tier: string;
}

interface StudentCodeItem {
  roll_no: string;
  name: string;
  branch: string;
  access_code: string;
}

export const UsersRolesView: React.FC = () => {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [companies, setCompanies] = useState<CompanyOption[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Active view tab
  const [activeSubTab, setActiveSubTab] = useState<"accounts" | "student_codes">("accounts");

  // Create User Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [newUsername, setNewUsername] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newRole, setNewRole] = useState<"coordinator" | "recruiter_readonly">("coordinator");
  const [newPassword, setNewPassword] = useState("");
  const [newCompanyId, setNewCompanyId] = useState("");
  const [creationReason, setCreationReason] = useState("Authorized institutional placement staff addition");
  const [creating, setCreating] = useState(false);

  // Status Toggle Modal State
  const [statusUser, setStatusUser] = useState<UserItem | null>(null);
  const [statusReason, setStatusReason] = useState("");
  const [updatingStatus, setUpdatingStatus] = useState(false);

  // Single OTP Issue State
  const [singleRollNo, setSingleRollNo] = useState("");
  const [singleCustomCode, setSingleCustomCode] = useState("");
  const [singleCodeResult, setSingleCodeResult] = useState<{ roll_no: string; access_code: string } | null>(null);
  const [singleIssuing, setSingleIssuing] = useState(false);

  // Bulk Student Codes State
  const [bulkBranch, setBulkBranch] = useState("all");
  const [bulkLimit, setBulkLimit] = useState<number>(50);
  const [bulkRoster, setBulkRoster] = useState<StudentCodeItem[]>([]);
  const [bulkIssuing, setBulkIssuing] = useState(false);
  const [copiedCodeIndex, setCopiedCodeIndex] = useState<number | null>(null);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const [uRes, cRes] = await Promise.all([
        api.get<UserItem[]>("/api/users"),
        api.get<CompanyOption[]>("/api/users/companies"),
      ]);
      setUsers(uRes || []);
      setCompanies(cRes || []);
      if (cRes && cRes.length > 0) {
        setNewCompanyId(cRes[0].id);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load accounts.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setCreating(true);
      setError(null);
      await api.post("/api/users", {
        username: newUsername.trim(),
        email: newEmail.trim(),
        role: newRole,
        password: newPassword,
        company_id: newRole === "recruiter_readonly" ? newCompanyId : null,
      });

      setSuccess(`Account for '${newUsername}' (${newRole}) created successfully.`);
      setIsCreateModalOpen(false);
      setNewUsername("");
      setNewEmail("");
      setNewPassword("");
      fetchUsers();
    } catch (err: any) {
      setError(err.message || "Failed to create user account.");
    } finally {
      setCreating(false);
    }
  };

  const handleConfirmToggleStatus = async () => {
    if (!statusUser) return;
    try {
      setUpdatingStatus(true);
      setError(null);
      const targetActive = !statusUser.is_active;
      await api.patch(`/api/users/${statusUser.id}/status`, {
        is_active: targetActive,
        reason: statusReason || "Administrative status toggle",
      });

      setSuccess(`Account '${statusUser.username}' successfully ${targetActive ? "activated" : "deactivated"}.`);
      setStatusUser(null);
      setStatusReason("");
      fetchUsers();
    } catch (err: any) {
      setError(err.message || "Failed to update account status.");
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleIssueSingleCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!singleRollNo.trim()) return;
    try {
      setSingleIssuing(true);
      setError(null);
      const res = await api.post<any>("/api/auth/student-otp/issue", {
        roll_no: singleRollNo.trim(),
        custom_code: singleCustomCode.trim() || null,
      });
      setSingleCodeResult({ roll_no: res.roll_no, access_code: res.access_code });
      setSuccess(`Issued passkey for candidate ${res.roll_no}.`);
      setSingleCustomCode("");
    } catch (err: any) {
      setError(err.message || "Failed to issue student code.");
    } finally {
      setSingleIssuing(false);
    }
  };

  const handleGenerateBulkCodes = async () => {
    try {
      setBulkIssuing(true);
      setError(null);
      const res = await api.post<any>("/api/users/student-codes/bulk", {
        branch: bulkBranch === "all" ? null : bulkBranch,
        limit: Number(bulkLimit),
      });
      setBulkRoster(res.roster || []);
      setSuccess(`Generated ${res.total_issued} one-time access codes ready for distribution.`);
    } catch (err: any) {
      setError(err.message || "Failed to generate bulk access codes.");
    } finally {
      setBulkIssuing(false);
    }
  };

  const handleCopyCode = (code: string, idx: number) => {
    navigator.clipboard.writeText(code);
    setCopiedCodeIndex(idx);
    setTimeout(() => setCopiedCodeIndex(null), 2000);
  };

  const handlePrintRoster = () => {
    window.print();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Users, Roles & Access Control</h1>
            <Badge variant="brand">Officer Authority (IM-101)</Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Provision coordinator accounts, recruiter read-only access with company link, and generate secure candidate access codes.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={fetchUsers}
            className="p-2 text-slate-600 hover:text-slate-900 bg-white border border-slate-200/80 rounded-xl hover:bg-slate-50 shadow-2xs transition-all cursor-pointer"
            title="Refresh accounts"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-sm transition-all cursor-pointer"
          >
            <UserPlus className="w-4 h-4" />
            <span>Create Account</span>
          </button>
        </div>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}
      {success && <AlertBanner type="success" message={success} onClose={() => setSuccess(null)} />}

      {/* Sub Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        <button
          type="button"
          onClick={() => setActiveSubTab("accounts")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
            activeSubTab === "accounts"
              ? "bg-slate-900 text-white shadow-2xs"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Staff & Recruiter Accounts ({users.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveSubTab("student_codes")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
            activeSubTab === "student_codes"
              ? "bg-slate-900 text-white shadow-2xs"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
          }`}
        >
          <Key className="w-4 h-4 text-emerald-500" />
          <span>Student One-Time Access Codes (LAN Authority)</span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* SUB TAB 1: ACCOUNTS LISTING                                              */}
      {/* ========================================================================= */}
      {activeSubTab === "accounts" && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="p-4 bg-slate-50/80 border-b border-slate-200 flex items-center justify-between text-xs">
            <span className="font-bold text-slate-700 uppercase tracking-wider">
              Registered System Accounts
            </span>
            <span className="text-slate-500 font-medium">All mutations logged to immutable audit ledger</span>
          </div>

          {loading ? (
            <div className="p-12 text-center text-slate-500 text-sm animate-pulse">
              Loading user credentials and roles...
            </div>
          ) : users.length === 0 ? (
            <div className="p-12 text-center text-slate-500 text-sm">
              No staff or recruiter accounts found. Click "Create Account" above to provision one.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
                  <th className="px-5 py-3.5">Username</th>
                  <th className="px-5 py-3.5">Email</th>
                  <th className="px-5 py-3.5">Role</th>
                  <th className="px-5 py-3.5">Linked Company</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-5 py-3.5 font-bold font-mono text-slate-900">{u.username}</td>
                    <td className="px-5 py-3.5 text-slate-600">{u.email}</td>
                    <td className="px-5 py-3.5">
                      <span
                        className={`px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${
                          u.role === "officer"
                            ? "bg-purple-100 text-purple-800 border border-purple-200"
                            : u.role === "coordinator"
                            ? "bg-blue-100 text-blue-800 border border-blue-200"
                            : "bg-emerald-100 text-emerald-800 border border-emerald-200"
                        }`}
                      >
                        {u.role.replace("_readonly", " (ReadOnly)")}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-slate-700 font-semibold">
                      {u.company_name ? (
                        <div className="flex items-center gap-1.5 text-emerald-700">
                          <Building className="w-3.5 h-3.5 shrink-0" />
                          <span>{u.company_name}</span>
                        </div>
                      ) : (
                        <span className="text-slate-400 font-mono text-[11px]">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      {u.is_active ? (
                        <span className="flex items-center gap-1 text-emerald-600 font-bold">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Active</span>
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-rose-500 font-bold">
                          <XCircle className="w-3.5 h-3.5" />
                          <span>Deactivated</span>
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      {u.role !== "officer" ? (
                        <button
                          type="button"
                          onClick={() => {
                            setStatusUser(u);
                            setStatusReason("");
                          }}
                          className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                            u.is_active
                              ? "bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200"
                              : "bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200"
                          }`}
                        >
                          {u.is_active ? "Deactivate" : "Activate"}
                        </button>
                      ) : (
                        <span className="text-slate-400 text-[11px] italic">Protected</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* SUB TAB 2: STUDENT ONE-TIME ACCESS CODES (SINGLE & BULK)                 */}
      {/* ========================================================================= */}
      {activeSubTab === "student_codes" && (
        <div className="space-y-6">
          {/* Card 1: Single Student Code Generation */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
            <div className="flex items-center gap-2">
              <Key className="w-5 h-5 text-emerald-600" />
              <h2 className="text-sm font-bold text-slate-900">Issue Individual Student Passkey</h2>
            </div>
            <p className="text-xs text-slate-500">
              Generates or resets a candidate's local Argon2 passkey for logging into the candidate portal.
            </p>

            <form onSubmit={handleIssueSingleCode} className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Candidate Roll Number <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. BT210001 or PIPE_001"
                  value={singleRollNo}
                  onChange={(e) => setSingleRollNo(e.target.value)}
                  className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold focus:bg-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Custom Code (Optional)
                </label>
                <input
                  type="text"
                  placeholder="Leave blank for random 6-digit PIN"
                  value={singleCustomCode}
                  onChange={(e) => setSingleCustomCode(e.target.value)}
                  className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold focus:bg-white"
                />
              </div>

              <button
                type="submit"
                disabled={singleIssuing}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-xs transition-all cursor-pointer disabled:opacity-50"
              >
                {singleIssuing ? "Generating..." : "Generate Passkey"}
              </button>
            </form>

            {singleCodeResult && (
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider block">
                    Access Code for {singleCodeResult.roll_no}
                  </span>
                  <span className="text-2xl font-black font-mono text-emerald-950 block mt-0.5 tracking-wider">
                    {singleCodeResult.access_code}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => handleCopyCode(singleCodeResult.access_code, -1)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl transition-all cursor-pointer"
                >
                  {copiedCodeIndex === -1 ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedCodeIndex === -1 ? "Copied" : "Copy Code"}</span>
                </button>
              </div>
            )}
          </div>

          {/* Card 2: Bulk Generation & Printable Slips */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <Printer className="w-5 h-5 text-blue-600" />
                  <h2 className="text-sm font-bold text-slate-900">Bulk Passkey Generation & Printable Slips</h2>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Produce batches of one-time login credentials categorized by engineering discipline for examination hall distribution.
                </p>
              </div>

              {bulkRoster.length > 0 && (
                <button
                  type="button"
                  onClick={handlePrintRoster}
                  className="flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl shadow-xs transition-all cursor-pointer"
                >
                  <Printer className="w-4 h-4" />
                  <span>Print Passkey Slips</span>
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end pt-2">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Filter by Discipline / Branch
                </label>
                <select
                  value={bulkBranch}
                  onChange={(e) => setBulkBranch(e.target.value)}
                  className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold focus:bg-white cursor-pointer"
                >
                  <option value="all">All Branches</option>
                  <option value="Computer Science and Engineering">Computer Science and Engineering</option>
                  <option value="Information Technology">Information Technology</option>
                  <option value="Data Science">Data Science</option>
                  <option value="Electronics and Communication Engineering">Electronics and Communication Engineering</option>
                  <option value="Electrical and Electronics Engineering">Electrical and Electronics Engineering</option>
                  <option value="Mechanical Engineering">Mechanical Engineering</option>
                  <option value="Civil Engineering">Civil Engineering</option>
                  <option value="Chemical Engineering">Chemical Engineering</option>
                  <option value="Biotechnology">Biotechnology</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Batch Batch Size Limit
                </label>
                <select
                  value={bulkLimit}
                  onChange={(e) => setBulkLimit(Number(e.target.value))}
                  className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold focus:bg-white cursor-pointer"
                >
                  <option value={25}>25 Candidates</option>
                  <option value={50}>50 Candidates</option>
                  <option value={100}>100 Candidates</option>
                  <option value={200}>200 Candidates</option>
                  <option value={500}>500 Candidates</option>
                </select>
              </div>

              <button
                type="button"
                onClick={handleGenerateBulkCodes}
                disabled={bulkIssuing}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl shadow-xs transition-all cursor-pointer disabled:opacity-50"
              >
                {bulkIssuing ? "Generating Batch..." : "Generate Batch Credentials"}
              </button>
            </div>

            {bulkRoster.length > 0 && (
              <div className="border border-slate-200 rounded-2xl overflow-hidden mt-4">
                <div className="p-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs font-bold text-slate-700">
                  <span>Batch Roster ({bulkRoster.length} Candidates)</span>
                  <span className="text-[11px] font-mono text-emerald-700 font-semibold">
                    100% Ready for Distribution
                  </span>
                </div>
                <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-100/70 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
                      <th className="px-4 py-2.5">Roll No</th>
                      <th className="px-4 py-2.5">Candidate Name</th>
                      <th className="px-4 py-2.5">Branch</th>
                      <th className="px-4 py-2.5">One-Time Passkey</th>
                      <th className="px-4 py-2.5 text-right no-print">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {bulkRoster.map((item, idx) => (
                      <tr key={item.roll_no} className="hover:bg-slate-50">
                        <td className="px-4 py-2.5 font-bold text-slate-900">{item.roll_no}</td>
                        <td className="px-4 py-2.5 font-sans font-semibold text-slate-800">{item.name}</td>
                        <td className="px-4 py-2.5 font-sans text-slate-600">{item.branch}</td>
                        <td className="px-4 py-2.5 font-black text-emerald-700 tracking-wider">
                          {item.access_code}
                        </td>
                        <td className="px-4 py-2.5 text-right no-print font-sans">
                          <button
                            type="button"
                            onClick={() => handleCopyCode(item.access_code, idx)}
                            className="p-1.5 hover:bg-slate-100 text-slate-500 hover:text-slate-900 rounded-lg transition-colors cursor-pointer"
                            title="Copy code"
                          >
                            {copiedCodeIndex === idx ? (
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 1: CREATE USER                                                      */}
      {/* ========================================================================= */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Provision System Account"
      >
        <form onSubmit={handleCreateUser} className="space-y-4 text-xs">
          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
              Username <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. coord_cse or rec_microsoft"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold text-slate-800 focus:bg-white"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
              Institutional Email Address <span className="text-rose-500">*</span>
            </label>
            <input
              type="email"
              required
              placeholder="e.g. coordinator@college.edu"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold text-slate-800 focus:bg-white"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
              Initial Password <span className="text-rose-500">*</span>
            </label>
            <input
              type="password"
              required
              minLength={6}
              placeholder="Minimum 6 characters"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold text-slate-800 focus:bg-white"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
              Account Role <span className="text-rose-500">*</span>
            </label>
            <select
              value={newRole}
              onChange={(e) => setNewRole(e.target.value as any)}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold text-slate-800 focus:bg-white cursor-pointer"
            >
              <option value="coordinator">Coordinator (Student data corrections, drive setup review)</option>
              <option value="recruiter_readonly">Recruiter (Read-only shortlist & schedule inspection)</option>
            </select>
          </div>

          {newRole === "recruiter_readonly" && (
            <div>
              <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
                Link Recruiter to Company <span className="text-rose-500">*</span>
              </label>
              <select
                required
                value={newCompanyId}
                onChange={(e) => setNewCompanyId(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold text-slate-800 focus:bg-white cursor-pointer"
              >
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.tier})
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
              Mandatory Officer Reason for Creation <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Approved by Head of T&P for Season 2026"
              value={creationReason}
              onChange={(e) => setCreationReason(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold text-slate-800 focus:bg-white"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsCreateModalOpen(false)}
              className="px-4 py-2 border border-slate-200 rounded-xl text-slate-600 font-bold hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={creating}
              className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white font-bold rounded-xl shadow-xs"
            >
              {creating ? "Creating..." : "Confirm & Create"}
            </button>
          </div>
        </form>
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL 2: CONFIRM STATUS TOGGLE WITH REASON                                */}
      {/* ========================================================================= */}
      <Modal
        isOpen={!!statusUser}
        onClose={() => setStatusUser(null)}
        title={`${statusUser?.is_active ? "Deactivate" : "Activate"} User Account`}
      >
        <div className="space-y-4 text-xs">
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-2.5 text-amber-900">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Security Confirmation Required</span>
              <p className="text-[11px] text-amber-800 mt-0.5">
                You are about to {statusUser?.is_active ? "disable" : "enable"} system access for user{" "}
                <strong>{statusUser?.username}</strong> ({statusUser?.role}).
              </p>
            </div>
          </div>

          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
              Mandatory Officer Reason <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Terminated semester assignment / coordinator rotation"
              value={statusReason}
              onChange={(e) => setStatusReason(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold text-slate-800 focus:bg-white"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setStatusUser(null)}
              className="px-4 py-2 border border-slate-200 rounded-xl text-slate-600 font-bold hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirmToggleStatus}
              disabled={updatingStatus || !statusReason.trim()}
              className={`px-4 py-2 font-bold rounded-xl text-white shadow-xs ${
                statusUser?.is_active
                  ? "bg-rose-600 hover:bg-rose-700"
                  : "bg-emerald-600 hover:bg-emerald-700"
              }`}
            >
              {updatingStatus ? "Processing..." : `Confirm ${statusUser?.is_active ? "Deactivation" : "Activation"}`}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
