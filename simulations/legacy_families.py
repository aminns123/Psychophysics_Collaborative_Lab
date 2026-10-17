"""Virtual reconstructions through the canonical runner; never participant data.

Example dimensions/conditions below are explicit development selections, not
assertions about the historical monitor or the missing ellipse protocol.
"""
import argparse
import json
from pathlib import Path
from psychophysics_lab.core.runner import run_request
from psychophysics_lab.core.synthetic import SimulationRun
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.paths import find_repo_root
from scripts.validate_run import validate_run


def simulate(output, *, identity, width_px, height_px, conditions=None, decision_scene="unresolved", seed=123):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Choose a NEW development output folder")
    values = {"reference_width_px":width_px, "reference_height_px":height_px,
              "trials_per_condition":5,"start_contrast":.1}
    if conditions is not None:
        values["condition_positions_deg"] = json.dumps(conditions)
    if identity == "ellipse_2d":
        values["decision_scene"] = decision_scene
    simulation = SimulationRun(output,{"seed":seed,"physical_display_used":False,
        "observer_parameters":{"accuracy":.9},
        "purpose":"DEVELOPMENT protocol reconstruction; no human acquisition"},lambda *args:None)
    result = run_request(SetupRequest(f"synthetic_{seed}","new",identity,"legacy_reference_display",values),
                         repo_root=find_repo_root(),data_root=output,simulation=simulation)
    failures = [c for c in validate_run(result.run_directory) if not c.passed]
    if failures:
        raise RuntimeError(str(failures))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment",required=True,choices=("indirect_flanker","base_flanker","ellipse_2d"))
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--width-px",required=True,type=int)
    parser.add_argument("--height-px",required=True,type=int)
    parser.add_argument("--conditions",type=float,nargs="+")
    parser.add_argument("--decision-scene",choices=("unresolved","fixation_only_development"),default="unresolved")
    parser.add_argument("--seed",type=int,default=123)
    args = parser.parse_args()
    result = simulate(args.output,identity=args.experiment,width_px=args.width_px,height_px=args.height_px,
                      conditions=args.conditions,decision_scene=args.decision_scene,seed=args.seed)
    print(result.status, result.run_directory)
