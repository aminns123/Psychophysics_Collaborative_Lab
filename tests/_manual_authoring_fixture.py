"""TEST-ONLY isolated fixture data; not a production authoring/generator feature."""
from pathlib import Path
import json
import keyword
import re


def scaffold(repo_root: Path, name: str, *, kind="pair") -> tuple[Path, ...]:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or keyword.iskeyword(name):
        raise ValueError("Use a lowercase Python module name, e.g. orientation_task_copy.")
    if kind not in {"pair", "stimulus", "experiment", "adaptive"}:
        raise ValueError("Choose pair, stimulus, experiment or adaptive blueprint.")
    root = repo_root.resolve()
    source = Path(__file__).parent / "fixtures" / "manual_authoring"
    files = {}
    # Beginner projects start from explicit examples, NOT copied Gabor science.
    if kind in {"pair", "stimulus"}:
        template = (source / "stimulus_line_compat.py.txt").read_text(encoding="utf-8")
        files[f"src/psychophysics_lab/stimuli/{name}.py"] = template.replace("vertical_line_probe", name)
        from psychophysics_lab.stimulus_library import VerticalLineProbe
        SPEC = VerticalLineProbe.SPEC
        from psychophysics_lab.config.stimulus_parameters import document_for
        document = document_for(SPEC)
        document["stimulus_id"] = name
        files[f"configs/stimuli/{name}.json"] = json.dumps(document, indent=2) + "\n"
    if kind in {"pair", "experiment"}:
        # Advanced authoring starts from an explicit, task-neutral research
        # skeleton. Do NOT clone left/right example_experiment science.
        template = (source / "experiment_starter.py.txt").read_text(encoding="utf-8")
        template = template.replace("BLUEPRINT_ID", name)
        template = template.replace("BLUEPRINT_STIMULUS", name if kind == "pair" else "vertical_line_probe")
        files[f"src/psychophysics_lab/experiments/{name}.py"] = template
        # This deliberately unfinished starter has its own field contract;
        # example_experiment also declares methods the starter does not use.
        document = {"schema_version": 1, "experiment_id": name, "values": {
            "trial_count": 6, "fixation_ms": 500, "stimulus_ms": 200,
            "interval_ms": 150, "response_timeout_ms": 0, "response_keys": "F,J",
        }}
        files[f"configs/experiments/{name}.json"] = json.dumps(document, indent=2) + "\n"
    if kind == "adaptive":
        files[f"src/psychophysics_lab/adaptive/{name}.py"] = (source / "adaptive_method.py.txt").read_text(encoding="utf-8").replace("BLUEPRINT_ID", name)
    paths = tuple(root / relative for relative in files)
    if any(p.exists() or p.is_symlink() or not p.resolve().is_relative_to(root) for p in paths):
        raise ValueError("Scaffold paths must be new files inside this checkout; nothing was overwritten.")
    created = []
    try:
        for path, text in zip(paths, files.values()):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as handle:
                created.append(path)
                handle.write(text)
    except Exception:
        for path in created:
            path.unlink()
        raise
    return paths

def scaffold_vertical_line(repo_root: Path, name: str) -> tuple[Path, ...]:
    """Generate an independent, editable line stimulus — no experiment copied."""
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or keyword.iskeyword(name):
        raise ValueError("Use a new lowercase Python module name.")
    root = Path(repo_root).resolve()
    sources = Path(__file__).parent / "fixtures" / "manual_authoring"
    code = (sources / "stimulus_line_compat.py.txt").read_text(encoding="utf-8")
    code = code.replace("vertical_line_probe", name)
    document = json.loads((Path(__file__).resolve().parents[1] / "configs/stimuli/vertical_line_probe.json").read_text(encoding="utf-8"))
    document["stimulus_id"] = name
    paths = (root / f"src/psychophysics_lab/stimuli/{name}.py",
             root / f"configs/stimuli/{name}.json")
    if any(path.exists() or path.is_symlink() or not path.resolve().is_relative_to(root) for path in paths):
        raise ValueError("The stimulus files already exist. Nothing was overwritten.")
    created = []
    try:
        for path, content in zip(paths, (code, json.dumps(document, indent=2) + "\n")):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as handle:
                created.append(path)
                handle.write(content)
    except Exception:
        for path in created:
            path.unlink()
        raise
    return paths


def scaffold_draft(repo_root, name, kind):
    """Test-only fixture registration; production users manually write files."""
    from psychophysics_lab.authoring import stage
    files = scaffold(repo_root, name, kind=kind)
    kinds = ("stimulus", "experiment") if kind == "pair" else (kind,)
    for item in kinds:
        stage(repo_root, item, name)
    return files
