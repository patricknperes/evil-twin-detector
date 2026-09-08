import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Database,
  Download,
  Fingerprint,
  HardDrive,
  LoaderCircle,
  RefreshCw,
  ServerCog,
  ShieldCheck,
  Sparkles,
  Wrench
} from "lucide-react";
import { motion } from "motion/react";

import { AutoScanRefreshNotice } from "../components/AutoScanRefreshNotice";
import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import { useRuntimeStatus } from "../contexts/RuntimeStatusContext";
import { useAutoScanRefresh } from "../hooks/useAutoScanRefresh";
import { api } from "../lib/api";
import {
  availableArtifactCount,
  supportBundleFileName,
  supportBundleJson
} from "../lib/diagnosticsUi";
import { formatDateTime } from "../lib/format";
import type { DiagnosticsSupportBundleResponse } from "../types/api";

export function DiagnosticsPage() {
  const runtime = useRuntimeStatus();
  const [bundle, setBundle] = useState<DiagnosticsSupportBundleResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(showLoader = true) {
    if (showLoader) setLoading(true);
    setError(null);
    try {
      setBundle(await api.diagnosticsSupportBundle());
    } catch {
      setError("Não foi possível gerar o diagnóstico pelo backend local.");
      throw new Error("diagnostics_load_failed");
    } finally {
      if (showLoader) setLoading(false);
    }
  }

  useEffect(() => {
    void load().catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!runtime.recoveredAt) return;
    void load(false).catch(() => undefined);
  }, [runtime.recoveredAt]);

  const autoRefresh = useAutoScanRefresh(async () => {
    await load(false);
  });

  async function exportBundle() {
    setExporting(true);
    setError(null);
    try {
      const current = await api.diagnosticsSupportBundle();
      setBundle(current);
      const blob = new Blob([supportBundleJson(current)], {
        type: "application/json"
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = supportBundleFileName(current.generated_at_utc);
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch {
      setError("Não foi possível exportar o arquivo de diagnóstico.");
    } finally {
      setExporting(false);
    }
  }

  const artifactCount = bundle ? availableArtifactCount(bundle) : 0;
  const readyServices = useMemo(() => {
    if (!bundle) return 0;
    return [
      bundle.runtime.scanner_status,
      bundle.runtime.database_status,
      bundle.runtime.model_status
    ].filter(status => status === "ready").length;
  }, [bundle]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.36, ease: [0.22, 1, 0.36, 1] }}
      className="space-y-7"
    >
      <PageHeader
        title="Diagnóstico"
        description="Resumo técnico local para auditoria e suporte. O bundle exportado não inclui identificadores Wi-Fi em claro nem observações individuais."
        actions={
          <div className="flex flex-wrap items-center justify-end gap-2">
            <AutoScanRefreshNotice state={autoRefresh} />
            <button
              type="button"
              className="btn-secondary"
              disabled={loading}
              onClick={() => void load().catch(() => undefined)}
            >
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
              Atualizar
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={exporting || !runtime.health}
              onClick={() => void exportBundle()}
            >
              {exporting ? (
                <LoaderCircle size={16} className="animate-spin" />
              ) : (
                <Download size={16} />
              )}
              Exportar JSON
            </button>
          </div>
        }
      />

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700"
        >
          <AlertTriangle size={17} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </motion.div>
      )}

      {loading && !bundle ? (
        <section className="panel flex min-h-72 items-center justify-center">
          <div className="text-center">
            <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-indigo-50 text-indigo-600">
              <LoaderCircle size={21} className="animate-spin" />
            </span>
            <p className="mt-4 text-sm font-semibold text-slate-700">
              Gerando resumo técnico…
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Coletando apenas informações seguras para suporte local.
            </p>
          </div>
        </section>
      ) : bundle ? (
        <>
          <section className="relative overflow-hidden rounded-[1.75rem] bg-[#303778] p-6 text-white shadow-[0_24px_70px_rgba(35,39,76,0.18)] lg:p-7">
            <div className="pointer-events-none absolute -right-24 -top-24 size-72 rounded-full bg-[#4968e8]/25 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-28 left-1/3 size-64 rounded-full bg-[#2ac7a9]/15 blur-3xl" />
            <div className="relative grid gap-7 xl:grid-cols-[minmax(0,1.25fr)_minmax(430px,0.75fr)] xl:items-end">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-indigo-100">
                    <ServerCog size={14} />
                    Support bundle v1
                  </span>
                  <span className="inline-flex items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1.5 text-[11px] font-semibold text-emerald-100">
                    <ShieldCheck size={14} />
                    Exportação local
                  </span>
                </div>

                <h2 className="mt-5 max-w-2xl text-2xl font-semibold tracking-[-0.035em] text-white lg:text-[1.8rem]">
                  Saúde técnica e privacidade em uma única visão
                </h2>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-indigo-100/75">
                  O diagnóstico consolida runtime, persistência, artefatos científicos e atividade recente sem expor SSID, BSSID ou caminhos locais.
                </p>

                <div className="mt-6 flex flex-wrap gap-3">
                  <HeroMetric
                    label="Serviços prontos"
                    value={`${readyServices}/3`}
                    icon={<Activity size={15} />}
                  />
                  <HeroMetric
                    label="Artefatos disponíveis"
                    value={`${artifactCount}/4`}
                    icon={<Cpu size={15} />}
                  />
                  <HeroMetric
                    label="Scans persistidos"
                    value={String(bundle.database.scan_count ?? 0)}
                    icon={<Database size={15} />}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <HeroSnapshot
                  label="Backend"
                  value={bundle.application.backend_version}
                  helper={bundle.application.platform}
                />
                <HeroSnapshot
                  label="Python"
                  value={bundle.application.python_version}
                  helper="runtime local"
                />
                <HeroSnapshot
                  label="Gerado em"
                  value={formatDateTime(bundle.generated_at_utc)}
                  helper="snapshot atual"
                />
                <HeroSnapshot
                  label="Bundle"
                  value="support_bundle_v1"
                  helper="JSON auditável"
                />
              </div>
            </div>
          </section>

          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <SummaryCard
              label="Banco local"
              value={bundle.database.status === "ready" ? "Pronto" : "Erro"}
              helper={`${bundle.database.observation_count ?? 0} observações persistidas`}
              icon={<Database size={18} />}
              tone={bundle.database.status === "ready" ? "good" : "danger"}
            />
            <SummaryCard
              label="Modelo"
              value={bundle.model.status === "ready" ? "Pronto" : "Não pronto"}
              helper={`${artifactCount}/4 artefatos disponíveis`}
              icon={<Cpu size={18} />}
              tone={bundle.model.status === "ready" ? "good" : "neutral"}
            />
            <SummaryCard
              label="Detecções"
              value={String(bundle.database.detection_count ?? 0)}
              helper="registros persistidos no banco"
              icon={<Fingerprint size={18} />}
              tone="primary"
            />
            <SummaryCard
              label="Avisos"
              value={String(bundle.warnings.length)}
              helper={bundle.warnings.length ? "informações parcialmente indisponíveis" : "nenhuma limitação reportada"}
              icon={<AlertTriangle size={18} />}
              tone={bundle.warnings.length ? "warning" : "good"}
            />
          </section>

          <section className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
            <div className="panel overflow-hidden">
              <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 px-5 py-5 lg:px-6">
                <div className="flex items-start gap-3">
                  <div className="grid size-10 place-items-center rounded-2xl bg-indigo-50 text-indigo-600">
                    <Wrench size={18} />
                  </div>
                  <div>
                    <h2 className="section-title">Estado técnico</h2>
                    <p className="muted mt-1">
                      Snapshot fornecido pelo backend, sem acesso direto ao sistema de arquivos pelo renderer.
                    </p>
                  </div>
                </div>
                <span className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">
                  <CheckCircle2 size={14} />
                  {readyServices} serviços prontos
                </span>
              </div>

              <div className="grid gap-px bg-slate-100 sm:grid-cols-2 lg:grid-cols-3">
                <RuntimeCell label="Scanner" value={bundle.runtime.scanner_status} />
                <RuntimeCell label="Database" value={bundle.runtime.database_status} />
                <RuntimeCell label="Modelo" value={bundle.runtime.model_status} />
                <RuntimeCell label="Python" value={bundle.application.python_version} mono />
                <RuntimeCell label="Observações" value={String(bundle.database.observation_count ?? 0)} />
                <RuntimeCell label="Detecções" value={String(bundle.database.detection_count ?? 0)} />
              </div>

              <div className="border-t border-slate-100 bg-slate-50/70 px-5 py-5 lg:px-6">
                <div className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                  <Sparkles size={14} />
                  Atividade mais recente
                </div>
                <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <Value
                    label="Último scan"
                    value={bundle.activity.latest_scan_at_utc ? formatDateTime(bundle.activity.latest_scan_at_utc) : "—"}
                  />
                  <Value
                    label="Redes no scan"
                    value={bundle.activity.latest_scan_network_count?.toString() ?? "—"}
                  />
                  <Value
                    label="Anomalias"
                    value={bundle.activity.latest_scan_anomaly_count?.toString() ?? "—"}
                  />
                  <Value
                    label="Última suspeita"
                    value={bundle.activity.latest_detection_suspicion_level ?? "—"}
                  />
                </dl>
              </div>
            </div>

            <div className="space-y-5">
              <section className="panel overflow-hidden">
                <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-indigo-500">
                      Modelo científico
                    </p>
                    <h2 className="section-title mt-1">Artefatos científicos</h2>
                    <p className="muted mt-1">Somente disponibilidade; caminhos não entram no bundle.</p>
                  </div>
                  <StatusBadge value={bundle.model.status} />
                </div>
                <div className="space-y-2 p-4">
                  {Object.entries(bundle.model.artifact_available).map(([name, available]) => (
                    <div
                      key={name}
                      className="flex items-center justify-between gap-3 rounded-2xl border border-slate-100 bg-slate-50/70 px-3.5 py-3"
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <span
                          className={[
                            "grid size-8 shrink-0 place-items-center rounded-xl",
                            available
                              ? "bg-emerald-50 text-emerald-600"
                              : "bg-slate-100 text-slate-400"
                          ].join(" ")}
                        >
                          <HardDrive size={15} />
                        </span>
                        <code className="truncate text-[11px] font-semibold text-slate-600">
                          {name}
                        </code>
                      </div>
                      <span
                        className={[
                          "badge shrink-0",
                          available
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-slate-100 text-slate-600"
                        ].join(" ")}
                      >
                        {available ? "Disponível" : "Ausente"}
                      </span>
                    </div>
                  ))}
                </div>
              </section>

              <section className="relative overflow-hidden rounded-[1.35rem] border border-emerald-200 bg-emerald-50 p-5">
                <div className="absolute -right-8 -top-8 size-28 rounded-full bg-emerald-200/40 blur-2xl" />
                <div className="relative flex items-start gap-3">
                  <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-white text-emerald-700 shadow-sm">
                    <ShieldCheck size={17} />
                  </span>
                  <div>
                    <h2 className="text-sm font-semibold text-emerald-950">Privacidade do diagnóstico</h2>
                    <p className="mt-2 text-xs leading-5 text-emerald-800">
                      O arquivo não inclui SSID/BSSID em claro, observações individuais, bytes brutos de IEs, variáveis de ambiente ou caminhos absolutos dos artefatos.
                    </p>
                  </div>
                </div>
              </section>

              {bundle.warnings.length > 0 && (
                <section className="rounded-[1.35rem] border border-amber-200 bg-amber-50 p-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle size={17} className="mt-0.5 shrink-0 text-amber-700" />
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-amber-950">
                        Informações parcialmente indisponíveis
                      </p>
                      <div className="mt-2 space-y-1 break-words font-mono text-[11px] leading-5 text-amber-700">
                        {bundle.warnings.map(warning => (
                          <p key={warning}>{warning}</p>
                        ))}
                      </div>
                    </div>
                  </div>
                </section>
              )}
            </div>
          </section>
        </>
      ) : null}
    </motion.div>
  );
}

