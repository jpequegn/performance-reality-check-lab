import json
import subprocess
from pathlib import Path

from .workloads import VARIANTS, Case

ROOT = Path(__file__).resolve().parents[2]


def compiler_flags(optimization=3):
    return [
        "--edition=2021",
        "-C",
        f"opt-level={optimization}",
        "-C",
        "target-cpu=generic",
        "-C",
        "codegen-units=1",
        "-C",
        "debug-assertions=off",
        "-C",
        "overflow-checks=off",
    ]


def build_commands(root, output):
    library = output / "libreality_kernels.rlib"
    return [
        [
            "rustc",
            "--crate-name",
            "reality_kernels",
            "--crate-type=rlib",
            str(root / "rust/src/lib.rs"),
            *compiler_flags(),
            "-o",
            str(library),
        ],
        [
            "rustc",
            str(root / "rust/src/main.rs"),
            "--extern",
            f"reality_kernels={library}",
            *compiler_flags(),
            "-o",
            str(output / "reality-kernels"),
        ],
    ]


def build_binary(root=ROOT, output=None):
    output = output or root / "rust/target/lab"
    output.mkdir(parents=True, exist_ok=True)
    for command in build_commands(root, output):
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
    return output / "reality-kernels"


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
