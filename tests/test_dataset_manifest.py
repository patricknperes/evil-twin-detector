from pathlib import Path

from ml.preprocessing.validate_dataset_manifest import validate_manifest


def test_dataset_manifest():
    root = Path(__file__).resolve().parents[1]

    data = validate_manifest(
        root
        / "config"
        / "dataset_manifest.json"
    )

    assert (
        data["manifest_version"]
        == "1.0.0"
    )

    assert len(
        data[
            "approved_experimental_sequence"
        ]
    ) == 6
