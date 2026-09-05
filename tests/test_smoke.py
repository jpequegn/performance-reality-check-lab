from reality_check.cli import main


def test_entrypoint(capsys):
    main()
    assert "Performance reality check" in capsys.readouterr().out
