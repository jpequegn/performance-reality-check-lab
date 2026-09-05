import json
import subprocess
from pathlib import Path

from .workloads import VARIANTS, Case

ROOT = Path(__file__).resolve().parents[2]


def build_binary(root=ROOT):
    subprocess.run(
        [
            "cargo",
            "build",
            "--release",
            "--locked",
            "--manifest-path",
            str(root / "rust/Cargo.toml"),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return root / "rust/target/release/reality-kernels"


def evaluate(binary: Path, case: Case, variant: str):
    if variant not in VARIANTS:
        raise ValueError("Unknown variant")
    result = subprocess.run(
        [str(binary), case.workload, variant, str(case.size), str(case.seed)],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return json.loads(result.stdout)
