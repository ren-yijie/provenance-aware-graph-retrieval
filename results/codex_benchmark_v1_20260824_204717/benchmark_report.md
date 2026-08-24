# Exploratory synthetic benchmark v1 report

## Status

All 120 method–question rows completed under the preregistered Top-3 contract. The data is synthetic and the study is exploratory, not confirmatory.

## Aggregate results

| Method | TP | FP | FN | Precision | Recall | F1 | Correct negative abstentions | Mean latency (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bm25_v1 | 49 | 26 | 9 | 0.653 | 0.845 | 0.737 | 0/5 | 0.739 |
| minilm_vector_v1 | 39 | 36 | 19 | 0.520 | 0.672 | 0.586 | 0/5 | 8.326 |
| unweighted_graph_v1 | 19 | 21 | 39 | 0.475 | 0.328 | 0.388 | 5/5 | 7.326 |
| provenance_graph_v1 | 17 | 13 | 41 | 0.567 | 0.293 | 0.386 | 5/5 | 8.575 |

Metrics are micro-averaged over the 25 answerable questions. Empty-gold questions are excluded from retrieval averages and evaluated primarily through abstention correctness.

## Earlier pilot comparison boundary

The earlier 30-profile pilot used different profiles, questions, implementations, and stored predictions. Its results are developmental and are not pooled with or treated as a baseline for this 50-profile run.

## Interpretation

The preregistered criterion for describing provenance-aware retrieval as better was not met. Results are reported neutrally.

## Limitations

This is a small synthetic fixture. The graph contains sparse extracted entities, a high-degree role concept, no calibrated edge confidence, and no production identity-resolution system. Results may not generalize to naturally occurring organizational graphs. Full GraphRAG, LLM answer generation, production security, and real-world user behavior were not evaluated.

## Implementation deviations and execution fixes

There were no deviations from the preregistered corpus, algorithms, thresholds, ranking rules, or metrics. Two environment/launcher defects were fixed before the successful run: Hugging Face's cache was redirected from an unwritable home path to the ignored repository-local `.cache/` directory, and the direct runner added the repository root to `sys.path`. The launcher fix has a regression test. Neither failed attempt created a benchmark result directory or row.

## Reproduction

```bash
python3.12 -m venv .venv-benchmark
.venv-benchmark/bin/python -m pip install -r requirements-benchmark.txt
HF_HOME=$PWD/.cache/huggingface .venv-benchmark/bin/python -W error::ResourceWarning -m unittest discover -v
HF_HOME=$PWD/.cache/huggingface .venv-benchmark/bin/python scripts/run_benchmark.py
```
