import subprocess

import pytest

from reality_check.native import evaluate
from reality_check.workloads import VARIANTS, WORKLOADS, Case, input_digest, inputs, reference


@pytest.mark.parametrize("workload", WORKLOADS)
@pytest.mark.parametrize("size,seed", [(64, 0), (128, 7), (4096, 91)])
def test_cross_language_identity(native_binary, workload, size, seed):
    case = Case(workload, size, seed)
    data = inputs(case)
    for variant in VARIANTS:
        result = evaluate(native_binary, case, variant)
        assert result["checksum"] == reference(case, data)
        assert result["input_digest"] == input_digest(data)


def test_native_rejects_invalid_arguments(native_binary):
    result = subprocess.run(
        [str(native_binary), "reduction", "loop", "65", "7"], capture_output=True
    )
    assert result.returncode == 2
