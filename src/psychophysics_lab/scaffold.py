"""Create two small contributor modules without overwriting existing files."""
from pathlib import Path
import keyword
import re


def scaffold(repo_root: Path, name: str) -> tuple[Path, Path]:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or keyword.iskeyword(name):
        raise ValueError("Use a lowercase Python module name, e.g. orientation_task.")
    root = repo_root.resolve()
    base = root / "src" / "psychophysics_lab"
    paths = (base / "stimuli" / (name + ".py"), base / "experiments" / (name + ".py"))
    if any(p.exists() or p.is_symlink() or not p.resolve().is_relative_to(root) for p in paths):
        raise ValueError("Scaffold paths must be new files inside this checkout; nothing was overwritten.")
    stimulus = f'''"""Define reusable stimulus parameters here; keep hardware imports lazy."""
from dataclasses import dataclass
from psychophysics_lab.researcher import StimulusSpec

@dataclass(frozen=True)
class Stimulus:
    contrast: float = 0.1

SPEC = StimulusSpec("{name}", "{name.replace('_',' ').title()}",
    "Describe the stimulus and its units.", "src/psychophysics_lab/stimuli/{name}.py")
'''
    procedure = f'''"""Own only your scientific procedure: timing, presentation and responses."""
from psychophysics_lab.researcher import ConfigField, experiment, LEFT_RIGHT
from psychophysics_lab.stimuli.{name} import Stimulus

def procedure(run):
    stimulus = Stimulus(contrast=run.values["contrast"])
    # Present stimulus with your renderer, accept a response, then run.record(...).
    # See docs/RESEARCHER_QUICKSTART.md for the canonical trial contract.
    raise NotImplementedError("Implement and validate this procedure before collecting data.")

SPEC = experiment(id="{name}", name="{name.replace('_',' ').title()}",
    description="Describe your experiment.", procedure=procedure, responses=LEFT_RIGHT,
    calibration_requirements=("geometry", "luminance", "timing"),
    monitor_capabilities=("display_binding", "resolution"),
    fields=(ConfigField("contrast", "Contrast", "float", default=0.1, minimum=0, maximum=1),),
    source_paths=("src/psychophysics_lab/experiments/{name}.py",
                  "src/psychophysics_lab/stimuli/{name}.py"))
'''
    created = []
    try:
        for path, text in zip(paths, (stimulus, procedure)):
            with path.open("x", encoding="utf-8") as handle:
                created.append(path)
                handle.write(text)
    except Exception:
        for path in created:
            path.unlink()
        raise
    return paths
