import {
  describe,
  expect,
  it
} from "vitest";

import {
  editableSettings,
  parseBoundedNumber,
  settingsChanged
} from "../src/lib/settingsUi";
import type {
  ApplicationSettingsResponse
} from "../src/types/api";

const values: ApplicationSettingsResponse["values"] = {
  request_fresh_scan: true,
  scan_wait_seconds: 4.2,
  auto_scan_enabled: false,
  auto_scan_interval_seconds: 30,
  history_page_size: 25,
  history_observation_page_size: 50,
  dashboard_recent_scans: 5,
  dashboard_recent_detections: 5,
  dashboard_trend_limit: 30,
  frontend_refresh_seconds: 10,
  show_technical_details: true,
  high_anomaly_notifications: true,
  updated_at_utc: "2026-08-31T12:00:00Z"
};

describe(
  "settings UI helpers",
  () => {
    it(
      "omits server-owned updated_at_utc from PATCH payload",
      () => {
        const patch =
          editableSettings(values);

        expect(
          Object.keys(patch)
        ).not.toContain(
          "updated_at_utc"
        );
      }
    );

    it(
      "detects unsaved changes",
      () => {
        expect(
          settingsChanged(
            values,
            values
          )
        ).toBe(false);

        expect(
          settingsChanged(
            values,
            {
              ...values,
              history_page_size: 10
            }
          )
        ).toBe(true);
      }
    );

    it(
      "clamps numeric values",
      () => {
        expect(
          parseBoundedNumber(
            "500",
            1,
            100,
            25
          )
        ).toBe(100);

        expect(
          parseBoundedNumber(
            "invalid",
            1,
            100,
            25
          )
        ).toBe(25);
      }
    );
  }
);
