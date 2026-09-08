import { AlertTriangle, CheckCircle2, CircleHelp, MapPin } from "lucide-react";

type Status =
  | "ready" | "not_ready" | "ok" | "error"
  | "unsupported_platform" | "not_initialized" | "location_access_denied";

const labels: Record<Status,string> = {
  ready:"Pronto", not_ready:"Não pronto", ok:"Online", error:"Erro",
  unsupported_platform:"Indisponível", not_initialized:"Não inicializado",
  location_access_denied:"Permissão necessária"
};

export function StatusBadge({ value }: { value: Status }) {
  const good = value === "ready" || value === "ok";
  const Icon = good ? CheckCircle2 : value === "error" ? AlertTriangle : value === "location_access_denied" ? MapPin : CircleHelp;
  return (
    <span className={["badge gap-1.5", good ? "bg-emerald-50 text-emerald-700" : value === "error" ? "bg-rose-50 text-rose-700" : value === "location_access_denied" ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-600"].join(" ")}>
      <Icon size={14}/>{labels[value]}
    </span>
  );
}
