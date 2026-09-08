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
    <article className="panel p-5">
      <div className="flex items-start justify-between gap-4">
        <div
          className={[
            "grid size-10 place-items-center rounded-xl",
            artifact.available
              ? "bg-emerald-50 text-emerald-700"
              : "bg-slate-100 text-slate-500"
          ].join(" ")}
        >
          {artifact.available ? (
            <CheckCircle2 size={19} />
          ) : (
            <FileQuestion size={19} />
          )}
        </div>

        <span
          className={[
            "badge",
            artifact.available
              ? "bg-emerald-50 text-emerald-700"
              : "bg-slate-100 text-slate-600"
          ].join(" ")}
        >
          {artifact.available
            ? "Disponível"
            : "Ausente"}
        </span>
      </div>

      <h3 className="mt-4 text-sm font-semibold text-slate-900">
        {artifact.title}
      </h3>

      <p className="mt-1 min-h-10 text-xs leading-5 text-slate-500">
        {artifact.role}
      </p>

      <div className="mt-4 rounded-xl bg-slate-50 p-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
          Caminho esperado
        </p>
        <p className="mt-1 break-all font-mono text-[11px] leading-5 text-slate-500">
          {artifact.path}
        </p>
      </div>

      <div className="mt-4 flex items-center gap-1.5 text-[11px] font-medium text-slate-400">
        <LockKeyhole size={12} />
        Somente leitura no produto
      </div>
    </article>
  );
}
