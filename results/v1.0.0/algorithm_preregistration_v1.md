# Algorithm preregistration: exploratory portfolio benchmark v1

Status: frozen before generation of any current 50-profile benchmark output.

This is a preregistered exploratory portfolio benchmark, not a confirmatory study. The synthetic dataset and gold labels predate this algorithm specification. The algorithms, thresholds, corpus construction, ranking rules, and metric conventions below must not be changed after results are viewed. A correctness defect may be repaired only with a documented test and rerun record.

## Canonical benchmark

- Synthetic Source profiles: 50
- Nodes: 118
- Directed edges: 116
- Questions: 30 (25 answerable, 5 abstention)
- Gold Source-ID assignments: 58
- Retrieval cutoff: Top-3
- Raw graph SHA-256: `bd6c8802a864b4599c064d34c01a5d8b460cb4f040bd8339f745bef8dcf61ad5`
- Canonical JSON SHA-256: `cfa22f31d1d0186f6f54119c5be0597f88b94c6fa4a1db8c39cef4c975c7f498`

Canonical JSON uses UTF-8, recursively sorted object keys, compact comma/colon separators, `ensure_ascii=false`, original array ordering, and no trailing newline. The historical workbook value `1616fb0f1e4499a6512aab756dd45f6a77526f1087cf735549cce2c434427876` is a documentation discrepancy and is not recreated.

## Shared corpus and normalization

Each Source has one `retrieval_text`: the existing `attributes.content` string from its frozen graph node. No metadata fields are appended because the content already contains the substantive human-readable profile evidence. Source IDs, donor IDs, gold labels, expected answers, questions, stored predictions, graph-derived features, and evaluation outputs are excluded.

Text normalization is Unicode NFKC, lowercase, whitespace collapsed to one ASCII space. Tokens are maximal Unicode alphanumeric sequences (underscore excluded). Lexical matching removes the following frozen English stop-word set:

`a, about, above, after, again, against, all, am, an, and, any, are, as, at, be, because, been, before, being, below, between, both, but, by, can, did, do, does, doing, down, during, each, few, for, from, further, had, has, have, having, he, her, here, hers, herself, him, himself, his, how, i, if, in, into, is, it, its, itself, just, me, more, most, my, myself, no, nor, not, now, of, off, on, once, only, or, other, our, ours, ourselves, out, over, own, same, she, should, so, some, such, than, that, the, their, theirs, them, themselves, then, there, these, they, this, those, through, to, too, under, until, up, very, was, we, were, what, when, where, which, while, who, whom, why, will, with, you, your, yours, yourself, yourselves`.

No stemming, lemmatization, synonym expansion, query-specific stop words, or parameter tuning is used. BM25 and vector retrieval use exactly the same unnormalized `retrieval_text`; their own fixed normalization/encoder is then applied.

## Shared result contract

Every retrieval call returns query ID, method name and implementation ID, ranked Source IDs (maximum three), scores, abstention flag, measured wall-clock latency in milliseconds, API cost `$0.00`, run status, method configuration, and method-specific trace metadata. `method_answer` is `NOT_APPLICABLE` because this benchmark evaluates Source retrieval, not generated prose.

Retrievers are constructed without a gold-label path or gold-label object. Gold data is loaded only by the evaluation layer after retrieval.

## Method 1: BM25 Keyword Search

Implementation ID: `bm25_v1`.

Standard Okapi BM25 ranks all Source retrieval texts using `k1=1.5`, `b=0.75`, natural logarithm IDF `ln(1 + (N-df+0.5)/(df+0.5))`, and the frozen lexical tokens above. Ranking is score descending then Source ID ascending. Return Top-3. Abstain only when the highest score is exactly zero.

## Method 2: Local Vector RAG

Implementation ID: `minilm_vector_v1`.

Model: `sentence-transformers/all-MiniLM-L6-v2`. The installed `sentence-transformers` version and resolved Hugging Face snapshot revision are recorded. The model encodes the shared Source text and questions locally. Embeddings are converted to float32 and explicitly L2-normalized. Similarity is their dot product (cosine similarity). Rank similarity descending then Source ID ascending. Abstain when the highest similarity is below `0.30`; otherwise return Top-3.

Source embeddings are cached under `.cache/retrieval_embeddings/v1/<canonical-fingerprint>/<model-revision>/`. Cache metadata contains the full fingerprint, model ID, resolved revision, Source-ID order, normalization flag, array shape, and dtype. A cache is reused only on an exact metadata match. The undocumented 768-dimensional Concept embeddings are never used.

## Shared graph seeding

Only `Discovered_entity` and `Concept` nodes can seed traversal. Seed aliases are the node's `name`; for `Discovered_entity`, each existing string in `attributes.tags` is also an alias. Free-form `context` is evidence, not an alias. Aliases use shared normalization and stop-word removal.

For each alias, the best seed class is:

1. exact normalized phrase: the normalized alias occurs as a contiguous, token-bounded phrase in the normalized query;
2. complete normalized token match: every non-stop alias token occurs in the query tokens;
3. partial multi-token overlap: the alias has at least two non-stop tokens, at least two overlap, and overlap is at least half the alias tokens.

