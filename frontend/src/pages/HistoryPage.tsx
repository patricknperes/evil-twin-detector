import {
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from "react";
import {
  Activity,
  ArrowRight,
  Database,
  FileClock,
  Filter,
  LoaderCircle,
  RefreshCw,
  ScanLine
} from "lucide-react";

import {
  AutoScanRefreshNotice
} from "../components/AutoScanRefreshNotice";
import {
  HistoryPagination
} from "../components/HistoryPagination";
import {
  PageHeader
} from "../components/PageHeader";
import {
  SuspicionBadge
} from "../components/SuspicionBadge";
import {
  useRuntimeStatus
} from "../contexts/RuntimeStatusContext";
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
  decisionLabel,
  matchesDecisionFilter,
  shortHash,
  type DetectionDecisionFilter
} from "../lib/historyUi";
import {
  formatFrequency,
  formatScore
} from "../lib/networkUi";
import type {
  HistoryDetectionDetailResponse,
  HistoryDetectionListResponse,
  HistoryDetectionSummary,
  HistoryModelVersion,
  HistoryModelVersionListResponse,
  HistoryObservation,
  HistoryScanDetailResponse,
  HistoryScanListResponse,
  HistoryScanSummary,
  SuspicionLevel
} from "../types/api";

type HistoryTab =
  | "scans"
  | "detections";

const EMPTY_PAGINATION = {
  limit: 25,
  offset: 0,
  returned: 0,
  total: 0
};

