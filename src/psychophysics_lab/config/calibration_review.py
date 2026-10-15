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
            verification = 'Researcher-reviewed visual consistency; NOT physical certification' if item['completed'] else item['message']
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



def luminance_verification_guidance(profile, root):
    """Read-only explanation of what needs review, never an auto-certification."""
    from .calibration_dataset import load_active, physical_snapshot_differences
    from .models import photometry_is_test_data

    if not profile.luminance_calibration:
        return ("No saved luminance pairs on this monitor. Setup can still be "
                "finished; actual photometry is needed before human acquisition.")
    parts = [f"{len(profile.luminance_calibration)} saved digital-command / cd/m² pairs. "
             "Saved readings remain available; reopening Calibration does NOT "
             "require repeating unchanged measurements."]
    try:
        dataset = load_active(root, profile)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parts.append("The active measurement record needs inspection: " + str(exc)
                     + " Earlier records are preserved. Open Calibrate → Luminance "
                       "to inspect recovery history; do not declare Verified.")
        return "\n".join(parts)

    differences = physical_snapshot_differences(profile, dataset)
    if differences:
        names = {
            'physical_width_m': 'screen width',
            'physical_height_m': 'screen height',
            'viewing_distance_m': 'viewing distance',
            'expected_resolution_px': 'pixel resolution',
            'display_binding': 'display binding',
            'refresh_rate_hz': 'refresh rate',
            'profile_uuid': 'physical profile identity',
            'id': 'display profile ID',
        }
        changes = ', '.join(
            f"{names.get(key, key)} ({before} → {after})"
            for key, (before, after) in differences.items()
        )
        parts.append(
            "Earlier measurement snapshot does not match this physical setup: "
            + changes + ". This is NOT caused by simply reopening the TUI or "
            "editing notes. Keep the old readings for reference/test workflows; "
            "obtain applicable real photometry for the changed display before "
            "declaring physical verification."
        )
    if photometry_is_test_data(profile) or any(
        obs.get('data_kind') == 'synthetic'
        for obs in dataset.get('observations', ())
    ):
        parts.append(
            "TEST/SYNTHETIC photometry detected. These saved values remain usable "
            "for simulation and designated presentation tests, but cannot be "
            "marked physically Verified or qualify human acquisition. "
            "Replacing the method label does not convert synthetic readings."
        )
    elif not differences:
        parts.append(
            "Saved measurements match the recorded physical configuration. "
            "Physical verification still requires genuine instrument readings "
            "and explicit independent laboratory review; no new measurements "
            "are demanded merely because this page was opened."
        )
    return "\n".join(parts)


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
        from .calibration_dataset import load_active,physical_snapshot_differences
        dataset=load_active(root,profile)
        if any(r['data_kind']=='synthetic' for r in dataset['observations']):
            raise ValueError('Fake/synthetic photometer data cannot be declared physically verified. Existing readings remain usable for test/simulation. Replace with actual observations before human acquisition; changing metadata alone is not evidence.')
        differences = physical_snapshot_differences(profile, dataset)
        if differences:
            changed_fields = ', '.join(sorted(differences))
            raise ValueError(
                'Saved luminance evidence was recorded for a different physical '
                f'configuration ({changed_fields}). It remains preserved and '
                'usable as historical/test data. Review the changed physical '
                'setup and obtain applicable real photometer readings before '
                'declaring Verified; reopening Calibration or editing notes alone '
                'does not invalidate measurements.'
            )
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



def save_one_verification(profile, root, *, category, status, reviewed, calibration_method=None):
    """Review/save one category without accidentally changing the other two.

    Delegates to the existing strict save_verification checks: test photometry
    cannot become certified and geometry/timing still require laboratory review.
    """
    keys=('geometry_status','calibration_status','timing_status')
    if category not in keys:
        raise ValueError('Select Geometry, Photometry or Timing.')
    if status not in ('unverified','manual_unverified','verified','accepted'):
        raise ValueError('Choose Yes, No, or Measurements saved but not verified.')
    if status=='accepted' and (category!='calibration_status' or profile.calibration_status!='accepted'):
        raise ValueError('Accept the mapping directly from the Luminance page.')
    statuses={key:getattr(profile,key) for key in keys}
    statuses[category]=status
    method=(profile.calibration_method if category!='calibration_status'
            else profile.calibration_method if calibration_method is None
            else calibration_method)
    return save_verification(profile, root,
                             **statuses, calibration_method=method,
                             reviewed=reviewed)


def qualify_experiment(profile, root, spec, *, reviewed, values=None):
    if not reviewed:
        raise ValueError('Explicitly confirm that the laboratory reviewed this experiment on this display.')
    failed = [check['detail'] for check in qualification_checks(spec, profile, values) if not check['passed']]
    if failed:
        raise ValueError('Experiment cannot be qualified:\n' + '\n'.join(failed))
    identities = tuple(dict.fromkeys((*profile.qualified_experiments, spec.id)))
    return save_profile(root, replace(profile, qualified_experiments=identities), expected_revision=profile.revision)
