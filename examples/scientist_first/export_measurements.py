"""Read-only derived TSV export; originals and the 20-column table stay intact."""
import argparse
import csv
import json
from pathlib import Path
from psychophysics_lab.data.reader import load_run


def export_measurements(run_directory, destination):
    root = Path(run_directory).resolve()
    output = Path(destination).resolve()
    if output.is_relative_to(root):
        raise ValueError("Write derived analysis outside the original run directory.")
    saved = load_run(root)
    accepted = [int(index) for index in saved["trials"]["trial_index"]]
    resolution = json.loads((root / "resolved_experiment.json").read_text(encoding="utf-8"))
    units = resolution["measurement_units"]
    rows = []
    for line in (root / "trial_events.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        presentation = event.get("presentation")
        if presentation is None or presentation["trial_index"] not in accepted:
            continue  # Interrupted, unaccepted displays are not invented answers.
        measurements = presentation["measurements"]
        if set(measurements) != set(units):
            raise ValueError("Journal measurements do not match saved measurement units.")
        rows.append([presentation["trial_index"], *(measurements[key] for key in units)])
    if [row[0] for row in rows] != accepted:
        raise ValueError("Journal must contain exactly one measurement row per accepted trial.")
    with output.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(["trial_index [count]", *(f"{key} [{unit}]" for key, unit in units.items())])
        writer.writerows(rows)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("destination", type=Path, help="New TSV outside the saved run; existing files are refused")
    args = parser.parse_args()
    print(export_measurements(args.run_directory, args.destination))