export function HistoryPage() {
  const runtime = useRuntimeStatus();

  const [
    activeTab,
    setActiveTab
  ] = useState<HistoryTab>(
    "scans"
  );

  const [
    scans,
    setScans
  ] = useState<HistoryScanListResponse>({
    pagination:
      EMPTY_PAGINATION,
    items: []
  });

  const [
    detections,
    setDetections
  ] = useState<HistoryDetectionListResponse>({
    pagination:
      EMPTY_PAGINATION,
    items: []
  });

  const [
    models,
    setModels
  ] = useState<HistoryModelVersionListResponse>({
    pagination:
      EMPTY_PAGINATION,
    items: []
  });

  const [
    selectedScan,
    setSelectedScan
  ] = useState<HistoryScanDetailResponse | null>(
    null
  );

  const [
    selectedDetection,
    setSelectedDetection
  ] = useState<HistoryDetectionDetailResponse | null>(
    null
  );

  const [
    selectedModel,
    setSelectedModel
  ] = useState<HistoryModelVersion | null>(
    null
  );

  const [
    decisionFilter,
    setDecisionFilter
  ] = useState<DetectionDecisionFilter>(
    "all"
  );

  const [
    suspicionFilter,
    setSuspicionFilter
  ] = useState<
    "all"
    | SuspicionLevel
  >(
    "all"
  );

  const [
    modelFilter,
    setModelFilter
  ] = useState<
    "all"
    | number
  >(
    "all"
  );

  const [
    loading,
    setLoading
  ] = useState(true);

  const [
    detailLoading,
    setDetailLoading
  ] = useState(false);

  const [
    error,
    setError
  ] = useState<string | null>(
    null
  );

  async function loadScans(
    offset = scans.pagination.offset
  ) {
    setLoading(true);
    setError(null);

    try {
      const payload =
        await api.historyScans({
          limit:
            scans.pagination.limit,
          offset
        });

      setScans(
        payload
      );

      if (
        payload.items.length
        === 0
      ) {
        setSelectedScan(
          null
        );
      }
    } catch {
      setError(
        "Não foi possível carregar o histórico de scans."
      );
    } finally {
      setLoading(false);
    }
  }

  async function loadDetections(
    offset = detections.pagination.offset
  ) {
    setLoading(true);
    setError(null);

    try {
      const isAnomaly =
        decisionFilter === "anomaly"
          ? true
          : decisionFilter === "normal"
            ? false
            : undefined;

      const payload =
        await api.historyDetections({
          limit:
            detections.pagination.limit,
          offset,
          is_anomaly:
            isAnomaly,
          suspicion_level:
            suspicionFilter === "all"
              ? undefined
              : suspicionFilter,
          model_version_id:
            modelFilter === "all"
              ? undefined
              : modelFilter
        });

      const filtered =
        decisionFilter === "insufficient"
          ? {
              ...payload,
              items:
                payload.items.filter(
                  detection =>
                    matchesDecisionFilter(
                      detection,
                      "insufficient"
                    )
                )
            }
          : payload;

      setDetections(
        filtered
      );

      if (
        filtered.items.length
        === 0
      ) {
        setSelectedDetection(
          null
        );
      }
    } catch {
      setError(
        "Não foi possível carregar o histórico de detecções."
      );
    } finally {
      setLoading(false);
    }
  }

  async function loadModels() {
    try {
      setModels(
        await api.historyModels({
          limit: 100,
          offset: 0
        })
      );
    } catch {
      // Model list is an optional enhancement for filters.
      setModels({
        pagination: {
          limit: 100,
          offset: 0,
          returned: 0,
          total: 0
        },
        items: []
      });
    }
  }

  async function openScan(
    scan:
      HistoryScanSummary
  ) {
    setDetailLoading(
      true
    );
    setSelectedDetection(
      null
    );
    setSelectedModel(
      null
    );

    try {
      setSelectedScan(
        await api
          .historyScanDetail(
            scan.scan_id
          )
      );
    } catch {
      setError(
        "Não foi possível abrir os detalhes deste scan."
      );
    } finally {
      setDetailLoading(
        false
      );
    }
  }

  async function openDetection(
    detectionId: number
  ) {
    setDetailLoading(
      true
    );
    setSelectedScan(
      null
    );
    setSelectedModel(
      null
    );

    try {
      const detail =
        await api
          .historyDetectionDetail(
            detectionId
          );

      setSelectedDetection(
        detail
      );

      setActiveTab(
        "detections"
      );
    } catch {
      setError(
        "Não foi possível abrir os detalhes desta detecção."
      );
    } finally {
      setDetailLoading(
        false
      );
    }
  }

  async function openModel(
    modelVersionId: number
  ) {
    setDetailLoading(
      true
    );

    try {
      setSelectedModel(
        await api
          .historyModelDetail(
            modelVersionId
          )
      );
    } catch {
      setError(
        "Não foi possível abrir a versão do modelo."
      );
    } finally {
      setDetailLoading(
        false
      );
    }
  }


async function refreshFromRuntimeEvent() {
  setError(null);
  try {
    const tasks: Promise<unknown>[] = [loadModels()];
    if (activeTab === "scans") {
      tasks.push(api.historyScans({limit:scans.pagination.limit,offset:scans.pagination.offset}).then(payload=>{setScans(payload);}));
    } else {
      const isAnomaly = decisionFilter === "anomaly" ? true : decisionFilter === "normal" ? false : undefined;
      tasks.push(api.historyDetections({limit:detections.pagination.limit,offset:detections.pagination.offset,is_anomaly:isAnomaly,suspicion_level:suspicionFilter === "all" ? undefined : suspicionFilter,model_version_id:modelFilter === "all" ? undefined : modelFilter}).then(payload=>{
        const filtered = decisionFilter === "insufficient" ? {...payload,items:payload.items.filter(detection=>matchesDecisionFilter(detection,"insufficient"))} : payload;
        setDetections(filtered);
      }));
    }
    if (selectedModel) {
      tasks.push(api.historyModelDetail(selectedModel.model_version_id).then(model=>{setSelectedModel(model);}));
    }
    await Promise.all(tasks);
  } catch {
    setError("Uma nova varredura foi persistida, mas o histórico não pôde ser atualizado automaticamente.");
    throw new Error("history_runtime_refresh_failed");
  }
}

const autoRefresh = useAutoScanRefresh(refreshFromRuntimeEvent);

useEffect(() => {
  if (!runtime.recoveredAt) return;
  void refreshFromRuntimeEvent().catch(()=>undefined);
}, [runtime.recoveredAt]);

  useEffect(() => {
    void Promise.all([
      loadScans(
        0
      ),
      loadModels()
    ]);
    // Initial load only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (
      activeTab
      === "detections"
    ) {
      void loadDetections(
        0
      );
    }
    // Filters intentionally trigger a first-page reload.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    activeTab,
    decisionFilter,
    suspicionFilter,
    modelFilter
  ]);

  const totals = useMemo(
    () => {
      const scanItems =
        scans.items;

      return {
        scans:
          scans.pagination.total,
        observations:
          scanItems.reduce(
            (
              sum,
              item
            ) =>
              sum
              + item.total_networks,
            0
          ),
        anomalies:
          scanItems.reduce(
            (
              sum,
              item
            ) =>
              sum
              + item.anomaly_count,
            0
          ),
        insufficient:
          scanItems.reduce(
            (
              sum,
              item
            ) =>
              sum
              + item
                .insufficient_history_count,
            0
          )
      };
    },
    [
      scans
    ]
  );

  return (
    <div className="space-y-7">
      <PageHeader
        title="Histórico"
        description="Auditoria local de scans, observações anonimizadas, detecções e versões do modelo. O histórico não armazena SSID, BSSID ou GUID da interface em claro."
        actions={
          <div className="flex flex-wrap items-center justify-end gap-2">
            <AutoScanRefreshNotice state={autoRefresh}/>
            <button
              type="button"
              className="btn-secondary"
              disabled={loading}
              onClick={() => {
                if (activeTab === "scans") {
                  void loadScans();
                } else {
                  void loadDetections();
                }
              }}
            >
              <RefreshCw size={16} className={loading ? "animate-spin" : ""}/>
              Atualizar
            </button>
          </div>
        }
      />

      <section className="grid grid-cols-4 gap-4">
        <SummaryCard
          label="Scans"
          value={totals.scans}
          icon={
            <ScanLine size={17} />
          }
        />
        <SummaryCard
          label="Observações nesta página"
          value={totals.observations}
          icon={
            <Database size={17} />
          }
        />
        <SummaryCard
          label="Anomalias nesta página"
          value={totals.anomalies}
          icon={
            <Activity size={17} />
          }
        />
        <SummaryCard
          label="Histórico insuficiente"
          value={totals.insufficient}
          icon={
            <FileClock size={17} />
          }
        />
      </section>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      )}

      <section className="panel overflow-hidden">
        <div className="flex items-center justify-between gap-4 border-b border-slate-100 px-5 py-4">
          <div className="flex items-center gap-2 rounded-xl bg-slate-100 p-1">
            <TabButton
              active={
                activeTab
                === "scans"
              }
              label="Scans"
              onClick={() => {
                setActiveTab(
                  "scans"
                );
                setSelectedDetection(
                  null
                );
                setSelectedModel(
                  null
                );
              }}
            />

            <TabButton
              active={
                activeTab
                === "detections"
              }
              label="Detecções"
              onClick={() => {
                setActiveTab(
                  "detections"
                );
                setSelectedScan(
                  null
                );
              }}
            />
          </div>

          {activeTab
            === "detections"
            && (
              <DetectionFilters
                decisionFilter={
                  decisionFilter
                }
                suspicionFilter={
                  suspicionFilter
                }
                modelFilter={
                  modelFilter
                }
                models={
                  models.items
                }
                onDecisionChange={
                  setDecisionFilter
                }
                onSuspicionChange={
                  setSuspicionFilter
                }
                onModelChange={
                  setModelFilter
                }
              />
            )}
        </div>

        <div className="grid min-h-[620px] grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
          <div className="border-r border-slate-100">
            {loading ? (
              <LoadingHistory />
            ) : activeTab
              === "scans" ? (
                <ScanList
                  scans={scans}
                  selectedScanId={
                    selectedScan
                      ?.scan
                      .scan_id
                    ?? null
                  }
                  onOpen={
                    scan =>
                      void openScan(
                        scan
                      )
                  }
                  onOffsetChange={
                    offset =>
                      void loadScans(
                        offset
                      )
                  }
                />
              ) : (
                <DetectionList
                  detections={
                    detections
                  }
                  selectedDetectionId={
                    selectedDetection
                      ?.detection
                      .detection_id
                    ?? null
                  }
                  onOpen={
                    detection =>
                      void openDetection(
                        detection
                        .detection_id
                      )
                  }
                  onOffsetChange={
                    offset =>
                      void loadDetections(
                        offset
                      )
                  }
                />
              )}
          </div>

          <aside className="bg-slate-50/60">
            {detailLoading ? (
              <div className="flex h-full min-h-[520px] items-center justify-center text-sm text-slate-500">
                <LoaderCircle
                  size={18}
                  className="mr-2 animate-spin"
                />
                Carregando detalhes…
              </div>
            ) : selectedScan ? (
              <ScanDetailPanel
                detail={
                  selectedScan
                }
                onOpenDetection={
                  id =>
                    void openDetection(
                      id
                    )
                }
              />
            ) : selectedDetection ? (
              <DetectionDetailPanel
                detail={
                  selectedDetection
                }
                selectedModel={
                  selectedModel
                }
                onOpenModel={
                  id =>
                    void openModel(
                      id
                    )
                }
              />
            ) : (
              <EmptyDetail />
            )}
          </aside>
        </div>
      </section>

      <div className="rounded-xl border border-slate-200 bg-slate-100/70 p-4 text-xs leading-5 text-slate-500">
        <strong className="font-semibold text-slate-700">
          Privacidade:
        </strong>{" "}
        esta tela mostra hashes persistidos de SSID, BSSID e interface.
        Os valores originais não são armazenados em claro; porém, hashes de
        SSIDs previsíveis não devem ser tratados como anonimização absoluta.
      </div>
    </div>
  );
}

