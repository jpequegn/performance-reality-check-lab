import gc
import json
import math
import statistics
import subprocess
import time
import tracemalloc
from dataclasses import dataclass

from .workloads import Case, input_digest, inputs, kernel, reference

MAX_REPEATS = 1 << 20


@dataclass(frozen=True)
class Settings:
    samples: int = 7
    min_ms: float = 20
    max_cv: float = 0.20

    def __post_init__(self):
        if type(self.samples) is not int or not 3 <= self.samples <= 31:
            raise ValueError("Samples must be an integer from 3 to 31")
        if not math.isfinite(self.min_ms) or not 1 <= self.min_ms <= 200:
            raise ValueError("Minimum batch duration must be 1 to 200 ms")
        if not math.isfinite(self.max_cv) or not 0 < self.max_cv <= 1:
            raise ValueError("Maximum coefficient of variation must be in (0, 1]")


def checked(function, data, expected):
    result = function(data)
    if type(result) is not int or result != expected:
        raise ValueError("Benchmark invalid: kernel checksum mismatch")
    return result


def summarize(batch_ns, repeats, settings: Settings, size):
    if type(repeats) is not int or not 1 <= repeats <= MAX_REPEATS:
        raise ValueError("Invalid repeat count")
    if len(batch_ns) != settings.samples or any(type(n) is not int or n <= 0 for n in batch_ns):
        raise ValueError("Invalid timing samples")
    samples = [n / repeats for n in batch_ns]
    median = statistics.median(samples)
    cv = statistics.stdev(samples) / statistics.mean(samples)
    reasons = []
    if min(batch_ns) < settings.min_ms * 1e6 * 0.5:
        reasons.append("batch duration below half the requested minimum")
    if cv > settings.max_cv:
        reasons.append("sample variance exceeds configured limit")
    return {
        "batch_ns": batch_ns,
        "repeats": repeats,
        "ns_per_iteration": samples,
        "median_ns": median,
        "min_ns": min(samples),
        "p95_ns": sorted(samples)[math.ceil(len(samples) * 0.95) - 1],
        "coefficient_of_variation": cv,
        "elements_per_second": size * 1e9 / median,
        "quality": {"valid": not reasons, "reasons": reasons},
    }


def python_measure(case: Case, variant, settings: Settings):
    data = inputs(case)
    function = kernel(case.workload, variant)
    expected = reference(case, data)
    for _ in range(2):
        checked(function, data, expected)

    def batch(repeats):
        start = time.perf_counter_ns()
        for _ in range(repeats):
            checked(function, data, expected)
        return time.perf_counter_ns() - start

    was_enabled = gc.isenabled()
    gc.disable()
    try:
        repeats = 1
        while batch(repeats) < settings.min_ms * 1e6 and repeats < MAX_REPEATS:
            repeats *= 2
        samples = [batch(repeats) for _ in range(settings.samples)]
    finally:
        if was_enabled:
            gc.enable()
    if tracemalloc.is_tracing():
        raise ValueError("Stop external tracemalloc before measuring allocation")
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        checked(function, data, expected)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return {
        "language": "python",
        "variant": variant,
        "checksum": expected,
        "input_digest": input_digest(data),
        **summarize(samples, repeats, settings, case.size),
        "allocation": {"method": "tracemalloc peak in an untimed invocation", "peak_bytes": peak},
    }


def rust_measure(binary, case: Case, variant, settings: Settings):
    result = subprocess.run(
        [
            str(binary),
            case.workload,
            variant,
            str(case.size),
            str(case.seed),
            str(settings.samples),
            str(settings.min_ms),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    payload = json.loads(result.stdout)
    data = inputs(case)
    if payload["checksum"] != reference(case, data) or payload["input_digest"] != input_digest(
        data
    ):
        raise ValueError("Benchmark invalid: native result or input mismatch")
    return {
        "language": "rust",
        "variant": variant,
        "checksum": payload["checksum"],
        "input_digest": payload["input_digest"],
        **summarize(payload["batch_ns"], payload["repeats"], settings, case.size),
        "allocation": {
            "method": "allocator counter delta in an untimed invocation",
            "calls": payload["allocation_calls"],
            "bytes": payload["allocation_bytes"],
        },
    }
