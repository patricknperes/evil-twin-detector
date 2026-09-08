from ml.evaluation.validate_local_admin_ablation_step12 import (
    validate_step12,
)

def test_local_admin_ablation_step12():
    report = validate_step12()
    assert report["primary_feature"] == "bssid_local_admin_flag"
    assert report["decision"]["status"] == "ablation_only"
