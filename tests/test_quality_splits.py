import pandas as pd

from ml.datasets.quality import (
    add_temporal_quality_flags,
)
from ml.datasets.splits import (
    assign_normal_splits,
    assert_no_group_leakage,
    balance_training_sources,
)


def test_temporal_quality_flags():
    df = pd.DataFrame({
        "rssi_mean_dbm": [-60, -200],
        "rssi_min_dbm": [-65, -205],
        "rssi_max_dbm": [-55, -190],
        "rssi_std_db": [2, 5],
        "rssi_delta_db": [1, 3],
        "window_count": [3, 3],
    })

    result = (
        add_temporal_quality_flags(
            df
        )
    )

    assert bool(
        result.loc[
            0,
            "q_temporal_rich",
        ]
    )

    assert not bool(
        result.loc[
            1,
            "q_temporal_rich",
        ]
    )


def test_split_has_no_group_leakage():
    rows = []

    for source in [
        "mendeley_rogue_ap",
        "zenodo_v2i",
    ]:
        for group_index in range(12):
            for row_index in range(3):
                rows.append({
                    "source_dataset":
                        source,
                    "session_id":
                        (
                            f"trace_{group_index}"
                            if source
                            == "zenodo_v2i"
                            else "session_001"
                        ),
                    "network_identity_id":
                        f"net_{group_index}",
                    "value":
                        row_index,
                })

    df = pd.DataFrame(rows)

    split = assign_normal_splits(
        df
    )

    assert_no_group_leakage(
        split
    )

    assert set(
        split["split"]
    ) == {
        "train",
        "validation",
        "test",
    }


def test_balance_only_training_sources():
    train = pd.DataFrame({
        "source_dataset":
            ["a"] * 10
            + ["b"] * 4,
        "value":
            list(range(14)),
    })

    balanced = (
        balance_training_sources(
            train,
            seed=1,
        )
    )

    counts = (
        balanced[
            "source_dataset"
        ].value_counts()
    )

    assert counts["a"] == 4
    assert counts["b"] == 4
