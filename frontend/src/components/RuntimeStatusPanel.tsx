import { Activity, Cpu, RadioTower, RefreshCw, Server } from "lucide-react";
import { useRuntimeStatus } from "../contexts/RuntimeStatusContext";
import {
  backendLabel,
  modelLabel,
  scannerLabel,
  schedulerLabel,
  type RuntimeLabel,
  type RuntimeTone,
} from "../lib/runtimeUi";

const toneClasses: Record<RuntimeTone, string> = {
  positive: "bg-[#28c7a5] shadow-[0_0_0_4px_rgba(40,199,165,0.10)]",
  neutral: "bg-white/35",
  warning: "bg-amber-400 shadow-[0_0_0_4px_rgba(251,191,36,0.10)]",
  danger: "bg-rose-400 shadow-[0_0_0_4px_rgba(251,113,133,0.10)]",
};

export function RuntimeStatusPanel() {
  const runtime = useRuntimeStatus();
  const connected = runtime.connection === "connected";
  const items = [
    { icon: Server, label: "Backend", value: backendLabel(runtime.connection) },
    { icon: RadioTower, label: "Scanner", value: scannerLabel(runtime.health?.scanner_status ?? null, connected) },
    { icon: Cpu, label: "Modelo", value: modelLabel(runtime.health?.model_status ?? null, connected) },
    { icon: Activity, label: "Scheduler", value: schedulerLabel(runtime.scheduler, connected, runtime.desktop) },
  ];

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.065] p-3 max-[1180px]:p-2 max-[760px]:hidden">
      <div className="flex items-center justify-between gap-2 max-[1180px]:justify-center">
        <div className="min-w-0 max-[1180px]:hidden">
          <div className="flex items-center gap-2">
            <span className={connected ? "size-1.5 rounded-full bg-[#28c7a5]" : "size-1.5 rounded-full bg-amber-400"} />
            <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-white/55">Estado do aplicativo</p>
          </div>
          <p className="mt-1.5 text-[10px] text-white/35">{runtime.lastCheckedAt ? "Monitoramento ativo" : "Inicializando"}</p>
        </div>

        <button
          type="button"
          className="grid size-8 shrink-0 place-items-center rounded-xl border border-white/10 bg-white/[0.065] text-white/50 transition hover:bg-white/10 hover:text-white disabled:opacity-50"
          disabled={runtime.checking}
          title="Atualizar estado agora"
          aria-label="Atualizar estado do aplicativo"
          onClick={() => void runtime.refresh()}
        >
          <RefreshCw size={14} className={runtime.checking ? "animate-spin" : ""} />
        </button>
      </div>

      <div className="mt-3 space-y-1 max-[1180px]:mt-2">
        {items.map((item) => (
          <RuntimeRow key={item.label} {...item} />
        ))}
      </div>
    </section>
  );
}

function RuntimeRow({ icon: Icon, label, value }: { icon: typeof Server; label: string; value: RuntimeLabel }) {
  return (
    <div
      className="flex min-h-8 items-center gap-2 rounded-xl px-2 py-1.5 transition-colors hover:bg-white/[0.045] max-[1180px]:justify-center max-[1180px]:px-1"
      title={`${label}: ${value.label}. ${value.detail}`}
    >
      <span className="grid size-6 shrink-0 place-items-center rounded-lg bg-white/[0.06] text-white/45">
        <Icon size={12.5} />
      </span>
      <span className="min-w-0 flex-1 truncate text-[10.5px] text-white/48 max-[1180px]:hidden">{label}</span>
      <span className="flex min-w-0 items-center gap-2 max-[1180px]:hidden">
        <span className={["size-1.5 shrink-0 rounded-full", toneClasses[value.tone]].join(" ")} />
        <span className="max-w-[92px] truncate text-[10.5px] font-medium text-white/78">{value.label}</span>
      </span>
      <span className={["hidden size-2 shrink-0 rounded-full max-[1180px]:block", toneClasses[value.tone]].join(" ")} aria-hidden="true" />
    </div>
  );
}
