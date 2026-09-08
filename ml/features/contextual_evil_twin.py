from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


SECURITY_STRENGTH = {
    "OPEN": 0,
    "WEP": 1,
    "WPA": 2,
    "WPA2": 3,
    "WPA3": 4,
}

CONTEXTUAL_FEATURES_V1 = [
    "ssid_bssid_count",
    "bssid_changed",
    "channel_changed",
    "security_changed",
    "security_strength_delta",
    "is_hidden",
    "configured_beacon_interval_ms",
]


def _clean_ssid(value):
    if pd.isna(value):
        return None

    text = str(value)

    # SSID é case-sensitive. Não alteramos caixa.
    # Apenas removemos espaços externos acidentais.
    text = text.strip()

    if text == "":
        return None

    return text


def _clean_bssid(value):
    if pd.isna(value):
        return None

    text = str(value).strip().upper()

    if text == "":
        return None

    return text


def _hash_identifier(
    namespace,
    value,
):
    if value is None:
        return None

    raw = (
        f"{namespace}|{value}"
        .encode("utf-8")
    )

    return hashlib.sha256(
        raw
    ).hexdigest()


def hash_ssid(value):
    return _hash_identifier(
        "ssid",
        _clean_ssid(value),
    )


def hash_bssid(value):
    return _hash_identifier(
        "bssid",
        _clean_bssid(value),
    )


def normalize_security(value):
    if pd.isna(value):
        return None

    text = (
        str(value)
        .strip()
        .upper()
    )

    aliases = {
        "OPEN": "OPEN",
        "WEP": "WEP",
        "WPA": "WPA",
        "WPA2": "WPA2",
        "WPA3": "WPA3",
    }

    return aliases.get(
        text,
        "OTHER",
    )


def security_rank(value):
    normalized = normalize_security(
        value
    )

    if normalized is None:
        return np.nan

    return float(
        SECURITY_STRENGTH.get(
            normalized,
            np.nan,
        )
    )


def current_channel(row):
    """
    Para mudança contextual usamos o canal observado da captura.

    advertised_channel continua disponível para experimentos futuros
    de mismatch, mas não entra em evil_twin_contextual_v1.
    """
    value = pd.to_numeric(
        pd.Series(
            [row.get("channel")]
        ),
        errors="coerce",
    ).iloc[0]

    if pd.isna(value):
        return None

    return int(value)


def _bool_as_float(value):
    if pd.isna(value):
        return np.nan

    return float(
        bool(value)
    )


def split_normal_contextual(
    normal_df,
    reference_ratio=0.40,
    model_train_ratio=0.30,
    validation_ratio=0.15,
    test_ratio=0.15,
):
    """
    Split determinístico dentro de cada sessão, ordenado por elapsed_ms.

    reference:
        usado SOMENTE para construir histórico/contexto.

    model_train:
        usado depois para treinar o anomaly model.

    validation/test:
        nunca entram no histórico de referência.

    Isso separa a construção do baseline contextual do treinamento
    estatístico do detector.
    """
    ratios = [
        reference_ratio,
        model_train_ratio,
        validation_ratio,
        test_ratio,
    ]

    if not np.isclose(
        sum(ratios),
        1.0,
    ):
        raise ValueError(
            "As proporções devem somar 1."
        )

    df = normal_df.copy()

    if "session_id" not in df:
        raise ValueError(
            "session_id ausente."
        )

    if "elapsed_ms" not in df:
        raise ValueError(
            "elapsed_ms ausente."
        )

    df["_original_order"] = np.arange(
        len(df)
    )

    parts = []

    for session_id, group in df.groupby(
        "session_id",
        sort=True,
        dropna=False,
    ):
        group = group.sort_values(
            [
                "elapsed_ms",
                "_original_order",
            ],
            na_position="last",
        ).copy()

        n = len(group)

        n_reference = int(
            np.floor(
                n
                * reference_ratio
            )
        )

        n_model_train = int(
            np.floor(
                n
                * model_train_ratio
            )
        )

        n_validation = int(
            np.floor(
                n
                * validation_ratio
            )
        )

        i1 = n_reference
        i2 = i1 + n_model_train
        i3 = i2 + n_validation

        split = np.empty(
            n,
            dtype=object,
        )

        split[:i1] = "reference"
        split[i1:i2] = "model_train"
        split[i2:i3] = "validation"
        split[i3:] = "test_normal"

        group["context_split"] = split

        parts.append(
            group
        )

    result = pd.concat(
        parts,
        ignore_index=True,
    )

    return result.drop(
        columns=[
            "_original_order"
        ]
    )


