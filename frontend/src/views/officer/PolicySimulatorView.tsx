import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Drive, Student } from "../../types";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  Cpu,
  Shield,
  FileCheck,
  AlertTriangle,
  CheckCircle,
  XCircle,
  HelpCircle,
  Briefcase,
  User,
  Sliders,
  RotateCcw,
  Sparkles,
} from "lucide-react";

interface PolicyDecision {
  status: "allowed" | "blocked" | "needs_review";
  clause_id: string;
  plain_english_reason: string;
  what_would_unblock: string;
  countable_offers_count: number;
  highest_current_ctc_lpa: number;
}

interface RuleResult {
  rule_id: string;
  rule_type: string;
  severity: "hard" | "advisory";
  status: "pass" | "fail" | "review";
  actual_value: any;
  required_value: any;
  data_source: string;
  student_explanation: string;
  officer_detail: string;
}

interface AcademicDecision {
  status: string;
  overall_student_reason: string;
  passed_rules: RuleResult[];
  failed_rules: RuleResult[];
  data_snapshot_hash: string;
}

interface SimulationResult {
  student: {
    id: string;
    roll_no: string;
    name: string;
    branch: string;
    cgpa: number;
    tenth_percentage: number;
    twelfth_percentage: number | null;
    diploma_percentage: number | null;
    active_backlogs: number;
    history_backlogs: number;
    existing_offers: Array<{
      company: string;
      ctc_lpa: number;
      fixed_pay_lpa: number | null;
      offer_date: string;
      source: string;
      status: string;
      is_dream: boolean;
    }>;
  };
  drive: {
    id: string;
    company_name: string;
    drive_date: string;
    ctc_lpa: number;
    fixed_pay_lpa: number | null;
  };
  policy_used: {
    id: string;
    name: string;
    max_total_offers: number;
    max_dream_offers: number;
    dream_threshold_lpa: number;
    allow_upgrade_to_dream: boolean;
    upgrade_ctc_multiplier: number;
    threshold_basis: string;
    is_threshold_inclusive: boolean;
    count_off_campus_offers: boolean;
    count_rejected_offers: boolean;
    count_revoked_offers: boolean;
    cooling_period_days: number;
  };
  policy_decision: PolicyDecision;
  academic_decision: AcademicDecision;
  combined_status: "ELIGIBLE" | "POLICY_BLOCKED" | "ACADEMICALLY_INELIGIBLE" | "NEEDS_REVIEW";
}

