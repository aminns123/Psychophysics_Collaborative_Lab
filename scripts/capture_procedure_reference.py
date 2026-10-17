"""Freeze pre-audit software traces using the original committed procedure."""
from pathlib import Path
import json
import hashlib
import os
import subprocess
import sys
import tempfile
import types
root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root / 'src'), str(root)]
from dataclasses import replace
from psychophysics_lab.experiments.registry import get_experiment
from psychophysics_lab.core.runner import run_request
from psychophysics_lab.core.synthetic import SimulationRun
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.experiments import registry

revision = '651b928371dc577717dbef96acdaa9c292d02c1a'
source = subprocess.check_output(['git', 'show', revision + ':src/psychophysics_lab/experiments/flanker_protocol.py'], cwd=root, text=True)
old = types.ModuleType('psychophysics_lab.experiments._frozen_protocol')
old.__file__ = str(root / 'src/psychophysics_lab/experiments/flanker_protocol.py')
exec(compile(source, old.__file__, 'exec'), old.__dict__)

def normalise(value):
    if isinstance(value, list):
        return [normalise(v) for v in value]
    if isinstance(value, dict):
        return {k: v.rsplit('.', 1)[-1] if k in {'function', 'update_value'} and isinstance(v, str) else normalise(v)
                for k, v in value.items()}
    return value

def scientific_trace(directory):
    actions = json.loads((directory / 'trial_actions.json').read_text())['trials']
    return {'trials_tsv': (directory / 'trials.tsv').read_text(),
            'actions_sha256': hashlib.sha256(json.dumps(normalise(actions), sort_keys=True).encode()).hexdigest(),
            'adaptive': json.loads((directory / 'adaptive_session.json').read_text())}

with tempfile.TemporaryDirectory(prefix='psycolab-equivalence-') as temporary:
    temp = Path(temporary)
    os.environ['PSYCOLAB_CONFIG_DIR'] = str(temp / 'config')
    fixtures = {}
    for identity, family in [('base_flanker','base'), ('indirect_flanker','indirect'), ('ellipse_2d','ellipse')]:
        spec = get_experiment(identity)
        values = {'reference_width_px': 1920, 'reference_height_px': 1080, 'start_contrast': .05,
                  'trials_per_condition': 2}
        if family == 'ellipse':
            values |= {'condition_positions_deg': '[0.25, 0.5]', 'decision_scene': 'fixation_only_development'}
        def procedure(run, family=family):
            return old.run_protocol(run, family=family)
        # Optional settings resolver uses procedure globals to find this checkout.
        procedure.__globals__['__file__'] = str(root / 'src/psychophysics_lab/experiments' / (identity + '.py'))
        legacy_spec = replace(spec, procedure=procedure)
        registry._REGISTRY[identity] = legacy_spec
        sim = SimulationRun(temp / 'data', {'seed': 123, 'physical_display_used': False,
            'observer_parameters': {'accuracy': .65}}, lambda *a: None)
        result = run_request(SetupRequest('synthetic_123', 'new', identity, 'legacy_reference_display', values),
                             repo_root=root, data_root=temp / 'data', simulation=sim)
        fixtures[identity] = {'values': values, 'seed': 123, 'accuracy': .65,
                             'expected': scientific_trace(result.run_directory)}
        registry._REGISTRY[identity] = spec
    path = root / 'tests/fixtures/researcher_procedures.json'
    path.write_text(json.dumps({'source_revision': revision, 'physical_equivalence': False,
                               'cases': fixtures}, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('Frozen original traces:', path, path.stat().st_size, 'bytes')
