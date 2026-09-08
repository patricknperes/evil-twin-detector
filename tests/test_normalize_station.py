from pathlib import Path
import tempfile

import pandas as pd

from ml.preprocessing.normalize_station import normalize_station


def test_station_minimal_directory():
    with tempfile.TemporaryDirectory() as tmp:
        dataset = (
            Path(tmp)
            / "datasets"
        )

        capture_1 = dataset / "1"
        capture_2 = dataset / "2"

        capture_1.mkdir(parents=True)
        capture_2.mkdir(parents=True)

        columns = (
            "Timestamp,type,MAC_timestamp,"
            "rssi,addr1,addr2,addr3,SSID\n"
        )

        (capture_1 / "capture-1.csv").write_text(
            columns
            + "1682624000.0,Dot11Beacon,100,-49,"
            "ff:ff:ff:ff:ff:ff,00:00:00:00:00:03,"
            "00:00:00:00:00:03,b'NETWORK_1'\n"
            + "1682624000.1,Dot11ProbeReq,200,-61,"
            "ff:ff:ff:ff:ff:ff,00:00:00:00:00:02,"
            "ff:ff:ff:ff:ff:ff,b''\n",
            encoding="utf-8",
        )

        (capture_2 / "capture-2.csv").write_text(
            columns
            + "1682625000.0,Dot11ProbeResp,300,-55,"
            "00:00:00:00:00:09,00:00:00:00:00:0a,"
            "00:00:00:00:00:0a,b'NETWORK_2'\n",
            encoding="utf-8",
        )

        output = Path(tmp) / "out"

        summary = normalize_station(
            dataset,
            output,
            output_format="csv",
        )

        assert summary["frames"] == 3
        assert summary["beacons"] == 1
        assert summary["probe_responses"] == 1
        assert summary["probe_requests"] == 1

        df = pd.read_csv(
            output / "station_all_normal.csv",
            dtype={
                "bssid": "string",
                "ap_id": "string",
                "receiver_address": "string",
                "transmitter_address": "string",
            },
        )

        assert len(df) == 3
        assert set(df["label"]) == {0}

        beacon = df[
            df["frame_type"] == "beacon"
        ].iloc[0]

        assert beacon["ssid"] == "NETWORK_1"
        assert (
            beacon["bssid"]
            == "00:00:00:00:00:03"
        )

        request = df[
            df["frame_type"]
            == "probe_request"
        ].iloc[0]

        assert pd.isna(
            request["bssid"]
        )

        response = df[
            df["frame_type"]
            == "probe_response"
        ].iloc[0]

        assert (
            response["bssid"]
            == "00:00:00:00:00:0a"
        )

        assert bool(
            response[
                "addresses_anonymized"
            ]
        )