function TabButton({
  active,
  label,
  onClick
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "rounded-lg px-4 py-2 text-sm font-semibold transition",
        active
          ? "bg-white text-slate-950 shadow-sm"
          : "text-slate-500 hover:text-slate-900"
      ].join(" ")}
    >
      {label}
    </button>
  );
}

function SummaryCard({
  label,
  value,
  icon
}: {
  label: string;
  value: number;
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

      <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        {value}
      </p>
    </article>
  );
}

function DetectionFilters({
  decisionFilter,
  suspicionFilter,
  modelFilter,
  models,
  onDecisionChange,
  onSuspicionChange,
  onModelChange
}: {
  decisionFilter:
    DetectionDecisionFilter;
  suspicionFilter:
    "all"
    | SuspicionLevel;
  modelFilter:
    "all"
    | number;
  models:
    HistoryModelVersion[];
  onDecisionChange: (
    value:
      DetectionDecisionFilter
  ) => void;
  onSuspicionChange: (
    value:
      "all"
      | SuspicionLevel
  ) => void;
  onModelChange: (
    value:
      "all"
      | number
  ) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <Filter
        size={15}
        className="text-slate-400"
      />

      <select
        aria-label="Filtrar decisão"
        value={decisionFilter}
        onChange={event =>
          onDecisionChange(
            event.target.value as DetectionDecisionFilter
          )
        }
        className="rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-xs text-slate-700 outline-none"
      >
        <option value="all">
          Todas as decisões
        </option>
        <option value="anomaly">
          Anomalias
        </option>
        <option value="normal">
          Dentro do esperado
        </option>
        <option value="insufficient">
          Histórico insuficiente
        </option>
      </select>

      <select
        aria-label="Filtrar suspeita"
        value={suspicionFilter}
        onChange={event =>
          onSuspicionChange(
            event.target.value as "all" | SuspicionLevel
          )
        }
        className="rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-xs text-slate-700 outline-none"
      >
        <option value="all">
          Toda suspeita
        </option>
        <option value="low">
          Baixa
        </option>
        <option value="medium">
          Média
        </option>
        <option value="high">
          Alta
        </option>
        <option value="unavailable">
          Indisponível
        </option>
      </select>

      <select
        aria-label="Filtrar modelo"
        value={
          modelFilter
        }
        onChange={event =>
          onModelChange(
            event.target.value
            === "all"
              ? "all"
              : Number(
                  event.target.value
                )
          )
        }
        className="max-w-[200px] rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-xs text-slate-700 outline-none"
      >
        <option value="all">
          Todos os modelos
        </option>

        {models.map(
          model => (
            <option
              key={
                model
                .model_version_id
              }
              value={
                model
                .model_version_id
              }
            >
              {model.version_name}
            </option>
          )
        )}
      </select>
    </div>
  );
}

