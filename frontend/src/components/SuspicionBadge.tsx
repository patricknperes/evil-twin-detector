import {
  AlertTriangle,
  CircleHelp,
  ShieldCheck,
  ShieldQuestion
} from "lucide-react";

import type {
  SuspicionLevel
} from "../types/api";

const labels: Record<
  SuspicionLevel,
  string
> = {
  low: "Baixa suspeita",
  medium: "Média suspeita",
  high: "Alta suspeita",
  unavailable: "Indisponível"
};

const classes: Record<
  SuspicionLevel,
  string
> = {
  low: "border-emerald-200 bg-emerald-50 text-emerald-700",
  medium: "border-amber-200 bg-amber-50 text-amber-700",
  high: "border-rose-200 bg-rose-50 text-rose-700",
  unavailable: "border-slate-200 bg-slate-100 text-slate-600"
};

const icons = {
  low: ShieldCheck,
  medium: ShieldQuestion,
  high: AlertTriangle,
  unavailable: CircleHelp
};

export function SuspicionBadge({
  level
}: {
  level: SuspicionLevel;
}) {
  const Icon = icons[level];

  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold",
        classes[level]
      ].join(" ")}
    >
      <Icon size={13} />
      {labels[level]}
    </span>
  );
}
