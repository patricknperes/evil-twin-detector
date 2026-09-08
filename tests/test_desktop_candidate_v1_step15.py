from desktop.validate_step15 import validate_step15


def test_desktop_candidate_step15_contract():
    config = validate_step15()
    assert config["status"] == "feature_contract_ready_retraining_required"
    assert config["windows_privacy"]["access_denied_handling_required"] is True
    assert (
        config["optional_observable_signals"]["tsf_reference_monotonic_violation"]
        == "technically_observable_but_ablation_only"
    )
