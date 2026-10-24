import React, { useState } from "react";
import { Modal } from "../common/Modal";
import {
  Users,
  FileText,
  Sliders,
  Calendar,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  CheckCircle,
} from "lucide-react";

interface GuidedTourModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigateToTab?: (tabId: string) => void;
}

export const GuidedTourModal: React.FC<GuidedTourModalProps> = ({
  isOpen,
  onClose,
  onNavigateToTab,
}) => {
  const [step, setStep] = useState(0);

  const steps = [
    {
      title: "Welcome to the Placement Engine",
      icon: <Users className="w-8 h-8 text-emerald-400" />,
      content:
        "Manage 40 to 120 campus recruitment drives entirely offline. All student academic records, company cut-offs, college offer policies, and interview schedules are computed locally with zero cloud dependencies.",
      highlight: "Step 1: Import your student batch roster with automatic column mapping.",
      targetTab: "students",
    },
    {
      title: "Paste or Upload Drive Announcements",
      icon: <FileText className="w-8 h-8 text-sky-400" />,
      content:
        "No manual re-typing. Paste messy email announcements or drop PDFs/DOCXs. Our offline extractor identifies CGPA cut-offs, branch aliases, backlogs, and gap limits, and presents them in a side-by-side review window.",
      highlight: "Step 2: Review extracted fields with exact quotation provenance.",
      targetTab: "create_drive",
    },
    {
      title: "Visual Rule Builder & College Policies",
      icon: <Sliders className="w-8 h-8 text-indigo-400" />,
      content:
        "Tweak requirements with simple sliders and checkboxes. Watch the eligible student counter update in real-time. Layer institutional offer rules ('one offer and you are out', dream company CTC exceptions) automatically.",
      highlight: "Step 3: Instant live candidate count without guessing.",
      targetTab: "rule_editor",
    },
    {
      title: "Clash-Free Interview & Test Scheduling",
      icon: <Calendar className="w-8 h-8 text-emerald-400" />,
      content:
        "Our Google OR-Tools CP-SAT engine schedules hundreds of students across multiple rooms and panels in seconds with mathematically proven ZERO overlapping student or room clashes.",
      highlight: "Step 4: Look for the green '0 Clashes Verified' badge.",
      targetTab: "schedule",
    },
    {
      title: "What-If Simulation & Safe Publishing",
      icon: <Sparkles className="w-8 h-8 text-amber-400" />,
      content:
        "Before publishing a schedule to students and recruiters, test changes in-memory. See computed headlines like 'Lowering cut-off from 7.0 to 6.5 adds 38 students; 6 clash with Test B' before committing.",
      highlight: "Step 5: Safe versioned publication with instant rollback protection.",
      targetTab: "what_if",
    },
  ];

  const current = steps[step];

  const handleNext = () => {
    if (step < steps.length - 1) {
      setStep(step + 1);
    } else {
      onClose();
    }
  };

  const handleJump = () => {
    if (onNavigateToTab && current.targetTab) {
      onNavigateToTab(current.targetTab);
    }
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Placement Officer Quick-Start Guide"
      maxWidth="lg"
      footer={
        <div className="flex items-center justify-between w-full">
          <div className="flex gap-1.5">
            {steps.map((_, i) => (
              <span
                key={i}
                className={`h-2 rounded-full transition-all ${
                  i === step
                    ? "w-6 bg-gradient-to-r from-blue-500 to-emerald-400"
                    : "w-2 bg-[#1e3258]"
                }`}
              />
            ))}
          </div>
          <div className="flex items-center gap-2">
            {step > 0 && (
              <button
                onClick={() => setStep(step - 1)}
                className="px-3 py-1.5 text-xs font-semibold text-slate-300 hover:text-white hover:bg-[#111d38] border border-[#1b2b4d] rounded-xl flex items-center gap-1 transition-colors cursor-pointer"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Back
              </button>
            )}
            <button
              onClick={handleJump}
              className="px-3 py-1.5 text-xs font-semibold text-emerald-300 bg-emerald-950/80 hover:bg-emerald-900/80 border border-emerald-800/60 rounded-xl transition-colors cursor-pointer"
            >
              Open This View
            </button>
            <button
              onClick={handleNext}
              className="px-4 py-1.5 text-xs font-bold text-white bg-gradient-to-r from-blue-600 via-teal-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 border border-emerald-400/40 rounded-xl shadow-xs flex items-center gap-1 transition-all cursor-pointer"
            >
              {step === steps.length - 1 ? (
                <>
                  <CheckCircle className="w-3.5 h-3.5" /> Finish
                </>
              ) : (
                <>
                  Next <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </div>
      }
    >
      <div className="space-y-4 py-2">
        <div className="w-16 h-16 rounded-2xl bg-[#111d38] border border-[#1b2b4d] flex items-center justify-center mx-auto mb-2 shadow-inner">
          {current.icon}
        </div>
        <div className="text-center">
          <h3 className="text-lg font-bold text-white">{current.title}</h3>
          <p className="text-sm text-slate-300 mt-2 leading-relaxed">{current.content}</p>
        </div>
        <div className="p-3 bg-emerald-950/60 border border-emerald-800/60 rounded-xl text-xs font-semibold text-emerald-200 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{current.highlight}</span>
        </div>
      </div>
    </Modal>
  );
};
