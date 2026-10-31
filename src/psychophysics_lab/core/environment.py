"""Read-only software environment evidence, never acquisition authority."""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import subprocess
import sys


def environment_evidence(repo_root):
    root = Path(repo_root).resolve()
    role = os.environ.get('PSYCOLAB_LAUNCH_ROLE', '')
    result = dict(schema_version=1, role='unknown', check='not_established',
                  locked_profile_check_passed=False,
                  checked_utc=datetime.now(timezone.utc).isoformat())
    if role not in ('development', 'locked'):
        return result
    folder, script, record = (('.venv-dev', 'developer_setup.py', '.psycolab-development.json')
        if role == 'development' else ('.venv', 'launcher_setup.py', '.psycolab-setup.json'))
    env = root / folder
    executable = env / 'Scripts/python.exe'
    if (Path(sys.executable).resolve() != executable.resolve()
            or Path(sys.prefix).resolve() != env.resolve()
            or env.is_symlink() or env.resolve() != root / folder):
        return result
    result.update(role=role, check='not_verified', interpreter_role=folder)
    files = [root/'scripts'/script, env/record, root/'pyproject.toml']
    try:
        # The launcher hint selects a route, not qualification. Independently
        # rerun that route's existing checks against the actual interpreter.
        result['evidence_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        check = subprocess.run([str(executable), '-I', '-B', str(files[0]), '--check'],
            cwd=root, capture_output=True, timeout=90, check=False)
        result.update(check='passed' if check.returncode == 0 else 'failed',
                      exit_code=check.returncode,
                      check_output_sha256=hashlib.sha256(check.stdout+check.stderr).hexdigest())
        result['locked_profile_check_passed'] = role == 'locked' and check.returncode == 0
    except (OSError, ValueError, subprocess.SubprocessError):
        result['check'] = 'unavailable'
    return result


def environment_notice(evidence):
    if evidence['role'] == 'development':
        return ('Development / unlocked environment — check: ' + evidence['check'] +
                '. No locked laboratory qualification. Existing testing, pilot and researcher-override rules apply.')
    if evidence['role'] == 'locked' and evidence['locked_profile_check_passed']:
        return 'Locked software environment — read-only profile check passed. Apparatus and protocol qualification remain separate.'
    return 'Environment role/check unknown or unverified. No locked software qualification established; existing readiness and override rules apply.'
