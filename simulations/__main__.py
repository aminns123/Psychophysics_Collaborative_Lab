"""Run an experiment-specific virtual observer or a named pipeline scenario.

Examples:
    python -m simulations --list-scenarios
    python -m simulations --scenario csf_baseline
    python -m simulations --scenario csf_short_censored
    python -m simulations --thresholds .05,.1,.2 --seeds 1,2,3
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .csf import CSFObserver
from .run import simulate


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Headless synthetic experiment pipeline: no participant or physical display"
    )
    parser.add_argument("--experiment", default="contrast_sensitivity", help="Registered experiment ID")
    parser.add_argument("--list-scenarios", action="store_true", help="List experiment-specific test scenarios")
    parser.add_argument("--scaffold-simulation", metavar="EXPERIMENT", help="Generate two non-overwriting virtual observer/scenario templates")
    parser.add_argument("--scenario", help="Run a named, experiment-specific scenario through the full pipeline")
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--seeds", help="Comma-separated seeds for direct CSF sweeps")
    parser.add_argument("--thresholds", default="0.1", help="CSF midpoint contrasts, comma-separated")
    parser.add_argument("--preferred-condition", type=float, default=63.,
                        help="CSF preferred legacy condition value (not calibrated cycles/degree)")
    parser.add_argument("--tuning-width-octaves", type=float, default=2.)
    parser.add_argument("--slope", type=float, default=3.)
    parser.add_argument("--lapse", type=float, default=0.02)
    parser.add_argument("--max-trials", type=int, default=400)
    parser.add_argument("--data-root", type=Path, help="Same external data repository as human experiments")
    parser.add_argument("--workspace", type=Path, help="Deprecated alias for --data-root")
    args = parser.parse_args(argv)
    if args.workspace is not None and args.data_root is not None:
        parser.error("Use --data-root or --workspace, not both.")
    data_root = args.data_root if args.data_root is not None else args.workspace

    if args.scaffold_simulation:
        from psychophysics_lab.paths import find_repo_root
        from .scaffold import scaffold_simulation
        for path in scaffold_simulation(find_repo_root(), args.scaffold_simulation):
            print(path)
        print("Implement the model, then register its SimulationSpec and SCENARIOS explicitly.")
        return 0

    if args.list_scenarios:
        from .scenarios import list_scenarios
        scenarios = list_scenarios(None if args.experiment == "all" else args.experiment)
        for scenario in scenarios:
            print(f"{scenario.experiment_id}\t{scenario.id}\t{scenario.description}")
        return 0

    if args.scenario:
        from .scenarios import run_scenario
        result = run_scenario(experiment_id=args.experiment,
                              scenario_id=args.scenario, data_root=data_root)
        print(f"SYNTHETIC scenario {args.scenario}: {'PASS' if result.passed else 'FAIL'}")
        for record in result.runs:
            print(f"seed={record.seed}, status={record.artifacts.status}, responses={record.artifacts.accepted_trials}")
            print(record.artifacts.run_directory)
        for check in result.checks:
            if not check["passed"]:
                print(f"FAILED seed={check['seed']} {check['name']}: {check['detail']}")
        print(f"Scenario report: {result.report_file}")
        return 0 if result.passed else 1

    if args.experiment != "contrast_sensitivity":
        parser.error("For non-CSF experiments select a registered --scenario; CSF sweep flags are model-specific.")

    seeds = [int(x) for x in args.seeds.split(",")] if args.seeds else [args.seed]
    for threshold in map(float, args.thresholds.split(",")):
        for seed in seeds:
            artifacts, analysis = simulate(
                data_root=data_root, seed=seed,
                observer=CSFObserver(
                    threshold=threshold, preferred_condition=args.preferred_condition,
                    tuning_width_octaves=args.tuning_width_octaves,
                    slope=args.slope, lapse=args.lapse,
                ),
                values={"max_trials": args.max_trials},
            )
            print(f"SYNTHETIC seed={seed} midpoint={threshold}: "
                  f"{artifacts.status}; {artifacts.accepted_trials} responses")
            print(artifacts.run_directory)
            print(analysis.summary_json if analysis else "No reversal estimate available.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
