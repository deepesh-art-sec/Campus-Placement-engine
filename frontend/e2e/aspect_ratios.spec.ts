import { test, expect } from "@playwright/test";

// Multi-Aspect-Ratio and Viewport Matrix
const VIEWPORTS = [
  { name: "Mobile Portrait (9:16 - iPhone SE)", width: 375, height: 667 },
  { name: "Modern Mobile (9:19.5 - iPhone 12/13/14)", width: 390, height: 844 },
  { name: "Mobile Landscape (19.5:9)", width: 844, height: 390 },
  { name: "Tablet Portrait (3:4 - iPad)", width: 768, height: 1024 },
  { name: "Tablet Landscape (4:3 - iPad)", width: 1024, height: 768 },
  { name: "Standard Laptop (16:9 - 1366x768)", width: 1366, height: 768 },
  { name: "Full HD Desktop (16:9 - 1080p)", width: 1920, height: 1080 },
  { name: "Ultra-Wide Monitor (21:9 - 2560x1080)", width: 2560, height: 1080 },
];

test.describe("Cross-Device & Multi-Aspect-Ratio Responsive Test Suite", () => {
  test.beforeEach(async ({ context }) => {
    await context.clearCookies();
  });

  for (const vp of VIEWPORTS) {
    test.describe(`Viewport: ${vp.name} (${vp.width}x${vp.height})`, () => {
      test.use({ viewport: { width: vp.width, height: vp.height } });

      test("1. Unauthenticated Login Screen Renders Responsively", async ({ page }) => {
        await page.goto("/");

        // Verify branding and heading fit viewport
        const heading = page.getByRole("heading", { name: "Placement Engine" });
        await expect(heading).toBeVisible();

        // Verify all 4 role switcher buttons are visible and clickable
        await expect(page.getByRole("button", { name: "Officer", exact: true })).toBeVisible();
        await expect(page.getByRole("button", { name: "Coordinator", exact: true })).toBeVisible();
        await expect(page.getByRole("button", { name: "Student", exact: true })).toBeVisible();
        await expect(page.getByRole("button", { name: "Recruiter", exact: true })).toBeVisible();

        // Check horizontal overflow on document body
        const bodyScrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
        expect(bodyScrollWidth).toBeLessThanOrEqual(vp.width + 1);
      });

      test("2. Student Portal Renders Responsively", async ({ page }) => {
        await page.goto("/");
        await page.getByRole("button", { name: "Student", exact: true }).click();
        await page.getByRole("button", { name: "Sign in as student" }).click();

        // Verify Student Portal loads
        await expect(page.getByText("Verified Candidate")).toBeVisible({ timeout: 10000 });
        await expect(page.getByText("Campus Drives & Eligibility Verdicts")).toBeVisible();

        // Verify scheduled rounds section is accessible
        await expect(page.getByText("My Scheduled Rounds & Campus Venues").first()).toBeVisible();

        // Ensure key action buttons (Print Sheet, Official PDF) exist and are clickable
        await expect(page.getByText("Print Sheet").first()).toBeVisible();
        await expect(page.getByText("Official PDF").first()).toBeVisible();

        // Check horizontal overflow
        const bodyScrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
        expect(bodyScrollWidth).toBeLessThanOrEqual(vp.width + 1);
      });

      test("3. Officer Workspace Renders Responsively", async ({ page }) => {
        await page.goto("/");
        await page.getByRole("button", { name: "Officer", exact: true }).click();
        await page.getByRole("button", { name: "Sign in as officer" }).click();

        // Verify Officer Dashboard loads
        await expect(page.getByText("Recruitment Drives")).toBeVisible({ timeout: 10000 });

        // Verify Navigation exists
        const nav = page.locator("aside[aria-label='Officer Dashboard Left Navigation']");
        await expect(nav).toBeVisible();

        // Verify clicking navigation items works
        await page.getByRole("button", { name: "Students & Importer" }).click();
        await expect(page.getByText("Student Academic Registry")).toBeVisible({ timeout: 10000 });

        // Navigate to Schedule Grid
        await page.getByRole("button", { name: "Schedule Grid" }).click();
        await expect(page.getByText("Interview & Test Schedule Grid")).toBeVisible({ timeout: 10000 });

        // Navigate to Audit & Settings (top-level module 12)
        await page.getByRole("button", { name: "Audit, Backup & Settings" }).click();
        await expect(page.getByText(/Audit|Backup|Air-Gap/i).first()).toBeVisible({ timeout: 10000 });

        // Check horizontal overflow
        const bodyScrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
        expect(bodyScrollWidth).toBeLessThanOrEqual(vp.width + 1);
      });

      test("4. Coordinator Portal Renders Responsively", async ({ page }) => {
        await page.goto("/");
        await page.getByRole("button", { name: "Coordinator", exact: true }).click();
        await page.getByRole("button", { name: "Sign in as coordinator" }).click();

        // Verify Coordinator Overview
        await expect(page.getByText("Coordinator Operations Overview")).toBeVisible({ timeout: 10000 });

        // Verify Coordinator Navigation exists
        const coordNav = page.locator("aside[aria-label='Coordinator Dashboard Left Navigation']");
        await expect(coordNav).toBeVisible();

        // Check horizontal overflow
        const bodyScrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
        expect(bodyScrollWidth).toBeLessThanOrEqual(vp.width + 1);
      });

      test("5. Recruiter Portal Renders Responsively", async ({ page }) => {
        await page.goto("/");
        await page.getByRole("button", { name: "Recruiter", exact: true }).click();
        await page.getByRole("button", { name: "Sign in as recruiter" }).click();

        // Verify Recruiter Portal
        await expect(page.getByText("Tenant Isolated Corporate Portal")).toBeVisible({ timeout: 10000 });

        // Check horizontal overflow
        const bodyScrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
        expect(bodyScrollWidth).toBeLessThanOrEqual(vp.width + 1);
      });
    });
  }
});
