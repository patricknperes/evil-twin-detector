from __future__ import annotations

import argparse

import uvicorn

from .migrations_runner import upgrade_database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Start local Evil Twin Detector backend."
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
    )
    parser.add_argument(
        "--reload",
        action="store_true",
    )
    args = parser.parse_args(argv)

    upgrade_database()

    uvicorn.run(
        "backend.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
