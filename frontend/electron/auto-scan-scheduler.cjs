const DEFAULT_DISABLED_POLL_MS = 5000;

function asIso(milliseconds) {
  return new Date(milliseconds).toISOString();
}

function highSuspicionNetworkIds(scan) {
  return new Set(
    (scan?.networks || [])
      .filter(
        network =>
          network?.analysis?.status === "ready"
          && network?.analysis?.suspicion_level === "high"
          && network?.analysis?.is_anomaly === true
      )
      .map(network => network.network_id)
      .filter(Boolean)
  );
}

function newHighSuspicionIds(previous, current) {
  return [...current].filter(
    id => !previous.has(id)
  );
}

function highSuspicionNotificationText(count) {
  if (count === 1) {
    return (
      "Uma rede observada apresentou alta suspeita. "
      + "Isso não confirma um Evil Twin; abra o aplicativo para revisar."
    );
  }

  return (
    `${count} redes observadas apresentaram alta suspeita. `
    + "Isso não confirma um Evil Twin; abra o aplicativo para revisar."
  );
}

class AutoScanScheduler {
  constructor({
    backendUrl,
    fetchImpl = fetch,
    onHighSuspicion = async () => {},
    onScanCompleted = async () => {},
    logger = console,
    disabledPollMs = DEFAULT_DISABLED_POLL_MS,
    setTimeoutImpl = setTimeout,
    clearTimeoutImpl = clearTimeout,
    now = () => Date.now(),
    platformSupported = process.platform === "win32"
  }) {
    this.backendUrl = backendUrl.replace(/\/+$/, "");
    this.fetchImpl = fetchImpl;
    this.onHighSuspicion = onHighSuspicion;
    this.onScanCompleted = onScanCompleted;
    this.logger = logger;
    this.disabledPollMs = disabledPollMs;
    this.setTimeoutImpl = setTimeoutImpl;
    this.clearTimeoutImpl = clearTimeoutImpl;
    this.now = now;
    this.platformSupported = platformSupported;

    this.active = false;
    this.timer = null;
    this.inFlight = false;
    this.settings = null;
    this.previousHighIds = new Set();

    this.state = {
      status: platformSupported
        ? "stopped"
        : "unsupported_platform",
      enabled: false,
      intervalSeconds: null,
      notificationsEnabled: false,
      inFlight: false,
      nextRunAt: null,
      lastStartedAt: null,
      lastCompletedAt: null,
      lastScanId: null,
      lastOutcome: null,
      lastError: null,
      lastHighCount: 0,
      lastNewHighCount: 0
    };
  }

  status() {
    return {
      ...this.state
    };
  }

  _clearTimer() {
    if (this.timer !== null) {
      this.clearTimeoutImpl(this.timer);
      this.timer = null;
    }

    this.state.nextRunAt = null;
  }

  _schedule(delayMs) {
    if (!this.active || !this.platformSupported) {
      return;
    }

    this._clearTimer();

    const boundedDelay = Math.max(
      1,
      Number(delayMs) || 1
    );

    this.state.nextRunAt = asIso(
      this.now() + boundedDelay
    );

    this.timer = this.setTimeoutImpl(
      () => {
        this.timer = null;
        void this._timerTick();
      },
      boundedDelay
    );
  }

