import {
  ChevronDown,
  ChevronUp,
  CircleGauge,
  Radio,
  ShieldCheck,
  Wifi
} from "lucide-react";
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

export function NetworkScanCard({
  network
}: Props) {
  const [expanded, setExpanded] = useState(false);

  const channel =
    network.ds_parameter_channel
    ?? "—";

  return (
    <article className="border-b border-slate-100 last:border-b-0">
      <button
        type="button"
        className="grid w-full grid-cols-[minmax(0,1fr)_110px_130px_150px_42px] items-center gap-4 px-5 py-4 text-left transition hover:bg-slate-50"
        onClick={() => setExpanded(value => !value)}
        aria-expanded={expanded}
      >
        <div className="min-w-0">
          <div className="flex min-w-0 items-center gap-2">
            <Wifi
              className="shrink-0 text-slate-400"
              size={17}
            />
            <p className="truncate font-medium text-slate-950">
              {network.ssid || "SSID não transmitido"}
            </p>
          </div>
          <p className="mt-1 truncate pl-6 font-mono text-xs text-slate-400">
            {network.bssid}
          </p>
        </div>

        <div>
          <p className="text-xs text-slate-400">
            Sinal
          </p>
          <p className="mt-1 text-sm font-medium text-slate-700">
            {network.rssi_dbm} dBm
          </p>
        </div>

        <div>
          <p className="text-xs text-slate-400">
            Canal
          </p>
          <p className="mt-1 text-sm font-medium text-slate-700">
            {channel}
          </p>
        </div>

        <div>
          <p className="mb-1.5 text-xs text-slate-400">
            Suspeita
          </p>
          <SuspicionBadge
            level={network.analysis.suspicion_level}
          />
        </div>

        <div className="grid size-9 place-items-center rounded-lg text-slate-400">
          {expanded
            ? <ChevronUp size={18} />
            : <ChevronDown size={18} />}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-slate-100 bg-slate-50/60 px-5 py-5">
          <div className="grid grid-cols-3 gap-4">
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

          <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
              Interpretação
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              {network.analysis.reason}
            </p>
          </div>

          {network.analysis.features && (
            <div className="mt-4 grid grid-cols-4 gap-3">
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
      )}
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
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
        <span className="text-slate-400">
          {icon}
        </span>
        {title}
      </div>

      <dl className="mt-4 space-y-3">
        {items.map(([label, value]) => (
          <div
            key={label}
            className="flex items-start justify-between gap-4"
          >
            <dt className="text-xs text-slate-400">
              {label}
            </dt>
            <dd className="max-w-[65%] break-all text-right text-xs font-medium text-slate-700">
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
    <div className="rounded-xl border border-slate-200 bg-white p-3">
      <p className="text-xs text-slate-400">
        {label}
      </p>
      <p className="mt-1.5 font-mono text-sm font-semibold text-slate-800">
        {value === null
          ? "—"
          : formatDecimal(value, 4)}
      </p>
    </div>
  );
}
