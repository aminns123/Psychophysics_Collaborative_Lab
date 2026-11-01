"""Real frozen/current execution; no scientific fields removed from comparisons."""
from contextlib import contextmanager
from dataclasses import replace
import importlib
import json
from pathlib import Path
import sys
import types
from psychophysics_lab.experiments._internal import registry
from psychophysics_lab.data.reader import load_run
from simulations.run import simulate
from simulations.registry import TeachingObserver
from scripts.validate_run import validate_run
ROOT=Path(__file__).resolve().parents[1]


def install_archived_detection_reference(patch):
    """Isolate the exact pre-207 runner dependencies within old-fixture tests.

    Current PsyCoLab never registers the retired scene or method. A frozen old
    study must be exercised with its *own* frozen method and headroom code,
    rather than mistakenly calling current atomic method signatures.
    """
    from _archived_detection_scene import DetectionScene
    from psychophysics_lab import stimulus_library
    from psychophysics_lab.stimuli import registry as stimulus_registry
    from psychophysics_lab.experiments._internal import detection_limits
    from psychophysics_lab.methods import probe as probe_methods

    patch.setattr(stimulus_library, "DetectionScene", DetectionScene, raising=False)
    patch.setitem(stimulus_registry._REGISTRY, "detection_scene", DetectionScene.SPEC)
    root = ROOT / "outdated_code/pre_atomic_207/src/psychophysics_lab"

    old_limits = root / "experiments/_internal/detection_limits.py"
    scope = {"__name__": "_historical_detection_limits",
             "__file__": str(old_limits)}
    exec(compile(old_limits.read_bytes(), str(old_limits), "exec"), scope)
    patch.setattr(detection_limits, "resolve_probe_limits",
                  scope["resolve_probe_limits"])
    patch.setattr(detection_limits, "probe_limit", scope["probe_limit"],
                  raising=False)

    old_methods = root / "methods/probe.py"
    methods_scope = {
        "__name__": "psychophysics_lab.methods.probe",
        "__package__": "psychophysics_lab.methods",
        "__file__": str(old_methods),
    }
    exec(compile(old_methods.read_bytes(), str(old_methods), "exec"),
         methods_scope)
    for key in (
        "probe_constant_method", "probe_contrast_fields",
        "fixed_contrast_levels", "make_probe_fixed_schedule",
        "validate_probe_fixed_settings",
    ):
        patch.setattr(probe_methods, key, methods_scope[key])


@contextmanager
def reference(patch, wave, identity, old, opening=True):
    registry.list_experiments()
    parent=importlib.import_module('psychophysics_lab.experiments')
    names = ('contrast_sensitivity','contrast_sensitivity_windowed') if wave==3 else (identity,)
    # Import current authored modules *before* temporarily overriding
    # historical shared methods. Otherwise a cold test registry can bind the
    # archived method functions permanently into a live module on import.
    live_modules = {
        name: importlib.import_module('psychophysics_lab.experiments.'+name)
        for name in names
    }
    if old and wave in (4, 5):
        install_archived_detection_reference(patch)
    for name in names:
        live=live_modules[name]
        module=live
        if old:
            path=ROOT/'tests/fixtures'/('issue165_wave'+str(wave))/(name+'.py')
            module=types.ModuleType(live.__name__);module.__file__=live.__file__
            exec(compile(path.read_bytes(),module.__file__,'exec'),module.__dict__)
            patch.setitem(sys.modules,module.__name__,module)
            patch.setattr(parent,name,module)
        spec=module.SPEC if opening else replace(module.SPEC,session_start=[])
        patch.setitem(registry._REGISTRY,name,spec)
    yield registry.get_experiment(identity)

def scientific_trial_actions(path):
    """Compare trial science while treating composited slot names as provenance.

    Pixel equivalence for the independent objects is checked separately in
    test_atomic_stimulus_parity. Do not erase state, alternative, event
    chronology or adaptive updates from this comparison.
    """
    recorded = json.loads(path.read_text(encoding="utf-8"))
    invariant = ("trial_index", "condition", "target",
                 "initial_state", "final_state", "status")

    def phase(phase):
        fields = ("name", "kind", "duration_ms", "beep", "key",
                  "actions", "trigger", "response")
        return {key: phase[key] for key in fields if key in phase}

    return [
        {key: trial[key] for key in invariant if key in trial}
        | {"phases": [phase(p) for p in trial["plan"]["phases"]]}
        for trial in recorded["trials"]
    ]


def compare(tmp_path, monkeypatch, wave, identity, method, values, seed, opening=True, abort=None):
    from psychophysics_lab.core.trial_execution import VirtualPresentation
    from psychophysics_lab.researcher import ParticipantAbort
    original_play=VirtualPresentation.play_phase
    runs=[]
    for old in (True,False,False):
        with monkeypatch.context() as patch:
            patch.setattr('psychophysics_lab.analysis.previews.create_run_figures',lambda **kw:None)
            seen=[0]
            def play(self,phase,event,**kw):
                if abort=='ready' and phase.kind=='key_wait':raise ParticipantAbort('Migration readiness abort')
                if phase.kind=='response':
                    seen[0]+=1
                    if abort=='trial' and seen[0]==3:raise ParticipantAbort('Migration third response abort')
                return original_play(self,phase,event,**kw)
            if abort:patch.setattr(VirtualPresentation,'play_phase',play)
            with reference(patch,wave,identity,old,opening) as spec:
                run,_=simulate(repo_root=ROOT,data_root=tmp_path/str(len(runs)),experiment_id=identity,
                    values=values,seed=seed,observer=TeachingObserver(.65),analyse=False)
                assert all(c.passed for c in validate_run(run.run_directory))
                assert len(load_run(run.run_directory)['trials'])==20
                assert (run.run_directory/'session_events.json').exists()==opening
                runs.append(run)
    assert len({(r.status,r.accepted_trials) for r in runs})==1
    assert len({r.trial_log_file.read_bytes() for r in runs})==1
    representation_files = {
        'trial_actions.json', 'trial_events.jsonl',
        'trial_presentations.json', 'resolved_experiment.json',
    }
    for filename in ('trial_actions.json','trial_events.jsonl','trial_presentations.json',
        'adaptive_history.json','adaptive_session.json','primary_thresholds.json','resolved_experiment.json'):
        paths=[r.run_directory/filename for r in runs]
        assert len({p.exists() for p in paths})==1,filename
        if paths[0].exists():
            # New runs must be reproducible byte-for-byte in every file.
            assert paths[1].read_bytes() == paths[2].read_bytes(), filename
            if wave in (4, 5) and filename in representation_files:
                # Old scene was serialized as first/second composite objects,
                # new science as independently named per-phase layers.
                continue
            assert paths[0].read_bytes() == paths[1].read_bytes(),filename
    if wave in (4, 5):
        prior, current = [
            scientific_trial_actions(run.run_directory/'trial_actions.json')
            for run in runs[:2]
        ]
        assert prior == current, (
            'Scientific trial states, target, method or event chronology '
            'changed, not merely the name of a rendered stimulus slot.'
        )
    if opening:
        sessions=[]
        for r in runs:
            s=json.loads((r.run_directory/'session_events.json').read_text(encoding='utf-8'))
            s.pop('started_utc')
            for node in (s,*s['events']):
                start=node.pop('software_started_s');finish=node.pop('software_finished_s',start)
                assert 0<=start<=finish
            sessions.append(s)
        assert sessions[0]==sessions[1]==sessions[2]
    return runs[1]
