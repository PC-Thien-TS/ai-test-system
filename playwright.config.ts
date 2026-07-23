import 'dotenv/config';
import { defineConfig, devices } from '@playwright/test';

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './e2e',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('')`. */
    baseURL: process.env.BASE_URL,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    permissions: ['local-network-access'],
  },

  projects: [
    {
      name: 'chromium',
      testMatch: [
        /.*[\\/]smoke[\\/]login\.spec\.ts/,
        /.*[\\/]environment[\\/].*\.spec\.ts/,
      ],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'setup-N13',
      testMatch: /.*[\\/]setup[\\/]N13\.setup\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'setup-N03',
      testMatch: /.*[\\/]setup[\\/]N03\.setup\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'setup-N02',
      testMatch: /.*[\\/]setup[\\/]N02\.setup\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'N13',
      dependencies: ['setup-N13'],
      testMatch: [
        /.*[\\/]smoke[\\/]role-session\.spec\.ts/,
        /.*[\\/]smoke[\\/]patient\.spec\.ts/,
        /.*[\\/]critical-flows[\\/].*\.spec\.ts/,
        /.*[\\/]regression[\\/].*\.spec\.ts/,
      ],
      testIgnore: [
        /.*[\\/]setup[\\/].*/,
        /.*[\\/]smoke[\\/]login\.spec\.ts/,
      ],
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/N13.json',
      },
    },
    {
      name: 'N03',
      dependencies: ['setup-N03'],
      testMatch: [
        /.*[\\/]smoke[\\/]role-session\.spec\.ts/,
        /.*[\\/]critical-flows[\\/].*\.spec\.ts/,
        /.*[\\/]regression[\\/].*\.spec\.ts/,
      ],
      testIgnore: [
        /.*[\\/]setup[\\/].*/,
        /.*[\\/]smoke[\\/]login\.spec\.ts/,
      ],
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/N03.json',
      },
    },
    {
      name: 'N02',
      dependencies: ['setup-N02'],
      testMatch: [
        /.*[\\/]smoke[\\/]role-session\.spec\.ts/,
        /.*[\\/]critical-flows[\\/].*\.spec\.ts/,
        /.*[\\/]regression[\\/].*\.spec\.ts/,
      ],
      testIgnore: [
        /.*[\\/]setup[\\/].*/,
        /.*[\\/]smoke[\\/]login\.spec\.ts/,
      ],
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/N02.json',
      },
    },
  ],

  /* Run your local dev server before starting the tests */
  // webServer: {
  //   command: 'npm run start',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: !process.env.CI,
  // },
});
