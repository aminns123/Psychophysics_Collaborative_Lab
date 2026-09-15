"""Read-only checks of a finalized PsyCoLab acquisition directory.

No runtime/renderer is imported and no file is created, repaired or rewritten.
PASS means internal consistency, not scientific or physical display validation.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from psychophysics_lab.data.trials import (  # noqa: E402
    TRIAL_COLUMNS, TRIAL_COLUMN_DEFINITIONS, TRIAL_SCHEMA_VERSION,
)
from psychophysics_lab.experiments.registry import get_experiment  # noqa: E402


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str = ""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def owned_path(root: Path, relative: str) -> Path:
    require(isinstance(relative, str) and relative, "empty/non-text file reference")
    posix, windows = PurePosixPath(relative), PureWindowsPath(relative)
    require(not posix.is_absolute() and not windows.drive and not windows.root
            and "\\" not in relative and ".." not in posix.parts,
            f"non-portable file reference: {relative!r}")
    path = root / relative
    require(path.resolve().is_relative_to(root.resolve()), f"file escapes run: {relative}")
    # Even an internal symlink is not an ordinary self-contained acquisition file.
    require(not any(part.is_symlink() for part in (path, *path.parents)
                    if part != root and part.is_relative_to(root)),
            f"symlink in run file reference: {relative}")
    return path


def read_json(root, name):
    payload = json.loads(owned_path(root, name).read_text(encoding="utf-8"))
    require(isinstance(payload, dict), f"{name} must contain a JSON object")
    return payload


def table(root, name):
    with owned_path(root, name).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        rows = list(reader)
        require(reader.fieldnames is not None, f"{name}: missing header")
        require(all(None not in row and None not in row.values() for row in rows),
                f"{name}: malformed row width")
        return reader.fieldnames, rows


def same_number(left, right):
    a, b = float(left), float(right)
    return math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)


def leaves(value, prefix=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from leaves(item, f"{prefix}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from leaves(item, f"{prefix}[{index}]")
    else:
        yield prefix, value


def validate_run(run_directory: Path) -> list[Check]:
    root = Path(run_directory).resolve()
    checks = []

    def check(name, function):
        try:
            function()
        except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
            checks.append(Check(name, False, str(exc)))
        else:
            checks.append(Check(name, True))

    manifest = {}

    def manifest_check():
        manifest.update(read_json(root, "manifest.json"))
        require(manifest.get("trial_schema_version") == TRIAL_SCHEMA_VERSION,
                "unsupported/missing trial_schema_version")

    check("Manifest JSON and schema", manifest_check)
    csf = manifest.get("experiment_id") == "contrast_sensitivity"
    adaptive_needed = csf or "adaptive_session" in manifest or (root / "adaptive_session.json").exists()
    required = ["manifest.json", "experiment_config.json", "monitor_profile.json",
                "runtime_display.json", "resolved_experiment.json", "trials.tsv",
                "trials_readable.txt", "trial_data_dictionary.tsv"]
    if adaptive_needed:
        required.append("adaptive_session.json")
    if csf:
        required += ["legacy_response.txt", "state/experiment_defined.json",
                     "state/user_experiment_config.json"]
        required += [f"state/{kind}.{phase}.json" for kind in ("conditions", "parameters")
                     for phase in ("initial", "runtime", "final")]
        required += [f"state/user_config.{phase}.json" for phase in ("initial", "final")]

    def files_check():
        missing = [name for name in required if not owned_path(root, name).is_file()]
        require(not missing, "missing files: " + ", ".join(missing))
        require(isinstance(manifest.get("files"), dict), "missing manifest files mapping")
        for _, name in leaves(manifest["files"]):
            require(owned_path(root, name).exists(), f"missing declared artifact: {name}")

    check("Required canonical files and declared artifacts", files_check)

    def hashes_check():
        hashes = manifest.get("output_sha256", {})
        require(isinstance(hashes, dict), "output_sha256 must be an object")
        require("output_sha256_error" not in manifest, "run reported output hashing failure")
        for name, expected in hashes.items():
            require(isinstance(expected, str) and re.fullmatch(r"[0-9a-fA-F]{64}", expected),
                    f"invalid SHA256 for {name}")
            digest = hashlib.sha256()
            with owned_path(root, name).open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            require(digest.hexdigest() == expected.lower(), f"SHA256 mismatch: {name}")

    check("Supplied output SHA256 hashes", hashes_check)
    if checks[-1].passed and not manifest.get("output_sha256"):
        checks[-1] = Check(checks[-1].name, True, "no hashes supplied; integrity not verified")

    rows = []

    def trials_check():
        header, loaded = table(root, "trials.tsv")
        require(tuple(header) == TRIAL_COLUMNS, "trials.tsv header differs from current schema")
        rows.extend(loaded)

    check("Canonical trial header and row widths", trials_check)

    def indices_check():
        require([row["trial_index"] for row in rows] == [str(i) for i in range(1, len(rows) + 1)],
                "trial_index must be sequential starting at 1")

    check("Sequential accepted-response indices", indices_check)
    check("Accepted count in manifest", lambda: require(
        type(manifest.get("accepted_trials")) is int and manifest["accepted_trials"] == len(rows),
        f"manifest accepted_trials differs from {len(rows)} canonical rows"))
    adaptive = {}

    def adaptive_check():
        if not adaptive_needed:
            return
        adaptive.update(read_json(root, "adaptive_session.json"))
        require(manifest.get("adaptive_session") == adaptive, "manifest adaptive snapshot differs")
        require(type(adaptive.get("total_trials")) is int and adaptive["total_trials"] == len(rows),
                "adaptive total_trials differs from canonical count")
        require(adaptive.get("canonical_trial_log") == "trials.tsv", "adaptive trial reference differs")
        states = adaptive["staircases"]
        require(bool(states), "no staircase states")
        require(all(row["staircase_id"] in states for row in rows), "unknown staircase in trials")
        for identity, state in states.items():
            trials = [row for row in rows if row["staircase_id"] == identity]
            require(state["trial_count"] == len(trials), f"staircase {identity}: trial count differs")
            require([row["staircase_trial_index"] for row in trials] ==
                    [str(i) for i in range(1, len(trials) + 1)], f"staircase {identity}: indices differ")
            require(type(state["complete"]) is bool and state["complete"] ==
                    (state["reversal_count"] >= state["config"]["reversal_limit"]),
                    f"staircase {identity}: completion criterion differs")
            if trials:
                last = trials[-1]
                require(int(last["reversal_count"]) == state["reversal_count"] and
                        last["staircase_complete"] == str(int(state["complete"])) and
                        same_number(last["next_screen_intensity"], state["last_value"]),
                        f"staircase {identity}: final canonical state differs")
        completed = {identity for identity, state in states.items() if state["complete"]}
        for key, expected in (("completed_staircase_ids", completed),
                              ("unfinished_staircase_ids", set(states) - completed),
                              ("active_staircase_ids", set(states) - completed)):
            actual = [str(item) for item in adaptive[key]]
            require(set(actual) == expected and len(actual) == len(expected), f"{key} differs from states")

    check("Adaptive counts, identities and saved staircase state", adaptive_check)

    def status_check():
        status = manifest.get("status")
        require(status in {"completed", "max_trials_reached", "aborted_by_user", "aborted", "error", "returned"},
                f"not a final run status: {status!r}")
        require(bool(manifest.get("finished_utc")), "missing finalization timestamp")
        require(status == "error" or not manifest.get("error"), "error attached to a non-error status")
        if not adaptive_needed:
            return
        state_status = adaptive["status"]
        require(status == state_status or (status == "error" and bool(manifest.get("error"))),
                "manifest/adaptive final statuses disagree")
        require(state_status in {"completed", "max_trials_reached", "aborted", "aborted_by_user", "error", "running"},
                "unknown adaptive status")
        ceiling = adaptive["max_trials"]
        require(len(rows) <= ceiling, "accepted count exceeds ceiling")
        all_complete = all(state["complete"] for state in adaptive["staircases"].values())
        expected = "completed" if all_complete else "max_trials_reached" if len(rows) == ceiling else "running"
        if state_status in {"completed", "max_trials_reached"}:
            require(state_status == expected, "final adaptive status contradicts completion/ceiling")
        elif state_status in {"aborted", "aborted_by_user", "running"}:
            require(expected == "running", "aborted/running status contradicts termination criteria")
        if rows:
            require(all(row["run_status"] == "running" for row in rows[:-1]),
                    "accepted response follows a terminal response")
            require(rows[-1]["run_status"] == expected, "last trial status contradicts saved state")

    check("Final lifecycle status consistency", status_check)

    def continuity_check():
        previous = {}
        for row in rows:
            identity = row["staircase_id"]
            if not identity:
                continue
            old = previous.get(identity)
            if old:
                require(old["staircase_complete"] != "1", f"staircase {identity}: response after completion")
            for suffix in ("display_contrast", "screen_intensity"):
                presented, following = row[f"presented_{suffix}"], row[f"next_{suffix}"]
                require(bool(presented) == bool(following), f"trial {row['trial_index']}: incomplete {suffix} pair")
                if presented:
                    require(same_number(presented, presented) and same_number(following, following),
                            f"trial {row['trial_index']}: nonfinite {suffix}")
                if old and (old[f"next_{suffix}"] or presented):
                    require(same_number(old[f"next_{suffix}"], presented),
                            f"staircase {identity}, trial {row['trial_index']}: {suffix} discontinuity")
            previous[identity] = row

    check("Per-staircase presented/next continuity (tolerance 1e-12)", continuity_check)
    metadata = {}

    def metadata_check():
        names = set(name for name in required if name.endswith(".json"))
        names.update(path.relative_to(root).as_posix() for path in root.glob("*.json"))
        names.update(path.relative_to(root).as_posix() for path in (root / "state").glob("*.json"))
        for name in sorted(names):
            metadata[name] = read_json(root, name)
        # Detect embedded absolute paths in prose as well as direct path values.
        absolute = re.compile(r"(?i)(?:[a-z]:[\\/]|\\\\[^\\\s]+\\|/(?:" +
                              "home|Users|root" + r")(?:/|\\)[^\s]+)")
        for name, payload in metadata.items():
            for location, value in leaves(payload):
                if isinstance(value, str):
                    require(not absolute.search(value) and not value.startswith("/"),
                            f"absolute machine path in {name}{location}")

    check("Portable canonical JSON metadata", metadata_check)

    def ceiling_check():
        found = []
        for name, payload in metadata.items():
            for location, value in leaves(payload):
                if location.rsplit(".", 1)[-1] in {"max_trials", "number_trials", "max_accepted_responses"}:
                    require(type(value) is int and value > 0, f"invalid response ceiling: {name}{location}")
                    found.append((name + location, value))
        if adaptive_needed:
            require(bool(found), "no saved response ceiling")
        if csf:
            expected_locations = {
                "manifest.json": ("legacy_setup.max_trials",),
                "experiment_config.json": ("normalised_experiment_values.max_trials", "legacy_setup.max_trials"),
                "resolved_experiment.json": ("adaptive_parameters.max_accepted_responses",),
                "adaptive_session.json": ("max_trials", "legacy_parameters.max_trials", "legacy_parameters.number_trials"),
                "state/experiment_defined.json": ("max_trials",),
            }
            for phase in ("initial", "runtime", "final"):
                expected_locations[f"state/parameters.{phase}.json"] = ("max_trials", "number_trials")
            for name in ("state/user_experiment_config.json", "state/user_config.initial.json", "state/user_config.final.json"):
                expected_locations[name] = ("experiment_params.number_trials", "staircase_params.number_trials", "staircase_params.max_trials")
            for name, locations in expected_locations.items():
                for location in locations:
                    require(any(key == name + "." + location for key, _ in found),
                            f"missing response ceiling: {name}.{location}")
        require(len({value for _, value in found}) <= 1, "saved response ceilings disagree: " + repr(found))
        if found:
            require(len(rows) <= found[0][1], "accepted responses exceed configured maximum")

    check("Configured maximum accepted responses across configuration/state", ceiling_check)

    def dictionary_check():
        header, definitions = table(root, "trial_data_dictionary.tsv")
        require(header == ["trial_schema_version", "experiment_id", "column_order", "column_name",
                           "logical_type", "units_or_encoding", "meaning", "notes"], "dictionary header differs")
        require([item["column_name"] for item in definitions] == list(TRIAL_COLUMNS), "dictionary columns differ")
        spec = get_experiment(manifest["experiment_id"])
        for index, item in enumerate(definitions, 1):
            require(item["column_order"] == str(index) and item["trial_schema_version"] == str(TRIAL_SCHEMA_VERSION)
                    and item["experiment_id"] == manifest["experiment_id"], "dictionary identity/order/version differs")
            expected = asdict(TRIAL_COLUMN_DEFINITIONS[item["column_name"]])
            expected.update(spec.trial_column_overrides.get(item["column_name"], {}))
            require(all(item[key] == value for key, value in expected.items()),
                    f"dictionary definition differs: {item['column_name']}")

    check("Trial dictionary matches schema and experiment definitions", dictionary_check)

    def readable_check():
        widths = {column: max([len(column)] + [len(row[column]) for row in rows]) for column in TRIAL_COLUMNS}

        def render(row):
            return "  ".join(row[column].ljust(widths[column]) for column in TRIAL_COLUMNS).rstrip()

        expected = [render({column: column for column in TRIAL_COLUMNS}),
                    "  ".join("-" * widths[column] for column in TRIAL_COLUMNS)]
        expected.extend(render(row) for row in rows)
        actual = owned_path(root, "trials_readable.txt").read_text(encoding="utf-8").splitlines()
        require(actual == expected, "readable trials differ from canonical TSV")

    check("Readable trial table matches canonical TSV", readable_check)

    def snapshots_check():
        config = metadata["experiment_config.json"]
        require(config["legacy_setup"] == manifest["legacy_setup"], "manifest/config legacy setup differs")
        require(metadata["monitor_profile.json"] == manifest["monitor_profile"], "monitor snapshot differs")
        require(metadata["runtime_display.json"] == manifest["runtime_display"], "runtime display snapshot differs")
        for key in ("participant_id", "experiment_id", "monitor_profile_id"):
            require(config["request"][key] == manifest[key], f"request/manifest {key} differs")
        require(metadata["resolved_experiment.json"]["experiment_id"] == manifest["experiment_id"],
                "resolved experiment identity differs")
        if csf:
            require(metadata["state/experiment_defined.json"] == config["legacy_setup"], "defined setup differs")
            for kind in ("conditions", "parameters"):
                require(metadata[f"state/{kind}.runtime.json"] == metadata[f"state/{kind}.final.json"],
                        f"{kind} final/runtime snapshot differs")
            require(metadata["state/parameters.initial.json"] == metadata["state/parameters.final.json"],
                    "static parameters changed during run")
            require(metadata["state/user_config.initial.json"] == metadata["state/user_config.final.json"] ==
                    metadata["state/user_experiment_config.json"], "user config snapshots differ")

    check("Manifest, configuration and state snapshot consistency", snapshots_check)

    def legacy_check():
        if not csf:
            return
        legacy = [line.split() for line in owned_path(root, "legacy_response.txt").read_text().splitlines() if line.strip()]
        columns = ("stimulus_condition", "target_alternative", "participant_response", "staircase_id",
                   "next_display_contrast", "next_screen_intensity")
        require(len(legacy) == len(rows), "legacy response count differs (or placeholder remains)")
        for index, (old, row) in enumerate(zip(legacy, rows), 1):
            require(len(old) == 6 and all(same_number(value, row[key]) for value, key in zip(old, columns)),
                    f"legacy response {index} differs from canonical post-response values")

    check("Legacy response agrees with canonical post-response values where applicable", legacy_check)
    return checks


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args(argv)
    checks = validate_run(args.run_directory)
    passed = all(item.passed for item in checks)
    print("PASS" if passed else "FAIL")
    for item in checks:
        print(f"[{'PASS' if item.passed else 'FAIL'}] {item.name}" +
              (f": {item.detail}" if item.detail else ""))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
