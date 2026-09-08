import {
  ChevronDown,
  CircleGauge,
  Radio,
  ShieldCheck,
  Signal,
  Wifi
} from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  useState,
  type ReactNode
} from "react";

import type {
  NetworkObservation
} from "../types/api";
import {
  formatDecimal
} from "../lib/format";
import {
  formatScore
} from "../lib/networkUi";
import {
  animationTokens
} from "../lib/animation";
import {
  SuspicionBadge
} from "./SuspicionBadge";

interface Props {
  network: NetworkObservation;
}

function analysisLabel(
  network: NetworkObservation
): string {
  switch (
    network.analysis.status
  ) {
    case "ready":
      return network.analysis.is_anomaly
        ? "Anomalia acima do threshold"
        : "Dentro do padrão modelado";
    case "insufficient_history":
      return "Histórico normal insuficiente";
    default:
      return "Modelo indisponível";
  }
}

function signalBars(rssi: number): number {
  if (rssi >= -50) return 4;
  if (rssi >= -60) return 3;
  if (rssi >= -70) return 2;
  return 1;
}

const accentClasses = {
  low: "bg-emerald-400",
  medium: "bg-amber-400",
  high: "bg-rose-400",
  unavailable: "bg-slate-300"
} as const;

export function NetworkScanCard({
  network
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const shouldReduceMotion = useReducedMotion();
  const channel = network.ds_parameter_channel ?? "—";
  const activeBars = signalBars(network.rssi_dbm);

  return (
    <article className="group relative border-b border-[#edf0f6] last:border-b-0">
      <span
        className={`absolute bottom-3 left-0 top-3 w-[3px] rounded-r-full opacity-0 transition-opacity group-hover:opacity-100 ${accentClasses[network.analysis.suspicion_level]}`}
        aria-hidden="true"
      />

      <button
        type="button"
        className="grid w-full grid-cols-[minmax(220px,1.7fr)_minmax(90px,.65fr)_minmax(86px,.55fr)_minmax(150px,.85fr)_42px] items-center gap-5 px-6 py-[18px] text-left transition-colors hover:bg-[#f9faff] max-[1050px]:grid-cols-[minmax(220px,1fr)_100px_170px_42px] max-[1050px]:[&>*:nth-child(3)]:hidden max-[700px]:grid-cols-[minmax(0,1fr)_42px] max-[700px]:gap-3 max-[700px]:px-4 max-[700px]:[&>*:nth-child(2)]:hidden max-[700px]:[&>*:nth-child(4)]:hidden"
        onClick={() => setExpanded(value => !value)}
        aria-expanded={expanded}
      >
        <div className="min-w-0">
          <div className="flex min-w-0 items-center gap-3">
            <div className="grid size-10 shrink-0 place-items-center rounded-xl border border-[#e7eaf3] bg-white text-[#4c5fc1] shadow-[0_5px_16px_rgba(35,41,87,0.05)]">
              <Wifi size={18} />
            </div>
            <div className="min-w-0">
              <p className="truncate text-[14px] font-semibold tracking-[-0.015em] text-[#1d2138]">
                {network.ssid || "SSID não transmitido"}
              </p>
              <p className="mt-1 truncate font-mono text-[11px] text-[#8b91a7]">
                {network.bssid}
              </p>
            </div>
          </div>
        </div>

        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#9aa0b5]">
            Sinal
          </p>
          <div className="mt-2 flex items-end gap-1">
            {[1, 2, 3, 4].map(bar => (
              <span
                key={bar}
                className={[
                  "w-1.5 rounded-full",
                  bar <= activeBars ? "bg-[#5268ce]" : "bg-[#e2e5ef]",
                  bar === 1 ? "h-2" : bar === 2 ? "h-3" : bar === 3 ? "h-4" : "h-5"
                ].join(" ")}
              />
            ))}
            <span className="ml-1.5 text-xs font-semibold tabular-nums text-[#535a73]">
              {network.rssi_dbm} dBm
            </span>
          </div>
        </div>

        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#9aa0b5]">
            Canal
          </p>
          <p className="mt-2 text-sm font-semibold tabular-nums text-[#535a73]">
            {channel}
          </p>
        </div>

        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-[#9aa0b5]">
            Avaliação
          </p>
          <SuspicionBadge
            level={network.analysis.suspicion_level}
          />
        </div>

        <motion.span
          className="grid size-9 place-items-center rounded-xl border border-transparent text-[#8b91a7] transition-colors group-hover:border-[#e5e8f2] group-hover:bg-white"
          animate={{ rotate: expanded ? 180 : 0 }}
          transition={shouldReduceMotion ? { duration: 0 } : { duration: animationTokens.duration.fast }}
          aria-hidden="true"
        >
          <ChevronDown size={17} />
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={shouldReduceMotion ? false : { height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={shouldReduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
            transition={{ duration: shouldReduceMotion ? 0 : animationTokens.duration.base, ease: animationTokens.motionEase }}
            className="overflow-hidden"
          >
            <div className="border-t border-[#edf0f6] bg-[linear-gradient(180deg,#fafbff_0%,#f7f8fc_100%)] px-6 py-6">
              <div className="grid grid-cols-3 gap-4 max-[1100px]:grid-cols-1">
                <DetailGroup
                  icon={<ShieldCheck size={17} />}
                  title="Análise"
                  items={[
                    ["Estado", analysisLabel(network)],
                    [
                      "Score",
                      network.analysis.anomaly_score === null
                        ? "—"
                        : formatScore(network.analysis.anomaly_score)
                    ],
                    [
                      "Threshold",
                      network.analysis.threshold === null
                        ? "—"
                        : formatScore(network.analysis.threshold)
                    ],
                    [
                      "Inferência",
                      network.analysis.inference_ms === null
                        ? "—"
                        : `${formatDecimal(network.analysis.inference_ms, 3)} ms`
                    ]
                  ]}
                />

                <DetailGroup
                  icon={<Radio size={17} />}
                  title="Wi-Fi"
                  items={[
                    ["Segurança", network.security_type],
                    ["Qualidade", `${network.link_quality}%`],
                    ["Frequência", `${formatDecimal(network.center_frequency_khz / 1000, 0)} MHz`],
                    ["Beacon interval", `${formatDecimal(network.beacon_interval_ms, 2)} ms`]
                  ]}
                />

                <DetailGroup
                  icon={<CircleGauge size={17} />}
                  title="Contexto"
                  items={[
                    [
                      "Disponível",
                      network.analysis.context_available === null
                        ? "—"
                        : network.analysis.context_available
                          ? "Sim"
                          : "Não"
                    ],
                    ["Resolução", network.analysis.context_resolution ?? "—"],
                    [
                      "Features completas",
                      network.analysis.feature_complete === null
                        ? "—"
                        : network.analysis.feature_complete
                          ? "Sim"
                          : "Não"
                    ],
                    ["Modelo", network.analysis.model_version ?? "—"]
                  ]}
                />
              </div>

              <div className="mt-4 rounded-2xl border border-[#e5e8f2] bg-white p-5 shadow-[0_8px_24px_rgba(35,41,87,0.035)]">
                <div className="flex items-center gap-2 text-[#4859b6]">
                  <Signal size={16} />
                  <p className="text-[10px] font-semibold uppercase tracking-[0.14em]">
                    Interpretação
                  </p>
                </div>
                <p className="mt-2.5 text-sm leading-6 text-[#666d85]">
                  {network.analysis.reason}
                </p>
              </div>

              {network.analysis.features && (
                <div className="mt-4 grid grid-cols-4 gap-3 max-[900px]:grid-cols-2">
                  <FeatureValue
                    label="SSID/BSSID count"
                    value={network.analysis.features.ssid_bssid_count}
                  />
                  <FeatureValue
                    label="BSSID changed"
                    value={network.analysis.features.bssid_changed}
                  />
                  <FeatureValue
                    label="Security changed"
                    value={network.analysis.features.security_changed}
                  />
                  <FeatureValue
                    label="Security strength Δ"
                    value={network.analysis.features.security_strength_delta}
                  />
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </article>
  );
}

function DetailGroup({
  icon,
  title,
  items
}: {
  icon: ReactNode;
  title: string;
  items: Array<[string, string]>;
}) {
  return (
    <div className="rounded-2xl border border-[#e5e8f2] bg-white p-5 shadow-[0_8px_24px_rgba(35,41,87,0.035)]">
      <div className="flex items-center gap-2 text-sm font-semibold text-[#242943]">
        <span className="text-[#5268ce]">
          {icon}
        </span>
        {title}
      </div>

      <dl className="mt-4 space-y-3.5">
        {items.map(([label, value]) => (
          <div
            key={label}
            className="flex items-start justify-between gap-4 border-b border-[#f0f2f7] pb-3 last:border-0 last:pb-0"
          >
            <dt className="text-xs text-[#969caf]">
              {label}
            </dt>
            <dd className="max-w-[65%] break-all text-right text-xs font-semibold text-[#5b6279]">
              {value}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function FeatureValue({
  label,
  value
}: {
  label: string;
  value: number | null;
}) {
  return (
    <div className="rounded-2xl border border-[#e5e8f2] bg-white p-4 shadow-[0_8px_24px_rgba(35,41,87,0.03)]">
      <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#9aa0b5]">
        {label}
      </p>
      <p className="mt-2 text-base font-semibold tabular-nums text-[#343a55]">
        {value === null ? "—" : formatDecimal(value, 3)}
      </p>
    </div>
  );
}
