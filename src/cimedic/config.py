"""Loads `.cimedic.yml` and Action inputs; validates them and applies defaults.

Precedence, highest first: environment (Action inputs as ``INPUT_<NAME>``), then
``.cimedic.yml`` in the repo root, then the defaults on `Config`. An empty environment
value counts as unset, because the runner passes unset inputs as empty strings.

``github_token`` is read from the environment only (``INPUT_GITHUB_TOKEN``, then
``GITHUB_TOKEN``). A token in the file is rejected so it never sits in the repo.
"""

from __future__ import annotations

import math
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Literal, cast

import yaml

CONFIG_FILENAME = ".cimedic.yml"
TOKEN_ENV_VARS = ("INPUT_GITHUB_TOKEN", "GITHUB_TOKEN")

CommentMode = Literal["update", "new"]
COMMENT_MODES: tuple[CommentMode, ...] = ("update", "new")


@dataclass(frozen=True)
class Config:
    github_token: str | None = field(default=None, repr=False)
    max_reruns: int = 0
    explain: bool = False
    history_backend: str = "cache"
    comment_mode: CommentMode = "update"
    flaky_threshold: float = 0.2
    ignore_patterns: tuple[re.Pattern[str], ...] = ()


class ConfigError(ValueError):
    """Raised with every problem found, one per line, so users can fix them in one pass."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__(
            "Invalid CI Medic configuration:\n" + "\n".join(f"- {p}" for p in problems)
        )


_FILE_KEYS = tuple(f.name for f in fields(Config) if f.name != "github_token")


def load_config(
    env: Mapping[str, str] | None = None,
    config_path: Path | None = None,
) -> Config:
    """Build a validated `Config` from the environment and an optional config file.

    ``env`` defaults to ``os.environ``. ``config_path`` defaults to ``.cimedic.yml`` under
    ``$GITHUB_WORKSPACE`` (or the current directory); a missing file is not an error.
    """
    env = os.environ if env is None else env
    if config_path is None:
        config_path = Path(env.get("GITHUB_WORKSPACE") or ".") / CONFIG_FILENAME

    problems: list[str] = []
    raw: dict[str, tuple[Any, str]] = {}

    for key, value in _read_file(config_path, problems).items():
        raw[key] = (value, f"{config_path.name}: {key}")
    for key in _FILE_KEYS:
        env_name = f"INPUT_{key.upper()}"
        if env.get(env_name, "").strip():
            raw[key] = (env[env_name], env_name)

    values: dict[str, Any] = {}
    for key, (value, source) in raw.items():
        parsed = _PARSERS[key](value, source, problems)
        if parsed is not None:
            values[key] = parsed

    if problems:
        raise ConfigError(problems)

    token = next((env[name] for name in TOKEN_ENV_VARS if env.get(name, "").strip()), None)
    return Config(github_token=token, **values)


def _read_file(path: Path, problems: list[str]) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.MarkedYAMLError as exc:
        # Report the position only: the default message quotes file content.
        mark = exc.problem_mark
        where = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        problems.append(f"{path.name}: not valid YAML{where} ({exc.problem})")
        return {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        problems.append(f"{path.name}: could not be read ({type(exc).__name__})")
        return {}

    if data is None:
        return {}
    if not isinstance(data, dict):
        problems.append(f"{path.name}: expected a mapping of settings, got {type(data).__name__}")
        return {}

    if "github_token" in data:
        problems.append(
            f"{path.name}: github_token must not be stored in the config file; "
            "pass it with the github_token Action input instead"
        )
    unknown = sorted(str(k) for k in data if k not in _FILE_KEYS and k != "github_token")
    if unknown:
        problems.append(
            f"{path.name}: unknown setting(s) {', '.join(unknown)}; "
            f"known settings are {', '.join(_FILE_KEYS)}"
        )
    return {k: v for k, v in data.items() if k in _FILE_KEYS}


def _parse_int(value: Any, source: str, problems: list[str]) -> int | None:
    if isinstance(value, str):
        try:
            value = int(value.strip())
        except ValueError:
            pass
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        problems.append(f"{source}: expected a non-negative integer, got {value!r}")
        return None
    return value


def _parse_bool(value: Any, source: str, problems: list[str]) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"
    problems.append(f"{source}: expected true or false, got {value!r}")
    return None


def _parse_history_backend(value: Any, source: str, problems: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        problems.append(f"{source}: expected a backend name, got {value!r}")
        return None
    return value.strip().lower()


def _parse_comment_mode(value: Any, source: str, problems: list[str]) -> CommentMode | None:
    mode = value.strip().lower() if isinstance(value, str) else value
    if mode not in COMMENT_MODES:
        problems.append(f"{source}: expected one of {', '.join(COMMENT_MODES)}, got {value!r}")
        return None
    return cast(CommentMode, mode)


def _parse_threshold(value: Any, source: str, problems: list[str]) -> float | None:
    number: float | None = None
    if isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            pass
    elif isinstance(value, int | float) and not isinstance(value, bool):
        number = float(value)
    if number is None or math.isnan(number) or not 0.0 <= number <= 1.0:
        problems.append(f"{source}: expected a number between 0 and 1, got {value!r}")
        return None
    return number


def _parse_patterns(
    value: Any, source: str, problems: list[str]
) -> tuple[re.Pattern[str], ...] | None:
    # Action inputs are strings: one pattern per line, since commas are valid in regexes.
    if isinstance(value, str):
        items: list[Any] = [line.strip() for line in value.splitlines() if line.strip()]
    elif isinstance(value, list):
        items = value
    else:
        problems.append(f"{source}: expected a list of regular expressions, got {value!r}")
        return None

    compiled: list[re.Pattern[str]] = []
    ok = True
    for i, item in enumerate(items):
        if not isinstance(item, str):
            problems.append(f"{source}[{i}]: expected a string, got {item!r}")
            ok = False
            continue
        try:
            compiled.append(re.compile(item))
        except re.error as exc:
            problems.append(f"{source}[{i}]: invalid regular expression {item!r} ({exc})")
            ok = False
    return tuple(compiled) if ok else None


_PARSERS: dict[str, Callable[[Any, str, list[str]], Any]] = {
    "max_reruns": _parse_int,
    "explain": _parse_bool,
    "history_backend": _parse_history_backend,
    "comment_mode": _parse_comment_mode,
    "flaky_threshold": _parse_threshold,
    "ignore_patterns": _parse_patterns,
}
