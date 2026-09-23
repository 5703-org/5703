import { defineConfig } from '@playwright/test';

const runId = new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-');

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60000,
  fullyParallel: false,
  workers: 1,
  reporter: [['list'], ['json', { outputFile: `../artifacts/reports/frontend/runs/${runId}/results.json` }]],
  outputDir: `../artifacts/reports/frontend/runs/${runId}/browser-artifacts`,
  use: {
    baseURL: process.env.FRONTEND_URL || 'http://127.0.0.1:5173',
    channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
});
