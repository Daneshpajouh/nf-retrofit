import pytest

from nf_retrofit.cli import main


def test_param_without_equals_is_a_usage_error(tmp_path, capsys):
    with pytest.raises(SystemExit) as stop:
        main(
            [
                "manifest",
                "--out",
                str(tmp_path / "m.json"),
                "--pipeline-dir",
                str(tmp_path),
                "--param",
                "profile",
            ]
        )
    assert stop.value.code == 2
    assert "key=value" in capsys.readouterr().err
    assert not (tmp_path / "m.json").exists()
