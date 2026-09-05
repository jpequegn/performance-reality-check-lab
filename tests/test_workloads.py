import pytest

from reality_check.workloads import (
    VARIANTS,
    WORKLOADS,
    Case,
    inputs,
    kernel,
    random_words,
    reference,
)


@pytest.mark.parametrize("workload", WORKLOADS)
@pytest.mark.parametrize("size,seed", [(64, 0), (128, 7), (4096, 91)])
def test_equal_variants(workload, size, seed):
    case = Case(workload, size, seed)
    data = inputs(case)
    original = data.copy()
    assert data == inputs(case)
    for variant in VARIANTS:
        assert kernel(workload, variant)(data) == reference(case, data)
    assert data == original


def test_generator_known_first_word_and_full_pointer_cycle():
    assert next(random_words(1)) == 1082269761
    data = inputs(Case("chase", 128, 11))
    visited = set()
    index = 0
    for _ in data:
        visited.add(index)
        index = data[index]
    assert len(visited) == 128
    assert index == 0


@pytest.mark.parametrize("size", [0, 63, 65, 1 << 21, True])
def test_invalid_size(size):
    with pytest.raises(ValueError):
        Case("reduction", size)


def test_invalid_names_and_seed():
    with pytest.raises(ValueError):
        Case("unknown")
    with pytest.raises(ValueError):
        Case("reduction", seed=-1)
    with pytest.raises(ValueError):
        kernel("reduction", "mystery")
