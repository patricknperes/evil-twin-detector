import {
  defineConfig
} from "@playwright/test";

const rendererPort =
  15173;

const backendPort =
  18765;

export default defineConfig({
  testDir:
    "./e2e",
  testMatch:
    "**/*.e2e.ts",
  fullyParallel:
    false,
  workers:
    1,
  timeout:
    45_000,
  expect: {
    timeout:
      12_000
  },
  retries:
    0,
  reporter: [
    [
      "list"
    ]
  ],
  use: {
    trace:
      "retain-on-failure",
    screenshot:
      "only-on-failure"
  },
  webServer: {
    command:
      `npm run dev -- --host 127.0.0.1 --port ${rendererPort} --strictPort`,
    url:
      `http://127.0.0.1:${rendererPort}`,
    reuseExistingServer:
      false,
    timeout:
      120_000,
    env: {
      VITE_API_BASE_URL:
        `http://127.0.0.1:${backendPort}`
    }
  }
});
