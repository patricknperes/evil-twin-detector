const {
  contextBridge,
  ipcRenderer
} = require("electron");

const e2eMode =
  process.env
    .EVIL_TWIN_E2E
  === "1";

contextBridge.exposeInMainWorld(
  "evilTwinDesktop",
  {
    platform:
      process.platform,
    desktop:
      true,

    openLocationSettings:
      () =>
        ipcRenderer.invoke(
          "desktop:open-location-settings"
        ),

    getBackendStatus:
      () =>
        ipcRenderer.invoke(
          "desktop:backend-status"
        ),

    getAutoScanSchedulerStatus:
      () =>
        ipcRenderer.invoke(
          "desktop:auto-scan-status"
        ),

    refreshAutoScanScheduler:
      () =>
        ipcRenderer.invoke(
          "desktop:auto-scan-refresh"
        ),

    onAutoScanCompleted:
      callback => {
        const listener = (
          _event,
          payload
        ) => {
          callback(
            payload
          );
        };

        ipcRenderer.on(
          "desktop:auto-scan-completed",
          listener
        );

        return () => {
          ipcRenderer.removeListener(
            "desktop:auto-scan-completed",
            listener
          );
        };
      },

    e2eRunAutoScan:
      e2eMode
        ? () =>
            ipcRenderer.invoke(
              "desktop:e2e-run-auto-scan"
            )
        : undefined
  }
);
