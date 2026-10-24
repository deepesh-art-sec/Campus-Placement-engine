// Core Domain & API Types for Institutional Placement Engine

export type UserRole = "officer" | "coordinator" | "student" | "recruiter_readonly";

export interface User {
  id: string;
  username: string;
  role: UserRole;
  student_id?: string;
  company_id?: string;
}

export type DriveStatus = "draft" | "needs_review" | "ready" | "published" | "completed";

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
  ambiguity_reason?: string;
}

export interface ExtractionParseResult {
  announcement_id: string;
  filename: string;
  company_name: string;
  job_role?: string;
  ctc_lpa?: number;
  requires_review: boolean;
  review_queue: Array<{
    field_name: string;
    extracted_value: any;
    confidence: number;
    source_sentence: string;
    status: string;
  }>;
  ambiguities: Array<{
    field_name: string;
    raw_snippet: string;
    reason: string;
    suggested_action: string;
  }>;
  fields: Record<string, ExtractedFieldItem>;
  rule_count: number;
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
}

export interface ScheduleSlot {
  id: string;
  student_id: string;
  student_name: string;
  roll_no: string;
  round_name: string;
  room_name: string;
  panel_name?: string;
  start_time: string;
  end_time?: string;
}

export interface ImpactReportData {
  drive_id: string;
  drive_name: string;
  headline: string;
  change_summary: string;
  students_added_count: number;
  students_removed_count: number;
  clashes_count: number;
  students_added_preview?: string[];
  students_removed_preview?: string[];
  clashes_preview?: string[];
  second_order_policy_effects?: string[];
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
