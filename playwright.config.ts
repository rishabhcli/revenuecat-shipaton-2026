import { defineConfig } from '@playwright/test';

const testHarnessHost = '127.0.0.1';
const testHarnessPort = 4222;
const testHarnessURL = `http://${testHarnessHost}:${testHarnessPort}`;

export default defineConfig({
  testDir: './Tests/e2e',
  outputDir: './.dev/playwright-results',
  use: {
    baseURL: testHarnessURL,
    browserName: 'chromium',
    storageState: './.dev/pw-profile/storage-state.json',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'python3 scripts/devctl.py e2e-server --timeout 10',
    url: `${testHarnessURL}/health/ready`,
    reuseExistingServer: false,
    gracefulShutdown: { signal: 'SIGTERM', timeout: 45_000 },
    timeout: 45_000,
  },
});
