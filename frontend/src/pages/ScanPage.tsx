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
  Clock3,
  Database,
  LoaderCircle,
  Radar,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Wifi,
  Zap
} from "lucide-react";
import { motion, useReducedMotion } from "motion/react";

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
import {
  ScanRadarScene
} from "../components/visual/ScanRadarScene";
import { useRuntimeStatus } from "../contexts/RuntimeStatusContext";
import {
  api
} from "../lib/api";
import {
  animationTokens
} from "../lib/animation";
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

const filterActiveClasses: Record<Filter, string> = {
  all: "bg-[#31396f] text-white shadow-[0_7px_18px_rgba(49,57,111,0.2)]",
  low: "bg-emerald-600 text-white shadow-[0_7px_18px_rgba(5,150,105,0.15)]",
  medium: "bg-amber-500 text-white shadow-[0_7px_18px_rgba(245,158,11,0.15)]",
  high: "bg-rose-500 text-white shadow-[0_7px_18px_rgba(244,63,94,0.15)]",
  unavailable: "bg-slate-600 text-white shadow-[0_7px_18px_rgba(71,85,105,0.15)]"
};

export function ScanPage() {
  const runtime = useRuntimeStatus();
  const shouldReduceMotion = useReducedMotion();
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
    <motion.div
      className="space-y-6"
      initial={shouldReduceMotion ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: shouldReduceMotion ? 0 : animationTokens.duration.base }}
    >
      <PageHeader
        title="Escanear redes"
        description="Execute uma varredura Native Wi-Fi do Windows e visualize os sinais observados. Quando o modelo estiver pronto, cada rede recebe uma indicação de anomalia/suspeita — nunca uma confirmação automática de Evil Twin."
      />

      <ScannerHero
        loading={loading}
        result={result}
        preflight={preflight}
        preflightLoading={preflightLoading}
        highRiskCount={counts.high}
        onScan={() => void scan()}
      />

      <PreflightPanel
        data={preflight}
        loading={preflightLoading}
        onRefresh={() => void loadPreflight()}
      />

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
            <div className="flex flex-wrap items-end justify-between gap-5 border-b border-[#edf0f6] px-6 py-5">
              <div>
                <div className="mb-2 flex items-center gap-2 text-[#5268ce]">
                  <span className="size-1.5 rounded-full bg-[#2ac7a9]" />
                  <span className="text-[10px] font-bold uppercase tracking-[0.15em]">
                    Resultado da varredura
                  </span>
                </div>
                <h2 className="section-title">
                  Redes observadas
                </h2>
                <p className="mt-1 text-sm text-[#7b829a]">
                  {visibleNetworks.length} de {result.total_networks} observações exibidas
                </p>
              </div>

              <div className="relative">
                <Search
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#9aa0b5]"
                  size={15}
                />
                <input
                  value={query}
                  onChange={event => setQuery(event.target.value)}
                  placeholder="SSID, BSSID ou segurança"
                  className="h-11 w-72 rounded-2xl border border-[#e3e6f0] bg-[#fafbfe] pl-10 pr-4 text-sm text-[#4d546d] outline-none transition placeholder:text-[#a4a9ba] focus:border-[#7485dc] focus:bg-white focus:shadow-[0_0_0_4px_rgba(73,104,232,0.08)] max-[760px]:w-full"
                />
              </div>
            </div>

            <div className="flex flex-wrap gap-2 border-b border-[#edf0f6] bg-[#fbfcff] px-6 py-3.5">
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
                      "rounded-full px-3.5 py-2 text-xs font-semibold transition-all duration-200",
                      filter === item
                        ? filterActiveClasses[item]
                        : "border border-[#e7e9f1] bg-white text-[#70778f] hover:border-[#d6daea] hover:text-[#3d4562]"
                    ].join(" ")}
                  >
                    {filterLabels[item]} · {count}
                  </button>
                );
              })}
            </div>

            {visibleNetworks.length === 0 ? (
              <div className="px-8 py-12 text-center">
                <div className="mx-auto grid size-12 place-items-center rounded-2xl bg-[#f1f3fa] text-[#6b75bc]">
                  <Search size={20} />
                </div>
                <p className="mt-4 text-sm font-semibold text-[#424960]">
                  Nenhuma rede corresponde aos filtros atuais.
                </p>
                <button
                  type="button"
                  className="mt-3 text-sm font-semibold text-[#5268ce] underline decoration-[#c5ccef] underline-offset-4"
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
    </motion.div>
  );
}