def build_reference(
    reference_df,
):
    """
    Constrói estado normal usando apenas hashes dos identificadores.

    Nenhum SSID/BSSID cru é armazenado no artefato.
    """
    ssid_profiles = {}
    bssid_to_ssids = defaultdict(
        set
    )

    # Primeiro passe: somente linhas com SSID observável.
    for _, row in reference_df.iterrows():
        ssid_hash = hash_ssid(
            row.get("ssid")
        )
        bssid_hash = hash_bssid(
            row.get("bssid")
        )

        if ssid_hash is None:
            continue

        profile = ssid_profiles.setdefault(
            ssid_hash,
            {
                "bssid_hashes": set(),
                "channels": set(),
                "security_types": set(),
                "security_ranks": [],
                "configured_beacon_intervals_ms": [],
                "hidden_values": [],
                "observations": 0,
            },
        )

        profile[
            "observations"
        ] += 1

        if bssid_hash is not None:
            profile[
                "bssid_hashes"
            ].add(
                bssid_hash
            )

            bssid_to_ssids[
                bssid_hash
            ].add(
                ssid_hash
            )

        channel = current_channel(
            row
        )

        if channel is not None:
            profile[
                "channels"
            ].add(
                channel
            )

        security = normalize_security(
            row.get(
                "security_type"
            )
        )

        if security is not None:
            profile[
                "security_types"
            ].add(
                security
            )

        rank = security_rank(
            row.get(
                "security_type"
            )
        )

        if np.isfinite(
            rank
        ):
            profile[
                "security_ranks"
            ].append(
                float(rank)
            )

        interval = pd.to_numeric(
            pd.Series([
                row.get(
                    "configured_beacon_interval_ms"
                )
            ]),
            errors="coerce",
        ).iloc[0]

        if pd.notna(
            interval
        ):
            profile[
                "configured_beacon_intervals_ms"
            ].append(
                float(interval)
            )

        hidden = row.get(
            "is_hidden"
        )

        if not pd.isna(
            hidden
        ):
            profile[
                "hidden_values"
            ].append(
                bool(hidden)
            )

    # Segundo passe: linhas sem SSID podem contribuir se o BSSID
    # resolve de forma inequívoca para um SSID conhecido.
    for _, row in reference_df.iterrows():
        if hash_ssid(
            row.get("ssid")
        ) is not None:
            continue

        bssid_hash = hash_bssid(
            row.get("bssid")
        )

        if bssid_hash is None:
            continue

        candidates = bssid_to_ssids.get(
            bssid_hash,
            set(),
        )

        if len(
            candidates
        ) != 1:
            continue

        ssid_hash = next(
            iter(
                candidates
            )
        )

        profile = ssid_profiles[
            ssid_hash
        ]

        channel = current_channel(
            row
        )

        if channel is not None:
            profile[
                "channels"
            ].add(
                channel
            )

        security = normalize_security(
            row.get(
                "security_type"
            )
        )

        if security is not None:
            profile[
                "security_types"
            ].add(
                security
            )

        rank = security_rank(
            row.get(
                "security_type"
            )
        )

        if np.isfinite(
            rank
        ):
            profile[
                "security_ranks"
            ].append(
                float(rank)
            )

    serialized_profiles = {}

    for ssid_hash, profile in (
        ssid_profiles.items()
    ):
        ranks = profile[
            "security_ranks"
        ]

        intervals = profile[
            "configured_beacon_intervals_ms"
        ]

        serialized_profiles[
            ssid_hash
        ] = {
            "bssid_hashes": sorted(
                profile[
                    "bssid_hashes"
                ]
            ),
            "channels": sorted(
                profile[
                    "channels"
                ]
            ),
            "security_types": sorted(
                profile[
                    "security_types"
                ]
            ),
            "security_rank_median": (
                float(
                    np.median(
                        ranks
                    )
                )
                if ranks
                else None
            ),
            "configured_beacon_interval_median_ms": (
                float(
                    np.median(
                        intervals
                    )
                )
                if intervals
                else None
            ),
            "observations": int(
                profile[
                    "observations"
                ]
            ),
        }

    return {
        "version":
            "1.0.0",
        "identifier_storage":
            "sha256 only",
        "ssid_profiles":
            serialized_profiles,
        "bssid_to_ssids": {
            bssid_hash: sorted(
                ssids
            )
            for bssid_hash, ssids
            in bssid_to_ssids.items()
        },
    }


def resolve_context(
    row,
    reference,
):
    ssid_hash = hash_ssid(
        row.get("ssid")
    )

    bssid_hash = hash_bssid(
        row.get("bssid")
    )

    profiles = reference[
        "ssid_profiles"
    ]

    if (
        ssid_hash is not None
        and ssid_hash in profiles
    ):
        return {
            "context_available":
                True,
            "context_resolution":
                "ssid",
            "resolved_ssid_hash":
                ssid_hash,
            "ssid_hash":
                ssid_hash,
            "bssid_hash":
                bssid_hash,
        }

    if bssid_hash is not None:
        candidates = reference[
            "bssid_to_ssids"
        ].get(
            bssid_hash,
            [],
        )

        if len(
            candidates
        ) == 1:
            resolved = candidates[
                0
            ]

            return {
                "context_available":
                    True,
                "context_resolution":
                    "bssid_fallback",
                "resolved_ssid_hash":
                    resolved,
                "ssid_hash":
                    ssid_hash,
                "bssid_hash":
                    bssid_hash,
            }

    return {
        "context_available":
            False,
        "context_resolution":
            "none",
        "resolved_ssid_hash":
            None,
        "ssid_hash":
            ssid_hash,
        "bssid_hash":
            bssid_hash,
    }