function HeroMetric({ label, value, icon }: { label: string; value: string; icon: ReactNode }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.08] px-3.5 py-3 backdrop-blur-sm">
      <span className="grid size-8 place-items-center rounded-xl bg-white/10 text-indigo-100">{icon}</span>
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-indigo-200/70">{label}</p>
        <p className="mt-0.5 text-sm font-bold text-white">{value}</p>
      </div>
    </div>
  );
}

function HeroSnapshot({ label, value, helper }: { label: string; value: string; helper: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.07] p-4 backdrop-blur-sm">
      <p className="text-[10px] font-semibold uppercase tracking-[0.11em] text-indigo-200/65">{label}</p>
      <p className="mt-2 truncate text-sm font-semibold text-white" title={value}>{value}</p>
      <p className="mt-1 truncate text-[11px] text-indigo-100/55">{helper}</p>
    </div>
  );
}

type SummaryTone = "primary" | "good" | "warning" | "danger" | "neutral";

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
  const tones: Record<SummaryTone, string> = {
    primary: "bg-indigo-50 text-indigo-600",
    good: "bg-emerald-50 text-emerald-600",
    warning: "bg-amber-50 text-amber-600",
    danger: "bg-rose-50 text-rose-600",
    neutral: "bg-slate-100 text-slate-500"
  };

  return (
    <article className="panel p-4.5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">{label}</p>
          <p className="mt-2 truncate text-xl font-semibold tracking-[-0.025em] text-slate-900">{value}</p>
          <p className="mt-1.5 truncate text-xs text-slate-400">{helper}</p>
        </div>
        <span className={["grid size-10 shrink-0 place-items-center rounded-2xl", tones[tone]].join(" ")}>{icon}</span>
      </div>
    </article>
  );
}

function RuntimeCell({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="bg-white p-4 lg:p-5">
      <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-slate-400">{label}</p>
      <p className={["mt-2 break-all text-sm font-semibold text-slate-700", mono ? "font-mono text-xs" : ""].join(" ")}>{value}</p>
    </div>
  );
}

function Value({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-3.5">
      <dt className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-400">{label}</dt>
      <dd className="mt-1.5 break-all text-xs font-semibold text-slate-700">{value}</dd>
    </div>
  );
}
