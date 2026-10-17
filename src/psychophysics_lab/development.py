"""Synthetic development operations for the USER_env Python terminal.

These helpers contain no Textual UI, window, event-loop or OS shell code.
Normal participant acquisition remains subject to full scientific preflight.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json

from .authoring import inventory, mark_tested, load_authored
from .experiments.registry import get_experiment
from .stimuli.registry import get_stimulus


def user_data_root(repo_root: Path) -> Path:
    suffix = hashlib.sha256(str(repo_root.resolve()).encode()).hexdigest()[:12]
    return Path.home() / "PsyCoLab_USER_env_data" / suffix


def preview_trial_storyboard(repo_root: Path, spec, values: dict, destination: Path) -> Path | None:
    """Illustrate the default *static* phase order; no real display or measured timing.

    Actual per-trial parameter overrides and dynamic shaders cannot be inferred
    solely from a timeline, so this file is explicitly an illustration.
    """
    from .core.timeline import load_timeline
    from .config.stimulus_parameters import load_parameters
    from .core.presentation import render_pixels
    import matplotlib.pyplot as plt
    import numpy as np

    path = repo_root / "configs" / "experiments" / (spec.id + ".json")
    if not path.is_file():
        return None
    if spec.procedure is not None:
        # The Python action plan is authoritative for new experiments. Render
        # executed actions from trial_actions.json rather than invent a JSON plan.
        return None
    timeline = load_timeline(path, timings=values, slots=spec.stimulus_slots)
    count = len(timeline.phases)
    fig, axes = plt.subplots(1, count, figsize=(max(6, 2.4 * count), 3))
    axes = np.atleast_1d(axes)
    try:
        for ax, phase in zip(axes, timeline.phases):
            pixels = np.full((128, 128), 128, dtype=np.uint8)
            if phase.slot in spec.stimulus_defaults:
                stimulus = get_stimulus(spec.stimulus_defaults[phase.slot])
                if stimulus.render is not None and stimulus.default_config:
                    selection = load_parameters(repo_root / stimulus.default_config, stimulus)
                    pixels = render_pixels(stimulus, selection["document"]["parameters"], pixels=(128,128))
            ax.imshow(pixels, cmap="gray", vmin=0, vmax=255)
            ax.set_title(f"{phase.name}\n{phase.duration_ms} ms" if phase.kind == "show" else f"{phase.name}\nwait/key", fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
        fig.suptitle("Illustrative default sequence — NOT measured photon timing", fontsize=10)
        fig.tight_layout()
        destination.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(destination, dpi=120)
    finally:
        plt.close(fig)
    return destination


def execute_user_action(repo_root: Path, operation: str, identity: str, values: dict) -> int:
    """CLI subprocess: software-only and synthetic, never real participant acquisition."""
    problems = load_authored(repo_root, include_drafts=True, tolerate_errors=True)
    if any(key.endswith(":" + identity) for key in problems):
        raise ValueError("Draft failed to import: " + "; ".join(f"{k} {v}" for k,v in problems.items() if k.endswith(":" + identity)))
    root = user_data_root(repo_root)
    root.mkdir(parents=True, exist_ok=True)
    marker = root / ".psycolab_user_env.json"
    if not marker.exists():
        marker.write_text(json.dumps({"schema_version": 1, "purpose": "development_only",
                                      "human_acquisition_allowed": False}) + "\n", encoding="utf-8")
    else:
        expected = {"schema_version": 1, "purpose": "development_only", "human_acquisition_allowed": False}
        if marker.is_symlink() or json.loads(marker.read_text(encoding="utf-8")) != expected:
            raise ValueError("USER_env marker invalid; refusing to reuse development output directory.")
    if operation == "preview":
        from .config.stimulus_parameters import load_parameters
        from .core.presentation import preview_stimulus
        stimulus = get_stimulus(identity)
        if stimulus.render is None:
            raise ValueError("Reference CSF/monitor diagnostic has no raster preview.")
        if stimulus.default_config:
            selected = load_parameters(repo_root / stimulus.default_config, stimulus)
        else:
            from .config.stimulus_parameters import document_for
            selected = {"document": document_for(stimulus)}
        preview_folder = root / "previews"
        preview_folder.mkdir(parents=True, exist_ok=True)
        path = preview_folder / (identity + ".png")
        preview_stimulus(identity, selected["document"]["parameters"], path)
        print("Preview saved:", path)
        print("This is a digital illustration, NOT physically calibrated luminance or timing.")
        return 0
    if operation == "test":
        from simulations.run import simulate
        from scripts.validate_run import validate_run
        spec = get_experiment(identity)
        if not spec.supports_simulation:
            raise ValueError("This experiment does not declare virtual observer support.")
        selected = spec.normalise_values(values)
        artifacts, _ = simulate(repo_root=repo_root, data_root=root, experiment_id=identity,
                                values=selected, analyse=False)
        failures = [check for check in validate_run(artifacts.run_directory) if not check.passed]
        if artifacts.status != "completed" or failures:
            raise ValueError(f"Simulation status: {artifacts.status}; validation failures: {failures}")
        try:
            storyboard = preview_trial_storyboard(repo_root, spec, selected,
                root / "previews" / (identity + "_timeline.png"))
            if storyboard is not None:
                print("Static phase storyboard:", storyboard)
        except (ValueError, KeyError, ImportError) as exc:
            print("Storyboard unavailable (virtual run remains validated):", exc)
        if any(item.name == identity and item.kind == "experiment" for item in inventory(repo_root)):
            mark_tested(repo_root, "experiment", identity)
        print("VALID virtual run:", artifacts.run_directory)
        print("NO human participant / physical display / verified calibration was used.")
        return 0
    raise ValueError("Unknown developer action; use 'preview' or 'test'.")
