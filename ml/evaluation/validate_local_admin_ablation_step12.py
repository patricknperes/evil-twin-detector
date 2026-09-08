from pathlib import Path
import json

def validate_step12(project_root="."):
    root = Path(project_root)
    report = json.loads(
        (
            root/"reports"/"features"/"local_admin_ablation_v1"/
            "local_admin_ablation_step12.json"
        ).read_text(encoding="utf-8")
    )
    assert report["phase"] == 4
    assert report["step"] == 12
    assert report["status"] == "ablation_only_not_promoted"
    assert report["generator_audit"]["all_source_rows_recovered"] is True
    assert report["decision"]["promote_to_contextual_full_v1"] is False
    return report

if __name__ == "__main__":
    validate_step12()
    print("Fase 4 / Passo 12 validado.")
