# Practicum Phase II: post-hoc diagnosis and mechanism experiments

These additions extend the analysis of **Benchmark v1.0.0**, without replacing its frozen graph, Gold labels, implementation or results. All profiles remain synthetic. No experimental variant is promoted to the official benchmark implementation.

## Read the findings

1. [Per-question error analysis (Chinese)](audit-2026-10-30/逐题错误分析.md): examines eight answerable questions with zero graph seeds, then six questions where provenance excludes Gold candidates. The audit contains all 120 method–question outcomes.
2. [Graph representation specification and case studies (Chinese)](research-2026-10-31/图表示规范与案例.md): contrasts query conditions, source evidence and missing graph entry points for Q005, Q006 and Q017; includes evidence-field and identity requirements.
3. [Three-step research results (Chinese)](research-2026-10-31/三步研究结果.md): reports isolated name-coverage, multi-alias and possessive-normalization experiments, including regressions.
4. [Protocol fixed before the mechanism runs](research-2026-10-31/experiment_protocol.md), [summary](research-2026-10-31/summary.csv), [all per-query results](research-2026-10-31/per_query_results.csv), [every ranking change](research-2026-10-31/changes.csv).

## What was observed

- Eight zero-seed questions account for 21 Gold-assignment misses in each graph method. The source profiles exist; the failure occurs before candidate generation.
- Seven Gold candidates across six questions are excluded because no path evidence passes the literal phrase checks. Four of those candidates were in Unweighted Top-3.
- Adding names for all 50 profiles recovers the two Q005 Gold Sources on the original diagnostic set. Additional checks expose false positives when the requested name and occupation do not hold for the same person.
- Checking multiple matching aliases recovers one Q007 Gold. Possessive compatibility recovers Q023 but also admits two false positives on Q016. Removing a filtering failure does not guarantee a Gold Source reaches Top-3.

These are local mechanism observations, not evidence of a generally superior retrieval method.

## Evaluation boundaries

The original 30 questions were already inspected and are a **diagnostic set**. The additional 16 questions were fixed before running the variants, but were authored after examining the same corpus and original failures. They are **post-hoc development checks, not an independent held-out test**. Their labels reuse some original decisions. In particular, the Q017-derived family-foundation label has a documented semantic ambiguity for the Drummond Foundation.

The 16 checks include 12 answerable questions and four empty-Gold negatives. Positive retrieval metrics and negative abstention are reported separately. Six configurations across 46 questions produce 276 rows. Experimental retrievers take graph/text inputs and queries, not Gold labels. No model download or MiniLM rerun is required for this analysis.

## Reproduce without overwriting archived evidence

From a full Git clone, with the `v1.0.0` tag available:

```bash
python scripts/reproduce_phase2.py
```

The launcher uses the standard library, stages the original sibling-folder layout in a temporary directory, and deletes that staging directory when done. It runs the audit, eight mechanism tests, evidence extraction and the experiments. It compares all archived CSV results, 210 representation facts and all substantive fields in the 276 traces; only wall-clock latency is excluded. It checks that tracked files remain unchanged. The archival reports' original local commands are historical; use this launcher from the repository.

Run the original benchmark tests separately in the benchmark environment (requires NumPy):

```bash
python -m unittest discover -v
```

The recorded original suite passed 22 tests. An initial attempt using system Python failed because NumPy was missing; the existing bundled environment then passed. Both the limitation and recovery are described in the report.

## Archive provenance

The two dated directories preserve the original local artifacts byte-for-byte, including code, protocols, hashes, run manifests and verification records. Statements in those reports that artifacts were outside the repository describe their **original creation**. They are now published under `research/`; the original graph, labels and `results/v1.0.0/` remain frozen.

The recorded 58-file integrity check and base commit refer to the repository before these additions. A fresh reproduction records the current checkout in its temporary manifest; historical manifests are not rewritten to pretend the new files existed during the original experiments. The launcher adapts the archive layout rather than changing the hash-recorded scripts.

`publication_manifest.json` records SHA-256 hashes of every imported dated artifact. `audit_evidence.json` includes complete candidate paths and exact Source IDs; `representation_facts.jsonl` distinguishes original text spans from metadata field paths. The relationship examples are curated specification evidence, not a claim that all relations have been automatically extracted.
