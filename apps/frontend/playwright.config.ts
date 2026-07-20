import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './src/e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  forbidOnly: true,
  retries: 1,
  workers: 1,
  reporter: [['html', { outputFolder: '../../output/playwright/report' }], ['list']],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    screenshot: 'on',
    video: 'off',
  },
  projects: [
    {
      name: 'Mobile — 375×812',
      use: { ...devices['iPhone 13 Pro'], viewport: { width: 375, height: 812 } },
    },
    {
      name: 'Tablet — 768×1024',
      use: { ...devices['iPad Mini'], viewport: { width: 768, height: 1024 } },
    },
    {
      name: 'Desktop — 1280×800',
      use: { viewport: { width: 1280, height: 800 } },
    },
    {
      name: 'Wide — 1440×900',
      use: { viewport: { width: 1440, height: 900 } },
    },
  ],
});
