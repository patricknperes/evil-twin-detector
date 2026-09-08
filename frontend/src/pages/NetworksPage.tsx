import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from "react";
import {
  Activity,
  ArrowDownUp,
  ChevronDown,
  Clock3,
  Fingerprint,
  Filter,
  Gauge,
  RadioTower,
  RefreshCw,
  Router,
  Search,
  ShieldAlert,
  ShieldCheck,
  Signal,
  SlidersHorizontal,
  Wifi
} from "lucide-react";
import {
  AnimatePresence,
  motion,
  useReducedMotion
} from "motion/react";

import {
  AutoScanRefreshNotice
} from "../components/AutoScanRefreshNotice";
import {
  PageHeader
} from "../components/PageHeader";
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
  animationTokens
} from "../lib/animation";
import {
  formatDateTime
} from "../lib/format";
import {
  countSuspicion,
  formatFrequency,
  formatScore,
  matchesNetworkQuery,
  sortNetworks,
  type NetworkSort
} from "../lib/networkUi";
import type {
  NetworkObservation,
  SuspicionLevel
} from "../types/api";

type FilterValue =
  | "all"
  | SuspicionLevel;

const filterLabels: Record<
  FilterValue,
  string
> = {
  all: "Todas",
  low: "Baixa",
  medium: "Média",
  high: "Alta",
  unavailable: "Indisponível"
};

const sortLabels: Record<
  NetworkSort,
  string
> = {
  signal_desc: "Sinal: mais forte",
  signal_asc: "Sinal: mais fraco",
  ssid_asc: "SSID: A–Z",
  suspicion_desc: "Maior suspeita"
};

const summaryConfig: Array<{
  key: "total" | SuspicionLevel;
  label: string;
  helper: string;
  icon: typeof Wifi;
  accent: string;
  iconClass: string;
}> = [
  {
    key: "total",
    label: "Redes",
    helper: "observadas no último scan",
    icon: Wifi,
    accent: "bg-[#4968e8]",
    iconClass: "bg-[#eef2ff] text-[#4968e8]"
  },
  {
    key: "low",
    label: "Baixa",
    helper: "dentro do esperado",
    icon: ShieldCheck,
    accent: "bg-emerald-500",
    iconClass: "bg-emerald-50 text-emerald-600"
  },
  {
    key: "medium",
    label: "Média",
    helper: "merecem revisão",
    icon: Activity,
    accent: "bg-amber-400",
    iconClass: "bg-amber-50 text-amber-600"
  },
  {
    key: "high",
    label: "Alta",
    helper: "acima do threshold",
    icon: ShieldAlert,
    accent: "bg-rose-500",
    iconClass: "bg-rose-50 text-rose-600"
  },
  {
    key: "unavailable",
    label: "Indisponível",
    helper: "contexto insuficiente",
    icon: RadioTower,
    accent: "bg-slate-400",
    iconClass: "bg-slate-100 text-slate-500"
  }
];

