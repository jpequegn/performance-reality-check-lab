import json
import platform
import random
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .evidence import capture, digest, source_hashes, verify
from .measurement import Settings, python_measure, rust_measure, summarize
from .model import Hardware, ceiling
from .workloads import VARIANTS, Case, input_digest, inputs, reference


def environment():
    cpu = platform.processor() or platform.machine()
    if sys.platform == "darwin":
        try:
            cpu = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).strip()
        except (OSError, subprocess.SubprocessError):
            cpu = "unavailable"
    elif sys.platform.startswith("linux") and Path("/proc/cpuinfo").exists():
        cpu = next(
            (
                line.split(":", 1)[1].strip()
                for line in Path("/proc/cpuinfo").read_text().splitlines()
                if line.startswith("model name")
            ),
            cpu,
        )
    return {
        "python": sys.version,
        "implementation": platform.python_implementation(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "cpu": cpu,
        "timer_resolution_seconds": time.get_clock_info("perf_counter").resolution,
    }


def row_key(row):
    return tuple(row[key] for key in ("workload", "size", "seed", "language", "variant"))


def run_experiment(output: Path, cases, settings: Settings, hardware: Hardware, progress=None):
    if not 1 <= len(cases) <= 4 or len(set(cases)) != len(cases):
        raise ValueError("Choose one to four distinct cases")
    output.mkdir(parents=True, exist_ok=False)
    manifest = capture(output / "evidence")
    metadata = environment()
    metadata["rustc"] = manifest["rustc"]
    binary = output.resolve() / "evidence" / manifest["binary"]
    schedule = [
        (case, variant, language)
        for case in cases
        for variant in VARIANTS
        for language in ("python", "rust")
    ]
    random.Random(0).shuffle(schedule)
    rows = []
    order = []
    for case, variant, language in schedule:
        if progress:
            progress(f"Measuring {case.workload}/{language}/{variant}")
        measured = (
            python_measure(case, variant, settings)
            if language == "python"
            else rust_measure(binary, case, variant, settings)
        )
        row = {**asdict(case), **measured}
        row["model"] = ceiling(case, variant, hardware, row["median_ns"])
        rows.append(row)
        order.append(list(row_key(row)))
    if source_hashes() != manifest["source_hashes"]:
        raise ValueError("Sources changed during measurement; rerun the experiment")
    verify(output / "evidence")
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "environment": metadata,
        "settings": asdict(settings),
        "warmups": 2,
        "compiler_flags": manifest["compiler_flags"],
        "measurement_order": order,
        "evidence_manifest_sha256": digest(output / "evidence/manifest.json"),
        "rows": sorted(rows, key=row_key),
        "valid": all(r["quality"]["valid"] for r in rows),
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    (output / "report.md").write_text(markdown(report, manifest))
    return report


def markdown(report, manifest):
    status = "VALID" if report["valid"] else "INVALID: inspect sample quality below"
    lines = [
        "# Performance reality check",
        "",
        f"Status: {status}",
        f"CPU: {report['environment']['cpu']}",
        f"Platform: {report['environment']['system']} / {report['environment']['machine']}",
        f"Samples: {report['settings']['samples']}; warmups: 2; "
        f"minimum batch: {report['settings']['min_ms']} ms",
        "",
        "## Measured results",
        "",
        "| Workload | Language | Variant | Median us | M elements/s | CV | Quality |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['workload']} | {row['language']} | {row['variant']} | "
            f"{row['median_ns'] / 1000:.3f} | {row['elements_per_second'] / 1e6:.3f} | "
            f"{row['coefficient_of_variation']:.3f} | "
            f"{'valid' if row['quality']['valid'] else 'INVALID'} |"
        )
    lines += [
        "",
        "## Allocation evidence",
        "",
        "Python reports traced peak bytes in an untimed invocation. Rust reports allocator "
        "calls and requested bytes in an untimed invocation. The metrics differ.",
        "Rust allocator counters remain present in the timed allocator path.",
        "",
    ]
    for row in report["rows"]:
        values = {k: v for k, v in row["allocation"].items() if k != "method"}
        lines.append(f"- {row['workload']}/{row['language']}/{row['variant']}: {values}")
    lines += [
        "",
        "## Model assumptions",
        "",
        json.dumps(report["rows"][0]["model"]["assumptions"], sort_keys=True),
        "",
        report["rows"][0]["model"]["caveat"],
        "",
    ]
    for row in report["rows"]:
        model = row["model"]
        lines.append(
            f"- {row['workload']}/{row['language']}/{row['variant']}: ideal "
            f"{model['ideal_minimum_ns'] / 1000:.3f} us; measured/ideal throughput "
            f"{model['measured_to_ideal_throughput_ratio']:.3f}; "
            f"{'MODEL EXCEEDED' if model['model_exceeded'] else model['limiting_assumption']}"
        )
    lines += [
        "",
        "## Source and compiler evidence",
        "",
        "[Raw samples and metadata](report.json), [evidence manifest](evidence/manifest.json), "
        "[Python kernels](evidence/sources/src/reality_check/workloads.py), "
        "[Rust kernels](evidence/sources/rust/src/lib.rs), "
        "[O0 IR](evidence/O0.ll), [O3 IR](evidence/O3.ll).",
        "",
    ]
    for file, symbols in manifest["symbols"].items():
        lines.append(
            f"- [{file}](evidence/{file}): "
            + ", ".join(
                f"[{name}, line {line}](evidence/{file}#L{line})" for name, line in symbols.items()
            )
        )
    lines += [
        "",
        "## Limits",
        "",
        "Input construction, process startup and allocation probes are outside kernel timing. "
        "Timing includes dispatch, checksum checks and loop overhead. Python cyclic GC is "
        "disabled during timing. Data is reused between batches; cache residency is uncontrolled. "
        "The compiler may vectorize loop or unrolled kernels and may remove machine branches. "
        "Inspect assembly before making instruction-level claims.",
        "",
    ]
    for row in report["rows"]:
        for reason in row["quality"]["reasons"]:
            lines.append(f"- INVALID {row_key(row)}: {reason}")
    return "\n".join(lines) + "\n"


def validate_report(report):
    if report.get("schema_version") != 1 or not 1 <= len(report.get("rows", [])) <= 24:
        raise ValueError("Invalid report schema")
    settings = Settings(**report["settings"])
    if len({row_key(r) for r in report["rows"]}) != len(report["rows"]):
        raise ValueError("Duplicate measurement rows")
    for row in report["rows"]:
        case = Case(row["workload"], row["size"], row["seed"])
        if row["language"] not in ("python", "rust") or row["variant"] not in VARIANTS:
            raise ValueError("Unknown report kernel")
        data = inputs(case)
        if row["checksum"] != reference(case, data) or row["input_digest"] != input_digest(data):
            raise ValueError("Report checksum or input mismatch")
        derived = summarize(row["batch_ns"], row["repeats"], settings, case.size)
        if any(row[key] != value for key, value in derived.items()):
            raise ValueError("Reported statistics disagree with raw samples")
        allocation = row["allocation"]
        metrics = ("calls", "bytes") if row["language"] == "rust" else ("peak_bytes",)
        if not isinstance(allocation.get("method"), str) or not allocation["method"]:
            raise ValueError("Missing allocation method")
        if any(type(allocation.get(key)) is not int or allocation[key] < 0 for key in metrics):
            raise ValueError("Invalid allocation measurement")
        if "model" in row:
            model = ceiling(
                case, row["variant"], Hardware(**row["model"]["assumptions"]), row["median_ns"]
            )
            if row["model"] != model:
                raise ValueError("Reported model disagrees with its assumptions")
    if report["valid"] != all(r["quality"]["valid"] for r in report["rows"]):
        raise ValueError("Report quality status is inconsistent")
    return report


def load_report(output: Path):
    manifest = verify(output / "evidence")
    report = validate_report(json.loads((output / "report.json").read_text()))
    if report["evidence_manifest_sha256"] != digest(output / "evidence/manifest.json"):
        raise ValueError("Evidence manifest changed since measurement")
    if report["compiler_flags"] != manifest["compiler_flags"]:
        raise ValueError("Compiler provenance mismatch")
    if report["environment"]["rustc"] != manifest["rustc"]:
        raise ValueError("Compiler version mismatch")
    if any("model" not in row for row in report["rows"]):
        raise ValueError("Report is missing its model assumptions")
    return report
