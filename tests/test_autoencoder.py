import torch

from ml.models.autoencoder.model import (
    Autoencoder,
    reconstruction_error,
)


def test_autoencoder_shape_and_score():
    model = Autoencoder()

    X = torch.tensor([
        [0.0, 0.0],
        [1.0, -1.0],
    ])

    output = model(
        X
    )

    assert output.shape == X.shape

    score = (
        reconstruction_error(
            model,
            X,
        )
    )

    assert score.shape == (
        2,
    )

    assert torch.isfinite(
        score
    ).all()
