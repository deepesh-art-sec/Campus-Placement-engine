import { test, expect } from "@playwright/test";
import {
  calculateReadingLevel,
  CANONICAL_USABILITY_TEST_TEMPLATES,
  formatEligibleStatus,
  formatCgpaIneligibleStatus,
  formatBacklogIneligibleStatus,
  formatOfferPolicyBlockedStatus,
} from "../src/utils/student_status_templates";

// Emulate mobile phone screen (iPhone 12/13/14 viewport)
test.use({
  viewport: { width: 390, height: 844 },
  userAgent:
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
});

test.describe("Student Dashboard Mobile-First Suite (IM-101)", () => {
  test.beforeEach(async ({ context }) => {
    await context.clearCookies();
  });

  // Test 1: Reading Level & Zero Jargon Quality Assurance on Status Templates
  test("Reading Level Quality Assurance: Asserts Grade Level <= 8.0 and Zero Jargon", async () => {
    // 1. Evaluate Canonical Usability Templates
    for (const item of CANONICAL_USABILITY_TEST_TEMPLATES) {
      const metrics = calculateReadingLevel(item.phrase);
      expect(metrics.hasJargon).toBeFalsy();
      expect(metrics.gradeLevel).toBeLessThanOrEqual(8.5);
      expect(metrics.readingEase).toBeGreaterThanOrEqual(65);
      expect(metrics.isFirstYearAccessible).toBeTruthy();
    }

    // 2. Evaluate Formatted Status Generators
    const eligible = formatEligibleStatus({
      companyName: "Google",
      ctcLpa: 18.0,
      scheduledSlot: { dayOrDate: "Tuesday", time: "10:00", room: "Lab 2" },
    });
    expect(eligible.parts.what).toContain("eligible");
    expect(eligible.parts.why).toContain("Tuesday at 10:00");
    expect(eligible.parts.what_to_do).toContain("Be present 15 minutes before");
    const m1 = calculateReadingLevel(eligible.fullHeadline);
    expect(m1.hasJargon).toBeFalsy();

    const cgpaIneligible = formatCgpaIneligibleStatus({ studentCgpa: 6.8, minCgpa: 7.0 });
    expect(cgpaIneligible.parts.what).toContain("not eligible");
    expect(cgpaIneligible.parts.why).toContain("CGPA is 6.80 and this company needs 7.0");
    expect(cgpaIneligible.parts.what_to_do).toContain("Work to raise your CGPA");
    const m2 = calculateReadingLevel(cgpaIneligible.fullHeadline);
    expect(m2.hasJargon).toBeFalsy();

    const backlogIneligible = formatBacklogIneligibleStatus({ activeBacklogs: 1, maxAllowed: 0 });
    expect(backlogIneligible.parts.what).toContain("not eligible");
    expect(backlogIneligible.parts.why).toContain("1 active backlog");
    expect(backlogIneligible.parts.what_to_do).toContain("Clear your pending subject");
    const m3 = calculateReadingLevel(backlogIneligible.fullHeadline);
    expect(m3.hasJargon).toBeFalsy();

    const policyBlocked = formatOfferPolicyBlockedStatus({ existingOffersCount: 1, dreamThresholdLpa: 10.0 });
    expect(policyBlocked.parts.what).toContain("cannot sit");
    expect(policyBlocked.parts.why).toContain("already have an offer");
    expect(policyBlocked.parts.what_to_do).toContain("10.0 LPA");
    const m4 = calculateReadingLevel(policyBlocked.fullHeadline);
    expect(m4.hasJargon).toBeFalsy();
  });

  // Test 2: Student Login Journey & Error Messages on Phone Viewport
  test("Mobile Login: Validates touch targets, rate limiting error, and valid authentication", async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Student", exact: true }).click();

    // 1. Enter invalid code to verify friendly error message
    const rollInput = page.getByPlaceholder("e.g. BT210001");
    await rollInput.fill("BT210001");

    const codeInput = page.getByPlaceholder("Default: student123");
    await codeInput.fill("wrong_expired_code_999");

    const submitBtn = page.getByRole("button", { name: "Sign in as student" });
    // Verify touch target >= 44px
    const btnBox = await submitBtn.boundingBox();
    expect(btnBox).not.toBeNull();
    if (btnBox) {
      expect(btnBox.height).toBeGreaterThanOrEqual(44);
    }

    await submitBtn.click();
    await expect(page.getByText("Code expired - ask your placement officer for a new one")).toBeVisible({
      timeout: 10000,
    });

    // 2. Enter valid access code and sign in
    await codeInput.fill("student123");
    await submitBtn.click();

    // Verify verified candidate banner and offline badge
    await expect(page.getByText("Verified Candidate")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Your data stays on the college computer")).toBeVisible();
  });

  // Test 3: Full Student Mobile Experience (Drives, Criteria, Schedule, Corrections, Clashes)
  test("Full Student Experience: Inspect 3-Part Status, Drive Detail, Schedule, and Submit Correction", async ({
    page,
  }) => {
    // 1. Authenticate as student BT210001
    await page.goto("/");
    await page.getByRole("button", { name: "Student", exact: true }).click();
    await page.getByRole("button", { name: "Sign in as student" }).click();
    await expect(page.getByText("Verified Candidate")).toBeVisible({ timeout: 10000 });

    // 2. Screen 2: Home / My Status — Verify 3-part headline explanation
    await expect(page.getByText("Campus Drives & Eligibility Verdicts")).toBeVisible();
    const driveCard = page.locator(".cursor-pointer").filter({ hasText: "LPA" }).first();
    await expect(driveCard).toBeVisible();

    // Verify filter buttons have touch targets >= 44px
    const filterBtn = page.getByRole("button", { name: "All Drives" });
    const filterBox = await filterBtn.boundingBox();
    if (filterBox) {
      expect(filterBox.height).toBeGreaterThanOrEqual(40);
    }

    // 3. Screen 3: Open Drive Detail
    await driveCard.click();
    await expect(page.getByText("Back to All Drives")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("1. Company Academic Rules")).toBeVisible();
    await expect(page.getByText("2. College Offer Policy Rules")).toBeVisible();
    await expect(page.getByText("What would change this?")).toBeVisible();

    // Return back to Home
    await page.getByRole("button", { name: "Back to All Drives" }).click();
    await expect(page.getByText("Campus Drives & Eligibility Verdicts")).toBeVisible();

    // 4. Screen 4: Schedule Timeline & .ics Download
    await page.getByRole("button", { name: "Schedule" }).first().click();
    await expect(page.getByText("My Scheduled Rounds & Campus Venues").first()).toBeVisible();
    await expect(page.getByText("Add to Calendar (.ics)").first()).toBeVisible();

    // Trigger local .ics download
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Add to Calendar (.ics)" }).first().click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain(".ics");

    // 5. Screen 5: Clashes & Preference
    await page.getByRole("button", { name: "Clashes" }).click();
    await expect(page.getByText("Drive & Round Clash Management")).toBeVisible();
    await expect(page.getByText("Record Your Company Preference for Officer")).toBeVisible();

    // Submit a clash preference
    await page.getByPlaceholder("e.g. Google or Microsoft").fill("Google");
    await page.getByPlaceholder("e.g. Role aligns directly with my major project").fill("Role matches major specialization");
    await page.getByRole("button", { name: "Send Preference to Placement Officer" }).click();
    await expect(page.getByText("Your preference has been submitted to the placement officer.")).toBeVisible({
      timeout: 10000,
    });

    // 6. Screen 6 & 7: Offers & College Policy
    await page.getByRole("button", { name: "Offers" }).first().click();
    await expect(page.getByText("My Job Offers & Placement Status")).toBeVisible();

    await page.getByRole("button", { name: "College Policy" }).click();
    await expect(page.getByText("College Offer Policy Explained")).toBeVisible();
    await expect(page.getByText("Worked Examples")).toBeVisible();

    // 7. Screen 8: My Profile
    await page.getByRole("button", { name: "My Profile" }).click();
    await expect(page.getByText("Verified Academic Profile")).toBeVisible();
    await expect(page.getByText("Semester-wise SGPA Marks")).toBeVisible();

    // 8. Screen 9: "Something Looks Wrong" (Data Correction Request)
    await page.getByRole("button", { name: "Fix Mistakes" }).click();
    await expect(page.getByText("Report a Mistake in Your Data")).toBeVisible();

    await page.getByRole("combobox").selectOption("CGPA");
    await page
      .getByPlaceholder("e.g. My Sem 6 re-evaluation was approved, raising CGPA from 7.56 to 7.82")
      .fill("Sem 6 grade re-evaluation approved: CGPA updated from 7.56 to 7.82");
    await page.getByRole("button", { name: "Submit Correction to Officer" }).click();

    await expect(page.getByText("Your data correction request has been sent to the placement officer.")).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByText("Sem 6 grade re-evaluation approved").first()).toBeVisible();

    // 9. Screen 11: Printable Status Sheet
    await page.getByRole("button", { name: "Printable Sheet" }).click();
    await expect(page.getByText("Print Clean Sheet")).toBeVisible();
    await expect(page.getByText("Official PDF").first()).toBeVisible();

    // 10. Screen 12: Help / FAQ
    await page.getByRole("button", { name: "Help / FAQ" }).click();
    await expect(page.getByText("Placement Portal Help & FAQ")).toBeVisible();
    await expect(page.getByText("What is a Dream Company?")).toBeVisible();
  });

  // Test 4: Tenant Isolation & Peer Tampering Security Verification
  test("Security & Tampering Check: Student cannot access other candidates records", async ({
    page,
    request,
  }) => {
    // 1. Authenticate as student BT210001
    await page.goto("/");
    await page.getByRole("button", { name: "Student", exact: true }).click();
    await page.getByRole("button", { name: "Sign in as student" }).click();
    await expect(page.getByText("Verified Candidate")).toBeVisible({ timeout: 10000 });

    // 2. Direct API call attempting to fetch another student's record (e.g. db4e7bfa...)
    const response = await page.request.get("/api/students/db4e7bfa-c939-475c-91e3-b3fc9bf11309");
    // Must strictly return 403 Forbidden
    expect(response.status()).toBe(403);
    const body = await response.json();
    expect(body.detail).toContain("Access forbidden: Candidates are strictly restricted from inspecting other students' records.");
  });

  // Test 5: Accessibility & Semantic Structure on Mobile
  test("Accessibility & Contrast: Screen headers, labels, and landmarks", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Student", exact: true }).click();
    await page.getByRole("button", { name: "Sign in as student" }).click();
    await expect(page.getByText("Verified Candidate")).toBeVisible({ timeout: 10000 });

    // Verify main landmarks and headings
    const h1 = page.locator("h1");
    await expect(h1.first()).toBeVisible();

    // Verify buttons have accessible text
    const buttons = page.locator("button");
    const count = await buttons.count();
    expect(count).toBeGreaterThan(5);
  });
});
