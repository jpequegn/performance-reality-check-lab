import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from .native import ROOT, build_binary, build_commands, compiler_flags
from .workloads import VARIANTS, WORKLOADS


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_paths(root=ROOT):
    return sorted(
        [
            *root.glob("src/reality_check/*.py"),
            *root.glob("rust/src/*.rs"),
            root / "rust/Cargo.toml",
            root / "rust/Cargo.lock",
            root / "pyproject.toml",
            root / "uv.lock",
        ]
    )


def source_hashes(root=ROOT):
    return {str(p.relative_to(root)): digest(p) for p in source_paths(root)}


def capture(output: Path, root=ROOT):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    before = source_hashes(root)
    commands = []
    records = []
    symbols = {}
    for source in source_paths(root):
        target = output / "sources" / source.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        records.append({"path": str(target.relative_to(output)), "sha256": digest(target)})
    source_root = output / "sources"
    for level in (0, 3):
        asm, ir = output / f"O{level}.s", output / f"O{level}.ll"
        command = [
            "rustc",
            "--crate-name",
            "reality_kernels",
            "--crate-type=rlib",
            str(source_root / "rust/src/lib.rs"),
            *compiler_flags(level),
            f"--emit=asm={asm},llvm-ir={ir}",
        ]
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
        commands.append(command)
        lines = asm.read_text().splitlines()
        found = {}
        for workload in WORKLOADS:
            for variant in VARIANTS:
                symbol = f"{workload}_{variant}"
                matches = [
                    i + 1
                    for i, line in enumerate(lines)
                    if re.match(rf"^_?{symbol}:|^\s*\.set\s+_?{symbol},", line)
                ]
                if not matches:
                    raise ValueError(f"Missing compiler symbol: {symbol} at O{level}")
                found[symbol] = matches[0]
        symbols[f"O{level}.s"] = found
        for artifact in (asm, ir):
            if not artifact.stat().st_size:
                raise ValueError("Compiler emitted empty artifact")
            records.append({"path": artifact.name, "sha256": digest(artifact)})
    binary = build_binary(source_root, output / "build")
    commands.extend(build_commands(source_root, output / "build"))
    for artifact in (binary, output / "build/libreality_kernels.rlib"):
        records.append({"path": str(artifact.relative_to(output)), "sha256": digest(artifact)})
    if source_hashes(root) != before:
        raise ValueError("Sources changed during evidence capture")
    manifest = {
        "schema_version": 1,
        "source_hashes": before,
        "rustc": subprocess.check_output(["rustc", "-vV"], text=True).strip(),
        "compiler_flags": compiler_flags(),
        "commands": commands,
        "artifacts": records,
        "symbols": symbols,
        "binary": "build/reality-kernels",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def verify(output: Path):
    output = output.resolve()
    manifest = json.loads((output / "manifest.json").read_text())
    if manifest.get("schema_version") != 1 or not manifest.get("artifacts"):
        raise ValueError("Invalid evidence manifest")
    for record in manifest["artifacts"]:
        artifact = (output / record["path"]).resolve()
        if not artifact.is_relative_to(output) or not artifact.is_file():
            raise ValueError("Missing or escaped evidence artifact")
        if digest(artifact) != record["sha256"]:
            raise ValueError(f"Changed evidence artifact: {record['path']}")
    return manifest
