import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode
} from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Cpu,
  Database,
  RadioTower,
  RefreshCw,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Wifi
} from "lucide-react";
import { gsap } from "gsap";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import {
  AutoScanRefreshNotice
} from "../components/AutoScanRefreshNotice";
import {
  PageHeader
} from "../components/PageHeader";
import {
  StatCard
} from "../components/StatCard";
import {
  StatusBadge
} from "../components/StatusBadge";
import {
  SuspicionBadge
} from "../components/SuspicionBadge";
import {
  useAutoScanRefresh
} from "../hooks/useAutoScanRefresh";
import {
  api
} from "../lib/api";
import {
  formatDateTime,
  formatDecimal,
  formatPercent,
  formatShortDateTime
} from "../lib/format";
import type {
  DashboardOverviewResponse,
  DashboardTrendsResponse,
  ScannerStatus
} from "../types/api";

interface DashboardState {
  overview: DashboardOverviewResponse;
  trends: DashboardTrendsResponse;
}

export function DashboardPage() {
  const [data, setData] = useState<DashboardState | null>(null);
  const [loading, setLoading] = useState(true);
  const [backgroundRefreshing, setBackgroundRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (
      options: {
        background?: boolean;
      } = {}
    ) => {
      const background = options.background === true;

      if (background) {
        setBackgroundRefreshing(true);
      } else {
        setLoading(true);
      }

      setError(null);

      try {
        const [overview, trends] = await Promise.all([
          api.dashboard(),
          api.dashboardTrends()
        ]);

        setData({
          overview,
          trends
        });
      } catch {
        setError("Não foi possível acessar os dados do backend local.");
        throw new Error("dashboard_refresh_failed");
      } finally {
        if (background) {
          setBackgroundRefreshing(false);
        } else {
          setLoading(false);
        }
      }
    },
    []
  );

  useEffect(
    () => {
      void load().catch(() => undefined);
    },
    [load]
  );

  const autoRefresh = useAutoScanRefresh(
    useCallback(
      async () => {
        await load({
          background: true
        });
      },
      [load]
    )
  );

  const trendData = useMemo(
    () =>
      data?.trends.points.map(point => ({
        ...point,
        label: formatShortDateTime(point.observed_at_utc)
      })) ?? [],
    [data]
  );

  return (
    <div className="space-y-7">
      <PageHeader
        title="Visão geral"
        description="Resumo operacional do detector, atividade recente e evolução das análises registradas no dispositivo."
        actions={
          <div className="flex flex-wrap items-center justify-end gap-2">
            <AutoScanRefreshNotice state={autoRefresh} />
            <button
              className="btn-secondary"
              type="button"
              disabled={loading || backgroundRefreshing}
              onClick={() =>
                void load().catch(() => undefined)
              }
            >
              <RefreshCw
                className={loading || backgroundRefreshing ? "animate-spin" : undefined}
                size={16}
              />
              Atualizar
            </button>
          </div>
        }
      />

      {error && (
        <div className="flex items-start gap-3 rounded-[20px] border border-amber-200/80 bg-amber-50/90 p-4 text-sm text-amber-900 shadow-[0_8px_24px_rgba(120,75,0,0.05)]">
          <div className="grid size-9 shrink-0 place-items-center rounded-xl bg-white/80 text-amber-600 shadow-sm">
            <AlertTriangle size={17} />
          </div>
          <div className="pt-0.5">
            <p className="font-semibold">Backend indisponível</p>
            <p className="mt-1 text-amber-700">{error}</p>
          </div>
        </div>
      )}

      {loading && !data ? (
        <DashboardSkeleton />
      ) : data ? (
        <DashboardContent
          data={data}
          trendData={trendData}
        />
      ) : (
        <EmptyDashboard />
      )}
    </div>
  );
}

