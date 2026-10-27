/**
 * Centralized Placement Student Status Wording Templates.
 * 
 * Every status explanation strictly follows the 3-part human clarity rule:
 * 1. What the status is (e.g., "You are not eligible:")
 * 2. Why (e.g., "your CGPA is 6.8 and this company needs 7.0 or above.")
 * 3. What you can do next (e.g., "Work to raise your CGPA in upcoming exams or check with the TPO.")
 * 
 * Designed for first-year college reading level (Flesch-Kincaid Grade Level <= 8).
 * Contains ZERO technical jargon (no rule IDs, no DB columns, no policy clause numbers).
 */

export type StudentDriveStatus = "eligible" | "ineligible" | "policy_blocked" | "needs_review";

export interface StatusParts {
  what: string;
  why: string;
  what_to_do: string;
}

export interface FormattedStatusExplanation {
  status: StudentDriveStatus;
  statusLabel: string;
  badgeVariant: "success" | "danger" | "warning" | "brand";
  parts: StatusParts;
  fullHeadline: string;
  whatWouldChangeThis: string;
}

/**
 * 1. Eligible Status Explanations
 */
export function formatEligibleStatus(params: {
  companyName: string;
  ctcLpa: number;
  scheduledSlot?: {
    dayOrDate: string;
    time: string;
    room: string;
  } | null;
}): FormattedStatusExplanation {
  if (params.scheduledSlot) {
    const parts: StatusParts = {
      what: "You are eligible.",
      why: `Your test is on ${params.scheduledSlot.dayOrDate} at ${params.scheduledSlot.time} in ${params.scheduledSlot.room}.`,
      what_to_do: "Be present 15 minutes before time with your college ID card.",
    };
    return {
      status: "eligible",
      statusLabel: "Eligible",
      badgeVariant: "success",
      parts,
      fullHeadline: `${parts.what} ${parts.why} ${parts.what_to_do}`,
      whatWouldChangeThis: "You are already qualified and scheduled for this recruitment drive.",
    };
  }

  const parts: StatusParts = {
    what: "You are eligible.",
    why: `You meet all academic criteria for ${params.companyName} (${params.ctcLpa.toFixed(1)} LPA).`,
    what_to_do: "Watch your schedule tab for your allocated room and time slot.",
  };
  return {
    status: "eligible",
    statusLabel: "Eligible",
    badgeVariant: "success",
    parts,
    fullHeadline: `${parts.what} ${parts.why} ${parts.what_to_do}`,
    whatWouldChangeThis: "You meet all requirements to attend this drive.",
  };
}

/**
 * 2. Ineligible (Company Academic Rules) Explanations
 */
export function formatCgpaIneligibleStatus(params: {
  studentCgpa: number;
  minCgpa: number;
}): FormattedStatusExplanation {
  const parts: StatusParts = {
    what: "You are not eligible:",
    why: `your CGPA is ${params.studentCgpa.toFixed(2)} and this company needs ${params.minCgpa.toFixed(1)} or above.`,
    what_to_do: "Work to raise your CGPA in upcoming exams or check with the TPO.",
  };
  return {
    status: "ineligible",
    statusLabel: "Not eligible",
    badgeVariant: "danger",
    parts,
    fullHeadline: `${parts.what} ${parts.why} ${parts.what_to_do}`,
    whatWouldChangeThis: `Raising your cumulative CGPA to ${params.minCgpa.toFixed(1)} in final grade sheets would qualify you for this drive.`,
  };
}

export function formatBacklogIneligibleStatus(params: {
  activeBacklogs: number;
  maxAllowed: number;
}): FormattedStatusExplanation {
  const parts: StatusParts = {
    what: "You are not eligible:",
    why: `you have ${params.activeBacklogs} active backlog and this company allows at most ${params.maxAllowed}.`,
    what_to_do: "Clear your pending subject in the next re-exam.",
  };
  return {
    status: "ineligible",
    statusLabel: "Not eligible",
    badgeVariant: "danger",
    parts,
    fullHeadline: `${parts.what} ${parts.why} ${parts.what_to_do}`,
    whatWouldChangeThis: `Clearing your ${params.activeBacklogs} active backlog before registration closes would make you eligible.`,
  };
}

