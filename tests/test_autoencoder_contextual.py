import torch

from ml.models.autoencoder_contextual.model import (
    ContextualAutoencoder,
    reconstruction_error,
)


def test_contextual_autoencoder_shape_and_score():
    model = ContextualAutoencoder()

    X = torch.tensor([
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [1.0, 0.0, -1.0, 0.0, 0.0, 0.0],
    ])

    output = model(X)

    assert output.shape == X.shape

    scores = reconstruction_error(
        model,
        X,
    )

    assert scores.shape == (
        2,
    )

    assert torch.isfinite(
        scores
    ).all()
