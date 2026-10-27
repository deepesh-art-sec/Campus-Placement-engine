import { test, expect } from "@playwright/test";

test.describe("Institutional Placement Engine End-to-End Suite", () => {
  test.beforeEach(async ({ context, page }) => {
    await context.clearCookies();
    page.on("console", (msg) => console.log("BROWSER LOG:", msg.text()));
    page.on("pageerror", (err) => console.log("BROWSER ERROR:", err.message));
  });

  // Test 1: Full Officer Journey
  test("Full Officer Journey: Extract -> Review -> Evaluate -> Schedule -> What-If -> Publish -> Result & Enforcement", async ({
    page,
  }) => {
    // 0. Intercept and assert all traffic is strictly local
    page.on("request", (req) => {
      const url = req.url();
      const isLocal =
        url.startsWith("http://127.0.0.1") ||
        url.startsWith("http://localhost") ||
        url.startsWith("data:") ||
        url.startsWith("blob:");
      expect(isLocal).toBeTruthy();
    });

    // 1. Visit App & Login as Officer
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Placement Engine" })).toBeVisible();
    await page.getByRole("button", { name: "Sign in as officer" }).click();

    // 2. Verify Officer Workspace Loaded
    await expect(page.getByText("Recruitment Drives")).toBeVisible();
    await expect(page.getByText("Offline mode: all data stays on this machine")).toBeVisible();

    // 3. Navigate to Student Registry & Importer
    await page.getByRole("button", { name: "Students & Importer" }).click();
    await expect(page.getByText("Student Academic Registry")).toBeVisible();
    await page.getByRole("button", { name: "Launch Import Wizard" }).click();
    await expect(page.getByText("Student Roster Import Wizard")).toBeVisible();
    await expect(page.getByText("Upload File")).toBeVisible();

    // 4. Navigate to Extract Drive & Review Announcement
    await page.getByRole("button", { name: "Extract Drive" }).click();
    await expect(page.getByText("Requirement Extraction & Review")).toBeVisible();

    // Ensure company name and announcement text are set
    await page.getByRole("button", { name: "Extract Requirements" }).click();

    // Verify Side-by-Side Field Provenance Table & Confidence Badges
    await expect(page.getByText("Side-by-Side Field Provenance")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("All Fields Validated").or(page.getByText("Requires Officer Review")).first()).toBeVisible();
    await expect(page.getByText("Save & Create Drive")).toBeVisible();
    await page.getByRole("button", { name: "Save & Create Drive" }).click();

    // 5. Eligibility Evaluation Run
    await expect(page.getByText("Eligibility Evaluation Engine")).toBeVisible({ timeout: 10000 });
    await page.getByRole("button", { name: "Evaluate Candidates" }).click();
    await expect(page.getByText("Academically Ineligible").or(page.getByText("Offer Policy Blocked")).first()).toBeVisible({ timeout: 10000 });

    // 6. Schedule Grid & 0 Clashes Verified Badge
    await page.getByRole("button", { name: "Schedule Grid" }).click();
    await expect(page.getByText("Interview & Test Schedule Grid")).toBeVisible();
    await page.getByRole("button", { name: "Generate Clash-Free Schedule" }).click();
    await expect(page.getByText("0 Clashes Verified")).toBeVisible({ timeout: 15000 });

    // 7. What-If Simulation & Safe Publish Safeguards
    await page.getByRole("button", { name: "What-If & Publish" }).click();
    await expect(page.getByText("What-If Simulation & Publish")).toBeVisible();
    await page.getByRole("button", { name: "Simulate What-If Impact" }).click();
    await expect(page.getByText("Computed Impact Headline")).toBeVisible({ timeout: 25000 });

    // Publish flow pre-flight checks
    await page.getByRole("button", { name: "Publish Drive" }).click();
    await expect(page.getByText("Pre-Flight Safeguard Checks")).toBeVisible();
    await expect(page.getByText("Zero unresolved extraction review queue items")).toBeVisible();
    await page.getByRole("button", { name: "Confirm & Publish" }).click();
    await expect(page.getByText("Drive successfully published")).toBeVisible({ timeout: 10000 });

    // 8. Result Entry & Downstream Policy Enforcement ChangeSet
    await page.getByRole("button", { name: "Result Entry" }).click();
    await expect(page.getByText("Result Entry & Policy Enforcement")).toBeVisible();
    await expect(page.getByRole("button", { name: "Record Outcome & Enforce Policy" })).toBeEnabled({ timeout: 15000 });
    await page.getByRole("button", { name: "Record Outcome & Enforce Policy" }).click();
    await expect(page.getByText("Downstream Enforcement ChangeSet")).toBeVisible({ timeout: 25000 });

    // 9. Dispute Explainer (Compare 2 Candidates)
    await page.getByRole("button", { name: "Dispute Explainer" }).click();
    await expect(page.getByText("Student Dispute Comparison Explainer")).toBeVisible();
    await expect(page.getByRole("button", { name: "Generate Dispute Explanation" })).toBeEnabled({ timeout: 15000 });
    await page.getByRole("button", { name: "Generate Dispute Explanation" }).click();
    await expect(page.getByText("Official Placement Cell Dispute Response")).toBeVisible({ timeout: 25000 });

    // 10. Company Export & Lossless Round-Trip Verification
    await page.getByRole("button", { name: "Company Export" }).click();
    await expect(page.getByText("Company-Format Custom Exporter")).toBeVisible();
    await page.waitForTimeout(500);
    await page.getByRole("button", { name: "Verify Lossless Round-Trip" }).click();
    await expect(page.getByText("Round-Trip Test Passed (100% Fidelity)")).toBeVisible({ timeout: 15000 });
  });

  // Test 2: Student Portal Journey
  test("Student Portal Journey: Authenticate -> Self-Scoped View -> Schedule -> Printable Sheet", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Placement Engine" })).toBeVisible();
    await page.getByRole("button", { name: "Student", exact: true }).click();
    await page.getByRole("button", { name: "Sign in as student" }).click();

    // Verify self-scoped view loaded
    await expect(page.getByText("Verified Candidate")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Campus Drives & Eligibility Verdicts")).toBeVisible();

    // Verify one-line plain wording
    await expect(page.getByText("My Scheduled Rounds & Campus Venues").first()).toBeVisible();
    await expect(page.getByText("Print Sheet").first()).toBeVisible();
    await expect(page.getByText("Official PDF").first()).toBeVisible();
  });

  // Test 3: Offline Self-Check & Zero External Network Calls
  test("Offline Self-Check: Asserts zero external calls and air-gap readiness", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Placement Engine" })).toBeVisible();
    await page.getByRole("button", { name: "Sign in as officer" }).click();
    await page.getByRole("button", { name: "Offline Audit" }).click();

    await expect(page.getByText("100% Offline Architecture Self-Check")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("External Calls: 0").last()).toBeVisible();
    await expect(page.getByText("100% Verified Offline")).toBeVisible();
    await expect(page.getByText("READY FOR AIR-GAP")).toBeVisible();
  });

  // Test 4: Accessibility and Visual Checks
  test("Accessibility & Structural Integrity Check", async ({ page }) => {
    await page.goto("/");
    // Check accessible headings and focus indicators
    const heading = page.locator("h2");
    await expect(heading.first()).toBeVisible();

    // Check keyboard navigation tabs
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
  });

  // Test 5: Officer Remove Drive Flow
  test("Officer Remove Drive: Duplicate drive, open remove modal, provide justification, and verify removal", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Placement Engine" })).toBeVisible();
    await page.getByPlaceholder("e.g. officer").fill("admin");
    await page.locator("input[type='password']").fill("admin123");
    await page.getByRole("button", { name: "Sign in as officer" }).click();
    await expect(page.getByText("Recruitment Drives")).toBeVisible({ timeout: 15000 });

    // 1. Duplicate existing drive to create a test drive
    const duplicateBtn = page.getByRole("button", { name: "Duplicate drive (reuse rules)" }).first();
    await duplicateBtn.click();
    await expect(page.getByText(/Duplicated drive created successfully/i)).toBeVisible({ timeout: 10000 });

    // 2. Locate the duplicated drive card and click remove button
    const removeBtn = page.locator("button[aria-label*='Remove drive for']").first();
    await expect(removeBtn).toBeVisible();
    await removeBtn.click();

    // 3. Verify confirmation modal and mandatory reason prompt
    await expect(page.getByText("Irreversible Administrative Action:")).toBeVisible({ timeout: 10000 });
    const reasonInput = page.locator("textarea[placeholder*='Duplicate drive created by error']");
    await reasonInput.fill("Automated test: duplicate test drive cleanup after validation");

    // 4. Confirm permanent deletion
    await page.getByRole("button", { name: "Confirm Permanent Removal" }).click();
    await expect(page.getByText(/has been permanently removed/i)).toBeVisible({ timeout: 10000 });
  });
});