function ScannerHero({
  loading,
  result,
  preflight,
  preflightLoading,
  highRiskCount,
  onScan
}: {
  loading: boolean;
  result: ScanResponse | null;
  preflight: PreflightState | null;
  preflightLoading: boolean;
  highRiskCount: number;
  onScan: () => void;
}) {
  const scannerReady = preflight?.health.scanner_status === "ready";
  const modelReady = preflight?.health.model_status === "ready";

  return (
    <section className="relative min-h-[410px] overflow-hidden rounded-[30px] border border-white/10 bg-[linear-gradient(135deg,#303776_0%,#303b83_46%,#252b60_100%)] shadow-[0_24px_64px_rgba(37,43,96,0.18)]">
      <div className="pointer-events-none absolute -left-20 -top-24 size-72 rounded-full border border-white/[0.07]" />
      <div className="pointer-events-none absolute -left-4 -top-8 size-44 rounded-full border border-white/[0.05]" />
      <div className="pointer-events-none absolute bottom-[-90px] left-[36%] size-56 rounded-full bg-[#2ac7a5]/10 blur-3xl" />

      <div className="grid min-h-[410px] grid-cols-[minmax(0,1.04fr)_minmax(430px,.96fr)] max-[1080px]:grid-cols-1">
        <div className="relative z-10 flex flex-col justify-between p-8 lg:p-10">
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.07] px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.15em] text-white/70">
                <span className={`size-1.5 rounded-full ${scannerReady ? "bg-[#2ac7a9]" : "bg-amber-300"}`} />
                {preflightLoading
                  ? "Verificando scanner"
                  : scannerReady
                    ? "Scanner pronto"
                    : "Scanner requer atenção"}
              </span>

              {modelReady && (
                <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.07] px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.15em] text-white/55">
                  <Sparkles size={12} className="text-[#8fe4d2]" />
                  Modelo ativo
                </span>
              )}
            </div>

            <h2 className="mt-7 max-w-[620px] text-[clamp(2rem,3.5vw,3.4rem)] font-semibold leading-[1.03] tracking-[-0.045em] text-white">
              Observe o ambiente Wi-Fi em tempo real.
            </h2>
            <p className="mt-5 max-w-[590px] text-[15px] leading-7 text-white/62">
              Faça uma leitura do espectro visível pelo adaptador local, compare o comportamento de cada rede com o histórico disponível e concentre sua atenção nos sinais que merecem investigação.
            </p>
          </div>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <button
              className="inline-flex min-h-12 items-center justify-center gap-2.5 rounded-2xl border border-white bg-white px-5 text-sm font-bold text-[#303776] shadow-[0_12px_32px_rgba(17,22,62,0.22)] transition hover:-translate-y-0.5 hover:shadow-[0_16px_38px_rgba(17,22,62,0.28)] disabled:cursor-not-allowed disabled:opacity-70 disabled:hover:translate-y-0"
              type="button"
              disabled={loading}
              onClick={onScan}
            >
              {loading ? (
                <LoaderCircle
                  className="animate-spin"
                  size={18}
                />
              ) : (
                <Radar size={18} />
              )}
              {loading
                ? "Escaneando…"
                : result
                  ? "Executar novo scan"
                  : "Iniciar scan"}
            </button>

            <div className="flex items-center gap-2.5 text-xs text-white/46">
              <Clock3 size={14} />
              <span>
                {preflight
                  ? `Aguarda ${preflight.settings.values.scan_wait_seconds}s antes de ler as BSS`
                  : "Native Wi-Fi · execução local"}
              </span>
            </div>
          </div>

          {loading && (
            <div className="mt-5 max-w-[620px] rounded-2xl border border-white/10 bg-white/[0.065] px-4 py-3.5" role="status" aria-live="polite">
              <div className="flex items-center gap-3">
                <div className="relative size-9 shrink-0">
                  <span className="absolute inset-0 rounded-full border border-[#7de1cc]/25" />
                  <span className="absolute inset-[6px] rounded-full bg-[#2ac7a9] shadow-[0_0_18px_rgba(42,199,169,0.45)]" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">
                    Solicitando varredura ao Windows
                  </p>
                  <p className="mt-0.5 text-xs leading-5 text-white/48">
                    O WlanScan é assíncrono. O backend aguarda o intervalo configurado antes de ler a lista de BSS observadas.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="relative min-h-[360px] overflow-hidden border-l border-white/[0.07] max-[1080px]:border-l-0 max-[1080px]:border-t">
          <ScanRadarScene
            active={loading}
            networkCount={result?.total_networks ?? 0}
            highRiskCount={highRiskCount}
          />

          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(48,55,118,0.62)_0%,rgba(48,55,118,0.12)_35%,rgba(48,55,118,0)_100%)] max-[1080px]:bg-[linear-gradient(180deg,rgba(48,55,118,0.38)_0%,rgba(48,55,118,0)_45%)]" />

          <div className="absolute bottom-7 left-7 right-7 flex items-end justify-between gap-4">
            <div className="rounded-2xl border border-white/10 bg-[#242b60]/70 px-4 py-3 backdrop-blur-md">
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-white/40">
                Último resultado
              </p>
              <p className="mt-1.5 text-xl font-semibold text-white">
                {result ? `${result.total_networks} redes` : "Aguardando scan"}
              </p>
            </div>

            {result && (
              <div className="rounded-2xl border border-white/10 bg-[#242b60]/70 px-4 py-3 text-right backdrop-blur-md">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-white/40">
                  Alta suspeita
                </p>
                <p className={`mt-1.5 text-xl font-semibold ${highRiskCount > 0 ? "text-rose-300" : "text-[#8fe4d2]"}`}>
                  {highRiskCount}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
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
    <section className="panel px-6 py-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[#5268ce]">
            <Zap size={14} />
            <span className="text-[10px] font-bold uppercase tracking-[0.14em]">
              Pré-verificação
            </span>
          </div>
          <p className="mt-1.5 text-sm text-[#7b829a]">
            Condições locais utilizadas para a próxima leitura.
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
        <div className="mt-5 rounded-2xl border border-[#eceef5] bg-[#f8f9fc] p-4 text-sm leading-6 text-[#767d95]">
          Não foi possível ler o estado do backend. O scan ainda pode ser tentado para obter uma mensagem de erro específica.
        </div>
      ) : (
        <div className="mt-5 grid grid-cols-4 divide-x divide-[#edf0f6] rounded-2xl border border-[#e7e9f2] bg-[#fbfcff] max-[980px]:grid-cols-2 max-[980px]:divide-x-0 max-[980px]:gap-px max-[980px]:bg-[#e7e9f2] max-[680px]:grid-cols-1">
          <PreflightItem
            icon={<Wifi size={17} />}
            label="Scanner"
            value={
              <StatusBadge
                value={data.health.scanner_status}
              />
            }
          />

          <PreflightItem
            icon={<Activity size={17} />}
            label="Modelo"
            value={
              <StatusBadge
                value={data.health.model_status}
              />
            }
          />

          <PreflightItem
            icon={<Database size={17} />}
            label="Banco local"
            value={
              <StatusBadge
                value={data.health.database_status}
              />
            }
          />

          <PreflightItem
            icon={<Radar size={17} />}
            label="Espera do scan"
            value={
              <span className="text-sm font-bold tabular-nums text-[#39405b]">
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
    <div className="flex min-h-[88px] items-center justify-between gap-4 bg-[#fbfcff] px-5 py-4 first:rounded-l-2xl last:rounded-r-2xl max-[980px]:rounded-none max-[980px]:first:rounded-none max-[980px]:last:rounded-none">
      <div className="flex items-center gap-3">
        <span className="grid size-9 place-items-center rounded-xl bg-white text-[#596bc8] shadow-[0_5px_16px_rgba(35,41,87,0.05)]">
          {icon}
        </span>
        <span className="text-xs font-semibold text-[#777e95]">
          {label}
        </span>
      </div>
      <div>
        {value}
      </div>
    </div>
  );
}

function EmptyScanState() {
  return (
    <section className="grid grid-cols-[auto_1fr_auto] items-center gap-5 rounded-[24px] border border-[#e5e8f2] bg-white px-6 py-5 shadow-[0_10px_30px_rgba(35,41,87,0.045)] max-[840px]:grid-cols-[auto_1fr]">
      <div className="grid size-12 place-items-center rounded-2xl bg-[#eef1ff] text-[#5268ce]">
        <Radar size={21} />
      </div>
      <div>
        <h2 className="text-sm font-semibold text-[#30364e]">
          Nenhuma varredura executada nesta sessão
        </h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-[#7b829a]">
          O scan consulta as redes visíveis pelo adaptador Wi-Fi do Windows. Se o acesso a BSSID estiver bloqueado, o sistema exibirá a orientação para habilitar a permissão de localização.
        </p>
      </div>
      <div className="flex items-center gap-2 rounded-full bg-[#f5f7fb] px-3 py-2 text-[11px] font-semibold text-[#8a90a5] max-[840px]:col-start-2 max-[840px]:justify-self-start">
        <ShieldCheck size={13} />
        Processamento local
      </div>
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
    <section className="grid grid-cols-[1.5fr_repeat(4,minmax(120px,1fr))] gap-4 max-[1180px]:grid-cols-3 max-[760px]:grid-cols-2">
      <div className="relative overflow-hidden rounded-[24px] border border-[#e3e6f0] bg-[linear-gradient(135deg,#ffffff_0%,#f5f7ff_100%)] p-5 shadow-[0_10px_30px_rgba(35,41,87,0.045)] max-[1180px]:col-span-3 max-[760px]:col-span-2">
        <div className="absolute -right-8 -top-12 size-32 rounded-full bg-[#5268ce]/[0.06]" />
        <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9aa0b5]">
          Última varredura
        </p>
        <p className="mt-2 text-lg font-semibold tracking-[-0.02em] text-[#252b43]">
          {formatDateTime(result.observed_at_utc)}
        </p>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs font-medium text-[#858ca2]">
          <span>{result.interface_count} interface(s)</span>
          <span className="text-[#c0c4d0]">•</span>
          <span>API {result.negotiated_api_version}</span>
          <span className="text-[#c0c4d0]">•</span>
          <span className="max-w-[210px] truncate font-mono">{result.scan_id}</span>
        </div>
      </div>

      <SummaryMetric
        label="Redes"
        value={result.total_networks}
        icon={<Wifi size={17} />}
        accent="indigo"
      />
      <SummaryMetric
        label="Baixa"
        value={counts.low}
        badge="low"
        accent="mint"
      />
      <SummaryMetric
        label="Média"
        value={counts.medium}
        badge="medium"
        accent="amber"
      />
      <SummaryMetric
        label="Alta"
        value={counts.high}
        badge="high"
        accent="rose"
      />
    </section>
  );
}

function SummaryMetric({
  label,
  value,
  icon,
  badge,
  accent
}: {
  label: string;
  value: number;
  icon?: ReactNode;
  badge?: SuspicionLevel;
  accent: "indigo" | "mint" | "amber" | "rose";
}) {
  const accentClass = {
    indigo: "bg-[#5268ce]",
    mint: "bg-[#2ac7a9]",
    amber: "bg-amber-400",
    rose: "bg-rose-400"
  }[accent];

  return (
    <div className="relative overflow-hidden rounded-[24px] border border-[#e5e8f2] bg-white p-5 shadow-[0_10px_30px_rgba(35,41,87,0.045)]">
      <span className={`absolute left-0 top-0 h-1 w-full ${accentClass}`} aria-hidden="true" />
      <div className="flex min-h-7 items-center justify-between gap-2">
        <p className="text-xs font-semibold text-[#858ca2]">
          {label}
        </p>
        {icon && (
          <span className="text-[#6576cf]">
            {icon}
          </span>
        )}
        {badge && (
          <SuspicionBadge level={badge} />
        )}
      </div>
      <p className="mt-4 text-[32px] font-semibold leading-none tracking-[-0.04em] text-[#252b43]">
        {value}
      </p>
    </div>
  );
}

function PrivacyNote() {
  return (
    <section className="grid grid-cols-2 gap-4 max-[900px]:grid-cols-1">
      <div className="rounded-[24px] border border-[#dbe4fb] bg-[linear-gradient(135deg,#f8fbff_0%,#eef4ff_100%)] p-5">
        <div className="flex items-start gap-3.5">
          <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-white text-[#5268ce] shadow-[0_6px_18px_rgba(73,104,232,0.08)]">
            <ShieldCheck size={18} />
          </div>
          <div>
            <p className="font-semibold text-[#303a66]">
              Identificadores em claro ficam no runtime
            </p>
            <p className="mt-1.5 text-sm leading-6 text-[#68749b]">
              SSID e BSSID podem aparecer nesta tela para identificar a rede observada. O histórico local persiste apenas hashes desses identificadores.
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-[24px] border border-amber-200/80 bg-[linear-gradient(135deg,#fffdf7_0%,#fff8e8_100%)] p-5">
        <div className="flex items-start gap-3.5">
          <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-white text-amber-600 shadow-[0_6px_18px_rgba(180,120,20,0.08)]">
            <AlertTriangle size={18} />
          </div>
          <div>
            <p className="font-semibold text-amber-950">
              Suspeita não é confirmação
            </p>
            <p className="mt-1.5 text-sm leading-6 text-amber-800/80">
              Um nível alto significa que a observação ficou acima do threshold do detector de anomalias. Ele não prova, isoladamente, a existência de um Evil Twin.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