def transform_contextual(
    df,
    reference,
):
    """
    Gera somente features derivadas de campos reais.

    label/attack_type são carregados como metadados para avaliação,
    mas nunca participam dos cálculos das features.
    """
    rows = []

    for _, row in df.iterrows():
        context = resolve_context(
            row,
            reference,
        )

        profile = (
            reference[
                "ssid_profiles"
            ].get(
                context[
                    "resolved_ssid_hash"
                ]
            )
            if context[
                "context_available"
            ]
            else None
        )

        bssid_hash = context[
            "bssid_hash"
        ]

        channel = current_channel(
            row
        )

        security = normalize_security(
            row.get(
                "security_type"
            )
        )

        current_rank = security_rank(
            row.get(
                "security_type"
            )
        )

        interval = pd.to_numeric(
            pd.Series([
                row.get(
                    "configured_beacon_interval_ms"
                )
            ]),
            errors="coerce",
        ).iloc[0]

        is_hidden = _bool_as_float(
            row.get(
                "is_hidden"
            )
        )

        if profile is None:
            ssid_bssid_count = np.nan
            bssid_changed = np.nan
            channel_changed = np.nan
            security_changed = np.nan
            security_delta = np.nan
            interval_delta = np.nan
        else:
            known_bssids = set(
                profile[
                    "bssid_hashes"
                ]
            )

            known_channels = set(
                profile[
                    "channels"
                ]
            )

            known_security = set(
                profile[
                    "security_types"
                ]
            )

            ssid_bssid_count = float(
                len(
                    known_bssids
                )
            )

            bssid_changed = (
                float(
                    bssid_hash
                    not in known_bssids
                )
                if bssid_hash
                is not None
                else np.nan
            )

            channel_changed = (
                float(
                    channel
                    not in known_channels
                )
                if (
                    channel
                    is not None
                    and known_channels
                )
                else np.nan
            )

            security_changed = (
                float(
                    security
                    not in known_security
                )
                if (
                    security
                    is not None
                    and known_security
                )
                else np.nan
            )

            baseline_rank = profile[
                "security_rank_median"
            ]

            security_delta = (
                float(
                    current_rank
                    - baseline_rank
                )
                if (
                    baseline_rank
                    is not None
                    and np.isfinite(
                        current_rank
                    )
                )
                else np.nan
            )

            baseline_interval = profile[
                "configured_beacon_interval_median_ms"
            ]

            interval_delta = (
                float(
                    interval
                    - baseline_interval
                )
                if (
                    baseline_interval
                    is not None
                    and pd.notna(
                        interval
                    )
                )
                else np.nan
            )

        feature_values = {
            "ssid_bssid_count":
                ssid_bssid_count,
            "bssid_changed":
                bssid_changed,
            "channel_changed":
                channel_changed,
            "security_changed":
                security_changed,
            "security_strength_delta":
                security_delta,
            "is_hidden":
                is_hidden,
            "configured_beacon_interval_ms":
                (
                    float(
                        interval
                    )
                    if pd.notna(
                        interval
                    )
                    else np.nan
                ),
        }

        feature_complete = all(
            pd.notna(
                value
            )
            for value in (
                feature_values.values()
            )
        )

        rows.append({
            "source_dataset":
                row.get(
                    "source_dataset"
                ),
            "session_id":
                row.get(
                    "session_id"
                ),
            "elapsed_ms":
                row.get(
                    "elapsed_ms"
                ),
            "ssid_hash":
                context[
                    "ssid_hash"
                ],
            "bssid_hash":
                context[
                    "bssid_hash"
                ],
            "context_available":
                bool(
                    context[
                        "context_available"
                    ]
                ),
            "context_resolution":
                context[
                    "context_resolution"
                ],
            "feature_complete":
                bool(
                    feature_complete
                ),
            "ssid_missing":
                float(
                    _clean_ssid(
                        row.get(
                            "ssid"
                        )
                    )
                    is None
                ),
            "configured_beacon_interval_delta_ms":
                interval_delta,
            "label":
                row.get(
                    "label"
                ),
            "attack_type":
                row.get(
                    "attack_type"
                ),
            "is_synthetic":
                row.get(
                    "is_synthetic"
                ),
            **feature_values,
        })

    result = pd.DataFrame(
        rows
    )

    return result


def save_reference(
    reference,
    path,
):
    path = Path(
        path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            reference,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def load_reference(
    path,
):
    return json.loads(
        Path(
            path
        ).read_text(
            encoding="utf-8"
        )
    )
