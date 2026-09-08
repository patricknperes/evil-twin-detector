export type AutoScanSchedulerState =
  | "stopped"
  | "unsupported_platform"
  | "disabled"
  | "waiting"
  | "scanning"
  | "settings_error"
  | "scan_error";

export interface AutoScanSchedulerStatus {
  status: AutoScanSchedulerState;
  enabled: boolean;
  intervalSeconds: number | null;
  notificationsEnabled: boolean;
  inFlight: boolean;
  nextRunAt: string | null;
  lastStartedAt: string | null;
  lastCompletedAt: string | null;
  lastScanId: string | null;
  lastOutcome: string | null;
  lastError: string | null;
  lastHighCount: number;
  lastNewHighCount: number;
}

export interface AutoScanCompletedEvent {
  scanId: string | null;
  observedAtUtc: string | null;
  totalNetworks: number;
  highCount: number;
  newHighCount: number;
}
