import type { ReactNode } from "react";

export function StatCard({ label, value, helper }: { label: string; value: ReactNode; helper?: string }) {
  return (
    <article className="panel p-5">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">{value}</p>
      {helper ? <p className="mt-2 text-xs text-slate-400">{helper}</p> : null}
    </article>
  );
}
