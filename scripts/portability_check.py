"""Check the shared PsyCoLab checkout for machine-specific artefacts.

The checker deliberately scans files that are tracked *or* would be added by
Git (tracked + untracked, excluding ignored files). That catches new shared
source files without being confused by local .venv/log/cache contents.
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
    ".idea/",
    "tmp/",
    "temp/",
    "local_psychophysics_data/",
)

SCAN_PREFIXES = (
    "src/",
    "Events/",
    "Experiments/",
    "Functions/",
    "Interface/",
    "scripts/",
    "configs/",
    ".github/",
)

ROOT_TEXT_FILES = {
    "run_psycolab.bat",
    "pyproject.toml",
    ".gitignore",
    "libC.py",
}

ALLOWED_TEXT_SUFFIXES = {".py", ".json", ".toml", ".bat", ".sh", ".yaml", ".yml", ".txt"}

# Build the detector expressions from fragments so this checker does not trigger
# on its own source code. These are detection rules, not project paths.
_slash = "/"
_backslash = "\\"
_author_first = "Alexander"
_author_last = "Minns"

PATTERNS = (
    (
        "Windows user-home path",
        re.compile(
            r"(?i)[A-Z]:[\\/]+" + r"(?:Users|Documents and Settings)" + r"[\\/]+"
        ),
    ),
    (
        "macOS user-home path",
        re.compile(re.escape(_slash) + "Users" + re.escape(_slash) + r"[^/\\\s]+/"),
    ),
    (
        "Linux user-home path",
        re.compile(re.escape(_slash) + "home" + re.escape(_slash) + r"[^/\\\s]+/"),
    ),
    (
        "author-specific username",
        re.compile(r"(?i)" + _author_first + r"\s*" + _author_last),
    ),
    (
        "old local project path",
        re.compile(
            r"(?i)" + "Physics" + r"[\\/]+" + "PhD" + r"[\\/]+" + "GitHub"
        ),
    ),
)


def _git_lines(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def tracked_files() -> list[str]:
    return _git_lines("ls-files")


def shared_candidate_files() -> list[str]:
    """Files that are tracked or are non-ignored candidates for a future commit."""
    return _git_lines("ls-files", "--cached", "--others", "--exclude-standard")


def _is_scannable(relative: str) -> bool:
    normalized = relative.replace("\\", "/")
    if normalized in ROOT_TEXT_FILES:
        return True
    if not any(normalized.startswith(prefix) for prefix in SCAN_PREFIXES):
        return False
    return Path(normalized).suffix.lower() in ALLOWED_TEXT_SUFFIXES


def text_files() -> list[Path]:
    files: list[Path] = []
    for relative in shared_candidate_files():
        normalized = relative.replace("\\", "/")
        if not _is_scannable(normalized):
            continue
        if any(part in {".venv", "__pycache__", ".git"} for part in Path(normalized).parts):
            continue
        path = ROOT / normalized
        if path.is_file():
            files.append(path)
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
        if normalized.startswith(".venv.incompatible-") or normalized.endswith((".log", ".tmp", ".swp", "~")):
            failures.append(f"tracked local runtime/temporary file: {path}")

    try:
        candidates = text_files()
    except Exception as exc:
        print(f"Could not enumerate shared source files: {exc}", file=sys.stderr)
        return 2

    for path in candidates:
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
        print(
            "\nRun scripts/cleanup_git_tracking.py for tracked local artefacts, "
            "then review any genuine hard-coded path finding."
        )
        return 1

    print("PsyCoLab portability check passed.")
    print(
        "No tracked local virtualenv/editor/cache artefacts or hard-coded "
        "user-home paths were found in shared source candidates."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
