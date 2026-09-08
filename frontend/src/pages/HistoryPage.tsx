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
  motion,
  useReducedMotion
} from "motion/react";

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
  const shouldReduceMotion = useReducedMotion();

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

      <motion.section
        initial={shouldReduceMotion ? false : {opacity: 0, y: 14}}
        animate={{opacity: 1, y: 0}}
        transition={{duration: 0.45, ease: [0.22, 1, 0.36, 1]}}
        className="relative overflow-hidden rounded-[28px] bg-[#303778] px-6 py-6 text-white shadow-[0_24px_70px_rgba(48,55,120,0.18)] sm:px-7 lg:px-8"
      >
        <div className="pointer-events-none absolute -right-20 -top-24 size-72 rounded-full border border-white/10" />
        <div className="pointer-events-none absolute -right-4 -top-10 size-44 rounded-full bg-[#4968e8]/[0.35] blur-3xl" />
        <div className="pointer-events-none absolute bottom-[-5rem] left-[42%] size-48 rounded-full bg-[#2ac7a9]/[0.20] blur-3xl" />

        <div className="relative grid gap-7 lg:grid-cols-[minmax(0,1fr)_minmax(380px,0.78fr)] lg:items-end">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/[0.12] bg-white/[0.08] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-white/[0.72]">
              <FileClock size={13} />
              Trilha de auditoria local
            </div>

            <h2 className="mt-5 max-w-xl text-2xl font-semibold tracking-[-0.035em] sm:text-[2rem] sm:leading-[1.15]">
              Revise o que foi observado sem expor os identificadores Wi-Fi originais.
            </h2>

            <p className="mt-3 max-w-xl text-sm leading-6 text-white/[0.62]">
              Cada scan conecta observações, decisões e a versão científica que participou da inferência, preservando a rastreabilidade do produto.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-2.5">
            <HeroMetric label="Scans persistidos" value={String(scans.pagination.total)} />
            <HeroMetric label="Registros na página" value={String(scans.pagination.returned)} />
            <HeroMetric label="Modelos auditáveis" value={String(models.pagination.total)} />
          </div>
        </div>
      </motion.section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          label="Scans"
          value={totals.scans}
          icon={<ScanLine size={17} />}
          accent="indigo"
        />
        <SummaryCard
          label="Observações nesta página"
          value={totals.observations}
          icon={<Database size={17} />}
          accent="blue"
        />
        <SummaryCard
          label="Anomalias nesta página"
          value={totals.anomalies}
          icon={<Activity size={17} />}
          accent="rose"
        />
        <SummaryCard
          label="Histórico insuficiente"
          value={totals.insufficient}
          icon={<FileClock size={17} />}
          accent="amber"
        />
      </section>

      {error && (
        <div className="rounded-2xl border border-rose-200/80 bg-rose-50/90 px-4 py-3.5 text-sm text-rose-700 shadow-sm">
          {error}
        </div>
      )}

      <section className="panel overflow-hidden">
        <div className="border-b border-[#edf0f7] bg-white px-4 py-4 sm:px-5">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#8a91a8]">
                Registros persistidos
              </p>
              <div className="mt-2 inline-flex items-center gap-1 rounded-2xl bg-[#f2f4fa] p-1">
                <TabButton
                  active={activeTab === "scans"}
                  label="Scans"
                  onClick={() => {
                    setActiveTab("scans");
                    setSelectedDetection(null);
                    setSelectedModel(null);
                  }}
                />
                <TabButton
                  active={activeTab === "detections"}
                  label="Detecções"
                  onClick={() => {
                    setActiveTab("detections");
                    setSelectedScan(null);
                  }}
                />
              </div>
            </div>

            {activeTab === "detections" && (
              <DetectionFilters
                decisionFilter={decisionFilter}
                suspicionFilter={suspicionFilter}
                modelFilter={modelFilter}
                models={models.items}
                onDecisionChange={setDecisionFilter}
                onSuspicionChange={setSuspicionFilter}
                onModelChange={setModelFilter}
              />
            )}
          </div>
        </div>

        <div className="grid min-h-[620px] xl:grid-cols-[minmax(0,1.12fr)_minmax(360px,0.88fr)]">
          <div className="min-w-0 border-b border-[#edf0f7] xl:border-b-0 xl:border-r">
            {loading ? (
              <LoadingHistory />
            ) : activeTab === "scans" ? (
              <ScanList
                scans={scans}
                selectedScanId={selectedScan?.scan.scan_id ?? null}
                onOpen={scan => void openScan(scan)}
                onOffsetChange={offset => void loadScans(offset)}
              />
            ) : (
              <DetectionList
                detections={detections}
                selectedDetectionId={selectedDetection?.detection.detection_id ?? null}
                onOpen={detection => void openDetection(detection.detection_id)}
                onOffsetChange={offset => void loadDetections(offset)}
              />
            )}
          </div>

          <aside className="min-w-0 bg-[#f8f9fd]">
            {detailLoading ? (
              <div className="flex h-full min-h-[420px] items-center justify-center text-sm text-[#737b95]">
                <LoaderCircle size={18} className="mr-2 animate-spin" />
                Carregando detalhes…
              </div>
            ) : selectedScan ? (
              <ScanDetailPanel detail={selectedScan} onOpenDetection={id => void openDetection(id)} />
            ) : selectedDetection ? (
              <DetectionDetailPanel
                detail={selectedDetection}
                selectedModel={selectedModel}
                onOpenModel={id => void openModel(id)}
              />
            ) : (
              <EmptyDetail />
            )}
          </aside>
        </div>
      </section>

      <div className="rounded-[20px] border border-[#e7e9f2] bg-white/[0.08]0 px-4 py-4 text-xs leading-5 text-[#737b95] shadow-[0_8px_24px_rgba(34,39,76,0.04)] sm:px-5">
        <strong className="font-semibold text-[#343a58]">Privacidade:</strong>{" "}
        esta tela mostra hashes persistidos de SSID, BSSID e interface. Os valores originais não são armazenados em claro; porém, hashes de SSIDs previsíveis não devem ser tratados como anonimização absoluta.
      </div>
    </div>
  );
}

