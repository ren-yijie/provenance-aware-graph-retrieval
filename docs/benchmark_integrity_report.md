# Benchmark integrity report

The current public 50-profile synthetic benchmark package passed structural and gold-label alignment validation before retrieval implementation or execution.

## Frozen package

| Property | Validated value |
|---|---:|
| Source profiles | 50 |
| Total nodes | 118 |
| Directed edges | 116 |
| Questions | 30 |
| Answerable questions | 25 |
| Abstention questions | 5 |
| Gold Source-ID assignments | 58 |
| Unique gold Source IDs | 50 |
| Raw SHA-256 | `bd6c8802a864b4599c064d34c01a5d8b460cb4f040bd8339f745bef8dcf61ad5` |
| Canonical JSON SHA-256 | `cfa22f31d1d0186f6f54119c5be0597f88b94c6fa4a1db8c39cef4c975c7f498` |

Canonicalization is UTF-8 JSON with recursively sorted object keys, compact comma/colon separators, `ensure_ascii=false`, original array ordering, and no trailing newline.

## Checksum discrepancy

The older `1616fb0f1e4499a6512aab756dd45f6a77526f1087cf735549cce2c434427876` remains embedded in the final evaluation workbook's README sheet. It is not the hash of the current JSON. The current JSON, Markdown data dictionary, and graph audit agree on `bd6c…1ad5`; no frozen data was changed to reproduce the historical value.

## Alignment and structural checks

- Every expected Source ID exists in both the graph and Source index.
- Every expected Source maps to its expected donor ID.
- Every answerable question has one to three valid expected Source IDs.
- All five abstention questions have empty Source/donor gold sets and expected count zero.
- All 58 expected source–question assignments have direct supporting profile text.
- Answerable gold sets collectively cover all 50 Source IDs.
- No duplicate node, Source, or edge IDs; no broken endpoints, self-loops, duplicate edge triples, or isolated nodes.
- Node and edge schemas are internally consistent by type.
- The original matrix has 30 rows per intended method and remains preserved with all 120 template rows `NOT_RUN`.

The package is internally aligned for an exploratory synthetic benchmark. This does not establish that the human-authored gold sets are exhaustive or that results generalize beyond the fixture.
