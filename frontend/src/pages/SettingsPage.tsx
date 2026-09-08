import {
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from "react";
import {
  BellRing,
  Database,
  Gauge,
  LayoutDashboard,
  LoaderCircle,
  LockKeyhole,
  RefreshCcw,
  Save,
  ScanLine,
  Settings2,
  ShieldCheck
} from "lucide-react";

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
import type {
  ApplicationSettingsResponse
} from "../types/api";
import type {
  AutoScanSchedulerStatus
} from "../types/desktop";

type SettingsValues =
  ApplicationSettingsResponse["values"];

export function SettingsPage() {
  const runtime = useRuntimeStatus();
  const [response, setResponse] =
    useState<ApplicationSettingsResponse | null>(null);
  const [draft, setDraft] =
    useState<SettingsValues | null>(null);
  const [loading, setLoading] =
    useState(true);
  const [saving, setSaving] =
    useState(false);
  const [resetting, setResetting] =
    useState(false);
  const [error, setError] =
    useState<string | null>(null);
  const [success, setSuccess] =
    useState<string | null>(null);
  async function load() {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const payload =
        await api.settings();
      setResponse(payload);
      setDraft(payload.values);
    } catch {
      setError(
        "Não foi possível carregar as configurações da aplicação."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);


  const dirty = useMemo(
    () =>
      Boolean(
        response
        && draft
        && settingsChanged(
          response.values,
          draft
        )
      ),
    [response, draft]
  );

  function update<K extends keyof SettingsValues>(
    key: K,
    value: SettingsValues[K]
  ) {
    setDraft(current =>
      current
        ? {
            ...current,
            [key]: value
          }
        : current
    );
    setSuccess(null);
  }

  async function save() {
    if (!draft || !dirty) {
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const payload =
        await api.updateSettings(
          editableSettings(draft)
        );
      setResponse(payload);
      setDraft(payload.values);
      setSuccess(
        "Configurações salvas no SQLite."
      );
      if (window.evilTwinDesktop?.refreshAutoScanScheduler) {
        await window.evilTwinDesktop.refreshAutoScanScheduler();
      }
      await runtime.refresh();
    } catch {
      setError(
        "O backend recusou ou não conseguiu persistir as configurações."
      );
    } finally {
      setSaving(false);
    }
  }

  async function reset() {
    setResetting(true);
    setError(null);
    setSuccess(null);

    try {
      const payload =
        await api.resetSettings();
      setResponse(payload);
      setDraft(payload.values);
      setSuccess(
        "Configurações restauradas para os valores padrão."
      );
      if (window.evilTwinDesktop?.refreshAutoScanScheduler) {
        await window.evilTwinDesktop.refreshAutoScanScheduler();
      }
      await runtime.refresh();
    } catch {
      setError(
        "Não foi possível restaurar as configurações padrão."
      );
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
        <section className="panel flex min-h-60 items-center justify-center">
          <LoaderCircle
            size={19}
            className="mr-2 animate-spin text-slate-400"
          />
          <span className="text-sm text-slate-500">
            Carregando configurações…
          </span>
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
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error
            ?? "As configurações não estão disponíveis."}
        </div>
      </div>
    );
  }

  const policy =
    response.scientific_policy;

  return (
    <div className="space-y-7">
      <PageHeader
        title="Configurações"
        description="Preferências persistentes do produto. Alterações científicas no modelo permanecem bloqueadas."
        actions={
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn-secondary"
              disabled={saving || resetting}
              onClick={() => void reset()}
            >
              <RefreshCcw
                size={16}
                className={
                  resetting
                    ? "animate-spin"
                    : ""
                }
              />
              Restaurar padrões
            </button>

            <button
              type="button"
              className="btn-primary"
              disabled={
                !dirty
                || saving
                || resetting
              }
              onClick={() => void save()}
            >
              {saving ? (
                <LoaderCircle
                  size={16}
                  className="animate-spin"
                />
              ) : (
                <Save size={16} />
              )}
              Salvar alterações
            </button>
          </div>
        }
      />

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      )}

      {success && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
          {success}
        </div>
      )}

      {dirty && (
        <div className="flex items-center justify-between gap-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <p className="text-sm text-amber-800">
            Existem alterações ainda não salvas.
          </p>
          <button
            type="button"
            onClick={discard}
            className="text-xs font-semibold text-amber-900 underline decoration-amber-400 underline-offset-4"
          >
            Descartar alterações
          </button>
        </div>
      )}

      <section className="grid grid-cols-3 gap-4">
        <StatusCard
          label="Configuração"
          value="Persistente"
          helper="SQLite / application_settings"
          icon={<Database size={17} />}
        />
        <StatusCard
          label="Modelo"
          value={
            response.model_status === "ready"
              ? "Pronto"
              : "Não pronto"
          }
          helper={`${response.missing_model_artifacts.length} artefatos ausentes`}
          icon={<Gauge size={17} />}
        />
        <StatusCard
          label="Última alteração"
          value={formatDateTime(
            draft.updated_at_utc
          )}
          helper="Horário persistido pelo backend"
          icon={<Settings2 size={17} />}
        />
      </section>

      <SettingsSection
        icon={<ScanLine size={18} />}
        title="Varredura Wi-Fi"
        description="Preferências usadas quando o POST /scan não envia overrides explícitos."
      >
        <div className="grid grid-cols-2 gap-3">
          <SettingsToggle
            checked={draft.request_fresh_scan}
            onChange={value =>
              update(
                "request_fresh_scan",
                value
              )
            }
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
            onChange={value =>
              update(
                "scan_wait_seconds",
                value
              )
            }
          />
        </div>
      </SettingsSection>

      <SettingsSection
        icon={<RefreshCcw size={18} />}
        title="Atualização automática"
        description="Controle do scheduler de varreduras executado pelo processo principal do Electron."
      >
        <AutoScanRuntimeStatus
          status={runtime.scheduler}
        />

        <div className="mt-4 grid grid-cols-2 gap-3">
          <SettingsToggle
            checked={draft.auto_scan_enabled}
            onChange={value =>
              update(
                "auto_scan_enabled",
                value
              )
            }
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
            onChange={value =>
              update(
                "auto_scan_interval_seconds",
                value
              )
            }
          />
        </div>
      </SettingsSection>

      <SettingsSection
        icon={<Database size={18} />}
        title="Histórico"
        description="Tamanho padrão das páginas quando os endpoints não recebem limit explicitamente."
      >
        <div className="grid grid-cols-2 gap-3">
          <SettingsNumberField
            label="Registros por página"
            description="Default para scans, detecções e versões do modelo."
            value={draft.history_page_size}
            min={1}
            max={100}
            onChange={value =>
              update(
                "history_page_size",
                value
              )
            }
          />
          <SettingsNumberField
            label="Observações por página"
            description="Default específico para observações de um scan."
            value={draft.history_observation_page_size}
            min={1}
            max={200}
            onChange={value =>
              update(
                "history_observation_page_size",
                value
              )
            }
          />
        </div>
      </SettingsSection>

      <SettingsSection
        icon={<LayoutDashboard size={18} />}
        title="Dashboard"
        description="Quantidade padrão de itens e pontos usados pela tela inicial."
      >
        <div className="grid grid-cols-3 gap-3">
          <SettingsNumberField
            label="Scans recentes"
            description="Quantidade no overview."
            value={draft.dashboard_recent_scans}
            min={0}
            max={20}
            onChange={value =>
              update(
                "dashboard_recent_scans",
                value
              )
            }
          />
          <SettingsNumberField
            label="Detecções recentes"
            description="Quantidade no overview."
            value={draft.dashboard_recent_detections}
            min={0}
            max={20}
            onChange={value =>
              update(
                "dashboard_recent_detections",
                value
              )
            }
          />
          <SettingsNumberField
            label="Pontos no gráfico"
            description="Janela padrão de /dashboard/trends."
            value={draft.dashboard_trend_limit}
            min={1}
            max={100}
            onChange={value =>
              update(
                "dashboard_trend_limit",
                value
              )
            }
          />
        </div>
      </SettingsSection>

      <SettingsSection
        icon={<BellRing size={18} />}
        title="Interface desktop"
        description="Preferências visuais e de atualização para React/Electron."
      >
        <div className="grid grid-cols-2 gap-3">
          <SettingsNumberField
            label="Atualização da interface"
            description="Intervalo desejado para telas com refresh automático."
            value={draft.frontend_refresh_seconds}
            min={2}
            max={300}
            unit="s"
            onChange={value =>
              update(
                "frontend_refresh_seconds",
                value
              )
            }
          />
          <SettingsToggle
            checked={draft.show_technical_details}
            onChange={value =>
              update(
                "show_technical_details",
                value
              )
            }
            label="Mostrar detalhes técnicos"
            description="Preferência para dados avançados de rádio, contexto e features."
          />
          <SettingsToggle
            checked={draft.high_anomaly_notifications}
            onChange={value =>
              update(
                "high_anomaly_notifications",
                value
              )
            }
            label="Notificações de alta suspeita"
            description="Quando ativado, o Electron notifica somente novas redes que entram em alta suspeita durante scans automáticos."
          />
        </div>
      </SettingsSection>

      <section className="panel overflow-hidden">
        <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-4">
          <div className="grid size-9 place-items-center rounded-xl bg-slate-100 text-slate-600">
            <LockKeyhole size={17} />
          </div>
          <div>
            <h2 className="section-title">
              Política científica
            </h2>
            <p className="muted mt-1">
              Restrições impostas pelo backend e não editáveis pela interface.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-px bg-slate-100">
          <PolicyItem
            label="Atualizar referência"
            allowed={policy.reference_update_allowed}
          />
          <PolicyItem
            label="Scaler.fit"
            allowed={policy.scaler_fit_allowed}
          />
          <PolicyItem
            label="Scaler.partial_fit"
            allowed={policy.scaler_partial_fit_allowed}
          />
          <PolicyItem
            label="Treinar modelo"
            allowed={policy.model_fit_allowed}
          />
          <PolicyItem
            label="Recalibrar threshold"
            allowed={policy.threshold_recalibration_allowed}
          />
          <PolicyItem
            label="Editar caminhos dos artefatos"
            allowed={policy.artifact_paths_editable_via_settings}
          />
        </div>

        <div className="border-t border-slate-100 bg-slate-50 px-5 py-4 text-xs leading-5 text-slate-500">
          A API rejeita campos extras. Tentativas de enviar threshold, caminhos
          de modelo ou flags de treinamento por PATCH `/settings` resultam em
          HTTP 422.
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-slate-100/70 p-4">
        <div className="flex items-start gap-3">
          <ShieldCheck
            size={17}
            className="mt-0.5 shrink-0 text-slate-600"
          />
          <p className="text-xs leading-5 text-slate-600">
            Alterar preferências de interface ou scan não modifica o bundle
            científico congelado. Referência normal, scaler, One-Class SVM e
            threshold continuam fora do escopo de edição do produto.
          </p>
        </div>
      </section>
    </div>
  );
}


