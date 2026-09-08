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
  motion,
  useReducedMotion
} from "motion/react";

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
  const shouldReduceMotion = useReducedMotion();

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
            <button type="button" className="btn-secondary" disabled={loading} onClick={() => void load()}>
              <RefreshCw size={16} className={loading ? "animate-spin" : ""}/>
              Atualizar
            </button>
          </div>
        }
      />

      {error && (
        <div className="rounded-2xl border border-rose-200/80 bg-rose-50/90 px-4 py-3.5 text-sm text-rose-700 shadow-sm">
          {error}
        </div>
      )}

      {loading && !status ? (
        <section className="panel flex min-h-56 items-center justify-center">
          <LoaderCircle size={19} className="mr-2 animate-spin text-[#7f879f]" />
          <span className="text-sm text-[#737b95]">Consultando artefatos…</span>
        </section>
      ) : status ? (
        <>
          <motion.section
            initial={shouldReduceMotion ? false : {opacity: 0, y: 14}}
            animate={{opacity: 1, y: 0}}
            transition={{duration: 0.45, ease: [0.22, 1, 0.36, 1]}}
            className="relative overflow-hidden rounded-[28px] bg-[#303778] p-6 text-white shadow-[0_24px_70px_rgba(48,55,120,0.18)] sm:p-7 lg:p-8"
          >
            <div className="pointer-events-none absolute -right-16 -top-24 size-72 rounded-full border border-white/10" />
            <div className="pointer-events-none absolute right-10 top-2 size-44 rounded-full bg-[#4968e8]/[0.35] blur-3xl" />
            <div className="pointer-events-none absolute -bottom-24 left-1/3 size-56 rounded-full bg-[#2ac7a9]/[0.20] blur-3xl" />

            <div className="relative grid gap-7 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-center">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-2 rounded-full border border-white/[0.12] bg-white/[0.075] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.17em] text-white/[0.70]">
                    <FlaskConical size={13} />
                    Bundle científico
                  </span>
                  <StatusBadge value={status.status} />
                </div>

                <h2 className="mt-5 text-2xl font-semibold tracking-[-0.04em] sm:text-[2rem]">
                  desktop_candidate_v1
                </h2>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-white/[0.62]">
                  {status.message}
                </p>

                <div className="mt-6 flex max-w-xl gap-2">
                  {[0, 1, 2, 3].map(index => (
                    <span
                      key={index}
                      className={[
                        "h-1.5 flex-1 rounded-full",
                        index < availableArtifactCount ? "bg-[#35d1b0]" : "bg-white/[0.15]"
                      ].join(" ")}
                    />
                  ))}
                </div>
                <p className="mt-2 text-[11px] font-medium text-white/[0.45]">
                  {availableArtifactCount}/4 artefatos disponíveis para inferência
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2.5">
                <HeroMetric label="Features" value={String(status.feature_set.length)} helper="contrato ativo" />
                <HeroMetric label="Versões" value={String(versions.length)} helper="persistidas" />
                <HeroMetric label="Artefatos" value={`${availableArtifactCount}/4`} helper="disponíveis" />
                <HeroMetric label="Modelo ativo" value={currentActive ? "Sim" : "Não"} helper={currentActive?.version_name ?? "nenhuma versão"} />
              </div>
            </div>
          </motion.section>

          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <SummaryCard
              label="Runtime ML"
              value={status.status === "ready" ? "Pronto" : "Não pronto"}
              helper={`${availableArtifactCount}/4 artefatos disponíveis`}
              icon={<Cpu size={17} />}
              tone="indigo"
            />
            <SummaryCard
              label="Feature set"
              value={`${status.feature_set.length} features`}
              helper="desktop_candidate_v1"
              icon={<Braces size={17} />}
              tone="blue"
            />
            <SummaryCard
              label="Versões persistidas"
              value={String(versions.length)}
              helper="model_version no SQLite"
              icon={<Activity size={17} />}
              tone="mint"
            />
            <SummaryCard
              label="Modelo ativo"
              value={currentActive ? "Sim" : "Não"}
              helper={currentActive?.version_name ?? "Nenhuma versão ativa"}
              icon={<FlaskConical size={17} />}
              tone="violet"
            />
          </section>

          <section className="panel overflow-hidden">
            <div className="grid gap-5 p-5 sm:p-6 lg:grid-cols-[minmax(0,1fr)_minmax(300px,0.72fr)] lg:items-center">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.17em] text-[#9299ae]">
                  Estado do runtime
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-3">
                  <h2 className="section-title">desktop_candidate_v1</h2>
                  <StatusBadge value={status.status} />
                </div>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-[#737b95]">
                  {status.message}
                </p>
              </div>

              <div className="rounded-2xl border border-[#e4e7f0] bg-[#f7f8fc] px-4 py-4">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#3f4663]">
                  <span className="grid size-8 place-items-center rounded-xl bg-white text-[#4968e8] shadow-sm">
                    <LockKeyhole size={14} />
                  </span>
                  Política científica — Somente leitura
                </div>
                <p className="mt-2 text-xs leading-5 text-[#737b95]">
                  Referência, scaler, OCSVM e threshold não podem ser treinados, recalibrados ou substituídos por esta interface.
                </p>
              </div>
            </div>
          </section>

          <section>
            <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="section-title">Artefatos congelados</h2>
                <p className="muted mt-1">
                  Os quatro arquivos precisam estar disponíveis para habilitar a inferência real do produto.
                </p>
              </div>
              <span className="inline-flex w-fit items-center rounded-full bg-[#eef1ff] px-3 py-1.5 text-xs font-semibold text-[#49549b]">
                {availableArtifactCount} de 4 disponíveis
              </span>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {artifacts.map(artifact => (
                <ModelArtifactCard key={artifact.key} artifact={artifact} />
              ))}
            </div>
          </section>

          <section className="grid gap-5 xl:grid-cols-[minmax(300px,0.72fr)_minmax(0,1.28fr)]">
            <div className="panel overflow-hidden">
              <div className="border-b border-[#edf0f7] px-5 py-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#9299ae]">
                  Entrada do modelo
                </p>
                <h2 className="section-title mt-1">Contrato de features</h2>
                <p className="muted mt-1">Ordem utilizada pelo scaler e pelo modelo.</p>
              </div>

              <ol className="space-y-2 p-4 sm:p-5">
                {status.feature_set.map((feature, index) => (
                  <li
                    key={feature}
                    className="flex items-center gap-3 rounded-2xl border border-[#ebedf4] bg-[#f8f9fc] px-3.5 py-3"
                  >
                    <span className="grid size-7 shrink-0 place-items-center rounded-lg bg-white text-[11px] font-semibold text-[#68708a] shadow-sm">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <code className="min-w-0 break-all text-xs font-medium text-[#4c536d]">{feature}</code>
                  </li>
                ))}
              </ol>
            </div>

            <div className="panel overflow-hidden">
              <div className="border-b border-[#edf0f7] px-5 py-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#9299ae]">
                  Rastreabilidade científica
                </p>
                <h2 className="section-title mt-1">Versões do modelo</h2>
                <p className="muted mt-1">Histórico de bundles que já produziram detecções.</p>
              </div>

              {versions.length === 0 ? (
                <div className="p-8 sm:p-10">
                  <p className="text-sm font-semibold text-[#343a58]">Nenhuma versão persistida</p>
                  <p className="mt-2 max-w-xl text-sm leading-6 text-[#737b95]">
                    Uma entrada em model_version só será criada quando os artefatos reais estiverem disponíveis e uma análise runtime utilizar esse bundle.
                  </p>
                </div>
              ) : (
                <div className="grid lg:grid-cols-[230px_minmax(0,1fr)]">
                  <div className="border-b border-[#edf0f7] bg-[#fafbfe] lg:border-b-0 lg:border-r">
                    {versions.map(model => (
                      <button
                        type="button"
                        key={model.model_version_id}
                        onClick={() => setSelectedModelId(model.model_version_id)}
                        className={[
                          "w-full border-b border-[#edf0f7] px-4 py-4 text-left transition-colors",
                          selectedModel?.model_version_id === model.model_version_id
                            ? "bg-[#eef1fb]"
                            : "hover:bg-white"
                        ].join(" ")}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <p className="truncate text-xs font-semibold text-[#3b4260]">{model.version_name}</p>
                          {model.active && <span className="size-2 shrink-0 rounded-full bg-[#2ac7a9] shadow-[0_0_0_4px_rgba(42,199,169,0.12)]" />}
                        </div>
                        <p className="mt-1 text-[11px] text-[#9aa0b4]">{formatDateTime(model.created_at_utc)}</p>
                      </button>
                    ))}
                  </div>

                  {selectedModel && <ModelVersionDetail model={selectedModel} />}
                </div>
              )}
            </div>
          </section>

          <section className="rounded-[20px] border border-amber-200/80 bg-amber-50/80 p-4 sm:p-5">
            <div className="flex items-start gap-3">
              <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-white text-amber-700 shadow-sm">
                <Fingerprint size={17} />
              </span>
              <div>
                <p className="text-sm font-semibold text-amber-950">Fingerprints SHA-256 e interpretação</p>
                <p className="mt-1 max-w-4xl text-xs leading-5 text-amber-900/75">
                  Os fingerprints permitem identificar exatamente qual referência, scaler, OCSVM e threshold participaram de uma detecção. Uma saída acima do threshold representa anomalia, não confirmação de um ataque Evil Twin.
                </p>
              </div>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}

function HeroMetric({
  label,
  value,
  helper
}: {
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.075] p-3.5 backdrop-blur-sm">
      <p className="text-[10px] font-semibold uppercase tracking-[0.13em] text-white/[0.45]">{label}</p>
      <p className="mt-2 truncate text-xl font-semibold tracking-[-0.035em] text-white">{value}</p>
      <p className="mt-1 truncate text-[10px] text-white/[0.40]">{helper}</p>
    </div>
  );
}

