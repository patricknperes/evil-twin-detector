from pathlib import Path
import tempfile

import pandas as pd

from ml.preprocessing.normalize_longterm import normalize_longterm


def test_longterm_minimal_directory():
    with tempfile.TemporaryDirectory() as tmp:
        dataset = (
            Path(tmp)
            / "UM_DSI_DB_v1.0.0_lite"
        )

        session = (
            dataset
            / "data"
            / "site_surveys"
            / "2019-02-19"
        )

        session.mkdir(parents=True)

        (
            dataset
            / "data"
            / "coords_info.csv"
        ).write_text(
            "1,-53.568360,5.837470\n",
            encoding="utf-8",
        )

        (
            dataset
            / "data"
            / "mds_info.csv"
        ).write_text(
            "rpi-c,-38.066516,"
            "4.728838,2.10\n",
            encoding="utf-8",
        )

        (
            session
            / "timestamps.csv"
        ).write_text(
            "20190219152821980\n"
            "20190219152826557\n",
            encoding="utf-8",
        )

        (
            session
            / "coordinates.csv"
        ).write_text(
            "-53.568360,5.837470,1.00\n"
            "-53.568360,5.837470,1.00\n",
            encoding="utf-8",
        )

        (
            session
            / "rssis.csv"
        ).write_text(
            "10000000:-72,"
            "00000001:-88\n"
            "10000000:-70\n",
            encoding="utf-8",
        )

        (
            session
            / "channels.csv"
        ).write_text(
            "10000000:100,"
            "00000001:6\n"
            "10000000:100\n",
            encoding="utf-8",
        )

        output = Path(tmp) / "out"

        stats = normalize_longterm(
            dataset,
            output,
            collection="site_surveys",
            chunk_size=2,
            output_format="csv",
        )

        assert stats["sessions"] == 1
        assert stats["samples"] == 2
        assert stats["observations"] == 3
        assert stats["unique_aps"] == 2

        df = pd.read_csv(
            output
            / "longterm_all_normal.csv",
            dtype={"ap_id": "string"},
        )

        assert len(df) == 3
        assert set(df["label"]) == {0}
        assert set(
            df["collection_mode"]
        ) == {"site_survey"}

        assert set(
            df["location_id"].dropna()
        ) == {"rp_1"}

        ap = df[
            df["ap_id"].astype(str)
            == "00000001"
        ].iloc[0]

        assert ap["rssi_dbm"] == -88
        assert ap["channel"] == 6
        assert (
            ap["frequency_mhz"]
            == 2437
        )
