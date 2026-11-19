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
| `config` | Loads `.cimedic.yml` and Action inputs; validates with defaults | stub |
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
- `Extractor.extract(log: NormalizedLog) -> list[Failure]`
- `Rule.evaluate(failure: Failure, history: History) -> Evidence | None`
- `HistoryStore.record(...)`, `HistoryStore.lookup(fingerprint)`
- `Explainer.explain(failure: Failure) -> str`

## Constraints

- Offline-testable: every network call sits behind `github` or `explain`.
- Deterministic classification: same inputs give the same verdict.
- Least privilege: the Action requests only `actions: read` and `pull-requests: write`.

## Packaging and tooling

- `pyproject.toml`, src layout, hatchling build backend, Python 3.11+, no runtime dependencies yet.
- Dev extras (`.[dev]`): pytest, pytest-cov, ruff, mypy (strict).
- CI (`.github/workflows/ci.yml`): ruff check, ruff format --check, mypy, pytest with coverage on Python 3.11 and 3.12.

## Open questions

Track unresolved design questions here and promote them to an ADR once decided.

- Where does history live by default (Actions cache, artifact, or committed file)?
- How should rerun probing be bounded to avoid wasting CI minutes?

## Decisions

See `docs/decisions/`.
