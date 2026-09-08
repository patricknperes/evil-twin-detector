from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "implementation_snapshot_step52_v1"

INCLUDED_FILES = {
    "README.md",
    "alembic.ini",
    "requirements-backend.txt",
    "requirements-ml.txt",
    "requirements-packaging.txt",
}

INCLUDED_ROOTS = (
    "backend",
    "config",
    "desktop",
    "frontend",
    "ml",
    "scripts",
    "tests",
)

EXCLUDED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
    "release",
    "build",
    ".git",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".tsbuildinfo",
}

# Generated status/report/config files are deliberately excluded so executing
# validation or collecting real data cannot mutate the implementation digest.
EXCLUDED_RELATIVE_PREFIXES = (
    "config/dataset_manifest.json",
    "config/frontend_toolchain_step47.json",
    "frontend/resources/backend/evil-twin-backend.exe",
    "ml/models/desktop_candidate_v1/ocsvm_v1",
    "ml/models/preprocessing/desktop_candidate_v1_standard_scaler.joblib",
    "ml/models/preprocessing/desktop_candidate_v1_standard_scaler.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _included(project_root: Path, path: Path) -> bool:
    if not path.is_file():
        return False

    relative = path.relative_to(project_root)

    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False

    if path.suffix in EXCLUDED_SUFFIXES:
        return False

    relative_text = relative.as_posix()
    if any(
        relative_text == prefix
        or relative_text.startswith(prefix + "/")
        for prefix in EXCLUDED_RELATIVE_PREFIXES
    ):
        return False

    if relative_text in INCLUDED_FILES:
        return True

    return bool(relative.parts and relative.parts[0] in INCLUDED_ROOTS)


def implementation_files(project_root: str | Path) -> list[Path]:
    root = Path(project_root).resolve()

    # Sort by the canonical POSIX relative path instead of Path's native
    # ordering. WindowsPath comparisons are case-insensitive while PosixPath
    # comparisons are case-sensitive; using Path ordering made the global tree
    # SHA-256 differ across operating systems even when every individual file
    # was byte-identical.
    return sorted(
        (
            path
            for path in root.rglob("*")
            if _included(root, path)
        ),
        key=lambda path: (
            path.relative_to(root)
            .as_posix()
        ),
    )


def compute_implementation_snapshot(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    files = implementation_files(root)

    entries = []
    tree = hashlib.sha256()

    for path in files:
        relative = path.relative_to(root).as_posix()
        digest = sha256_file(path)
        size = path.stat().st_size

        entries.append({
            "path": relative,
            "sha256": digest,
            "size": size,
        })

        tree.update(relative.encode("utf-8"))
        tree.update(b"\0")
        tree.update(digest.encode("ascii"))
        tree.update(b"\0")
        tree.update(str(size).encode("ascii"))
        tree.update(b"\n")

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "implementation_frozen",
        "file_count": len(entries),
        "tree_sha256": tree.hexdigest(),
        "files": entries,
        "exclusions": {
            "raw_or_processed_data": True,
            "reports": True,
            "node_modules_dist_release_build": True,
            "generated_status_files": list(EXCLUDED_RELATIVE_PREFIXES),
        },
    }


def verify_implementation_snapshot(
    project_root: str | Path,
    snapshot_path: str | Path,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    snapshot_path = Path(snapshot_path)
    if not snapshot_path.is_absolute():
        snapshot_path = root / snapshot_path

    if not snapshot_path.exists():
        return {
            "ready": False,
            "status": "implementation_snapshot_missing",
        }

    try:
        expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "ready": False,
            "status": "implementation_snapshot_invalid",
            "reason": type(exc).__name__,
        }

    if expected.get("schema_version") != SCHEMA_VERSION:
        return {
            "ready": False,
            "status": "implementation_snapshot_schema_mismatch",
        }

    current = compute_implementation_snapshot(root)
    expected_files = {
        item["path"]: item
        for item in expected.get("files", [])
    }
    current_files = {
        item["path"]: item
        for item in current["files"]
    }

    added = sorted(set(current_files) - set(expected_files))
    removed = sorted(set(expected_files) - set(current_files))
    changed = sorted(
        path
        for path in set(expected_files) & set(current_files)
        if expected_files[path].get("sha256") != current_files[path].get("sha256")
        or expected_files[path].get("size") != current_files[path].get("size")
    )

    ready = (
        expected.get("tree_sha256") == current["tree_sha256"]
        and not added
        and not removed
        and not changed
    )

    return {
        "ready": ready,
        "status": "ready" if ready else "implementation_snapshot_mismatch",
        "expected_tree_sha256": expected.get("tree_sha256"),
        "current_tree_sha256": current["tree_sha256"],
        "expected_file_count": expected.get("file_count"),
        "current_file_count": current["file_count"],
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--snapshot",
        default="reports/implementation/implementation_snapshot_step52.json",
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()
    snapshot_path = Path(args.snapshot)
    if not snapshot_path.is_absolute():
        snapshot_path = root / snapshot_path

    if args.write:
        snapshot = compute_implementation_snapshot(root)
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(
            json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        result = {
            "ready": True,
            "status": "implementation_snapshot_written",
            "snapshot": str(snapshot_path),
            "tree_sha256": snapshot["tree_sha256"],
            "file_count": snapshot["file_count"],
        }
    else:
        result = verify_implementation_snapshot(root, snapshot_path)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ready") else 8


if __name__ == "__main__":
    raise SystemExit(main())
