const assert = require("assert");

const {
  AutoScanScheduler,
  highSuspicionNetworkIds,
  newHighSuspicionIds,
  highSuspicionNotificationText
} = require("../electron/auto-scan-scheduler.cjs");

function response(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload
  };
}

function settingsPayload({
  enabled = true,
  notifications = true
} = {}) {
  return {
    values: {
      auto_scan_enabled: enabled,
      auto_scan_interval_seconds: 30,
      high_anomaly_notifications: notifications
    }
  };
}

function scanPayload(ids) {
  return {
    scan_id: `scan-${ids.join("-") || "none"}`,
    observed_at_utc: "2026-08-31T18:00:00Z",
    total_networks: ids.length,
    networks: ids.map(
      id => ({
        network_id: id,
        analysis: {
          status: "ready",
          suspicion_level: "high",
          is_anomaly: true
        }
      })
    )
  };
}

(async () => {
  const current = highSuspicionNetworkIds({
    networks: [
      {
        network_id: "high",
        analysis: {
          status: "ready",
          suspicion_level: "high",
          is_anomaly: true
        }
      },
      {
        network_id: "unavailable",
        analysis: {
          status: "insufficient_history",
          suspicion_level: "unavailable",
          is_anomaly: null
        }
      }
    ]
  });

  assert.deepStrictEqual(
    [...current],
    ["high"]
  );

  assert.deepStrictEqual(
    newHighSuspicionIds(
      new Set(["existing"]),
      new Set(["existing", "new"])
    ),
    ["new"]
  );

  assert.ok(
    highSuspicionNotificationText(1).includes(
      "não confirma um Evil Twin"
    )
  );

  const calls = [];
  const notifications = [];
  const completions = [];
  let scanNumber = 0;

  const scheduler = new AutoScanScheduler({
    backendUrl: "http://127.0.0.1:8765",
    platformSupported: true,
    fetchImpl: async (
      url,
      options = {}
    ) => {
      calls.push({
        url,
        method: options.method || "GET"
      });

      if (url.endsWith("/settings")) {
        return response(
          200,
          settingsPayload()
        );
      }

      if (url.endsWith("/scan")) {
        scanNumber += 1;

        return response(
          200,
          scanPayload(["A"])
        );
      }

      throw new Error(
        `unexpected URL: ${url}`
      );
    },
    onHighSuspicion: async event => {
      notifications.push(event);
    },
    onScanCompleted: async event => {
      completions.push(event);
    }
  });

  const first = await scheduler.runOnce();

  assert.strictEqual(
    first.outcome,
    "scan_completed"
  );

  assert.strictEqual(
    first.newHighCount,
    1
  );

  assert.strictEqual(
    notifications.length,
    1
  );

  assert.strictEqual(
    completions.length,
    1
  );

  assert.strictEqual(
    completions[0].observedAtUtc,
    "2026-08-31T18:00:00Z"
  );

  const second = await scheduler.runOnce();

  assert.strictEqual(
    second.newHighCount,
    0
  );

  assert.strictEqual(
    notifications.length,
    1,
    "same high network must not notify repeatedly"
  );

  assert.ok(
    calls.some(
      call =>
        call.url.endsWith("/scan")
        && call.method === "POST"
    )
  );

  let scanCalled = false;

  const disabled = new AutoScanScheduler({
    backendUrl: "http://127.0.0.1:8765",
    platformSupported: true,
    fetchImpl: async url => {
      if (url.endsWith("/settings")) {
        return response(
          200,
          settingsPayload({
            enabled: false
          })
        );
      }

      scanCalled = true;
      return response(
        200,
        scanPayload([])
      );
    }
  });

  const disabledResult =
    await disabled.runOnce();

  assert.strictEqual(
    disabledResult.outcome,
    "disabled"
  );

  assert.strictEqual(
    scanCalled,
    false
  );

  const conflict = new AutoScanScheduler({
    backendUrl: "http://127.0.0.1:8765",
    platformSupported: true,
    fetchImpl: async url => {
      if (url.endsWith("/settings")) {
        return response(
          200,
          settingsPayload()
        );
      }

      return response(
        409,
        {
          detail: {
            code: "scan_in_progress"
          }
        }
      );
    }
  });

  const conflictResult =
    await conflict.runOnce();

  assert.strictEqual(
    conflictResult.outcome,
    "skipped_backend_scan_in_progress"
  );

  assert.strictEqual(
    conflict.status().lastError,
    null
  );

  console.log(
    "auto-scan scheduler contracts OK"
  );
})().catch(
  error => {
    console.error(error);
    process.exitCode = 1;
  }
);
