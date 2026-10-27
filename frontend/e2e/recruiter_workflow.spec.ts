import { test, expect } from "@playwright/test";

test.describe("Corporate Recruiter Operations & Tenant Security Suite", () => {
  test("Recruiter Journey: Login -> View Shortlist -> Verify Why-This-Student -> View Schedule -> Check Requirements -> Submit Inquiry -> Download Formats", async ({
    page,
  }) => {
    // 1. Login as Recruiter
    await page.goto("/");
    await page.getByRole("button", { name: "Recruiter", exact: true }).click();
    await page.getByRole("button", { name: "Sign in as recruiter" }).click();

    // Verify Recruiter Workspace Loaded with Company Scope
    await expect(page.getByText("Tenant Isolated Corporate Portal")).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole("heading", { name: "Google" })).toBeVisible();
    await expect(page.getByText("Recruiter Read-Only").first()).toBeVisible();

    // Verify Overview Stat Cards
    await expect(page.getByText("Shortlisted Candidates")).toBeVisible();
    await expect(page.getByText("Scheduled Slots")).toBeVisible();
    await expect(page.getByText("Recruitment Rounds")).toBeVisible();

    // 2. Shortlist View (Module 2)
    await page.getByRole("button", { name: /02 Shortlist/i }).click();
    await expect(page.getByText("Approved Candidate Shortlist")).toBeVisible();

    // Verify approved columns are present
    await expect(page.getByRole("columnheader", { name: "Roll No" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Candidate Full Name" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Branch" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "CGPA" })).toBeVisible();

    // Verify private demographics are strictly absent from table headers
    await expect(page.getByRole("columnheader", { name: "Phone" })).toHaveCount(0);
    await expect(page.getByRole("columnheader", { name: "Date of Birth" })).toHaveCount(0);
    await expect(page.getByRole("columnheader", { name: "Address" })).toHaveCount(0);
    await expect(page.getByRole("columnheader", { name: "Religion" })).toHaveCount(0);

    // 3. Why This Student Breakdown (Module 3)
    const whyButton = page.getByRole("button", { name: /Why Eligible/i }).first();
    await expect(whyButton).toBeVisible();
    await whyButton.click();

    // Verify modal verification checklist
    await expect(page.getByText("Why This Student Is In The Room")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Candidate Verified: Meets 100% of/i)).toBeVisible();
    await expect(page.getByText("Undergraduate CGPA")).toBeVisible();
    await expect(page.getByText("Class 10th Secondary Score")).toBeVisible();
    await expect(page.getByText("Active Standing Backlogs")).toBeVisible();

    // Close verification modal
    await page.getByRole("button", { name: "Close Verification" }).click();
    await expect(page.getByText("Why This Student Is In The Room")).not.toBeVisible();

    // 4. Drive Schedule (Module 4)
    await page.getByRole("button", { name: /04 Schedule/i }).click();
    await expect(page.getByText("Interview Round Schedule")).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Round" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Venue / Cabin" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Evaluation Panel" })).toBeVisible();

    // 5. Requirements Used (Module 5)
    await page.getByRole("button", { name: /05 Requirements Used/i }).click();
    await expect(page.getByText("Eligibility Conditions Applied For Your Drive")).toBeVisible();
    await expect(page.getByText(/CGPA Cut-off/i)).toBeVisible();
    await expect(page.getByText(/Standing Backlog Rule/i)).toBeVisible();

    // 6. Contact the College & Submit Inquiry (Module 8)
    await page.getByRole("button", { name: /08 Contact College/i }).click();
    await expect(page.getByText("Submit Inquiry or Request to Placement Officer")).toBeVisible();
    await expect(page.getByText("Placement Cell Office")).toBeVisible();

    // Fill inquiry form
    await page.locator('input[placeholder*="Need one more interview panel"]').fill("Requesting 1 additional interview cabin for afternoon slot.");
    await page.locator('textarea[placeholder*="Provide specific details"]').fill("Our technical leads would like to split into 4 simultaneous interview streams starting at 14:00.");
    await page.getByRole("button", { name: "Submit Inquiry to Officer" }).click();

    // Verify success banner and entry in thread
    await expect(page.getByText(/Inquiry submitted to Placement Officer/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Requesting 1 additional interview cabin for afternoon slot.").first()).toBeVisible();

    // 7. Corporate Exports (Module 7)
    await page.getByRole("button", { name: /07 Export Files/i }).click();
    await expect(page.getByText("Corporate File Exports (Company Format)")).toBeVisible();
    await expect(page.getByText("Candidate Shortlist Roster")).toBeVisible();
    await expect(page.getByText("Interview Schedule Timetable")).toBeVisible();
  });

  test("Tenant Security & Tampering Tests: Restricted Controls Hidden & Direct Cross-Company Calls Return 403 Forbidden", async ({
    page,
  }) => {
    // 1. Login as Recruiter
    await page.goto("/");
    await page.getByRole("button", { name: "Recruiter", exact: true }).click();
    await page.getByRole("button", { name: "Sign in as recruiter" }).click();
    await expect(page.getByText("Tenant Isolated Corporate Portal")).toBeVisible({ timeout: 10000 });

    // 2. Verify Officer & Coordinator Mutating Controls Are NOT Rendered
    const forbiddenControls = [
      "Offer Policy",
      "Rule Editor",
      "Policy Simulator",
      "What-If & Publish",
      "Publish Drive",
      "Users & Roles",
      "Audit & Backup",
      "Rollback",
      "Add Student",
      "Import Students",
    ];

    for (const ctrl of forbiddenControls) {
      await expect(page.locator(`button:has-text("${ctrl}")`)).toHaveCount(0);
    }

    // 3. Tampering Test 1: Recruiter attempts to access another company's drive -> MUST RETURN 403 Forbidden
    const crossDriveStatus = await page.evaluate(async () => {
      const res = await fetch("/api/recruiter/drive/drive_northwind");
      return res.status;
    });
    expect(crossDriveStatus).toBe(403);

    // 4. Tampering Test 2: Recruiter attempts to access another company's candidate "why" -> MUST RETURN 403 Forbidden
    const crossCandidateStatus = await page.evaluate(async () => {
      // Candidate PIPE_002 or non-shortlisted ID
      const res = await fetch("/api/recruiter/candidate/NON_EXISTENT_OR_OTHER_CANDIDATE/why");
      return res.status;
    });
    expect([403, 404]).toContain(crossCandidateStatus);

    // 5. Tampering Test 3: Recruiter attempts to publish a drive -> MUST RETURN 403 Forbidden
    const publishStatus = await page.evaluate(async () => {
      const res = await fetch("/api/drives/drive_techcorp/publish", { method: "POST" });
      return res.status;
    });
    expect(publishStatus).toBe(403);

    // 6. Tampering Test 4: Recruiter attempts to modify college offer policy -> MUST RETURN 403 Forbidden
    const policyStatus = await page.evaluate(async () => {
      const res = await fetch("/api/policies/policy_active", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ max_offers: 5 }),
      });
      return res.status;
    });
    expect(policyStatus).toBe(403);
  });

  test("Recruiter Accessibility & Semantic Structure Integrity", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Recruiter", exact: true }).click();
    await page.getByRole("button", { name: "Sign in as recruiter" }).click();
    await expect(page.getByText("Tenant Isolated Corporate Portal")).toBeVisible({ timeout: 10000 });

    // Validate semantic landmarks
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.locator("main")).toBeVisible();

    // Verify tab buttons have accessible text
    const tabs = page.locator("button:has-text('0')");
    const count = await tabs.count();
    expect(count).toBeGreaterThanOrEqual(5);

    // Verify no broken images or invalid links
    const externalLinks = await page.locator('a[href^="http"]:not([href*="127.0.0.1"]):not([href*="localhost"])').count();
    expect(externalLinks).toBe(0);
  });
});