export const PolicySimulatorView: React.FC = () => {
  const [drives, setDrives] = useState<Drive[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState<string>("");
  const [selectedDriveId, setSelectedDriveId] = useState<string>("");
  const [selectedPolicyPreset, setSelectedPolicyPreset] = useState<string>("policy-001-strict-one-offer");

  // Configurable policy toggles
  const [maxTotalOffers, setMaxTotalOffers] = useState<number>(1);
  const [maxDreamOffers, setMaxDreamOffers] = useState<number>(1);
  const [dreamThreshold, setDreamThreshold] = useState<number>(10.0);
  const [allowUpgrade, setAllowUpgrade] = useState<boolean>(true);
  const [upgradeMultiplier, setUpgradeMultiplier] = useState<number>(1.0);
  const [isInclusive, setIsInclusive] = useState<boolean>(true);
  const [countOffCampus, setCountOffCampus] = useState<boolean>(true);
  const [coolingDays, setCoolingDays] = useState<number>(0);

  const [loading, setLoading] = useState<boolean>(false);
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [drvRes, stuRes] = await Promise.all([
          api.get<Drive[]>("/api/drives"),
          api.get<{ items: Student[] }>("/api/students?limit=200"),
        ]);
        const driveList = drvRes || [];
        setDrives(driveList);
        if (driveList.length > 0) {
          if (!selectedDriveId || !driveList.some((d) => d.id === selectedDriveId)) {
            setSelectedDriveId(driveList[0].id);
          }
        } else {
          setSelectedDriveId("");
        }

        const studentList = stuRes.items || [];
        setStudents(studentList);
        if (studentList.length > 0) setSelectedStudentId(studentList[0].id);
      } catch {
        setError("Failed to load drives or student records for simulator.");
      }
    };
    fetchData();
  }, []);

  const handlePresetChange = (presetId: string) => {
    setSelectedPolicyPreset(presetId);
    if (presetId === "policy-001-strict-one-offer") {
      setMaxTotalOffers(1);
      setMaxDreamOffers(1);
      setDreamThreshold(10.0);
      setAllowUpgrade(true);
      setUpgradeMultiplier(1.0);
      setIsInclusive(true);
      setCountOffCampus(true);
      setCoolingDays(0);
    } else if (presetId === "policy-002-progressive-multiplier") {
      setMaxTotalOffers(2);
      setMaxDreamOffers(2);
      setDreamThreshold(12.0);
      setAllowUpgrade(true);
      setUpgradeMultiplier(1.5);
      setIsInclusive(true);
      setCountOffCampus(true);
      setCoolingDays(0);
    } else if (presetId === "policy-003-tiered-quota") {
      setMaxTotalOffers(3);
      setMaxDreamOffers(2);
      setDreamThreshold(8.0);
      setAllowUpgrade(true);
      setUpgradeMultiplier(1.0);
      setIsInclusive(true);
      setCountOffCampus(false);
      setCoolingDays(0);
    }
  };

  const handleRunSimulation = async () => {
    if (!selectedStudentId || !selectedDriveId) {
      setError("Please select both a student and a recruitment drive.");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const overridePayload = {
        id: `custom-sim-${Date.now()}`,
        name: `Interactive Simulation (${selectedPolicyPreset})`,
        version: 1,
        max_total_offers: maxTotalOffers,
        max_dream_offers: maxDreamOffers,
        dream_threshold_lpa: dreamThreshold,
        allow_upgrade_to_dream: allowUpgrade,
        upgrade_ctc_multiplier: upgradeMultiplier,
        threshold_basis: "ctc",
        is_threshold_inclusive: isInclusive,
        count_off_campus_offers: countOffCampus,
        count_rejected_offers: false,
        count_revoked_offers: false,
        cooling_period_days: coolingDays,
      };

      const res = await api.post<SimulationResult>("/api/policies/simulate", {
        student_id: selectedStudentId,
        drive_id: selectedDriveId,
        override_policy: overridePayload,
      });

      setSimulationResult(res);
    } catch (err: any) {
      setError(err.message || "Simulation execution failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-indigo-50 text-indigo-700 rounded-xl">
              <Cpu className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">
              Interactive Policy & Eligibility Simulator
            </h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Simulate edge-case outcomes, test policy ambiguity toggles, and inspect pure-domain rule AST evaluation without mutating production state.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleRunSimulation}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-xl shadow-md shadow-brand-500/20 transition-all cursor-pointer disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            <span>{loading ? "Simulating..." : "Run Simulation"}</span>
          </button>
        </div>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}

      {/* Simulator Control Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Student & Drive Selection */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-2 text-xs font-black text-slate-900 uppercase tracking-wider pb-2 border-b border-slate-100">
            <User className="w-4 h-4 text-slate-500" />
            <span>Target Candidate & Drive</span>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-700 block mb-1">
              Select Candidate ({students.length} loaded)
            </label>
            <select
              value={selectedStudentId}
              onChange={(e) => setSelectedStudentId(e.target.value)}
              className="w-full text-xs font-medium border border-slate-300 rounded-xl px-3 py-2.5 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {students.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.roll_no} — {s.name} ({s.branch}, CGPA: {s.cgpa})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-700 block mb-1">
              Select Target Drive ({drives.length} drives)
            </label>
            <select
              value={selectedDriveId}
              onChange={(e) => setSelectedDriveId(e.target.value)}
              className="w-full text-xs font-medium border border-slate-300 rounded-xl px-3 py-2.5 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {drives.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.company_name} — {d.ctc_lpa} LPA ({d.drive_date})
                </option>
              ))}
            </select>
          </div>

          <div className="pt-2">
            <label className="text-xs font-bold text-slate-700 block mb-1">
              Policy Template Preset
            </label>
            <select
              value={selectedPolicyPreset}
              onChange={(e) => handlePresetChange(e.target.value)}
              className="w-full text-xs font-medium border border-slate-300 rounded-xl px-3 py-2.5 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="policy-001-strict-one-offer">Policy 1: Strict One-Offer (Dream &gt;= 10 LPA)</option>
              <option value="policy-002-progressive-multiplier">Policy 2: Progressive 1.5x Multiplier (Max 2 Offers)</option>
              <option value="policy-003-tiered-quota">Policy 3: Tier-Based Quota (Standard, Dream, Super-Dream)</option>
            </select>
          </div>
        </div>

        {/* Middle & Right Column: Policy Override Sandbox */}
        <div className="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex items-center gap-2 text-xs font-black text-slate-900 uppercase tracking-wider">
              <Sliders className="w-4 h-4 text-slate-500" />
              <span>Policy Ambiguity & Parameter Sandbox</span>
            </div>
            <button
              type="button"
              onClick={() => handlePresetChange(selectedPolicyPreset)}
              className="flex items-center gap-1 text-[11px] font-bold text-slate-500 hover:text-slate-800"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset to Preset Defaults</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Max Total Offers Allowed
              </label>
              <input
                type="number"
                min={1}
                max={5}
                value={maxTotalOffers}
                onChange={(e) => setMaxTotalOffers(Number(e.target.value))}
                className="w-full text-xs font-medium border border-slate-300 rounded-xl px-3 py-2 bg-slate-50 focus:bg-white"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Dream Threshold (CTC in LPA)
              </label>
              <input
                type="number"
                step="0.5"
                min={0}
                value={dreamThreshold}
                onChange={(e) => setDreamThreshold(Number(e.target.value))}
                className="w-full text-xs font-medium border border-slate-300 rounded-xl px-3 py-2 bg-slate-50 focus:bg-white"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Upgrade CTC Multiplier
              </label>
              <input
                type="number"
                step="0.1"
                min={1.0}
                value={upgradeMultiplier}
                onChange={(e) => setUpgradeMultiplier(Number(e.target.value))}
                className="w-full text-xs font-medium border border-slate-300 rounded-xl px-3 py-2 bg-slate-50 focus:bg-white"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Mandatory Cooling Window (Days)
              </label>
              <input
                type="number"
                min={0}
                value={coolingDays}
                onChange={(e) => setCoolingDays(Number(e.target.value))}
                className="w-full text-xs font-medium border border-slate-300 rounded-xl px-3 py-2 bg-slate-50 focus:bg-white"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
            <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200 cursor-pointer">
              <input
                type="checkbox"
                checked={allowUpgrade}
                onChange={(e) => setAllowUpgrade(e.target.checked)}
                className="rounded text-brand-600 focus:ring-brand-500"
              />
              <span className="text-xs font-medium text-slate-700">Allow Dream Upgrade</span>
            </label>

            <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200 cursor-pointer">
              <input
                type="checkbox"
                checked={isInclusive}
                onChange={(e) => setIsInclusive(e.target.checked)}
                className="rounded text-brand-600 focus:ring-brand-500"
              />
              <span className="text-xs font-medium text-slate-700">Threshold Inclusive (&gt;=)</span>
            </label>

            <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200 cursor-pointer">
              <input
                type="checkbox"
                checked={countOffCampus}
                onChange={(e) => setCountOffCampus(e.target.checked)}
                className="rounded text-brand-600 focus:ring-brand-500"
              />
              <span className="text-xs font-medium text-slate-700">Count Off-Campus Offers</span>
            </label>
          </div>
        </div>
      </div>

      {/* Simulation Results Display */}
      {simulationResult && (
        <div className="space-y-6 animate-fade-in">
          {/* Status Verdict Banner */}
          <div
            className={`p-6 rounded-2xl border shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
              simulationResult.combined_status === "ELIGIBLE"
                ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                : simulationResult.combined_status === "POLICY_BLOCKED"
                ? "bg-rose-50 border-rose-200 text-rose-900"
                : simulationResult.combined_status === "NEEDS_REVIEW"
                ? "bg-purple-50 border-purple-200 text-purple-900"
                : "bg-amber-50 border-amber-200 text-amber-900"
            }`}
          >
            <div className="flex items-start gap-4">
              <span className="p-3 bg-white/80 rounded-2xl shadow-xs mt-1">
                {simulationResult.combined_status === "ELIGIBLE" ? (
                  <CheckCircle className="w-8 h-8 text-emerald-600" />
                ) : simulationResult.combined_status === "POLICY_BLOCKED" ? (
                  <XCircle className="w-8 h-8 text-rose-600" />
                ) : (
                  <AlertTriangle className="w-8 h-8 text-amber-600" />
                )}
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-white/70">
                    Combined Verdict
                  </span>
                  <span className="font-mono text-xs opacity-80">
                    {simulationResult.drive.company_name} ({simulationResult.drive.ctc_lpa} LPA)
                  </span>
                </div>
                <h3 className="text-xl font-black tracking-tight mt-1">
                  {simulationResult.combined_status === "ELIGIBLE"
                    ? "Candidate is FULLY ELIGIBLE to Participate"
                    : simulationResult.combined_status === "POLICY_BLOCKED"
                    ? "Candidate is BLOCKED by Institutional Offer Policy"
                    : simulationResult.combined_status === "NEEDS_REVIEW"
                    ? "FLAGGED: Manual Verification Required"
                    : "Candidate FAILS Academic Cut-off Rules"}
                </h3>
                <p className="text-xs mt-1 font-medium opacity-90 max-w-2xl">
                  {simulationResult.policy_decision.plain_english_reason}
                </p>
              </div>
            </div>

            <div className="text-right sm:border-l sm:pl-6 border-current/20">
              <div className="text-[11px] uppercase tracking-wider font-bold opacity-70">Clause Cited</div>
              <div className="font-mono text-xs font-bold mt-0.5">{simulationResult.policy_decision.clause_id}</div>
              <div className="text-[11px] uppercase tracking-wider font-bold opacity-70 mt-2">Active Offers</div>
              <div className="text-xs font-bold">
                {simulationResult.policy_decision.countable_offers_count} held (Highest: {simulationResult.policy_decision.highest_current_ctc_lpa} LPA)
              </div>
            </div>
          </div>

          {/* Side-by-Side Breakdown: Policy vs Academic Rules */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Policy Enforcement Card */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-brand-600" />
                  <span className="text-xs font-black text-slate-900 uppercase tracking-wider">
                    Offer Policy Trace
                  </span>
                </div>
                <Badge
                  variant={
                    simulationResult.policy_decision.status === "allowed"
                      ? "success"
                      : simulationResult.policy_decision.status === "blocked"
                      ? "danger"
                      : "warning"
                  }
                >
                  {simulationResult.policy_decision.status.toUpperCase()}
                </Badge>
              </div>

              <div className="space-y-3 text-xs">
                <div>
                  <span className="font-bold text-slate-700 block">Decision Summary:</span>
                  <p className="text-slate-600 mt-0.5">{simulationResult.policy_decision.plain_english_reason}</p>
                </div>

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <span className="font-bold text-slate-700 block">Resolution / What Would Unblock:</span>
                  <p className="text-slate-600 mt-0.5 font-mono text-[11px]">
                    {simulationResult.policy_decision.what_would_unblock}
                  </p>
                </div>

                <div>
                  <span className="font-bold text-slate-700 block mb-1">Held Offers Breakdown:</span>
                  {simulationResult.student.existing_offers.length === 0 ? (
                    <span className="text-slate-400 italic">No existing offers on record.</span>
                  ) : (
                    <div className="space-y-1.5">
                      {simulationResult.student.existing_offers.map((off, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-2 bg-slate-50 rounded-lg border border-slate-100 text-[11px]"
                        >
                          <div>
                            <span className="font-bold text-slate-800">{off.company}</span>
                            <span className="text-slate-500 ml-1.5">({off.ctc_lpa} LPA)</span>
                            {off.is_dream && (
                              <span className="ml-1.5 px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded text-[10px] font-bold">
                                Dream
                              </span>
                            )}
                          </div>
                          <span className="text-slate-500">{off.source} • {off.status}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Academic Eligibility AST Card */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <FileCheck className="w-4 h-4 text-brand-600" />
                  <span className="text-xs font-black text-slate-900 uppercase tracking-wider">
                    Academic Rule AST Trace
                  </span>
                </div>
                <Badge
                  variant={
                    simulationResult.academic_decision.status === "eligible"
                      ? "success"
                      : simulationResult.academic_decision.status === "ineligible"
                      ? "danger"
                      : "warning"
                  }
                >
                  {simulationResult.academic_decision.status.toUpperCase()}
                </Badge>
              </div>

              <div className="space-y-3 text-xs">
                <div>
                  <span className="font-bold text-slate-700 block">Academic Summary:</span>
                  <p className="text-slate-600 mt-0.5">
                    {simulationResult.academic_decision.overall_student_reason}
                  </p>
                </div>

                <div className="space-y-2">
                  <span className="font-bold text-slate-700 block">Evaluated Rule Nodes:</span>

                  {/* Failed Rules */}
                  {simulationResult.academic_decision.failed_rules.map((rule, idx) => (
                    <div
                      key={`fail-${idx}`}
                      className="p-2.5 bg-rose-50/70 border border-rose-200 rounded-xl space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[10px] font-bold text-rose-800 uppercase">
                          {rule.rule_type} ({rule.severity})
                        </span>
                        <span className="text-[10px] font-bold text-rose-700 bg-white px-1.5 py-0.5 rounded">
                          FAILED
                        </span>
                      </div>
                      <p className="text-rose-900 text-[11px]">{rule.student_explanation}</p>
                      <div className="text-[10px] text-rose-700/80 font-mono">
                        source: {rule.data_source} | actual: {String(rule.actual_value)} | req: {String(rule.required_value)}
                      </div>
                    </div>
                  ))}

                  {/* Passed Rules */}
                  {simulationResult.academic_decision.passed_rules.map((rule, idx) => (
                    <div
                      key={`pass-${idx}`}
                      className="p-2.5 bg-emerald-50/50 border border-emerald-200 rounded-xl space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[10px] font-bold text-emerald-800 uppercase">
                          {rule.rule_type}
                        </span>
                        <span className="text-[10px] font-bold text-emerald-700 bg-white px-1.5 py-0.5 rounded">
                          PASSED
                        </span>
                      </div>
                      <p className="text-emerald-900 text-[11px]">{rule.student_explanation}</p>
                    </div>
                  ))}
                </div>

                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400 font-mono">
                  <span>Hash: {simulationResult.academic_decision.data_snapshot_hash.slice(0, 16)}...</span>
                  <span>Pure Domain Deterministic</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