function DashboardContent({
  data,
  trendData
}: {
  data: DashboardState;
  trendData: Array<DashboardTrendsResponse["points"][number] & { label: string }>;
}) {
  const rootRef = useRef<HTMLDivElement>(null);
  const { overview } = data;
  const hasHistory = overview.metrics.scan_count > 0;

  useLayoutEffect(() => {
    const root = rootRef.current;

    if (!root || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    const elements = Array.from(
      root.querySelectorAll<HTMLElement>("[data-dashboard-reveal]")
    );

    const tween = gsap.fromTo(
      elements,
      {
        y: 18,
        opacity: 0
      },
      {
        y: 0,
        opacity: 1,
        duration: 0.58,
        stagger: 0.065,
        ease: "power2.out",
        clearProps: "transform,opacity"
      }
    );

    return () => {
      tween.kill();
    };
  }, []);

  return (
    <div ref={rootRef} className="space-y-5">
      <section data-dashboard-reveal>
        <OperationalHero overview={overview} />
      </section>

      <section data-dashboard-reveal className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Scans realizados"
          value={overview.metrics.scan_count}
          helper={
            overview.latest_scan_at_utc
              ? `Último: ${formatDateTime(overview.latest_scan_at_utc)}`
              : "Nenhum scan persistido"
          }
          icon={ScanSearch}
          tone="blue"
        />

        <StatCard
          label="Redes distintas"
          value={overview.metrics.unique_network_count}
          helper={`${overview.metrics.observation_count} observações persistidas`}
          icon={Wifi}
          tone="mint"
        />

        <StatCard
          label="Anomalias"
          value={overview.metrics.anomaly_count}
          helper={`${formatPercent(overview.metrics.anomaly_rate_among_decided)} das decisões válidas`}
          icon={AlertTriangle}
          tone="amber"
        />

        <StatCard
          label="Histórico insuficiente"
          value={overview.metrics.insufficient_history_count}
          helper="Sem decisão binária de anomalia"
          icon={Clock3}
          tone="indigo"
        />
      </section>

      <section data-dashboard-reveal className="grid gap-4 xl:grid-cols-[1.12fr_0.88fr]">
        <div className="panel overflow-hidden p-5 sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div>
              <div className="flex items-center gap-2 text-[#353c7d]">
                <span className="grid size-8 place-items-center rounded-xl bg-[#eef0fb]">
                  <Cpu size={16} />
                </span>
                <h2 className="section-title">Estado do sistema</h2>
              </div>
              <p className="muted mt-2">Serviços necessários para a análise local.</p>
            </div>

            <div className="rounded-full border border-[#e6e8f1] bg-[#f8f9fc] px-3 py-1.5 text-[11px] font-medium text-[#858ca2]">
              Backend {overview.system.backend_version}
            </div>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <SystemStatusCard
              icon={Database}
              label="Banco local"
              value={overview.system.database_status}
              helper="SQLite"
            />
            <SystemStatusCard
              icon={ShieldCheck}
              label="Modelo"
              value={overview.system.model_status}
              helper={
                overview.system.model_status === "ready"
                  ? "Artefatos disponíveis"
                  : "Artefatos reais pendentes"
              }
            />
            <SystemStatusCard
              icon={RadioTower}
              label="Scanner"
              value={overview.system.scanner_status}
              helper={overview.system.platform}
            />
          </div>
        </div>

        <div className="panel overflow-hidden p-5 sm:p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="section-title">Cobertura da análise</h2>
              <p className="muted mt-2">Relação entre observações persistidas e análises auditáveis.</p>
            </div>
            <div className="grid size-10 shrink-0 place-items-center rounded-[14px] bg-[#eafaf6] text-[#1aa88d]">
              <Activity size={18} />
            </div>
          </div>

          <div className="mt-7 space-y-6">
            <ProgressMetric
              label="Cobertura"
              value={overview.metrics.analysis_coverage_rate}
              text={formatPercent(overview.metrics.analysis_coverage_rate)}
              tone="blue"
            />
            <ProgressMetric
              label="Anomalias entre decisões"
              value={overview.metrics.anomaly_rate_among_decided}
              text={formatPercent(overview.metrics.anomaly_rate_among_decided)}
              tone="mint"
            />
          </div>

          <div className="mt-6 grid grid-cols-3 gap-3 border-t border-[#edf0f5] pt-5">
            <MiniMetric label="Features" value={overview.metrics.feature_count} />
            <MiniMetric label="Detecções" value={overview.metrics.detection_count} />
            <MiniMetric label="Modelos" value={overview.metrics.model_version_count} />
          </div>
        </div>
      </section>

      <section data-dashboard-reveal className="grid gap-4 xl:grid-cols-[1.38fr_0.62fr]">
        <ChartPanel
          title="Evolução dos scans"
          description="Redes observadas e decisões registradas nos scans mais recentes."
          empty={!hasHistory || trendData.length === 0}
          legend={
            <div className="flex items-center gap-4 text-[11px] font-medium text-[#8a91a7]">
              <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-[#353c7d]" />Redes</span>
              <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-[#4968e8]" />Análises</span>
            </div>
          }
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={trendData}
              margin={{
                top: 14,
                right: 8,
                left: -18,
                bottom: 0
              }}
            >
              <defs>
                <linearGradient id="dashboardNetworks" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#353c7d" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#353c7d" stopOpacity={0.01} />
                </linearGradient>
                <linearGradient id="dashboardDetections" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#4968e8" stopOpacity={0.18} />
                  <stop offset="100%" stopColor="#4968e8" stopOpacity={0.01} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke="#edf0f5" />
              <XAxis
                dataKey="label"
                tick={{
                  fill: "#9298ab",
                  fontSize: 10
                }}
                tickLine={false}
                axisLine={false}
                minTickGap={28}
              />
              <YAxis
                allowDecimals={false}
                tick={{
                  fill: "#9298ab",
                  fontSize: 10
                }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                cursor={{ stroke: "#dfe3ef", strokeWidth: 1 }}
                contentStyle={{
                  borderRadius: 14,
                  borderColor: "#e4e7f0",
                  boxShadow: "0 14px 36px rgba(34,39,76,0.10)",
                  fontSize: 12
                }}
              />
              <Area
                type="monotone"
                dataKey="network_count"
                name="Redes"
                stroke="#353c7d"
                fill="url(#dashboardNetworks)"
                strokeWidth={2.2}
                dot={false}
                activeDot={{ r: 4 }}
              />
              <Area
                type="monotone"
                dataKey="detection_count"
                name="Análises"
                stroke="#4968e8"
                fill="url(#dashboardDetections)"
                strokeWidth={2.2}
                dot={false}
                activeDot={{ r: 4 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel
          title="Distribuição de suspeita"
          description="Contagem histórica por nível retornado pelo runtime."
          empty={overview.metrics.detection_count === 0}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={[
                {
                  name: "Baixa",
                  value: overview.suspicion_distribution.low,
                  color: "#2ac7a9"
                },
                {
                  name: "Média",
                  value: overview.suspicion_distribution.medium,
                  color: "#f3b64a"
                },
                {
                  name: "Alta",
                  value: overview.suspicion_distribution.high,
                  color: "#ef6b6b"
                },
                {
                  name: "Indisp.",
                  value: overview.suspicion_distribution.unavailable,
                  color: "#adb3c4"
                }
              ]}
              margin={{
                top: 14,
                right: 8,
                left: -18,
                bottom: 0
              }}
            >
              <CartesianGrid vertical={false} stroke="#edf0f5" />
              <XAxis
                dataKey="name"
                tick={{
                  fill: "#9298ab",
                  fontSize: 10
                }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{
                  fill: "#9298ab",
                  fontSize: 10
                }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                cursor={{ fill: "#f7f8fb" }}
                contentStyle={{
                  borderRadius: 14,
                  borderColor: "#e4e7f0",
                  boxShadow: "0 14px 36px rgba(34,39,76,0.10)",
                  fontSize: 12
                }}
              />
              <Bar dataKey="value" name="Ocorrências" radius={[8, 8, 3, 3]} maxBarSize={42}>
                {[
                  "#2ac7a9",
                  "#f3b64a",
                  "#ef6b6b",
                  "#adb3c4"
                ].map(color => (
                  <Cell key={color} fill={color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>
      </section>

      <section data-dashboard-reveal className="grid gap-4 xl:grid-cols-2">
        <RecentScansPanel items={overview.recent_scans} />
        <RecentDetectionsPanel items={overview.recent_detections} />
      </section>

      <section data-dashboard-reveal className="grid gap-4 xl:grid-cols-[0.78fr_1.22fr]">
        <div className="panel overflow-hidden p-5 sm:p-6">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <span className="grid size-9 place-items-center rounded-[13px] bg-[#eef0fb] text-[#353c7d]">
                <Activity size={17} />
              </span>
              <div>
                <h2 className="section-title">Modelo ativo</h2>
                <p className="mt-1 text-xs text-[#9298ab]">Versão utilizada nas análises locais.</p>
              </div>
            </div>
          </div>

          {overview.active_model ? (
            <dl className="mt-6 space-y-1">
              <DetailRow label="Versão" value={overview.active_model.version_name} />
              <DetailRow label="Algoritmo" value={overview.active_model.algorithm} />
              <DetailRow label="Features" value={overview.active_model.feature_set_name} />
              <DetailRow
                label="Threshold"
                value={
                  overview.active_model.threshold === null
                    ? "—"
                    : formatDecimal(overview.active_model.threshold)
                }
              />
              <DetailRow label="Detecções" value={String(overview.active_model.detection_count)} />
            </dl>
          ) : (
            <div className="mt-6 rounded-[18px] border border-[#edf0f5] bg-[#f8f9fc] p-4 text-sm leading-6 text-[#7f869d]">
              Nenhuma versão real do modelo foi registrada no banco. O scanner pode continuar operando, mas a análise permanece indisponível.
            </div>
          )}
        </div>

        <div className="panel overflow-hidden p-5 sm:p-6">
          <div className="flex items-center gap-2.5">
            <span className="grid size-9 place-items-center rounded-[13px] bg-[#eef2ff] text-[#4968e8]">
              <Clock3 size={17} />
            </span>
            <div>
              <h2 className="section-title">Última atividade</h2>
              <p className="mt-1 text-xs text-[#9298ab]">Referências mais recentes registradas no dispositivo.</p>
            </div>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <ActivityCard
              icon={ScanSearch}
              title="Último scan"
              value={formatDateTime(overview.latest_scan_at_utc)}
            />
            <ActivityCard
              icon={ShieldCheck}
              title="Última detecção"
              value={formatDateTime(overview.latest_detection_at_utc)}
            />
          </div>

          <div className="mt-4 flex gap-3 rounded-[18px] border border-[#e7e9f1] bg-[#fafbfe] p-4">
            <div className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-xl bg-white text-[#4968e8] shadow-sm">
              <Sparkles size={15} />
            </div>
            <div>
              <p className="text-sm font-semibold text-[#333951]">Interpretação do protótipo</p>
              <p className="mt-1 text-sm leading-6 text-[#7c839a]">
                “Alta suspeita” representa uma observação acima do threshold de anomalia. O sistema não confirma, sozinho, a existência de um ataque Evil Twin.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function OperationalHero({
  overview
}: {
  overview: DashboardOverviewResponse;
}) {
  const rate = Math.max(
    0,
    Math.min(100, overview.metrics.anomaly_rate_among_decided * 100)
  );

  const readyServices = [
    overview.system.database_status === "ready",
    overview.system.model_status === "ready",
    overview.system.scanner_status === "ready"
  ].filter(Boolean).length;

  return (
    <div className="relative overflow-hidden rounded-[28px] border border-white/10 bg-[linear-gradient(135deg,#353c7d_0%,#2e356f_56%,#262c5d_100%)] px-6 py-6 text-white shadow-[0_24px_60px_rgba(35,41,87,0.16)] sm:px-7 sm:py-7">
      <div className="pointer-events-none absolute -right-24 -top-28 size-[340px] rounded-full border border-white/10" aria-hidden="true" />
      <div className="pointer-events-none absolute -right-8 top-8 size-40 rounded-full bg-[#2ac7a9]/10 blur-3xl" aria-hidden="true" />
      <div className="pointer-events-none absolute bottom-0 left-[44%] h-px w-[44%] bg-gradient-to-r from-transparent via-white/20 to-transparent" aria-hidden="true" />

      <div className="relative grid gap-7 xl:grid-cols-[minmax(0,1fr)_330px] xl:items-center">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.08] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/70">
              <span className="size-1.5 rounded-full bg-[#2ac7a9] shadow-[0_0_0_5px_rgba(42,199,169,0.11)]" />
              Security overview
            </span>
            <span className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 text-[10px] font-medium text-white/55">
              {readyServices}/3 serviços prontos
            </span>
          </div>

          <h2 className="mt-5 max-w-2xl text-[clamp(1.65rem,2.6vw,2.65rem)] font-semibold leading-[1.04] tracking-[-0.045em] text-white">
            Monitoramento Wi-Fi com leitura operacional mais clara.
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-white/58">
            Acompanhe scans, cobertura das análises e sinais de anomalia sem perder o contexto científico dos resultados.
          </p>

          <div className="mt-6 flex flex-wrap gap-2.5">
            <HeroStatus label="Banco" value={overview.system.database_status} />
            <HeroStatus label="Modelo" value={overview.system.model_status} />
            <HeroStatus label="Scanner" value={overview.system.scanner_status} />
          </div>

          <div className="mt-7 flex flex-wrap items-center gap-x-7 gap-y-3 border-t border-white/10 pt-5 text-xs text-white/48">
            <span>
              Último scan <strong className="ml-1 font-medium text-white/80">{formatDateTime(overview.latest_scan_at_utc)}</strong>
            </span>
            <span>
              Última detecção <strong className="ml-1 font-medium text-white/80">{formatDateTime(overview.latest_detection_at_utc)}</strong>
            </span>
          </div>
        </div>

        <div className="rounded-[24px] border border-white/10 bg-white/[0.075] p-5 backdrop-blur-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-white/42">Anomalias entre decisões</p>
              <p className="mt-2 text-sm text-white/64">Taxa histórica entre resultados com decisão válida.</p>
            </div>
            <ShieldCheck className="shrink-0 text-[#78e0cc]" size={20} />
          </div>

          <div className="mt-6 flex items-center gap-5">
            <div
              className="grid size-[126px] shrink-0 place-items-center rounded-full p-[10px]"
              style={{
                background: `conic-gradient(#2ac7a9 0 ${rate}%, rgba(255,255,255,0.11) ${rate}% 100%)`
              }}
            >
              <div className="grid size-full place-items-center rounded-full bg-[#30376f] text-center shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]">
                <div>
                  <p className="text-[25px] font-semibold tracking-[-0.04em] text-white">{formatPercent(overview.metrics.anomaly_rate_among_decided)}</p>
                  <p className="mt-0.5 text-[9px] font-semibold uppercase tracking-[0.13em] text-white/38">taxa</p>
                </div>
              </div>
            </div>

            <div className="min-w-0 flex-1 space-y-3">
              <HeroMetric label="Normais" value={overview.metrics.normal_count} accent="mint" />
              <HeroMetric label="Anomalias" value={overview.metrics.anomaly_count} accent="blue" />
              <HeroMetric label="Sem decisão" value={overview.metrics.insufficient_history_count} accent="neutral" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function HeroStatus({
  label,
  value
}: {
  label: string;
  value: string;
}) {
  const ready = value === "ready";

  return (
    <div className="flex items-center gap-2 rounded-[13px] border border-white/10 bg-white/[0.055] px-3 py-2 text-xs">
      <span className={`size-1.5 rounded-full ${ready ? "bg-[#2ac7a9]" : "bg-amber-400"}`} />
      <span className="text-white/46">{label}</span>
      <span className="font-medium text-white/82">{ready ? "Pronto" : value}</span>
    </div>
  );
}

function HeroMetric({
  label,
  value,
  accent
}: {
  label: string;
  value: number;
  accent: "mint" | "blue" | "neutral";
}) {
  const dotClass = accent === "mint"
    ? "bg-[#2ac7a9]"
    : accent === "blue"
      ? "bg-[#8ca3ff]"
      : "bg-white/35";

  return (
    <div className="flex items-center justify-between gap-3 border-b border-white/[0.07] pb-2.5 last:border-b-0 last:pb-0">
      <div className="flex min-w-0 items-center gap-2">
        <span className={`size-1.5 shrink-0 rounded-full ${dotClass}`} />
        <span className="truncate text-xs text-white/48">{label}</span>
      </div>
      <span className="text-sm font-semibold text-white/86">{value}</span>
    </div>
  );
}

function SystemStatusCard({
  icon: Icon,
  label,
  value,
  helper
}: {
  icon: typeof Database;
  label: string;
  value:
    | "ready"
    | "not_ready"
    | "error"
    | ScannerStatus;
  helper: string;
}) {
  return (
    <div className="rounded-[18px] border border-[#e8eaf2] bg-[#fbfbfd] p-4 transition-colors duration-200 hover:bg-white">
      <div className="flex items-center justify-between gap-3">
        <div className="grid size-9 place-items-center rounded-[13px] bg-white text-[#50577b] shadow-[0_5px_14px_rgba(34,39,76,0.055)]">
          <Icon size={16} />
        </div>
        <StatusBadge value={value} />
      </div>
      <p className="mt-4 text-sm font-semibold text-[#2b3049]">{label}</p>
      <p className="mt-1 truncate text-xs text-[#969caf]">{helper}</p>
    </div>
  );
}

function ProgressMetric({
  label,
  value,
  text,
  tone
}: {
  label: string;
  value: number;
  text: string;
  tone: "blue" | "mint";
}) {
  const width = Math.max(
    0,
    Math.min(100, value * 100)
  );

  return (
    <div>
      <div className="flex items-center justify-between gap-4 text-sm">
        <span className="font-medium text-[#697088]">{label}</span>
        <span className="font-semibold text-[#2a3049]">{text}</span>
      </div>
      <div className="mt-2.5 h-2 overflow-hidden rounded-full bg-[#eef0f5]">
        <div
          className={`h-full rounded-full transition-all duration-500 ${tone === "blue" ? "bg-[#4968e8]" : "bg-[#2ac7a9]"}`}
          style={{
            width: `${width}%`
          }}
        />
      </div>
    </div>
  );
}

function MiniMetric({
  label,
  value
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="rounded-[15px] bg-[#f8f9fc] px-3 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[#9ba1b3]">{label}</p>
      <p className="mt-1.5 text-lg font-semibold tracking-[-0.03em] text-[#2c324b]">{value}</p>
    </div>
  );
}

function ChartPanel({
  title,
  description,
  empty,
  children,
  legend
}: {
  title: string;
  description: string;
  empty: boolean;
  children: ReactNode;
  legend?: ReactNode;
}) {
  return (
    <div className="panel overflow-hidden p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="section-title">{title}</h2>
          <p className="muted mt-2">{description}</p>
        </div>
        {legend}
      </div>

      <div className="mt-5 h-72">
        {empty ? (
          <div className="grid h-full place-items-center rounded-[18px] border border-dashed border-[#dfe3ed] bg-[#fafbfc] px-6 text-center">
            <div>
              <div className="mx-auto grid size-11 place-items-center rounded-2xl bg-white text-[#b2b7c8] shadow-sm">
                <Wifi size={21} />
              </div>
              <p className="mt-3 text-sm font-semibold text-[#60677e]">Ainda não há dados para o gráfico</p>
              <p className="mt-1 text-xs text-[#969caf]">Os dados aparecerão após scans e análises persistidas.</p>
            </div>
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}

function RecentScansPanel({
  items
}: {
  items: DashboardOverviewResponse["recent_scans"];
}) {
  return (
    <div className="panel overflow-hidden">
      <div className="flex items-center justify-between border-b border-[#edf0f5] px-5 py-5 sm:px-6">
        <div>
          <h2 className="section-title">Scans recentes</h2>
          <p className="muted mt-1.5">Sessões mais recentes persistidas no dispositivo.</p>
        </div>
        <div className="grid size-10 place-items-center rounded-[14px] bg-[#eef2ff] text-[#4968e8]">
          <ScanSearch size={18} />
        </div>
      </div>

      {items.length === 0 ? (
        <ListEmpty text="Nenhum scan persistido." />
      ) : (
        <div className="divide-y divide-[#f0f2f6]">
          {items.map(scan => (
            <div
              key={scan.scan_id}
              className="grid grid-cols-[minmax(0,1fr)_72px_82px] items-center gap-4 px-5 py-4 transition-colors duration-150 hover:bg-[#fbfbfd] sm:px-6 max-[560px]:grid-cols-1 max-[560px]:gap-2 max-[560px]:px-4"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="size-1.5 rounded-full bg-[#2ac7a9]" />
                  <p className="truncate text-sm font-semibold text-[#343a53]">{formatDateTime(scan.observed_at_utc)}</p>
                </div>
                <p className="mt-1.5 truncate pl-3.5 font-mono text-[10px] text-[#9ba1b3]">{scan.scan_id}</p>
              </div>
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.07em] text-[#a0a5b6]">Redes</p>
                <p className="mt-1 text-sm font-semibold text-[#555d76]">{scan.total_networks}</p>
              </div>
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.07em] text-[#a0a5b6]">Anomalias</p>
                <p className="mt-1 text-sm font-semibold text-[#555d76]">{scan.anomaly_count}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RecentDetectionsPanel({
  items
}: {
  items: DashboardOverviewResponse["recent_detections"];
}) {
  return (
    <div className="panel overflow-hidden">
      <div className="flex items-center justify-between border-b border-[#edf0f5] px-5 py-5 sm:px-6">
        <div>
          <h2 className="section-title">Análises recentes</h2>
          <p className="muted mt-1.5">Últimos resultados auditáveis registrados no SQLite.</p>
        </div>
        <div className="grid size-10 place-items-center rounded-[14px] bg-[#eafaf6] text-[#1aa88d]">
          <ShieldCheck size={18} />
        </div>
      </div>

      {items.length === 0 ? (
        <ListEmpty text="Nenhuma análise persistida." />
      ) : (
        <div className="divide-y divide-[#f0f2f6]">
          {items.map(detection => (
            <div
              key={detection.detection_id}
              className="flex items-center justify-between gap-5 px-5 py-4 transition-colors duration-150 hover:bg-[#fbfbfd] sm:px-6"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-[#343a53]">Análise #{detection.detection_id}</p>
                  <SuspicionBadge level={detection.suspicion_level} />
                </div>
                <p className="mt-1.5 truncate text-xs text-[#9ba1b3]">{formatDateTime(detection.created_at_utc)}</p>
              </div>

              <div className="shrink-0 text-right">
                <p className="text-[10px] font-semibold uppercase tracking-[0.07em] text-[#a0a5b6]">Score</p>
                <p className="mt-1 text-sm font-semibold text-[#555d76]">
                  {detection.anomaly_score === null
                    ? "—"
                    : formatDecimal(detection.anomaly_score)}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ActivityCard({
  icon: Icon,
  title,
  value
}: {
  icon: typeof Clock3;
  title: string;
  value: string;
}) {
  return (
    <div className="rounded-[18px] border border-[#e8eaf1] bg-[#fbfbfd] p-4">
      <div className="flex items-center gap-2 text-[#778098]">
        <Icon size={15} />
        <p className="text-[10px] font-semibold uppercase tracking-[0.09em]">{title}</p>
      </div>
      <p className="mt-3 text-sm font-semibold leading-5 text-[#343a53]">{value}</p>
    </div>
  );
}

function DetailRow({
  label,
  value
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-[#f0f2f6] py-3 first:pt-0 last:border-b-0 last:pb-0">
      <dt className="text-sm text-[#858ca1]">{label}</dt>
      <dd className="max-w-[65%] break-all text-right text-sm font-semibold text-[#434961]">{value}</dd>
    </div>
  );
}

function ListEmpty({
  text
}: {
  text: string;
}) {
  return (
    <div className="px-6 py-10 text-center text-sm text-[#9298ab]">{text}</div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-5" aria-label="Carregando dashboard">
      <div className="h-[310px] animate-pulse rounded-[28px] bg-[#30376f]" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map(item => (
          <div
            key={item}
            className="panel h-36 animate-pulse p-5"
          >
            <div className="h-3 w-24 rounded bg-[#eef0f5]" />
            <div className="mt-5 h-8 w-16 rounded bg-[#eef0f5]" />
            <div className="mt-5 h-3 w-32 rounded bg-[#f1f2f6]" />
          </div>
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="panel h-80 animate-pulse" />
        <div className="panel h-80 animate-pulse" />
      </div>
    </div>
  );
}

function EmptyDashboard() {
  return (
    <div className="panel p-12 text-center">
      <div className="mx-auto grid size-14 place-items-center rounded-[20px] bg-[#eef0fb] text-[#7e86aa]">
        <CheckCircle2 size={27} />
      </div>
      <p className="mt-5 text-base font-semibold text-[#50566f]">Dashboard sem dados</p>
      <p className="mt-2 text-sm text-[#949aad]">Execute um scan para começar a registrar atividade.</p>
    </div>
  );
}
