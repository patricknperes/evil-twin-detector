import { Sparkles } from "lucide-react";
import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex items-start justify-between gap-8 max-[900px]:flex-col max-[900px]:gap-4">
      <div className="min-w-0">
        <div className="mb-2.5 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#4968e8]">
          <span className="grid size-5 place-items-center rounded-lg bg-[#edf1ff]" aria-hidden="true">
            <Sparkles size={11} strokeWidth={2.2} />
          </span>
          Security workspace
        </div>
        <h1 className="text-[30px] font-semibold leading-[1.12] tracking-[-0.035em] text-[var(--evil-text)] max-[560px]:text-[26px]">
          {title}
        </h1>
        <p className="mt-2 max-w-3xl text-[13px] leading-6 text-[var(--evil-text-muted)] max-[560px]:leading-[1.65]">
          {description}
        </p>
      </div>

      {actions ? (
        <div className="shrink-0 pt-1 max-[900px]:w-full max-[900px]:pt-0 max-[900px]:[&>div]:justify-start max-[560px]:[&_button]:min-h-10">
          {actions}
        </div>
      ) : null}
    </header>
  );
}
