"""Structured human readiness from authoritative preflight, separate from simulation."""
from .local import config_root, content_hash
from .preflight import human_requirements, validate_setup
from .calibration_progress import calibration_progress
from .models import photometry_is_test_data

# Dependencies come before experiment qualification: the latter cannot be
# completed until the physical calibration checks are satisfied.
HUMAN_CHECK_ORDER = (
    "binding", "geometry", "luminance", "timing", "sampling", "contrast",
    "configuration", "participant", "qualification",
)


def next_human_requirement(report):
    """First actionable required failure, independently of display order."""
    blocked = [row for row in report["requirements"]
               if row.get("required") and not row["passed"]]
    rank = {key: i for i, key in enumerate(HUMAN_CHECK_ORDER)}
    return min(blocked, key=lambda row: rank.get(row["key"], len(rank))) if blocked else None


def human_readiness_checklist(report):
    """Required steps in dependency order, with source-backed completion."""
    rank = {key: i for i, key in enumerate(HUMAN_CHECK_ORDER)}
    return sorted((row for row in report["requirements"] if row.get("required")),
                  key=lambda row: rank.get(row["key"], len(rank)))


def experiment_readiness(request, spec, profile, *, repo_root):
    stages = calibration_progress(profile, config_root(repo_root))
    requirements = human_requirements(spec, profile, request.experiment_values)
    requirements.insert(0, {'key':'setup','passed':stages['review']['completed'],
        'required':False,'name':'Calibration setup records',
        'status':'Complete' if stages['review']['completed'] else 'Requires attention',
        'detail':'Saved setup observations are not physical certification. Missing optional diagnostic records do not themselves replace experiment preflight.',
        'action':'Review saved calibration','destination':'calibration','stage':'review'})
    by_key = {row['key']:row for row in requirements}
    if 'luminance' in by_key:
        row=by_key['luminance']
        from .calibration_dataset import luminance_state,load_active
        try:
            row['status']=luminance_state(profile,load_active(config_root(repo_root),profile))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            row['status']='Saved dataset requires inspection'
            row['detail']='Active luminance dataset could not be read: ' + str(exc) + '. ' + row['detail']
        count=len(profile.luminance_calibration)
        synthetic=photometry_is_test_data(profile)
        row['detail']=f'{count} intensity/luminance pairs saved. ' + (
            'Their recorded source is synthetic/test: researcher acceptance does NOT make '
            'them measured photometry. ' if synthetic else ''
        ) + row['detail']
        if not row['passed'] and (count<2 or synthetic):
            row.update(destination='calibration',stage='luminance',
                       action='Record real photometer readings' if synthetic
                       else 'Add at least two measured luminance pairs')
        elif not row['passed']:
            row.update(destination='verification',
                       action='Review physical photometry declaration')
    if 'geometry' in by_key and not by_key['geometry']['passed'] and not stages['geometry']['measurement_recorded']:
        by_key['geometry'].update(destination='calibration',stage='geometry',action='Record a ruler measurement')
    configuration_error=None
    try:
        validate_setup(request,spec,profile,mode='configuration')
    except (ValueError,TypeError,KeyError) as exc:
        configuration_error=str(exc)
        target=next((field.key for field in spec.fields if field.key in configuration_error), None)
        if target is None and 'luminance' in configuration_error.lower():
            target='Background_Screen_intensity' if spec.id=='contrast_sensitivity' else None
        requirements.append({'key':'configuration','passed':False,'required':True,
            'name':'Reviewed configuration','status':'Blocked','detail':configuration_error,
            'action':'Review current settings','destination':'settings','field':target})
    if configuration_error is None:
        requirements.append({'key':'configuration','passed':True,'required':True,'name':'Reviewed configuration',
            'status':'Complete','detail':'Current settings validate. Physical display and acquisition requirements remain separate.',
            'action':'Review current settings','destination':'settings','field':'starting_probe_intensity' if spec.id=='contrast_sensitivity' else None})
    from simulations.scenarios import list_scenarios
    simulation_available = configuration_error is None and bool(list_scenarios(spec.id))
    if request.participant_id=='synthetic_preview':
        requirements.append({'key':'participant','passed':False,'required':True,'name':'Human participant identity',
            'status':'Blocked','detail':'Provide a pseudonymous human participant ID before human acquisition; simulation remains separate.',
            'action':'Edit participant','destination':'participant'})
    for category in ('geometry','luminance','timing'):
        if category not in by_key:
            requirements.append({'key':category,'passed':True,'required':False,'name':category.title()+' laboratory verification',
                'status':'Not required','detail':'Not required by this experiment/profile compatibility policy; no new physical certification is inferred.',
                'action':'','destination':'verification'})
    blockers=[row for row in requirements if row['required'] and not row['passed']]
    return {'human_ready':not blockers,'simulation_available':simulation_available,
            'simulation_detail':configuration_error or ('Registered virtual observer available; no physical certification required.' if simulation_available else 'No registered virtual-observer scenario for this experiment.'),
            'requirements':requirements,'blockers':blockers,
            'profile_sha256':content_hash(profile.to_dict())}
