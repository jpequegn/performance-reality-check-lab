import copy
from dataclasses import asdict

import pytest

from reality_check.cli import main
from reality_check.compare import compare
from reality_check.measurement import Settings, summarize
from reality_check.model import Hardware
from reality_check.report import load_report, run_experiment
from reality_check.workloads import Case, input_digest, inputs, reference


def sample_report(duration=1_000_000, calls=0):
    case = Case("reduction", 64)
    settings = Settings(3, 1, 0.2)
    row = {
        **asdict(case),
        "language": "rust",
        "variant": "loop",
        "checksum": reference(case, inputs(case)),
        "input_digest": input_digest(inputs(case)),
        **summarize([duration] * 3, 1, settings, case.size),
        "allocation": {"method": "counter", "calls": calls, "bytes": calls * 512},
    }
    return {
        "schema_version": 1,
        "rows": [row],
        "valid": True,
        "settings": asdict(settings),
        "environment": {"cpu": "fixture"},
        "compiler_flags": [],
        "warmups": 2,
        "measurement_order": [],
    }


def test_regression_detects_slowdown_and_allocation_increase():
    result = compare(sample_report(), sample_report(2_000_000, 1))
    assert not result["passed"]
    assert {r["kind"] for r in result["regressions"]} == {
        "timing",
        "allocation_calls",
        "allocation_bytes",
    }
    assert compare(sample_report(), sample_report())["passed"]


def test_incompatible_or_inconsistent_reports_are_rejected():
    report = sample_report()
    changed = copy.deepcopy(report)
    changed["environment"]["cpu"] = "other"
    with pytest.raises(ValueError, match="Incompatible"):
        compare(report, changed)
    changed = copy.deepcopy(report)
    changed["rows"][0]["median_ns"] = 1
    with pytest.raises(ValueError, match="statistics"):
        compare(report, changed)


def test_run_bundle_can_be_verified_and_missing_evidence_fails(tmp_path):
    out = tmp_path / "run"
    report = run_experiment(out, [Case("reduction", 1024)], Settings(3, 2, 1), Hardware())
    assert len(report["rows"]) == 6
    assert load_report(out) == report
    text = (out / "report.md").read_text()
    assert "Measured results" in text and "Model assumptions" in text
    assert "O3.s" in text
    assert main(["inspect", str(out)]) == (0 if report["valid"] else 2)
    with pytest.raises(FileExistsError):
        run_experiment(out, [Case("reduction")], Settings(), Hardware())
    (out / "evidence/O3.s").unlink()
    assert main(["inspect", str(out)]) == 2


def test_cli_rejects_invalid_run_before_creating_output(tmp_path):
    out = tmp_path / "invalid"
    assert main(["run", "--out", str(out), "--size", "65"]) == 2
    assert not out.exists()
