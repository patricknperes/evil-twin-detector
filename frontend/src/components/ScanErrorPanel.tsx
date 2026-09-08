import {
  AlertTriangle,
  DatabaseZap,
  ExternalLink,
  MapPinOff,
  ServerOff,
  WifiOff
} from "lucide-react";

import type {
  ScanErrorView
} from "../lib/scanErrors";

const iconByKind = {
  backend_unavailable: ServerOff,
  location_access_denied: MapPinOff,
  unsupported_platform: WifiOff,
  native_wifi_api_error: AlertTriangle,
  database_persist_failed: DatabaseZap,
  scan_in_progress: AlertTriangle,
  unknown: AlertTriangle
} as const;

interface Props {
  error: ScanErrorView;
  onOpenLocationSettings?: () => void;
  onRetry: () => void;
}

export function ScanErrorPanel({
  error,
  onOpenLocationSettings,
  onRetry
}: Props) {
  const Icon = iconByKind[
    error.kind
  ];

  return (
    <section className="rounded-2xl border border-rose-200 bg-rose-50 p-5">
      <div className="flex items-start gap-4">
        <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-white text-rose-600 shadow-sm">
          <Icon size={20} />
        </div>

        <div className="min-w-0 flex-1">
          <h2 className="font-semibold text-rose-950">
            {error.title}
          </h2>

          <p className="mt-1 text-sm leading-6 text-rose-800">
            {error.message}
          </p>

          {(error.functionName || error.win32Code !== undefined) && (
            <dl className="mt-3 grid max-w-lg grid-cols-2 gap-3 rounded-xl bg-white/70 p-3 text-xs">
              {error.functionName && (
                <div>
                  <dt className="text-rose-500">
                    Função
                  </dt>
                  <dd className="mt-1 font-mono text-rose-900">
                    {error.functionName}
                  </dd>
                </div>
              )}

              {error.win32Code !== undefined && (
                <div>
                  <dt className="text-rose-500">
                    Código Win32
                  </dt>
                  <dd className="mt-1 font-mono text-rose-900">
                    {error.win32Code}
                  </dd>
                </div>
              )}
            </dl>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            {error.kind === "location_access_denied" && onOpenLocationSettings && (
              <button
                type="button"
                className="btn-primary"
                onClick={onOpenLocationSettings}
              >
                <ExternalLink size={16} />
                Abrir configurações de localização
              </button>
            )}

            <button
              type="button"
              className="btn-secondary"
              onClick={onRetry}
            >
              Tentar novamente
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