Single-token aliases qualify only through exact phrase/complete-token matching. One node is one seed, retaining its highest class and lexicographically smallest matching alias. Gold labels are unavailable.

## Method 3: Unweighted Graph Retrieval

Implementation ID: `unweighted_graph_v1`.

The frozen directed edges are traversed as an undirected adjacency for discovery because Source-to-entity `MENTIONS` edges point away from Source nodes; each recorded path retains the stored edge ID, type, source, target, and whether traversal followed or opposed stored direction. All simple paths of one or two existing edges from each seed to a Source are enumerated. No inferred edge is created, and every edge has equal cost.

Candidate rank is lexicographic:

1. count of distinct exact-phrase seed nodes reaching the Source, descending;
2. shortest qualifying path length, ascending;
3. count of distinct qualifying `(seed, edge-path)` paths, descending;
4. Source ID ascending.

The displayed retrieval score is the rank tuple serialized as metadata, not a weighted scalar. The numeric `score` field is the exact-phrase seed count for interoperability. Abstain only when no Source is reachable. Return Top-3.

## Method 4: Provenance-Aware Graph Retrieval

Implementation ID: `provenance_graph_v1`.

Start with exactly the graph seeds, candidates, and paths from `unweighted_graph_v1`. No confidence field or learned weight is added.

### Direct evidence

Evidence is accepted only from the candidate Source's frozen `attributes.content` field:

- a matched seed alias appearing as a contiguous normalized phrase;
- a query-relevant Discovered_entity name on the stored path appearing as a contiguous normalized phrase; or
- an existing `IS_CONCEPT.attributes.original_trigger` on the stored path that both overlaps the query under the seed rules and appears as a contiguous normalized phrase.

Evidence spans store the evidence kind, matched normalized text, and character offsets into normalized Source content. Distinct evidence matches are distinct `(kind, normalized text)` pairs. A candidate requires at least one direct evidence match and a valid stored path.

`direct_named_entity=true` only when a query-relevant Discovered_entity name is directly present in Source content. Graph membership alone is false.

### Generic concepts

Concept support is the number of distinct Source nodes reachable through existing `Concept—IS_CONCEPT—Discovered_entity—MENTIONS—Source` paths. A Concept supporting at least 10 Sources (20% of 50) is generic. Generic Concept evidence alone is insufficient. Eligibility then requires either direct named-entity evidence or a directly supported non-generic matched seed in the same Source. The run records all generic Concept IDs, names, and support counts.

### Identity collisions

A collision Entity is derived without gold labels: its normalized name exactly equals the normalized profile name in at least two directly connected Source nodes whose frozen donor IDs differ. Entity membership alone is insufficient.

For a collision-seeded candidate, the entity name must appear directly in Source content and an additional constraint must be evidenced. Additional constraint is either (a) a non-identity query token appearing in Source content, or (b) when the query requests employer, role, profession, or occupation, the Source's first sentence contains the collision name plus one of these frozen professional cues: `associate, banker, cardiologist, consultant, director, entrepreneur, founder, investment, lawyer, managing, officer, partner, physician, professor, retired, works, designer`. This rule validates distinguishing profile text without using expected employers or roles. Otherwise the collision path is excluded with reason `unsupported_identity_collision`.

### Eligibility and ranking

Candidates supported solely by generic concepts, shared metadata, entity membership, or unrelated paths are excluded. Eligible candidates rank lexicographically by:

1. direct named-entity evidence (`true` first);
2. number of distinct direct evidence matches, descending;
3. number of distinct directly supported non-generic matched seeds, descending;
4. shortest valid evidence-bearing path, ascending;
5. preregistered `bm25_v1` query-to-Source score, descending;
6. Source ID ascending.

The numeric `score` field is the number of distinct direct evidence matches; the complete lexicographic tuple is preserved in trace metadata. Abstain when no candidate remains. Return Top-3. Included and excluded candidate traces record query term, seed, paths, edge types, evidence spans, generic decisions, collision decisions, and reasons.

## Metrics

For answerable questions: TP is retrieved intersect gold, FP is retrieved minus gold, FN is gold minus retrieved; precision, recall, and F1 use standard formulas, and abstention is incorrect.

For empty-gold questions, abstention correctness is primary. Correct abstention records TP=FP=FN=0 and precision/recall/F1 `NOT_APPLICABLE`. Retrieval records every returned Source as FP, with precision `0.0`; recall and F1 are `NOT_APPLICABLE` because there are no relevant items. `NOT_APPLICABLE` is excluded from macro retrieval averages. Micro retrieval precision/recall/F1 are computed over answerable questions only. Abstention accuracy is reported separately over all 30 questions and over the five empty-gold questions.

Latency is observed wall-clock retrieval time via `time.perf_counter_ns`, excluding one-time model download and Source-embedding cache construction. Vector query encoding is included. All API costs are exactly `$0.00` because execution is local and uses no paid API.

## Execution protocol

1. Save and hash this document.
2. Confirm the original matrix still contains 120 `NOT_RUN` rows.
3. Run all tests under Python 3.10+.
4. Resolve and cache the named model.
5. Execute one complete 4×30 run without changing rules.
6. Preserve per-query outputs, traces, environment, versions, timestamps, metrics, and error analysis in a new results directory.

No benchmark result had been generated when this file was frozen.
