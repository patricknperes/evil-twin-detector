import {
  useEffect,
  useRef,
  useState
} from "react";

import type {
  AutoScanCompletedEvent
} from "../types/desktop";

export interface AutoScanRefreshState {
  supported: boolean;
  refreshing: boolean;
  lastEvent: AutoScanCompletedEvent | null;
  lastRefreshAt: string | null;
  lastRefreshFailed: boolean;
}

export function useAutoScanRefresh(
  onRefresh: (
    event: AutoScanCompletedEvent
  ) => Promise<void>
): AutoScanRefreshState {
  const callbackRef = useRef(
    onRefresh
  );

  const inFlightRef = useRef(
    false
  );

  const pendingRef = useRef<
    AutoScanCompletedEvent
    | null
  >(
    null
  );

  const mountedRef = useRef(
    true
  );

  const [state, setState] =
    useState<AutoScanRefreshState>({
      supported:
        Boolean(
          window
            .evilTwinDesktop
            ?.onAutoScanCompleted
        ),
      refreshing:
        false,
      lastEvent:
        null,
      lastRefreshAt:
        null,
      lastRefreshFailed:
        false
    });

  useEffect(
    () => {
      callbackRef.current =
        onRefresh;
    },
    [onRefresh]
  );

  useEffect(
    () => {
      mountedRef.current =
        true;

      const subscribe =
        window
          .evilTwinDesktop
          ?.onAutoScanCompleted;

      if (!subscribe) {
        return () => {
          mountedRef.current =
            false;
        };
      }

      async function drain(
        firstEvent:
          AutoScanCompletedEvent
      ) {
        if (inFlightRef.current) {
          pendingRef.current =
            firstEvent;
          return;
        }

        inFlightRef.current =
          true;

        let current:
          AutoScanCompletedEvent
          | null =
            firstEvent;

        while (
          current
          && mountedRef.current
        ) {
          const refreshEvent =
            current;

          pendingRef.current =
            null;

          setState(
            previous => ({
              ...previous,
              refreshing:
                true,
              lastRefreshFailed:
                false
            })
          );

          try {
            await callbackRef
              .current(
                refreshEvent
              );

            if (mountedRef.current) {
              setState(
                previous => ({
                  ...previous,
                  lastEvent:
                    refreshEvent,
                  lastRefreshAt:
                    new Date()
                      .toISOString(),
                  lastRefreshFailed:
                    false
                })
              );
            }
          } catch {
            if (mountedRef.current) {
              setState(
                previous => ({
                  ...previous,
                  lastRefreshFailed:
                    true
                })
              );
            }
          }

          current =
            pendingRef.current;
        }

        inFlightRef.current =
          false;

        if (mountedRef.current) {
          setState(
            previous => ({
              ...previous,
              refreshing:
                false
            })
          );
        }
      }

      const unsubscribe =
        subscribe(
          event => {
            void drain(event);
          }
        );

      return () => {
        mountedRef.current =
          false;
        pendingRef.current =
          null;
        unsubscribe();
      };
    },
    []
  );

  return state;
}