function HeroMetric({
  label,
  value
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.075] px-3.5 py-3 backdrop-blur-sm">
      <p className="text-[10px] font-semibold uppercase tracking-[0.13em] text-white/[0.48]">{label}</p>
      <p className="mt-2 text-xl font-semibold tracking-[-0.03em] text-white">{value}</p>
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
        "rounded-xl px-4 py-2 text-sm font-semibold transition-all duration-200",
        active
          ? "bg-white text-[#303778] shadow-[0_5px_16px_rgba(34,39,76,0.09)]"
          : "text-[#7a829b] hover:bg-white/65 hover:text-[#343a58]"
      ].join(" ")}
    >
      {label}
    </button>
  );
}

type SummaryAccent = "indigo" | "blue" | "rose" | "amber";

const summaryAccentClasses: Record<SummaryAccent, {icon: string; bar: string}> = {
  indigo: {icon: "bg-[#eef0ff] text-[#414b9a]", bar: "bg-[#414b9a]"},
  blue: {icon: "bg-[#edf3ff] text-[#4968e8]", bar: "bg-[#4968e8]"},
  rose: {icon: "bg-rose-50 text-rose-600", bar: "bg-rose-500"},
  amber: {icon: "bg-amber-50 text-amber-600", bar: "bg-amber-400"}
};

