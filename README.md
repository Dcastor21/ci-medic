# CI Medic

A GitHub Action that reads a failed CI run, decides whether the failure is **flaky** or a **real regression**, and posts a short diagnosis on the pull request.

> Status: early development. See `docs/ARCHITECTURE.md` for the design and `docs/decisions/` for why it is built this way.

## What it does

1. Fetches logs for the failed workflow run through the GitHub API.
2. Normalizes the logs and extracts individual test failures (pytest, jest, `go test`, plus a generic fallback).
3. Fingerprints each failure so the same failure can be recognized across runs.
4. Classifies each failure as `flaky`, `likely-real`, or `unknown`, with the evidence used.
5. Posts (or updates) one PR comment with the diagnosis.
6. Optionally asks an LLM to explain the failure in plain language. This is off by default and never decides the classification.

## Quick start (planned)

```yaml
# .github/workflows/ci-medic.yml
on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]
permissions:
  actions: read
  pull-requests: write
jobs:
  diagnose:
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
    steps:
      - uses: <owner>/ci-medic@v0
```

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

All tests run offline against recorded log fixtures in `tests/fixtures/`. No API keys are needed to develop or test.

## License

MIT. See `LICENSE`.