function ScanList({
  scans,
  selectedScanId,
  onOpen,
  onOffsetChange
}: {
  scans:
    HistoryScanListResponse;
  selectedScanId:
    string
    | null;
  onOpen: (
    scan:
      HistoryScanSummary
  ) => void;
  onOffsetChange: (
    offset: number
  ) => void;
}) {
  if (
    scans.items.length
    === 0
  ) {
    return (
      <EmptyList
        title="Nenhum scan persistido"
        description="O histórico começará a aparecer depois que uma varredura for executada e salva no SQLite."
      />
    );
  }

  return (
    <>
      <div className="divide-y divide-slate-100">
        {scans.items.map(
          scan => (
            <button
              type="button"
              key={scan.scan_id}
              onClick={() =>
                onOpen(
                  scan
                )
              }
              className={[
                "grid w-full grid-cols-[minmax(0,1fr)_95px_90px_90px_24px] items-center gap-3 px-5 py-4 text-left transition",
                selectedScanId
                  === scan.scan_id
                  ? "bg-slate-100"
                  : "hover:bg-slate-50"
              ].join(" ")}
            >
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-900">
                  {formatDateTime(
                    scan
                      .observed_at_utc
                  )}
                </p>

                <p className="mt-1 truncate font-mono text-[11px] text-slate-400">
                  {scan.scan_id}
                </p>
              </div>

              <SmallValue
                label="Redes"
                value={
                  scan
                    .total_networks
                }
              />

              <SmallValue
                label="Anomalias"
                value={
                  scan
                    .anomaly_count
                }
              />

              <SmallValue
                label="Sem contexto"
                value={
                  scan
                    .insufficient_history_count
                }
              />

              <ArrowRight
                size={15}
                className="text-slate-300"
              />
            </button>
          )
        )}
      </div>

      <HistoryPagination
        pagination={
          scans.pagination
        }
        onOffsetChange={
          onOffsetChange
        }
      />
    </>
  );
}

