"""One-time helper to stop tracking local runtime artefacts already in Git.

.gitignore prevents new files from being added, but it cannot untrack files that
were committed previously. This script only changes the Git index; it does not
delete the local .venv or cache files from disk.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    try:
        tracked = subprocess.run(
            ["git", "ls-files"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    except Exception as exc:
        print(f"Could not inspect Git index: {exc}", file=sys.stderr)
        return 1

    unwanted = [
        path for path in tracked
        if path == ".venv"
        or path.startswith(".venv/")
        or path.startswith(".venv.incompatible-")
        or path.startswith(".pytest_cache/")
        or "/__pycache__/" in f"/{path}"
        or path.endswith((".pyc", ".pyo"))
    ]
    if not unwanted:
        print("No tracked .venv / Python cache files were found.")
        return 0

    print(f"Stopping Git tracking for {len(unwanted)} local runtime files...")
    chunk_size = 100
    for start in range(0, len(unwanted), chunk_size):
        chunk = unwanted[start:start + chunk_size]
        result = subprocess.run(
            ["git", "rm", "--cached", "--ignore-unmatch", "--", *chunk],
            cwd=repo,
        )
        if result.returncode != 0:
            return result.returncode

    print("\nDone. Your local files remain on disk.")
    print("Review with: git status")
    print("Then commit the removals from Git tracking when satisfied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
