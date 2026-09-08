const {
  spawn
} = require("child_process");
const path = require("path");

const DEFAULT_BACKEND_URL =
  process.env.EVIL_TWIN_BACKEND_URL
  || "http://127.0.0.1:8765";

const HEALTH_URL =
  `${DEFAULT_BACKEND_URL}/health`;

const STARTUP_TIMEOUT_MS =
  Number(
    process.env.EVIL_TWIN_BACKEND_STARTUP_TIMEOUT_MS
    || 15000
  );

const POLL_INTERVAL_MS = 250;

function sleep(
  milliseconds
) {
  return new Promise(
    resolve => setTimeout(
      resolve,
      milliseconds
    )
  );
}

async function healthCheck({
  timeoutMs = 1000
} = {}) {
  const controller =
    new AbortController();

  const timer = setTimeout(
    () =>
      controller.abort(),
    timeoutMs
  );

  try {
    const response = await fetch(
      HEALTH_URL,
      {
        method: "GET",
        signal: controller.signal
      }
    );

    if (!response.ok) {
      return {
        ok: false,
        status:
          response.status,
        payload: null
      };
    }

    const payload =
      await response.json();

    return {
      ok:
        payload
          ?.status
        === "ok",
      status:
        response.status,
      payload
    };
  } catch {
    return {
      ok: false,
      status: null,
      payload: null
    };
  } finally {
    clearTimeout(
      timer
    );
  }
}

function resolveBackendCommand({
  app,
  isDev
}) {
  const explicitExecutable =
    process.env
      .EVIL_TWIN_BACKEND_EXECUTABLE;

  if (
    explicitExecutable
  ) {
    return {
      command:
        explicitExecutable,
      args: [],
      cwd:
        path.dirname(
          explicitExecutable
        ),
      mode:
        "explicit_executable"
    };
  }

  if (
    !isDev
  ) {
    const executable =
      path.join(
        process.resourcesPath,
        "backend",
        "evil-twin-backend.exe"
      );

    return {
      command:
        executable,
      args: [],
      cwd:
        path.dirname(
          executable
        ),
      mode:
        "packaged_executable"
    };
  }

  const python =
    process.env
      .EVIL_TWIN_PYTHON
    || (
      process.platform
      === "win32"
        ? "python"
        : "python3"
    );

  const projectRoot =
    path.resolve(
      __dirname,
      "../.."
    );

  return {
    command:
      python,
    args: [
      "-m",
      "backend"
    ],
    cwd:
      projectRoot,
    mode:
      "development_python_module"
  };
}

class BackendProcessManager {
  constructor({
    app,
    isDev,
    logger = console
  }) {
    this.app = app;
    this.isDev = isDev;
    this.logger = logger;
    this.child = null;
    this.startedByElectron = false;
    this.stderrTail = "";
    this.stdoutTail = "";
    this.lastHealth = null;
    this.mode = null;
  }

  appendTail(
    current,
    chunk
  ) {
    const next =
      current
      + String(
        chunk
      );

    return next.slice(
      -8000
    );
  }

  status() {
    return {
      backendUrl:
        DEFAULT_BACKEND_URL,
      healthUrl:
        HEALTH_URL,
      ready:
        Boolean(
          this.lastHealth
            ?.ok
        ),
      startedByElectron:
        this.startedByElectron,
      pid:
        this.child
          ?.pid
        ?? null,
      mode:
        this.mode,
      stderrTail:
        this.stderrTail
    };
  }

  async ensureReady() {
    const existing =
      await healthCheck();

    if (
      existing.ok
    ) {
      this.lastHealth =
        existing;

      this.startedByElectron =
        false;

      this.mode =
        "existing_backend";

      this.logger.info(
        "[backend] healthy backend already available"
      );

      return this.status();
    }

    this.start();

    await this.waitUntilReady();

    return this.status();
  }

  start() {
    if (
      this.child
    ) {
      return;
    }

    const command =
      resolveBackendCommand({
        app:
          this.app,
        isDev:
          this.isDev
      });

    this.mode =
      command.mode;

    this.logger.info(
      `[backend] starting (${command.mode})`,
      command.command,
      command.args.join(" ")
    );

    this.child = spawn(
      command.command,
      command.args,
      {
        cwd:
          command.cwd,
        env: {
          ...process.env,
          PYTHONUNBUFFERED:
            "1"
        },
        windowsHide:
          true,
        stdio: [
          "ignore",
          "pipe",
          "pipe"
        ]
      }
    );

    this.startedByElectron =
      true;

    this.child.stdout?.on(
      "data",
      chunk => {
        this.stdoutTail =
          this.appendTail(
            this.stdoutTail,
            chunk
          );

        this.logger.info(
          `[backend:stdout] ${String(chunk).trim()}`
        );
      }
    );

    this.child.stderr?.on(
      "data",
      chunk => {
        this.stderrTail =
          this.appendTail(
            this.stderrTail,
            chunk
          );

        this.logger.error(
          `[backend:stderr] ${String(chunk).trim()}`
        );
      }
    );

    this.child.on(
      "error",
      error => {
        this.stderrTail =
          this.appendTail(
            this.stderrTail,
            error.stack
            || error.message
          );
      }
    );

    this.child.on(
      "exit",
      (
        code,
        signal
      ) => {
        this.logger.info(
          `[backend] exited code=${code} signal=${signal}`
        );

        this.child =
          null;
      }
    );
  }

  async waitUntilReady() {
    const startedAt =
      Date.now();

    while (
      Date.now()
      - startedAt
      < STARTUP_TIMEOUT_MS
    ) {
      if (
        this.startedByElectron
        && !this.child
      ) {
        throw new Error(
          "O processo do backend encerrou antes de ficar disponível."
        );
      }

      const health =
        await healthCheck();

      if (
        health.ok
      ) {
        this.lastHealth =
          health;

        this.logger.info(
          "[backend] health check ready"
        );

        return;
      }

      await sleep(
        POLL_INTERVAL_MS
      );
    }

    throw new Error(
      `O backend não respondeu em ${STARTUP_TIMEOUT_MS} ms.`
    );
  }

  async stop() {
    if (
      !this.startedByElectron
      || !this.child
    ) {
      return;
    }

    const child =
      this.child;

    this.child =
      null;

    this.logger.info(
      `[backend] stopping pid=${child.pid}`
    );

    if (
      process.platform
      === "win32"
      && child.pid
    ) {
      await new Promise(
        resolve => {
          const killer = spawn(
            "taskkill",
            [
              "/pid",
              String(
                child.pid
              ),
              "/T",
              "/F"
            ],
            {
              windowsHide:
                true,
              stdio:
                "ignore"
            }
          );

          killer.once(
            "exit",
            () =>
              resolve()
          );

          killer.once(
            "error",
            () => {
              try {
                child.kill();
              } catch {
                // Process may already be gone.
              }

              resolve();
            }
          );
        }
      );

      return;
    }

    try {
      child.kill(
        "SIGTERM"
      );
    } catch {
      // Process may already be gone.
    }
  }
}

module.exports = {
  BackendProcessManager,
  DEFAULT_BACKEND_URL,
  HEALTH_URL,
  STARTUP_TIMEOUT_MS,
  healthCheck,
  resolveBackendCommand
};
