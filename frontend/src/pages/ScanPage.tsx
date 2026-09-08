import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from "react";
import {
  Activity,
  AlertTriangle,
  Database,
  LoaderCircle,
  MapPin,
  Radar,
  RefreshCw,
  Search,
  ShieldCheck,
  Wifi
} from "lucide-react";

import {
  NetworkScanCard
} from "../components/NetworkScanCard";
import {
  PageHeader
} from "../components/PageHeader";
import {
  ScanErrorPanel
} from "../components/ScanErrorPanel";
import {
  StatusBadge
} from "../components/StatusBadge";
import {
  SuspicionBadge
} from "../components/SuspicionBadge";
import { useRuntimeStatus } from "../contexts/RuntimeStatusContext";
import {
  api
} from "../lib/api";
import {
  formatDateTime
} from "../lib/format";
import {
  classifyScanError,
  type ScanErrorView
} from "../lib/scanErrors";
import type {
  ApplicationSettingsResponse,
  HealthResponse,
  ScanResponse,
  SuspicionLevel
} from "../types/api";

type Filter =
  | "all"
  | SuspicionLevel;

interface PreflightState {
  health: HealthResponse;
  settings: ApplicationSettingsResponse;
}

const filterLabels: Record<
  Filter,
  string
> = {
  all: "Todas",
  low: "Baixa",
  medium: "Média",
  high: "Alta",
  unavailable: "Indisponível"
};