function DetectionList({
  detections,
  selectedDetectionId,
  onOpen,
  onOffsetChange
}: {
  detections:
    HistoryDetectionListResponse;
  selectedDetectionId:
    number
    | null;
  onOpen: (
    detection:
      HistoryDetectionSummary
  ) => void;
  onOffsetChange: (
    offset: number
  ) => void;
}) {
  if (
    detections.items.length
    === 0
  ) {
    return (
      <EmptyList
        title="Nenhuma detecção encontrada"
        description="Não existem registros que correspondam aos filtros atuais."
      />
    );
  }

  return (
    <>
      <div className="divide-y divide-slate-100">
        {detections.items.map(
          detection => (
            <button
              type="button"
              key={
                detection
                  .detection_id
              }
              onClick={() =>
                onOpen(
                  detection
                )
              }
              className={[
                "grid w-full grid-cols-[minmax(0,1fr)_170px_100px_24px] items-center gap-3 px-5 py-4 text-left transition",
                selectedDetectionId
                  === detection
                    .detection_id
                  ? "bg-slate-100"
                  : "hover:bg-slate-50"
              ].join(" ")}
            >
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-900">
                  Detecção #
                  {detection
                    .detection_id}
                </p>

                <p className="mt-1 text-xs text-slate-400">
                  {formatDateTime(
                    detection
                      .created_at_utc
                  )}
                </p>
              </div>

              <SuspicionBadge
                level={
                  detection
                    .suspicion_level
                }
              />

              <span className="text-xs font-medium text-slate-500">
                {decisionLabel(
                  detection
                )}
              </span>

              <ArrowRight
                size={15}
                className="text-slate-300"
              />
            </button>
          )
        )}
      </div>

      <HistoryPagination
        pagination={
          detections
            .pagination
        }
        onOffsetChange={
          onOffsetChange
        }
      />
    </>
  );
}

