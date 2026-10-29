import React, { useState } from "react";
import { Button } from "../../components/common/Button";
import { Input } from "../../components/common/Input";
import { Select } from "../../components/common/Select";
import { MultiSelect } from "../../components/common/MultiSelect";
import { DatePicker } from "../../components/common/DatePicker";
import { Table, Column } from "../../components/common/Table";
import { Card, CardHeader, CardBody, CardFooter } from "../../components/common/Card";
import { Tabs } from "../../components/common/Tabs";
import { ConfirmDialog } from "../../components/common/ConfirmDialog";
import { Skeleton } from "../../components/common/Skeleton";
import { Stepper } from "../../components/common/Stepper";
import { Timeline, TimelineEvent } from "../../components/common/Timeline";
import { DiffView } from "../../components/common/DiffView";
import { FileDropzone } from "../../components/common/FileDropzone";
import { ReasonLine } from "../../components/domain/ReasonLine";
import { ReasonTrace, RuleCriterionResult } from "../../components/domain/ReasonTrace";
import { StatusPill } from "../../components/domain/StatusPill";
import { ClashBadge } from "../../components/domain/ClashBadge";
import { VersionBadge } from "../../components/domain/VersionBadge";
import { SourceBadge } from "../../components/domain/SourceBadge";
import { ScheduleGrid, ScheduleAllocation } from "../../components/domain/ScheduleGrid";
import { Sparkles, Layers, ShieldCheck, CheckCircle2 } from "lucide-react";

