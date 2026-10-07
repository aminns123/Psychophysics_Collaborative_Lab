import csv
import json
from pathlib import Path

import pytest

from psychophysics_lab.analysis.thresholds import analyse_thresholds
from psychophysics_lab.data.trials import TRIAL_COLUMNS


def _write_run(data_root: Path) -> Path:
    run = data_root / "S001" / "contrast_sensitivity" / "display" / "2026-10-07" / "run_001"
    run.mkdir(parents=True)
    (run / "manifest.json").write_text(
        json.dumps(
            {
                "run_uuid": "run-test-001",
                "participant_id": "S001",
                "experiment_id": "contrast_sensitivity",
            }
        ),
        encoding="utf-8",
    )

    rows = []
    trial = 0
    # Two staircases for one condition. Ten reversals each means the default
    # 80% rule retains the final eight values from each staircase.
    for staircase, base in (("0", 0.10), ("1", 0.20)):
        for index in range(10):
            trial += 1
            row = {column: "" for column in TRIAL_COLUMNS}
            row.update(
                {
                    "trial_index": str(trial),
                    "stimulus_condition": "2",
                    "staircase_id": staircase,
                    "reversal": "1",
                    "next_display_contrast": str(base + index * 0.01),
                    "presented_display_contrast": str(base + index * 0.01 - 0.005),
                }
            )
            rows.append(row)

    with (run / "trials.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRIAL_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    return run


def test_default_threshold_uses_final_eighty_percent_and_averages_staircases(tmp_path):
    data = tmp_path / "external_data"
    run = _write_run(data)
    result = analyse_thresholds(
        data_root=data,
        run_directory=run,
        create_plot=False,
    )
    assert len(result.staircase_thresholds) == 2
    assert all(item.retained_count == 8 for item in result.staircase_thresholds)

    # staircase 0 retains 0.12..0.19 -> mean .155
    # staircase 1 retains 0.22..0.29 -> mean .255
    # condition mean -> .205
    assert result.staircase_thresholds[0].threshold == pytest.approx(0.155)
    assert result.staircase_thresholds[1].threshold == pytest.approx(0.255)
    assert result.condition_thresholds[0].threshold == pytest.approx(0.205)
    assert result.output_directory.is_relative_to(data / "analysis")
    assert not result.output_directory.is_relative_to(run)


def test_threshold_analysis_never_accepts_run_outside_active_workspace(tmp_path):
    data = tmp_path / "data"
    other = tmp_path / "other"
    run = _write_run(other)
    with pytest.raises(ValueError):
        analyse_thresholds(data_root=data, run_directory=run, create_plot=False)
