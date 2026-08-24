#!/usr/bin/env python3
"""Execute the preregistered exploratory 50-profile synthetic benchmark."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from retrieval_benchmark.runner import default_output_dir, execute, write_reports


def main() -> None:
    root = ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=root / ".cache" / "retrieval_embeddings")
    args = parser.parse_args()
    output_dir = args.output_dir or default_output_dir(root)
    rows, aggregates, manifest = execute(root, output_dir, args.cache_dir)
    write_reports(root, output_dir, rows, aggregates, manifest)
    print(output_dir)
    for aggregate in aggregates:
        print(
            aggregate["implementation_id"],
            f"rows={aggregate['completed_rows']}",
            f"TP={aggregate['tp']}",
            f"FP={aggregate['fp']}",
            f"FN={aggregate['fn']}",
            f"F1={aggregate['micro_f1_answerable']:.6f}",
            f"negative_abstentions={aggregate['correct_negative_abstentions']}/5",
        )


if __name__ == "__main__":
    main()
