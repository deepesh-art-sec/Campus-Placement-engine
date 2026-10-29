// Core Domain & API Types for Institutional Placement Engine

export type UserRole = "officer" | "coordinator" | "student" | "recruiter_readonly" | "recruiter";

export interface User {
  id: string;
  username: string;
  role: UserRole;
  student_id?: string;
  company_id?: string;
}

export type DriveStatus = "draft" | "needs_review" | "ready" | "published" | "completed";

export interface DriveRequirements {
  min_cgpa?: number;
  min_tenth_percentage?: number;
  min_twelfth_percentage?: number;
  allowed_branches?: string[];
  max_active_backlogs?: number;
  max_gap_years?: number;
}

export interface Drive {
  id: string;
  company_id: string;
  company_name: string;
  drive_date: string;
  mode: string;
  status: DriveStatus;
  ctc_lpa: number;
  fixed_pay_lpa?: number;
  is_dream?: boolean;
  job_role?: string;
  version: number;
  requirements_summary?: string;
  requirements?: DriveRequirements;
  applied_count?: number;
}

export interface Student {
  id: string;
  roll_no: string;
  name: string;
  email: string;
  branch: string;
  program: string;
  cgpa: number;
  tenth_percentage: number;
  twelfth_percentage?: number | null;
  diploma_percentage?: number | null;
  date_of_birth: string;
  gender?: string | null;
  category?: string | null;
  active_backlogs?: number;
  history_backlogs?: number;
  gap_years?: number;
  existing_offers_count?: number;
  active_backlogs_count?: number;
  total_backlogs_count?: number;
  gap_years_count?: number;
  offers_count?: number;
}

export interface ExtractedFieldItem {
  extracted_value: any;
  confidence: number;
  source_sentence: string;
  is_ambiguous: boolean;
  is_missing?: boolean;
  is_uncertain?: boolean;
  ambiguity_reason?: string;
}

export interface ExtractedRoundItem {
  round_number: number;
  name: string;
  round_type: string;
  duration_minutes: number;
  source_sentence: string;
}

export interface ExtractionParseResult {
  announcement_id: string;
  filename: string;
  company_name: string;
  job_role?: string;
  location?: string;
  ctc_lpa?: number;
  drive_date?: string;
  application_deadline?: string;
  mode?: string;
  allowed_branches?: string[];
  min_cgpa?: number;
  min_tenth_percentage?: number;
  min_twelfth_percentage?: number;
  max_active_backlogs?: number;
  max_gap_years?: number;
  selection_process?: ExtractedRoundItem[];
  requires_review: boolean;
  missing_fields?: string[];
  uncertain_fields?: string[];
  review_queue: Array<{
    field_name: string;
    extracted_value: any;
    confidence: number;
    source_sentence: string;
    status: string;
  }>;
  ambiguities: Array<{
    field_name: string;
    raw_snippet?: string;
    raw_text?: string;
    reason: string;
    suggested_action: string;
  }>;
  fields: Record<string, ExtractedFieldItem>;
  rule_count: number;
  raw_content_preview?: string;
}

export interface ConfirmSaveExtractionPayload {
  company_name: string;
  job_role?: string;
  job_location?: string;
  drive_date: string;
  mode: string;
  ctc_lpa: number;
  min_cgpa: number;
  min_tenth_percentage: number;
  min_twelfth_percentage?: number;
  allowed_branches: string[];
  max_active_backlogs: number;
  max_gap_years: number;
  selection_process?: ExtractedRoundItem[];
  raw_source_text?: string;
  confirmed_by?: string;
}

export interface EligibilityDecisionItem {
  student_id: string;
  student_name: string;
  roll_no: string;
  branch: string;
  cgpa: number;
  status: "eligible" | "ineligible" | "policy_blocked" | "needs_review";
  reason: string;
  passed_rules: string[];
  failed_rules: string[];
  has_applied?: boolean;
  applied_at?: string | null;
  application_status?: string;
}

export interface ScheduleSlot {
  id: string;
  student_id: string;
  student_name: string;
  roll_no: string;
  round_name: string;
  room_id?: string;
  room_name: string;
  panel_name?: string;
  time_slot?: string;
  start_time: string;
  end_time?: string;
  has_applied?: boolean;
}

export interface StudentImpactItem {
  student_id: string;
  student_roll_no: string;
  student_name: string;
  branch: string;
  cgpa: number;
  change_type: "added" | "removed";
  reason: string;
}

export interface ClashImpactItem {
  student_id: string;
  student_roll_no: string;
  student_name: string;
  conflicting_drive_id: string;
  conflicting_drive_name: string;
  conflicting_slot_time: string;
  details: string;
}

export interface ImpactReportData {
  drive_id: string;
  drive_name: string;
  headline: string;
  change_summary: string;
  students_added_count: number;
  students_removed_count: number;
  clashes_count: number;
  students_added?: StudentImpactItem[];
  students_removed?: StudentImpactItem[];
  newly_clashing_students?: ClashImpactItem[];
  students_added_preview?: string[];
  students_removed_preview?: string[];
  clashes_preview?: string[];
  second_order_policy_effects?: string[];
  second_order_effects?: Array<{
    student_id: string;
    student_name: string;
    source_drive_name: string;
    target_drive_name: string;
    description: string;
  }>;
}

export interface EventRecord {
  id: string;
  aggregate_type: string;
  aggregate_id: string;
  event_type: string;
  actor: string;
  timestamp: string;
  payload: Record<string, any>;
}

export interface PolicyModel {
  id: string;
  name: string;
  max_offers_allowed: number;
  dream_tier_ctc_threshold: number;
  allow_dream_offers: boolean;
  cooling_period_days: number;
  count_off_campus_offers: boolean;
  use_fixed_pay_for_threshold: boolean;
  threshold_is_inclusive: boolean;
  revoked_offers_count: boolean;
  offer_date_uses_acceptance: boolean;
}
