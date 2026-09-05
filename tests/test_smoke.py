import pytest

from reality_check.cli import main


def test_entrypoint(capsys):
    with pytest.raises(SystemExit) as result:
        main(["--help"])
    assert result.value.code == 0
    assert "Performance reality check" in capsys.readouterr().out
