# Command log

## Environment and preregistration

- Isolated runtime: Python 3.12.13 in a temporary environment outside the repository.
- Installed `sentence-transformers==6.0.0` and its local dependencies; no paid API was used.
- Frozen `docs/algorithm_preregistration_v1.md` SHA-256: `e63fff2345e947406ad0d8cbfa89abbb0a01c387660d179034077a83afa1ce7f`.
- Confirmed the original evaluation template contained 120 rows, all `NOT_RUN`, before execution.

## Tests

Command:

```bash
HF_HOME="$PWD/.cache/huggingface" python -W error::ResourceWarning -m unittest discover -v
```

Result: exit 0; 21 tests passed.

## Model resolution

The first model-load attempt failed before retrieval because the default user-level Hugging Face cache was not writable. The cache was redirected to the repository-local ignored `.cache/huggingface` directory without changing the model.

Resolved model:

- ID: `sentence-transformers/all-MiniLM-L6-v2`
- revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`
- embedding dimension: 384
- maximum sequence length: 256

## Benchmark execution

The first runner attempt failed before creating results with `ModuleNotFoundError: retrieval_benchmark`. The direct launcher path was fixed and regression-tested.

Successful command:

```bash
HF_HOME="$PWD/.cache/huggingface" python scripts/run_benchmark.py
```

Result: exit 0; 120 of 120 rows completed. The original workbook and CSV method template were not edited.

## Post-run validation

- Recomputed every row's TP/FP/FN from the frozen gold sets.
- Parsed all 120 trace records and confirmed every saved graph path ends at its reported valid Source ID, uses existing edge IDs, and is at most two edges.
- Confirmed all rows are `COMPLETE`, contain no more than three distinct Source IDs, and record API cost `$0.00`.
- `python3 scripts/verify_release.py` still passes and confirms the original 120-row template remains `NOT_RUN`.
- After pinning the exact model revision used by the completed run, the final regression suite passed 22/22 tests. The run manifest correctly records the 21 tests that existed at the pre-execution gate.
