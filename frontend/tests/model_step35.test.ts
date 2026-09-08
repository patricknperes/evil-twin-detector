import {
  describe,
  expect,
  it
} from "vitest";

import {
  activeModel,
  artifactViews,
  shortFingerprint
} from "../src/lib/modelUi";
import type {
  HistoryModelVersion,
  ModelArtifactStatusResponse
} from "../src/types/api";

const status: ModelArtifactStatusResponse = {
  status: "not_ready",
  feature_set: [
    "ssid_bssid_count",
    "bssid_changed",
    "security_changed",
    "security_strength_delta"
  ],
  reference_path: "reference.json",
  scaler_path: "scaler.joblib",
  model_path: "model.joblib",
  threshold_path: "threshold.json",
  missing_artifacts: [
    "model",
    "threshold"
  ],
  message: "fixture"
};

function version(
  id: number,
  isActive: boolean
): HistoryModelVersion {
  return {
    model_version_id: id,
    version_name: `model-${id}`,
    algorithm: "OneClassSVM",
    feature_set_name: "desktop_candidate_v1",
    reference_sha256: "a".repeat(64),
    scaler_sha256: "b".repeat(64),
    model_sha256: "c".repeat(64),
    threshold_sha256: "d".repeat(64),
    threshold: 0.5,
    active: isActive,
    created_at_utc: "2026-08-31T12:00:00Z",
    notes: null,
    detection_count: 3
  };
}

describe(
  "model UI helpers",
  () => {
    it(
      "maps all four frozen artifacts",
      () => {
        const artifacts =
          artifactViews(
            status
          );

        expect(
          artifacts
        ).toHaveLength(4);

        expect(
          artifacts.find(
            item =>
              item.key
              === "reference"
          )?.available
        ).toBe(true);

        expect(
          artifacts.find(
            item =>
              item.key
              === "model"
          )?.available
        ).toBe(false);
      }
    );

    it(
      "finds the active model version",
      () => {
        expect(
          activeModel([
            version(
              1,
              false
            ),
            version(
              2,
              true
            )
          ])?.model_version_id
        ).toBe(2);
      }
    );

    it(
      "shortens a fingerprint only for presentation",
      () => {
        expect(
          shortFingerprint(
            "a".repeat(
              64
            )
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
  }
);
