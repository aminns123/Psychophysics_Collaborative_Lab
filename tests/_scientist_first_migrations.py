"""Exact new sources and immutable pre-migration references for Waves 3–5."""
import hashlib
import json

def historical_one_map_source(root, identity, raw):
    """Undo only frozen registration-map edits before historical source SHA checks.

    No methods, conditions, trial events or data functions are normalized here.
    Any accidental science change still fails the exact frozen SHA.
    """
    fixture = root / "tests/fixtures/scientist_first_one_map_reversible.json"
    if not fixture.exists():
        return raw
    changes = json.loads(fixture.read_text(encoding="utf-8")).get(identity, ())
    for pair in changes:
        updated = pair["replacement"].encode("utf-8")
        original = pair["baseline"].encode("utf-8")
        assert raw.count(updated) == 1, (identity, updated[:60])
        raw = raw.replace(updated, original, 1)
    return raw


def migration_reference(root, identity):
    for wave in (3, 4, 5):
        folder = root / "tests/fixtures" / ("issue165_wave" + str(wave))
        manifest = folder / "baseline.json"
        if not manifest.exists():
            continue
        saved = json.loads(manifest.read_text(encoding="utf-8"))
        assert saved["commit"] == "8f493fa0a54cbe57109943120b5e410e77c0541a"
        if identity not in saved["experiments"]:
            continue
        contract = saved["experiments"][identity]
        before = folder / (identity + ".py")
        after = root / "src/psychophysics_lab/experiments" / before.name
        atomic = {
            "line_position_baseline": "9ffa7a908b68e0b05b264aec4bb97ad48da6d9d4",
            "line_position_flanker": "e583fde32713d1794c5343309c7b412c9446f15b",
            "ellipse_centre": "4860552bbbe3677ebf74b792b083e307307a0d85",
            "ellipse_major_axis": "2a18b66c398f7d86bedbe1b3c77151737a53d20b",
        }
        if identity in atomic:
            # Wave4/5 first introduced the exact pre-atomic procedure. #207
            # changes the *representation*, so comparing new source bytes
            # with the old after-hash is no longer a valid source-only test.
            # Freeze the original archive and original before-source instead;
            # numerical, event and data equivalence are independently tested.
            preserved = (root / "outdated_code/pre_atomic_207/src/psychophysics_lab"
                         / "experiments" / (identity + ".py"))
            data = preserved.read_bytes().replace(b"\r\n", b"\n")
            actual = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            assert actual == atomic[identity], identity
            new = after.read_text(encoding="utf-8")
            assert "STIMULI =" in new and "detection_scene" not in new
            assert "def trial_events(" in new and "def prepare_stimuli(" in new
            raw = before.read_bytes().replace(b"\r\n", b"\n")
            assert hashlib.sha256(raw).hexdigest() == contract["before_sha256_lf"]
            return before
        for path, key in ((before, "before_sha256_lf"), (after, "after_sha256_lf")):
            raw = path.read_bytes().replace(b"\r\n", b"\n")
            if key == "after_sha256_lf":
                if identity == "contrast_sensitivity_windowed":
                    # Issue #196: reverse only the approved CSF Review fix.
                    # Keep the original scientific source checksum intact.
                    approved = (
                        "        # Do not inherit Gaussian CSF's method_reviewer. Review must call the\n"
                        "        # circular factory, which supplies aperture-specific resolution\n"
                        "        # instead of requesting Gaussian sigma/cutoff fields removed above.\n"
                        '        method_reviewer={"constant_stimuli": fixed_contrast_method},\n'
                    )
                    assert raw.count(approved.encode("utf-8")) == 1, identity
                    raw = raw.replace(approved.encode("utf-8"), b"", 1)

                # Undo only the reviewed single-STIMULI declarations.
                raw = historical_one_map_source(root, identity, raw)
            assert hashlib.sha256(raw).hexdigest() == contract[key], (identity, key)
        return before
    return None


def inline_measurement_declarations(node, functions):
    """Recover the exact frozen record AST from pure named measurement/instruction declarations.

    This permits source organisation only. Any changed dictionary value,
    instruction, call argument or extra helper statement still fails the frozen
    function hash. No scientific fixture or expected digest is rewritten.
    """
    import ast
    import copy
    class BindArguments(ast.NodeTransformer):
        def __init__(self, arguments):
            self.arguments = arguments
        def visit_Name(self, name):
            return copy.deepcopy(self.arguments.get(name.id, name))
    class Inline(ast.NodeTransformer):
        def visit_Call(self, call):
            call = self.generic_visit(call)
            if not isinstance(call.func, ast.Name) or call.func.id not in {
                    'trial_measurements', 'fixed_trial_measurements', 'response_instructions'}:
                return call
            function = functions[call.func.id]
            body = list(function.body)
            if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                body.pop(0)
            assert len(body) == 1 and isinstance(body[0], ast.Return)
            assert not call.keywords and len(call.args) == len(function.args.args)
            assert not function.args.defaults and not function.args.kwonlyargs
            assert function.args.vararg is None and function.args.kwarg is None
            arguments = {parameter.arg: value for parameter, value in zip(function.args.args, call.args)}
            return BindArguments(arguments).visit(copy.deepcopy(body[0].value))
    return Inline().visit(copy.deepcopy(node))


