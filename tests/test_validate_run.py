"""Read-only validator regression tests using the *current* real simulation runner.

Previously this file executed the retired CSF shader/staircase implementation.
These checks retain canonical-data, corruption, integrity and CLI coverage.
"""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from simulations.run import simulate
from scripts.validate_run import validate_run

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def run_dir(tmp_path):
    artifacts,_=simulate(data_root=tmp_path/"data",repo_root=ROOT,
                         seed=27,values={"frequencies_cpd":"2,5",
                                         "staircases_per_condition":1,
                                         "max_trials":12},analyse=False)
    assert artifacts.accepted_trials>0
    return artifacts.run_directory


def snapshot(root):
    return {
        p.relative_to(root).as_posix():
          (hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns)
        for p in root.rglob("*") if p.is_file()
    }


def errors(root):
    return {c.name:c.detail for c in validate_run(root) if not c.passed}


def update_json(root,name,fn):
    path=root/name
    value=json.loads(path.read_text(encoding="utf-8"))
    fn(value)
    path.write_text(json.dumps(value),encoding="utf-8")


def test_valid_new_simulation_run_is_read_only(run_dir):
    before=snapshot(run_dir)
    failures=errors(run_dir)
    assert not failures, failures
    assert snapshot(run_dir)==before


@pytest.mark.parametrize("name,edit,prefix",[
    ("manifest.json",lambda d:d.update(accepted_trials=999),"Accepted count"),
    ("manifest.json",lambda d:d.update(status="running"),"Final lifecycle"),
    ("manifest.json",lambda d:d.update(output_sha256={"../outside":"0"*64}),"Supplied output"),
    ("adaptive_session.json",lambda d:d.update(total_trials=999),"Adaptive counts"),
    ("monitor_profile.json",lambda d:d.update(notes="C:\\Users\\Someone\\data"),"Portable canonical"),
])
def test_corruption_is_detected_without_mutating_evidence(run_dir,name,edit,prefix):
    update_json(run_dir,name,edit)
    before=snapshot(run_dir)
    result=errors(run_dir)
    assert any(n.startswith(prefix) for n in result),result
    assert snapshot(run_dir)==before


@pytest.mark.parametrize("column,value,prefix",[
    ("trial_index","99","Sequential"),
    ("staircase_id","9999","Adaptive counts"),
])
def test_corrupted_trial_index_or_identity_is_detected(run_dir,column,value,prefix):
    path=run_dir/"trials.tsv"
    with path.open(newline="",encoding="utf-8") as handle:
        reader=csv.DictReader(handle,delimiter="\t")
        cols,rows=reader.fieldnames,list(reader)
    rows[-1][column]=value
    with path.open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=cols,delimiter="\t")
        writer.writeheader();writer.writerows(rows)
    result=errors(run_dir)
    assert any(k.startswith(prefix) for k in result),result


@pytest.mark.parametrize("name,body,prefix",[
    ("trials.tsv","wrong\theader\n","Canonical trial header"),
    ("manifest.json","not JSON","Manifest JSON"),
    ("manifest.json","[]","Manifest JSON"),
    ("trials_readable.txt","wrong","Readable trial"),
    ("trial_data_dictionary.tsv","wrong","Trial dictionary"),
])
def test_malformed_or_derived_files_are_detected(run_dir,name,body,prefix):
    (run_dir/name).write_text(body,encoding="utf-8")
    result=errors(run_dir)
    assert any(k.startswith(prefix) for k in result),result


def test_cli_returns_success_then_nonzero_for_missing_file(run_dir):
    cmd=[sys.executable,str(ROOT/"scripts/validate_run.py"),str(run_dir)]
    before=snapshot(run_dir)
    completed=subprocess.run(cmd,capture_output=True,text=True)
    assert completed.returncode==0,completed.stdout+completed.stderr
    assert completed.stdout.startswith("PASS\n")
    assert snapshot(run_dir)==before
    (run_dir/"trials_readable.txt").unlink()
    failed=subprocess.run(cmd,capture_output=True,text=True)
    assert failed.returncode==1
    assert failed.stdout.startswith("FAIL\n")


def test_missing_hashes_are_reported_not_equated_to_verified_integrity(run_dir):
    update_json(run_dir,"manifest.json",lambda d:d.pop("output_sha256",None))
    outcomes=validate_run(run_dir)
    assert all(c.passed for c in outcomes),outcomes
    assert any("no hashes supplied" in c.detail for c in outcomes)


def test_missing_directory_reports_failure(tmp_path):
    assert errors(tmp_path/"missing")
