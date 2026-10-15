import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: '.', testMatch: ['health.spec.ts', 'recovery.spec.ts'], workers: 1, retries: 0,
  timeout: 90_000, expect: { timeout: 20_000 },
  reporter: [['json', { outputFile: process.env.ATLAS_QA_RUN + '/browser.json' }]],
  outputDir: process.env.ATLAS_QA_RUN + '/screenshots',
  use: { baseURL: process.env.ATLAS_QA_UI, browserName: 'chromium',
    viewport: { width: 1440, height: 1000 }, screenshot: 'only-on-failure', trace: 'off', video: 'off' },
});
