import math
from dataclasses import asdict, dataclass

from .workloads import VARIANTS, Case


@dataclass(frozen=True)
class Hardware:
    name: str = "Illustrative 3 GHz / 256-bit / 30 GB/s profile"
    source: str = "Hypothetical learning assumptions; not detected hardware"
    clock_ghz: float = 3.0
    vector_lanes_u64: int = 4
    vector_ops_per_cycle: float = 2.0
    bandwidth_gbps: float = 30.0
    dependent_load_cycles: float = 8.0

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Hardware model needs a name")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("Hardware assumptions need provenance")
        for key in ("clock_ghz", "vector_ops_per_cycle", "bandwidth_gbps", "dependent_load_cycles"):
            value = getattr(self, key)
            if (
                type(value) not in (int, float)
                or not math.isfinite(value)
                or not 0 < value <= 10000
            ):
                raise ValueError(f"Invalid hardware assumption: {key}")
        if type(self.vector_lanes_u64) is not int or not 1 <= self.vector_lanes_u64 <= 64:
            raise ValueError("Vector lanes must be an integer from 1 to 64")


def ceiling(case: Case, variant: str, hardware: Hardware, measured_ns: float):
    if variant not in VARIANTS:
        raise ValueError("Unknown variant")
    if not math.isfinite(measured_ns) or measured_ns <= 0:
        raise ValueError("Measured duration must be finite and positive")
    arithmetic_ops = case.size * (3 if case.workload == "branch" else 1)
    logical_bytes = case.size * (24 if variant == "allocating" else 8)
    lanes = 1 if case.workload == "chase" else hardware.vector_lanes_u64
    clock_hz = hardware.clock_ghz * 1e9
    bounds = {
        "compute_seconds": arithmetic_ops / (clock_hz * lanes * hardware.vector_ops_per_cycle),
        "memory_seconds": logical_bytes / (hardware.bandwidth_gbps * 1e9),
        "dependency_seconds": case.size * hardware.dependent_load_cycles / clock_hz
        if case.workload == "chase"
        else 0,
    }
    bottleneck = max(bounds, key=bounds.get)
    seconds = bounds[bottleneck]
    ratio = seconds * 1e9 / measured_ns
    return {
        "assumptions": asdict(hardware),
        "arithmetic_ops_proxy": arithmetic_ops,
        "logical_u64_traffic_bytes": logical_bytes,
        **bounds,
        "ideal_minimum_ns": seconds * 1e9,
        "ideal_elements_per_second": case.size / seconds,
        "limiting_assumption": bottleneck,
        "measured_to_ideal_throughput_ratio": ratio,
        "model_exceeded": ratio > 1,
        "caveat": "Illustrative arithmetic/traffic model. It assumes vectorization where eligible, "
        "uses logical u64 traffic, and omits Python object traffic, allocation, caches, "
        "branches and interpreter costs. Exceeding it means assumptions need revision.",
    }
