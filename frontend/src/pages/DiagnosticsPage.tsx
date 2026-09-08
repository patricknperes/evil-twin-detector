import { useEffect, useState, type ReactNode } from "react";
import { Activity, Cpu, Database, Download, FileJson, LoaderCircle, RefreshCw, ShieldCheck, Wrench } from "lucide-react";
import { AutoScanRefreshNotice } from "../components/AutoScanRefreshNotice";
import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import { useRuntimeStatus } from "../contexts/RuntimeStatusContext";
import { useAutoScanRefresh } from "../hooks/useAutoScanRefresh";
import { api } from "../lib/api";
import { availableArtifactCount, supportBundleFileName, supportBundleJson } from "../lib/diagnosticsUi";
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

  useEffect(() => { void load().catch(() => undefined); }, []);
  useEffect(() => {
    if (!runtime.recoveredAt) return;
    void load(false).catch(() => undefined);
  }, [runtime.recoveredAt]);

  const autoRefresh = useAutoScanRefresh(async () => { await load(false); });

  async function exportBundle() {
    setExporting(true); setError(null);
    try {
      const current = await api.diagnosticsSupportBundle();
      setBundle(current);
      const blob = new Blob([supportBundleJson(current)], { type: "application/json" });
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

  return <div className="space-y-7">
    <PageHeader title="Diagnóstico" description="Resumo técnico local para auditoria e suporte. O bundle exportado não inclui identificadores Wi-Fi em claro nem observações individuais." actions={<div className="flex flex-wrap items-center justify-end gap-2"><AutoScanRefreshNotice state={autoRefresh}/><button type="button" className="btn-secondary" disabled={loading} onClick={()=>void load().catch(()=>undefined)}><RefreshCw size={16} className={loading?"animate-spin":""}/>Atualizar</button><button type="button" className="btn-primary" disabled={exporting || !runtime.health} onClick={()=>void exportBundle()}>{exporting?<LoaderCircle size={16} className="animate-spin"/>:<Download size={16}/>}Exportar JSON</button></div>}/>
    {error && <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>}
    {loading && !bundle ? <section className="panel flex min-h-56 items-center justify-center"><LoaderCircle size={19} className="mr-2 animate-spin text-slate-400"/><span className="text-sm text-slate-500">Gerando resumo técnico…</span></section> : bundle ? <>
      <section className="grid grid-cols-4 gap-4">
        <SummaryCard label="Backend" value={bundle.application.backend_version} helper={bundle.application.platform} icon={<Activity size={17}/>}/>
        <SummaryCard label="Banco local" value={bundle.database.status === "ready" ? "Pronto" : "Erro"} helper={`${bundle.database.scan_count ?? 0} scans persistidos`} icon={<Database size={17}/>}/>
        <SummaryCard label="Modelo" value={bundle.model.status === "ready" ? "Pronto" : "Não pronto"} helper={`${artifactCount}/4 artefatos`} icon={<Cpu size={17}/>}/>
        <SummaryCard label="Bundle" value="support_bundle_v1" helper={formatDateTime(bundle.generated_at_utc)} icon={<FileJson size={17}/>}/>
      </section>
      <section className="grid grid-cols-[minmax(0,1fr)_minmax(360px,0.75fr)] gap-5">
        <div className="panel p-5">
          <div className="flex items-start gap-3"><div className="grid size-10 place-items-center rounded-xl bg-slate-100 text-slate-600"><Wrench size={18}/></div><div><h2 className="section-title">Estado técnico</h2><p className="muted mt-1">Snapshot gerado pelo backend, sem leitura direta do sistema de arquivos pelo renderer.</p></div></div>
          <dl className="mt-5 grid grid-cols-2 gap-4">
            <Value label="Scanner" value={bundle.runtime.scanner_status}/><Value label="Database" value={bundle.runtime.database_status}/><Value label="Modelo" value={bundle.runtime.model_status}/><Value label="Python" value={bundle.application.python_version}/><Value label="Observações persistidas" value={String(bundle.database.observation_count ?? 0)}/><Value label="Detecções persistidas" value={String(bundle.database.detection_count ?? 0)}/>
          </dl>
          <div className="mt-6 border-t border-slate-100 pt-5"><p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Atividade mais recente</p><dl className="mt-4 grid grid-cols-2 gap-4"><Value label="Último scan" value={bundle.activity.latest_scan_at_utc ? formatDateTime(bundle.activity.latest_scan_at_utc) : "—"}/><Value label="Redes no último scan" value={bundle.activity.latest_scan_network_count?.toString() ?? "—"}/><Value label="Anomalias no último scan" value={bundle.activity.latest_scan_anomaly_count?.toString() ?? "—"}/><Value label="Última suspeita" value={bundle.activity.latest_detection_suspicion_level ?? "—"}/></dl></div>
        </div>
        <div className="space-y-5">
          <section className="panel p-5"><div className="flex items-center justify-between gap-3"><div><h2 className="section-title">Artefatos científicos</h2><p className="muted mt-1">Apenas disponibilidade; caminhos não entram no bundle.</p></div><StatusBadge value={bundle.model.status}/></div><div className="mt-4 space-y-2">{Object.entries(bundle.model.artifact_available).map(([name,available])=><div key={name} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2.5"><code className="text-xs text-slate-600">{name}</code><span className={["badge",available?"bg-emerald-50 text-emerald-700":"bg-slate-100 text-slate-600"].join(" ")}>{available?"Disponível":"Ausente"}</span></div>)}</div></section>
          <section className="rounded-xl border border-emerald-200 bg-emerald-50 p-5"><div className="flex items-start gap-3"><ShieldCheck size={18} className="mt-0.5 shrink-0 text-emerald-700"/><div><h2 className="text-sm font-semibold text-emerald-900">Privacidade do diagnóstico</h2><p className="mt-2 text-xs leading-5 text-emerald-800">O arquivo não inclui SSID/BSSID em claro, observações individuais, bytes brutos de IEs, variáveis de ambiente ou caminhos absolutos dos artefatos.</p></div></div></section>
          {bundle.warnings.length>0 && <section className="rounded-xl border border-amber-200 bg-amber-50 p-4"><p className="text-xs font-semibold text-amber-900">Informações parcialmente indisponíveis</p><div className="mt-2 space-y-1 font-mono text-[11px] text-amber-700">{bundle.warnings.map(warning=><p key={warning}>{warning}</p>)}</div></section>}
        </div>
      </section>
    </> : null}
  </div>;
}

function SummaryCard({label,value,helper,icon}:{label:string;value:string;helper:string;icon:ReactNode}) { return <article className="panel p-4"><div className="flex items-center justify-between gap-3"><p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p><span className="text-slate-400">{icon}</span></div><p className="mt-2 truncate text-lg font-semibold tracking-tight text-slate-950">{value}</p><p className="mt-1 truncate text-xs text-slate-400">{helper}</p></article>; }
function Value({label,value}:{label:string;value:string}) { return <div className="rounded-xl border border-slate-100 bg-slate-50 p-3"><dt className="text-[11px] text-slate-400">{label}</dt><dd className="mt-1 break-all text-xs font-semibold text-slate-700">{value}</dd></div>; }
