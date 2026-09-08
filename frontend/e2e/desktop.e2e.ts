import {
  expect,
  test
} from "@playwright/test";
import {
  _electron as electron,
  type ElectronApplication,
  type Page
} from "playwright";
import path from "node:path";
import {
  fileURLToPath
} from "node:url";

import {
  FakeDesktopBackend
} from "./support/fake-backend";

const currentFile =
  fileURLToPath(
    import.meta.url
  );

const frontendRoot =
  path.resolve(
    path.dirname(
      currentFile
    ),
    ".."
  );

const rendererUrl =
  "http://127.0.0.1:15173";

let backend:
  FakeDesktopBackend;

let electronApp:
  ElectronApplication;

let page:
  Page;

async function launchDesktop() {
  electronApp =
    await electron.launch({
      args: [
        "."
      ],
      cwd:
        frontendRoot,
      env: {
        ...process.env,
        EVIL_TWIN_E2E:
          "1",
        EVIL_TWIN_E2E_RENDERER_URL:
          rendererUrl,
        EVIL_TWIN_E2E_FORCE_SCHEDULER:
          "1",
        EVIL_TWIN_BACKEND_URL:
          backend.baseUrl,
        EVIL_TWIN_BACKEND_STARTUP_TIMEOUT_MS:
          "3000",
        ELECTRON_DISABLE_SECURITY_WARNINGS:
          "true"
      }
    });

  page =
    await electronApp
      .firstWindow();

  await expect(
    page.getByText(
      "Evil Twin Detector",
      {
        exact:
          true
      }
    )
  ).toBeVisible();
}

test.describe.configure({
  mode:
    "serial"
});

test.beforeEach(
  async () => {
    backend =
      new FakeDesktopBackend();

    await backend.start();
    await launchDesktop();
  }
);

test.afterEach(
  async () => {
    await electronApp
      ?.close()
      .catch(
        () => undefined
      );

    await backend
      ?.stop()
      .catch(
        () => undefined
      );
  }
);

test(
  "navega pelas telas e mantém modelo não pronto como estado operacional",
  async () => {
    const routes = [
      [
        "Visão geral",
        "Visão geral"
      ],
      [
        "Escanear redes",
        "Escanear redes"
      ],
      [
        "Redes observadas",
        "Redes observadas"
      ],
      [
        "Histórico",
        "Histórico"
      ],
      [
        "Modelo",
        "Modelo"
      ],
      [
        "Diagnóstico",
        "Diagnóstico"
      ],
      [
        "Configurações",
        "Configurações"
      ]
    ] as const;

    for (
      const [
        navigation,
        heading
      ]
      of routes
    ) {
      await page
        .getByRole(
          "link",
          {
            name:
              navigation
          }
        )
        .click();

      await expect(
        page.getByRole(
          "heading",
          {
            name:
              heading,
            level:
              1
          }
        )
      ).toBeVisible();
    }

    await page
      .getByRole(
        "link",
        {
          name:
            "Modelo"
        }
      )
      .click();

    await expect(
      page.getByText(
        "Não pronto",
        {
          exact:
            true
        }
      ).first()
    ).toBeVisible();

    await expect(
      page.getByText(
        "0/4 artefatos disponíveis"
      )
    ).toBeVisible();

    await expect(
      page.getByText(
        "Evil Twin confirmado"
      )
    ).toHaveCount(
      0
    );
  }
);

test(
  "scanner indisponível produz o erro específico no scan manual",
  async () => {
    backend.scanMode =
      "unsupported_platform";

    backend.scannerStatus =
      "unsupported_platform";

    await page
      .getByRole(
        "link",
        {
          name:
            "Escanear redes"
        }
      )
      .click();

    await page
      .getByRole(
        "button",
        {
          name:
            "Iniciar scan"
        }
      )
      .click();

    await expect(
      page.getByRole(
        "heading",
        {
          name:
            "Scanner disponível apenas no Windows"
        }
      )
    ).toBeVisible();

    expect(
      backend.scanCount
    ).toBe(
      0
    );
  }
);

test(
  "scan manual sem modelo persiste atividade sem classificar a rede como normal",
  async () => {
    backend.scanMode =
      "success";

    backend.modelReady =
      false;

    backend.scannerStatus =
      "ready";

    await page
      .getByRole(
        "link",
        {
          name:
            "Escanear redes"
        }
      )
      .click();

    await page
      .getByRole(
        "button",
        {
          name:
            "Iniciar scan"
        }
      )
      .click();

    await expect(
      page.getByText(
        "E2E-Test-Network"
      )
    ).toBeVisible();

    await expect(
      page.getByText(
        "Indisponível"
      ).first()
    ).toBeVisible();

    await expect(
      page.getByText(
        "Normal",
        {
          exact:
            true
        }
      )
    ).toHaveCount(
      0
    );

    await page
      .getByRole(
        "link",
        {
          name:
            "Histórico"
        }
      )
      .click();

    await expect(
      page.getByText(
        "step49-scan-1"
      )
    ).toBeVisible();

    await expect(
      page.getByText(
        "Nenhum scan persistido"
      )
    ).toHaveCount(
      0
    );
  }
);

