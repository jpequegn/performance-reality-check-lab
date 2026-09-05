import pytest

from reality_check.model import Hardware, ceiling
from reality_check.workloads import Case


def test_dimensional_compute_and_memory_bounds():
    result = ceiling(Case("reduction", 1024), "loop", Hardware(), 10000)
    assert result["compute_seconds"] == pytest.approx(1024 / 24e9)
    assert result["memory_seconds"] == pytest.approx(8192 / 30e9)
    assert result["ideal_elements_per_second"] == pytest.approx(30e9 / 8)
    assert result["limiting_assumption"] == "memory_seconds"


def test_chase_dependency_bound_and_allocation_traffic():
    result = ceiling(Case("chase", 1024), "loop", Hardware(), 10000)
    assert result["dependency_seconds"] == pytest.approx(1024 * 8 / 3e9)
    assert result["limiting_assumption"] == "dependency_seconds"
    allocating = ceiling(Case("reduction", 1024), "allocating", Hardware(), 10000)
    assert allocating["logical_u64_traffic_bytes"] == 24576


def test_fast_measurement_flags_model_assumptions():
    assert ceiling(Case("reduction", 1024), "loop", Hardware(), 1)["model_exceeded"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("clock_ghz", 0),
        ("bandwidth_gbps", float("inf")),
        ("vector_lanes_u64", 1.5),
        ("dependent_load_cycles", -1),
        ("source", ""),
        ("clock_ghz", True),
    ],
)
def test_invalid_assumptions(field, value):
    with pytest.raises(ValueError):
        Hardware(**{field: value})
