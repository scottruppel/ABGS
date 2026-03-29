from __future__ import annotations

import os
from pathlib import Path


def load_local_env(start_dir: str | Path | None = None, *, override: bool = False) -> None:
    """Load repo-root `.env` into `os.environ`.

    By default, existing environment variables win (`setdefault`). Pass ``override=True``
    so values from `.env` replace them—useful when the shell has a stale API key.
    """
    search_root = Path(start_dir or Path.cwd()).resolve()
    candidates = [search_root / ".env", search_root.parent / ".env"]

    for candidate in candidates:
        if not candidate.exists():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if override:
                os.environ[key] = value
            else:
                os.environ.setdefault(key, value)
        break
