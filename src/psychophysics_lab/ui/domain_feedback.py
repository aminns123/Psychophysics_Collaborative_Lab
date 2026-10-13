"""Shared visible domains for calibration/profile controls, with pure validators."""
import math
from textual.widgets import Input,Select,Static,Button


def show_domains(screen,domains,errors=()):
    lines=[]
    for widget in screen.query('Input, Select'):
        if isinstance(widget,Select):
            widget.tooltip='Choose one of the displayed options; changing dependencies revalidates the draft.'
            continue
        domain=domains.get(widget.id)
        if domain:
            widget.tooltip=domain
            lines.append(widget.id.replace('geometry-','').replace('profile-','')+': '+domain)
    target=screen.query('#live-input-domains')
    if target: target.first().update('Allowed input domains (updated from current settings):\n'+'\n'.join(lines)+'\n'+'\n'.join(errors))


def profile_domains(screen):
    from ..config.monitor import _profile_from_dict
    from ..stimuli.spatial_calibration import resolve_spatial_geometry
    domains={}; payload=screen.profile.to_dict(); errors=[]
    for key in ('physical_width_m','physical_height_m','viewing_distance_m','refresh_rate_hz','pyglet_wakeup_rate_hz'):
        widget=screen.query_one('#profile-'+key,Input); domains[widget.id]='Finite > 0; manually measured dimensions/distance, OS or manual rate.'
        try:
            value=float(widget.value)
            if not math.isfinite(value) or value<=0: raise ValueError('must be positive and finite')
            payload[key]=value; widget.remove_class('invalid-input')
        except ValueError as exc: errors.append(key+': '+str(exc)); widget.add_class('invalid-input')
    pixels=[screen.query_one('#profile-pixel-'+dimension,Input) for dimension in ('width','height')]
    try:
        if any(p.value.strip() for p in pixels):
            values=[float(p.value) for p in pixels]
            if any(not math.isfinite(v) or not v.is_integer() or v<=0 for v in values): raise ValueError('Both pixel dimensions must be positive integers, or both blank.')
            payload['expected_resolution_px']=[int(v) for v in values]
        else: payload['expected_resolution_px']=None
        for p in pixels: p.remove_class('invalid-input')
    except ValueError as exc:
        errors.append(str(exc))
        for p in pixels: p.add_class('invalid-input')
    for p in pixels: domains[p.id]='Positive integer pixels; enter both dimensions or leave both blank.'
    if not errors:
        try:
            profile=_profile_from_dict(payload)
            if profile.expected_resolution_px:
                calibration=resolve_spatial_geometry(profile,profile.expected_resolution_px)
                errors.append(f"Current geometry: Nyquist X={calibration.nyquist_cpd_at_centre[0]:.6g}, Y={calibration.nyquist_cpd_at_centre[1]:.6g} cpd. Changes invalidate dependent evidence; no OS physical certification.")
        except ValueError as exc: errors.append(str(exc))
    invalid=any(w.has_class('invalid-input') for w in screen.query(Input))
    screen.query_one('#profile-save',Button).disabled=invalid
    show_domains(screen,domains,errors)


def diagnostic_domains(screen):
    profile=screen._profile(); domains={}; errors=[]
    rules={'geometry-value':(0,None,True),'geometry-thickness':(0,None,True),'geometry-duration':(0,None,False),
        'geometry-spatial':(0,None,True),'geometry-temporal':(0,profile.refresh_rate_hz/2,True),
        'geometry-luminance':(0,1,False),'geometry-luminance-background':(0,1,False),'geometry-luminance-step':(0,1,True),
        'geometry-measured':(0,None,True),'geometry-x':(None,None,False),'geometry-y':(None,None,False)}
    if profile.expected_resolution_px:
        from ..stimuli.spatial_calibration import resolve_spatial_geometry
        limit=min(resolve_spatial_geometry(profile,profile.expected_resolution_px).nyquist_cpd_at_centre)
        rules['geometry-spatial']=(0,limit,True)
    for key,(minimum,maximum,strict) in rules.items():
        widget=screen.query_one('#'+key,Input)
        domains[key]=f"Finite; {'>' if strict else '≥'} {minimum}" if minimum is not None else 'Finite position; must fit on the selected monitor with the stimulus.'
        if maximum is not None: domains[key]+=f'; ≤ {maximum:g}'
        if key=='geometry-luminance-background': domains[key]='Finite 0 ≤ background < 1'
        try:
            if key=='geometry-measured' and not widget.value.strip(): continue
            v=float(widget.value)
            if not math.isfinite(v) or minimum is not None and (v<=minimum if strict else v<minimum) or maximum is not None and v>maximum or key=='geometry-luminance-background' and v==1: raise ValueError(domains[key])
            widget.remove_class('invalid-input')
        except ValueError as exc: widget.add_class('invalid-input'); errors.append(key+': '+str(exc))
    if profile.expected_resolution_px:
        from ..stimuli.spatial_calibration import resolve_spatial_geometry
        from ..stimuli.geometry import visual_angle_for_physical_length
        geometry=resolve_spatial_geometry(profile,profile.expected_resolution_px)
        domains['geometry-spatial']=f'Finite > 0; ≤ {min(geometry.nyquist_cpd_at_centre):.6g} cpd from current geometry.'
        dimension=profile.physical_width_m if str(screen.query_one('#geometry-orientation',Select).value)=='horizontal' else profile.physical_height_m
        unit=str(screen.query_one('#geometry-mode',Select).value)
        domains['geometry-value']=f"Finite > 0; monitor fit limit {visual_angle_for_physical_length(dimension,profile.viewing_distance_m):.6g} degrees" if unit=='visual_angle_deg' else f'Finite > 0; monitor fit limit {dimension*1000:.6g} mm'
        try:
            from ..core.display_tests import resolve_test
            resolve_test(profile,screen._request(),profile.expected_resolution_px)
        except ValueError as exc:
            errors.append(str(exc))
            kind=str(screen.query_one('#geometry-test',Select).value)
            target='geometry-spatial' if kind=='spatial' else 'geometry-temporal' if kind.startswith('temporal_') else 'geometry-luminance' if kind=='luminance_patch' else 'geometry-value'
            screen.query_one('#'+target,Input).add_class('invalid-input')
            if kind=='position':
                for key in ('geometry-x','geometry-y'): screen.query_one('#'+key,Input).add_class('invalid-input')
    try:
        from ..core.luminance_session import validate_luminance_session
        validate_luminance_session(screen._luminance_request(),profile)
    except ValueError as exc: errors.append('Photometer sweep: '+str(exc))
    show_domains(screen,domains,errors)


def observer_domain(experiment_id,key,value):
    if experiment_id=='contrast_sensitivity':
        if key=='lapse': return 'finite 0 ≤ lapse < 0.5'
        if key in ('threshold','preferred_condition','tuning_width_octaves','slope'): return 'positive finite number'
    if isinstance(value,bool): return 'true or false'
    if isinstance(value,int): return 'whole number; selected observer validates its domain'
    if isinstance(value,float): return 'finite number; selected observer validates its domain'
    return 'declared JSON/value type; selected observer validates its domain'
