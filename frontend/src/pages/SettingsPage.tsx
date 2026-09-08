import {
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from "react";
import {
  BellRing,
  CheckCircle2,
  Clock3,
  Database,
  Gauge,
  LayoutDashboard,
  LoaderCircle,
  LockKeyhole,
  RefreshCcw,
  Save,
  ScanLine,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Wifi,
  XCircle
} from "lucide-react";
import { motion } from "motion/react";

import { PageHeader } from "../components/PageHeader";
import { SettingsNumberField } from "../components/SettingsNumberField";
import { SettingsToggle } from "../components/SettingsToggle";
import { StatusBadge } from "../components/StatusBadge";
import { useRuntimeStatus } from "../contexts/RuntimeStatusContext";
import { api } from "../lib/api";
import { formatDateTime } from "../lib/format";
import {
  editableSettings,
  settingsChanged
} from "../lib/settingsUi";
import type { ApplicationSettingsResponse } from "../types/api";
import type { AutoScanSchedulerStatus } from "../types/desktop";

type SettingsValues = ApplicationSettingsResponse["values"];

export function SettingsPage() {
  const runtime = useRuntimeStatus();
  const [response, setResponse] = useState<ApplicationSettingsResponse | null>(null);
  const [draft, setDraft] = useState<SettingsValues | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const payload = await api.settings();
      setResponse(payload);
      setDraft(payload.values);
    } catch {
      setError("Não foi possível carregar as configurações da aplicação.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const dirty = useMemo(
    () => Boolean(response && draft && settingsChanged(response.values, draft)),
    [response, draft]
  );

  function update<K extends keyof SettingsValues>(key: K, value: SettingsValues[K]) {
    setDraft(current => current ? { ...current, [key]: value } : current);
    setSuccess(null);
  }

  async function save() {
    if (!draft || !dirty) return;

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const payload = await api.updateSettings(editableSettings(draft));
      setResponse(payload);
      setDraft(payload.values);
      setSuccess("Configurações salvas no SQLite.");
      if (window.evilTwinDesktop?.refreshAutoScanScheduler) {
        await window.evilTwinDesktop.refreshAutoScanScheduler();
      }
      await runtime.refresh();
    } catch {
      setError("O backend recusou ou não conseguiu persistir as configurações.");
    } finally {
      setSaving(false);
    }
  }

  async function reset() {
    setResetting(true);
    setError(null);
    setSuccess(null);

    try {
      const payload = await api.resetSettings();
      setResponse(payload);
      setDraft(payload.values);
      setSuccess("Configurações restauradas para os valores padrão.");
      if (window.evilTwinDesktop?.refreshAutoScanScheduler) {
        await window.evilTwinDesktop.refreshAutoScanScheduler();
      }
      await runtime.refresh();
    } catch {
      setError("Não foi possível restaurar as configurações padrão.");
    } finally {
      setResetting(false);
    }
  }

  function discard() {
    if (response) {
      setDraft(response.values);
      setError(null);
      setSuccess(null);
    }
  }

  if (loading && !response) {
    return (
      <div className="space-y-7">
        <PageHeader
          title="Configurações"
          description="Preferências locais do scanner, histórico, dashboard e comportamento visual."
        />
        <section className="panel flex min-h-72 items-center justify-center">
          <div className="text-center">
            <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-indigo-50 text-indigo-600">
              <LoaderCircle size={21} className="animate-spin" />
            </span>
            <p className="mt-4 text-sm font-semibold text-slate-700">Carregando configurações…</p>
            <p className="mt-1 text-xs text-slate-400">Sincronizando preferências persistidas.</p>
          </div>
        </section>
      </div>
    );
  }

  if (!response || !draft) {
    return (
      <div className="space-y-7">
        <PageHeader
          title="Configurações"
          description="Preferências locais do scanner, histórico, dashboard e comportamento visual."
        />
        <div className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          <XCircle size={17} className="mt-0.5 shrink-0" />
          <span>{error ?? "As configurações não estão disponíveis."}</span>
        </div>
      </div>
    );
  }

  const policy = response.scientific_policy;
  const activePreferences = [
    draft.request_fresh_scan,
    draft.auto_scan_enabled,
    draft.show_technical_details,
    draft.high_anomaly_notifications
  ].filter(Boolean).length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.36, ease: [0.22, 1, 0.36, 1] }}
      className="space-y-7"
    >
      <PageHeader
        title="Configurações"
        description="Preferências persistentes do produto. Alterações científicas no modelo permanecem bloqueadas."
        actions={
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              className="btn-secondary"
              disabled={saving || resetting}
              onClick={() => void reset()}
            >
              <RefreshCcw size={16} className={resetting ? "animate-spin" : ""} />
              Restaurar padrões
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={!dirty || saving || resetting}
              onClick={() => void save()}
            >
              {saving ? <LoaderCircle size={16} className="animate-spin" /> : <Save size={16} />}
              Salvar alterações
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
          <XCircle size={17} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </motion.div>
      )}

      {success && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700"
        >
          <CheckCircle2 size={17} className="mt-0.5 shrink-0" />
          <span>{success}</span>
        </motion.div>
      )}

      <section className="relative overflow-hidden rounded-[1.75rem] bg-[#303778] p-6 text-white shadow-[0_24px_70px_rgba(35,39,76,0.18)] lg:p-7">
        <div className="pointer-events-none absolute -right-24 -top-24 size-72 rounded-full bg-[#4968e8]/25 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-24 left-1/4 size-60 rounded-full bg-[#2ac7a9]/15 blur-3xl" />

        <div className="relative grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(420px,0.8fr)] xl:items-end">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-indigo-100">
                <SlidersHorizontal size={14} />
                Preferências locais
              </span>
              <span
                className={[
                  "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[11px] font-semibold",
                  dirty
                    ? "border-amber-300/25 bg-amber-300/10 text-amber-100"
                    : "border-emerald-300/20 bg-emerald-300/10 text-emerald-100"
                ].join(" ")}
              >
                {dirty ? <Clock3 size={14} /> : <CheckCircle2 size={14} />}
                {dirty ? "Alterações pendentes" : "Tudo salvo"}
              </span>
            </div>

            <h2 className="mt-5 max-w-2xl text-2xl font-semibold tracking-[-0.035em] text-white lg:text-[1.8rem]">
              Ajuste o comportamento do aplicativo sem tocar no modelo científico
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-indigo-100/75">
              Scanner, scheduler, histórico, dashboard e preferências de interface permanecem separados dos artefatos congelados de ML.
            </p>

            <div className="mt-6 flex flex-wrap gap-3">
              <HeroMetric label="Preferências ativas" value={`${activePreferences}/4`} icon={<Sparkles size={15} />} />
              <HeroMetric label="Auto scan" value={draft.auto_scan_enabled ? "Ativo" : "Inativo"} icon={<Wifi size={15} />} />
              <HeroMetric label="Refresh UI" value={`${draft.frontend_refresh_seconds}s`} icon={<RefreshCcw size={15} />} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <HeroSnapshot label="Persistência" value="SQLite" helper="application_settings" />
            <HeroSnapshot
              label="Modelo"
              value={response.model_status === "ready" ? "Pronto" : "Não pronto"}
              helper={`${response.missing_model_artifacts.length} artefatos ausentes`}
            />
            <HeroSnapshot label="Scan automático" value={`${draft.auto_scan_interval_seconds}s`} helper="intervalo configurado" />
            <HeroSnapshot label="Última alteração" value={formatDateTime(draft.updated_at_utc)} helper="horário do backend" />
          </div>
        </div>
      </section>

      {dirty && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3.5"
        >
          <div className="flex items-center gap-3">
            <span className="grid size-8 place-items-center rounded-xl bg-amber-100 text-amber-700">
              <Clock3 size={15} />
            </span>
            <div>
              <p className="text-sm font-semibold text-amber-950">Existem alterações ainda não salvas.</p>
              <p className="mt-0.5 text-xs text-amber-700">Salve para persistir no backend ou descarte para retornar ao último estado.</p>
            </div>
          </div>
          <button
            type="button"
            onClick={discard}
            className="rounded-xl border border-amber-200 bg-white px-3 py-2 text-xs font-semibold text-amber-900 transition hover:border-amber-300 hover:shadow-sm"
          >
            Descartar alterações
          </button>
        </motion.div>
      )}

      <section className="grid gap-4 md:grid-cols-3">
        <StatusCard
          label="Configuração"
          value="Persistente"
          helper="SQLite / application_settings"
          icon={<Database size={18} />}
          tone="primary"
        />
        <StatusCard
          label="Modelo"
          value={response.model_status === "ready" ? "Pronto" : "Não pronto"}
          helper={`${response.missing_model_artifacts.length} artefatos ausentes`}
          icon={<Gauge size={18} />}
          tone={response.model_status === "ready" ? "good" : "neutral"}
        />
        <StatusCard
          label="Última alteração"
          value={formatDateTime(draft.updated_at_utc)}
          helper="Horário persistido pelo backend"
          icon={<Settings2 size={18} />}
          tone="neutral"
        />
      </section>

      <div className="grid gap-5 xl:grid-cols-2">
        <SettingsSection
          icon={<ScanLine size={18} />}
          eyebrow="Scanner"
          title="Varredura Wi-Fi"
          description="Preferências usadas quando o POST /scan não envia overrides explícitos."
        >
          <div className="grid gap-3">
            <SettingsToggle
              checked={draft.request_fresh_scan}
              onChange={value => update("request_fresh_scan", value)}
              label="Solicitar scan fresco"
              description="Solicita WlanScan antes de consultar a lista BSS."
            />
            <SettingsNumberField
              label="Espera após WlanScan"
              description="Tempo aguardado antes da consulta das redes observadas."
              value={draft.scan_wait_seconds}
              min={0}
              max={15}
              step={0.1}
              unit="s"
              onChange={value => update("scan_wait_seconds", value)}
            />
          </div>
        </SettingsSection>

        <SettingsSection
          icon={<RefreshCcw size={18} />}
          eyebrow="Automação"
          title="Atualização automática"
          description="Controle do scheduler de varreduras executado pelo processo principal do Electron."
        >
          <AutoScanRuntimeStatus status={runtime.scheduler} />
          <div className="mt-3 grid gap-3">
            <SettingsToggle
              checked={draft.auto_scan_enabled}
              onChange={value => update("auto_scan_enabled", value)}
              label="Scan automático"
              description="Quando ativado no Electron, agenda varreduras usando o intervalo configurado e o mesmo POST /scan do aplicativo."
            />
            <SettingsNumberField
              label="Intervalo do scan automático"
              description="Intervalo desejado entre varreduras automáticas."
              value={draft.auto_scan_interval_seconds}
              min={10}
              max={3600}
              unit="s"
              disabled={!draft.auto_scan_enabled}
              onChange={value => update("auto_scan_interval_seconds", value)}
            />
          </div>
        </SettingsSection>

        <SettingsSection
          icon={<Database size={18} />}
          eyebrow="Persistência"
          title="Histórico"
          description="Tamanho padrão das páginas quando os endpoints não recebem limit explicitamente."
        >
          <div className="grid gap-3">
            <SettingsNumberField
              label="Registros por página"
              description="Default para scans, detecções e versões do modelo."
              value={draft.history_page_size}
              min={1}
              max={100}
              onChange={value => update("history_page_size", value)}
            />
            <SettingsNumberField
              label="Observações por página"
              description="Default específico para observações de um scan."
              value={draft.history_observation_page_size}
              min={1}
              max={200}
              onChange={value => update("history_observation_page_size", value)}
            />
          </div>
        </SettingsSection>

        <SettingsSection
          icon={<LayoutDashboard size={18} />}
          eyebrow="Visão geral"
          title="Dashboard"
          description="Quantidade padrão de itens e pontos usados pela tela inicial."
        >
          <div className="grid gap-3">
            <SettingsNumberField
              label="Scans recentes"
              description="Quantidade no overview."
              value={draft.dashboard_recent_scans}
              min={0}
              max={20}
              onChange={value => update("dashboard_recent_scans", value)}
            />
            <SettingsNumberField
              label="Detecções recentes"
              description="Quantidade no overview."
              value={draft.dashboard_recent_detections}
              min={0}
              max={20}
              onChange={value => update("dashboard_recent_detections", value)}
            />
            <SettingsNumberField
              label="Pontos no gráfico"
              description="Janela padrão de /dashboard/trends."
              value={draft.dashboard_trend_limit}
              min={1}
              max={100}
              onChange={value => update("dashboard_trend_limit", value)}
            />
          </div>
        </SettingsSection>
      </div>

      <SettingsSection
        icon={<BellRing size={18} />}
        eyebrow="Experiência"
        title="Interface desktop"
        description="Preferências visuais e de atualização para React/Electron."
      >
        <div className="grid gap-3 lg:grid-cols-3">
          <SettingsNumberField
            label="Atualização da interface"
            description="Intervalo desejado para telas com refresh automático."
            value={draft.frontend_refresh_seconds}
            min={2}
            max={300}
            unit="s"
            onChange={value => update("frontend_refresh_seconds", value)}
          />
          <SettingsToggle
            checked={draft.show_technical_details}
            onChange={value => update("show_technical_details", value)}
            label="Mostrar detalhes técnicos"
            description="Preferência para dados avançados de rádio, contexto e features."
          />
          <SettingsToggle
            checked={draft.high_anomaly_notifications}
            onChange={value => update("high_anomaly_notifications", value)}
            label="Notificações de alta suspeita"
            description="Quando ativado, o Electron notifica somente novas redes que entram em alta suspeita durante scans automáticos."
          />
        </div>
      </SettingsSection>

      <section className="panel overflow-hidden">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 px-5 py-5 lg:px-6">
          <div className="flex items-start gap-3">
            <div className="grid size-10 place-items-center rounded-2xl bg-indigo-50 text-indigo-600">
              <LockKeyhole size={18} />
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-indigo-500">Somente leitura</p>
              <h2 className="section-title mt-1">Política científica</h2>
              <p className="muted mt-1">Restrições impostas pelo backend e não editáveis pela interface.</p>
            </div>
          </div>
          <span className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">
            <ShieldCheck size={14} />
            Bundle protegido
          </span>
        </div>

        <div className="grid gap-px bg-slate-100 sm:grid-cols-2 lg:grid-cols-3">
          <PolicyItem label="Atualizar referência" allowed={policy.reference_update_allowed} />
          <PolicyItem label="Scaler.fit" allowed={policy.scaler_fit_allowed} />
          <PolicyItem label="Scaler.partial_fit" allowed={policy.scaler_partial_fit_allowed} />
          <PolicyItem label="Treinar modelo" allowed={policy.model_fit_allowed} />
          <PolicyItem label="Recalibrar threshold" allowed={policy.threshold_recalibration_allowed} />
          <PolicyItem label="Editar caminhos dos artefatos" allowed={policy.artifact_paths_editable_via_settings} />
        </div>

        <div className="flex items-start gap-3 border-t border-slate-100 bg-slate-50/75 px-5 py-4 text-xs leading-5 text-slate-500 lg:px-6">
          <LockKeyhole size={15} className="mt-0.5 shrink-0 text-slate-400" />
          <p>
            A API rejeita campos extras. Tentativas de enviar threshold, caminhos de modelo ou flags de treinamento por PATCH <code className="rounded bg-slate-200/70 px-1.5 py-0.5 text-[11px] font-semibold text-slate-600">/settings</code> resultam em HTTP 422.
          </p>
        </div>
      </section>

      <section className="relative overflow-hidden rounded-[1.35rem] border border-indigo-100 bg-indigo-50/70 p-5">
        <div className="absolute -right-8 -top-8 size-32 rounded-full bg-indigo-200/40 blur-2xl" />
        <div className="relative flex items-start gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-white text-indigo-600 shadow-sm">
            <ShieldCheck size={17} />
          </span>
          <div>
            <p className="text-sm font-semibold text-indigo-950">Separação entre produto e ciência preservada</p>
            <p className="mt-1.5 text-xs leading-5 text-indigo-700">
              Alterar preferências de interface ou scan não modifica o bundle científico congelado. Referência normal, scaler, One-Class SVM e threshold continuam fora do escopo de edição do produto.
            </p>
          </div>
        </div>
      </section>
    </motion.div>
  );
}

