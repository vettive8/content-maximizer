import { defineConfig } from '@playwright/test';

const apiBaseUrl = process.env.API_BASE_URL || 'http://127.0.0.1:5011';
const appBaseUrl = process.env.APP_BASE_URL || 'http://127.0.0.1:5181';
const slowMo = Number(process.env.PLAYWRIGHT_LIVE_SLOWMO || 0);

process.env.API_BASE_URL = apiBaseUrl;

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  expect: {
    timeout: 10_000
  },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['line']],
  webServer: [
    {
      command: `node tests/e2e/start-backend.mjs ${new URL(apiBaseUrl).port || 5000}`,
      url: `${apiBaseUrl}/api/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 45_000
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5181',
      url: appBaseUrl,
      reuseExistingServer: !process.env.CI,
      timeout: 45_000,
      env: {
        ...process.env,
        VITE_API_BASE_URL: apiBaseUrl
      }
    }
  ],
  use: {
    baseURL: appBaseUrl,
    channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome',
    viewport: { width: 1440, height: 960 },
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
    launchOptions: {
      slowMo
    }
  },
  outputDir: 'test-results'
});
