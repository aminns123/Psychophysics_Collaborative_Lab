"""Scientific-reference guard: a single editable CSF shader definition.

No OpenGL context is opened by these tests. Physical readback remains a
separate lab validation stage and these tests cannot prove photon timing.
"""
import ast
from pathlib import Path

from psychophysics_lab.stimulus_library import CSFGrating

ROOT = Path(__file__).resolve().parents[1]


def test_reference_csf_shader_exactly_matches_frozen_pre_migration_source():
    original = (ROOT / "tests/fixtures/reference_csf_frag_source.glsl").read_text()
    assert CSFGrating.FRAGMENT_SOURCE == original
    assert "lum2image" in original
    assert "pitchX, pitchY, eyeDistance" in original
    assert "gl_FragColor.rgba" in original


def test_internal_hardware_renderer_consumes_the_only_shader_definition():
    source = (ROOT / "src/psychophysics_lab/_reference_csf/stimuliC.py").read_text()
    tree = ast.parse(source)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "Grating_ADM")
    assigns = [node for node in cls.body if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == "frag_source"
                       for target in node.targets)]
    assert len(assigns) == 1
    expr = assigns[0].value
    assert isinstance(expr, ast.Attribute) and expr.attr == "FRAGMENT_SOURCE"
    assert isinstance(expr.value, ast.Name) and expr.value.id == "CSFGrating"


def test_only_package_internal_reference_remains_at_old_root_paths():
    for dirname in ("Events", "Experiments", "Functions", "Interface"):
        assert not (ROOT / dirname).exists()
    assert not (ROOT / "libC.py").exists()
    assert not (ROOT / "packages.zip").exists()
    assert (ROOT / "src/psychophysics_lab/_reference_csf/stimuliC.py").is_file()
    assert CSFGrating.SPEC.source_path == "src/psychophysics_lab/stimulus_library.py"
    assert CSFGrating.SPEC.render is None
