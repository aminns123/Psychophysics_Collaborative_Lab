"""Execute a deterministic, exhaustive portion of the Windows pytest suite.

Only CI orchestration changes: no scientific fixture or test is dropped.
The weighting comes from actual module runtimes of the last complete
Windows run, and can be changed without altering test membership.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


WEIGHTS_SECONDS = {
    "test_source_recovery.py": 280,
    "test_independent_scientific_stress.py": 140,
    "test_stage_c_event_first.py": 105,
    "test_progressive_lessons.py": 98,
    "test_issue165_wave5.py": 97,
    "test_scientist_first_onboarding.py": 87,
    "test_review_parameter_authority.py": 79,
    "test_issue165_wave1.py": 75,
    "test_laboratory_console.py": 73,
    "test_issue165_wave4.py": 58,
    "test_official_method_baseline.py": 55,
    "test_spatial_observations.py": 53,
    "test_stage_b_event_first.py": 52,
    "test_issue165_wave3.py": 52,
    "test_scientist_first_examples.py": 52,
    "test_simulation_tui.py": 52,
    "test_teaching_scenario_analysis.py": 42,
    "test_laboratory_extensions.py": 42,
    "test_researcher_override.py": 39,
    "test_issue165_wave2.py": 37,
    "test_console_controls.py": 34,
    "test_configure_review_separation.py": 34,
    "test_independent_authoring_routes.py": 33,
    "test_tui_refresh.py": 31,
    "test_session_events.py": 28,
    "test_console_geometry.py": 28,
}

SHARDS = 4


def partition():
    # A full filename list, not a subset of tests chosen by old stage names.
    root = Path(__file__).resolve().parents[1]
    files = sorted((root / "tests").rglob("test_*.py"))
    if not files:
        raise RuntimeError("No pytest modules discovered; fail closed.")
    buckets = [[] for _ in range(SHARDS)]
    loads = [0] * SHARDS
    for file in sorted(
        files, key=lambda file: (-WEIGHTS_SECONDS.get(file.name, 8), file.name)
    ):
        slot = min(range(SHARDS), key=lambda index: (loads[index], index))
        buckets[slot].append(file)
        loads[slot] += WEIGHTS_SECONDS.get(file.name, 8)
    assert len(files) == sum(len(bucket) for bucket in buckets)
    assert len(set().union(*(set(bucket) for bucket in buckets))) == len(files)
    return root, buckets, loads


def main(argv):
    if len(argv) != 2 or argv[1] not in {str(i) for i in range(SHARDS)}:
        raise SystemExit("Usage: python scripts/ci_test_shard.py {0|1|2|3}")
    root, buckets, loads = partition()
    index = int(argv[1])
    selection = [str(path.relative_to(root)) for path in buckets[index]]
    print(
        f"Windows test shard {index+1}/{SHARDS}: {len(selection)} modules, "
        f"estimated {loads[index]} weighted seconds; {sum(map(len, buckets))} "
        f"modules covered exactly once across shards.",
        flush=True,
    )
    return subprocess.call(
        [
            sys.executable, "-X", "faulthandler", "-u", "-m", "pytest",
            "-vv", "-o", "faulthandler_timeout=30", "-o", "log_cli=true",
            "-o", "log_cli_level=WARNING", *selection,
        ],
        cwd=root,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
