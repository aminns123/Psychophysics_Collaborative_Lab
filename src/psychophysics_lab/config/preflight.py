"""Configuration validity and human qualification are distinct boundaries."""
from dataclasses import replace
from .local import content_hash
from ..data.participants import validate_participant_id


def compatible(spec, profile) -> bool:
    """Retained public qualification policy; never used to hide available profiles."""
    return not spec.compatible_monitor_profiles or profile.id in spec.compatible_monitor_profiles or spec.id in profile.qualified_experiments


def qualification_checks(spec, profile, values=None):
    """Shared experiment-owned laboratory requirements, not automatic certification.

    Stored Verified flags are researcher declarations. Configuration checks
    remain separate and use the same validator as final acquisition preflight.
    """
    spec = effective_requirements(spec)
    from .models import photometry_is_test_data
    capabilities = spec.monitor_capabilities if spec.procedure is not None else ("display_binding", "resolution")
    checks = []
    if capabilities:
        passed = ("display_binding" not in capabilities or (profile.origin == "local" and bool(profile.display_binding))) and ("resolution" not in capabilities or bool(profile.expected_resolution_px))
        checks.append({"key":"binding", "name": "Required physical display capabilities", "passed": passed,
                       "detail": "Save the required display binding and pixel resolution on Display: " + ", ".join(capabilities)})
    for key in spec.calibration_requirements:
        if key == "geometry":
            passed = profile.geometry_status == "verified" and all(profile.measurement_sources.get(field) == "manual" for field in ("physical_width_m","physical_height_m","viewing_distance_m"))
            detail = "Review measured screen dimensions, eye distance and ruler error; declare geometry verified under laboratory criteria."
        elif key == "luminance":
            passed = len(profile.luminance_calibration) >= 2 and profile.has_verified_luminance_mapping and bool(profile.calibration_method.strip()) and not photometry_is_test_data(profile)
            detail = "Physical photometry needs genuine saved observations and explicit verification. Fake/synthetic methods cannot qualify human acquisition."
        else:
            passed = profile.timing_status == "verified"
            detail = "Review independent photon-timing instrument evidence and explicitly declare timing verified. Software flips are insufficient."
        checks.append({"key":key, "name": key.title() + " laboratory verification (manually declared)", "passed": passed, "detail": detail})
    if values is not None:
        from .models import SetupRequest
        try:
            validate_setup(SetupRequest("calibration_review", "new", spec.id, profile.id, values), spec, profile, mode="configuration")
        except (ValueError, TypeError, KeyError) as exc:
            checks.append({"name": "Current experiment configuration", "passed": False, "detail": str(exc)})
        else:
            checks.append({"name": "Current experiment configuration", "passed": True, "detail": "Current settings validate; acquisition still checks response/range safeguards."})
        # The same contrast row used at human launch also applies to explicit
        # review of a current CSF configuration. No separate range formula.
        checks.extend({"key":row["key"],"name":row["name"],"passed":row["passed"],"detail":row["detail"]}
                      for row in human_requirements(spec,profile,values) if row["key"] == "contrast")
    return checks


def human_requirements(spec, profile, values=None):
    """One source for human blockers and their targeted resolution actions."""
    spec = effective_requirements(spec)
    rows=[]
    def add(key,name,passed,detail,destination,*,field=None,stage=None,required=True):
        if passed:
            detail = {"qualification":"Explicit qualification declared or retained historical compatibility policy; final preflight still applies.",
                "binding":"Saved local display binding and pixel resolution; the actual connected mode is checked at launch.",
                "geometry":"Geometry is manually declared verified using laboratory criteria; PsyCoLab does not independently measure it.",
                "luminance":"Photometer mapping is manually declared verified with recorded instrument/method; the software does not independently certify it.",
                "timing":"Photon timing is manually declared verified from independent laboratory evidence, not software flips.",
                "sampling":"Expected fullscreen pixel resolution is saved; sampling and actual mode remain checked."}.get(key,detail)
        rows.append({"key":key,"name":name,"passed":passed,"required":required,
            "status":"Verified" if passed and key in {"geometry","luminance","timing"} else "Complete" if passed else "Saved but unverified" if key in {"geometry","luminance","timing"} else "Blocked",
            "detail":detail,"destination":destination,"field":field,"stage":stage,
            "action": {"verification":"Review physical " + ("photometry" if key=="luminance" else key),"qualification":"Check experiment requirements","settings":"Edit contrast settings","calibration":"Open " + (stage or "display") + " calibration"}[destination]})
    add("qualification","Experiment qualification",compatible(spec,profile),
        "This experiment/profile combination has not been qualified. Explicitly review the registered experiment requirements; calibration completion does not qualify human acquisition.","qualification")
    if spec.acquisition_block_reason:
        add("protocol", "Protocol not qualified for acquisition", False,
            spec.acquisition_block_reason + " This is a protocol-level qualification limit; marking a monitor Verified does not remove it.", "qualification")
    if spec.procedure is not None and spec.monitor_validator is not None and values:
        notes = display_configuration_notes(spec, profile, values)
        add("sampling", "Configured conditions on this physical display", not notes,
            "\n".join(notes) if notes else "Configured condition frequencies fit the saved display sampling.", "settings")
        rows[-1]["action"] = "Review condition settings"
    from .models import photometry_is_test_data
    if profile.origin=="local" or spec.procedure is not None:
        for check in qualification_checks(spec,profile):
            key=check['key']
            if key=="binding" and not profile.display_binding:
                check=dict(check,detail="This local profile is an UNBOUND DRAFT. Detect connected displays, select the actual monitor and save its binding/resolution on Display.")
            add(key,check['name'],check['passed'],check['detail'],"calibration" if key=="binding" else "verification",stage="bind" if key=="binding" else None)
    if "luminance" in spec.calibration_requirements and photometry_is_test_data(profile) and not any(row['key']=='luminance' for row in rows):
        add("luminance","Physical photometry",False,"Fake/synthetic photometry cannot support human acquisition.","verification")
    pass  # Retired protocol branch removed.
    return rows


