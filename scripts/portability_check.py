"""Check the shared PsyCoLab checkout for machine-specific artefacts.

This is intentionally conservative. Runtime data/workspace files are outside the
repository and local preferences/logs are ignored by Git.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_TRACKED_PREFIXES = (
    ".venv/",
    ".vscode/",
    ".pytest_cache/",
    ".psycolab_logs/",
)

TEXT_SCAN_DIRS = (
    ROOT / "src",
    ROOT / "Events",
    ROOT / "Experiments",
    ROOT / "Functions",
    ROOT / "Interface",
    ROOT / "scripts",
    ROOT / "configs",
)

ROOT_TEXT_FILES = (
    ROOT / "run_psycolab.bat",
    ROOT / "pyproject.toml",
    ROOT / ".gitignore",
)

PATTERNS = (
    ("Windows user-home path", re.compile(r"(?i)[A-Z]:[\\/](?:Users|Documents and Settings)[\\/]")),
    ("macOS user-home path", re.compile(r"/Users/[^/\\\s]+/")),
    ("Linux user-home path", re.compile(r"/home/[^/\\\s]+/")),
    ("author-specific username", re.compile(r"(?i)AlexanderMinns|Alexander\s+Minns")),
    ("old local project path", re.compile(r"(?i)Physics[\\/]PhD[\\/]GitHub")),
)


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def text_files() -> list[Path]:
    allowed = {".py", ".json", ".toml", ".bat", ".sh", ".yaml", ".yml", ".txt"}
    files: list[Path] = []
    for directory in TEXT_SCAN_DIRS:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in allowed:
                continue
            parts = set(path.parts)
            if {".venv", "__pycache__", ".git"} & parts:
                continue
            files.append(path)
    files.extend(path for path in ROOT_TEXT_FILES if path.exists())
    return sorted(set(files))


def main() -> int:
    failures: list[str] = []

    try:
        tracked = tracked_files()
    except Exception as exc:
        print(f"Could not inspect Git tracking: {exc}", file=sys.stderr)
        return 2

    for path in tracked:
        normalized = path.replace("\\", "/")
        if normalized.endswith((".pyc", ".pyo")) or "/__pycache__/" in f"/{normalized}":
            failures.append(f"tracked Python cache: {path}")
        if any(normalized.startswith(prefix) for prefix in FORBIDDEN_TRACKED_PREFIXES):
            failures.append(f"tracked local-only path: {path}")

    for path in text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in PATTERNS:
            match = pattern.search(text)
            if match:
                rel = path.relative_to(ROOT)
                failures.append(f"{label} in {rel}: {match.group(0)!r}")

    if failures:
        print("PsyCoLab portability check FAILED:\n")
        for failure in failures:
            print(f" - {failure}")
        print("\nRun scripts/cleanup_git_tracking.py for tracked local artefacts, then review any hard-coded path finding.")
        return 1

    print("PsyCoLab portability check passed.")
    print("No tracked local virtualenv/editor/cache artefacts or hard-coded user-home paths were found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
