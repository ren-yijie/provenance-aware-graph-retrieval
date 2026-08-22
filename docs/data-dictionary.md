# Data dictionary

All donor profiles in this public portfolio are synthetic. Names and biographies are test fixtures, not real donor records. Phone and email fields are excluded.

## Frozen graph

`data/test_graph_slice.json` follows a node-link structure:

| Object | Key fields | Purpose |
|---|---|---|
| Source node | `id`, `name`, `attributes.content`, `attributes.metadata` | Synthetic source profile and stable provenance anchor |
| Discovered entity | `id`, `name`, `attributes.context`, `attributes.tags` | Entity extracted from one or more profiles |
| Concept | `id`, `name`, `attributes.embedding` | Semantic grouping used by the supplied graph |
| Centroid | `id`, `name`, `attributes.members` | Higher-level concept cluster |
| Edge | `id`, `type`, `source`, `target`, `attributes` | Directed `MENTIONS`, `IS_CONCEPT`, or `BELONGS_TO` relationship |

Frozen SHA-256: `bd6c8802a864b4599c064d34c01a5d8b460cb4f040bd8339f745bef8dcf61ad5`.

## Final evaluation CSVs

| File | Description |
|---|---|
| `source_index.csv` | 50 frozen synthetic profiles and collision flags |
| `question_gold.csv` | 30 questions, gold Source IDs, evidence notes, and answerability |
| `method_outputs.csv` | Four methods × 30 questions; all rows remain `NOT_RUN` |
| `metrics_summary.csv` | Formula-output area, intentionally blank until validated runs exist |
| `entity_collisions.csv` | Known duplicate-name collision cases and review labels |

## Pilot CSVs

| File | Description |
|---|---|
| `pilot_sources.csv` | 30 synthetic source profiles |
| `pilot_questions.csv` | 30 frozen pilot questions and gold labels |
| `pilot_predictions.csv` | Ranked outputs from three completed transparent baselines |
| `pilot_query_metrics.csv` | Per-method, per-question metric breakdown |
| `pilot_metrics.csv` | Workbook summary values |
| `pilot_relation_labels.csv` | Reviewed relationship labels used in the pilot |
| `pilot_data_quality.csv` | Sampling and data-quality checks |

The original 367 MB graph is intentionally excluded. The public portfolio contains only the frozen, reviewable slice used by the final evaluation design.
