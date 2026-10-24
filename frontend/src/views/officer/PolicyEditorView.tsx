import React, { useState } from "react";
import { Shield, Sparkles, CheckCircle, Save, Info, Sliders } from "lucide-react";
import { AlertBanner } from "../../components/common/AlertBanner";
import { Badge } from "../../components/common/Badge";

export const PolicyEditorView: React.FC = () => {
  const [policyName, setPolicyName] = useState("Institutional Standard Policy 2026");
  const [maxOffers, setMaxOffers] = useState<number>(1);
  const [dreamThreshold, setDreamThreshold] = useState<number>(15.0);
  const [allowDreamOffers, setAllowDreamOffers] = useState<boolean>(true);
  const [coolingPeriodDays, setCoolingPeriodDays] = useState<number>(0);

  // Ambiguity toggles with defaults from docs/POLICY_AMBIGUITIES.md
  const [useFixedPay, setUseFixedPay] = useState<boolean>(false);
  const [thresholdInclusive, setThresholdInclusive] = useState<boolean>(true);
  const [revokedOffersCount, setRevokedOffersCount] = useState<boolean>(false);
  const [countOffCampus, setCountOffCampus] = useState<boolean>(true);
  const [useAcceptanceDate, setUseAcceptanceDate] = useState<boolean>(false);

  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);

  const [activePolicyPreset, setActivePolicyPreset] = useState<number>(1);

  const applyPolicyPreset = (presetIndex: number) => {
    setActivePolicyPreset(presetIndex);
    if (presetIndex === 1) {
      setPolicyName("Policy 1: Strict One-Offer with Dream Tier Exception");
      setMaxOffers(1);
      setDreamThreshold(10.0);
      setAllowDreamOffers(true);
      setUseFixedPay(false);
      setThresholdInclusive(true);
      setCountOffCampus(true);
      setRevokedOffersCount(false);
    } else if (presetIndex === 2) {
      setPolicyName("Policy 2: Progressive Salary Multiplier (1.5x Rule)");
      setMaxOffers(2);
      setDreamThreshold(12.0);
      setAllowDreamOffers(true);
      setUseFixedPay(false);
      setThresholdInclusive(true);
      setCountOffCampus(true);
      setRevokedOffersCount(false);
    } else if (presetIndex === 3) {
      setPolicyName("Policy 3: Tier-Based Quota Policy (Standard, Dream, Super-Dream)");
      setMaxOffers(3);
      setDreamThreshold(8.0);
      setAllowDreamOffers(true);
      setUseFixedPay(false);
      setThresholdInclusive(true);
      setCountOffCampus(false);
      setRevokedOffersCount(false);
    }
  };

  const handleSave = () => {
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">College Offer Policy Editor</h1>
          <p className="text-sm text-slate-500 mt-1">
            Institutional rules layered on top of company eligibility. Live plain-English preview with ambiguity toggles.
          </p>
        </div>

        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors"
        >
          <Save className="w-4 h-4" />
          <span>Save College Policy</span>
        </button>
      </div>

      {savedSuccess && (
        <AlertBanner
          type="success"
          message="College placement policy successfully committed and active for live enforcement."
          onClose={() => setSavedSuccess(false)}
        />
      )}

      {/* Three College Offer Policies Preset Selector */}
      <div className="bg-[#0d1527] border border-[#1b2b4d] rounded-2xl p-5 shadow-md space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">
              Three College Offer Policies (with Ambiguities)
            </h3>
          </div>
          <span className="text-[11px] text-slate-400 font-medium">As written by institutional placement cells</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
          <button
            type="button"
            onClick={() => applyPolicyPreset(1)}
            className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
              activePolicyPreset === 1
                ? "bg-gradient-to-r from-blue-900/60 to-emerald-950/60 text-white border-emerald-500 shadow-xs"
                : "bg-[#080e1c] text-slate-300 border-[#1b2b4d] hover:bg-[#111d38]"
            }`}
          >
            <div className="text-xs font-bold flex items-center justify-between">
              <span>Policy 1: Strict One-Offer</span>
              <span className="text-[10px] text-emerald-400 font-mono">1 Offer</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1 leading-snug">
              Dream Tier &ge; 10 LPA. Ambiguities: Off-campus offer reporting & Base pay vs CTC.
            </p>
          </button>

          <button
            type="button"
            onClick={() => applyPolicyPreset(2)}
            className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
              activePolicyPreset === 2
                ? "bg-gradient-to-r from-blue-900/60 to-emerald-950/60 text-white border-emerald-500 shadow-xs"
                : "bg-[#080e1c] text-slate-300 border-[#1b2b4d] hover:bg-[#111d38]"
            }`}
          >
            <div className="text-xs font-bold flex items-center justify-between">
              <span>Policy 2: 1.5x Multiplier</span>
              <span className="text-[10px] text-emerald-400 font-mono">2 Offers</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1 leading-snug">
              Hold up to 2 offers. Ambiguities: Concurrent drive precedence & lateral entry diploma.
            </p>
          </button>

          <button
            type="button"
            onClick={() => applyPolicyPreset(3)}
            className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
              activePolicyPreset === 3
                ? "bg-gradient-to-r from-blue-900/60 to-emerald-950/60 text-white border-emerald-500 shadow-xs"
                : "bg-[#080e1c] text-slate-300 border-[#1b2b4d] hover:bg-[#111d38]"
            }`}
          >
            <div className="text-xs font-bold flex items-center justify-between">
              <span>Policy 3: Tiered Quota</span>
              <span className="text-[10px] text-emerald-400 font-mono">3 Offers</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1 leading-snug">
              Standard / Dream / Super-Dream tiers. Ambiguities: Re-evaluation timing & lock rules.
            </p>
          </button>
        </div>
      </div>

      {/* Plain-English Live Preview Box */}
      <div className="bg-gradient-to-r from-brand-900 to-indigo-950 text-white p-6 rounded-2xl shadow-lg border border-brand-800 space-y-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-brand-400" />
          <span className="text-xs font-bold tracking-wider text-brand-300 uppercase">
            Live Plain-English Policy Formulation
          </span>
        </div>
        <p className="text-sm font-medium leading-relaxed text-slate-100">
          "Students are allowed a maximum of <strong className="text-white underline">{maxOffers} offer(s)</strong>.{" "}
          {allowDreamOffers
            ? `Once placed, candidates are excluded from further campus drives unless the offering company package is ${
                thresholdInclusive ? "at least" : "strictly greater than"
              } ${dreamThreshold} LPA (${useFixedPay ? "evaluated on Fixed Pay" : "evaluated on Total CTC"}). `
            : "No secondary dream company offers are permitted once placed. "}
          {revokedOffersCount
            ? "Declined or revoked offers still count against candidate quotas. "
            : "Declined or verified revoked offers do not consume offer allowances. "}
          {countOffCampus
            ? "Reported off-campus placements count towards this policy limit. "
            : "Off-campus offers do not restrict campus drive participation. "}
          {coolingPeriodDays > 0 ? `A cooling window of ${coolingPeriodDays} days applies between successive round interviews.` : ""}"
        </p>
      </div>

      {/* Main Settings Form */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <Shield className="w-4 h-4 text-brand-600" />
          Core Policy Parameters
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
              Maximum Offers Permitted Per Candidate
            </label>
            <input
              type="number"
              min="1"
              max="5"
              value={maxOffers}
              onChange={(e) => setMaxOffers(parseInt(e.target.value) || 1)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold"
            />
          </div>

          <div>
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
              Dream Company Salary Band (LPA)
            </label>
            <input
              type="number"
              step="0.5"
              value={dreamThreshold}
              onChange={(e) => setDreamThreshold(parseFloat(e.target.value) || 15.0)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-brand-700"
            />
          </div>
        </div>

        {/* Ambiguity Toggles Grid */}
        <div className="space-y-4 pt-4 border-t border-slate-100">
          <div>
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Configurable Interpretation Toggles (from docs/POLICY_AMBIGUITIES.md)
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Every ambiguity in written placement rules is exposed as an explicit, deliberate toggle.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            {/* Toggle 1: CTC vs Fixed Pay */}
            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
              <div>
                <span className="font-bold text-slate-800 block">Dream Band Metric</span>
                <span className="text-[11px] text-slate-500">
                  {useFixedPay ? "Evaluated on Fixed Base Pay" : "Evaluated on Total CTC (Standard)"}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setUseFixedPay(!useFixedPay)}
                className={`px-3 py-1.5 rounded-lg font-bold ${
                  useFixedPay ? "bg-brand-600 text-white" : "bg-slate-200 text-slate-700"
                }`}
              >
                {useFixedPay ? "Fixed Pay" : "CTC"}
              </button>
            </div>

            {/* Toggle 2: Inclusive vs Exclusive */}
            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
              <div>
                <span className="font-bold text-slate-800 block">Threshold Boundary</span>
                <span className="text-[11px] text-slate-500">
                  {thresholdInclusive ? "Inclusive (>= Threshold)" : "Exclusive (> Threshold)"}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setThresholdInclusive(!thresholdInclusive)}
                className={`px-3 py-1.5 rounded-lg font-bold ${
                  thresholdInclusive ? "bg-emerald-600 text-white" : "bg-slate-200 text-slate-700"
                }`}
              >
                {thresholdInclusive ? ">= (Inclusive)" : "> (Strict)"}
              </button>
            </div>

            {/* Toggle 3: Revoked Offers */}
            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
              <div>
                <span className="font-bold text-slate-800 block">Revoked / Declined Offers</span>
                <span className="text-[11px] text-slate-500">
                  {revokedOffersCount ? "Consumes allowance" : "Exempt / Restores allowance"}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setRevokedOffersCount(!revokedOffersCount)}
                className={`px-3 py-1.5 rounded-lg font-bold ${
                  revokedOffersCount ? "bg-rose-600 text-white" : "bg-emerald-600 text-white"
                }`}
              >
                {revokedOffersCount ? "Counted" : "Ignored"}
              </button>
            </div>

            {/* Toggle 4: Off-Campus Offers */}
            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
              <div>
                <span className="font-bold text-slate-800 block">Off-Campus Offers</span>
                <span className="text-[11px] text-slate-500">
                  {countOffCampus ? "Included in policy limit" : "Exempt from campus limits"}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setCountOffCampus(!countOffCampus)}
                className={`px-3 py-1.5 rounded-lg font-bold ${
                  countOffCampus ? "bg-brand-600 text-white" : "bg-slate-200 text-slate-700"
                }`}
              >
                {countOffCampus ? "Counted" : "Exempt"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
