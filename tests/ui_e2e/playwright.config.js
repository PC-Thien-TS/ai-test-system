const path = require("path");
const { createRequire } = require("module");

const requireFromSmoke = createRequire(path.resolve(__dirname, "..", "ui_smoke", "package.json"));
const { defineConfig } = requireFromSmoke("@playwright/test");

const artifactDir =
  process.env.UI_E2E_ARTIFACT_DIR ||
  path.resolve(__dirname, "..", "..", "artifacts", "test-results", "ui-e2e");

module.exports = defineConfig({
  testDir: path.join(__dirname, "tests"),
  timeout: 90_000,
  retries: 0,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: path.join(artifactDir, "playwright-report.json") }],
    ["junit", { outputFile: path.join(artifactDir, "playwright-junit.xml") }]
  ],
  use: {
    baseURL: process.env.BASE_URL || "http://192.168.1.7:19068",
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "off"
  },
  outputDir: path.join(artifactDir, "test-output")
});
