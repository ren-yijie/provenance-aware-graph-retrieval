# Validation notes

## Public-release QA correction

An earlier presentation draft described all three pilot methods as recovering all 30 relevant-source labels. Recalculation from the included gold labels and ranked predictions shows that Keyword-IDF@3 misses one gold source on Q24:

- Keyword-IDF@3: 29 TP, 61 FP, 1 FN, 96.7% recall;
- TF-IDF Vector@3: 30 TP, 60 FP, 0 FN, 100% recall;
- Graph Entity@3: 30 TP, 28 FP, 0 FN, 100% recall.

The README and public results use the recomputed figures. This note preserves the audit trail instead of silently carrying forward the draft slide claim.

## Maturity labels

| Evidence | Status | Permitted claim |
|---|---|---|
| 30-source pilot predictions | Completed and recomputed | Compare Source-level retrieval metrics within this synthetic benchmark |
| 50-source graph slice | Frozen and structurally audited | Describe graph composition and observed structural risks |
| 50-source method outputs | `NOT_RUN` | Describe the evaluation design only; do not rank methods |
| Confidence-weighted edges | Proposed | Describe architecture and future threshold testing only |
| Generated answers | Not evaluated | Do not claim answer faithfulness or hallucination reduction at the generation layer |

## Known limitations

- The personal-relationship network is a demonstration sample, not the sole purpose of the platform or framework.
- Synthetic data reduces privacy risk but does not establish performance on real organizational data.
- Gold labels are human-authored and may reflect labeling judgment.
- The pilot uses transparent lexical and graph baselines, not a full production RAG stack.
- A language model's inherent knowledge can influence future generated answers even when retrieval is controlled.
- The current work does not validate production security, dynamic graph updates, calibration, or generalization.
