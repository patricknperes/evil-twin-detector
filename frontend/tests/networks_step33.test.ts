import {
  describe,
  expect,
  it
} from "vitest";

import {
  countSuspicion,
  formatScore,
  matchesNetworkQuery,
  sortNetworks
} from "../src/lib/networkUi";
import type {
  NetworkObservation
} from "../src/types/api";

function network(
  overrides:
    Partial<NetworkObservation>
    & Pick<
      NetworkObservation,
      "network_id"
      | "ssid"
      | "bssid"
      | "rssi_dbm"
    >
): NetworkObservation {
  return {
    interface_guid: "{TEST}",
    ssid_not_broadcast: false,
    link_quality: 80,
    beacon_interval_ms: 102.4,
    tsf_us: 1,
    host_timestamp_100ns: 1,
    center_frequency_khz: 2437000,
    ds_parameter_channel: 6,
    security_type: "WPA2_OR_NEWER",
    security_strength: 3,
    security_source: "rsn",
    phy_type: "ht",
    bss_type: "infrastructure",
    supported_rates_mbps: [],
    analysis: {
      status: "ready",
      anomaly_score: 0.1,
      threshold: 0.5,
      is_anomaly: false,
      suspicion_level: "low",
      context_available: true,
      context_resolution: "ssid_hash",
      feature_complete: true,
      features: null,
      model_version: "fixture",
      inference_ms: 0.1,
      reason: "fixture"
    },
    ...overrides
  };
}

describe(
  "networks UI helpers",
  () => {
    const low = network({
      network_id: "low",
      ssid: "Casa",
      bssid: "00:00:00:00:00:01",
      rssi_dbm: -40
    });

    const high = network({
      network_id: "high",
      ssid: "Laboratorio",
      bssid: "00:00:00:00:00:02",
      rssi_dbm: -80,
      analysis: {
        ...low.analysis,
        suspicion_level: "high",
        is_anomaly: true
      }
    });

    it(
      "searches by SSID and BSSID",
      () => {
        expect(
          matchesNetworkQuery(
            low,
            "casa"
          )
        ).toBe(true);

        expect(
          matchesNetworkQuery(
            high,
            "00:02"
          )
        ).toBe(true);
      }
    );

    it(
      "sorts signal strongest first",
      () => {
        expect(
          sortNetworks(
            [high, low],
            "signal_desc"
          )[0].network_id
        ).toBe("low");
      }
    );

    it(
      "sorts high suspicion first",
      () => {
        expect(
          sortNetworks(
            [low, high],
            "suspicion_desc"
          )[0].network_id
        ).toBe("high");
      }
    );

    it(
      "counts suspicion levels",
      () => {
        expect(
          countSuspicion(
            [low, high]
          )
        ).toEqual({
          low: 1,
          medium: 0,
          high: 1,
          unavailable: 0
        });
      }
    );

    it(
      "formats very small scientific scores without rounding them to zero",
      () => {
        expect(
          formatScore(
            3.2659592363870615e-8
          )
        ).toBe("3.266e-8");

        expect(
          formatScore(0.913437)
        ).toBe("0.9134");

        expect(
          formatScore(0)
        ).toBe("0.0000");

        expect(
          formatScore(null)
        ).toBe("\u2014");
      }
    );
  }
);
