"""Structured human readiness from authoritative preflight, separate from simulation."""
from .local import config_root, content_hash
from .preflight import human_requirements, validate_setup
from .calibration_progress import calibration_progress
from .models import photometry_is_test_data


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
        count=len(profile.luminance_calibration)
        row['detail']=f'{count} intensity/luminance pairs saved. ' + ('Recorded method labels these as synthetic/test data; they cannot verify physical photometry. ' if photometry_is_test_data(profile) else '') + row['detail']
    if 'geometry' in by_key and not by_key['geometry']['passed'] and not stages['geometry']['measurement_recorded']:
        by_key['geometry'].update(destination='calibration',stage='geometry',action='Record a ruler measurement')
    if 'luminance' in by_key and not by_key['luminance']['passed'] and (len(profile.luminance_calibration)<2 or photometry_is_test_data(profile)):
        by_key['luminance'].update(destination='calibration',stage='luminance',action='Record genuine photometer observations')
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
