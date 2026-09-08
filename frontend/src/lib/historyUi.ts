import type {
  HistoryDetectionSummary,
  SuspicionLevel
} from "../types/api";

export type DetectionDecisionFilter =
  | "all"
  | "anomaly"
  | "normal"
  | "insufficient";

export function shortHash(
  value: string | null,
  visible = 12
): string {
  if (!value) {
    return "—";
  }

  if (
    value.length
    <= visible * 2 + 1
  ) {
    return value;
  }

  return `${value.slice(
    0,
    visible
  )}…${value.slice(
    -visible
  )}`;
}

export function decisionLabel(
  detection:
    HistoryDetectionSummary
): string {
  if (
    detection.is_anomaly
    === true
  ) {
    return "Anomalia";
  }

  if (
    detection.is_anomaly
    === false
  ) {
    return "Dentro do esperado";
  }

  return "Histórico insuficiente";
}

export function decisionQuery(
  value:
    DetectionDecisionFilter
): boolean | null | undefined {
  if (
    value
    === "anomaly"
  ) {
    return true;
  }

  if (
    value
    === "normal"
  ) {
    return false;
  }

  return undefined;
}

export function matchesDecisionFilter(
  detection:
    HistoryDetectionSummary,
  value:
    DetectionDecisionFilter
): boolean {
  if (
    value === "all"
  ) {
    return true;
  }

  if (
    value === "anomaly"
  ) {
    return (
      detection.is_anomaly
      === true
    );
  }

  if (
    value === "normal"
  ) {
    return (
      detection.is_anomaly
      === false
    );
  }

  return (
    detection.is_anomaly
    === null
  );
}

export function suspicionText(
  value: SuspicionLevel
): string {
  return {
    low:
      "Baixa suspeita",
    medium:
      "Média suspeita",
    high:
      "Alta suspeita",
    unavailable:
      "Indisponível"
  }[
    value
  ];
}
