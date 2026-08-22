# Results and current status

## Completed 30-source pilot

The included pilot compares three transparent retrieval methods on the same synthetic sources, questions, gold labels, and Top-3 cutoff. Values below are recomputed by `scripts/evaluate_pilot.py` from `pilot_questions.csv` and `pilot_predictions.csv`.

| Method | TP | FP | FN | Precision | Recall | F1 | Negative abstention |
|---|---:|---:|---:|---:|---:|---:|---:|
| Keyword-IDF@3 | 29 | 61 | 1 | 32.2% | 96.7% | 48.3% | 0.0% |
| TF-IDF Vector@3 | 30 | 60 | 0 | 33.3% | 100.0% | 50.0% | 0.0% |
| Graph Entity@3 | 30 | 28 | 0 | 51.7% | 100.0% | 68.2% | 40.0% |

Within this frozen pilot, graph entity retrieval reduced false positives from 60–61 to 28 while preserving all 30 gold labels. It correctly abstained on two of five out-of-scope questions; the text baselines always returned results.

These are benchmark-specific retrieval results. They do not establish generated-answer quality, production readiness, privacy/security, or cross-domain generalization.

## Frozen 50-source benchmark

The final package is structurally audited and ready for a controlled run:

- 50 Source nodes;
- 118 total nodes and 116 directed edges;
- 30 frozen questions and 120 method-question rows;
- all answerable gold sets collectively cover all 50 Source IDs;
- all 120 current method outputs remain `NOT_RUN`.

No method winner is claimed for the 50-source benchmark.

## Structural findings

- No duplicate node IDs, duplicate edge IDs, dangling endpoints, self-loops, duplicate edge triples, or isolated nodes were found.
- The graph has five weakly connected components; the largest contains 75 nodes.
- Exact-name resolution exposes six pairwise false-positive merge cases across four duplicate-name groups.
- The generic `Managing Director` concept receives 25 of 47 `IS_CONCEPT` edges (53.2%), making it a high-degree semantic hub that can introduce broad, weakly specific paths.
- None of the 116 graph edges contains an implemented confidence field.

Run `python3 scripts/audit_graph.py` to reproduce these checks.