function AutoScanRuntimeStatus({
  status
}: {
  status: AutoScanSchedulerStatus | null;
}) {
  if (!window.evilTwinDesktop) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-500">
        O scheduler automático pertence ao Electron e não é executado quando a
        interface está aberta apenas no navegador.
      </div>
    );
  }

  if (!status) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-500">
        Consultando o estado do scheduler automático…
      </div>
    );
  }

  const labels: Record<
    AutoScanSchedulerStatus["status"],
    string
  > = {
    stopped: "Parado",
    unsupported_platform: "Indisponível nesta plataforma",
    disabled: "Desativado",
    waiting: "Aguardando próximo scan",
    scanning: "Executando scan",
    settings_error: "Erro ao ler configurações",
    scan_error: "Erro no último scan"
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Runtime do scheduler
          </p>
          <p className="mt-1 text-sm font-semibold text-slate-800">
            {labels[status.status]}
          </p>
        </div>

        <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-500">
          <span>
            Intervalo:{" "}
            {status.intervalSeconds === null
              ? "—"
              : `${status.intervalSeconds}s`}
          </span>
          <span>
            Último scan:{" "}
            {status.lastCompletedAt
              ? formatDateTime(status.lastCompletedAt)
              : "—"}
          </span>
          <span>
            Alta suspeita no último scan:{" "}
            {status.lastHighCount}
          </span>
        </div>
      </div>

      {status.lastError && (
        <p className="mt-3 text-xs leading-5 text-rose-600">
          {status.lastError}
        </p>
      )}
    </div>
  );
}


function SettingsSection({
  icon,
  title,
  description,
  children
}: {
  icon: ReactNode;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="panel p-5">
      <div className="flex items-start gap-3">
        <div className="grid size-9 shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-600">
          {icon}
        </div>
        <div>
          <h2 className="section-title">
            {title}
          </h2>
          <p className="muted mt-1">
            {description}
          </p>
        </div>
      </div>
      <div className="mt-5">
        {children}
      </div>
    </section>
  );
}

function StatusCard({
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
      <p className="mt-2 text-lg font-semibold tracking-tight text-slate-950">
        {value}
      </p>
      <p className="mt-1 text-xs text-slate-400">
        {helper}
      </p>
    </article>
  );
}

function PolicyItem({
  label,
  allowed
}: {
  label: string;
  allowed: boolean;
}) {
  return (
    <div className="bg-white p-4">
      <p className="text-xs font-medium text-slate-500">
        {label}
      </p>
      <div className="mt-2">
        {allowed ? (
          <StatusBadge value="ready" />
        ) : (
          <span className="badge bg-slate-100 text-slate-600">
            Bloqueado
          </span>
        )}
      </div>
    </div>
  );
}
