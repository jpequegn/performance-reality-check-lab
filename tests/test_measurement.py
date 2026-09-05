import pytest

from reality_check.measurement import Settings, checked, python_measure, rust_measure, summarize
from reality_check.workloads import Case


def test_summary_separates_valid_noisy_and_short_evidence():
    settings = Settings(samples=3, min_ms=1)
    valid = summarize([1_000_000] * 3, 10, settings, 64)
    assert valid["quality"]["valid"]
    assert valid["median_ns"] == 100_000
    assert valid["elements_per_second"] == 640_000
    assert not summarize([1_000_000, 10_000_000, 1_000_000], 10, settings, 64)["quality"]["valid"]
    assert not summarize([100] * 3, 1, settings, 64)["quality"]["valid"]
    with pytest.raises(ValueError):
        summarize([0] * 3, 1, settings, 64)
    with pytest.raises(ValueError):
        checked(lambda _: 99, [], 100)


@pytest.mark.parametrize("settings", [{"samples": 2}, {"min_ms": float("nan")}, {"max_cv": 0}])
def test_settings_are_bounded(settings):
    with pytest.raises(ValueError):
        Settings(**settings)


def test_python_allocation_probe_detects_deliberate_copy():
    case = Case("reduction", 1024)
    settings = Settings(samples=3, min_ms=1, max_cv=1)
    loop = python_measure(case, "loop", settings)
    allocating = python_measure(case, "allocating", settings)
    assert loop["checksum"] == allocating["checksum"]
    assert allocating["allocation"]["peak_bytes"] > loop["allocation"]["peak_bytes"] + 4096


def test_native_measures_kernel_and_counts_copy_allocations(native_binary):
    case = Case("reduction", 1024)
    settings = Settings(samples=3, min_ms=1, max_cv=1)
    loop = rust_measure(native_binary, case, "loop", settings)
    allocating = rust_measure(native_binary, case, "allocating", settings)
    assert loop["allocation"]["calls"] == 0
    assert allocating["allocation"]["calls"] == 1
    assert allocating["allocation"]["bytes"] == 8192
    assert loop["checksum"] == allocating["checksum"]
    assert len(loop["batch_ns"]) == 3
