import {
  describe,
  expect,
  it
} from "vitest";

import type {
  AutoScanCompletedEvent
} from "../src/types/desktop";

describe(
  "automatic scan view refresh contract",
  () => {
    it(
      "does not expose clear Wi-Fi identifiers in the event payload",
      () => {
        const event: AutoScanCompletedEvent = {
          scanId: "scan-123",
          observedAtUtc: "2026-08-31T18:00:00Z",
          totalNetworks: 12,
          highCount: 2,
          newHighCount: 1
        };

        expect(event.totalNetworks).toBe(12);
        expect(Object.keys(event)).not.toContain("ssid");
        expect(Object.keys(event)).not.toContain("bssid");
      }
    );
  }
);
