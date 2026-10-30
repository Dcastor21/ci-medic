# Architecture

Living document. Update it whenever components or data flow change.

## Goal

Given a failed GitHub Actions run, produce a per-failure verdict (`flaky`, `likely-real`, `unknown`) with evidence, and post it on the pull request.

## Data flow

```
workflow_run event
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

| Module | Responsibility |
| --- | --- |
| `cli` | Entry point for the Action and local runs; wires the pipeline together |
| `config` | Loads `.cimedic.yml` and Action inputs; validates with defaults |
| `github` | Thin API client (runs, jobs, logs, rerun, comments); fully mockable |
| `logs` | Normalizes raw logs into structured lines grouped by job and step |
| `extract` | Framework parsers behind one `Extractor` interface; generic fallback |
| `fingerprint` | Normalizes volatile data (paths, ids, timings) and hashes failures |
| `history` | Stores per-fingerprint outcomes; pluggable backend |
| `classify` | Ordered heuristic rules; each rule returns a verdict and evidence |
| `explain` | Optional provider interface for plain-language explanations |
| `report` | Renders the PR comment; includes a hidden marker for idempotent updates |

## Key interfaces

- `Extractor.extract(log: NormalizedLog) -> list[Failure]`
- `Rule.evaluate(failure: Failure, history: History) -> Evidence | None`
- `HistoryStore.record(...)`, `HistoryStore.lookup(fingerprint)`
- `Explainer.explain(failure: Failure) -> str`

## Constraints

- Offline-testable: every network call sits behind `github` or `explain`.
- Deterministic classification: same inputs give the same verdict.
- Least privilege: the Action requests only `actions: read` and `pull-requests: write`.

## Open questions

Track unresolved design questions here and promote them to an ADR once decided.

- Where does history live by default (Actions cache, artifact, or committed file)?
- How should rerun probing be bounded to avoid wasting CI minutes?

## Decisions

See `docs/decisions/`.
