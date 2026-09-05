import copy
import json

import pytest
from test_reports import sample_report

from reality_check.cli import main
from reality_check.compare import compare
from reality_check.evidence import capture, verify
from reality_check.measurement import Settings
from reality_check.model import Hardware, ceiling
from reality_check.report import run_experiment, validate_report
from reality_check.workloads import Case


def test_allocation_and_model_fields_are_validated():
    report = sample_report()
    report["rows"][0]["allocation"]["calls"] = -1
    with pytest.raises(ValueError, match="allocation"):
        validate_report(report)
    report = sample_report()
    row = report["rows"][0]
    row["model"] = ceiling(Case("reduction", 64), "loop", Hardware(), row["median_ns"])
    row["model"]["ideal_minimum_ns"] = 0
    with pytest.raises(ValueError, match="model"):
        validate_report(report)


def test_noise_and_unknown_cpu_block_comparison():
    report = sample_report()
    unknown = copy.deepcopy(report)
    unknown["environment"]["cpu"] = "unavailable"
    with pytest.raises(ValueError, match="CPU"):
        compare(unknown, unknown)
    noisy = sample_report()
    noisy["settings"]["max_cv"] = 0.01
    noisy["rows"][0]["batch_ns"][0] *= 20
    with pytest.raises(ValueError):
        compare(report, noisy)


def test_incomplete_manifest_cannot_hide_missing_artifact(tmp_path):
    out = tmp_path / "evidence"
    capture(out)
    path = out / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["artifacts"] = [r for r in manifest["artifacts"] if r["path"] != "O3.s"]
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Incomplete"):
        verify(out)


def test_noisy_run_is_saved_and_inspect_fails(tmp_path, monkeypatch):
    import reality_check.report as reports
    from reality_check.measurement import summarize

    def measurement(case, variant, settings, language="rust"):
        row = sample_report()["rows"][0]
        return {
            key: value for key, value in row.items() if key not in ("workload", "size", "seed")
        } | {
            "variant": variant,
            "language": language,
            "allocation": {
                "method": "fixture",
                **({"peak_bytes": 100} if language == "python" else {"calls": 0, "bytes": 0}),
            },
            **summarize([1_000_000, 100_000_000, 1_000_000], 1, settings, case.size),
        }

    monkeypatch.setattr(reports, "python_measure", lambda *args: measurement(*args, "python"))
    monkeypatch.setattr(reports, "rust_measure", lambda binary, *args: measurement(*args))
    out = tmp_path / "noisy"
    report = run_experiment(out, [Case("reduction", 64)], Settings(3, 1, 0.2), Hardware())
    assert not report["valid"]
    validate_report(report)
    assert "INVALID" in (out / "report.md").read_text()
    assert main(["inspect", str(out)]) == 2
