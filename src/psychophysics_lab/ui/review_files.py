"""Locate real parameter sources. Never invent editable derived parameters."""
import ast
import inspect
import json
from pathlib import Path
from uuid import uuid4
from .parameter_files import working_path,ensure_json,load_experiment_json
from ..config.stimulus_parameters import load_parameters
from ..stimuli.registry import get_stimulus
from .settings_review import parameter_sources, parameter_controller


def definition_line(path, *, key=None, owner=None, function=None):
    try:
        tree=ast.parse(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError,SyntaxError,UnicodeError):
        return 1
    if owner:
        tree=next((node for node in ast.walk(tree) if isinstance(node,ast.ClassDef) and node.name==owner),tree)
    for node in ast.walk(tree):
        if key and isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id==key for target in node.targets):
            return node.lineno
        if function and isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==function:
            return node.lineno
        if key and isinstance(node,ast.Call) and node.args and isinstance(node.args[0],ast.Constant) and node.args[0].value==key:
            name=node.func.id if isinstance(node.func,ast.Name) else getattr(node.func,"attr","")
            if name=="ConfigField":
                return node.lineno
    return getattr(tree,"lineno",1)


def json_value_line(path, key):
    """Find the exact parameter key inside a JSON values/parameters object.

    This returns a *navigation hint*, not an editable JSON parser. Use the
    existing JSON loading/validation code for actual scientific values.
    """
    if not key or path is None:
        return 1
    try:
        lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError):
        return 1
    # Generated and imported JSON can have different indentation. Match
    # the key under its data section, not a duplicate inside parameter_info.
    import re
    section = re.compile(r'^\s*"(?:values|parameters)"\s*:\s*\{')
    wanted = re.compile(r'^\s*"' + re.escape(str(key)) + r'"\s*:')
    for index, line in enumerate(lines):
        if not section.search(line):
            continue
        level = len(line) - len(line.lstrip())
        for offset in range(index + 1, len(lines)):
            candidate = lines[offset]
            if wanted.search(candidate):
                return offset + 1
            if candidate.strip().startswith("}") and len(candidate) - len(candidate.lstrip()) <= level:
                break
    return 1


from ..extensions import source_path

def experiment_source(spec,root):
    try:
        source=inspect.getsourcefile(spec.procedure) if spec.procedure else None
    except TypeError:
        source=None
    candidates=([Path(source)] if source else [])+[source_path(root, spec, relative) for relative in spec.source_paths]
    return next((path.resolve() for path in candidates if path.is_file()),None)


def actual_json_sources(app,request):
    """Prefer known loaded files; infer no absolute path from a portable snapshot."""
    from psychophysics_lab.experiments._internal.registry import get_experiment
    spec=get_experiment(request.experiment_id)
    tracked=app.review_parameter_files.get(app.settings_key(request),{})
    experiment=None
    for name in tracked:
        path=Path(name)
        try:
            if load_experiment_json(path,spec)==request.experiment_values:
                experiment=path
                break
        except (ValueError,OSError,TypeError,UnicodeError):
            pass
    if experiment is None and spec.default_config:
        candidate=source_path(app.repo_root, spec, spec.default_config)
        try:
            if load_experiment_json(candidate,spec)==request.experiment_values:
                experiment=candidate
        except (ValueError,OSError,TypeError,UnicodeError):
            pass
    stimuli={}
    for slot,selected in request.stimulus_snapshots.items():
        cached=app.stimulus_drafts.get((request.participant_id,spec.id,request.monitor_profile_id,slot))
        candidates=([Path(cached[1])] if cached and cached[1] else [])+[Path(name) for name in tracked]
        stimulus=get_stimulus(selected["document"]["stimulus_id"])
        if stimulus.default_config:
            candidates.append(source_path(app.repo_root, stimulus, stimulus.default_config))
        for path in candidates:
            try:
                loaded=load_parameters(path,stimulus)
                if loaded["document"]["parameters"]==selected["document"]["parameters"]:
                    stimuli[slot]=path
                    break
            except (ValueError,OSError,TypeError,UnicodeError):
                pass
    return {"experiment":experiment,"stimuli":stimuli}


