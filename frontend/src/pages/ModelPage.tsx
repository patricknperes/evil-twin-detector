import {
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from "react";
import {
  Activity,
  Braces,
  Cpu,
  Fingerprint,
  FlaskConical,
  LoaderCircle,
  LockKeyhole,
  RefreshCw
} from "lucide-react";

import {
  AutoScanRefreshNotice
} from "../components/AutoScanRefreshNotice";
import {
  ModelArtifactCard
} from "../components/ModelArtifactCard";
import {
  PageHeader
} from "../components/PageHeader";
import {
  StatusBadge
} from "../components/StatusBadge";
import {
  useRuntimeStatus
} from "../contexts/RuntimeStatusContext";
import {
  useAutoScanRefresh
} from "../hooks/useAutoScanRefresh";
import {
  api
} from "../lib/api";
import {
  formatDateTime
} from "../lib/format";
import {
  activeModel,
  artifactViews,
  shortFingerprint
} from "../lib/modelUi";
import {
  formatScore
} from "../lib/networkUi";
import type {
  HistoryModelVersion,
  ModelArtifactStatusResponse
} from "../types/api";

export function ModelPage() {
  const runtime = useRuntimeStatus();

  const [
    status,
    setStatus
  ] = useState<ModelArtifactStatusResponse | null>(
    null
  );

  const [
    versions,
    setVersions
  ] = useState<HistoryModelVersion[]>(
    []
  );

  const [
    selectedModelId,
    setSelectedModelId
  ] = useState<number | null>(
    null
  );

  const [
    loading,
    setLoading
  ] = useState(true);

  const [
    error,
    setError
  ] = useState<string | null>(
    null
  );

  async function load() {
    setLoading(true);
    setError(null);

    try {
      const [
        modelStatus,
        modelHistory
      ] = await Promise.all([
        api.modelStatus(),
        api.historyModels({
          limit: 100,
          offset: 0
        })
      ]);

      setStatus(
        modelStatus
      );
      setVersions(
        modelHistory.items
      );

      const currentActive =
        activeModel(
          modelHistory.items
        );

      setSelectedModelId(
        current =>
          current
          ?? currentActive
            ?.model_version_id
          ?? modelHistory.items[0]
            ?.model_version_id
          ?? null
      );
    } catch {
      setError(
        "Não foi possível consultar o estado do modelo no backend local."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const autoRefresh = useAutoScanRefresh(async () => {
    await load();
  });

  useEffect(() => {
    if (!runtime.recoveredAt) return;
    void load();
  }, [runtime.recoveredAt]);

  const artifacts = useMemo(
    () =>
      status
        ? artifactViews(
            status
          )
        : [],
    [
      status
    ]
  );

  const currentActive = useMemo(
    () =>
      activeModel(
        versions
      ),
    [
      versions
    ]
  );

  const selectedModel =
    versions.find(
      model =>
        model.model_version_id
        === selectedModelId
    )
    ?? currentActive
    ?? null;

  const availableArtifactCount =
    artifacts.filter(
      artifact =>
        artifact.available
    ).length;

  return (
    <div className="space-y-7">
      <PageHeader
        title="Modelo"
        description="Estado dos artefatos científicos congelados usados pelo desktop_candidate_v1. Esta área é exclusivamente de consulta e auditoria."
        actions={
          <div className="flex flex-wrap items-center justify-end gap-2">
            <AutoScanRefreshNotice state={autoRefresh}/>
            <button type="button" className="btn-secondary" disabled={loading} onClick={()=>void load()}>
              <RefreshCw size={16} className={loading ? "animate-spin" : ""}/>
              Atualizar
            </button>
          </div>
        }
      />

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      )}

      {loading && !status ? (
        <section className="panel flex min-h-52 items-center justify-center">
          <LoaderCircle
            size={19}
            className="mr-2 animate-spin text-slate-400"
          />
          <span className="text-sm text-slate-500">
            Consultando artefatos…
          </span>
        </section>
      ) : status ? (
        <>
          <section className="grid grid-cols-4 gap-4">
            <SummaryCard
              label="Runtime ML"
              value={
                status.status
                === "ready"
                  ? "Pronto"
                  : "Não pronto"
              }
              helper={`${availableArtifactCount}/4 artefatos disponíveis`}
              icon={
                <Cpu size={17} />
              }
            />

            <SummaryCard
              label="Feature set"
              value={`${status.feature_set.length} features`}
              helper="desktop_candidate_v1"
              icon={
                <Braces size={17} />
              }
            />

            <SummaryCard
              label="Versões persistidas"
              value={String(
                versions.length
              )}
              helper="model_version no SQLite"
              icon={
                <Activity size={17} />
              }
            />

            <SummaryCard
              label="Modelo ativo"
              value={
                currentActive
                  ? "Sim"
                  : "Não"
              }
              helper={
                currentActive
                  ?.version_name
                ?? "Nenhuma versão ativa"
              }
              icon={
                <FlaskConical size={17} />
              }
            />
          </section>

          <section className="panel p-5">
            <div className="flex items-start justify-between gap-6">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Estado do runtime
                </p>

                <div className="mt-2 flex items-center gap-3">
                  <h2 className="section-title">
                    desktop_candidate_v1
                  </h2>
                  <StatusBadge
                    value={
                      status.status
                    }
                  />
                </div>

                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
                  {status.message}
                </p>
              </div>

              <div className="max-w-md rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
                  <LockKeyhole
                    size={14}
                  />
                  Política científica — Somente leitura
                </div>

                <p className="mt-1 text-xs leading-5 text-slate-500">
                  Referência, scaler, OCSVM e threshold não podem ser
                  treinados, recalibrados ou substituídos por esta interface.
                </p>
              </div>
            </div>
          </section>

          <section>
            <div className="mb-4">
              <h2 className="section-title">
                Artefatos congelados
              </h2>
              <p className="muted mt-1">
                Os quatro arquivos precisam estar disponíveis para habilitar
                a inferência real do produto.
              </p>
            </div>

            <div className="grid grid-cols-4 gap-4">
              {artifacts.map(
                artifact => (
                  <ModelArtifactCard
                    key={artifact.key}
                    artifact={artifact}
                  />
                )
              )}
            </div>
          </section>

          <section className="grid grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] gap-5">
            <div className="panel p-5">
              <h2 className="section-title">
                Contrato de features
              </h2>
              <p className="muted mt-1">
                Ordem utilizada pelo scaler e pelo modelo.
              </p>

              <ol className="mt-5 space-y-3">
                {status.feature_set.map(
                  (
                    feature,
                    index
                  ) => (
                    <li
                      key={feature}
                      className="flex items-center gap-3 rounded-xl border border-slate-100 bg-slate-50 px-4 py-3"
                    >
                      <span className="grid size-7 shrink-0 place-items-center rounded-lg bg-white text-xs font-semibold text-slate-500 shadow-sm">
                        {index + 1}
                      </span>
                      <code className="text-xs font-medium text-slate-700">
                        {feature}
                      </code>
                    </li>
                  )
                )}
              </ol>
            </div>

            <div className="panel overflow-hidden">
              <div className="border-b border-slate-100 px-5 py-4">
                <h2 className="section-title">
                  Versões do modelo
                </h2>
                <p className="muted mt-1">
                  Histórico de bundles que já produziram detecções.
                </p>
              </div>

              {versions.length === 0 ? (
                <div className="p-8">
                  <p className="text-sm font-semibold text-slate-800">
                    Nenhuma versão persistida
                  </p>
                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    Uma entrada em model_version só será criada quando os
                    artefatos reais estiverem disponíveis e uma análise
                    runtime utilizar esse bundle.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-[220px_minmax(0,1fr)]">
                  <div className="border-r border-slate-100">
                    {versions.map(
                      model => (
                        <button
                          type="button"
                          key={model.model_version_id}
                          onClick={() =>
                            setSelectedModelId(
                              model.model_version_id
                            )
                          }
                          className={[
                            "w-full border-b border-slate-100 px-4 py-4 text-left transition",
                            selectedModel
                              ?.model_version_id
                              === model.model_version_id
                              ? "bg-slate-100"
                              : "hover:bg-slate-50"
                          ].join(" ")}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <p className="truncate text-xs font-semibold text-slate-800">
                              {model.version_name}
                            </p>
                            {model.active && (
                              <span className="size-2 shrink-0 rounded-full bg-emerald-500" />
                            )}
                          </div>
                          <p className="mt-1 text-[11px] text-slate-400">
                            {formatDateTime(
                              model.created_at_utc
                            )}
                          </p>
                        </button>
                      )
                    )}
                  </div>

                  {selectedModel && (
                    <ModelVersionDetail
                      model={selectedModel}
                    />
                  )}
                </div>
              )}
            </div>
          </section>

          <section className="rounded-xl border border-amber-200 bg-amber-50 p-4">
            <div className="flex items-start gap-3">
              <Fingerprint
                size={17}
                className="mt-0.5 shrink-0 text-amber-700"
              />
              <div>
                <p className="text-sm font-semibold text-amber-900">
                  Fingerprints SHA-256 e interpretação
                </p>
                <p className="mt-1 text-xs leading-5 text-amber-800">
                  Os fingerprints permitem identificar exatamente qual
                  referência, scaler, OCSVM e threshold participaram de uma
                  detecção. Uma saída acima do threshold representa anomalia,
                  não confirmação de um ataque Evil Twin.
                </p>
              </div>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}

function SummaryCard({
  label,
  value,
  helper,
  icon
}: {
  label: string;
  value: string;
  helper: string;
  icon: ReactNode;
}) {
  return (
    <article className="panel p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
          {label}
        </p>
        <span className="text-slate-400">
          {icon}
        </span>
      </div>

      <p className="mt-2 truncate text-xl font-semibold tracking-tight text-slate-950">
        {value}
      </p>
      <p className="mt-1 truncate text-xs text-slate-400">
        {helper}
      </p>
    </article>
  );
}

function ModelVersionDetail({
  model
}: {
  model: HistoryModelVersion;
}) {
  return (
    <div className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Bundle científico
          </p>
          <h3 className="mt-2 break-all text-base font-semibold text-slate-900">
            {model.version_name}
          </h3>
          <p className="mt-1 text-xs text-slate-400">
            {model.algorithm}
            {" · "}
            {model.feature_set_name}
          </p>
        </div>

        <span
          className={[
            "badge shrink-0",
            model.active
              ? "bg-emerald-50 text-emerald-700"
              : "bg-slate-100 text-slate-600"
          ].join(" ")}
        >
          {model.active
            ? "Ativo"
            : "Histórico"}
        </span>
      </div>

      <dl className="mt-5 grid grid-cols-3 gap-4">
        <Value
          label="Threshold"
          value={formatScore(
            model.threshold
          )}
        />
        <Value
          label="Detecções"
          value={String(
            model.detection_count
          )}
        />
        <Value
          label="Criado em"
          value={formatDateTime(
            model.created_at_utc
          )}
        />
      </dl>

      <div className="mt-6 border-t border-slate-100 pt-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Fingerprints SHA-256
        </p>

        <dl className="mt-3 space-y-3">
          <FingerprintValue
            label="Referência"
            value={model.reference_sha256}
          />
          <FingerprintValue
            label="Scaler"
            value={model.scaler_sha256}
          />
          <FingerprintValue
            label="OCSVM"
            value={model.model_sha256}
          />
          <FingerprintValue
            label="Threshold"
            value={model.threshold_sha256}
          />
        </dl>
      </div>

      {model.notes && (
        <div className="mt-5 rounded-xl bg-slate-50 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Notas
          </p>
          <p className="mt-2 text-xs leading-5 text-slate-600">
            {model.notes}
          </p>
        </div>
      )}
    </div>
  );
}

function Value({
  label,
  value
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <dt className="text-[11px] text-slate-400">
        {label}
      </dt>
      <dd className="mt-1 text-xs font-semibold text-slate-700">
        {value}
      </dd>
    </div>
  );
}

function FingerprintValue({
  label,
  value
}: {
  label: string;
  value: string | null;
}) {
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-3">
      <dt className="text-[11px] text-slate-400">
        {label}
      </dt>
      <dd
        className="mt-1 break-all font-mono text-[11px] text-slate-600"
        title={value ?? undefined}
      >
        {shortFingerprint(
          value
        )}
      </dd>
    </div>
  );
}
