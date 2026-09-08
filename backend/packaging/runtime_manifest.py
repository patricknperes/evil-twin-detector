from __future__ import annotations

import argparse
import json
from pathlib import Path


RUNTIME_ARTIFACTS = {
    "reference":
        Path(
            "data/processed/desktop_candidate_v1/"
            "desktop_normal_reference.json"
        ),
    "scaler":
        Path(
            "ml/models/preprocessing/"
            "desktop_candidate_v1_standard_scaler.joblib"
        ),
    "model":
        Path(
            "ml/models/desktop_candidate_v1/ocsvm_v1/"
            "one_class_svm_desktop_candidate_v1.joblib"
        ),
    "threshold":
        Path(
            "ml/models/desktop_candidate_v1/ocsvm_v1/"
            "threshold.json"
        ),
}


REQUIRED_STATIC_RESOURCES = {
    "alembic_ini":
        Path(
            "alembic.ini"
        ),
    "migrations":
        Path(
            "backend/migrations"
        ),
    "backend_api_config":
        Path(
            "config/backend_local_api.json"
        ),
    "application_settings_config":
        Path(
            "config/application_settings_v1.json"
        ),
}


def inspect_packaging_inputs(
    project_root:
        str
        | Path,
) -> dict[
    str,
    object,
]:
    root = Path(
        project_root
    ).resolve()

    static = {
        name: {
            "relative_path":
                str(
                    relative
                ),
            "exists":
                (
                    root
                    / relative
                ).exists(),
        }
        for name, relative
        in REQUIRED_STATIC_RESOURCES.items()
    }

    scientific = {
        name: {
            "relative_path":
                str(
                    relative
                ),
            "exists":
                (
                    root
                    / relative
                ).exists(),
        }
        for name, relative
        in RUNTIME_ARTIFACTS.items()
    }

    return {
        "schema_version":
            "backend_packaging_inputs_v1",
        "project_root":
            str(
                root
            ),
        "static_resources":
            static,
        "scientific_artifacts":
            scientific,
        "static_ready":
            all(
                item["exists"]
                for item
                in static.values()
            ),
        "scientific_ready":
            all(
                item["exists"]
                for item
                in scientific.values()
            ),
    }


def main(
    argv:
        list[str]
        | None = None,
) -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--project-root",
        default=".",
    )

    parser.add_argument(
        "--allow-missing-scientific-artifacts",
        action="store_true",
    )

    parser.add_argument(
        "--json-output",
    )

    args = parser.parse_args(
        argv
    )

    report = (
        inspect_packaging_inputs(
            args.project_root
        )
    )

    if args.json_output:
        destination = Path(
            args.json_output
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
    )

    if not report["static_ready"]:
        return 2

    if (
        not report["scientific_ready"]
        and not args
        .allow_missing_scientific_artifacts
    ):
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
