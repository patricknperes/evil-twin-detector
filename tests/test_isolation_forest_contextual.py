import numpy as np

from sklearn.ensemble import (
    IsolationForest,
)


def test_iforest_does_not_split_constant_feature():
    rng = np.random.default_rng(
        42
    )

    variable = rng.normal(
        size=500
    )

    constant = np.zeros(
        500
    )

    X = np.column_stack([
        variable,
        constant,
    ])

    model = IsolationForest(
        n_estimators=50,
        random_state=42,
    )

    model.fit(
        X
    )

    used = set()

    for estimator in model.estimators_:
        for feature in (
            estimator.tree_.feature
        ):
            if feature >= 0:
                used.add(
                    int(
                        feature
                    )
                )

    assert 0 in used
    assert 1 not in used
