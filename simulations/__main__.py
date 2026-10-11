"""python -m simulations --seed 123 --thresholds .05,.1,.2 --seeds 1,2,3"""
import argparse
from pathlib import Path
from .csf import CSFObserver
from .run import simulate

def main():
    parser = argparse.ArgumentParser(description="SYNTHETIC CSF pipeline simulation; no hardware or participant data")
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--seeds", help="Comma-separated seeds for a sweep")
    parser.add_argument("--thresholds", default="0.1", help="Comma-separated observer midpoint thresholds")
    parser.add_argument("--preferred-condition", type=float, default=63.)
    parser.add_argument("--max-trials", type=int, default=400)
    parser.add_argument("--data-root", type=Path, help="Same external PsyCoLab data repository used for human acquisition")
    parser.add_argument("--workspace", type=Path, help="Deprecated alias for --data-root")
    args = parser.parse_args()
    if args.workspace is not None and args.data_root is not None:
        parser.error("Use --data-root or --workspace, not both.")
    data_root = args.data_root if args.data_root is not None else args.workspace
    seeds = [int(x) for x in args.seeds.split(",")] if args.seeds else [args.seed]
    for threshold in map(float, args.thresholds.split(",")):
        for seed in seeds:
            artifacts, analysis = simulate(data_root=data_root, seed=seed,
                observer=CSFObserver(threshold=threshold, preferred_condition=args.preferred_condition),
                values={"max_trials": args.max_trials})
            print(f"SYNTHETIC seed={seed} midpoint={threshold}: {artifacts.status}; {artifacts.accepted_trials} responses")
            print(artifacts.run_directory)
            print(analysis.summary_json if analysis else "No reversal estimate available for this short run.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