export function NetworksPage() {
  const shouldReduceMotion = useReducedMotion();

  const [
    networks,
    setNetworks
  ] = useState<NetworkObservation[]>(
    []
  );

  const [
    hasScan,
    setHasScan
  ] = useState(false);

  const [
    scanId,
    setScanId
  ] = useState<string | null>(
    null
  );

  const [
    observedAtUtc,
    setObservedAtUtc
  ] = useState<string | null>(
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

  const [
    query,
    setQuery
  ] = useState("");

  const [
    filter,
    setFilter
  ] = useState<FilterValue>(
    "all"
  );

  const [
    sort,
    setSort
  ] = useState<NetworkSort>(
    "signal_desc"
  );

  const [
    expanded,
    setExpanded
  ] = useState<Set<string>>(
    new Set()
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
        const payload =
          await api.latestNetworks();

        setHasScan(
          payload.has_scan
        );
        setScanId(
          payload.scan_id
        );
        setObservedAtUtc(
          payload.observed_at_utc
        );
        setNetworks(
          payload.networks
        );

        const currentIds =
          new Set(
            payload.networks.map(
              network =>
                network.network_id
            )
          );

        setExpanded(
          current =>
            new Set(
              [
                ...current
              ].filter(
                id =>
                  currentIds.has(id)
              )
            )
        );
      } catch {
        setError(
          "Não foi possível acessar a última varredura no backend local."
        );
        throw new Error(
          "networks_refresh_failed"
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

  const counts = useMemo(
    () =>
      countSuspicion(
        networks
      ),
    [
      networks
    ]
  );

  const visibleNetworks = useMemo(
    () => {
      const filtered =
        networks.filter(
          network =>
            (
              filter === "all"
              || network.analysis
                .suspicion_level
                === filter
            )
            && matchesNetworkQuery(
              network,
              query
            )
        );

      return sortNetworks(
        filtered,
        sort
      );
    },
    [
      networks,
      query,
      filter,
      sort
    ]
  );

  const attentionCount =
    counts.medium
    + counts.high;

  function toggle(
    id: string
  ) {
    setExpanded(
      current => {
        const next = new Set(
          current
        );

        if (
          next.has(
            id
          )
        ) {
          next.delete(
            id
          );
        } else {
          next.add(
            id
          );
        }

        return next;
      }
    );
  }

  return (
    <motion.div
      className="space-y-6"
      initial={
        shouldReduceMotion
          ? false
          : { opacity: 0 }
      }
      animate={{ opacity: 1 }}
      transition={{
        duration: animationTokens.duration.base
      }}
    >
      <PageHeader
        title="Redes observadas"
        description="Consulta da última varredura mantida no runtime local. SSID e BSSID em claro aparecem somente nesta sessão ativa; o histórico persistido continua anonimizado."
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
                size={16}
                className={
                  (
                    loading
                    || backgroundRefreshing
                  )
                    ? "animate-spin"
                    : ""
                }
              />
              Atualizar
            </button>
          </div>
        }
      />

      {error && (
        <motion.div
          initial={
            shouldReduceMotion
              ? false
              : {
                  opacity: 0,
                  y: -8
                }
          }
          animate={{
            opacity: 1,
            y: 0
          }}
          className="flex items-start gap-3 rounded-[1.25rem] border border-rose-200 bg-rose-50 px-4 py-3.5 text-sm text-rose-700 shadow-[0_8px_24px_rgba(225,29,72,0.06)]"
        >
          <ShieldAlert
            size={17}
            className="mt-0.5 shrink-0"
          />
          <span>{error}</span>
        </motion.div>
      )}

      {loading && !hasScan ? (
        <section className="panel overflow-hidden p-8">
          <div className="flex min-h-36 items-center justify-center">
            <div className="flex flex-col items-center text-center">
              <div className="grid size-12 place-items-center rounded-2xl bg-[#eef2ff] text-[#4968e8]">
                <RefreshCw
                  size={20}
                  className="animate-spin"
                />
              </div>
              <p className="mt-4 text-sm font-semibold text-[#30354f]">
                Consultando a última varredura…
              </p>
              <p className="mt-1 text-xs text-slate-400">
                Sincronizando observações do runtime local.
              </p>
            </div>
          </div>
        </section>
      ) : !hasScan ? (
        <section className="panel relative overflow-hidden p-10 text-center">
          <div className="pointer-events-none absolute -right-12 -top-12 size-44 rounded-full bg-[#edf1ff]" />
          <div className="pointer-events-none absolute -bottom-16 left-8 size-40 rounded-full bg-emerald-50/70" />

          <div className="relative mx-auto grid size-14 place-items-center rounded-[1.2rem] bg-[#31396f] text-white shadow-[0_14px_34px_rgba(49,57,111,0.22)]">
            <Wifi size={24} />
          </div>

          <h2 className="relative mt-5 text-lg font-semibold tracking-[-0.02em] text-[#20243b]">
            Nenhuma varredura disponível
          </h2>

          <p className="relative mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">
            Execute um scan na tela “Escanear redes”.
            Esta página mostra somente a última varredura
            ainda disponível no runtime local.
          </p>
        </section>
      ) : (
        <>
          <NetworkOverviewHero
            total={networks.length}
            counts={counts}
            attentionCount={attentionCount}
            observedAtUtc={observedAtUtc}
            scanId={scanId}
          />

          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            {summaryConfig.map(
              (item, index) => {
                const {
                  key,
                  ...cardProps
                } = item;

                const value =
                  key === "total"
                    ? networks.length
                    : counts[key];

                return (
                  <SummaryCard
                    key={key}
                    {...cardProps}
                    value={value}
                    index={index}
                    reduceMotion={
                      shouldReduceMotion === true
                    }
                  />
                );
              }
            )}
          </section>

          <section className="panel overflow-hidden">
            <div className="border-b border-[#eceef5] px-5 py-4 sm:px-6">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-xl bg-[#f0f3ff] text-[#4968e8]">
                    <SlidersHorizontal size={18} />
                  </div>
                  <div>
                    <h2 className="text-sm font-semibold text-[#252a43]">
                      Explorar observações
                    </h2>
                    <p className="mt-0.5 text-xs text-slate-400">
                      Refine a leitura sem alterar os dados da varredura.
                    </p>
                  </div>
                </div>

                <p className="text-xs font-medium text-slate-400">
                  Exibindo <strong className="font-semibold text-[#3d4565]">{visibleNetworks.length}</strong> de {networks.length} redes
                </p>
              </div>
            </div>

            <div className="grid gap-3 p-4 sm:p-5 lg:grid-cols-[minmax(260px,1fr)_190px_220px]">
              <label className="relative block">
                <span className="sr-only">
                  Buscar redes
                </span>
                <Search
                  size={16}
                  className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400"
                />
                <input
                  value={query}
                  onChange={event =>
                    setQuery(
                      event.target.value
                    )
                  }
                  placeholder="Buscar por SSID, BSSID, segurança ou suspeita"
                  className="w-full rounded-xl border border-[#e3e6f0] bg-[#fafbfe] py-2.5 pl-10 pr-3 text-sm text-[#30364f] outline-none transition placeholder:text-slate-400 hover:border-[#d7dbea] focus:border-[#8fa2ee] focus:bg-white focus:ring-4 focus:ring-[#4968e8]/8"
                />
              </label>

              <label className="relative block">
                <span className="sr-only">
                  Filtrar por análise
                </span>
                <Filter
                  size={15}
                  className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400"
                />
                <select
                  value={filter}
                  onChange={event =>
                    setFilter(
                      event.target.value as FilterValue
                    )
                  }
                  className="w-full appearance-none rounded-xl border border-[#e3e6f0] bg-[#fafbfe] py-2.5 pl-10 pr-9 text-sm font-medium text-[#4e5570] outline-none transition hover:border-[#d7dbea] focus:border-[#8fa2ee] focus:bg-white focus:ring-4 focus:ring-[#4968e8]/8"
                >
                  {Object.entries(
                    filterLabels
                  ).map(
                    ([
                      value,
                      label
                    ]) => (
                      <option
                        key={value}
                        value={value}
                      >
                        {label}
                      </option>
                    )
                  )}
                </select>
                <ChevronDown
                  size={14}
                  className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400"
                />
              </label>

              <label className="relative block">
                <span className="sr-only">
                  Ordenar redes
                </span>
                <ArrowDownUp
                  size={15}
                  className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400"
                />
                <select
                  value={sort}
                  onChange={event =>
                    setSort(
                      event.target.value as NetworkSort
                    )
                  }
                  className="w-full appearance-none rounded-xl border border-[#e3e6f0] bg-[#fafbfe] py-2.5 pl-10 pr-9 text-sm font-medium text-[#4e5570] outline-none transition hover:border-[#d7dbea] focus:border-[#8fa2ee] focus:bg-white focus:ring-4 focus:ring-[#4968e8]/8"
                >
                  {Object.entries(
                    sortLabels
                  ).map(
                    ([
                      value,
                      label
                    ]) => (
                      <option
                        key={value}
                        value={value}
                      >
                        {label}
                      </option>
                    )
                  )}
                </select>
                <ChevronDown
                  size={14}
                  className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400"
                />
              </label>
            </div>
          </section>

          <section className="panel overflow-hidden">
            <div className="flex flex-col gap-3 border-b border-[#eceef5] px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#8990a7]">
                  Inventário da sessão
                </p>
                <h2 className="mt-1 text-base font-semibold tracking-[-0.02em] text-[#242941]">
                  Redes detectadas
                </h2>
              </div>

              <div className="flex items-center gap-2 text-xs text-slate-400">
                <Signal size={14} />
                Sinal mais forte aparece primeiro por padrão
              </div>
            </div>

            {visibleNetworks.length === 0 ? (
              <div className="p-12 text-center">
                <div className="mx-auto grid size-12 place-items-center rounded-2xl bg-slate-100 text-slate-400">
                  <Search size={20} />
                </div>
                <p className="mt-4 text-sm font-semibold text-slate-700">
                  Nenhuma rede corresponde aos filtros atuais.
                </p>
                <p className="mx-auto mt-1 max-w-md text-xs leading-5 text-slate-400">
                  Tente remover parte da busca ou selecionar outro nível de suspeita.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-[#eef0f5]">
                {visibleNetworks.map(
                  (network, index) => {
                    const isExpanded =
                      expanded.has(
                        network.network_id
                      );

                    return (
                      <NetworkRow
                        key={network.network_id}
                        network={network}
                        expanded={isExpanded}
                        index={index}
                        reduceMotion={
                          shouldReduceMotion === true
                        }
                        onToggle={() =>
                          toggle(
                            network.network_id
                          )
                        }
                      />
                    );
                  }
                )}
              </div>
            )}
          </section>

          <div className="flex items-start gap-3 rounded-[1.25rem] border border-[#e2e6f1] bg-[#f6f7fb] p-4 text-xs leading-5 text-slate-500">
            <div className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-white text-[#59627f] shadow-sm">
              <ShieldCheck size={15} />
            </div>
            <p>
              <strong className="font-semibold text-[#424a67]">
                Interpretação:
              </strong>{" "}
              “Baixa suspeita” representa uma observação dentro do comportamento
              esperado pelo modelo. “Alta suspeita” indica uma observação acima
              do threshold de anomalia e não confirma um ataque Evil Twin.
              “Indisponível” indica contexto insuficiente ou artefatos ainda
              não prontos.
            </p>
          </div>
        </>
      )}
    </motion.div>
  );
}

function NetworkOverviewHero({
  total,
  counts,
  attentionCount,
  observedAtUtc,
  scanId
}: {
  total: number;
  counts: Record<SuspicionLevel, number>;
  attentionCount: number;
  observedAtUtc: string | null;
  scanId: string | null;
}) {
  const highPresent = counts.high > 0;
  const mediumPresent = counts.medium > 0;

  const posture = highPresent
    ? {
        eyebrow: "Atenção recomendada",
        title: `${counts.high} ${counts.high === 1 ? "rede exige" : "redes exigem"} revisão prioritária`,
        description: "Há observações classificadas com alta suspeita na varredura mais recente.",
        dot: "bg-rose-400",
        pill: "border-rose-300/20 bg-rose-400/10 text-rose-100"
      }
    : mediumPresent
      ? {
          eyebrow: "Revisão sugerida",
          title: `${attentionCount} ${attentionCount === 1 ? "observação merece" : "observações merecem"} atenção`,
          description: "Nenhuma rede está em alta suspeita, mas há sinais intermediários para revisar.",
          dot: "bg-amber-300",
          pill: "border-amber-200/20 bg-amber-300/10 text-amber-50"
        }
      : {
          eyebrow: "Ambiente estável",
          title: "Nenhuma rede em atenção elevada",
          description: "A última leitura não contém observações classificadas com média ou alta suspeita.",
          dot: "bg-emerald-300",
          pill: "border-emerald-200/20 bg-emerald-300/10 text-emerald-50"
        };

  const distribution = [
    {
      key: "low",
      count: counts.low,
      className: "bg-emerald-400"
    },
    {
      key: "medium",
      count: counts.medium,
      className: "bg-amber-300"
    },
    {
      key: "high",
      count: counts.high,
      className: "bg-rose-400"
    },
    {
      key: "unavailable",
      count: counts.unavailable,
      className: "bg-white/25"
    }
  ];

  return (
    <section className="relative overflow-hidden rounded-[1.75rem] bg-[#30376f] px-5 py-6 text-white shadow-[0_22px_60px_rgba(41,47,103,0.18)] sm:px-7 sm:py-7">
      <div className="pointer-events-none absolute -right-20 -top-28 size-80 rounded-full border border-white/[0.06]" />
      <div className="pointer-events-none absolute -right-5 -top-10 size-56 rounded-full border border-white/[0.07]" />
      <div className="pointer-events-none absolute right-20 top-12 size-20 rounded-full bg-[#4968e8]/30 blur-2xl" />
      <div className="pointer-events-none absolute -bottom-20 left-[42%] size-48 rounded-full bg-[#29c7aa]/12 blur-3xl" />

      <div className="relative grid gap-7 xl:grid-cols-[minmax(0,1.4fr)_minmax(340px,0.8fr)] xl:items-end">
        <div>
          <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] ${posture.pill}`}>
            <span className={`size-1.5 rounded-full ${posture.dot}`} />
            {posture.eyebrow}
          </div>

          <h2 className="mt-5 max-w-2xl text-[clamp(1.65rem,2.5vw,2.4rem)] font-semibold leading-[1.08] tracking-[-0.04em]">
            {posture.title}
          </h2>

          <p className="mt-3 max-w-2xl text-sm leading-6 text-white/60">
            {posture.description}
          </p>

          <div className="mt-6 flex flex-wrap gap-x-6 gap-y-3 text-xs text-white/55">
            <div className="flex items-center gap-2">
              <Clock3 size={14} className="text-[#8fa2ff]" />
              <span>
                {observedAtUtc
                  ? formatDateTime(
                      observedAtUtc
                    )
                  : "Horário indisponível"}
              </span>
            </div>

            <div className="flex min-w-0 items-center gap-2">
              <Fingerprint size={14} className="shrink-0 text-[#52d8bd]" />
              <span className="max-w-[420px] truncate font-mono text-[11px]" title={scanId ?? undefined}>
                {scanId ?? "scan_id indisponível"}
              </span>
            </div>
          </div>
        </div>

        <div className="rounded-[1.35rem] border border-white/10 bg-white/[0.065] p-4 backdrop-blur-sm sm:p-5">
          <div className="flex items-end justify-between gap-5">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-white/45">
                Última leitura
              </p>
              <div className="mt-2 flex items-end gap-2">
                <span className="text-4xl font-semibold tracking-[-0.05em]">
                  {total}
                </span>
                <span className="pb-1 text-xs text-white/45">
                  redes
                </span>
              </div>
            </div>

            <div className="grid size-12 place-items-center rounded-2xl bg-white/[0.09] text-[#aebaff]">
              <Router size={21} />
            </div>
          </div>

          <div className="mt-5 flex h-2 overflow-hidden rounded-full bg-white/10" aria-label="Distribuição dos níveis de suspeita">
            {distribution.map(item => {
              const width = total > 0
                ? `${Math.max((item.count / total) * 100, item.count > 0 ? 1.5 : 0)}%`
                : "0%";

              return (
                <div
                  key={item.key}
                  className={item.className}
                  style={{ width }}
                />
              );
            })}
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
            <HeroLegend label="Baixa" value={counts.low} dot="bg-emerald-400" />
            <HeroLegend label="Média" value={counts.medium} dot="bg-amber-300" />
            <HeroLegend label="Alta" value={counts.high} dot="bg-rose-400" />
            <HeroLegend label="Sem análise" value={counts.unavailable} dot="bg-white/35" />
          </div>
        </div>
      </div>
    </section>
  );
}

function HeroLegend({
  label,
  value,
  dot
}: {
  label: string;
  value: number;
  dot: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3 text-white/55">
      <span className="flex items-center gap-2">
        <span className={`size-1.5 rounded-full ${dot}`} />
        {label}
      </span>
      <strong className="font-semibold text-white/85">
        {value}
      </strong>
    </div>
  );
}

function SummaryCard({
  label,
  helper,
  value,
  icon: Icon,
  accent,
  iconClass,
  index,
  reduceMotion
}: {
  label: string;
  helper: string;
  value: number;
  icon: typeof Wifi;
  accent: string;
  iconClass: string;
  index: number;
  reduceMotion: boolean;
}) {
  return (
    <motion.div
      className="panel relative overflow-hidden px-4 py-4 sm:px-5"
      initial={
        reduceMotion
          ? false
          : {
              opacity: 0,
              y: 10
            }
      }
      animate={{
        opacity: 1,
        y: 0
      }}
      transition={{
        duration: 0.28,
        delay: reduceMotion
          ? 0
          : index * 0.035
      }}
    >
      <span className={`absolute inset-x-0 top-0 h-[2px] ${accent}`} />

      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#9298ac]">
            {label}
          </p>
          <p className="mt-2 text-[1.7rem] font-semibold leading-none tracking-[-0.04em] text-[#22273f]">
            {value}
          </p>
        </div>

        <div className={`grid size-9 shrink-0 place-items-center rounded-xl ${iconClass}`}>
          <Icon size={16} />
        </div>
      </div>

      <p className="mt-3 truncate text-[11px] text-slate-400" title={helper}>
        {helper}
      </p>
    </motion.div>
  );
}

function NetworkRow({
  network,
  expanded,
  index,
  reduceMotion,
  onToggle
}: {
  network: NetworkObservation;
  expanded: boolean;
  index: number;
  reduceMotion: boolean;
  onToggle: () => void;
}) {
  const level =
    network.analysis.suspicion_level;

  const accentClass: Record<SuspicionLevel, string> = {
    low: "bg-emerald-400",
    medium: "bg-amber-400",
    high: "bg-rose-500",
    unavailable: "bg-slate-300"
  };

  return (
    <motion.article
      initial={
        reduceMotion
          ? false
          : {
              opacity: 0,
              y: 8
            }
      }
      animate={{
        opacity: 1,
        y: 0
      }}
      transition={{
        duration: 0.24,
        delay: reduceMotion
          ? 0
          : Math.min(index, 8) * 0.025
      }}
      className="relative bg-white"
    >
      <span className={`absolute inset-y-0 left-0 w-[3px] opacity-0 transition-opacity ${accentClass[level]} ${expanded ? "opacity-100" : "group-hover:opacity-100"}`} />

      <button
        type="button"
        onClick={onToggle}
        aria-expanded={expanded}
        className="group relative grid w-full gap-4 px-5 py-4 text-left transition-colors hover:bg-[#fafbfe] sm:px-6 lg:grid-cols-[minmax(230px,1.35fr)_130px_95px_minmax(145px,0.8fr)_170px_34px] lg:items-center"
      >
        <div className="flex min-w-0 items-center gap-3">
          <div className="relative grid size-10 shrink-0 place-items-center rounded-xl border border-[#e5e8f2] bg-[#f7f8fc] text-[#56607f] transition group-hover:border-[#dce1f0] group-hover:bg-white">
            <Wifi size={17} />
            <span className={`absolute -right-0.5 -top-0.5 size-2 rounded-full ring-2 ring-white ${accentClass[level]}`} />
          </div>

          <div className="min-w-0">
            <p className="truncate text-sm font-semibold tracking-[-0.01em] text-[#262b43]">
              {network.ssid
                || "SSID não transmitido"}
            </p>

            <p className="mt-1 truncate font-mono text-[10px] text-[#9aa0b4]">
              {network.bssid}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:contents">
          <SignalValue
            rssi={network.rssi_dbm}
          />

          <Value
            label="Canal"
            value={
              network.ds_parameter_channel
                ?.toString()
              ?? "—"
            }
          />

          <Value
            label="Segurança"
            value={network.security_type}
          />

          <div className="min-w-0">
            <p className="mb-1.5 text-[10px] font-medium uppercase tracking-[0.08em] text-[#a0a5b7]">
              Análise
            </p>
            <SuspicionBadge
              level={level}
            />
          </div>
        </div>

        <motion.span
          animate={{
            rotate: expanded
              ? 180
              : 0
          }}
          transition={{
            duration: reduceMotion
              ? 0
              : 0.2
          }}
          className="absolute right-5 top-5 grid size-8 place-items-center rounded-lg text-slate-400 transition group-hover:bg-white group-hover:text-[#59627f] sm:right-6 lg:static"
        >
          <ChevronDown size={17} />
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={
              reduceMotion
                ? false
                : {
                    opacity: 0,
                    height: 0
                  }
            }
            animate={{
              opacity: 1,
              height: "auto"
            }}
            exit={{
              opacity: 0,
              height: 0
            }}
            transition={{
              duration: reduceMotion
                ? 0
                : 0.22
            }}
            className="overflow-hidden"
          >
            <NetworkDetail
              network={network}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.article>
  );
}

function SignalValue({
  rssi
}: {
  rssi: number;
}) {
  const strength = rssi >= -50
    ? 4
    : rssi >= -60
      ? 3
      : rssi >= -70
        ? 2
        : 1;

  return (
    <div className="min-w-0">
      <p className="text-[10px] font-medium uppercase tracking-[0.08em] text-[#a0a5b7]">
        Sinal
      </p>
      <div className="mt-1.5 flex items-center gap-2">
        <div className="flex h-4 items-end gap-[2px]" aria-hidden="true">
          {[1, 2, 3, 4].map(level => (
            <span
              key={level}
              className={[
                "w-[3px] rounded-full",
                level <= strength
                  ? "bg-[#526de1]"
                  : "bg-[#e2e5ee]",
                level === 1
                  ? "h-1.5"
                  : level === 2
                    ? "h-2.5"
                    : level === 3
                      ? "h-3.5"
                      : "h-4"
              ].join(" ")}
            />
          ))}
        </div>
        <span className="text-sm font-semibold tabular-nums text-[#444c68]">
          {rssi} dBm
        </span>
      </div>
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
    <div className="min-w-0">
      <p className="text-[10px] font-medium uppercase tracking-[0.08em] text-[#a0a5b7]">
        {label}
      </p>
      <p className="mt-1.5 truncate text-sm font-medium text-[#505872]" title={value}>
        {value}
      </p>
    </div>
  );
}

function DetailItem({
  label,
  value,
  mono = false,
  icon
}: {
  label: string;
  value: string;
  mono?: boolean;
  icon?: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-[#e9ebf3] bg-white px-3.5 py-3">
      <dt className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-[0.08em] text-[#9a9fb2]">
        {icon}
        {label}
      </dt>
      <dd
        className={[
          "mt-1.5 break-all text-sm font-medium text-[#4a526d]",
          mono
            ? "font-mono text-[11px] leading-5"
            : ""
        ].join(" ")}
      >
        {value}
      </dd>
    </div>
  );
}

function DetailSection({
  title,
  icon,
  children
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <section>
      <div className="flex items-center gap-2 text-[#59627f]">
        {icon}
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.12em]">
          {title}
        </h3>
      </div>
      <dl className="mt-3 grid gap-2">
        {children}
      </dl>
    </section>
  );
}

function NetworkDetail({
  network
}: {
  network: NetworkObservation;
}) {
  const analysis =
    network.analysis;

  const features =
    analysis.features;

  return (
    <div className="border-t border-[#eceef5] bg-[#f8f9fc] px-5 py-5 sm:px-6 sm:py-6">
      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        <DetailSection
          title="Identificação"
          icon={<Fingerprint size={14} />}
        >
          <DetailItem
            label="SSID"
            value={
              network.ssid
              || "SSID não transmitido"
            }
          />
          <DetailItem
            label="BSSID"
            value={network.bssid}
            mono
          />
          <DetailItem
            label="Network ID"
            value={network.network_id}
            mono
          />
        </DetailSection>

        <DetailSection
          title="Wi-Fi"
          icon={<RadioTower size={14} />}
        >
          <DetailItem
            label="Frequência"
            value={formatFrequency(
              network.center_frequency_khz
            )}
          />
          <DetailItem
            label="Qualidade"
            value={`${network.link_quality}%`}
          />
          <DetailItem
            label="Beacon interval"
            value={`${network.beacon_interval_ms.toFixed(2)} ms`}
          />
          <DetailItem
            label="PHY"
            value={network.phy_type}
          />
        </DetailSection>

        <DetailSection
          title="Análise"
          icon={<Gauge size={14} />}
        >
          <DetailItem
            label="Status"
            value={analysis.status}
          />
          <DetailItem
            label="Anomaly score"
            value={formatScore(
              analysis.anomaly_score
            )}
          />
          <DetailItem
            label="Threshold"
            value={formatScore(
              analysis.threshold
            )}
          />
          <DetailItem
            label="Inferência"
            value={
              analysis.inference_ms === null
                ? "—"
                : `${analysis.inference_ms.toFixed(3)} ms`
            }
          />
        </DetailSection>

        <DetailSection
          title="Contexto"
          icon={<Activity size={14} />}
        >
          <DetailItem
            label="Histórico disponível"
            value={
              analysis.context_available === null
                ? "—"
                : analysis.context_available
                  ? "Sim"
                  : "Não"
            }
          />
          <DetailItem
            label="Resolução"
            value={
              analysis.context_resolution
              ?? "—"
            }
          />
          <DetailItem
            label="Features completas"
            value={
              analysis.feature_complete === null
                ? "—"
                : analysis.feature_complete
                  ? "Sim"
                  : "Não"
            }
          />
          <DetailItem
            label="Modelo"
            value={
              analysis.model_version
              ?? "—"
            }
            mono
          />
        </DetailSection>
      </div>

      {features && (
        <section className="mt-6 rounded-[1.2rem] border border-[#e4e7f0] bg-white p-4">
          <div className="flex items-center gap-2 text-[#59627f]">
            <SlidersHorizontal size={14} />
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.12em]">
              Features desktop_candidate_v1
            </h3>
          </div>

          <dl className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            <DetailItem
              label="SSID/BSSID count"
              value={
                features.ssid_bssid_count
                  ?.toString()
                ?? "—"
              }
            />
            <DetailItem
              label="BSSID changed"
              value={
                features.bssid_changed
                  ?.toString()
                ?? "—"
              }
            />
            <DetailItem
              label="Security changed"
              value={
                features.security_changed
                  ?.toString()
                ?? "—"
              }
            />
            <DetailItem
              label="Security strength delta"
              value={
                features.security_strength_delta
                  ?.toString()
                ?? "—"
              }
            />
          </dl>
        </section>
      )}

      <div className="mt-4 flex items-start gap-3 rounded-xl border border-[#dfe4f2] bg-[#f1f4fd] p-3.5 text-xs leading-5 text-[#5f6884]">
        <div className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-lg bg-white text-[#526de1] shadow-sm">
          <ShieldCheck size={14} />
        </div>
        <p>{analysis.reason}</p>
      </div>
    </div>
  );
}
