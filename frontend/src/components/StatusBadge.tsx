import {
  AlertTriangle,
  CheckCircle2,
  CircleHelp,
  MapPin,
} from "lucide-react";

type Status =
  | "ready"
  | "not_ready"
  | "ok"
  | "error"
  | "unsupported_platform"
  | "not_initialized"
  | "location_access_denied";

const labels: Record<Status, string> = {
  ready: "Pronto",
  not_ready: "Não pronto",
  ok: "Online",
  error: "Erro",
  unsupported_platform: "Indisponível",
  not_initialized: "Não inicializado",
  location_access_denied: "Permissão necessária",
};

const toneClasses: Record<Status, string> = {
  ready: "border-emerald-200/80 bg-emerald-50/90 text-emerald-700",
  ok: "border-emerald-200/80 bg-emerald-50/90 text-emerald-700",
  error: "border-rose-200/80 bg-rose-50/90 text-rose-700",
  location_access_denied: "border-amber-200/80 bg-amber-50/90 text-amber-800",
  not_ready: "border-[#e1e4ef] bg-[#f5f6fa] text-[#646c84]",
  unsupported_platform: "border-[#e1e4ef] bg-[#f5f6fa] text-[#646c84]",
  not_initialized: "border-[#e1e4ef] bg-[#f5f6fa] text-[#646c84]",
};

export function StatusBadge({ value }: { value: Status }) {
  const good = value === "ready" || value === "ok";
  const Icon = good
    ? CheckCircle2
    : value === "error"
      ? AlertTriangle
      : value === "location_access_denied"
        ? MapPin
        : CircleHelp;

  return (
    <span
      className={[
        "badge max-w-full gap-1.5 border shadow-[0_2px_8px_rgba(34,39,76,0.025)]",
        toneClasses[value],
      ].join(" ")}
      title={labels[value]}
    >
      <Icon size={13.5} className="shrink-0" aria-hidden="true" />
      <span className="truncate">{labels[value]}</span>
    </span>
  );
}
