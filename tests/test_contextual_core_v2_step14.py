from ml.evaluation.validate_contextual_core_v2_step14 import validate_step14


def test_contextual_core_v2_step14():
    report=validate_step14()
    assert report["status"] == "completed"
    assert report["profile"]["coverage_unchanged"] is True
