import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

type StatCardTone = "indigo" | "blue" | "mint" | "amber";

const toneClasses: Record<StatCardTone, { icon: string; dot: string; halo: string }> = {
  indigo: {
    icon: "bg-[#eef0fb] text-[#353c7d]",
    dot: "bg-[#353c7d]",
    halo: "bg-[#353c7d]/8"
  },
  blue: {
    icon: "bg-[#eef2ff] text-[#4968e8]",
    dot: "bg-[#4968e8]",
    halo: "bg-[#4968e8]/8"
  },
  mint: {
    icon: "bg-[#eafaf6] text-[#1aa88d]",
    dot: "bg-[#2ac7a9]",
    halo: "bg-[#2ac7a9]/10"
  },
  amber: {
    icon: "bg-amber-50 text-amber-600",
    dot: "bg-amber-400",
    halo: "bg-amber-400/10"
  }
};

export function StatCard({
  label,
  value,
  helper,
  icon: Icon,
  tone = "indigo"
}: {
  label: string;
  value: ReactNode;
  helper?: string;
  icon?: LucideIcon;
  tone?: StatCardTone;
}) {
  const styles = toneClasses[tone];

  return (
    <article className="group relative overflow-hidden rounded-[22px] border border-[var(--evil-border)] bg-white p-5 shadow-[var(--evil-shadow-sm)] transition-[transform,box-shadow,border-color] duration-200 hover:-translate-y-0.5 hover:border-[#daddEA] hover:shadow-[0_16px_38px_rgba(34,39,76,0.08)]">
      <div className={`pointer-events-none absolute -right-10 -top-10 size-28 rounded-full blur-2xl ${styles.halo}`} aria-hidden="true" />

      <div className="relative flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className={`size-1.5 rounded-full ${styles.dot}`} aria-hidden="true" />
            <p className="text-[11px] font-semibold uppercase tracking-[0.11em] text-[#838aa2]">{label}</p>
          </div>
          <p className="mt-3 text-[30px] font-semibold leading-none tracking-[-0.04em] text-[#1f2440]">{value}</p>
        </div>

        {Icon ? (
          <div className={`grid size-10 shrink-0 place-items-center rounded-[14px] ${styles.icon}`}>
            <Icon size={18} strokeWidth={2} />
          </div>
        ) : null}
      </div>

      {helper ? <p className="relative mt-4 text-xs leading-5 text-[#8b91a6]">{helper}</p> : null}
    </article>
  );
}
