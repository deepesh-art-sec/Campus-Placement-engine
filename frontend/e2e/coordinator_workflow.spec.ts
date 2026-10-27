import { test, expect } from "@playwright/test";

test.describe("Placement Coordinator Operations & Governance Verification Suite", () => {
  test.beforeEach(async ({ context, page }) => {
    await context.clearCookies();
    page.on("console", (msg) => console.log("COORDINATOR BROWSER LOG:", msg.text()));
    page.on("pageerror", (err) => console.log("COORDINATOR BROWSER ERROR:", err.message));
  });

  test("Coordinator Journey: View Eligibility -> Raise Correction -> Enter Pending Result -> On-The-Day Floor Check -> Officer Approval Session", async ({
    page,
  }) => {
    // 1. Visit Portal & Sign in as Placement Coordinator
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Placement Engine" })).toBeVisible();

    await page.getByRole("button", { name: "Coordinator", exact: true }).click();
    await page.getByRole("button", { name: "Sign in as coordinator" }).click();

    // 2. Verify Coordinator Workspace Overview Loaded
    await expect(page.getByText("Coordinator Operations Overview")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Open Requests")).toBeVisible();
    await expect(page.getByText("Unresolved Clashes")).toBeVisible();

    // 3. View Eligibility List (Module 4) & Open One-Line Student Explanation
    await page.getByTestId("coord-nav-eligibility").click();
    await expect(page.getByText("Eligibility Explainer List")).toBeVisible();
    await expect(page.getByText("Total Evaluated")).toBeVisible();

    // Filter by ineligible to test student explanation reader
    await page.getByRole("button", { name: "ineligible", exact: true }).click();
    await page.waitForTimeout(500);

    const explanationRow = page.locator("tr.cursor-pointer").first();
    if (await explanationRow.isVisible()) {
      await explanationRow.click();
      await expect(page.getByText(/Student Inquiry Explanation/i)).toBeVisible();
      await page.keyboard.press("Escape");
      await page.waitForTimeout(300);
    }

    // 4. Navigate to Students (Module 2) & Raise Correction Request
    await page.getByTestId("coord-nav-students").click();
    await expect(page.getByText("Student Academic Roster")).toBeVisible();

    // Search and select first student via Inspect button
    await page.getByRole("button", { name: "Inspect" }).first().click();

    // Click "Request Correction" tab in drawer
    await page.getByRole("button", { name: "Request Correction" }).click();

    // Fill new CGPA and justification note
    await page.locator('input[placeholder="e.g. 8.25 or 0"]').fill("8.75");
    await page.locator('textarea[placeholder*="re-evaluation grade card"]').fill("Re-evaluation result submitted with grade card copy.");
    await page.getByRole("button", { name: "Submit Request to Officer" }).click();
    await expect(page.getByText(/submitted to the Placement Officer|Request.*submitted/i)).toBeVisible({ timeout: 10000 });

    // Close student drawer
    await page.keyboard.press("Escape");
    await page.waitForTimeout(300);

    // 5. Navigate to Result Entry (Module 7) & Submit Result (Strictly Pending)
    await page.getByTestId("coord-nav-results").click();
    await expect(page.getByText("Result Entry (Pending Officer Approval)")).toBeVisible();

    // Wait for students and drives to populate
    await expect(page.locator("select").first().locator("option")).not.toHaveCount(0, { timeout: 15000 });
    await expect(page.locator("select").nth(1).locator("option")).not.toHaveCount(0, { timeout: 15000 });
    await expect(page.getByRole("button", { name: "Log Result as Pending" })).toBeEnabled({ timeout: 15000 });

    // Enter result
    await page.locator('input[type="number"]').first().fill("13.5");
    await page.locator('textarea[placeholder*="Cleared all 3 interview"]').fill("Selected in campus technical and manager round.");
    await page.getByRole("button", { name: "Log Result as Pending" }).click();

    // Verify submission is held as PENDING
    await expect(page.getByText(/Result saved as PENDING/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("PENDING").first()).toBeVisible();

    // 6. Navigate to On-The-Day Floor View (Module 9)
    await page.getByTestId("coord-nav-ontheday").click();
    await expect(page.getByText("On-The-Day Drive Attendance")).toBeVisible();

    // Mark attendance for first candidate if available
    const presentBtn = page.getByRole("button", { name: "Present" }).first();
    if (await presentBtn.isVisible()) {
      await presentBtn.click();
      await page.waitForTimeout(500);
    }

    // 7. Officer Approval Session: Reset Session & Login as Officer
    await page.context().clearCookies();
    await page.goto("/");
    await page.getByRole("button", { name: "Officer", exact: true }).click();
    await page.getByRole("button", { name: "Sign in as officer" }).click();

    // Verify Officer Workspace Loaded
    await expect(page.getByText("Recruitment Drives")).toBeVisible({ timeout: 10000 });

    // Navigate to Officer Result Entry View
    await page.getByRole("button", { name: "Result Entry" }).click();
    await expect(page.getByText("Result Entry & Policy Enforcement")).toBeVisible();

    // Assert the pending submission from coordinator is present
    await expect(page.getByText("Pending Coordinator Submissions (Two-Man Rule Protocol)")).toBeVisible();
    const approveBtn = page.getByRole("button", { name: "Approve & Enforce Policy" }).first();
    await expect(approveBtn).toBeVisible({ timeout: 10000 });

    // Officer confirms and approves pending submission
    await approveBtn.click();
    await expect(page.getByText(/approved|Downstream policy rules applied/i).first()).toBeVisible({ timeout: 10000 });
  });

  test("Permission Tests: Restricted Controls Strictly Hidden & Direct API Calls Return 403 Forbidden", async ({
    page,
  }) => {
    // 1. Login as Coordinator
    await page.goto("/");
    await page.getByRole("button", { name: "Coordinator", exact: true }).click();
    await page.getByRole("button", { name: "Sign in as coordinator" }).click();
    await expect(page.getByText("Coordinator Operations Overview")).toBeVisible({ timeout: 10000 });

    // 2. Prove restricted officer controls are NOT rendered in DOM
    const restrictedLabels = [
      "Offer Policy",
      "Rule Editor",
      "Policy Simulator",
      "What-If & Publish",
      "Publish Drive",
      "Users & Roles",
      "Audit & Backup",
      "Rollback",
    ];

    for (const label of restrictedLabels) {
      await expect(page.locator(`button:has-text("${label}")`)).toHaveCount(0);
    }

    // 3. Direct API Call 1: Coordinator attempting to publish drive -> MUST RETURN 403 Forbidden
    const pubStatus = await page.evaluate(async () => {
      const res = await fetch("/api/drives/drive_mock_1/publish", { method: "POST" });
      return res.status;
    });
    expect(pubStatus).toBe(403);

    // 4. Direct API Call 2: Coordinator attempting to approve a request -> MUST RETURN 403 Forbidden
    const approveStatus = await page.evaluate(async () => {
      const res = await fetch("/api/coordinator/requests/req_test/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ response: "Illicit coordinator approval" }),
      });
      return res.status;
    });
    expect(approveStatus).toBe(403);

    // 5. Direct API Call 3: Coordinator attempting to modify offer policy -> MUST RETURN 403 Forbidden
    const policyStatus = await page.evaluate(async () => {
      const res = await fetch("/api/policies/policy_active", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ max_offers: 5 }),
      });
      return res.status;
    });
    expect(policyStatus).toBe(403);

    // 6. Direct API Call 4: Coordinator attempting to directly mutate student marks -> MUST RETURN 403 Forbidden
    const stuStatus = await page.evaluate(async () => {
      const res = await fetch("/api/students/BT210001", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cgpa: 9.99 }),
      });
      return res.status;
    });
    expect(stuStatus).toBe(403);
  });

  test("Coordinator Views Accessibility & Semantic Structure Integrity", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Coordinator", exact: true }).click();
    await page.getByRole("button", { name: "Sign in as coordinator" }).click();

    // Assert main ARIA landmarks
    await expect(page.locator("aside")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("main")).toBeVisible({ timeout: 10000 });

    // Navigation through modules using keyboard Tab key
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");

    // Check headings hierarchy
    const h1 = page.locator("h1");
    await expect(h1.first()).toBeVisible();
  });
});
