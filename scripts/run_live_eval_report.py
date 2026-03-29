"""Prefer: `abgs-run live-eval --run-dir ... --output-dir ...` (see docs/user_guide.md)."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    from abgs.cli import main as cli_main

    sys.argv = [
        "abgs-run",
        "live-eval",
        "--run-dir",
        str(ROOT / "artifacts" / "runs" / "fly_fishing"),
        "--output-dir",
        str(ROOT / "artifacts" / "reports" / "fly_fishing_gemini_claude"),
        "--repo-root",
        str(ROOT),
        *sys.argv[1:],
    ]
    cli_main()


if __name__ == "__main__":
    main()
