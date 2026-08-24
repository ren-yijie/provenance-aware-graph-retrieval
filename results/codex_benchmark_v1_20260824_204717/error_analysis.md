# Error analysis

## Scope

This analysis covers the newly executed 50-profile synthetic benchmark. It does not reuse or relabel the earlier pilot.

## Generic concepts

- `CONCEPT_4a3570986e7548ef9dccd7042bbecaa0` — Managing Director: 30 supported Sources; classified generic.

Provenance exclusion counts:

- `no_valid_evidence_path`: 35

## Same-name identity collisions

- Q001: retrieved `SRC_0441dc10f8e34937bdcfda1a68b4d7c2|SRC_7ec60d6b0cec447fa0ee0dbbf6fb386f|SRC_68ed2f97e7a248d694f231d451831c04`; TP=3, FP=0, FN=0.
- Q002: retrieved `SRC_41567911c8b045bd8dd0e55e8e69a06b|SRC_b159124a50e14ab3b5f92aabb61fdf89`; TP=2, FP=0, FN=0.
- Q003: retrieved `SRC_e724d27deb20445695164b8765b80b63|SRC_7d71e393a7e045b99266d9b05b499cb3`; TP=2, FP=0, FN=0.
- Q004: retrieved `SRC_fe56228c8f38461b96964e6e5303294b|SRC_9f81162e8a1f428a9ea29c0188dca111`; TP=2, FP=0, FN=0.
- Q005: retrieved `ABSTAIN`; TP=0, FP=0, FN=2.

## Representative missed relevant Sources

- `bm25_v1` Q006: `SRC_06bb790e8ccb4aa288baa0a74279a9cd`
- `bm25_v1` Q007: `SRC_a708b816d69f4c9b94fae6fb6e9c8c5d|SRC_b4afb6b3a6dc49408f204f940ec09a27`
- `bm25_v1` Q009: `SRC_b0b29907d30d405bbd3fdc6c785fec65|SRC_f5c42c43daaf4f36ad61277877289e94`
- `bm25_v1` Q013: `SRC_f5c42c43daaf4f36ad61277877289e94`
- `bm25_v1` Q016: `SRC_3901afe8826243ab985f340222cb3199`
- `bm25_v1` Q017: `SRC_b940430c90694a15b8d27ebc539db542|SRC_fd700683d4cb4511aec4a0b3f4752e22`
- `minilm_vector_v1` Q006: `SRC_05424f4340bd4183b43e9b0526e2a595|SRC_06bb790e8ccb4aa288baa0a74279a9cd`
- `minilm_vector_v1` Q007: `SRC_a708b816d69f4c9b94fae6fb6e9c8c5d|SRC_b4afb6b3a6dc49408f204f940ec09a27|SRC_cbf9e213476b4447a62ec10998109cd0`
- `minilm_vector_v1` Q008: `SRC_05c73e6a1a964f5bac6d06fdd4468454`
- `minilm_vector_v1` Q009: `SRC_b0b29907d30d405bbd3fdc6c785fec65|SRC_f5c42c43daaf4f36ad61277877289e94`
- `minilm_vector_v1` Q014: `SRC_2f3c6a1b3c25481a8a6ee604ec4ef9b5|SRC_b4afb6b3a6dc49408f204f940ec09a27`
- `minilm_vector_v1` Q015: `SRC_059c3e0c07014a2b9d9d79006bae40b6|SRC_1e85ef4a27624583b2bbed5203988083|SRC_e7fc70d2108f48148e5f9706036c0d54`
- `minilm_vector_v1` Q016: `SRC_f3170dc618be459aa194ccad5623ba6c`
- `minilm_vector_v1` Q017: `SRC_b940430c90694a15b8d27ebc539db542`
- `minilm_vector_v1` Q019: `SRC_c3f817b46752487499f5cbc776601946`
- `minilm_vector_v1` Q020: `SRC_6e88f96639d441a5a3cbbdce2ae2ccab|SRC_ed547720efc542e09abb139fcb3e0d12`
- `minilm_vector_v1` Q025: `SRC_85008339e41847d38d3bbcbcdaa743d9`
- `unweighted_graph_v1` Q005: `SRC_06bb790e8ccb4aa288baa0a74279a9cd|SRC_07d47bea6aab444da70c50c215cf1e4e`
- `unweighted_graph_v1` Q006: `SRC_05424f4340bd4183b43e9b0526e2a595|SRC_06bb790e8ccb4aa288baa0a74279a9cd|SRC_67fcc1ef6eaa4d7faf93e8b31f914bab`
- `unweighted_graph_v1` Q007: `SRC_b4afb6b3a6dc49408f204f940ec09a27|SRC_cbf9e213476b4447a62ec10998109cd0`

## Representative irrelevant retrieved Sources

- `bm25_v1` Q002: `SRC_ed547720efc542e09abb139fcb3e0d12`
- `bm25_v1` Q003: `SRC_3ac471dea79b40518de8e10ff9121d44`
- `bm25_v1` Q004: `SRC_ca382c534abf423ba1926acd4f02191e`
- `bm25_v1` Q005: `SRC_8170175835fa4ff2bce4dae447fb7688`
- `bm25_v1` Q006: `SRC_41567911c8b045bd8dd0e55e8e69a06b`
- `bm25_v1` Q007: `SRC_41567911c8b045bd8dd0e55e8e69a06b|SRC_e7fc70d2108f48148e5f9706036c0d54`
- `bm25_v1` Q009: `SRC_e724d27deb20445695164b8765b80b63|SRC_e7fc70d2108f48148e5f9706036c0d54`
- `bm25_v1` Q010: `SRC_cbf9e213476b4447a62ec10998109cd0`
- `bm25_v1` Q011: `SRC_c3f817b46752487499f5cbc776601946`
- `bm25_v1` Q013: `SRC_b940430c90694a15b8d27ebc539db542`
- `bm25_v1` Q016: `SRC_d94ae1c2c8e241cd9e0209b0859a15f6`
- `bm25_v1` Q017: `SRC_8170175835fa4ff2bce4dae447fb7688|SRC_e7fc70d2108f48148e5f9706036c0d54`
- `bm25_v1` Q018: `SRC_8170175835fa4ff2bce4dae447fb7688`
- `bm25_v1` Q019: `SRC_06bb790e8ccb4aa288baa0a74279a9cd`
- `bm25_v1` Q020: `SRC_0441dc10f8e34937bdcfda1a68b4d7c2`
- `bm25_v1` Q021: `SRC_4912b2840ea44851adfd0c9e12aedafa|SRC_7d71e393a7e045b99266d9b05b499cb3`
- `bm25_v1` Q022: `SRC_3ac471dea79b40518de8e10ff9121d44|SRC_ed547720efc542e09abb139fcb3e0d12`
- `bm25_v1` Q023: `SRC_19d8b205b26b4f32a7345cfbff2497b3|SRC_7ec60d6b0cec447fa0ee0dbbf6fb386f`
- `bm25_v1` Q024: `SRC_2b70735578ff431ca60183fe32cb12a8|SRC_a21d8945b3304f7bba67ff8e4e9ba0ba`
- `bm25_v1` Q026: `SRC_05424f4340bd4183b43e9b0526e2a595|SRC_67fcc1ef6eaa4d7faf93e8b31f914bab|SRC_a708b816d69f4c9b94fae6fb6e9c8c5d`

## Answer/provenance limitations

Generated answers were `NOT_APPLICABLE`; unsupported-answer analysis therefore remains `NOT_EVALUATED`. Graph path and evidence details for every retrieved Source are in `provenance_traces.jsonl`.