function ScanDetailPanel({
  detail,
  onOpenDetection
}: {
  detail:
    HistoryScanDetailResponse;
  onOpenDetection: (
    detectionId: number
  ) => void;
}) {
  const scan = detail.scan;

  return (
    <div className="p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
        Scan selecionado
      </p>

      <h2 className="mt-2 text-lg font-semibold text-slate-950">
        {formatDateTime(
          scan
            .observed_at_utc
        )}
      </h2>

      <p className="mt-1 break-all font-mono text-[11px] text-slate-400">
        {scan.scan_id}
      </p>

      <dl className="mt-5 grid grid-cols-2 gap-4">
        <DetailValue
          label="Redes"
          value={
            String(
              scan
                .total_networks
            )
          }
        />
        <DetailValue
          label="Interfaces"
          value={
            String(
              scan
                .interface_count
            )
          }
        />
        <DetailValue
          label="Features"
          value={
            String(
              scan
                .feature_count
            )
          }
        />
        <DetailValue
          label="Detecções"
          value={
            String(
              scan
                .detection_count
            )
          }
        />
      </dl>

      <div className="mt-6 border-t border-slate-200 pt-5">
        <h3 className="text-sm font-semibold text-slate-900">
          Observações anonimizadas
        </h3>

        {detail.observations.length
          === 0 ? (
            <p className="mt-3 text-sm text-slate-500">
              Nenhuma observação registrada.
            </p>
          ) : (
            <div className="mt-3 space-y-3">
              {detail.observations.map(
                observation => (
                  <ObservationCard
                    key={
                      observation
                        .observation_id
                    }
                    observation={
                      observation
                    }
                    onOpenDetection={
                      onOpenDetection
                    }
                  />
                )
              )}
            </div>
          )}
      </div>
    </div>
  );
}

