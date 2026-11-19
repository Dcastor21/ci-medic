import re
from pathlib import Path

import pytest

from cimedic.config import Config, ConfigError, load_config

FIXTURES = Path(__file__).parent / "fixtures" / "config"
FAKE_TOKEN = "fake-token-do-not-load-0123456789"


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / ".cimedic.yml"
    path.write_text(text, encoding="utf-8")
    return path


def problems_of(exc: pytest.ExceptionInfo[ConfigError]) -> str:
    return "\n".join(exc.value.problems)


def test_defaults_without_env_or_file(tmp_path: Path) -> None:
    config = load_config(env={}, config_path=tmp_path / "missing.yml")
    assert config == Config()
    assert config.max_reruns == 0
    assert config.explain is False
    assert config.history_backend == "cache"
    assert config.comment_mode == "update"
    assert config.flaky_threshold == 0.2
    assert config.ignore_patterns == ()
    assert config.github_token is None


def test_file_overrides_defaults() -> None:
    config = load_config(env={}, config_path=FIXTURES / "full.yml")
    assert config.max_reruns == 2
    assert config.explain is True
    assert config.history_backend == "file"
    assert config.comment_mode == "new"
    assert config.flaky_threshold == 0.35
    assert [p.pattern for p in config.ignore_patterns] == ["^tests/e2e/", "test_[a-z]+_slow"]


def test_env_overrides_file() -> None:
    env = {
        "INPUT_MAX_RERUNS": "5",
        "INPUT_EXPLAIN": "False",
        "INPUT_HISTORY_BACKEND": "memory",
        "INPUT_COMMENT_MODE": "update",
        "INPUT_FLAKY_THRESHOLD": "0.1",
        "INPUT_IGNORE_PATTERNS": "^vendor/\n\n  flaky_.*  \n",
    }
    config = load_config(env=env, config_path=FIXTURES / "full.yml")
    assert config.max_reruns == 5
    assert config.explain is False
    assert config.history_backend == "memory"
    assert config.comment_mode == "update"
    assert config.flaky_threshold == 0.1
    assert [p.pattern for p in config.ignore_patterns] == ["^vendor/", "flaky_.*"]


def test_empty_env_value_does_not_override_file() -> None:
    config = load_config(
        env={"INPUT_MAX_RERUNS": "", "INPUT_COMMENT_MODE": "  "},
        config_path=FIXTURES / "full.yml",
    )
    assert config.max_reruns == 2
    assert config.comment_mode == "new"


def test_default_path_is_repo_root_from_github_workspace(tmp_path: Path) -> None:
    write(tmp_path, "max_reruns: 3\n")
    assert load_config(env={"GITHUB_WORKSPACE": str(tmp_path)}).max_reruns == 3


@pytest.mark.parametrize("text", ["", "# only a comment\n"])
def test_empty_file_gives_defaults(tmp_path: Path, text: str) -> None:
    assert load_config(env={}, config_path=write(tmp_path, text)) == Config()


