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
  low: "border-emerald-200/80 bg-emerald-50/80 text-emerald-700 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.45)]",
  medium: "border-amber-200/90 bg-amber-50/85 text-amber-700 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.45)]",
  high: "border-rose-200/90 bg-rose-50/85 text-rose-700 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.45)]",
  unavailable: "border-slate-200 bg-slate-100/80 text-slate-600 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.45)]"
};

const dots: Record<
  SuspicionLevel,
  string
> = {
  low: "bg-emerald-500",
  medium: "bg-amber-500",
  high: "bg-rose-500",
  unavailable: "bg-slate-400"
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
        "inline-flex min-h-7 items-center gap-1.5 whitespace-nowrap rounded-lg border px-2.5 py-1 text-[11px] font-semibold leading-none",
        classes[level]
      ].join(" ")}
    >
      <span className={`size-1.5 shrink-0 rounded-full ${dots[level]}`} />
      <Icon
        size={12}
        strokeWidth={2}
        aria-hidden="true"
      />
      {labels[level]}
    </span>
  );
}
