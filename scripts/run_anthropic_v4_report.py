"""Prefer: `abgs-run live-eval --v4-paths --strategy anthropic_only` (see docs/user_guide.md)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    from abgs.cli import main as cli_main

    argv = ["abgs-run", "live-eval", "--v4-paths", "--strategy", "anthropic_only", "--repo-root", str(ROOT)]
    argv.extend(sys.argv[1:])
    sys.argv = argv
    cli_main()


if __name__ == "__main__":
    main()
