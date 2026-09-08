import numpy as np
from sklearn.svm import OneClassSVM
from ml.evaluation.anomaly_protocol import to_anomaly_score

def test_ocsvm_can_react_to_feature_constant_in_normal():
    rng = np.random.default_rng(123)
    variable = rng.normal(0, 1, size=500)
    constant = np.zeros(500)
    X = np.column_stack([variable, constant])

    model = OneClassSVM(kernel="rbf", gamma="scale", nu=0.05)
    model.fit(X)

    normal_point = np.array([[0.0, 0.0]])
    event_point = np.array([[0.0, 1.0]])

    normal_score = to_anomaly_score(
        model.decision_function(normal_point),
        higher_is_more_anomalous=False,
    )[0]
    event_score = to_anomaly_score(
        model.decision_function(event_point),
        higher_is_more_anomalous=False,
    )[0]

    assert event_score > normal_score
