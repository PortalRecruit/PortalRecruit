#!/usr/bin/env python3
"""PortalRecruit quick sanity checks.

This script is intentionally lightweight and safe: it does NOT modify data.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def check(label: str, ok: bool, detail: str = "") -> bool:
    status = "OK" if ok else "FAIL"
    print(f"[{status}] {label}{(' — ' + detail) if detail else ''}")
    return ok


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)

    failures = 0

    # Python
    check("python", True, sys.executable)
    check("cwd", True, str(root))

    # Required env vars (best-effort; names inferred from codebase)
    env_candidates = [
        "OPENAI_API_KEY",
        "SYNERGY_API_KEY",
        "SYNERGY_USERNAME",
        "SYNERGY_PASSWORD",
    ]
    for k in env_candidates:
        if k in os.environ and os.environ.get(k):
            check(f"env:{k}", True, "set")
        else:
            # not necessarily fatal, but warn
            print(f"[WARN] env:{k} not set")

    # Tools
    ffmpeg = shutil.which("ffmpeg")
    check("ffmpeg", ffmpeg is not None, ffmpeg or "not found")

    # Python deps
    try:
        import chromadb  # noqa: F401
        check("import chromadb", True)
    except Exception as e:
        failures += 1
        check("import chromadb", False, str(e))

    try:
        import torch  # noqa: F401
        check("import torch", True)
    except Exception as e:
        failures += 1
        check("import torch", False, str(e))

    try:
        import sentence_transformers  # noqa: F401
        check("import sentence-transformers", True)
    except Exception as e:
        failures += 1
        check("import sentence-transformers", False, str(e))

    # Data paths (non-fatal)
    data_dir = root / "data"
    check("data/ exists", data_dir.exists(), str(data_dir))

    chroma_db = data_dir / "vector_db" / "chroma.sqlite3"
    if chroma_db.exists():
        check("chroma sqlite", True, str(chroma_db))
    else:
        print(f"[WARN] chroma sqlite not found at {chroma_db}")

    # Entry points
    check("run_portalrecruit.py", (root / "run_portalrecruit.py").exists())
    check("streamlit Home.py", (root / "src" / "dashboard" / "Home.py").exists())

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
