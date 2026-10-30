from importlib.metadata import entry_points, version

import pytest

import cimedic
from cimedic.cli import main


def test_package_version_matches_installed_metadata() -> None:
    assert cimedic.__version__ == version("cimedic")


def test_version_flag_prints_version_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"cimedic {cimedic.__version__}"


def test_console_script_points_at_cli_main() -> None:
    (script,) = entry_points(group="console_scripts", name="cimedic")
    assert script.value == "cimedic.cli:main"


def test_unknown_flag_exits_with_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--no-such-flag"])
    assert exc.value.code == 2
    assert "unrecognized arguments" in capsys.readouterr().err
