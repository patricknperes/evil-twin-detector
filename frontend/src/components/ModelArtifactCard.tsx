import {
  CheckCircle2,
  FileQuestion,
  LockKeyhole
} from "lucide-react";

import type {
  ModelArtifactView
} from "../lib/modelUi";

export function ModelArtifactCard({
  artifact
}: {
  artifact: ModelArtifactView;
}) {
  return (
    <article className="panel group relative overflow-hidden p-[18px] transition-transform duration-200 hover:-translate-y-0.5">
      <div
        className={[
          "absolute inset-x-0 top-0 h-0.5",
          artifact.available
            ? "bg-[#2ac7a9]"
            : "bg-[#cfd4e1]"
        ].join(" ")}
      />

      <div className="flex items-start justify-between gap-4">
        <div
          className={[
            "grid size-10 place-items-center rounded-2xl",
            artifact.available
              ? "bg-[#eafaf6] text-[#168970]"
              : "bg-[#f1f3f7] text-[#8790a7]"
          ].join(" ")}
        >
          {artifact.available ? (
            <CheckCircle2 size={18} />
          ) : (
            <FileQuestion size={18} />
          )}
        </div>

        <span
          className={[
            "badge",
            artifact.available
              ? "bg-[#eafaf6] text-[#168970]"
              : "bg-[#f1f3f7] text-[#747c95]"
          ].join(" ")}
        >
          {artifact.available
            ? "Disponível"
            : "Ausente"}
        </span>
      </div>

      <h3 className="mt-4 text-sm font-semibold tracking-[-0.015em] text-[#2d324f]">
        {artifact.title}
      </h3>

      <p className="mt-1 min-h-10 text-xs leading-5 text-[#7a829b]">
        {artifact.role}
      </p>

      <div className="mt-4 rounded-2xl border border-[#eceef5] bg-[#f8f9fc] p-3.5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#9aa0b4]">
          Caminho esperado
        </p>
        <p className="mt-1.5 break-all font-mono text-[10px] leading-5 text-[#69718a]">
          {artifact.path}
        </p>
      </div>

      <div className="mt-4 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-[#a0a6b8]">
        <LockKeyhole size={11} />
        Somente leitura no produto
      </div>
    </article>
  );
}
