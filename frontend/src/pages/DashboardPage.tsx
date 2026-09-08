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
  CheckCircle2,
  Clock3,
  Database,
  RadioTower,
  RefreshCw,
  ScanSearch,
  ShieldCheck,
  Wifi
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
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
  const [
    data,
    setData
  ] = useState<DashboardState | null>(
    null
  );

  const [
    loading,
    setLoading
  ] = useState(true);

  const [
    backgroundRefreshing,
    setBackgroundRefreshing
  ] = useState(false);

  const [
    error,
    setError
  ] = useState<string | null>(
    null
  );

const load = useCallback(
  async (
    options: {
      background?: boolean;
    } = {}
  ) => {
    const background =
      options.background
      === true;

    if (background) {
      setBackgroundRefreshing(
        true
      );
    } else {
      setLoading(
        true
      );
    }

    setError(
      null
    );

    try {
      const [
        overview,
        trends
      ] = await Promise.all([
        api.dashboard(),
        api.dashboardTrends()
      ]);

      setData({
        overview,
        trends
      });
    } catch {
      setError(
        "Não foi possível acessar os dados do backend local."
      );
      throw new Error(
        "dashboard_refresh_failed"
      );
    } finally {
      if (background) {
        setBackgroundRefreshing(
          false
        );
      } else {
        setLoading(
          false
        );
      }
    }
  },
  []
);

  useEffect(
    () => {
      void load()
        .catch(
          () => undefined
        );
    },
    [load]
  );

  const autoRefresh =
    useAutoScanRefresh(
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
      data?.trends.points.map(
        point => ({
          ...point,
          label: formatShortDateTime(
            point.observed_at_utc
          )
        })
      ) ?? [],
    [data]
  );

  return (
    <div className="space-y-7">
      <PageHeader
        title="Visão geral"
        description="Resumo operacional do detector, atividade recente e evolução das análises registradas no dispositivo."
        actions={
          <div className="flex flex-wrap items-center justify-end gap-2">
            <AutoScanRefreshNotice
              state={autoRefresh}
            />
            <button
              className="btn-secondary"
              type="button"
              disabled={
                loading
                || backgroundRefreshing
              }
              onClick={() =>
                void load()
                  .catch(
                    () => undefined
                  )
              }
            >
              <RefreshCw
                className={
                  (
                    loading
                    || backgroundRefreshing
                  )
                    ? "animate-spin"
                    : undefined
                }
                size={16}
              />
              Atualizar
            </button>
          </div>
        }
      />

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <AlertTriangle
            className="mt-0.5 shrink-0"
            size={17}
          />
          <div>
            <p className="font-medium">
              Backend indisponível
            </p>
            <p className="mt-1 text-amber-700">
              {error}
            </p>
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
  trendData: Array<
    DashboardTrendsResponse["points"][number]
    & { label: string }
  >;
}) {
  const {
    overview
  } = data;

  const hasHistory =
    overview.metrics.scan_count > 0;

  return (
    <>
      <section className="grid gap-4 xl:grid-cols-4 md:grid-cols-2">
        <StatCard
          label="Scans realizados"
          value={overview.metrics.scan_count}
          helper={
            overview.latest_scan_at_utc
              ? `Último: ${formatDateTime(overview.latest_scan_at_utc)}`
              : "Nenhum scan persistido"
          }
        />

        <StatCard
          label="Redes distintas"
          value={overview.metrics.unique_network_count}
          helper={`${overview.metrics.observation_count} observações persistidas`}
        />

        <StatCard
          label="Anomalias"
          value={overview.metrics.anomaly_count}
          helper={`${formatPercent(overview.metrics.anomaly_rate_among_decided)} das decisões válidas`}
        />

        <StatCard
          label="Histórico insuficiente"
          value={overview.metrics.insufficient_history_count}
          helper="Sem decisão binária de anomalia"
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="panel p-5">
          <div className="flex items-start justify-between gap-5">
            <div>
              <h2 className="section-title">
                Estado do sistema
              </h2>
              <p className="muted mt-1">
                Serviços necessários para a análise local.
              </p>
            </div>

            <span className="text-xs text-slate-400">
              Backend {overview.system.backend_version}
            </span>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-3">
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

        <div className="panel p-5">
          <h2 className="section-title">
            Cobertura da análise
          </h2>
          <p className="muted mt-1">
            Relação entre observações persistidas e análises auditáveis.
          </p>

          <div className="mt-5 space-y-5">
            <ProgressMetric
              label="Cobertura"
              value={overview.metrics.analysis_coverage_rate}
              text={formatPercent(overview.metrics.analysis_coverage_rate)}
            />
            <ProgressMetric
              label="Anomalias entre decisões"
              value={overview.metrics.anomaly_rate_among_decided}
              text={formatPercent(overview.metrics.anomaly_rate_among_decided)}
            />
          </div>

          <div className="mt-5 grid grid-cols-3 gap-3 border-t border-slate-100 pt-5">
            <MiniMetric
              label="Features"
              value={overview.metrics.feature_count}
            />
            <MiniMetric
              label="Detecções"
              value={overview.metrics.detection_count}
            />
            <MiniMetric
              label="Modelos"
              value={overview.metrics.model_version_count}
            />
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.35fr_0.65fr]">
        <ChartPanel
          title="Evolução dos scans"
          description="Redes observadas e decisões registradas nos scans mais recentes."
          empty={!hasHistory || trendData.length === 0}
        >
          <ResponsiveContainer
            width="100%"
            height="100%"
          >
            <AreaChart
              data={trendData}
              margin={{
                top: 12,
                right: 8,
                left: -18,
                bottom: 0
              }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
                stroke="#e2e8f0"
              />
              <XAxis
                dataKey="label"
                tick={{
                  fill: "#64748b",
                  fontSize: 11
                }}
                tickLine={false}
                axisLine={false}
                minTickGap={24}
              />
              <YAxis
                allowDecimals={false}
                tick={{
                  fill: "#64748b",
                  fontSize: 11
                }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: 12,
                  borderColor: "#e2e8f0",
                  fontSize: 12
                }}
              />
              <Area
                type="monotone"
                dataKey="network_count"
                name="Redes"
                stroke="#0f172a"
                fill="#e2e8f0"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="detection_count"
                name="Análises"
                stroke="#2563eb"
                fill="#dbeafe"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel
          title="Distribuição de suspeita"
          description="Contagem histórica por nível retornado pelo runtime."
          empty={overview.metrics.detection_count === 0}
        >
          <ResponsiveContainer
            width="100%"
            height="100%"
          >
            <BarChart
              data={[
                {
                  name: "Baixa",
                  value: overview.suspicion_distribution.low
                },
                {
                  name: "Média",
                  value: overview.suspicion_distribution.medium
                },
                {
                  name: "Alta",
                  value: overview.suspicion_distribution.high
                },
                {
                  name: "Indisp.",
                  value: overview.suspicion_distribution.unavailable
                }
              ]}
              margin={{
                top: 12,
                right: 8,
                left: -18,
                bottom: 0
              }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
                stroke="#e2e8f0"
              />
              <XAxis
                dataKey="name"
                tick={{
                  fill: "#64748b",
                  fontSize: 11
                }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{
                  fill: "#64748b",
                  fontSize: 11
                }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                cursor={{
                  fill: "#f8fafc"
                }}
                contentStyle={{
                  borderRadius: 12,
                  borderColor: "#e2e8f0",
                  fontSize: 12
                }}
              />
              <Bar
                dataKey="value"
                name="Ocorrências"
                fill="#334155"
                radius={[6, 6, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <RecentScansPanel
          items={overview.recent_scans}
        />
        <RecentDetectionsPanel
          items={overview.recent_detections}
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.75fr_1.25fr]">
        <div className="panel p-5">
          <div className="flex items-center gap-2">
            <Activity
              size={18}
              className="text-slate-500"
            />
            <h2 className="section-title">
              Modelo ativo
            </h2>
          </div>

          {overview.active_model ? (
            <dl className="mt-5 space-y-4">
              <DetailRow
                label="Versão"
                value={overview.active_model.version_name}
              />
              <DetailRow
                label="Algoritmo"
                value={overview.active_model.algorithm}
              />
              <DetailRow
                label="Features"
                value={overview.active_model.feature_set_name}
              />
              <DetailRow
                label="Threshold"
                value={
                  overview.active_model.threshold === null
                    ? "—"
                    : formatDecimal(overview.active_model.threshold)
                }
              />
              <DetailRow
                label="Detecções"
                value={String(overview.active_model.detection_count)}
              />
            </dl>
          ) : (
            <div className="mt-5 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-500">
              Nenhuma versão real do modelo foi registrada no banco. O scanner pode continuar operando, mas a análise permanece indisponível.
            </div>
          )}
        </div>

        <div className="panel p-5">
          <div className="flex items-center gap-2">
            <Clock3
              size={18}
              className="text-slate-500"
            />
            <h2 className="section-title">
              Última atividade
            </h2>
          </div>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
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

          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-sm font-medium text-slate-700">
              Interpretação do protótipo
            </p>
            <p className="mt-1 text-sm leading-6 text-slate-500">
              “Alta suspeita” representa uma observação acima do threshold de anomalia. O sistema não confirma, sozinho, a existência de um ataque Evil Twin.
            </p>
          </div>
        </div>
      </section>
    </>
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
    <div className="rounded-xl border border-slate-200 p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="grid size-9 place-items-center rounded-lg bg-slate-100 text-slate-600">
          <Icon size={17} />
        </div>
        <StatusBadge value={value} />
      </div>
      <p className="mt-3 text-sm font-semibold text-slate-900">
        {label}
      </p>
      <p className="mt-1 truncate text-xs text-slate-400">
        {helper}
      </p>
    </div>
  );
}

function ProgressMetric({
  label,
  value,
  text
}: {
  label: string;
  value: number;
  text: string;
}) {
  const width = Math.max(
    0,
    Math.min(
      100,
      value * 100
    )
  );

  return (
    <div>
      <div className="flex items-center justify-between gap-4 text-sm">
        <span className="text-slate-500">
          {label}
        </span>
        <span className="font-semibold text-slate-900">
          {text}
        </span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-slate-800 transition-all"
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
    <div>
      <p className="text-xs text-slate-400">
        {label}
      </p>
      <p className="mt-1 text-lg font-semibold text-slate-900">
        {value}
      </p>
    </div>
  );
}

function ChartPanel({
  title,
  description,
  empty,
  children
}: {
  title: string;
  description: string;
  empty: boolean;
  children: ReactNode;
}) {
  return (
    <div className="panel p-5">
      <h2 className="section-title">
        {title}
      </h2>
      <p className="muted mt-1">
        {description}
      </p>

      <div className="mt-5 h-72">
        {empty ? (
          <div className="grid h-full place-items-center rounded-xl border border-dashed border-slate-200 bg-slate-50 px-6 text-center">
            <div>
              <Wifi
                className="mx-auto text-slate-300"
                size={28}
              />
              <p className="mt-3 text-sm font-medium text-slate-600">
                Ainda não há dados para o gráfico
              </p>
              <p className="mt-1 text-xs text-slate-400">
                Os dados aparecerão após scans e análises persistidas.
              </p>
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
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <div>
          <h2 className="section-title">
            Scans recentes
          </h2>
          <p className="muted mt-1">
            Sessões mais recentes persistidas no dispositivo.
          </p>
        </div>
        <ScanSearch
          className="text-slate-400"
          size={20}
        />
      </div>

      {items.length === 0 ? (
        <ListEmpty text="Nenhum scan persistido." />
      ) : (
        <div className="divide-y divide-slate-100">
          {items.map(
            scan => (
              <div
                key={scan.scan_id}
                className="grid grid-cols-[minmax(0,1fr)_80px_90px] items-center gap-4 px-5 py-4"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-800">
                    {formatDateTime(scan.observed_at_utc)}
                  </p>
                  <p className="mt-1 truncate font-mono text-[11px] text-slate-400">
                    {scan.scan_id}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-400">
                    Redes
                  </p>
                  <p className="mt-1 text-sm font-semibold text-slate-700">
                    {scan.total_networks}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-400">
                    Anomalias
                  </p>
                  <p className="mt-1 text-sm font-semibold text-slate-700">
                    {scan.anomaly_count}
                  </p>
                </div>
              </div>
            )
          )}
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
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <div>
          <h2 className="section-title">
            Análises recentes
          </h2>
          <p className="muted mt-1">
            Últimos resultados auditáveis registrados no SQLite.
          </p>
        </div>
        <ShieldCheck
          className="text-slate-400"
          size={20}
        />
      </div>

      {items.length === 0 ? (
        <ListEmpty text="Nenhuma análise persistida." />
      ) : (
        <div className="divide-y divide-slate-100">
          {items.map(
            detection => (
              <div
                key={detection.detection_id}
                className="flex items-center justify-between gap-5 px-5 py-4"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-slate-800">
                      Análise #{detection.detection_id}
                    </p>
                    <SuspicionBadge
                      level={detection.suspicion_level}
                    />
                  </div>
                  <p className="mt-1 truncate text-xs text-slate-400">
                    {formatDateTime(detection.created_at_utc)}
                  </p>
                </div>

                <div className="text-right">
                  <p className="text-xs text-slate-400">
                    Score
                  </p>
                  <p className="mt-1 text-sm font-semibold text-slate-700">
                    {detection.anomaly_score === null
                      ? "—"
                      : formatDecimal(detection.anomaly_score)}
                  </p>
                </div>
              </div>
            )
          )}
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
    <div className="rounded-xl border border-slate-200 p-4">
      <div className="flex items-center gap-2 text-slate-500">
        <Icon size={16} />
        <p className="text-xs font-medium uppercase tracking-wide">
          {title}
        </p>
      </div>
      <p className="mt-3 text-sm font-semibold text-slate-900">
        {value}
      </p>
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
    <div className="flex items-start justify-between gap-4">
      <dt className="text-sm text-slate-500">
        {label}
      </dt>
      <dd className="max-w-[65%] break-all text-right text-sm font-medium text-slate-800">
        {value}
      </dd>
    </div>
  );
}

function ListEmpty({
  text
}: {
  text: string;
}) {
  return (
    <div className="p-8 text-center text-sm text-slate-500">
      {text}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4" aria-label="Carregando dashboard">
      <div className="grid gap-4 xl:grid-cols-4 md:grid-cols-2">
        {[0, 1, 2, 3].map(
          item => (
            <div
              key={item}
              className="panel h-32 animate-pulse bg-white p-5"
            >
              <div className="h-4 w-24 rounded bg-slate-100" />
              <div className="mt-4 h-8 w-16 rounded bg-slate-100" />
            </div>
          )
        )}
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="panel h-80 animate-pulse bg-white" />
        <div className="panel h-80 animate-pulse bg-white" />
      </div>
    </div>
  );
}

function EmptyDashboard() {
  return (
    <div className="panel p-10 text-center">
      <CheckCircle2
        className="mx-auto text-slate-300"
        size={32}
      />
      <p className="mt-4 text-sm font-medium text-slate-700">
        Dashboard sem dados
      </p>
      <p className="mt-1 text-sm text-slate-400">
        Execute um scan para começar a registrar atividade.
      </p>
    </div>
  );
}
