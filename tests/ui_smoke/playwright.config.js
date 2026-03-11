const path = require("path");
const { defineConfig } = require("@playwright/test");

const artifactDir =
  process.env.UI_SMOKE_ARTIFACT_DIR ||
  path.resolve(__dirname, "..", "..", "artifacts", "test-results", "ui-smoke");

module.exports = defineConfig({
  testDir: path.join(__dirname, "tests"),
  timeout: 60_000,
  retries: 0,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: path.join(artifactDir, "playwright-report.json") }],
    ["junit", { outputFile: path.join(artifactDir, "playwright-junit.xml") }]
  ],
  use: {
    baseURL: process.env.BASE_URL,
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "off"
  },
  outputDir: path.join(artifactDir, "test-output")
});
