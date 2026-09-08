import type {
  NetworkObservation,
  SuspicionLevel
} from "../types/api";

export type NetworkSort =
  | "signal_desc"
  | "signal_asc"
  | "ssid_asc"
  | "suspicion_desc";

const suspicionRank: Record<
  SuspicionLevel,
  number
> = {
  high: 4,
  medium: 3,
  unavailable: 2,
  low: 1
};

export function matchesNetworkQuery(
  network: NetworkObservation,
  query: string
): boolean {
  const normalized = query
    .trim()
    .toLocaleLowerCase("pt-BR");

  if (!normalized) {
    return true;
  }

  return [
    network.ssid,
    network.bssid,
    network.security_type,
    network.phy_type,
    network.analysis.suspicion_level
  ]
    .filter(Boolean)
    .some(value =>
      value
        .toLocaleLowerCase("pt-BR")
        .includes(normalized)
    );
}

export function sortNetworks(
  networks: NetworkObservation[],
  sort: NetworkSort
): NetworkObservation[] {
  return [...networks].sort(
    (left, right) => {
      if (sort === "signal_desc") {
        return right.rssi_dbm - left.rssi_dbm;
      }

      if (sort === "signal_asc") {
        return left.rssi_dbm - right.rssi_dbm;
      }

      if (sort === "ssid_asc") {
        return (
          left.ssid || "SSID não transmitido"
        ).localeCompare(
          right.ssid || "SSID não transmitido",
          "pt-BR",
          {
            sensitivity: "base"
          }
        );
      }

      return (
        suspicionRank[
          right.analysis.suspicion_level
        ]
        - suspicionRank[
          left.analysis.suspicion_level
        ]
      );
    }
  );
}

export function countSuspicion(
  networks: NetworkObservation[]
): Record<
  SuspicionLevel,
  number
> {
  return networks.reduce(
    (accumulator, network) => {
      accumulator[
        network.analysis.suspicion_level
      ] += 1;

      return accumulator;
    },
    {
      low: 0,
      medium: 0,
      high: 0,
      unavailable: 0
    } satisfies Record<
      SuspicionLevel,
      number
    >
  );
}

export function formatFrequency(
  frequencyKHz: number
): string {
  if (!frequencyKHz) {
    return "—";
  }

  return `${(
    frequencyKHz / 1_000_000
  ).toFixed(3)} GHz`;
}

export function formatScore(
  value: number | null
): string {
  if (
    value === null
    || Number.isNaN(value)
  ) {
    return "—";
  }

  if (
    value !== 0
    && Math.abs(value) < 0.00005
  ) {
    return value.toExponential(3);
  }

  return value.toFixed(4);
}