export function formatBranchIneligibleStatus(params: {
  studentBranch: string;
  allowedBranches: string[];
}): FormattedStatusExplanation {
  const branchSummary = params.allowedBranches.slice(0, 2).join(", ");
  const parts: StatusParts = {
    what: "You are not eligible:",
    why: `this drive is restricted to ${branchSummary} and your branch is ${params.studentBranch}.`,
    what_to_do: "Explore upcoming recruitment drives open specifically to your department.",
  };
  return {
    status: "ineligible",
    statusLabel: "Not eligible",
    badgeVariant: "danger",
    parts,
    fullHeadline: `${parts.what} ${parts.why} ${parts.what_to_do}`,
    whatWouldChangeThis: "Eligibility for this drive is restricted to specific engineering disciplines by the employer.",
  };
}

export function formatSchoolMarksIneligibleStatus(params: {
  exam: "10th" | "12th";
  studentPercentage: number;
  minPercentage: number;
}): FormattedStatusExplanation {
  const parts: StatusParts = {
    what: "You are not eligible:",
    why: `your ${params.exam} percentage is ${params.studentPercentage.toFixed(1)}% and this company requires ${params.minPercentage.toFixed(1)}% or above.`,
    what_to_do: "Look for recruitment drives that have flexible secondary school criteria.",
  };
  return {
    status: "ineligible",
    statusLabel: "Not eligible",
    badgeVariant: "danger",
    parts,
    fullHeadline: `${parts.what} ${parts.why} ${parts.what_to_do}`,
    whatWouldChangeThis: "School percentage cutoffs are fixed by the company's human resources policy.",
  };
}

export function formatGapYearsIneligibleStatus(params: {
  studentGaps: number;
  maxGaps: number;
}): FormattedStatusExplanation {
  const parts: StatusParts = {
    what: "You are not eligible:",
    why: `you have ${params.studentGaps} gap years and this company permits at most ${params.maxGaps}.`,
    what_to_do: "Apply for drives that allow career break or education gap flexibility.",
  };
  return {
    status: "ineligible",
    statusLabel: "Not eligible",
    badgeVariant: "danger",
    parts,
    fullHeadline: `${parts.what} ${parts.why} ${parts.what_to_do}`,
    whatWouldChangeThis: "Gap year thresholds are set directly by the hiring employer.",
  };
}

/**
 * 3. Policy Blocked (College Placement Policy) Explanations
 */
export function formatOfferPolicyBlockedStatus(params: {
  existingOffersCount: number;
  existingCompany?: string;
  dreamThresholdLpa?: number;
}): FormattedStatusExplanation {
  const dreamThreshold = params.dreamThresholdLpa || 10.0;

  if (params.existingOffersCount >= 2) {
    const parts: StatusParts = {
      what: "You cannot sit for this drive:",
      why: "you have reached the maximum allowed offers (2 offers) under college policy.",
      what_to_do: "Your placement journey is complete! Help your peers prepare for upcoming drives.",
    };
    return {
      status: "policy_blocked",
      statusLabel: "Blocked by college policy",
      badgeVariant: "warning",
      parts,
      fullHeadline: `${parts.what} ${parts.why} ${parts.what_to_do}`,
      whatWouldChangeThis: "College policy limits every student to a maximum of 2 placement offers.",
    };
  }

  const parts: StatusParts = {
    what: "You cannot sit for this drive:",
    why: "you already have an offer. This company is not in the dream-company category.",
    what_to_do: `Wait for a dream drive offering ${dreamThreshold.toFixed(1)} LPA or above.`,
  };
  return {
    status: "policy_blocked",
    statusLabel: "Blocked by college policy",
    badgeVariant: "warning",
    parts,
    fullHeadline: `${parts.what} ${parts.why} ${parts.what_to_do}`,
    whatWouldChangeThis: `Under college policy, candidates with an existing offer can only participate in Dream Tier companies offering ${dreamThreshold.toFixed(1)} LPA or higher.`,
  };
}

/**
 * 4. Needs Review Explanations
 */
export function formatNeedsReviewStatus(params: {
  reviewReason?: string;
}): FormattedStatusExplanation {
  const parts: StatusParts = {
    what: "Your application needs review:",
    why: params.reviewReason || "your grade submission or diploma percentage is pending verification.",
    what_to_do: "Visit the placement office with your original mark sheets to complete verification.",
  };
  return {
    status: "needs_review",
    statusLabel: "Needs review",
    badgeVariant: "brand",
    parts,
    fullHeadline: `${parts.what} ${parts.why} ${parts.what_to_do}`,
    whatWouldChangeThis: "Verification by the Training and Placement Cell will immediately update your status to eligible.",
  };
}

