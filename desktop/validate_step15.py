from __future__ import annotations

from pathlib import Path
import json


def validate_step15(project_root: str | Path = ".") -> dict:
    root = Path(project_root)
    config = json.loads(
        (root / "config" / "desktop_candidate_v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert config["phase"] == 4
    assert config["step"] == 15
    assert config["profile"] == "desktop_candidate_v1"
    assert config["packet_capture_required"] is False
    assert config["model_reuse"]["reuse_contextual_core_v2_ocsvm"] is False
    assert config["primary_features"] == [
        "ssid_bssid_count",
        "bssid_changed",
        "security_changed",
        "security_strength_delta",
    ]
    assert (
        config["core_v2_mapping"]["is_hidden"]
        == "not_semantically_compatible_use_ssid_not_broadcast_metadata_only"
    )
    return config


if __name__ == "__main__":
    validate_step15()
    print("Fase 4 / Passo 15 validado.")
