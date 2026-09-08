from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import pandas as pd


DEFAULT_SEED = 20260831

REQUIRED_SPLITS = (
    "reference",
    "model_train",
    "validation",
    "test_normal",
)


def discover_interim_sessions(
    interim_root: str | Path,
) -> list[dict[str, object]]:
    root = Path(
        interim_root
    )

    if not root.exists():
        return []

    sessions = []

    for folder in sorted(
        root.iterdir()
    ):
        if not folder.is_dir():
            continue

        observations = (
            folder
            / "observations.csv.gz"
        )

        manifest_path = (
            folder
            / "import_manifest.json"
        )

        if (
            not observations.exists()
            or not manifest_path.exists()
        ):
            continue

        manifest = json.loads(
            manifest_path.read_text(
                encoding="utf-8"
            )
        )

        frame = pd.read_csv(
            observations,
            nrows=1,
        )

        environment = None

        if (
            "environment"
            in frame.columns
            and len(
                frame
            )
        ):
            environment = (
                None
                if pd.isna(
                    frame.iloc[
                        0
                    ][
                        "environment"
                    ]
                )
                else str(
                    frame.iloc[
                        0
                    ][
                        "environment"
                    ]
                )
            )

        sessions.append({
            "session_id":
                str(
                    manifest[
                        "session_id"
                    ]
                ),
            "environment":
                environment,
            "observations_path":
                str(
                    observations
                ),
            "manifest_path":
                str(
                    manifest_path
                ),
            "rows":
                int(
                    manifest.get(
                        "rows",
                        0,
                    )
                ),
            "runtime_ready":
                bool(
                    manifest.get(
                        "runtime_ready",
                        False,
                    )
                ),
        })

    return sessions


def _deterministic_rank(
    session_id: str,
    seed: int,
) -> str:
    return hashlib.sha256(
        (
            f"{seed}|{session_id}"
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def make_split_plan(
    sessions: list[dict[str, object]],
    *,
    seed: int = DEFAULT_SEED,
) -> dict[str, object]:
    """
    Group-level split only.

    Minimum strict plan:
        >= 5 independent runtime-ready sessions

    Allocation for first five:
        1 reference
        2 model_train
        1 validation
        1 test_normal

    Extra sessions are assigned deterministically in a 2:1:1
    model_train/validation/test_normal cycle. Reference remains frozen at
    one session initially so new data cannot silently alter the historical
    reference after a plan is frozen.
    """
    ready = [
        item
        for item in sessions
        if item.get(
            "runtime_ready"
        )
    ]

    session_ids = [
        str(
            item[
                "session_id"
            ]
        )
        for item in ready
    ]

    if len(
        session_ids
    ) != len(
        set(
            session_ids
        )
    ):
        raise ValueError(
            "session_id duplicado."
        )

    if len(
        ready
    ) < 5:
        return {
            "schema_version":
                "desktop_session_split_plan_v1",
            "seed":
                int(
                    seed
                ),
            "status":
                "insufficient_sessions",
            "minimum_required_sessions":
                5,
            "runtime_ready_sessions":
                len(
                    ready
                ),
            "assignments":
                [],
            "scientific_rule":
                "Split is by session_id only; no row-level random split.",
        }

    ordered = sorted(
        ready,
        key=lambda item:
            _deterministic_rank(
                str(
                    item[
                        "session_id"
                    ]
                ),
                seed,
            ),
    )

    assignments = []

    initial_splits = [
        "reference",
        "model_train",
        "model_train",
        "validation",
        "test_normal",
    ]

    for item, split in zip(
        ordered[
            :5
        ],
        initial_splits,
    ):
        assignments.append({
            **item,
            "split":
                split,
        })

    cycle = [
        "model_train",
        "model_train",
        "validation",
        "test_normal",
    ]

    for index, item in enumerate(
        ordered[
            5:
        ]
    ):
        assignments.append({
            **item,
            "split":
                cycle[
                    index
                    % len(
                        cycle
                    )
                ],
        })

    split_counts = {
        split:
            sum(
                1
                for item in assignments
                if item[
                    "split"
                ] == split
            )
        for split in REQUIRED_SPLITS
    }

    return {
        "schema_version":
            "desktop_session_split_plan_v1",
        "seed":
            int(
                seed
            ),
        "status":
            "ready",
        "minimum_required_sessions":
            5,
        "runtime_ready_sessions":
            len(
                ready
            ),
        "assignments":
            assignments,
        "split_counts":
            split_counts,
        "reference_frozen":
            True,
        "scientific_rules": [
            "No observation-level random split.",
            "A session_id appears in exactly one split.",
            "Reference observations never become anomaly-model training rows.",
            "Validation/test sessions do not update the reference.",
            "Reference remains frozen once this plan is committed.",
        ],
    }


def save_split_plan(
    plan: dict[str, object],
    path: str | Path,
) -> None:
    path = Path(
        path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            plan,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
