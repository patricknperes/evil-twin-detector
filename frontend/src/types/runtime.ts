import type { HealthResponse } from "./api";
import type { AutoScanSchedulerStatus } from "./desktop";

export type BackendConnectionState = "connecting" | "connected" | "reconnecting" | "disconnected";

export interface RuntimeStatusSnapshot {
  connection: BackendConnectionState;
  health: HealthResponse | null;
  scheduler: AutoScanSchedulerStatus | null;
  refreshIntervalSeconds: number;
  consecutiveFailures: number;
  lastCheckedAt: string | null;
  lastConnectedAt: string | null;
  recoveredAt: string | null;
  checking: boolean;
  desktop: boolean;
}