export const ComponentsShowcaseView: React.FC = () => {
  const [activeCategory, setActiveCategory] = useState<"common" | "domain">("domain");
  const [inputValue, setInputValue] = useState("");
  const [selectValue, setSelectValue] = useState("option1");
  const [multiSelectValue, setMultiSelectValue] = useState<string[]>(["CSE", "IT"]);
  const [dateValue, setDateValue] = useState("2026-10-25");
  const [showConfirm, setShowConfirm] = useState(false);
  const [stepperStep, setStepperStep] = useState(1);

  // Sample data for Table
  interface DemoStudent {
    roll: string;
    name: string;
    branch: string;
    cgpa: number;
    status: string;
  }
  const sampleStudents: DemoStudent[] = [
    { roll: "BT21001", name: "Aarav Sharma", branch: "CSE", cgpa: 8.9, status: "ELIGIBLE" },
    { roll: "BT21002", name: "Pooja Patel", branch: "IT", cgpa: 7.4, status: "NOT_ELIGIBLE" },
    { roll: "BT21003", name: "Rohan Varma", branch: "ECE", cgpa: 8.2, status: "ELIGIBLE" },
    { roll: "BT21004", name: "Ananya Rao", branch: "ME", cgpa: 6.8, status: "NOT_ELIGIBLE" },
  ];

  const tableColumns: Column<DemoStudent>[] = [
    { key: "roll", header: "Roll No", sortable: true },
    { key: "name", header: "Student Name", sortable: true },
    { key: "branch", header: "Branch", sortable: true },
    { key: "cgpa", header: "CGPA", sortable: true },
    {
      key: "status",
      header: "Status",
      render: (item) => <StatusPill status={item.status} size="sm" />,
    },
  ];

  // Sample data for ReasonTrace
  const sampleCriteria: RuleCriterionResult[] = [
    {
      ruleName: "Minimum CGPA",
      criterion: "cgpa",
      operator: ">=",
      threshold: 7.5,
      actualValue: 8.42,
      passed: true,
      explanation: "Student CGPA (8.42) meets or exceeds drive requirement (7.50)",
    },
    {
      ruleName: "Active Backlogs",
      criterion: "backlogs",
      operator: "<=",
      threshold: 0,
      actualValue: 0,
      passed: true,
      explanation: "No active backlogs recorded",
    },
    {
      ruleName: "Allowed Departments",
      criterion: "branch",
      operator: "in",
      threshold: ["CSE", "IT", "ECE"],
      actualValue: "CSE",
      passed: true,
      explanation: "Department 'CSE' is in eligible branch roster",
    },
    {
      ruleName: "Max Existing Offers (Dream Policy)",
      criterion: "existing_offers",
      operator: "<=",
      threshold: 1,
      actualValue: 0,
      passed: true,
      isPolicy: true,
      explanation: "Candidate has 0 offers, eligible for Tier-1 Dream company",
    },
  ];

  // Sample allocations for ScheduleGrid
  const sampleAllocations: ScheduleAllocation[] = [
    {
      id: "alloc-1",
      studentName: "Aarav Sharma",
      rollNumber: "BT21001",
      companyName: "TechCorp Labs",
      room: "Interview Lab 101",
      timeSlot: "09:00 - 09:45",
      status: "scheduled",
    },
    {
      id: "alloc-2",
      studentName: "Rohan Varma",
      rollNumber: "BT21003",
      companyName: "Microsoft IDC",
      room: "Lab 102",
      timeSlot: "09:00 - 09:45",
      status: "scheduled",
    },
    {
      id: "alloc-3",
      studentName: "Aarav Sharma",
      rollNumber: "BT21001",
      companyName: "Amazon Dev",
      room: "Conference Room A",
      timeSlot: "09:00 - 09:45",
      isClash: true, // Simulating a clash for Aarav!
      status: "scheduled",
    },
    {
      id: "alloc-4",
      studentName: "Pooja Patel",
      rollNumber: "BT21002",
      companyName: "Goldman Sachs",
      room: "Interview Lab 101",
      timeSlot: "10:45 - 11:30",
      status: "scheduled",
    },
  ];

  // Sample timeline events
  const timelineEvents: TimelineEvent[] = [
    {
      id: "1",
      title: "Drive Announcement Published",
      description: "Software Engineer drive published with 7.5 CGPA cut-off.",
      timestamp: "10:00 AM",
      actor: "Placement Officer",
      type: "create",
    },
    {
      id: "2",
      title: "Eligibility Batch Run",
      description: "Deterministic engine evaluated 1,842 candidates: 412 eligible.",
      timestamp: "10:15 AM",
      actor: "Placement Engine",
      type: "update",
    },
    {
      id: "3",
      title: "Schedule Optimized (0 Clashes)",
      description: "Allocated 412 candidates across 4 interview panels.",
      timestamp: "11:00 AM",
      actor: "Scheduler",
      type: "status_change",
    },
  ];

  return (
    <div className="space-y-8 pb-16">
      {/* Top Banner */}
      <div className="bg-[#0d1527] border border-[#1e3258] rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-600/50 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              Design System Showcase (/dev/components)
            </span>
            <span className="text-xs text-slate-400 font-mono">100% Offline • Zero External CDNs</span>
          </div>
          <h2 className="text-2xl font-black text-white">
            Placement Engine Component System
          </h2>
          <p className="text-sm text-slate-300 mt-1 max-w-2xl">
            Live catalog of enterprise dark UI components, domain-specific visual primitives, and responsive interactive widgets meeting Prompt 0 specification.
          </p>
        </div>

        {/* Category Tabs */}
        <div className="mt-6 flex items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveCategory("domain")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              activeCategory === "domain"
                ? "bg-gradient-to-r from-blue-600 to-emerald-600 text-white shadow-md shadow-emerald-950"
                : "bg-[#111d38] text-slate-300 hover:text-white border border-[#1e3258]"
            }`}
          >
            Domain Components (Placement Primitives)
          </button>
          <button
            type="button"
            onClick={() => setActiveCategory("common")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              activeCategory === "common"
                ? "bg-gradient-to-r from-blue-600 to-emerald-600 text-white shadow-md shadow-emerald-950"
                : "bg-[#111d38] text-slate-300 hover:text-white border border-[#1e3258]"
            }`}
          >
            Common Design System Primitives
          </button>
        </div>
      </div>

      {/* DOMAIN COMPONENTS SHOWCASE */}
      {activeCategory === "domain" && (
        <div className="space-y-8">
          {/* Section: ReasonLine & StatusPills */}
          <Card>
            <CardHeader
              title="1. ReasonLine & StatusPill"
              subtitle="Plain-English 3-part decisions (status, why, what to do next) and standardized badges"
            />
            <CardBody className="space-y-6">
              <div className="space-y-3">
                <h4 className="text-xs font-mono font-bold uppercase text-slate-400">ReasonLine Variants</h4>
                <ReasonLine
                  status="Eligible"
                  why="CGPA 8.42 >= 7.50 and no active backlogs."
                  whatNext="Submit your slot preference before 6:00 PM."
                  variant="success"
                />
                <ReasonLine
                  status="Not Eligible"
                  why="Department Mechanical Engineering (ME) is not invited by recruiter."
                  whatNext="Check open pool drives or request an eligibility waiver with your coordinator."
                  variant="danger"
                />
                <ReasonLine
                  status="Pending Verification"
                  why="Semester 6 marksheet uploaded awaiting coordinator sign-off."
                  whatNext="Visit Placement Cell Room 204 or wait for batch approval."
                  variant="warning"
                />
              </div>

              <div className="pt-4 border-t border-[#1e3258]/60 space-y-3">
                <h4 className="text-xs font-mono font-bold uppercase text-slate-400">StatusPills</h4>
                <div className="flex flex-wrap gap-2">
                  <StatusPill status="ELIGIBLE" />
                  <StatusPill status="NOT_ELIGIBLE" />
                  <StatusPill status="PENDING" />
                  <StatusPill status="OVERRIDDEN" />
                  <StatusPill status="PUBLISHED" />
                  <StatusPill status="IN_PROGRESS" />
                  <StatusPill status="PRESENT" />
                  <StatusPill status="ABSENT" />
                  <StatusPill status="LATE" />
                  <StatusPill status="DRAFT" />
                </div>
              </div>
            </CardBody>
          </Card>

          {/* Section: ReasonTrace */}
          <Card>
            <CardHeader
              title="2. ReasonTrace"
              subtitle="Deterministic rule-by-rule evaluation breakdown with candidate values vs threshold"
            />
            <CardBody>
              <ReasonTrace
                studentName="Aarav Sharma"
                rollNumber="BT21001"
                driveName="TechCorp SWE 2026"
                isEligible={true}
                overallReason="Candidate satisfies all 4 required eligibility and policy criteria."
                criteria={sampleCriteria}
              />
            </CardBody>
          </Card>

          {/* Section: ClashBadge, VersionBadge & SourceBadge */}
          <Card>
            <CardHeader
              title="3. ClashBadge, VersionBadge & SourceBadge"
              subtitle="Operational badges verifying constraint scheduling, rule versioning, and data provenance"
            />
            <CardBody className="space-y-6">
              <div>
                <h4 className="text-xs font-mono font-bold uppercase text-slate-400 mb-2">Clash Badges</h4>
                <div className="flex flex-wrap items-center gap-3">
                  <ClashBadge clashCount={0} />
                  <ClashBadge clashCount={3} />
                  <ClashBadge clashCount={1} label="1 Room Conflict" />
                </div>
              </div>

              <div className="pt-4 border-t border-[#1e3258]/60">
                <h4 className="text-xs font-mono font-bold uppercase text-slate-400 mb-2">Version Badges</h4>
                <div className="flex flex-wrap items-center gap-3">
                  <VersionBadge version="1.0" status="active" />
                  <VersionBadge version="2.0" status="draft" />
                  <VersionBadge version="0.9" status="superseded" />
                  <VersionBadge version="0.8" status="archived" />
                </div>
              </div>

              <div className="pt-4 border-t border-[#1e3258]/60">
                <h4 className="text-xs font-mono font-bold uppercase text-slate-400 mb-2">Provenance Source Badges</h4>
                <div className="flex flex-wrap items-center gap-3">
                  <SourceBadge source="erp" />
                  <SourceBadge source="csv_import" />
                  <SourceBadge source="coordinator_verified" />
                  <SourceBadge source="officer_override" />
                  <SourceBadge source="self_reported" />
                </div>
              </div>
            </CardBody>
          </Card>

          {/* Section: ScheduleGrid */}
          <Card>
            <CardHeader
              title="4. ScheduleGrid"
              subtitle="Room x Time slot matrix with live clash detection and candidate placement"
            />
            <CardBody>
              <ScheduleGrid
                allocations={sampleAllocations}
                onSelectAllocation={(alloc) =>
                  alert(`Selected interview for ${alloc.studentName} at ${alloc.timeSlot}`)
                }
              />
            </CardBody>
          </Card>
        </div>
      )}

      {/* COMMON DESIGN SYSTEM SHOWCASE */}
      {activeCategory === "common" && (
        <div className="space-y-8">
          {/* Buttons & Inputs */}
          <Card>
            <CardHeader title="Buttons & Form Controls" subtitle="Standard interactive form inputs with high-contrast accessibility" />
            <CardBody className="space-y-6">
              <div>
                <h4 className="text-xs font-mono font-bold uppercase text-slate-400 mb-3">Button Variants</h4>
                <div className="flex flex-wrap gap-3">
                  <Button variant="primary">Primary Emerald</Button>
                  <Button variant="secondary">Secondary Slate</Button>
                  <Button variant="outline">Outline Border</Button>
                  <Button variant="danger">Danger Action</Button>
                  <Button variant="ghost">Ghost Plain</Button>
                  <Button variant="primary" loading>Loading Button</Button>
                  <Button variant="primary" disabled>Disabled State</Button>
                </div>
              </div>

              <div className="pt-4 border-t border-[#1e3258]/60 grid grid-cols-1 md:grid-cols-3 gap-4">
                <Input
                  label="Candidate Name"
                  placeholder="e.g. Priyanshu Singh"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  helperText="Enter full official name as per ERP"
                />
                <Select
                  label="Select Placement Drive"
                  value={selectValue}
                  onChange={(e) => setSelectValue(e.target.value)}
                  options={[
                    { value: "option1", label: "TechCorp SWE 2026" },
                    { value: "option2", label: "Microsoft Cloud Engineer" },
                    { value: "option3", label: "Goldman Sachs Analyst" },
                  ]}
                />
                <DatePicker
                  label="Interview Date"
                  value={dateValue}
                  onChange={(val) => setDateValue(val)}
                  helperText="100% offline date picker"
                />
              </div>

              <div className="pt-4 border-t border-[#1e3258]/60">
                <MultiSelect
                  label="Eligible Branches (MultiSelect)"
                  selected={multiSelectValue}
                  onChange={(sel) => setMultiSelectValue(sel)}
                  options={[
                    { value: "CSE", label: "Computer Science & Engineering" },
                    { value: "IT", label: "Information Technology" },
                    { value: "ECE", label: "Electronics & Communication" },
                    { value: "EE", label: "Electrical Engineering" },
                    { value: "ME", label: "Mechanical Engineering" },
                  ]}
                />
              </div>
            </CardBody>
          </Card>

          {/* Stepper & File Dropzone */}
          <Card>
            <CardHeader title="Stepper Wizard & File Upload" subtitle="Multi-step progress tracker and drag-and-drop CSV parser" />
            <CardBody className="space-y-6">
              <div>
                <h4 className="text-xs font-mono font-bold uppercase text-slate-400 mb-3">Wizard Stepper</h4>
                <Stepper
                  currentStep={stepperStep}
                  onStepClick={(s) => setStepperStep(s)}
                  steps={[
                    { id: 1, title: "Upload Roster", description: "CSV with 1,842 students" },
                    { id: 2, title: "Rules & Policy", description: "Define cutoffs & tiers" },
                    { id: 3, title: "Execute Scheduler", description: "0 clashes verification" },
                    { id: 4, title: "Publish Results", description: "Broadcast to portals" },
                  ]}
                />
              </div>

              <div className="pt-4 border-t border-[#1e3258]/60">
                <FileDropzone
                  accept=".csv,.xlsx"
                  maxSizeMB={25}
                  label="Drop student roster or placement circular here"
                  onFilesSelected={(files) => alert(`Selected ${files.length} file(s)`)}
                />
              </div>
            </CardBody>
          </Card>

          {/* Table with instant filter & export */}
          <Card>
            <CardHeader
              title="Data Table"
              subtitle="Full sorting, filtering, pagination, and zero-dependency client CSV export"
            />
            <CardBody>
              <Table
                columns={tableColumns}
                data={sampleStudents}
                searchPlaceholder="Search candidate roll or name..."
                pageSize={5}
                exportFilename="candidate_roster"
              />
            </CardBody>
          </Card>

          {/* Diff View & Timeline */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader title="DiffView" subtitle="Before / After state inspection for student corrections" />
              <CardBody>
                <DiffView
                  before={{
                    cgpa: 7.2,
                    backlogs: 1,
                    status: "NOT_ELIGIBLE",
                    phone: "+91 98765 00000",
                  }}
                  after={{
                    cgpa: 7.8,
                    backlogs: 0,
                    status: "ELIGIBLE",
                    phone: "+91 98765 11111",
                  }}
                  title="Candidate Correction Request (#REQ-104)"
                />
              </CardBody>
            </Card>

            <Card>
              <CardHeader title="Audit Timeline" subtitle="Tamper-evident placement event stream" />
              <CardBody>
                <Timeline events={timelineEvents} />
              </CardBody>
            </Card>
          </div>

          {/* Dialogs and Skeletals */}
          <Card>
            <CardHeader title="Modal & Skeleton States" subtitle="Destructive confirm modals and accessible loaders" />
            <CardBody className="space-y-4">
              <div className="flex items-center gap-3">
                <Button variant="danger" onClick={() => setShowConfirm(true)}>
                  Trigger Typed Confirm Modal
                </Button>
              </div>

              <div className="pt-4 border-t border-[#1e3258]/60 space-y-2">
                <h4 className="text-xs font-mono font-bold uppercase text-slate-400">Loading Skeletons</h4>
                <div className="space-y-2">
                  <Skeleton variant="text" width="60%" />
                  <Skeleton variant="text" width="40%" />
                  <Skeleton variant="card" height={80} />
                </div>
              </div>
            </CardBody>
          </Card>
        </div>
      )}

      {/* Confirm Dialog instance */}
      <ConfirmDialog
        isOpen={showConfirm}
        title="Override Eligibility Verdict?"
        message="This action will manually override the deterministic eligibility engine for this candidate. You must type OVERRIDE to confirm."
        confirmText="OVERRIDE"
        requireTypedConfirm={true}
        onConfirm={() => {
          setShowConfirm(false);
          alert("Confirmed override");
        }}
        onCancel={() => setShowConfirm(false)}
      />
    </div>
  );
};
