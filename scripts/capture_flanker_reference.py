"""One-off reference capture: AST-selected numeric functions, no legacy imports."""
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import numpy as np
import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True, help='Pinned legacy Functions/functionUSE.py')
parser.add_argument('--output', type=Path, required=True, help='NEW fixture JSON path')
args = parser.parse_args()
if args.output.exists():
    raise ValueError('Refusing to overwrite a fixture; compare a new capture separately')
source = args.source
code = source.read_text(encoding='utf-8-sig')
if hashlib.sha256(code.encode()).hexdigest() != '102f8a8ccef835fdebb788942488386ddec8fca666ce1510ba44a14815dfd481':
    raise ValueError('Expected the pinned, newline-normalized source at commit 1c317759')
tree = ast.parse(code)
functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
selected = set()
def include(name):
    if name in selected:
        return
    selected.add(name)
    for n in ast.walk(functions[name]):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in functions:
            include(n.func.id)
include('conditions')
# Reviewable numeric allowlist, never execute the legacy module/imports/I/O.
allowed = {'conditions', 'check_values', 'count_values_type', 'appendTrials', 'count_Abs_type',
           'returnOnce', 'findIndexFloat', 'findIndex', 'admID_staircase', 'weberContrast',
           'count_reversals_HighLow', 'defineReversal_Multi', 'conditionRateUPDW', 'rate_dw',
           'findCPU_fromWeberContrast'}
assert selected == allowed, selected ^ allowed
namespace = {'np': np}
exec(compile(ast.Module(body=[functions[n] for n in sorted(selected)], type_ignores=[]), str(source), 'exec'), namespace)
cases = []
for name, schedule in (
    ('initial_and_reversals', [(1, x) for x in [True]*12 + [False, True, True, True]*6]),
    ('interleaved', [(1+i%2, i%7 not in (3,6)) for i in range(60)]),
    ('leading_holds', [(1, x) for x in [False, False, True, True, True, True, False, True]*4]),
):
    data = [[0.] for _ in range(16)]
    background = .24
    start = background + (1-background)*.1
    params = [start,0,0,0,start,0,.5,0,-1,0,.5,0,background,1,1,2,1,1,.000155,9,0,.005,2,.19,.7393*.19,100,0,0,.2,1,9,60,1,0,0]
    values = {}
    rows = []
    for identity, correct in schedule:
        presented = values.get(identity, start)
        for column,value in {0: .25*identity, 1:0, 2:0 if correct else 1, 4:identity, 6:round(presented,8),
                             7:.5, 12:.6, 13:3}.items():
            data[column].append(value)
        with contextlib.redirect_stdout(io.StringIO()):
            updated, reversal_tick, ticks, param_start, rate, count, reversals, rate_up = namespace['conditions'](data, params, True)
        for column,value in {3:reversals,5:rate,8:reversal_tick,9:param_start,10:ticks,11:round(updated,8),
                             14:(presented-background)/(1-background),15:1.}.items():
            data[column].append(value)
        values[identity] = round(updated,8)
        params[5],params[9],params[10] = reversal_tick,reversals,rate_up
        rows.append({'identity':identity,'correct':correct,'presented':round(presented,8),
                     'next':round(updated,8),'correct_ticks':ticks,'reversals':reversals})
    cases.append({'name':name,'rows':rows})
path = args.output
path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps({'source_commit':'1c3177594e00f0b26fa361238db0f4db5de403fa',
    'source_path':'Functions/functionUSE.py', 'source_sha256':hashlib.sha256(code.encode()).hexdigest(),
    'capture':'AST-only numeric functions; original zero row, rounding and conditions() preserved',
    'functions':sorted(selected),'cases':cases},indent=2)+'\n')
print('Captured',sum(len(c['rows']) for c in cases),'original numeric updates')
