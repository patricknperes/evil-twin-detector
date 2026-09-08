const assert =
  require("assert");
const http =
  require("http");

const {
  AutoScanScheduler
} = require(
  "../electron/auto-scan-scheduler.cjs"
);

function listen(
  server,
  port = 0
) {
  return new Promise(
    (
      resolve,
      reject
    ) => {
      server.once(
        "error",
        reject
      );

      server.listen(
        port,
        "127.0.0.1",
        () => {
          server.removeListener(
            "error",
            reject
          );

          resolve(
            server.address().port
          );
        }
      );
    }
  );
}

function close(
  server
) {
  return new Promise(
    (
      resolve,
      reject
    ) => {
      server.close(
        error => {
          if (error) {
            reject(
              error
            );
            return;
          }

          resolve();
        }
      );
    }
  );
}

function json(
  response,
  status,
  payload
) {
  const body =
    JSON.stringify(
      payload
    );

  response.writeHead(
    status,
    {
      "content-type":
        "application/json",
      "content-length":
        Buffer.byteLength(
          body
        )
    }
  );

  response.end(
    body
  );
}

(async () => {
  // Reserve an ephemeral port, then deliberately leave it offline.
  const reservation =
    http.createServer();

  const port =
    await listen(
      reservation
    );

  await close(
    reservation
  );

  const notifications = [];
  const completions = [];

  const scheduler =
    new AutoScanScheduler({
      backendUrl:
        `http://127.0.0.1:${port}`,
      platformSupported:
        true,
      onHighSuspicion:
        async event => {
          notifications.push(
            event
          );
        },
      onScanCompleted:
        async event => {
          completions.push(
            event
          );
        },
      logger: {
        error:
          () => {}
      }
    });

  const offline =
    await scheduler.runOnce();

  assert.strictEqual(
    offline.outcome,
    "settings_error"
  );

  let conflict =
    false;

  let scanCount =
    0;

  const backend =
    http.createServer(
      (
        request,
        response
      ) => {
        if (
          request.method
            === "GET"
          && request.url
            === "/settings"
        ) {
          json(
            response,
            200,
            {
              values: {
                auto_scan_enabled:
                  true,
                auto_scan_interval_seconds:
                  30,
                high_anomaly_notifications:
                  true
              }
            }
          );
          return;
        }

        if (
          request.method
            === "POST"
          && request.url
            === "/scan"
        ) {
          if (
            conflict
          ) {
            json(
              response,
              409,
              {
                detail: {
                  code:
                    "scan_in_progress"
                }
              }
            );
            return;
          }

          scanCount += 1;

          json(
            response,
            200,
            {
              scan_id:
                `step48-scan-${scanCount}`,
              observed_at_utc:
                "2026-09-01T18:00:00Z",
              total_networks:
                1,
              networks: [
                {
                  network_id:
                    "transient-network-id",
                  analysis: {
                    status:
                      "ready",
                    suspicion_level:
                      "high",
                    is_anomaly:
                      true
                  }
                }
              ]
            }
          );
          return;
        }

        json(
          response,
          404,
          {
            detail:
              "not_found"
          }
        );
      }
    );

  await listen(
    backend,
    port
  );

  const recovered =
    await scheduler.runOnce();

  assert.strictEqual(
    recovered.outcome,
    "scan_completed"
  );

  assert.strictEqual(
    recovered.newHighCount,
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
    completions[0]
      .observedAtUtc,
    "2026-09-01T18:00:00Z"
  );

  const repeated =
    await scheduler.runOnce();

  assert.strictEqual(
    repeated.outcome,
    "scan_completed"
  );

  assert.strictEqual(
    repeated.newHighCount,
    0
  );

  assert.strictEqual(
    notifications.length,
    1,
    "A mesma rede que permanece HIGH não deve gerar spam."
  );

  conflict =
    true;

  const concurrent =
    await scheduler.runOnce();

  assert.strictEqual(
    concurrent.outcome,
    "skipped_backend_scan_in_progress"
  );

  await close(
    backend
  );

  const offlineAgain =
    await scheduler.runOnce();

  assert.strictEqual(
    offlineAgain.outcome,
    "settings_error"
  );

  console.log(
    JSON.stringify({
      schema_version:
        "desktop_integration_electron_v1",
      status:
        "passed",
      scenarios: {
        backend_offline:
          true,
        backend_recovery:
          true,
        automatic_scan_real_http_fetch:
          true,
        high_suspicion_notification:
          true,
        repeated_high_deduplicated:
          true,
        scan_in_progress_conflict:
          true,
        backend_loss_after_recovery:
          true
      },
      real_windows_native_wifi_used:
        false,
      real_scientific_artifacts_used:
        false,
      os_notification_displayed:
        false
    })
  );
})().catch(
  error => {
    console.error(
      error
    );
    process.exitCode =
      1;
  }
);