export function ScanPage() {
  const runtime = useRuntimeStatus();
  const [preflight, setPreflight] = useState<PreflightState | null>(null);
  const [preflightLoading, setPreflightLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScanResponse | null>(null);
  const [error, setError] = useState<ScanErrorView | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");

  const loadPreflight = useCallback(
    async () => {
      setPreflightLoading(true);

      try {
        const [health, settings] = await Promise.all([
          api.health(),
          api.settings()
        ]);

        setPreflight({
          health,
          settings
        });
      } catch {
        setPreflight(null);
      } finally {
        setPreflightLoading(false);
      }
    },
    []
  );

  useEffect(
    () => {
      void loadPreflight();
    },
    [loadPreflight]
  );

  const scan = useCallback(
    async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await api.scan();
        setResult(response);
        setFilter("all");
        setQuery("");
        await loadPreflight();
      } catch (scanError) {
        setError(
          classifyScanError(scanError)
        );
      } finally {
        setLoading(false);
        void runtime.refresh();
      }
    },
    [loadPreflight, runtime]
  );

  const counts = useMemo(
    () => {
      const initial: Record<SuspicionLevel, number> = {
        low: 0,
        medium: 0,
        high: 0,
        unavailable: 0
      };

      for (const network of result?.networks ?? []) {
        initial[
          network.analysis.suspicion_level
        ] += 1;
      }

      return initial;
    },
    [result]
  );

  const visibleNetworks = useMemo(
    () => {
      const normalized = query
        .trim()
        .toLowerCase();

      return (
        result?.networks
        .filter(network =>
          filter === "all"
          || network.analysis.suspicion_level === filter
        )
        .filter(network => {
          if (!normalized) {
            return true;
          }

          return (
            network.ssid.toLowerCase().includes(normalized)
            || network.bssid.toLowerCase().includes(normalized)
            || network.security_type.toLowerCase().includes(normalized)
          );
        })
        ?? []
      );
    },
    [filter, query, result]
  );

  const openLocationSettings = useCallback(
    () => {
      if (
        window.evilTwinDesktop
        ?.openLocationSettings
      ) {
        void window.evilTwinDesktop
          .openLocationSettings();
      }
    },
    []
  );

  return (
    <div className="space-y-7">
      <PageHeader
        title="Escanear redes"
        description="Execute uma varredura Native Wi-Fi do Windows e visualize os sinais observados. Quando o modelo estiver pronto, cada rede recebe uma indicação de anomalia/suspeita — nunca uma confirmação automática de Evil Twin."
        actions={
          <button
            className="btn-primary"
            type="button"
            disabled={loading}
            onClick={() => void scan()}
          >
            {loading ? (
              <LoaderCircle
                className="animate-spin"
                size={17}
              />
            ) : (
              <Radar size={17} />
            )}
            {loading
              ? "Escaneando…"
              : result
                ? "Executar novo scan"
                : "Iniciar scan"}
          </button>
        }
      />

      <PreflightPanel
        data={preflight}
        loading={preflightLoading}
        onRefresh={() => void loadPreflight()}
      />

      {loading && (
        <section className="panel p-5">
          <div className="flex items-center gap-4">
            <div className="grid size-11 place-items-center rounded-xl bg-slate-950 text-white">
              <LoaderCircle
                className="animate-spin"
                size={20}
              />
            </div>
            <div>
              <p className="font-semibold text-slate-900">
                Solicitando varredura ao Windows
              </p>
              <p className="mt-1 text-sm text-slate-500">
                O `WlanScan` é assíncrono. O backend aguarda o intervalo configurado antes de ler a lista de BSS observadas.
              </p>
            </div>
          </div>
        </section>
      )}

      {error && (
        <ScanErrorPanel
          error={error}
          onRetry={() => void scan()}
          onOpenLocationSettings={
            error.kind === "location_access_denied"
            && window.evilTwinDesktop?.openLocationSettings
              ? openLocationSettings
              : undefined
          }
        />
      )}

      {!result && !loading && !error && (
        <EmptyScanState />
      )}

      {result && (
        <>
          <ScanSummary
            result={result}
            counts={counts}
          />

          <section className="panel overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 px-5 py-4">
              <div>
                <h2 className="section-title">
                  Redes observadas
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  {visibleNetworks.length} de {result.total_networks} observações exibidas
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <Search
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    size={15}
                  />
                  <input
                    value={query}
                    onChange={event => setQuery(event.target.value)}
                    placeholder="SSID, BSSID ou segurança"
                    className="h-10 w-64 rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-slate-400"
                  />
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 border-b border-slate-100 px-5 py-3">
              {(
                Object.keys(filterLabels) as Filter[]
              ).map(item => {
                const count = item === "all"
                  ? result.total_networks
                  : counts[item];

                return (
                  <button
                    key={item}
                    type="button"
                    onClick={() => setFilter(item)}
                    className={[
                      "rounded-full px-3 py-1.5 text-xs font-medium transition",
                      filter === item
                        ? "bg-slate-950 text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    ].join(" ")}
                  >
                    {filterLabels[item]} · {count}
                  </button>
                );
              })}
            </div>

            {visibleNetworks.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-sm font-medium text-slate-700">
                  Nenhuma rede corresponde aos filtros atuais.
                </p>
                <button
                  type="button"
                  className="mt-3 text-sm font-medium text-slate-600 underline underline-offset-4"
                  onClick={() => {
                    setFilter("all");
                    setQuery("");
                  }}
                >
                  Limpar filtros
                </button>
              </div>
            ) : (
              <div>
                {visibleNetworks.map(network => (
                  <NetworkScanCard
                    key={network.network_id}
                    network={network}
                  />
                ))}
              </div>
            )}
          </section>

          <PrivacyNote />
        </>
      )}
    </div>
  );
}

function PreflightPanel({
  data,
  loading,
  onRefresh
}: {
  data: PreflightState | null;
  loading: boolean;
  onRefresh: () => void;
}) {
  return (
    <section className="panel p-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="section-title">
            Pré-verificação
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Estado do serviço local e preferências que serão usadas se o scan não enviar overrides.
          </p>
        </div>

        <button
          className="btn-secondary"
          type="button"
          disabled={loading}
          onClick={onRefresh}
        >
          <RefreshCw
            className={loading ? "animate-spin" : undefined}
            size={15}
          />
          Atualizar
        </button>
      </div>

      {!data ? (
        <div className="mt-5 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
          Não foi possível ler o estado do backend. O scan ainda pode ser tentado para obter uma mensagem de erro específica.
        </div>
      ) : (
        <div className="mt-5 grid grid-cols-4 gap-4">
          <PreflightItem
            icon={<Wifi size={18} />}
            label="Scanner"
            value={
              <StatusBadge
                value={data.health.scanner_status}
              />
            }
          />

          <PreflightItem
            icon={<Activity size={18} />}
            label="Modelo"
            value={
              <StatusBadge
                value={data.health.model_status}
              />
            }
          />

          <PreflightItem
            icon={<Database size={18} />}
            label="Banco local"
            value={
              <StatusBadge
                value={data.health.database_status}
              />
            }
          />

          <PreflightItem
            icon={<Radar size={18} />}
            label="Espera do scan"
            value={
              <span className="text-sm font-semibold text-slate-800">
                {data.settings.values.scan_wait_seconds}s
              </span>
            }
          />
        </div>
      )}
    </section>
  );
}

