"""Read-only Windows display binding preflight (not an optical calibration).

Run from PsyCoLab's Python environment:
    .venv\\Scripts\\python.exe scripts\\windows_display_preflight.py --profile legacy_reference_display

Does not create a window, acquire responses, or write to a data repository.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def inspect(profile_id: str) -> dict:
    from psychophysics_lab.config.monitor import load_monitor_profiles
    from psychophysics_lab.core.display import enumerate_displays, select_screen

    profiles = load_monitor_profiles(ROOT)
    if profile_id not in profiles:
        raise ValueError(f"Unknown profile: {profile_id}. Known IDs: {', '.join(profiles)}")
    p = profiles[profile_id]
    screens = enumerate_displays()
    report = {
        "operating_system": platform.platform(),
        "profile": profile_id,
        "profile_origin": p.origin,
        "profile_physical_size_mm": [p.physical_width_m * 1000, p.physical_height_m * 1000],
        "profile_viewing_distance_mm": p.viewing_distance_m * 1000,
        "profile_nominal_refresh_hz": p.refresh_rate_hz,
        "profile_expected_resolution_px": list(p.expected_resolution_px) if p.expected_resolution_px else None,
        "profile_calibration_status": p.calibration_status,
        "profile_geometry_status": p.geometry_status,
        "profile_timing_status": p.timing_status,
        "os_detected_screens": [asdict(screen) for screen in screens],
        "notes": [
            "OS display resolution may be affected by Windows DPI scaling; verify real fullscreen framebuffer separately.",
            "Detected refresh mode is not a measured photon refresh timing or guarantee of no dropped frames.",
            "Physical screen dimensions and viewing distance require manual measurement.",
            "Only photometric/photodiode measurement can verify contrast luminance and physical timing.",
        ],
    }
    try:
        _, selected = select_screen(p)
        report["selected_screen"] = selected
        report["screen_selection_ok"] = True
    except (ValueError, OSError, RuntimeError) as exc:
        report["screen_selection_ok"] = False
        report["selection_error"] = str(exc)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="legacy_reference_display")
    args = parser.parse_args(argv)
    if sys.platform != "win32":
        print("This preflight is intended for the physical Windows laboratory workstation.")
        return 2
    try:
        report = inspect(args.profile)
    except Exception as exc:
        print(f"Display preflight failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report["screen_selection_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