def human_blockers(spec, profile, values=None):
    return tuple(row['detail'] for row in human_requirements(spec,profile,values) if row['required'] and not row['passed'])


def display_configuration_notes(spec, profile, values):
    """Nonblocking feedback while designing/simulating; physical launch checks it.

    The experiment owns which configured quantities must be checked. Cropping,
    blank/control stimuli and target visibility are researcher choices.
    """
    if spec.monitor_validator is None:
        return ()
    try:
        spec.monitor_validator(values, profile)
    except (ValueError, TypeError, KeyError) as exc:
        return (str(exc),)
    return ()


def effective_requirements(spec, snapshots=None):
    """Union experiment and selected stimulus requirements at every UI/run boundary."""
    if not spec.stimulus_slots or spec.procedure is None:
        return spec
    from ..stimuli.registry import get_stimulus
    requirements = set(spec.calibration_requirements)
    defaults = dict(spec.stimulus_defaults)
    for slot in spec.stimulus_slots:
        selected = (snapshots or {}).get(slot)
        identity = selected['document']['stimulus_id'] if selected else spec.stimulus_defaults[slot]
        defaults[slot] = identity
        requirements.update(get_stimulus(identity).calibration_requirements)
    return replace(spec, calibration_requirements=tuple(sorted(requirements)),
        stimulus_defaults=defaults,
        calibration_not_applicable=spec.calibration_not_applicable if not requirements else '',
        monitor_capabilities=tuple(sorted(set(spec.monitor_capabilities or ()) | {'display_binding', 'resolution'})))


def validate_setup(request, spec, profile, *, mode="human"):
    """Default preserves strict public preflight; UI must name configuration/simulation mode."""
    if mode not in {"human", "configuration", "simulation"}:
        raise ValueError("Unknown acquisition validation mode.")
    participant=validate_participant_id(request.participant_id)
    if (mode == "human" and request.researcher_override is not None
            and participant.lower().startswith(("synthetic_", "presentation_test_"))):
        raise ValueError("Provide a human participant ID; synthetic/test identities are reserved.")
    if mode == "simulation" and request.researcher_override is not None:
        raise ValueError("Researcher overrides apply only to human acquisition.")
    if request.session_mode not in {'new','reuse'}:
        raise ValueError('Unknown starting-settings mode.')
    profile.validate()
    if request.experiment_id != spec.id:
        raise ValueError('Selected experiment identity differs from request.')
    if request.monitor_profile_id!=profile.id:
        raise ValueError('Selected profile identity differs from request.')
    if request.monitor_profile_hash and request.monitor_profile_hash!=content_hash(profile.to_dict()):
        raise ValueError('Display profile changed since review. Return to configuration, refresh the display and Review again.')
    values=spec.normalise_values(request.experiment_values)
    from .stimulus_parameters import resolve_stimuli
    snapshots = resolve_stimuli(spec, values, request.stimulus_snapshots)
    spec = effective_requirements(spec, snapshots)
    if spec.procedure is not None and profile.expected_resolution_px:
        from ..core.presentation import validate_geometry
        from ..stimuli.registry import get_stimulus
        for selected in snapshots.values():
            document = selected['document']
            validate_geometry(profile, profile.expected_resolution_px, get_stimulus(document['stimulus_id']), document['parameters'])
    if spec.monitor_validator and (mode == "human" or spec.historical):
        spec.monitor_validator(values,profile)
    request = replace(request,participant_id=participant,experiment_values=values,monitor_profile_hash=content_hash(profile.to_dict()), stimulus_snapshots=snapshots)
    if mode == "human":
        from .researcher_override import outstanding_requirements, validate_researcher_override
        outstanding = outstanding_requirements(spec, profile, values)
        waived = (validate_researcher_override(request, profile, outstanding)
                  if request.researcher_override is not None else ())
        blockers = tuple(row['detail'] for row in outstanding if row['key'] not in waived)
        if blockers:
            raise ValueError("Human acquisition blocked:\n" + "\n".join(blockers))
    return request
