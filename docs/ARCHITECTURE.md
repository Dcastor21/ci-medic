# Architecture

Living document. Update it whenever components or data flow change.

## Goal

Given a failed GitHub Actions run, produce a per-failure verdict (`flaky`, `likely-real`, `unknown`) with evidence, and post it on the pull request.

## Data flow

```
workflow_run event / `cimedic` console script
   -> cli      (parse args, build config, run the pipeline)
   -> github   (fetch run, jobs, logs)
   -> logs     (strip ANSI/timestamps, split by job/step)
   -> extract  (parse test failures per framework)
   -> fingerprint (stable ID per failure)
   -> history  (load prior outcomes for each fingerprint)
   -> classify (heuristics -> verdict + evidence)
   -> explain  (optional LLM summary; never changes verdict)
   -> report   (render markdown)
   -> github   (create or update the PR comment)
```

## Components

All modules live in `src/cimedic/`. The package version is `cimedic.__version__` (single source, read by the build backend).

| Module | Responsibility | Status |
| --- | --- | --- |
| `cli` | Entry point for the Action and local runs; wires the pipeline together | `--version` only (argparse, ADR 0004) |
| `config` | Loads `.cimedic.yml` and Action inputs; validates with defaults | done (dataclass + PyYAML, ADRs 0005, 0006) |
| `github` | Thin API client (runs, jobs, logs, rerun, comments); fully mockable | stub |
| `logs` | Normalizes raw logs into structured lines grouped by job and step | stub |
| `extract` | Framework parsers behind one `Extractor` interface; generic fallback | stub |
| `fingerprint` | Normalizes volatile data (paths, ids, timings) and hashes failures | stub |
| `history` | Stores per-fingerprint outcomes; pluggable backend | stub |
| `classify` | Ordered heuristic rules; each rule returns a verdict and evidence | stub |
| `explain` | Optional provider interface for plain-language explanations | stub |
| `report` | Renders the PR comment; includes a hidden marker for idempotent updates | stub |

## Key interfaces

- `cli.main(argv: Sequence[str] | None = None) -> int` (console script `cimedic`; returns the exit code)
- `config.load_config(env: Mapping[str, str] | None = None, config_path: Path | None = None) -> Config` (raises `ConfigError` listing every problem)
- `Extractor.extract(log: NormalizedLog) -> list[Failure]`
- `Rule.evaluate(failure: Failure, history: History) -> Evidence | None`
- `HistoryStore.record(...)`, `HistoryStore.lookup(fingerprint)`
- `Explainer.explain(failure: Failure) -> str`

## Constraints

- Offline-testable: every network call sits behind `github` or `explain`.
- Deterministic classification: same inputs give the same verdict.
- Least privilege: the Action requests only `actions: read` and `pull-requests: write`.

## Configuration

`load_config()` merges three sources, highest precedence first:

1. Environment: Action inputs as `INPUT_<SETTING>` (for example `INPUT_MAX_RERUNS`). Empty values count as unset, because the runner passes unset inputs as `""`. The composite `action.yml` must map each input to this name explicitly, since composite actions don't export inputs automatically.
2. `.cimedic.yml` under `$GITHUB_WORKSPACE` (or the current directory). Optional. Unknown keys are errors, to catch typos.
3. Defaults on `Config`.

| Setting | Type | Default | Notes |
| --- | --- | --- | --- |
| `github_token` | str or None | None | Env only: `INPUT_GITHUB_TOKEN`, then `GITHUB_TOKEN`. Rejected if found in the file. Hidden from `repr`. |
| `max_reruns` | int >= 0 | 0 | |
| `explain` | bool | false | Env accepts `true`/`false`, case-insensitive |
| `history_backend` | str | `cache` | Lowercased. Not yet checked against real backends (see `history`) |
| `comment_mode` | `update` or `new` | `update` | |
| `flaky_threshold` | float in [0, 1] | 0.2 | |
| `ignore_patterns` | list of regex | empty | Env: one pattern per line (commas are valid regex). Compiled at load time. |

Error messages name their source (`INPUT_MAX_RERUNS: ...` or `.cimedic.yml: max_reruns: ...`). They never include a token or quote raw file content.

## Packaging and tooling

- `pyproject.toml`, src layout, hatchling build backend, Python 3.11+. Runtime dependency: PyYAML (ADR 0006).
- Dev extras (`.[dev]`): pytest, pytest-cov, ruff, mypy (strict), types-PyYAML.
- CI (`.github/workflows/ci.yml`): ruff check, ruff format --check, mypy, pytest with coverage on Python 3.11 and 3.12.

## Open questions

Track unresolved design questions here and promote them to an ADR once decided.

- Where does history live by default (Actions cache, artifact, or committed file)?
- How should rerun probing be bounded to avoid wasting CI minutes?

## Decisions

See `docs/decisions/`.
