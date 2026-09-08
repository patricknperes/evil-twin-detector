import {
  describe,
  expect,
  it
} from "vitest";

import {
  decisionLabel,
  matchesDecisionFilter,
  shortHash
} from "../src/lib/historyUi";
import type {
  HistoryDetectionSummary
} from "../src/types/api";

function detection(
  isAnomaly:
    boolean
    | null
): HistoryDetectionSummary {
  return {
    detection_id: 1,
    scan_id: "scan",
    observation_id: 1,
    model_version_id: 1,
    anomaly_score:
      isAnomaly === null
        ? null
        : 0.1,
    threshold:
      isAnomaly === null
        ? null
        : 0.5,
    is_anomaly:
      isAnomaly,
    suspicion_level:
      isAnomaly === true
        ? "high"
        : isAnomaly === false
          ? "low"
          : "unavailable",
    reason: "fixture",
    inference_ms: 0.1,
    created_at_utc:
      "2026-08-31T12:00:00Z"
  };
}

describe(
  "history UI helpers",
  () => {
    it(
      "shortens persisted hashes without pretending to recover identifiers",
      () => {
        const value =
          "a".repeat(
            64
          );

        expect(
          shortHash(
            value
          )
        ).toBe(
          `${"a".repeat(
            12
          )}…${"a".repeat(
            12
          )}`
        );
      }
    );

    it(
      "keeps insufficient history separate from anomaly and normal",
      () => {
        expect(
          decisionLabel(
            detection(
              null
            )
          )
        ).toBe(
          "Histórico insuficiente"
        );

        expect(
          matchesDecisionFilter(
            detection(
              null
            ),
            "insufficient"
          )
        ).toBe(true);
      }
    );

    it(
      "labels anomaly and expected behavior separately",
      () => {
        expect(
          decisionLabel(
            detection(
              true
            )
          )
        ).toBe(
          "Anomalia"
        );

        expect(
          decisionLabel(
            detection(
              false
            )
          )
        ).toBe(
          "Dentro do esperado"
        );
      }
    );
  }
);