/**
 * Reading-Level & Clarity Quality Assurance Analyzer
 * Computes Flesch-Kincaid Grade Level and Flesch Reading Ease score.
 */
export function calculateReadingLevel(text: string): {
  readingEase: number;
  gradeLevel: number;
  isFirstYearAccessible: boolean;
  wordCount: number;
  sentenceCount: number;
  hasJargon: boolean;
} {
  const words = text.match(/\b[A-Za-z]+\b/g) || [];
  // Split on sentence boundaries preserving numbers with decimals like 6.8 or 10.0
  const sentences = text.split(/[.!?]+(?:\s+|$)/).filter((s) => s.trim().length > 0);

  if (words.length === 0 || sentences.length === 0) {
    return {
      readingEase: 100,
      gradeLevel: 1,
      isFirstYearAccessible: true,
      wordCount: 0,
      sentenceCount: 0,
      hasJargon: false,
    };
  }

  // Count syllables roughly
  let totalSyllables = 0;
  for (const word of words) {
    const w = word.toLowerCase();
    if (w.length <= 3) {
      totalSyllables += 1;
      continue;
    }
    const matches = w.match(/[aeiouy]{1,2}/g);
    let count = matches ? matches.length : 1;
    if (w.endsWith("e") && !w.endsWith("le")) {
      count = Math.max(1, count - 1);
    }
    totalSyllables += count;
  }

  const wordsPerSentence = words.length / sentences.length;
  const syllablesPerWord = totalSyllables / words.length;

  // Standard Flesch Reading Ease formula:
  // 206.835 - 1.015 * (total words / total sentences) - 84.6 * (total syllables / total words)
  const readingEase = Math.round(206.835 - 1.015 * wordsPerSentence - 84.6 * syllablesPerWord);

  // Standard Flesch-Kincaid Grade Level formula:
  // 0.39 * (total words / total sentences) + 11.8 * (total syllables / total words) - 15.59
  const gradeLevel = Math.max(1, Math.round((0.39 * wordsPerSentence + 11.8 * syllablesPerWord - 15.59) * 10) / 10);

  // Check for technical jargon
  const jargonRegex = /\b(rule_[0-9]+|clause\s+[a-z0-9-]+|subclause|policy_blocked|boolean|sql|db_|ast_|regex)\b/i;
  const hasJargon = jargonRegex.test(text);

  return {
    readingEase,
    gradeLevel,
    isFirstYearAccessible: gradeLevel <= 8.5 && !hasJargon,
    wordCount: words.length,
    sentenceCount: sentences.length,
    hasJargon,
  };
}

/**
 * Canonical test phrases evaluated during 3-student usability testing
 */
export const CANONICAL_USABILITY_TEST_TEMPLATES = [
  {
    id: "cgpa_ineligible",
    title: "CGPA Shortfall",
    phrase: "You are not eligible: your CGPA is 6.8 and this company needs 7.0 or above. Work to raise your CGPA in upcoming exams or check with the TPO.",
    expectedMeaning: "My current CGPA is 6.8 which is below the 7.0 requirement for this company.",
    expectedAction: "Study to improve my CGPA in next semester or verify if my latest grades were already submitted to the placement officer.",
  },
  {
    id: "offer_policy_blocked",
    title: "One-Offer Rule with Dream Exception",
    phrase: "You cannot sit for this drive: you already have an offer. This company is not in the dream-company category. Wait for a dream drive offering 10.0 LPA or above.",
    expectedMeaning: "I already have one job offer, so college rules only allow me to sit for Dream companies paying 10 LPA or higher.",
    expectedAction: "Do not attend this drive; prepare for upcoming Dream tier drives offering at least 10 LPA.",
  },
  {
    id: "eligible_scheduled",
    title: "Eligible and Scheduled",
    phrase: "You are eligible. Your test is on Tuesday at 10:00 in Lab 2. Be present 15 minutes before time with your college ID card.",
    expectedMeaning: "I passed all requirements and have an assigned seat for the exam.",
    expectedAction: "Arrive at Lab 2 on Tuesday by 9:45 AM carrying my college ID card.",
  },
  {
    id: "active_backlog",
    title: "Active Backlog Block",
    phrase: "You are not eligible: you have 1 active backlog and this company allows at most 0. Clear your pending subject in the next re-exam.",
    expectedMeaning: "I have an uncleared subject and this company requires all subjects to be passed.",
    expectedAction: "Register for and pass the supplementary re-exam when scheduled.",
  },
];
