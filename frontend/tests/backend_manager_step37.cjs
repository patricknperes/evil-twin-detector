const assert =
  require("assert");
const path =
  require("path");

const {
  DEFAULT_BACKEND_URL,
  HEALTH_URL,
  resolveBackendCommand
} = require(
  "../electron/backend-manager.cjs"
);

assert.strictEqual(
  DEFAULT_BACKEND_URL,
  "http://127.0.0.1:8765"
);

assert.strictEqual(
  HEALTH_URL,
  "http://127.0.0.1:8765/health"
);

const fakeApp = {};

const dev =
  resolveBackendCommand({
    app: fakeApp,
    isDev: true
  });

assert.strictEqual(
  dev.mode,
  "development_python_module"
);

assert.deepStrictEqual(
  dev.args,
  [
    "-m",
    "backend"
  ]
);

assert.strictEqual(
  path.basename(
    dev.cwd
  ),
  "evil-twin-detector"
);

const originalResourcesPath =
  process.resourcesPath;

Object.defineProperty(
  process,
  "resourcesPath",
  {
    value:
      path.join(
        "C:",
        "App",
        "resources"
      ),
    configurable:
      true
  }
);

const packaged =
  resolveBackendCommand({
    app: fakeApp,
    isDev: false
  });

assert.strictEqual(
  packaged.mode,
  "packaged_executable"
);

assert.ok(
  packaged.command.endsWith(
    path.join(
      "backend",
      "evil-twin-backend.exe"
    )
  )
);

if (
  originalResourcesPath
  !== undefined
) {
  Object.defineProperty(
    process,
    "resourcesPath",
    {
      value:
        originalResourcesPath,
      configurable:
        true
    }
  );
}

console.log(
  "backend-manager contracts OK"
);
