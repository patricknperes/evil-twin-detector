import pandas as pd

from ml.evaluation.source_leakage import (
    source_target,
)


def test_source_target():
    metadata = pd.DataFrame({
        "source_dataset": [
            "mendeley_rogue_ap",
            "zenodo_v2i",
        ]
    })

    target = source_target(
        metadata
    )

    assert target.tolist() == [
        0,
        1,
    ]
