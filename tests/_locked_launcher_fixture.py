"""Legacy identity fixtures intentionally omit runtime packages; keep that scope explicit."""
import copy


def locked_fixture(monkeypatch, launcher):
    profile, digest = launcher._profile()
    evidence = dict(profile_id=profile['id'], profile_sha256=digest, interpreter={'fixture': 'identity-only'},
        inventory={}, core_fingerprint='identity-only-fixture', artifacts={
            name: {k: profile['artifacts'][name][k] for k in ('version','filename','sha256')}
            for name in profile['core']})
    monkeypatch.setattr(launcher, '_inspect_interpreter', lambda python: {})
    monkeypatch.setattr(launcher, '_validate_interpreter', lambda identity: None)
    monkeypatch.setattr(launcher, '_environment_evidence', lambda python: copy.deepcopy(evidence))
    def install(python):
        launcher._run([str(python), '-m', 'pip', 'install', '--require-hashes', '--only-binary=:all:',
                       '--requirement', str(launcher.PROFILE_DIR / 'runtime.lock')])
        return copy.deepcopy(evidence['artifacts'])
    monkeypatch.setattr(launcher, '_install_locked', install)
    return evidence