function AutoScanRuntimeStatus({ status }: { status: AutoScanSchedulerStatus | null }) {
  if (!window.evilTwinDesktop) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs leading-5 text-slate-500">
        O scheduler automático pertence ao Electron e não é executado quando a interface está aberta apenas no navegador.
      </div>
    );
  }

  if (!status) {
    return (
      <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-500">
        <LoaderCircle size={15} className="animate-spin" />
        Consultando o estado do scheduler automático…
      </div>
    );
  }

  const labels: Record<AutoScanSchedulerStatus["status"], string> = {
    stopped: "Parado",
    unsupported_platform: "Indisponível nesta plataforma",
    disabled: "Desativado",
    waiting: "Aguardando próximo scan",
    scanning: "Executando scan",
    settings_error: "Erro ao ler configurações",
    scan_error: "Erro no último scan"
  };

  const healthy = status.status === "waiting" || status.status === "scanning";

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-slate-50/80 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className={[
            "grid size-9 place-items-center rounded-xl",
            healthy ? "bg-emerald-50 text-emerald-600" : "bg-slate-200/70 text-slate-500"
          ].join(" ")}>
            <RefreshCcw size={16} className={status.status === "scanning" ? "animate-spin" : ""} />
          </span>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-slate-400">Runtime do scheduler</p>
            <p className="mt-1 text-sm font-semibold text-slate-800">{labels[status.status]}</p>
          </div>
        </div>
        <span className={[
          "badge",
          healthy ? "bg-emerald-50 text-emerald-700" : "bg-slate-200/70 text-slate-600"
        ].join(" ")}>
          {healthy ? "Operacional" : "Em espera"}
        </span>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        <RuntimeMetric
          label="Intervalo"
          value={status.intervalSeconds === null ? "—" : `${status.intervalSeconds}s`}
        />
        <RuntimeMetric
          label="Último scan"
          value={status.lastCompletedAt ? formatDateTime(status.lastCompletedAt) : "—"}
        />
        <RuntimeMetric label="Alta suspeita" value={String(status.lastHighCount)} />
      </div>

      {status.lastError && (
        <p className="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-xs leading-5 text-rose-600">{status.lastError}</p>
      )}
    </div>
  );
}

function RuntimeMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white bg-white/80 px-3 py-2.5">
      <p className="text-[9px] font-bold uppercase tracking-[0.09em] text-slate-400">{label}</p>
      <p className="mt-1 truncate text-xs font-semibold text-slate-700" title={value}>{value}</p>
    </div>
  );
}

function SettingsSection({
  icon,
  eyebrow,
  title,
  description,
  children
}: {
  icon: ReactNode;
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="panel overflow-hidden">
      <div className="flex items-start gap-3 border-b border-slate-100 px-5 py-5">
        <div className="grid size-10 shrink-0 place-items-center rounded-2xl bg-indigo-50 text-indigo-600">{icon}</div>
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-indigo-500">{eyebrow}</p>
          <h2 className="section-title mt-1">{title}</h2>
          <p className="muted mt-1">{description}</p>
        </div>
      </div>
      <div className="p-4 lg:p-5">{children}</div>
    </section>
  );
}

type CardTone = "primary" | "good" | "neutral";

function StatusCard({
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
  tone: CardTone;
}) {
  const tones: Record<CardTone, string> = {
    primary: "bg-indigo-50 text-indigo-600",
    good: "bg-emerald-50 text-emerald-600",
    neutral: "bg-slate-100 text-slate-500"
  };

  return (
    <article className="panel p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">{label}</p>
          <p className="mt-2 truncate text-lg font-semibold tracking-[-0.025em] text-slate-900">{value}</p>
          <p className="mt-1.5 truncate text-xs text-slate-400">{helper}</p>
        </div>
        <span className={["grid size-10 shrink-0 place-items-center rounded-2xl", tones[tone]].join(" ")}>{icon}</span>
      </div>
    </article>
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

function PolicyItem({ label, allowed }: { label: string; allowed: boolean }) {
  return (
    <div className="bg-white p-4 lg:p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-medium text-slate-600">{label}</p>
        {allowed ? (
          <StatusBadge value="ready" />
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
            <LockKeyhole size={12} />
            Bloqueado
          </span>
        )}
      </div>
    </div>
  );
}
