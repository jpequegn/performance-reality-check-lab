import math

from .report import row_key, validate_report


def compare(baseline, candidate, slowdown=1.15):
    if not math.isfinite(slowdown) or slowdown <= 1:
        raise ValueError("Slowdown ratio must be finite and greater than one")
    for report in (baseline, candidate):
        validate_report(report)
        if not report["valid"]:
            raise ValueError("Cannot compare noisy or invalid measurements")
        if report["environment"].get("cpu") == "unavailable":
            raise ValueError(
                "CPU identity is unavailable; comparison cannot establish compatibility"
            )
    for key in ("environment", "settings", "compiler_flags", "warmups", "measurement_order"):
        if baseline[key] != candidate[key]:
            raise ValueError(f"Incompatible runs: {key}")
    before = {row_key(row): row for row in baseline["rows"]}
    after = {row_key(row): row for row in candidate["rows"]}
    if before.keys() != after.keys():
        raise ValueError("Incompatible workload sets")
    regressions = []
    for key, previous in before.items():
        current = after[key]
        ratio = current["median_ns"] / previous["median_ns"]
        if ratio > slowdown:
            regressions.append({"case": key, "kind": "timing", "ratio": ratio})
        if previous["allocation"]["method"] != current["allocation"]["method"]:
            raise ValueError("Incompatible allocation probes")
        for metric in ("calls", "bytes", "peak_bytes"):
            if metric in previous["allocation"]:
                old = previous["allocation"][metric]
                new = current["allocation"][metric]
                if new > old + (0 if metric == "calls" else 256):
                    regressions.append(
                        {"case": key, "kind": f"allocation_{metric}", "before": old, "after": new}
                    )
    return {
        "compatible": True,
        "slowdown_threshold": slowdown,
        "regressions": regressions,
        "passed": not regressions,
        "caveat": "Threshold comparison is a screening check, not statistical proof of regression.",
    }
