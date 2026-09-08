/// <reference types="vite/client" />

import type {
  AutoScanCompletedEvent,
  AutoScanSchedulerStatus
} from "./types/desktop";


declare global {
  interface ImportMetaEnv {
    readonly VITE_API_BASE_URL?: string;
  }

  interface Window {
    evilTwinDesktop?: {
      platform: string;
      desktop: boolean;

      openLocationSettings: () => Promise<{
        ok: boolean;
        reason?: string;
      }>;

      getBackendStatus: () => Promise<{
        backendUrl: string;
        healthUrl: string;
        ready: boolean;
        startedByElectron: boolean;
        pid: number | null;
        mode: string | null;
        stderrTail: string;
      }>;

      getAutoScanSchedulerStatus: () =>
        Promise<AutoScanSchedulerStatus>;

      refreshAutoScanScheduler: () =>
        Promise<AutoScanSchedulerStatus>;

      onAutoScanCompleted: (
        callback: (
          event: AutoScanCompletedEvent
        ) => void
      ) => () => void;

      e2eRunAutoScan?: () => Promise<{
        outcome: string;
        highCount?: number;
        newHighCount?: number;
      }>;
    };
  }
}

export {};
