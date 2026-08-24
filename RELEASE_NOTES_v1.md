# Release notes: Package B benchmark v1

## Release scope

This release packages a small, inspectable synthetic benchmark for evidence-first retrieval. It contains 50 synthetic Source profiles, 118 graph nodes, 116 directed edges, 30 fixed questions, and a shared Top-3 Source-ID evaluation contract.

The earlier 30-profile developmental pilot remains preserved as historical project evidence. Its stored predictions, data, and implementations differ from this release and are not current benchmark outputs.

## Frozen Package B implementation

The [algorithm preregistration](docs/algorithm_preregistration_v1.md) froze four local methods before the 120 current outputs were generated:

- Okapi BM25 lexical retrieval;
- dense MiniLM retrieval, representing only the retrieval stage of Vector RAG;
- deterministic unweighted graph traversal;
- deterministic provenance-aware graph retrieval with evidence, generic-concept, and identity-collision checks.

Dataset, questions, gold labels, algorithms, thresholds, and Top-3 cutoff are frozen for v1. The benchmark is preregistered exploratory portfolio work, not a confirmatory study.

## Successful execution

All four methods completed all 30 questions: 120/120 rows have status `COMPLETE`. The 22-test suite passed.

| Method | TP | FP | FN | Precision | Recall | F1 | Correct abstentions |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 | 49 | 26 | 9 | 65.3% | 84.5% | 73.7% | 0/5 |
| MiniLM vector | 39 | 36 | 19 | 52.0% | 67.2% | 58.6% | 0/5 |
| Unweighted graph | 19 | 21 | 39 | 47.5% | 32.8% | 38.8% | 5/5 |
| Provenance-aware graph | 17 | 13 | 41 | 56.7% | 29.3% | 38.6% | 5/5 |

BM25 had the highest F1 on this small, entity-heavy synthetic benchmark. Provenance filtering reduced graph false positives and improved precision, but reduced true positives and recall; it did not improve F1 over the unweighted graph baseline. Both graph methods correctly abstained on all five empty-gold questions, while the text methods did not.

## Limitations

- All profiles are synthetic, and results may not generalize to real organizational graphs.
- Thirty questions and five abstention cases are insufficient for broad scientific claims.
- The benchmark evaluates retrieval, not generated-answer quality.
- Local latency is not a production scalability measurement.
- API cost was `$0.00`; local compute cost was not monetized.
- The historical `1616fb0…7876` checksum is absent; executable v1 uses the documented raw and canonical fingerprints in the integrity report.

## Deferred v2 work

These ideas are intentionally not incorporated into v1:

- hybrid BM25 candidate generation plus provenance reranking;
- separate development data for abstention calibration;
- prefix- and alias-aware entity seeding;
- versioned threshold sensitivity analysis;
- larger or authorized non-synthetic evaluation data;
- generated-answer grounding evaluation.

The frozen v1 outputs and full evidence are in `results/v1.0.0/`.