function ObservationCard({
  observation,
  onOpenDetection
}: {
  observation:
    HistoryObservation;
  onOpenDetection: (
    id: number
  ) => void;
}) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">
            Observação #
            {observation
              .observation_id}
          </p>

          <p className="mt-1 font-mono text-[11px] text-slate-400">
            Network{" "}
            {shortHash(
              observation
                .network_id,
              8
            )}
          </p>
        </div>

        {observation
          .detection
          && (
            <SuspicionBadge
              level={
                observation
                  .detection
                  .suspicion_level
              }
            />
          )}
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3">
        <DetailValue
          label="SSID hash"
          value={shortHash(
            observation
              .ssid_hash
          )}
          mono
        />
        <DetailValue
          label="BSSID hash"
          value={shortHash(
            observation
              .bssid_hash
          )}
          mono
        />
        <DetailValue
          label="RSSI"
          value={`${observation.rssi_dbm} dBm`}
        />
        <DetailValue
          label="Canal"
          value={
            observation
              .ds_parameter_channel
              ?.toString()
            ?? "—"
          }
        />
        <DetailValue
          label="Frequência"
          value={formatFrequency(
            observation
              .center_frequency_khz
          )}
        />
        <DetailValue
          label="Segurança"
          value={
            observation
              .security_type
          }
        />
      </dl>

      {observation.features
        && (
          <div className="mt-4 rounded-lg bg-slate-50 p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              desktop_candidate_v1
            </p>

            <dl className="mt-2 grid grid-cols-2 gap-2">
              <DetailValue
                label="SSID/BSSID count"
                value={
                  observation
                    .features
                    .ssid_bssid_count
                    ?.toString()
                  ?? "—"
                }
              />
              <DetailValue
                label="BSSID changed"
                value={
                  observation
                    .features
                    .bssid_changed
                    ?.toString()
                  ?? "—"
                }
              />
              <DetailValue
                label="Security changed"
                value={
                  observation
                    .features
                    .security_changed
                    ?.toString()
                  ?? "—"
                }
              />
              <DetailValue
                label="Security delta"
                value={
                  observation
                    .features
                    .security_strength_delta
                    ?.toString()
                  ?? "—"
                }
              />
            </dl>
          </div>
        )}

      {observation
        .detection
        && (
          <button
            type="button"
            onClick={() =>
              onOpenDetection(
                observation
                  .detection!
                  .detection_id
              )
            }
            className="mt-4 inline-flex items-center gap-2 text-xs font-semibold text-slate-700 hover:text-slate-950"
          >
            Abrir detecção
            <ArrowRight
              size={13}
            />
          </button>
        )}
    </article>
  );
}

function DetectionDetailPanel({
  detail,
  selectedModel,
  onOpenModel
}: {
  detail:
    HistoryDetectionDetailResponse;
  selectedModel:
    HistoryModelVersion
    | null;
  onOpenModel: (
    modelVersionId:
      number
  ) => void;
}) {
  const detection =
    detail.detection;

  const observation =
    detail.observation;

  return (
    <div className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Detecção selecionada
          </p>

          <h2 className="mt-2 text-lg font-semibold text-slate-950">
            Detecção #
            {detection
              .detection_id}
          </h2>

          <p className="mt-1 text-xs text-slate-400">
            {formatDateTime(
              detection
                .created_at_utc
            )}
          </p>
        </div>

        <SuspicionBadge
          level={
            detection
              .suspicion_level
          }
        />
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-4">
        <DetailValue
          label="Decisão"
          value={decisionLabel(
            detection
          )}
        />
        <DetailValue
          label="Anomaly score"
          value={formatScore(
            detection
              .anomaly_score
          )}
        />
        <DetailValue
          label="Threshold"
          value={formatScore(
            detection
              .threshold
          )}
        />
        <DetailValue
          label="Inferência"
          value={
            detection
              .inference_ms
              === null
              ? "—"
              : `${detection.inference_ms.toFixed(3)} ms`
          }
        />
      </dl>

      <div className="mt-5 rounded-xl border border-slate-200 bg-white p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Observação associada
        </p>

        <dl className="mt-3 grid grid-cols-2 gap-3">
          <DetailValue
            label="SSID hash"
            value={shortHash(
              observation
                .ssid_hash
            )}
            mono
          />
          <DetailValue
            label="BSSID hash"
            value={shortHash(
              observation
                .bssid_hash
            )}
            mono
          />
          <DetailValue
            label="RSSI"
            value={`${observation.rssi_dbm} dBm`}
          />
          <DetailValue
            label="Segurança"
            value={
              observation
                .security_type
            }
          />
        </dl>
      </div>

      <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Motivo
        </p>

        <p className="mt-2 text-sm leading-6 text-slate-600">
          {detection.reason
            || "Nenhuma justificativa registrada."}
        </p>
      </div>

      {detail
        .model_version
        && (
          <div className="mt-5 border-t border-slate-200 pt-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Modelo
                </p>

                <p className="mt-1 text-sm font-semibold text-slate-900">
                  {detail
                    .model_version
                    .version_name}
                </p>
              </div>

              <button
                type="button"
                className="btn-secondary !px-3 !py-2"
                onClick={() =>
                  onOpenModel(
                    detail
                      .model_version!
                      .model_version_id
                  )
                }
              >
                Auditar modelo
              </button>
            </div>

            {selectedModel
              && (
                <ModelAudit
                  model={
                    selectedModel
                  }
                />
              )}
          </div>
        )}
    </div>
  );
}

