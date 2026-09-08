import {
  CheckCircle2,
  LoaderCircle,
  RadioTower
} from "lucide-react";

import type {
  AutoScanRefreshState
} from "../hooks/useAutoScanRefresh";
import {
  formatDateTime
} from "../lib/format";

export function AutoScanRefreshNotice({
  state
}: {
  state: AutoScanRefreshState;
}) {
  if (!state.supported) {
    return null;
  }

  if (state.refreshing) {
    return (
      <div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-500">
        <LoaderCircle
          size={14}
          className="animate-spin"
        />
        Sincronizando scan automático…
      </div>
    );
  }

  if (state.lastRefreshFailed) {
    return (
      <div className="inline-flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-700">
        <RadioTower size={14} />
        Scan automático concluído; atualização da tela falhou.
      </div>
    );
  }

  if (!state.lastEvent) {
    return null;
  }

  const timestamp =
    state.lastEvent.observedAtUtc
    ?? state.lastRefreshAt;

  return (
    <div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
      <CheckCircle2
        size={14}
        className="text-slate-600"
      />
      <span>
        Atualizado automaticamente
        {timestamp
          ? ` · ${formatDateTime(timestamp)}`
          : ""}
        {" · "}
        {state.lastEvent.totalNetworks} redes
        {state.lastEvent.highCount > 0
          ? ` · ${state.lastEvent.highCount} em alta suspeita`
          : ""}
      </span>
    </div>
  );
}
