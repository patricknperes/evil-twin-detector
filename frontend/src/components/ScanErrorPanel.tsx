import {
  AlertTriangle,
  DatabaseZap,
  ExternalLink,
  MapPinOff,
  RotateCcw,
  ServerOff,
  WifiOff
} from "lucide-react";
import { motion, useReducedMotion } from "motion/react";

import type {
  ScanErrorView
} from "../lib/scanErrors";
import {
  animationTokens
} from "../lib/animation";

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
  const Icon = iconByKind[error.kind];
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.section
      initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: shouldReduceMotion ? 0 : animationTokens.duration.base, ease: animationTokens.motionEase }}
      className="relative overflow-hidden rounded-[24px] border border-rose-200/80 bg-white shadow-[0_14px_40px_rgba(125,38,65,0.08)]"
    >
      <div className="absolute inset-y-0 left-0 w-1 bg-rose-400" aria-hidden="true" />
      <div className="absolute -right-14 -top-20 size-48 rounded-full bg-rose-100/70 blur-3xl" aria-hidden="true" />

      <div className="relative flex items-start gap-4 p-6">
        <div className="grid size-12 shrink-0 place-items-center rounded-2xl border border-rose-100 bg-rose-50 text-rose-600">
          <Icon size={21} />
        </div>

        <div className="min-w-0 flex-1">
          <p className="mb-1.5 text-[10px] font-bold uppercase tracking-[0.15em] text-rose-500">
            Varredura interrompida
          </p>
          <h2 className="text-lg font-semibold tracking-[-0.02em] text-[#3d2430]">
            {error.title}
          </h2>

          <p className="mt-2 max-w-3xl text-sm leading-6 text-[#765966]">
            {error.message}
          </p>

          {(error.functionName || error.win32Code !== undefined) && (
            <dl className="mt-4 grid max-w-xl grid-cols-2 gap-3 rounded-2xl border border-rose-100 bg-rose-50/55 p-4 text-xs max-[720px]:grid-cols-1">
              {error.functionName && (
                <div>
                  <dt className="font-medium text-rose-500">
                    Função
                  </dt>
                  <dd className="mt-1.5 font-mono font-semibold text-rose-950">
                    {error.functionName}
                  </dd>
                </div>
              )}

              {error.win32Code !== undefined && (
                <div>
                  <dt className="font-medium text-rose-500">
                    Código Win32
                  </dt>
                  <dd className="mt-1.5 font-mono font-semibold text-rose-950">
                    {error.win32Code}
                  </dd>
                </div>
              )}
            </dl>
          )}

          <div className="mt-5 flex flex-wrap gap-2.5">
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
              <RotateCcw size={15} />
              Tentar novamente
            </button>
          </div>
        </div>
      </div>
    </motion.section>
  );
}