def test_token_read_from_action_input_then_github_token(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yml"
    assert load_config(env={"GITHUB_TOKEN": "b"}, config_path=missing).github_token == "b"
    both = {"INPUT_GITHUB_TOKEN": "a", "GITHUB_TOKEN": "b"}
    assert load_config(env=both, config_path=missing).github_token == "a"
    empty_input = {"INPUT_GITHUB_TOKEN": "", "GITHUB_TOKEN": "b"}
    assert load_config(env=empty_input, config_path=missing).github_token == "b"


def test_token_is_never_loaded_from_file() -> None:
    with pytest.raises(ConfigError) as exc:
        load_config(env={}, config_path=FIXTURES / "with_token.yml")
    assert "github_token must not be stored in the config file" in problems_of(exc)
    assert FAKE_TOKEN not in str(exc.value)


def test_token_in_file_is_rejected_even_when_env_provides_one() -> None:
    with pytest.raises(ConfigError) as exc:
        load_config(
            env={"INPUT_GITHUB_TOKEN": "env-token"}, config_path=FIXTURES / "with_token.yml"
        )
    assert FAKE_TOKEN not in str(exc.value)
    assert "env-token" not in str(exc.value)


def test_token_is_hidden_from_repr(tmp_path: Path) -> None:
    config = load_config(env={"INPUT_GITHUB_TOKEN": "s3cr3t"}, config_path=tmp_path / "missing.yml")
    assert "s3cr3t" not in repr(config)


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({"INPUT_MAX_RERUNS": "-1"}, "INPUT_MAX_RERUNS: expected a non-negative integer"),
        ({"INPUT_MAX_RERUNS": "1.5"}, "INPUT_MAX_RERUNS: expected a non-negative integer"),
        ({"INPUT_MAX_RERUNS": "three"}, "INPUT_MAX_RERUNS: expected a non-negative integer"),
        ({"INPUT_EXPLAIN": "maybe"}, "INPUT_EXPLAIN: expected true or false"),
        ({"INPUT_COMMENT_MODE": "delete"}, "INPUT_COMMENT_MODE: expected one of update, new"),
        ({"INPUT_FLAKY_THRESHOLD": "1.5"}, "INPUT_FLAKY_THRESHOLD: expected a number between 0"),
        ({"INPUT_FLAKY_THRESHOLD": "-0.1"}, "INPUT_FLAKY_THRESHOLD: expected a number between 0"),
        ({"INPUT_FLAKY_THRESHOLD": "nan"}, "INPUT_FLAKY_THRESHOLD: expected a number between 0"),
        ({"INPUT_FLAKY_THRESHOLD": "low"}, "INPUT_FLAKY_THRESHOLD: expected a number between 0"),
        ({"INPUT_IGNORE_PATTERNS": "ok\n(unclosed"}, "INPUT_IGNORE_PATTERNS[1]: invalid regular"),
    ],
)
def test_invalid_env_values(tmp_path: Path, env: dict[str, str], expected: str) -> None:
    with pytest.raises(ConfigError) as exc:
        load_config(env=env, config_path=tmp_path / "missing.yml")
    assert expected in problems_of(exc)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("max_reruns: true\n", ".cimedic.yml: max_reruns: expected a non-negative integer"),
        ("explain: 1\n", ".cimedic.yml: explain: expected true or false"),
        ("history_backend: ''\n", ".cimedic.yml: history_backend: expected a backend name"),
        ("flaky_threshold: true\n", ".cimedic.yml: flaky_threshold: expected a number"),
        ("ignore_patterns: 7\n", ".cimedic.yml: ignore_patterns: expected a list"),
        ("ignore_patterns: [1]\n", ".cimedic.yml: ignore_patterns[0]: expected a string"),
        ("max_rerun: 2\n", ".cimedic.yml: unknown setting(s) max_rerun"),
        ("- a\n- b\n", ".cimedic.yml: expected a mapping of settings, got list"),
    ],
)
def test_invalid_file_values(tmp_path: Path, text: str, expected: str) -> None:
    with pytest.raises(ConfigError) as exc:
        load_config(env={}, config_path=write(tmp_path, text))
    assert expected in problems_of(exc)


def test_invalid_file_value_is_ignored_when_env_overrides_it(tmp_path: Path) -> None:
    path = write(tmp_path, "max_reruns: lots\n")
    assert load_config(env={"INPUT_MAX_RERUNS": "1"}, config_path=path).max_reruns == 1


def test_all_problems_are_reported_together(tmp_path: Path) -> None:
    path = write(tmp_path, "comment_mode: sometimes\nflaky_threshold: 2\n")
    with pytest.raises(ConfigError) as exc:
        load_config(env={"INPUT_EXPLAIN": "perhaps"}, config_path=path)
    assert len(exc.value.problems) == 3
    assert str(exc.value).startswith("Invalid CI Medic configuration:\n- ")


def test_unreadable_file_is_reported_without_content(tmp_path: Path) -> None:
    path = tmp_path / ".cimedic.yml"
    path.write_bytes(b"max_reruns: \xff\xfe\n")
    with pytest.raises(ConfigError) as exc:
        load_config(env={}, config_path=path)
    assert ".cimedic.yml: could not be read (UnicodeDecodeError)" in problems_of(exc)


def test_yaml_syntax_error_reports_position_without_file_content(tmp_path: Path) -> None:
    path = write(tmp_path, "max_reruns: 1\nexplain: [secret-looking-value\n")
    with pytest.raises(ConfigError) as exc:
        load_config(env={}, config_path=path)
    message = str(exc.value)
    assert re.search(r"not valid YAML at line \d+, column \d+", message)
    assert "secret-looking-value" not in message
