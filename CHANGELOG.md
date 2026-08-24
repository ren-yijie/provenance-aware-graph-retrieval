# Changelog

All notable public benchmark changes are documented here.

## [1.0.0] - 2026-08-24

### Added

- Package B preregistration for BM25, pinned MiniLM dense retrieval, unweighted graph traversal, and provenance-aware graph retrieval.
- Shared deterministic loaders, retrieval schemas, metrics, evidence traces, and versioned embedding caching.
- Twenty-two integrity and behavior tests.
- A complete 120-row run over the frozen 50-profile, 30-question synthetic benchmark.
- Per-query outputs, aggregate metrics, provenance traces, error analysis, environment manifest, and benchmark report.
- Reproducible result charts generated from the validated aggregate CSV.

### Documentation

- Disclosed that every profile is synthetic and separated the current benchmark from the earlier 30-profile developmental pilot.
- Recorded the authoritative executable-v1 raw and canonical fingerprints and the historical checksum discrepancy.
- Defined the valid claim boundary: retrieval only, exploratory scope, no production or real-world generalization claim.

