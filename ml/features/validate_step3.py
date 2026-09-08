from pathlib import Path
import json

import pandas as pd


def validate_step3():
    root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    manifest = json.loads(
        (
            root
            / "data"
            / "processed"
            / "feature_manifest.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert manifest[
        "phase"
    ] == 3

    assert manifest[
        "step"
    ] == 3

    assert (
        manifest["profiles"][
            "PROFILE_BEACON_1S"
        ]["files"][
            "v2i_normal"
        ]["rows"]
        == 14812
    )

    path = (
        root
        / "data"
        / "processed"
        / "profile_beacon_1s"
        / "mendeley_normal.csv.gz"
    )

    df = pd.read_csv(
        path
    )

    forbidden = {
        "ssid",
        "bssid",
        "ap_id",
    }

    assert not (
        forbidden
        & set(
            df.columns
        )
    )

    assert (
        "network_group_id"
        in df.columns
    )

    print(
        "Fase 3 / Passo 3 "
        "validado com sucesso."
    )


if __name__ == "__main__":
    validate_step3()
