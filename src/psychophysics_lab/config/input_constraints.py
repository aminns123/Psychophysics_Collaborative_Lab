"""Live explanatory domains, backed by the same specification/preflight validators."""
from .models import SetupRequest
from .preflight import validate_setup


def experiment_constraints(spec,profile,raw):
    reports={}; parsed={}; errors=[]
    for field in spec.fields:
        domain='Allowed choices: '+', '.join(map(str,field.choices)) if field.kind=='choice' else (
            ('Whole number' if field.kind=='int' else 'Finite number')+f"; range {field.minimum if field.minimum is not None else 'no declared lower bound'} to {field.maximum if field.maximum is not None else 'no declared upper bound'}" if field.kind in ('int','float') else 'Text; '+field.help_text)
        report={'domain':domain,'error':'','classification':'fixed / experiment specification'}
        try: parsed[field.key]=field.coerce(raw.get(field.key))
        except (ValueError,TypeError) as exc: report['error']=str(exc)
        reports[field.key]=report
    if spec.id=='contrast_sensitivity':
        for key in ('logUNIT_UP','logUNIT_DW'):
            reports[key]['domain']='Allowed: finite > 0 in legacy log10 contrast units; upward steps remain subject to the runtime shader guard.'
        for key in ('timeFixate','timeInterval','timeAB'):
            reports[key]['domain']='Allowed: whole milliseconds ≥ 1; zero stalls this keyless phase.'
        reports['timeT']['domain']='Allowed: whole milliseconds ≥ 0; 0 is self-paced response.'
        try:
            from ..stimuli.contrast_validation import starting_contrast_limits
            limits=starting_contrast_limits(parsed['Background_Screen_intensity'],parsed['starting_probe_intensity'],parsed['logUNIT_UP'])
            reports['starting_probe_intensity']['domain']=f"Allowed range: {limits['minimum_starting']:.3f}–{limits['maximum_starting']:.3f} (current shader)"
            reports['starting_probe_intensity']['classification']='multiple values: background + shader'
            if not limits['initial_valid']: reports['starting_probe_intensity']['error']='Outside the current shader range. Retain and correct the entered value; no clamping.'
        except (ValueError,KeyError): pass
        if 'Max_monitor_Luminance' in parsed:
            reports['Background_Luminance']['domain']=f"Allowed: ≥ 0 and < {parsed['Max_monitor_Luminance']:g} cd/m²; verified mapping requires the measured pair."
        reports['Background_Screen_intensity']['domain']='Allowed range: 0 ≤ intensity < 1; background and starting intensity jointly determine contrast.'
        try:
            from ..experiments.contrast_sensitivity import resolved_condition_frequencies
            frequencies=resolved_condition_frequencies(parsed['condition_values'],parsed['condition_unit'])
            reports['number_conditions']['domain']=f'Allowed: exactly {len(frequencies)} for these condition values (1–24).'
            if parsed.get('number_conditions')!=len(frequencies): reports['number_conditions']['error']='Condition count must match the entered frequency list.'
            if parsed['condition_unit']!='legacy_shader_radians' and profile.expected_resolution_px:
                from ..stimuli.spatial_calibration import resolve_spatial_geometry,validate_requested_cpd
                geometry=resolve_spatial_geometry(profile,profile.expected_resolution_px)
                maximum=min(1000,*geometry.nyquist_cpd_at_centre)
                reports['condition_values']['domain']=f'Physical frequency: > 0 and ≤ {maximum:.6g} cpd; depends on measured dimensions, viewing distance and pixels. Period input uses reciprocal cpd.'
                reports['condition_values']['classification']='monitor + input units + experiment'
                try: validate_requested_cpd(frequencies,geometry)
                except ValueError as exc: reports['condition_values']['error']=str(exc)
        except (ValueError,KeyError) as exc:
            if isinstance(exc,ValueError): reports['condition_values']['error']=str(exc)
        endpoint=next((p.luminance_cdm2 for p in profile.luminance_calibration if p.screen_intensity==1),None)
        if endpoint is not None: reports['Max_monitor_Luminance']['domain']=f'Measured full-command endpoint: {endpoint:g} cd/m²; enforced for a verified mapping.'
    if len(parsed)==len(spec.fields):
        try: validate_setup(SetupRequest('input_preview','new',spec.id,profile.id,parsed),spec,profile,mode='configuration')
        except (ValueError,TypeError) as exc:
            errors=str(exc).splitlines()
            for message in errors:
                matching=[f.key for f in spec.fields if f.key.lower() in message.lower() or f.label.split(' (')[0].lower() in message.lower()]
                if not matching and spec.id=='contrast_sensitivity':
                    aliases={'up-step':'logUNIT_UP','down-step':'logUNIT_DW','n-down':'n_down','n-up':'n_up','reversal':'reversal_termination','maximum responses':'max_trials','background luminance':'Background_Luminance','maximum luminance':'Max_monitor_Luminance','background screen':'Background_Screen_intensity','staircases per':'staircases_per_condition','measured full-command':'Max_monitor_Luminance','luminance':'Background_Luminance'}
                    matching=[key for phrase,key in aliases.items() if phrase in message.lower()]
                for key in matching: reports[key]['error']=message
    return reports,errors