test(
  "scan automático percorre o Electron main e atualiza o Dashboard por IPC",
  async () => {
    backend.modelReady =
      true;

    backend.scannerStatus =
      "ready";

    backend.settings
      .auto_scan_enabled =
        true;

    backend.nextScanHigh =
      true;

    await page.evaluate(
      async () => {
        const desktop = (
          window as Window & {
            evilTwinDesktop?: {
              refreshAutoScanScheduler?: () =>
                Promise<unknown>;
            };
          }
        ).evilTwinDesktop;

        const refresh =
          desktop
            ?.refreshAutoScanScheduler;

        if (!refresh) {
          throw new Error(
            "E2E scheduler refresh IPC unavailable."
          );
        }

        await refresh();
      }
    );

    await page
      .getByRole(
        "link",
        {
          name:
            "Visão geral"
        }
      )
      .click();

    await expect(
      page.getByText(
        "Scans realizados"
      )
    ).toBeVisible();

    const result =
      await page.evaluate(
        async () => {
          const desktop = (
            window as Window & {
              evilTwinDesktop?: {
                e2eRunAutoScan?: () => Promise<{
                  outcome: string;
                  highCount?: number;
                  newHighCount?: number;
                }>;
              };
            }
          ).evilTwinDesktop;

          const run =
            desktop
              ?.e2eRunAutoScan;

          if (!run) {
            throw new Error(
              "E2E auto-scan IPC unavailable."
            );
          }

          return await run();
        }
      );

    expect(
      result.outcome
    ).toBe(
      "scan_completed"
    );

    await expect(
      page.getByText(
        "step49-scan-1"
      )
    ).toBeVisible();

    await expect(
      page.getByText(
        "Atualizado automaticamente"
      )
    ).toBeVisible();

    expect(
      backend.scanCount
    ).toBe(
      1
    );
  }
);

test(
  "perda do backend mantém a UI e recuperação é detectada sem reload",
  async () => {
    await page
      .getByRole(
        "link",
        {
          name:
            "Visão geral"
        }
      )
      .click();

    await expect(
      page.getByText(
        "Scans realizados"
      )
    ).toBeVisible();

    await backend.stop();

    await expect(
      page.getByText(
        "Backend local desconectado"
      )
    ).toBeVisible({
      timeout:
        14_000
    });

    await expect(
      page.getByRole(
        "heading",
        {
          name:
            "Visão geral",
          level:
            1
        }
      )
    ).toBeVisible();

    await backend.start();

    await expect(
      page.getByText(
        "Conexão com o backend restaurada"
      )
    ).toBeVisible({
      timeout:
        10_000
    });
  }
);

test(
  "diagnóstico exportado é local e não contém identificadores Wi-Fi individuais",
  async () => {
    await page
      .getByRole(
        "link",
        {
          name:
            "Diagnóstico"
        }
      )
      .click();

    await expect(
      page.getByText(
        "Privacidade do diagnóstico"
      )
    ).toBeVisible();

    await page.evaluate(
      () => {
        const target = (
          window as Window & {
            __evilTwinDiagnosticsDownload?: {
              filename: string | null;
              content: string | null;
            };
          }
        );

        target
          .__evilTwinDiagnosticsDownload = {
            filename:
              null,
            content:
              null
          };

        const originalCreateObjectURL =
          URL.createObjectURL.bind(
            URL
          );

        URL.createObjectURL =
          (
            blob: Blob
          ) => {
            void blob
              .text()
              .then(
                content => {
                  const capture =
                    target
                      .__evilTwinDiagnosticsDownload;

                  if (capture) {
                    capture.content =
                      content;
                  }
                }
              );

            return originalCreateObjectURL(
              blob
            );
          };

        HTMLAnchorElement
          .prototype
          .click =
            function () {
              const capture =
                target
                  .__evilTwinDiagnosticsDownload;

              if (
                capture
                && this.download
              ) {
                capture.filename =
                  this.download;
              }
            };
      }
    );

    await page
      .getByRole(
        "button",
        {
          name:
            "Exportar JSON"
        }
      )
      .click();

    await page.waitForFunction(
      () => {
        const capture = (
          window as Window & {
            __evilTwinDiagnosticsDownload?: {
              filename: string | null;
              content: string | null;
            };
          }
        )
          .__evilTwinDiagnosticsDownload;

        return Boolean(
          capture?.filename
          && capture?.content
        );
      }
    );

    const capture =
      await page.evaluate(
        () => (
          window as Window & {
            __evilTwinDiagnosticsDownload?: {
              filename: string | null;
              content: string | null;
            };
          }
        )
          .__evilTwinDiagnosticsDownload
      );

    expect(
      capture?.filename
    ).toMatch(
      /^evil-twin-diagnostics-.*\.json$/
    );

    expect(
      capture?.content
    ).toBeTruthy();

    const bundle =
      JSON.parse(
        capture?.content
        ?? "null"
      ) as unknown;

    const forbiddenKeys =
      new Set([
        "ssid",
        "bssid",
        "ssid_hash",
        "bssid_hash",
        "interface_guid",
        "interface_guid_hash",
        "raw_ie_hex"
      ]);

    function walk(
      value: unknown
    ) {
      if (
        Array.isArray(
          value
        )
      ) {
        value.forEach(
          walk
        );

        return;
      }

      if (
        typeof value
        !== "object"
        || value
        === null
      ) {
        return;
      }

      for (
        const [
          key,
          child
        ]
        of Object.entries(
          value
        )
      ) {
        expect(
          forbiddenKeys.has(
            key
          )
        ).toBe(
          false
        );

        walk(
          child
        );
      }
    }

    walk(
      bundle
    );
  }
);
