const {
  app,
  BrowserWindow,
  Notification,
  dialog,
  ipcMain,
  shell
} = require("electron");
const path = require("path");

const {
  BackendProcessManager,
  DEFAULT_BACKEND_URL
} = require("./backend-manager.cjs");

const {
  AutoScanScheduler,
  highSuspicionNotificationText
} = require("./auto-scan-scheduler.cjs");

const isDev =
  !app.isPackaged;

const e2eMode =
  process.env
    .EVIL_TWIN_E2E
  === "1";

const e2eRendererUrl =
  process.env
    .EVIL_TWIN_E2E_RENDERER_URL;

const e2eForceScheduler =
  e2eMode
  && process.env
    .EVIL_TWIN_E2E_FORCE_SCHEDULER
  === "1";

if (
  process.platform
  === "win32"
) {
  app.setAppUserModelId(
    "br.edu.ufop.eviltwindetector"
  );
}

let mainWindow = null;

const backend =
  new BackendProcessManager({
    app,
    isDev
  });

function showHighSuspicionNotification({
  count
}) {
  // Renderer/Electron E2E must never create an OS notification.
  if (
    e2eMode
  ) {
    return;
  }

  if (
    !Notification.isSupported()
  ) {
    return;
  }

  const notification =
    new Notification({
      title:
        count === 1
          ? "Rede Wi-Fi com alta suspeita"
          : "Redes Wi-Fi com alta suspeita",
      body:
        highSuspicionNotificationText(
          count
        ),
      silent:
        false
    });

  notification.on(
    "click",
    () => {
      if (
        mainWindow
        && !mainWindow.isDestroyed()
      ) {
        if (
          mainWindow.isMinimized()
        ) {
          mainWindow.restore();
        }

        mainWindow.show();
        mainWindow.focus();
      }
    }
  );

  notification.show();
}

const autoScanScheduler =
  new AutoScanScheduler({
    backendUrl:
      DEFAULT_BACKEND_URL,
    platformSupported:
      (
        process.platform
        === "win32"
      )
      || e2eForceScheduler,
    onHighSuspicion:
      showHighSuspicionNotification,
    onScanCompleted:
      async summary => {
        if (
          mainWindow
          && !mainWindow.isDestroyed()
        ) {
          mainWindow
            .webContents
            .send(
              "desktop:auto-scan-completed",
              summary
            );
        }
      }
  });

function createWindow() {
  const win =
    new BrowserWindow({
      width:
        1440,
      height:
        900,
      minWidth:
        1100,
      minHeight:
        720,
      show:
        false,
      autoHideMenuBar:
        true,
      backgroundColor:
        "#f8fafc",
      webPreferences: {
        preload:
          path.join(
            __dirname,
            "preload.cjs"
          ),
        contextIsolation:
          true,
        nodeIntegration:
          false,
        sandbox:
          true
      }
    });

  mainWindow =
    win;

  win.once(
    "ready-to-show",
    () => {
      win.show();
    }
  );

  win.on(
    "closed",
    () => {
      if (
        mainWindow
        === win
      ) {
        mainWindow =
          null;
      }
    }
  );

  win.webContents.setWindowOpenHandler(
    ({
      url
    }) => {
      shell.openExternal(
        url
      );

      return {
        action:
          "deny"
      };
    }
  );

  if (
    isDev
  ) {
    win.loadURL(
      (
        e2eMode
        && e2eRendererUrl
      )
        ? e2eRendererUrl
        : "http://127.0.0.1:5173"
    );
  } else {
    win.loadFile(
      path.join(
        __dirname,
        "../dist/index.html"
      )
    );
  }

  return win;
}

ipcMain.handle(
  "desktop:open-location-settings",
  async () => {
    if (
      process.platform
      !== "win32"
    ) {
      return {
        ok: false,
        reason:
          "unsupported_platform"
      };
    }

    await shell.openExternal(
      "ms-settings:privacy-location"
    );

    return {
      ok: true
    };
  }
);

ipcMain.handle(
  "desktop:backend-status",
  () =>
    backend.status()
);

ipcMain.handle(
  "desktop:auto-scan-status",
  () =>
    autoScanScheduler.status()
);

ipcMain.handle(
  "desktop:auto-scan-refresh",
  async () =>
    autoScanScheduler.refresh()
);


if (
  e2eMode
) {
  ipcMain.handle(
    "desktop:e2e-run-auto-scan",
    async () =>
      autoScanScheduler.runOnce()
  );
}

async function startDesktop() {
  try {
    await backend.ensureReady();

    createWindow();

    await autoScanScheduler.start();
  } catch (
    error
  ) {
    const details = [
      error
        ?.message
      || String(
        error
      ),
      backend.stderrTail
        ? `\nBackend:\n${backend.stderrTail}`
        : ""
    ]
      .join("")
      .slice(
        -10000
      );

    dialog.showErrorBox(
      "Não foi possível iniciar o backend",
      [
        "O aplicativo não conseguiu iniciar o serviço local necessário.",
        "",
        details,
        "",
        "Feche esta mensagem e tente iniciar o aplicativo novamente."
      ].join("\n")
    );

    await backend.stop();

    app.quit();
  }
}

app.whenReady().then(
  () =>
    startDesktop()
);

app.on(
  "activate",
  () => {
    if (
      BrowserWindow
        .getAllWindows()
        .length
      === 0
    ) {
      if (
        backend
          .status()
          .ready
      ) {
        createWindow();
      } else {
        void startDesktop();
      }
    }
  }
);

app.on(
  "before-quit",
  event => {
    autoScanScheduler.stop();

    if (
      backend.startedByElectron
      && backend.child
    ) {
      event.preventDefault();

      backend.stop()
        .finally(
          () => {
            backend.startedByElectron =
              false;

            app.quit();
          }
        );
    }
  }
);

app.on(
  "window-all-closed",
  () => {
    if (
      process.platform
      !== "darwin"
    ) {
      app.quit();
    }
  }
);
