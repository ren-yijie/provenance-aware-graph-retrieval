#!/usr/bin/env python3
"""Run the core public-portfolio reproducibility checks."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from audit_graph import audit
from evaluate_pilot import evaluate, load_predictions, load_questions


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    csv_dir = root / "data/csv"
    failures: list[str] = []

    graph_result = audit(root / "data/test_graph_slice.json")
    expected_graph = {
        "sha256_matches_frozen_record": True,
        "node_count": 118,
        "edge_count": 116,
        "duplicate_node_ids": 0,
        "duplicate_edge_ids": 0,
        "self_loops": 0,
        "duplicate_edge_triples": 0,
        "isolated_nodes": 0,
        "edges_with_confidence": 0,
    }
    for key, expected in expected_graph.items():
        if graph_result[key] != expected:
            failures.append(f"graph {key}: expected {expected!r}, got {graph_result[key]!r}")

    questions = load_questions(csv_dir / "pilot_questions.csv")
    methods, predictions, _ = load_predictions(csv_dir / "pilot_predictions.csv")
    metrics = {result["method"]: result for result in evaluate(questions, methods, predictions)}
    expected_metrics = {
        "Keyword-IDF@3": (29, 61, 1),
        "TF-IDF Vector@3": (30, 60, 0),
        "Graph Entity@3": (30, 28, 0),
    }
    for method, expected in expected_metrics.items():
        actual = tuple(metrics[method][key] for key in ("tp", "fp", "fn"))
        if actual != expected:
            failures.append(f"{method}: expected TP/FP/FN {expected}, got {actual}")

    with (csv_dir / "method_outputs.csv").open(newline="", encoding="utf-8-sig") as handle:
        raw_rows = list(csv.reader(handle))
    header_index = next(
        index for index, row in enumerate(raw_rows) if row and row[0] == "Result_Row_ID"
    )
    header = raw_rows[header_index]
    rows = [dict(zip(header, row)) for row in raw_rows[header_index + 1 :] if row and row[0]]
    if len(rows) != 120:
        failures.append(f"50-source method rows: expected 120, got {len(rows)}")
    statuses = {row["Run_Status"] for row in rows}
    if statuses != {"NOT_RUN"}:
        failures.append(f"50-source statuses: expected only NOT_RUN, got {sorted(statuses)}")

    if failures:
        print("Release verification failed:")
        for failure in failures:
            print(f"- {failure}")
        sys.exit(1)

    print("Release verification passed.")
    print("- Frozen graph hash and structural counts match.")
    print("- Pilot metrics recompute from predictions and gold labels.")
    print("- All 120 final benchmark outputs remain explicitly NOT_RUN.")


if __name__ == "__main__":
    main()
