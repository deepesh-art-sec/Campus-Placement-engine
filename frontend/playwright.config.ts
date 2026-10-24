import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60000,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3000",
    channel: "chrome",
    trace: "on-first-retry",
    headless: true,
  },
  webServer: [
    {
      command: "python -m uvicorn backend.app.api.main:app --host 127.0.0.1 --port 8000",
      cwd: "..",
      url: "http://127.0.0.1:8000/docs",
      reuseExistingServer: true,
      timeout: 30000,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 3000",
      cwd: ".",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: true,
      timeout: 30000,
    },
  ],
});