type SummaryTone = "indigo" | "blue" | "mint" | "violet";

const summaryToneClasses: Record<SummaryTone, {icon: string; bar: string}> = {
  indigo: {icon: "bg-[#eef0ff] text-[#414b9a]", bar: "bg-[#414b9a]"},
  blue: {icon: "bg-[#edf3ff] text-[#4968e8]", bar: "bg-[#4968e8]"},
  mint: {icon: "bg-[#ebfaf6] text-[#1fa88e]", bar: "bg-[#2ac7a9]"},
  violet: {icon: "bg-violet-50 text-violet-600", bar: "bg-violet-500"}
};

function SummaryCard({
  label,
  value,
  helper,
  icon,
  tone
}: {
  label: string;
  value: string;
  helper: string;
  icon: ReactNode;
  tone: SummaryTone;
}) {
  const palette = summaryToneClasses[tone];

  return (
    <article className="panel relative overflow-hidden p-[18px]">
      <div className={["absolute inset-x-0 top-0 h-0.5", palette.bar].join(" ")} />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#9299ae]">{label}</p>
          <p className="mt-3 truncate text-xl font-semibold tracking-[-0.035em] text-[#262b47]">{value}</p>
          <p className="mt-1 truncate text-xs text-[#9299ae]">{helper}</p>
        </div>
        <span className={["grid size-9 shrink-0 place-items-center rounded-xl", palette.icon].join(" ")}>{icon}</span>
      </div>
    </article>
  );
}

