"""Generate obvious beginner scientific templates; never overwrite existing work."""
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
    source = Path(__file__).parent
    files = {}
    # Beginner projects start from explicit examples, NOT copied Gabor science.
    if kind in {"pair", "stimulus"}:
        template = (source / "stimuli/example_stimulus.py").read_text(encoding="utf-8")
        files[f"src/psychophysics_lab/stimuli/{name}.py"] = template.replace("example_stimulus", name)
        from .stimuli.example_stimulus import SPEC
        from .config.stimulus_parameters import document_for
        document = document_for(SPEC)
        document["stimulus_id"] = name
        files[f"configs/stimuli/{name}.json"] = json.dumps(document, indent=2) + "\n"
    if kind in {"pair", "experiment"}:
        template = (source / "experiments/example_experiment.py").read_text(encoding="utf-8")
        template = template.replace("example_experiment", name)
        if kind == "pair":
            template = template.replace("example_stimulus", name)
        files[f"src/psychophysics_lab/experiments/{name}.py"] = template
        document = json.loads((source.parent.parent / "configs/experiments/example_experiment.json").read_text(encoding="utf-8"))
        document["experiment_id"] = name
        files[f"configs/experiments/{name}.json"] = json.dumps(document, indent=2) + "\n"
    if kind == "adaptive":
        files[f"src/psychophysics_lab/adaptive/{name}.py"] = (source / "blueprints/adaptive_method.py.txt").read_text(encoding="utf-8").replace("BLUEPRINT_ID", name)
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
    sources = Path(__file__).parent
    code = (sources / "stimuli/vertical_line_probe.py").read_text(encoding="utf-8")
    code = code.replace("vertical_line_probe", name)
    document = json.loads((sources.parent.parent / "configs/stimuli/vertical_line_probe.json").read_text(encoding="utf-8"))
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
