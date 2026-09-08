from pathlib import Path
import json
import pandas as pd

EXPECTED = [
    "ssid_bssid_count",
    "bssid_changed",
    "security_changed",
    "security_strength_delta",
    "is_hidden",
]


def validate_step14(project_root="."):
    root=Path(project_root)
    report=json.loads((root/"reports"/"models"/"contextual_core_v2"/"contextual_core_v2_step14.json").read_text(encoding="utf-8"))
    assert report["phase"] == 4
    assert report["step"] == 14
    assert report["profile"]["features"] == EXPECTED
    assert "channel_changed" not in EXPECTED
    for split in ["model_train_normal","validation_normal","test_normal","test_attack_synthetic"]:
        X=pd.read_csv(root/"data"/"processed"/"ml_ready"/"evil_twin_contextual_core_v2"/split/"X.csv.gz")
        assert list(X.columns) == EXPECTED
        assert not X.isna().any().any()
    assert report["operational_candidate"]["not_final"] is True
    return report