function PreflightItem({
  icon,
  label,
  value
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
      <div className="flex items-center gap-2 text-slate-400">
        {icon}
        <span className="text-xs font-medium uppercase tracking-wide">
          {label}
        </span>
      </div>
      <div className="mt-3">
        {value}
      </div>
    </div>
  );
}

function EmptyScanState() {
  return (
    <section className="panel p-10 text-center">
      <div className="mx-auto grid size-14 place-items-center rounded-2xl bg-slate-100 text-slate-500">
        <Radar size={25} />
      </div>
      <h2 className="mt-4 font-semibold text-slate-900">
        Nenhuma varredura executada nesta sessão
      </h2>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-500">
        O scan consulta as redes visíveis pelo adaptador Wi-Fi do Windows. Se o acesso a BSSID estiver bloqueado, o sistema exibirá a orientação para habilitar a permissão de localização.
      </p>
    </section>
  );
}

function ScanSummary({
  result,
  counts
}: {
  result: ScanResponse;
  counts: Record<SuspicionLevel, number>;
}) {
  return (
    <section className="grid grid-cols-[1.4fr_repeat(4,1fr)] gap-4">
      <div className="panel p-5">
        <p className="text-sm font-medium text-slate-500">
          Última varredura
        </p>
        <p className="mt-2 text-lg font-semibold text-slate-950">
          {formatDateTime(result.observed_at_utc)}
        </p>
        <p className="mt-2 text-xs text-slate-400">
          {result.interface_count} interface(s) · API {result.negotiated_api_version}
        </p>
      </div>

      <SummaryMetric
        label="Redes"
        value={result.total_networks}
        icon={<Wifi size={17} />}
      />
      <SummaryMetric
        label="Baixa"
        value={counts.low}
        badge="low"
      />
      <SummaryMetric
        label="Alta"
        value={counts.high}
        badge="high"
      />
      <SummaryMetric
        label="Indisponível"
        value={counts.unavailable}
        badge="unavailable"
      />
    </section>
  );
}

function SummaryMetric({
  label,
  value,
  icon,
  badge
}: {
  label: string;
  value: number;
  icon?: ReactNode;
  badge?: SuspicionLevel;
}) {
  return (
    <div className="panel p-5">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium text-slate-500">
          {label}
        </p>
        {icon && (
          <span className="text-slate-400">
            {icon}
          </span>
        )}
        {badge && (
          <SuspicionBadge level={badge} />
        )}
      </div>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
        {value}
      </p>
    </div>
  );
}

function PrivacyNote() {
  return (
    <section className="grid grid-cols-2 gap-4">
      <div className="rounded-2xl border border-sky-200 bg-sky-50 p-5">
        <div className="flex items-start gap-3">
          <ShieldCheck
            className="mt-0.5 shrink-0 text-sky-700"
            size={19}
          />
          <div>
            <p className="font-semibold text-sky-950">
              Identificadores em claro ficam no runtime
            </p>
            <p className="mt-1 text-sm leading-6 text-sky-800">
              SSID e BSSID podem aparecer nesta tela para identificar a rede observada. O histórico local persiste apenas hashes desses identificadores.
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
        <div className="flex items-start gap-3">
          <AlertTriangle
            className="mt-0.5 shrink-0 text-amber-700"
            size={19}
          />
          <div>
            <p className="font-semibold text-amber-950">
              Suspeita não é confirmação
            </p>
            <p className="mt-1 text-sm leading-6 text-amber-800">
              Um nível alto significa que a observação ficou acima do threshold do detector de anomalias. Ele não prova, isoladamente, a existência de um Evil Twin.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
