import {
  CheckCircle2,
  LoaderCircle,
  RadioTower,
} from "lucide-react";

import type { AutoScanRefreshState } from "../hooks/useAutoScanRefresh";
import { formatDateTime } from "../lib/format";

export function AutoScanRefreshNotice({
  state,
}: {
  state: AutoScanRefreshState;
}) {
  if (!state.supported) {
    return null;
  }

  if (state.refreshing) {
    return (
      <div
        className="inline-flex min-h-10 max-w-full items-center gap-2 rounded-xl border border-[#dfe4f3] bg-white/90 px-3.5 py-2 text-xs font-medium text-[#6c748d] shadow-[0_5px_16px_rgba(35,41,87,0.035)] backdrop-blur-sm"
        role="status"
        aria-live="polite"
      >
        <span className="grid size-6 shrink-0 place-items-center rounded-lg bg-[#edf1ff] text-[#4968e8]">
          <LoaderCircle size={13} className="animate-spin" />
        </span>
        <span className="truncate max-[560px]:whitespace-normal">Sincronizando scan automático…</span>
      </div>
    );
  }

  if (state.lastRefreshFailed) {
    return (
      <div
        className="inline-flex min-h-10 max-w-full items-center gap-2 rounded-xl border border-amber-200/80 bg-amber-50/90 px-3.5 py-2 text-xs font-medium text-amber-800 shadow-[0_5px_16px_rgba(120,75,0,0.035)]"
        role="status"
        aria-live="polite"
      >
        <span className="grid size-6 shrink-0 place-items-center rounded-lg bg-white/80 text-amber-700">
          <RadioTower size={13} />
        </span>
        <span className="max-[560px]:leading-5">Scan automático concluído; atualização da tela falhou.</span>
      </div>
    );
  }

  if (!state.lastEvent) {
    return null;
  }

  const timestamp = state.lastEvent.observedAtUtc ?? state.lastRefreshAt;

  return (
    <div
      className="inline-flex min-h-10 max-w-full items-center gap-2 rounded-xl border border-[#dcefe9] bg-[#f4fbf9]/95 px-3.5 py-2 text-xs text-[#53766e] shadow-[0_5px_16px_rgba(40,199,165,0.035)]"
      role="status"
      aria-live="polite"
    >
      <span className="grid size-6 shrink-0 place-items-center rounded-lg bg-white text-[#28a98f] shadow-sm">
        <CheckCircle2 size={13} />
      </span>
      <span className="min-w-0 max-[560px]:leading-5">
        <span className="font-semibold text-[#347d6e]">Atualizado automaticamente</span>
        {timestamp ? ` · ${formatDateTime(timestamp)}` : ""}
        {" · "}
        {state.lastEvent.totalNetworks} redes
        {state.lastEvent.highCount > 0
          ? ` · ${state.lastEvent.highCount} em alta suspeita`
          : ""}
      </span>
    </div>
  );
}