function SummaryCard({
  label,
  value,
  icon,
  accent
}: {
  label: string;
  value: number;
  icon: ReactNode;
  accent: SummaryAccent;
}) {
  const palette = summaryAccentClasses[accent];

  return (
    <article className="panel relative overflow-hidden p-[18px]">
      <div className={["absolute inset-x-0 top-0 h-0.5", palette.bar].join(" ")} />
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#8a91a8]">
            {label}
          </p>
          <p className="mt-3 text-[1.65rem] font-semibold leading-none tracking-[-0.04em] text-[#222742]">
            {value}
          </p>
        </div>

        <span className={["grid size-9 shrink-0 place-items-center rounded-xl", palette.icon].join(" ")}>
          {icon}
        </span>
      </div>
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
    <div className="flex flex-wrap items-center gap-2">
      <span className="grid size-9 place-items-center rounded-xl bg-[#f2f4fa] text-[#7a829b]">
        <Filter size={15} />
      </span>

      <select
        aria-label="Filtrar decisão"
        value={decisionFilter}
        onChange={event =>
          onDecisionChange(
            event.target.value as DetectionDecisionFilter
          )
        }
        className="min-h-9 rounded-xl border border-[#e4e7f0] bg-white px-3 py-2 text-xs font-medium text-[#555d78] outline-none transition focus:border-[#9eabed]"
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
        className="min-h-9 rounded-xl border border-[#e4e7f0] bg-white px-3 py-2 text-xs font-medium text-[#555d78] outline-none transition focus:border-[#9eabed]"
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
        className="min-h-9 max-w-[210px] rounded-xl border border-[#e4e7f0] bg-white px-3 py-2 text-xs font-medium text-[#555d78] outline-none transition focus:border-[#9eabed]"
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
                "relative grid w-full grid-cols-[minmax(0,1fr)_95px_90px_90px_24px] items-center gap-3 px-5 py-4 text-left transition-colors duration-200 max-[700px]:grid-cols-1 max-[700px]:gap-2 max-[700px]:px-4 max-[700px]:pr-12",
                selectedScanId
                  === scan.scan_id
                  ? "bg-[#f1f3fb]"
                  : "hover:bg-[#fafbfe]"
              ].join(" ")}
            >
              <div className="min-w-0">
                <p className="text-sm font-semibold text-[#2a2f4c]">
                  {formatDateTime(
                    scan
                      .observed_at_utc
                  )}
                </p>

                <p className="mt-1 truncate font-mono text-[11px] text-[#9aa0b4]">
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
                className="text-[#c3c8d8] max-[700px]:absolute max-[700px]:right-4 max-[700px]:top-5"
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
                "relative grid w-full grid-cols-[minmax(0,1fr)_170px_110px_24px] items-center gap-3 px-5 py-4 text-left transition-colors duration-200 max-[700px]:grid-cols-1 max-[700px]:gap-2 max-[700px]:px-4 max-[700px]:pr-12",
                selectedDetectionId
                  === detection
                    .detection_id
                  ? "bg-[#f1f3fb]"
                  : "hover:bg-[#fafbfe]"
              ].join(" ")}
            >
              <div className="min-w-0">
                <p className="text-sm font-semibold text-[#2a2f4c]">
                  Detecção #
                  {detection
                    .detection_id}
                </p>

                <p className="mt-1 text-xs text-[#9aa0b4]">
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
                className="text-[#c3c8d8] max-[700px]:absolute max-[700px]:right-4 max-[700px]:top-5"
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
    <div className="p-5 sm:p-6">
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#9299ae]">
        Scan selecionado
      </p>

      <h2 className="mt-2 text-lg font-semibold tracking-[-0.025em] text-[#262b47]">
        {formatDateTime(
          scan
            .observed_at_utc
        )}
      </h2>

      <p className="mt-1 break-all font-mono text-[11px] text-[#9aa0b4]">
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

      <div className="mt-6 border-t border-[#e7e9f2] pt-5">
        <h3 className="text-sm font-semibold text-[#2a2f4c]">
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
    <article className="rounded-2xl border border-[#e7e9f2] bg-white p-4 shadow-[0_8px_22px_rgba(34,39,76,0.035)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[#2a2f4c]">
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
          <div className="mt-4 rounded-xl bg-[#f5f6fb] p-3">
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
            className="mt-4 inline-flex items-center gap-2 text-xs font-semibold text-[#4968e8] transition hover:text-[#303778]"
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
    <div className="p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#9299ae]">
            Detecção selecionada
          </p>

          <h2 className="mt-2 text-lg font-semibold tracking-[-0.025em] text-[#262b47]">
            Detecção #
            {detection
              .detection_id}
          </h2>

          <p className="mt-1 text-xs text-[#9aa0b4]">
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

      <div className="mt-5 rounded-2xl border border-[#e7e9f2] bg-white p-4 shadow-[0_8px_22px_rgba(34,39,76,0.035)]">
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#9299ae]">
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

      <div className="mt-4 rounded-2xl border border-[#e7e9f2] bg-white p-4 shadow-[0_8px_22px_rgba(34,39,76,0.035)]">
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#9299ae]">
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
          <div className="mt-5 border-t border-[#e7e9f2] pt-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#9299ae]">
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
    <div className="mt-4 rounded-2xl border border-[#e7e9f2] bg-white p-4 shadow-[0_8px_22px_rgba(34,39,76,0.035)]">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[#2a2f4c]">
            {model
              .version_name}
          </p>

          <p className="mt-1 text-xs text-[#9aa0b4]">
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
      <dt className="text-[11px] text-[#9299ae]">
        {label}
      </dt>

      <dd
        className={[
          "mt-1 break-all text-xs font-medium text-[#4b526d]",
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
      <p className="text-[11px] text-[#9299ae]">
        {label}
      </p>
      <p className="mt-1 text-sm font-semibold text-[#343a58]">
        {value}
      </p>
    </div>
  );
}

function LoadingHistory() {
  return (
    <div className="flex min-h-[520px] items-center justify-center text-sm text-[#737b95]">
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
    <div className="p-10 text-center sm:p-14">
      <p className="text-sm font-semibold text-[#343a58]">
        {title}
      </p>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[#737b95]">
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
          className="mx-auto text-[#c8ccda]"
        />

        <p className="mt-3 text-sm font-semibold text-[#424966]">
          Selecione um registro
        </p>

        <p className="mx-auto mt-1 max-w-xs text-xs leading-5 text-[#9299ae]">
          Os detalhes de auditoria aparecem aqui sem reconstruir
          SSID ou BSSID em claro.
        </p>
      </div>
    </div>
  );
}
