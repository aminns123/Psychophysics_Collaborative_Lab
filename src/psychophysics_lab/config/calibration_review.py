"""Completion and deliberate calibration review, independent of navigation."""
from dataclasses import replace
from .calibration_progress import calibration_progress
from .local import save_profile
from .preflight import qualification_checks
from .models import photometry_is_test_data


def review_summary(profile, root):
    progress = calibration_progress(profile, root)
    lines = []
    names = {'bind': 'Display', 'geometry': 'Geometry', 'spatial': 'Spatial',
             'luminance': 'Luminance', 'timing': 'Timing'}
    outstanding = []
    for key, name in names.items():
        item = progress[key]
        saved = 'Saved' if item['completed'] else 'INCOMPLETE'
        if key == 'luminance' and profile.luminance_calibration:
            saved = f'{len(profile.luminance_calibration)} intensity / cd/m² pairs saved'
        if key == 'bind':
            verification = 'Configuration recorded; not physical certification' if item['completed'] else 'Binding / measured dimensions missing'
        elif key == 'spatial':
            verification = 'Geometry-dependent; software grating is not independent certification'
        else:
            verification = 'Manually declared verified' if item['verified'] else 'Physical verification pending'
        lines.append(f'{name}: {saved} ({item["state"].upper().replace("_", " ")})\n  {verification}')
        if not item['completed']:
            outstanding.append(f'{name}: {item["message"]}. Open calibration page {list(names).index(key)+1}.')
        elif key == 'luminance' and photometry_is_test_data(profile):
            outstanding.append('Luminance: the recorded method describes fake/synthetic test data. Open Luminance and record actual photometer observations before physical verification or human qualification.')
        elif key in {'geometry', 'luminance', 'timing'} and not item['verified']:
            outstanding.append(f'{name}: saved observations need independent review. Choose Review physical verification; use actual ruler/photometer/photodiode evidence as applicable.')
    if not profile.qualified_experiments:
        outstanding.append('Experiment qualification: none declared. Choose Check / qualify experiment to inspect its requirements. This does not prevent finishing setup.')
    else:
        from ..experiments.registry import list_experiments
        names_by_id = {spec.id: spec.display_name for spec in list_experiments()}
        lines.append('Explicit experiment qualification: ' + ', '.join(names_by_id.get(key, key) for key in profile.qualified_experiments))
    return '\n\n'.join(lines), '\n\n'.join(outstanding) or 'No setup/review actions outstanding. Human acquisition still checks its actual configuration and connected display.'


def save_verification(profile, root, *, geometry_status, calibration_status,
                      timing_status, calibration_method, reviewed):
    from .models import photometry_is_test_data
    candidate = replace(profile, geometry_status=geometry_status,
                        calibration_status=calibration_status, timing_status=timing_status,
                        calibration_method=calibration_method.strip())
    if candidate == profile:
        return save_profile(root, candidate, expected_revision=profile.revision)
    newly_verified = [key for key in ('geometry_status', 'calibration_status', 'timing_status')
                      if getattr(candidate, key) == 'verified' and getattr(profile, key) != 'verified']
    if candidate.calibration_status == "verified" and candidate.calibration_method != profile.calibration_method:
        newly_verified.append("calibration_method")
    if newly_verified and not reviewed:
        raise ValueError('Confirm independent laboratory review before declaring a changed field Verified.')
    progress = calibration_progress(profile, root)
    if 'geometry_status' in newly_verified and not progress['geometry']['measurement_recorded']:
        raise ValueError('Geometry needs a compatible saved ruler measurement. Record it on Geometry before verification.')
    if 'calibration_status' in newly_verified or 'calibration_method' in newly_verified:
        from .calibration_dataset import load_active,physical_snapshot
        dataset=load_active(root,profile)
        if any(r['data_kind']=='synthetic' for r in dataset['observations']):
            raise ValueError('Fake/synthetic photometer data cannot be declared physically verified. Replace actual observations explicitly; changing metadata alone is not evidence.')
        if dataset['physical_snapshot']!=physical_snapshot(profile):
            raise ValueError('Saved luminance evidence belongs to an earlier physical configuration. Replace measurements explicitly before verification.')
        if len(candidate.luminance_calibration) < 2 or not candidate.calibration_method:
            raise ValueError('Photometry verification needs saved pairs and the actual instrument/method. Optional notes do not block setup completion.')
        if photometry_is_test_data(candidate):
            raise ValueError('Fake/synthetic photometer data cannot be declared physically verified.')
    # Do not retain qualifications whose registered requirements no longer hold.
    from ..experiments.registry import get_experiment
    keep = []
    for identity in candidate.qualified_experiments:
        try:
            if all(check['passed'] for check in qualification_checks(get_experiment(identity), candidate)):
                keep.append(identity)
        except KeyError:
            continue
    candidate = replace(candidate, qualified_experiments=tuple(keep))
    if reviewed and candidate.calibration_status=='verified' and candidate.calibration_method!=profile.calibration_method and (root/'profiles'/profile.id/'current'/'luminance.json').exists():
        # Both validations above have already passed. Record the instrument
        # while unverified first, then the explicit laboratory declaration.
        # This uses the existing save/invalidation rules, with no override flag.
        # An interrupted/concurrent second save leaves the data unverified.
        intermediate=save_profile(root,replace(candidate,calibration_status='manual_unverified',qualified_experiments=()),expected_revision=profile.revision)
        candidate=replace(intermediate,calibration_status='verified')
        return save_profile(root,candidate,expected_revision=intermediate.revision)
    return save_profile(root, candidate, expected_revision=profile.revision)


def qualify_experiment(profile, root, spec, *, reviewed, values=None):
    if not reviewed:
        raise ValueError('Explicitly confirm that the laboratory reviewed this experiment on this display.')
    failed = [check['detail'] for check in qualification_checks(spec, profile, values) if not check['passed']]
    if failed:
        raise ValueError('Experiment cannot be qualified:\n' + '\n'.join(failed))
    identities = tuple(dict.fromkeys((*profile.qualified_experiments, spec.id)))
    return save_profile(root, replace(profile, qualified_experiments=identities), expected_revision=profile.revision)
