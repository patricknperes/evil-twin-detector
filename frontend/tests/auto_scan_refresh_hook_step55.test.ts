// @vitest-environment jsdom

import {
  act,
  renderHook,
  waitFor
} from "@testing-library/react";
import {
  describe,
  expect,
  it
} from "vitest";

import {
  useAutoScanRefresh
} from "../src/hooks/useAutoScanRefresh";
import type {
  AutoScanCompletedEvent
} from "../src/types/desktop";

describe(
  "useAutoScanRefresh",
  () => {
    it(
      "preserves the completed event after the automatic refresh finishes",
      async () => {
        let listener:
          (
            event:
              AutoScanCompletedEvent
          ) => void =
            () => undefined;

        Object.defineProperty(
          window,
          "evilTwinDesktop",
          {
            configurable:
              true,
            value: {
              onAutoScanCompleted:
                (
                  callback:
                    (
                      event:
                        AutoScanCompletedEvent
                    ) => void
                ) => {
                  listener =
                    callback;

                  return () =>
                    undefined;
                }
            }
          }
        );

        const event:
          AutoScanCompletedEvent = {
            scanId:
              "step55-scan-1",
            observedAtUtc:
              "2026-09-02T03:00:00Z",
            totalNetworks:
              3,
            highCount:
              1,
            newHighCount:
              1
          };

        const {
          result
        } = renderHook(
          () =>
            useAutoScanRefresh(
              async () =>
                undefined
            )
        );

        act(
          () => {
            listener(
              event
            );
          }
        );

        await waitFor(
          () => {
            expect(
              result.current
                .refreshing
            ).toBe(
              false
            );

            expect(
              result.current
                .lastRefreshAt
            ).not.toBeNull();
          }
        );

        expect(
          result.current.lastEvent
        ).toEqual(
          event
        );

        expect(
          result.current
            .lastRefreshFailed
        ).toBe(
          false
        );
      }
    );
  }
);
