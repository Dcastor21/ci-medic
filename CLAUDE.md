# CLAUDE.md

Guidance for Claude Code when working in this repo.

## Project

CI Medic is a GitHub Action (Python 3.11+) that diagnoses failed CI runs: flaky vs real failure. Read `docs/ARCHITECTURE.md` before changing structure and `docs/decisions/` before reversing a past choice.

## Rules

- Never ask for, print, or write secrets. Tests must run with no API keys and no network. Use recorded fixtures in `tests/fixtures/`.
- The LLM explainer is optional and off by default. Classification must be deterministic and explainable without it.
- Never log or store raw CI logs beyond what a feature needs. Do not add telemetry.
- Small steps: one feature or fix per change, tests first or alongside.

## Commands

- Install: `pip install -e ".[dev]"`
- Test: `pytest -q`
- Lint/format: `ruff check . && ruff format .`
- Types: `mypy src`

## Layout

- `src/cimedic/` package: `cli`, `github`, `logs`, `extract`, `fingerprint`, `history`, `classify`, `report`, `explain`, `config`
- `tests/` mirrors `src/`; fixtures in `tests/fixtures/`
- `docs/ARCHITECTURE.md` living architecture doc
- `docs/decisions/NNNN-title.md` one ADR per significant decision

## Definition of done for every feature

1. Tests pass, including at least one fixture-based test and one edge case.
2. `ruff` and `mypy` clean.
3. `docs/ARCHITECTURE.md` updated if components or data flow changed.
4. An ADR added in `docs/decisions/` if a real choice between alternatives was made.
5. README updated if user-facing behavior changed.