def targets_for_rows(spec,snapshots,description,rows,sources,root):
    source=experiment_source(spec,root)
    def python(path=source,*,key=None,owner=None,function=None,note="Defined in Python; save changes, then Refresh (F5)"):
        if path is None:
            return dict(kind="unavailable",path=None,line=1,note="This component records no inspectable source file; file navigation is unavailable for this row")
        return dict(kind="python",path=Path(path),line=definition_line(path,key=key,owner=owner,function=function),note=note)
    def experiment(key=None):
        return dict(kind="experiment_json",path=sources["experiment"],key=key,
            line=json_value_line(sources["experiment"], key),
            note="Edit ordinary JSON, save, then Reload files" if sources["experiment"] else "Unsaved TUI values; Enter saves an ordinary JSON copy and opens it")
    fields={field.display_label:field for field in spec.fields}
    targets=[]
    for group,label,value,origin in rows:
        if group in {"Experiment", "Adaptive"} and label in fields:
            field=fields[label]
            targets.append(experiment(field.key) if field.editable else python(key=field.key))
        elif group in snapshots:
            slot=group
            stimulus=get_stimulus(snapshots[slot]["document"]["stimulus_id"])
            field=next((field for field in stimulus.parameters if field.display_label==label),None)
            binding=parameter_controller(spec,slot,field.key) if field else None
            if field is None and label=="Stimulus" and slot not in sources["stimuli"] and snapshots[slot]["file_identity"]=="library_defaults":
                targets.append(python(key="STIMULUS_DEFAULTS",note="Default stimulus selection is declared by the experiment Python"))
            elif binding:
                targets.append(experiment(binding))
            elif field and field.key in parameter_sources(description,slot):
                targets.append(python(function="prepare_stimuli",note="Trial-controlled value: edit the experiment procedure, not a preset"))
            elif slot in sources["stimuli"]:
                targets.append(dict(kind="stimulus_json",path=sources["stimuli"][slot],slot=slot,key=field.key if field else None,
                    line=json_value_line(sources["stimuli"][slot], field.key if field else None),
                    note="Selected stimulus JSON; save and Reload files"))
            elif (snapshots[slot]["file_identity"]=="library_defaults"
                  and snapshots[slot]["document"]["parameters"]=={field.key:field.default for field in stimulus.parameters}):
                owner=stimulus.render.__qualname__.split(".")[0] if stimulus.render else None
                targets.append(python(source_path(root, stimulus, stimulus.source_path),key=field.key if field else None,owner=owner,
                    note="Stimulus class defaults; save Python changes, then Refresh (F5) to apply updated defaults"))
            else:
                targets.append(dict(kind="stimulus_json",path=None,slot=slot,key=field.key if field else None,line=1,
                    note="Saved snapshot without its original file; Enter saves an ordinary JSON copy"))
        elif group in {"Intensity","Contrast","Adaptive scale"}:
            path=Path(__file__).with_name("settings_review.py")
            targets.append(python(path,function="probe_intensity_rows",note="Derived display value; this function calculates it from the experiment settings above"))
        elif group in {"Stimulus geometry", "Viewport"}:
            targets.append(python(Path(__file__).parents[1]/"core/viewport.py",
                function="stimulus_geometry" if group=="Stimulus geometry" else "angular_viewport",
                note="Derived geometry; change the scientific inputs above, not this displayed result"))
        elif group=="Threshold estimation":
            targets.append(python(function="primary_rule",
                                  note="Thresholds are estimated from recorded responses; this is the experiment's declared analysis rule"))
        elif group=="Run plan":
            targets.append(python(function="initialise_experiment",note="Resolved from the experiment planning code and selected settings"))
        elif group=="Adaptive":
            targets.append(python(key="adaptive",note="Adaptive selection declared by the experiment Python"))
        elif group=="Responses":
            targets.append(python(key="RESPONSES",note="Alternative meanings are declared by the experiment; response keys are settings above"))
        elif group=="Conditions":
            targets.append(python(function="make_conditions",note="Derived condition list; edit its settings above or the experiment's make_conditions"))
        elif group=="Session start (once)":
            event_name, _, attribute = label.rpartition(" ")
            key = description.get("session_inputs", {}).get(event_name, {}).get(attribute)
            if isinstance(key, str) and key in {f.key for f in spec.fields}:
                targets.append(experiment(key))
            else:
                targets.append(python(key="SESSION_START", note="Once-only event declaration; selected input fields are editable in Configure"))
        elif group=="Trial" and label.endswith(" planned display"):
            targets.append(python(Path(__file__).parents[1]/"core/presentation.py",function="presentation_frames",
                note="Derived frame count from requested duration and monitor refresh rate; edit those inputs"))
        elif group=="Trial" and label.endswith(" duration") and description.get("phase_inputs",{}).get(label[:-9]) in {f.key for f in spec.fields}:
            targets.append(experiment(description["phase_inputs"][label[:-9]]))
        else:
            targets.append(python(function=description.get("trial_event_function", "make_trial") if group in {"Trial","Trial action","Audio"} else None))
    return targets


def export_current_json(root,spec,document,slot=None):
    """Explicit export, never an implicit mandatory configuration or overwrite."""
    candidate=working_path(root,spec.id,slot)
    if candidate.exists():
        try:
            if slot is None:
                matches=load_experiment_json(candidate,spec)==document["values"]
            else:
                stimulus=get_stimulus(document["stimulus_id"])
                matches=load_parameters(candidate,stimulus)["document"]["parameters"]==document["parameters"]
        except (ValueError,OSError,TypeError,UnicodeError):
            matches=False
        if matches:
            return candidate
        candidate=candidate.with_name(candidate.stem+"_"+uuid4().hex[:10]+".json")
    ensure_json(candidate,document)
    return candidate
