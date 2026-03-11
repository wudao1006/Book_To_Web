import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  use: {
    baseURL: "http://127.0.0.1:4173",
    headless: true,
    launchOptions: {
      executablePath: "/usr/bin/google-chrome-stable",
      args: [
        "--disable-dev-shm-usage",
        "--no-first-run",
        "--no-default-browser-check",
        "--no-sandbox"
      ]
    }
  },
  webServer: [
    {
      command:
        "env PYTHONPATH=/home/wudao/BTW /home/wudao/BTW/btw/.venv/bin/python -m uvicorn btw.main:app --host 127.0.0.1 --port 8000",
      port: 8000,
      reuseExistingServer: true,
      timeout: 240_000
    },
    {
      command: "npm run preview -- --host 127.0.0.1 --port 4173",
      port: 4173,
      reuseExistingServer: true,
      timeout: 240_000
    }
  ]
});
