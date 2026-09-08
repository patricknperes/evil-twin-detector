import {
  useCallback,
  useEffect,
  useMemo,
  useState
} from "react";
import {
  ChevronDown,
  ChevronUp,
  Filter,
  RefreshCw,
  Search,
  Wifi
} from "lucide-react";

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

export function NetworksPage() {
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
    <div className="space-y-7">
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
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      )}

      {loading && !hasScan ? (
        <section className="panel p-8">
          <div className="flex items-center gap-3 text-sm text-slate-500">
            <RefreshCw
              size={17}
              className="animate-spin"
            />
            Consultando a última varredura…
          </div>
        </section>
      ) : !hasScan ? (
        <section className="panel p-10 text-center">
          <div className="mx-auto grid size-12 place-items-center rounded-2xl bg-slate-100 text-slate-500">
            <Wifi size={22} />
          </div>

          <h2 className="mt-4 text-base font-semibold text-slate-900">
            Nenhuma varredura disponível
          </h2>

          <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">
            Execute um scan na tela “Escanear redes”.
            Esta página mostra somente a última varredura
            ainda disponível no runtime local.
          </p>
        </section>
      ) : (
        <>
          <section className="panel flex flex-wrap items-center justify-between gap-4 px-5 py-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Última varredura no runtime
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-800">
                {observedAtUtc
                  ? formatDateTime(
                      observedAtUtc
                    )
                  : "Horário indisponível"}
              </p>
            </div>

            <div className="text-right">
              <p className="text-[11px] text-slate-400">
                scan_id
              </p>
              <p
                className="mt-1 max-w-[360px] truncate font-mono text-[11px] text-slate-500"
                title={scanId ?? undefined}
              >
                {scanId ?? "—"}
              </p>
            </div>
          </section>

          <section className="grid grid-cols-5 gap-4">
            <SummaryCard
              label="Redes"
              value={networks.length}
            />
            <SummaryCard
              label="Baixa"
              value={counts.low}
            />
            <SummaryCard
              label="Média"
              value={counts.medium}
            />
            <SummaryCard
              label="Alta"
              value={counts.high}
            />
            <SummaryCard
              label="Indisponível"
              value={counts.unavailable}
            />
          </section>

          <section className="panel p-4">
            <div className="flex flex-wrap items-center gap-3">
              <label className="relative min-w-[280px] flex-1">
                <Search
                  size={16}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                />
                <input
                  value={query}
                  onChange={event =>
                    setQuery(
                      event.target.value
                    )
                  }
                  placeholder="Buscar por SSID, BSSID, segurança ou suspeita"
                  className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-9 pr-3 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-slate-400"
                />
              </label>

              <label className="relative">
                <Filter
                  size={15}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                />
                <select
                  value={filter}
                  onChange={event =>
                    setFilter(
                      event.target.value as FilterValue
                    )
                  }
                  className="appearance-none rounded-xl border border-slate-200 bg-white py-2.5 pl-9 pr-9 text-sm text-slate-700 outline-none"
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
              </label>

              <select
                value={sort}
                onChange={event =>
                  setSort(
                    event.target.value as NetworkSort
                  )
                }
                className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none"
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
            </div>

            <div className="mt-3 text-xs text-slate-400">
              Exibindo {visibleNetworks.length} de {networks.length} redes.
            </div>
          </section>

          <section className="panel overflow-hidden">
            {visibleNetworks.length === 0 ? (
              <div className="p-10 text-center text-sm text-slate-500">
                Nenhuma rede corresponde aos filtros atuais.
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {visibleNetworks.map(
                  network => {
                    const isExpanded =
                      expanded.has(
                        network.network_id
                      );

                    return (
                      <article
                        key={network.network_id}
                      >
                        <button
                          type="button"
                          onClick={() =>
                            toggle(
                              network.network_id
                            )
                          }
                          className="grid w-full grid-cols-[minmax(0,1.6fr)_110px_110px_160px_170px_32px] items-center gap-4 px-5 py-4 text-left transition hover:bg-slate-50"
                        >
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-slate-900">
                              {network.ssid
                                || "SSID não transmitido"}
                            </p>

                            <p className="mt-1 truncate font-mono text-xs text-slate-400">
                              {network.bssid}
                            </p>
                          </div>

                          <Value
                            label="Sinal"
                            value={`${network.rssi_dbm} dBm`}
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

                          <div>
                            <p className="mb-1.5 text-xs text-slate-400">
                              Análise
                            </p>

                            <SuspicionBadge
                              level={
                                network.analysis
                                  .suspicion_level
                              }
                            />
                          </div>

                          <span className="text-slate-400">
                            {isExpanded ? (
                              <ChevronUp size={17} />
                            ) : (
                              <ChevronDown size={17} />
                            )}
                          </span>
                        </button>

                        {isExpanded && (
                          <NetworkDetail
                            network={network}
                          />
                        )}
                      </article>
                    );
                  }
                )}
              </div>
            )}
          </section>

          <div className="rounded-xl border border-slate-200 bg-slate-100/70 p-4 text-xs leading-5 text-slate-500">
            <strong className="font-semibold text-slate-700">
              Interpretação:
            </strong>{" "}
            “Baixa suspeita” representa uma observação dentro do comportamento
            esperado pelo modelo. “Alta suspeita” indica uma observação acima
            do threshold de anomalia e não confirma um ataque Evil Twin.
            “Indisponível” indica contexto insuficiente ou artefatos ainda
            não prontos.
          </div>
        </>
      )}
    </div>
  );
}

function SummaryCard({
  label,
  value
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="panel px-4 py-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <p className="mt-1.5 text-2xl font-semibold tracking-tight text-slate-950">
        {value}
      </p>
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
      <p className="text-xs text-slate-400">
        {label}
      </p>
      <p className="mt-1 truncate text-sm font-medium text-slate-700">
        {value}
      </p>
    </div>
  );
}

function DetailItem({
  label,
  value,
  mono = false
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="text-xs text-slate-400">
        {label}
      </dt>
      <dd
        className={[
          "mt-1 break-all text-sm text-slate-700",
          mono
            ? "font-mono text-xs"
            : ""
        ].join(" ")}
      >
        {value}
      </dd>
    </div>
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
    <div className="border-t border-slate-100 bg-slate-50/80 px-5 py-5">
      <div className="grid grid-cols-4 gap-6">
        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Identificação
          </h3>

          <dl className="mt-3 space-y-3">
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
          </dl>
        </section>

        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Wi-Fi
          </h3>

          <dl className="mt-3 space-y-3">
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
          </dl>
        </section>

        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Análise
          </h3>

          <dl className="mt-3 space-y-3">
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
          </dl>
        </section>

        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Contexto
          </h3>

          <dl className="mt-3 space-y-3">
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
          </dl>
        </section>
      </div>

      {features && (
        <section className="mt-6 border-t border-slate-200 pt-5">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Features desktop_candidate_v1
          </h3>

          <dl className="mt-3 grid grid-cols-4 gap-4">
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

      <div className="mt-5 rounded-xl border border-slate-200 bg-white p-3 text-xs leading-5 text-slate-500">
        {analysis.reason}
      </div>
    </div>
  );
}
