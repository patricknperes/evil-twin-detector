from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd


DEFAULT_RATIOS = {
    "train": 0.70,
    "validation": 0.15,
    "test": 0.15,
}


def _stable_hash(value, seed):
    raw = (
        f"{seed}|{value}"
        .encode("utf-8")
    )

    return int(
        hashlib.sha256(
            raw
        ).hexdigest()[:16],
        16,
    )


def choose_split_group_column(
    source_dataset,
):
    """
    Regra por fonte:

    Mendeley:
      usar identidade do AP/BSSID. Há centenas de redes e apenas
      quatro sessões muito desbalanceadas.

    V2I:
      usar session_id/trace. Existe apenas um AP ('ap-n') repetido
      em oito traces, portanto separar por AP tornaria split impossível.

    Futuras coletas:
      usar session_id por padrão.
    """
    if (
        source_dataset
        == "mendeley_rogue_ap"
    ):
        return "network_identity_id"

    if (
        source_dataset
        == "zenodo_v2i"
    ):
        return "session_id"

    return "session_id"


def _assign_groups_greedily(
    group_sizes,
    ratios,
    seed,
):
    split_names = [
        "train",
        "validation",
        "test",
    ]

    total = float(
        group_sizes.sum()
    )

    targets = {
        split: (
            total
            * ratios[split]
        )
        for split in split_names
    }

    assigned = {
        split: 0.0
        for split in split_names
    }

    groups = list(
        group_sizes.items()
    )

    # Grupos maiores primeiro; hash apenas desempata.
    groups.sort(
        key=lambda item: (
            -item[1],
            _stable_hash(
                item[0],
                seed,
            ),
        )
    )

    mapping = {}

    for group_id, size in groups:
        def score(split):
            target = max(
                targets[split],
                1.0,
            )

            return (
                (
                    targets[split]
                    - assigned[split]
                )
                / target
            )

        # Maior déficit proporcional recebe o grupo.
        chosen = max(
            split_names,
            key=lambda split: (
                score(split),
                -_stable_hash(
                    f"{group_id}|{split}",
                    seed,
                ),
            ),
        )

        mapping[group_id] = chosen
        assigned[chosen] += float(
            size
        )

    return mapping


def assign_normal_splits(
    df,
    ratios=None,
    seed=20260831,
):
    if ratios is None:
        ratios = DEFAULT_RATIOS

    result = df.copy()
    result["split"] = pd.NA
    result["split_group_type"] = pd.NA
    result["split_group_id"] = pd.NA

    for source, source_df in (
        result.groupby(
            "source_dataset",
            sort=False,
        )
    ):
        group_column = (
            choose_split_group_column(
                source
            )
        )

        if group_column not in source_df:
            raise ValueError(
                f"{source}: coluna "
                f"{group_column} ausente."
            )

        group_ids = (
            source_df[group_column]
            .astype("string")
        )

        sizes = (
            group_ids
            .value_counts()
        )

        mapping = (
            _assign_groups_greedily(
                sizes,
                ratios,
                seed,
            )
        )

        indexes = source_df.index

        result.loc[
            indexes,
            "split_group_type",
        ] = group_column

        result.loc[
            indexes,
            "split_group_id",
        ] = group_ids.values

        result.loc[
            indexes,
            "split",
        ] = (
            group_ids
            .map(mapping)
            .values
        )

    if result["split"].isna().any():
        raise RuntimeError(
            "Existem linhas sem split."
        )

    return result


def assert_no_group_leakage(df):
    check = (
        df.groupby(
            [
                "source_dataset",
                "split_group_type",
                "split_group_id",
            ],
            dropna=False,
        )["split"]
        .nunique()
    )

    leaking = check[
        check > 1
    ]

    if not leaking.empty:
        raise AssertionError(
            "Data leakage entre splits: "
            f"{len(leaking)} grupo(s)."
        )

    return True


def balance_training_sources(
    train_df,
    source_column="source_dataset",
    seed=20260831,
):
    counts = (
        train_df[
            source_column
        ]
        .value_counts()
    )

    if counts.empty:
        raise ValueError(
            "Treino vazio."
        )

    target = int(
        counts.min()
    )

    parts = []

    for source, group in (
        train_df.groupby(
            source_column,
            sort=True,
        )
    ):
        if len(group) > target:
            sampled = group.sample(
                n=target,
                random_state=seed,
            )
        else:
            sampled = group.copy()

        parts.append(sampled)

    balanced = (
        pd.concat(
            parts,
            ignore_index=True,
        )
        .sample(
            frac=1.0,
            random_state=seed,
        )
        .reset_index(
            drop=True
        )
    )

    return balanced


def split_summary(df):
    rows = []

    grouped = (
        df.groupby(
            [
                "source_dataset",
                "split",
            ],
            dropna=False,
        )
    )

    for (
        source,
        split,
    ), group in grouped:
        rows.append({
            "source_dataset":
                source,
            "split":
                split,
            "rows":
                int(
                    len(group)
                ),
            "split_groups":
                int(
                    group[
                        "split_group_id"
                    ].nunique()
                ),
            "sessions":
                int(
                    group[
                        "session_id"
                    ].nunique()
                ),
            "network_identities":
                int(
                    group[
                        "network_identity_id"
                    ].nunique()
                )
                if (
                    "network_identity_id"
                    in group
                )
                else None,
        })

    return rows