function ModelAudit({
  model
}: {
  model:
    HistoryModelVersion;
}) {
  return (
    <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">
            {model
              .version_name}
          </p>

          <p className="mt-1 text-xs text-slate-400">
            {model.algorithm}
            {" · "}
            {model
              .feature_set_name}
          </p>
        </div>

        <span
          className={[
            "badge",
            model.active
              ? "bg-emerald-50 text-emerald-700"
              : "bg-slate-100 text-slate-600"
          ].join(" ")}
        >
          {model.active
            ? "Ativo"
            : "Histórico"}
        </span>
      </div>

      <dl className="mt-4 space-y-3">
        <DetailValue
          label="Threshold"
          value={formatScore(
            model.threshold
          )}
        />
        <DetailValue
          label="Reference SHA-256"
          value={shortHash(
            model
              .reference_sha256
          )}
          mono
        />
        <DetailValue
          label="Scaler SHA-256"
          value={shortHash(
            model
              .scaler_sha256
          )}
          mono
        />
        <DetailValue
          label="Model SHA-256"
          value={shortHash(
            model
              .model_sha256
          )}
          mono
        />
        <DetailValue
          label="Threshold SHA-256"
          value={shortHash(
            model
              .threshold_sha256
          )}
          mono
        />
        <DetailValue
          label="Detecções"
          value={
            String(
              model
                .detection_count
            )
          }
        />
      </dl>
    </div>
  );
}

function DetailValue({
  label,
  value,
  mono = false
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] text-slate-400">
        {label}
      </dt>

      <dd
        className={[
          "mt-1 break-all text-xs font-medium text-slate-700",
          mono
            ? "font-mono font-normal"
            : ""
        ].join(" ")}
      >
        {value}
      </dd>
    </div>
  );
}

function SmallValue({
  label,
  value
}: {
  label: string;
  value: number;
}) {
  return (
    <div>
      <p className="text-[11px] text-slate-400">
        {label}
      </p>
      <p className="mt-1 text-sm font-semibold text-slate-700">
        {value}
      </p>
    </div>
  );
}

function LoadingHistory() {
  return (
    <div className="flex min-h-[520px] items-center justify-center text-sm text-slate-500">
      <LoaderCircle
        size={18}
        className="mr-2 animate-spin"
      />
      Carregando histórico…
    </div>
  );
}

function EmptyList({
  title,
  description
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="p-10 text-center">
      <p className="text-sm font-semibold text-slate-800">
        {title}
      </p>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
        {description}
      </p>
    </div>
  );
}

function EmptyDetail() {
  return (
    <div className="flex min-h-[520px] items-center justify-center p-8 text-center">
      <div>
        <FileClock
          size={26}
          className="mx-auto text-slate-300"
        />

        <p className="mt-3 text-sm font-semibold text-slate-700">
          Selecione um registro
        </p>

        <p className="mx-auto mt-1 max-w-xs text-xs leading-5 text-slate-400">
          Os detalhes de auditoria aparecem aqui sem reconstruir
          SSID ou BSSID em claro.
        </p>
      </div>
    </div>
  );
}
