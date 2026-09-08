from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runtime_validation import validate_scan_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Valida um scans.jsonl coletado no Windows."
    )
    parser.add_argument("scans_jsonl")
    parser.add_argument("--json", dest="json_output")
    args = parser.parse_args(argv)

    report = validate_scan_file(args.scans_jsonl)

    if args.json_output:
        path = Path(args.json_output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
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

    return (
        0
        if report["runtime_ready_for_own_normal_collection"]
        else 6
    )


if __name__ == "__main__":
    raise SystemExit(main())