  async _jsonRequest(path, options = {}) {
    const response = await this.fetchImpl(
      `${this.backendUrl}${path}`,
      {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {})
        }
      }
    );

    const payload = await response
      .json()
      .catch(() => null);

    return {
      response,
      payload
    };
  }

  async _readSettings() {
    const {
      response,
      payload
    } = await this._jsonRequest(
      "/settings"
    );

    if (!response.ok || !payload?.values) {
      throw new Error(
        `Unable to read auto-scan settings (${response.status}).`
      );
    }

    this.settings = payload.values;

    this.state.enabled = Boolean(
      this.settings.auto_scan_enabled
    );

    this.state.intervalSeconds = Number(
      this.settings.auto_scan_interval_seconds
    );

    this.state.notificationsEnabled = Boolean(
      this.settings.high_anomaly_notifications
    );

    return this.settings;
  }

  _scheduleFromSettings() {
    if (
      !this.active
      || !this.platformSupported
      || this.inFlight
    ) {
      return;
    }

    if (this.settings?.auto_scan_enabled) {
      const intervalMs = Math.max(
        10000,
        Number(
          this.settings.auto_scan_interval_seconds
        ) * 1000
      );

      this.state.status = "waiting";
      this._schedule(intervalMs);
      return;
    }

    this.previousHighIds.clear();
    this.state.status = "disabled";
    this._schedule(this.disabledPollMs);
  }

  async start() {
    if (!this.platformSupported) {
      this.state.status = "unsupported_platform";
      return this.status();
    }

    this.active = true;
    await this.refresh();
    return this.status();
  }

  async refresh() {
    if (!this.platformSupported) {
      this.state.status = "unsupported_platform";
      return this.status();
    }

    this._clearTimer();

    try {
      await this._readSettings();
      this.state.lastError = null;
    } catch (error) {
      this.state.status = "settings_error";
      this.state.lastError =
        error?.message || String(error);

      if (this.active && !this.inFlight) {
        this._schedule(this.disabledPollMs);
      }

      return this.status();
    }

    if (!this.inFlight) {
      this._scheduleFromSettings();
    }

    return this.status();
  }

  stop() {
    this.active = false;
    this._clearTimer();

    this.state.status = this.platformSupported
      ? "stopped"
      : "unsupported_platform";

    this.state.enabled = false;
    this.state.inFlight = this.inFlight;
  }

  async runOnce() {
    if (!this.platformSupported) {
      this.state.status = "unsupported_platform";
      return {
        outcome: "unsupported_platform"
      };
    }

    let settings;

    try {
      settings = await this._readSettings();
      this.state.lastError = null;
    } catch (error) {
      this.state.status = "settings_error";
      this.state.lastError =
        error?.message || String(error);

      return {
        outcome: "settings_error"
      };
    }

    if (!settings.auto_scan_enabled) {
      this.previousHighIds.clear();
      this.state.status = "disabled";

      return {
        outcome: "disabled"
      };
    }

    if (this.inFlight) {
      this.state.lastOutcome =
        "skipped_local_in_flight";

      return {
        outcome: "skipped_local_in_flight"
      };
    }

    this.inFlight = true;
    this.state.inFlight = true;
    this.state.status = "scanning";
    this.state.lastStartedAt = asIso(
      this.now()
    );

    try {
      const {
        response,
        payload
      } = await this._jsonRequest(
        "/scan",
        {
          method: "POST",
          body: JSON.stringify({})
        }
      );

      if (
        response.status === 409
        && payload?.detail?.code === "scan_in_progress"
      ) {
        this.state.lastOutcome =
          "skipped_backend_scan_in_progress";

        this.state.lastError = null;

        return {
          outcome: "skipped_backend_scan_in_progress"
        };
      }

      if (!response.ok || !payload) {
        const code =
          payload?.detail?.code
          || `http_${response.status}`;

        throw new Error(
          `Automatic scan failed: ${code}.`
        );
      }

      const currentHigh =
        highSuspicionNetworkIds(
          payload
        );

      const newlyHigh =
        newHighSuspicionIds(
          this.previousHighIds,
          currentHigh
        );

      this.previousHighIds =
        currentHigh;

      this.state.lastScanId =
        payload.scan_id || null;

      this.state.lastHighCount =
        currentHigh.size;

      this.state.lastNewHighCount =
        newlyHigh.length;

      this.state.lastOutcome =
        "scan_completed";

      this.state.lastError = null;

      if (
        settings.high_anomaly_notifications
        && newlyHigh.length > 0
      ) {
        await this.onHighSuspicion({
          scanId: payload.scan_id || null,
          count: newlyHigh.length,
          highCount: currentHigh.size,
          networkIds: newlyHigh
        });
      }

      await this.onScanCompleted({
        scanId: payload.scan_id || null,
        observedAtUtc:
          payload.observed_at_utc
          || null,
        totalNetworks:
          Number(payload.total_networks)
          || 0,
        highCount: currentHigh.size,
        newHighCount: newlyHigh.length
      });

      return {
        outcome: "scan_completed",
        scan: payload,
        highCount: currentHigh.size,
        newHighCount: newlyHigh.length
      };
    } catch (error) {
      this.state.status = "scan_error";
      this.state.lastOutcome = "scan_error";
      this.state.lastError =
        error?.message || String(error);

      this.logger.error(
        "[auto-scan]",
        this.state.lastError
      );

      return {
        outcome: "scan_error",
        error: this.state.lastError
      };
    } finally {
      this.inFlight = false;
      this.state.inFlight = false;
      this.state.lastCompletedAt = asIso(
        this.now()
      );
    }
  }

  async _timerTick() {
    if (!this.active) {
      return;
    }

    await this.runOnce();

    if (this.active) {
      await this.refresh();
    }
  }
}

module.exports = {
  AutoScanScheduler,
  DEFAULT_DISABLED_POLL_MS,
  highSuspicionNetworkIds,
  newHighSuspicionIds,
  highSuspicionNotificationText
};
