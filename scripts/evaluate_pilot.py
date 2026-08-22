#!/usr/bin/env python3
"""Recompute Source-level retrieval metrics for the completed 30-source pilot."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def split_ids(value: str) -> set[str]:
    return {item.strip() for item in value.split("|") if item.strip()}


def is_true(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes"}


def load_questions(path: Path) -> dict[str, dict[str, object]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        return {
            row["Query ID"]: {
                "gold": split_ids(row["Gold Source IDs"]),
                "answerable": is_true(row["Answerable in Subset"]),
                "type": row["Type"],
            }
            for row in rows
        }


def load_predictions(path: Path) -> tuple[list[str], dict[tuple[str, str], list[str]], list[str]]:
    method_order: list[str] = []
    predictions: dict[tuple[str, str], list[str]] = defaultdict(list)
    label_mismatches: list[str] = []

    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            method = row["Method"]
            query_id = row["Query ID"]
            if method not in method_order:
                method_order.append(method)
            predictions[(method, query_id)].append(row["Source ID"])

    return method_order, predictions, label_mismatches


def evaluate(
    questions: dict[str, dict[str, object]],
    methods: list[str],
    predictions: dict[tuple[str, str], list[str]],
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    unanswerable = [qid for qid, q in questions.items() if not q["answerable"]]

    for method in methods:
        tp = fp = fn = 0
        abstained_all = 0
        correct_negative_abstentions = 0
        duplicate_predictions: list[str] = []

        for query_id, question in questions.items():
            ranked = predictions.get((method, query_id), [])
            if len(ranked) != len(set(ranked)):
                duplicate_predictions.append(query_id)
            predicted = set(ranked)
            gold = question["gold"]

            tp += len(predicted & gold)
            fp += len(predicted - gold)
            fn += len(gold - predicted)

            if not predicted:
                abstained_all += 1
                if not question["answerable"]:
                    correct_negative_abstentions += 1

        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        results.append(
            {
                "method": method,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "overall_abstention_rate": abstained_all / len(questions),
                "negative_abstention_rate": (
                    correct_negative_abstentions / len(unanswerable) if unanswerable else 0.0
                ),
                "duplicate_prediction_queries": duplicate_predictions,
            }
        )

    return results


def render_markdown(results: list[dict[str, object]]) -> str:
    lines = [
        "| Method | TP | FP | FN | Precision | Recall | F1 | Negative abstention |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        lines.append(
            "| {method} | {tp} | {fp} | {fn} | {precision:.1%} | {recall:.1%} | "
            "{f1:.1%} | {negative_abstention_rate:.1%} |".format(**result)
        )
    return "\n".join(lines)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--questions",
        type=Path,
        default=repo_root / "data/csv/pilot_questions.csv",
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        default=repo_root / "data/csv/pilot_predictions.csv",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    args = parser.parse_args()

    questions = load_questions(args.questions)
    methods, predictions, _ = load_predictions(args.predictions)
    results = evaluate(questions, methods, predictions)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(render_markdown(results))


if __name__ == "__main__":
    main()
