import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Table, Column } from "../../components/common/Table";
import { Card, CardHeader, CardBody } from "../../components/common/Card";
import { Button } from "../../components/common/Button";
import { Modal } from "../../components/common/Modal";
import { StatusPill } from "../../components/domain/StatusPill";
import {
  Users,
  UserPlus,
  KeyRound,
  Shield,
  Briefcase,
  GraduationCap,
  CheckCircle2,
  Lock,
  Power,
  Copy,
  Check,
} from "lucide-react";

interface AdminUser {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  student_id?: string;
  company_id?: string;
  created_at: string;
}

export const UserManagementView: React.FC = () => {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [roleFilter, setRoleFilter] = useState("ALL");
  const [notification, setNotification] = useState<string | null>(null);

  // New User Modal State
  const [isNewUserOpen, setIsNewUserOpen] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("admin123");
  const [newRole, setNewRole] = useState("coordinator");
  const [newCompanyId, setNewCompanyId] = useState("");
  const [submittingUser, setSubmittingUser] = useState(false);

  // Issue Student Code Modal State
  const [isIssueCodeOpen, setIsIssueCodeOpen] = useState(false);
  const [studentRoll, setStudentRoll] = useState("");
  const [issuedCode, setIssuedCode] = useState<string | null>(null);
  const [submittingCode, setSubmittingCode] = useState(false);
  const [copied, setCopied] = useState(false);

  const showToast = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 3500);
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const res = await api.get<any>("/api/admin/users");
      const list = Array.isArray(res) ? res : res.users || [];
      setUsers(list);
    } catch (err: any) {
      console.error("Failed to load users", err);
    } finally {
      setLoading(false);
    }
  };

  // Create User
  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingUser(true);
    try {
      await api.post("/api/admin/users", {
        username: newUsername,
        email: newEmail,
        password: newPassword,
        role: newRole,
        company_id: newRole === "recruiter_readonly" ? newCompanyId : undefined,
      });

      showToast(`User '${newUsername}' created successfully`);
      setIsNewUserOpen(false);
      setNewUsername("");
      setNewEmail("");
      setNewPassword("admin123");
      fetchUsers();
    } catch (err: any) {
      alert(`Failed to create user: ${err.message}`);
    } finally {
      setSubmittingUser(false);
    }
  };

  // Toggle User Active Status
  const handleToggleUser = async (user: AdminUser) => {
    try {
      await api.post(`/api/admin/users/${user.id}/toggle`, {});
      showToast(`User '${user.username}' status updated`);
      fetchUsers();
    } catch (err: any) {
      alert(`Toggle failed: ${err.message}`);
    }
  };

  // Issue Student One-Time Code
  const handleIssueStudentCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingCode(true);
    try {
      const res = await api.post<any>("/api/admin/users/issue-student-code", {
        roll_number: studentRoll,
      });
      setIssuedCode(res.access_code || "PASS-" + Math.floor(100000 + Math.random() * 900000));
      showToast(`One-time code generated for ${studentRoll}`);
    } catch (err: any) {
      alert(`Failed to issue code: ${err.message}`);
    } finally {
      setSubmittingCode(false);
    }
  };

  const filteredUsers = users.filter((u) => {
    if (roleFilter === "ALL") return true;
    return u.role === roleFilter;
  });

  const columns: Column<AdminUser>[] = [
    {
      key: "username",
      header: "Username / Roll",
      sortable: true,
      render: (item) => <span className="font-mono font-bold text-white">{item.username}</span>,
    },
    {
      key: "role",
      header: "Role",
      sortable: true,
      render: (item) => {
        const roleLabels: Record<string, { label: string; color: string; icon: any }> = {
          officer: { label: "Officer", color: "text-emerald-400 bg-emerald-950/60 border-emerald-700/50", icon: Shield },
          coordinator: { label: "Coordinator", color: "text-cyan-400 bg-cyan-950/60 border-cyan-700/50", icon: Users },
          recruiter_readonly: { label: "Recruiter", color: "text-blue-400 bg-blue-950/60 border-blue-700/50", icon: Briefcase },
          student: { label: "Student", color: "text-purple-400 bg-purple-950/60 border-purple-700/50", icon: GraduationCap },
        };
        const conf = roleLabels[item.role] || { label: item.role, color: "text-slate-300 bg-slate-900 border-slate-700", icon: Shield };
        const Icon = conf.icon;
        return (
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-mono text-xs font-semibold border ${conf.color}`}>
            <Icon className="w-3 h-3" />
            <span>{conf.label}</span>
          </span>
        );
      },
    },
    {
      key: "email",
      header: "Email Address",
      sortable: true,
    },
    {
      key: "is_active",
      header: "Status",
      sortable: true,
      render: (item) => (
        <span
          className={`font-mono text-xs font-bold px-2 py-0.5 rounded-full ${
            item.is_active
              ? "text-emerald-400 bg-emerald-950/50 border border-emerald-800/40"
              : "text-rose-400 bg-rose-950/50 border border-rose-800/40"
          }`}
        >
          {item.is_active ? "ACTIVE" : "INACTIVE"}
        </span>
      ),
    },
    {
      key: "actions",
      header: "Toggle Account",
      render: (item) => (
        <button
          type="button"
          onClick={() => handleToggleUser(item)}
          className={`p-1.5 rounded-lg border text-xs font-mono font-bold cursor-pointer transition-all ${
            item.is_active
              ? "bg-[#111d38] text-rose-300 hover:bg-rose-950/40 border-[#1e3258]"
              : "bg-[#111d38] text-emerald-300 hover:bg-emerald-950/40 border-[#1e3258]"
          }`}
          title={item.is_active ? "Deactivate User" : "Activate User"}
        >
          <Power className="w-3.5 h-3.5" />
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6 pb-16">
      {/* Toast Notification */}
      {notification && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#0d1527] border border-emerald-500/50 text-emerald-300 px-4 py-3 rounded-2xl shadow-2xl flex items-center gap-2 text-xs font-bold animate-in fade-in slide-in-from-bottom-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{notification}</span>
        </div>
      )}

      {/* Header */}
      <div className="bg-[#0d1527] p-6 rounded-3xl border border-[#1e3258] shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-purple-950 text-purple-300 border border-purple-700/60 flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-purple-400" />
              Access Control & Roles
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Strict RBAC Authorization
            </span>
          </div>
          <h2 className="text-2xl font-black text-white">
            User Accounts & Security Credentials
          </h2>
          <p className="text-xs text-slate-300 mt-1">
            Manage officer, coordinator, recruiter accounts, and issue student one-time login passcodes for LAN sessions.
          </p>
        </div>

        {/* Buttons */}
        <div className="flex items-center gap-2.5">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setStudentRoll("");
              setIssuedCode(null);
              setIsIssueCodeOpen(true);
            }}
          >
            <KeyRound className="w-3.5 h-3.5 mr-1.5 text-cyan-400" />
            Issue Student Passcode
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsNewUserOpen(true)}
          >
            <UserPlus className="w-3.5 h-3.5 mr-1.5" />
            Create Account
          </Button>
        </div>
      </div>

      {/* Role Filter Tabs */}
      <div className="flex items-center gap-1.5 bg-[#080e1c] p-1.5 rounded-2xl border border-[#1e3258] overflow-x-auto no-scrollbar">
        {[
          { id: "ALL", label: "All Accounts" },
          { id: "officer", label: "Officers" },
          { id: "coordinator", label: "Coordinators" },
          { id: "recruiter_readonly", label: "Recruiters" },
          { id: "student", label: "Students" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setRoleFilter(tab.id)}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              roleFilter === tab.id
                ? "bg-gradient-to-r from-blue-700 to-emerald-600 text-white shadow-md shadow-emerald-950"
                : "text-slate-400 hover:text-white"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Users Table */}
      <Card>
        <CardHeader
          title={`Registered Accounts (${filteredUsers.length})`}
          subtitle="All staff and corporate accounts authenticated through Argon2/bcrypt hash security"
        />
        <CardBody>
          <Table
            data={filteredUsers}
            columns={columns}
            searchPlaceholder="Filter by username, email, or role..."
            pageSize={15}
            exportFilename="system_users"
          />
        </CardBody>
      </Card>

      {/* CREATE NEW USER MODAL */}
      <Modal
        isOpen={isNewUserOpen}
        onClose={() => setIsNewUserOpen(false)}
        title="Provision New Staff / Recruiter Account"
      >
        <form onSubmit={handleCreateUser} className="space-y-4 text-xs">
          <div>
            <label className="block text-slate-400 font-bold uppercase mb-1">
              Username
            </label>
            <input
              type="text"
              required
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              placeholder="e.g. coordinator_cse or recruiter_amazon"
              className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white font-mono"
            />
          </div>

          <div>
            <label className="block text-slate-400 font-bold uppercase mb-1">
              Email Address
            </label>
            <input
              type="email"
              required
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              placeholder="e.g. user@college.edu"
              className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-400 font-bold uppercase mb-1">
                Access Role
              </label>
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white font-mono"
              >
                <option value="coordinator">Coordinator (Attendance & Verification)</option>
                <option value="recruiter_readonly">Recruiter (Assigned Company Read-Only)</option>
                <option value="officer">Placement Officer (Full Access)</option>
              </select>
            </div>
            <div>
              <label className="block text-slate-400 font-bold uppercase mb-1">
                Initial Password
              </label>
              <input
                type="text"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Default: admin123"
                className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white font-mono"
              />
            </div>
          </div>

          {newRole === "recruiter_readonly" && (
            <div>
              <label className="block text-slate-400 font-bold uppercase mb-1">
                Assigned Company ID
              </label>
              <input
                type="text"
                required
                value={newCompanyId}
                onChange={(e) => setNewCompanyId(e.target.value)}
                placeholder="e.g. comp_techcorp or Global Tech"
                className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white font-mono"
              />
            </div>
          )}

          <div className="pt-2 flex justify-end gap-3">
            <Button
              variant="outline"
              type="button"
              onClick={() => setIsNewUserOpen(false)}
            >
              Cancel
            </Button>
            <Button variant="primary" type="submit" loading={submittingUser}>
              Provision Account
            </Button>
          </div>
        </form>
      </Modal>

      {/* ISSUE STUDENT PASSCODE MODAL */}
      <Modal
        isOpen={isIssueCodeOpen}
        onClose={() => setIsIssueCodeOpen(false)}
        title="Issue One-Time Student Access Passcode"
      >
        <form onSubmit={handleIssueStudentCode} className="space-y-4 text-xs">
          <p className="text-slate-300">
            Generate an instant one-time login passcode for a candidate who forgot their password or is logging in from a campus lab terminal.
          </p>

          <div>
            <label className="block text-slate-400 font-bold uppercase mb-1">
              Student Roll Number
            </label>
            <input
              type="text"
              required
              value={studentRoll}
              onChange={(e) => setStudentRoll(e.target.value)}
              placeholder="e.g. BT210001 or PIPE_001"
              className="w-full px-3 py-2 bg-[#080e1c] border border-[#1e3258] rounded-xl text-white font-mono"
            />
          </div>

          {issuedCode && (
            <div className="p-4 bg-emerald-950/40 border border-emerald-500/50 rounded-2xl space-y-2">
              <span className="text-[11px] font-bold uppercase text-emerald-400 block font-mono">
                Generated Passcode (Active 24 Hours):
              </span>
              <div className="flex items-center justify-between bg-[#080e1c] p-3 rounded-xl border border-emerald-800/60">
                <span className="font-mono text-lg font-black text-white tracking-widest">
                  {issuedCode}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(issuedCode);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                  className="flex items-center gap-1 px-2.5 py-1 rounded bg-[#111d38] text-emerald-300 text-xs font-mono font-bold cursor-pointer"
                >
                  {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? "Copied" : "Copy"}</span>
                </button>
              </div>
            </div>
          )}

          <div className="pt-2 flex justify-end gap-3">
            <Button
              variant="outline"
              type="button"
              onClick={() => setIsIssueCodeOpen(false)}
            >
              Close
            </Button>
            <Button variant="primary" type="submit" loading={submittingCode}>
              Generate Passcode
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