function ModelVersionDetail({
  model
}: {
  model: HistoryModelVersion;
}) {
  return (
    <div className="p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#9299ae]">
            Bundle científico
          </p>
          <h3 className="mt-2 break-all text-base font-semibold tracking-[-0.02em] text-[#2b304d]">
            {model.version_name}
          </h3>
          <p className="mt-1 text-xs text-[#9299ae]">
            {model.algorithm}
            {" · "}
            {model.feature_set_name}
          </p>
        </div>

        <span
          className={[
            "badge shrink-0",
            model.active
              ? "bg-[#e9faf5] text-[#168970]"
              : "bg-[#f0f2f7] text-[#747c95]"
          ].join(" ")}
        >
          {model.active
            ? "Ativo"
            : "Histórico"}
        </span>
      </div>

      <dl className="mt-5 grid gap-3 sm:grid-cols-3">
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

      <div className="mt-6 border-t border-[#edf0f7] pt-5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#9299ae]">
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
        <div className="mt-5 rounded-2xl bg-[#f7f8fc] p-4">
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
      <dt className="text-[11px] text-[#9299ae]">
        {label}
      </dt>
      <dd className="mt-1 text-xs font-semibold text-[#4b526d]">
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
    <div className="rounded-xl border border-[#e9ebf3] bg-[#f8f9fc] px-3 py-3">
      <dt className="text-[11px] text-[#9299ae]">
        {label}
      </dt>
      <dd
        className="mt-1 break-all font-mono text-[11px] text-[#5f6781]"
        title={value ?? undefined}
      >
        {shortFingerprint(
          value
        )}
      </dd>
    </div>
  );
}
