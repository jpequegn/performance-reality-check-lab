import argparse
import json
import subprocess
import sys
from pathlib import Path

from .compare import compare
from .measurement import Settings
from .model import Hardware
from .report import load_report, run_experiment
from .workloads import WORKLOADS, Case


def main(argv=None):
    parser = argparse.ArgumentParser(description="Performance reality check lab")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Measure kernels and write an evidence bundle")
    run.add_argument("--out", required=True, type=Path)
    run.add_argument("--workload", action="append", choices=WORKLOADS)
    run.add_argument("--size", type=int, default=4096)
    run.add_argument("--seed", type=int, default=7)
    run.add_argument("--samples", type=int, default=7)
    run.add_argument("--min-ms", type=float, default=20)
    run.add_argument("--max-cv", type=float, default=0.20)
    run.add_argument("--hardware", type=Path)
    inspect = commands.add_parser("inspect", help="Verify an existing report and compiler evidence")
    inspect.add_argument("directory", type=Path)
    comparison = commands.add_parser("compare", help="Compare compatible validated runs")
    comparison.add_argument("baseline", type=Path)
    comparison.add_argument("candidate", type=Path)
    comparison.add_argument("--slowdown", type=float, default=1.15)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            settings = Settings(args.samples, args.min_ms, args.max_cv)
            hardware = (
                Hardware(**json.loads(args.hardware.read_text())) if args.hardware else Hardware()
            )
            cases = [Case(w, args.size, args.seed) for w in (args.workload or WORKLOADS)]
            report = run_experiment(
                args.out, cases, settings, hardware, lambda message: print(message, file=sys.stderr)
            )
            print(json.dumps({"report": str(args.out / "report.md"), "valid": report["valid"]}))
            return 0 if report["valid"] else 2
        if args.command == "inspect":
            report = load_report(args.directory)
            print(
                json.dumps(
                    {"verified": True, "valid": report["valid"], "rows": len(report["rows"])}
                )
            )
            return 0 if report["valid"] else 2
        result = compare(load_report(args.baseline), load_report(args.candidate), args.slowdown)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
