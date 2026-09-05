import pytest

from reality_check.evidence import capture, verify
from reality_check.native import evaluate
from reality_check.workloads import Case, inputs, reference


def test_compiler_evidence_is_inspectable_and_measured_binary_matches(tmp_path):
    output = tmp_path / "evidence"
    manifest = capture(output)
    assert verify(output) == manifest
    assert "reduction_loop" in manifest["symbols"]["O3.s"]
    assert "chase_loop" in manifest["symbols"]["O0.s"]
    assert "define" in (output / "O3.ll").read_text()
    case = Case("reduction", 64)
    result = evaluate(output / manifest["binary"], case, "loop")
    assert result["checksum"] == reference(case, inputs(case))
    (output / "O3.s").write_text("changed")
    with pytest.raises(ValueError, match="Changed"):
        verify(output)
    (output / "O3.s").unlink()
    with pytest.raises(ValueError, match="Missing"):
        verify(output)
