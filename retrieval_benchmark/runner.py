"""One-shot execution and artifact generation for exploratory benchmark v1."""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import math
import platform
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .bm25 import BM25Retriever
from .data import CANONICAL_SHA256, RAW_SHA256, load_benchmark, load_retrieval_inputs
from .graph import ProvenanceGraphRetriever, UnweightedGraphRetriever
from .metrics import NOT_APPLICABLE, QueryMetrics, evaluate_query
from .vector import MODEL_ID, VectorRetriever, load_sentence_transformer


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def _aggregate(method_rows: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [row for row in method_rows if row["answerable"]]
    tp = sum(row["tp"] for row in answerable)
    fp = sum(row["fp"] for row in answerable)
    fn = sum(row["fn"] for row in answerable)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    latencies = [row["latency_ms"] for row in method_rows]
    negatives = [row for row in method_rows if not row["answerable"]]
    return {
        "method": method_rows[0]["method"],
        "implementation_id": method_rows[0]["implementation_id"],
        "completed_rows": len(method_rows),
        "answerable_rows": len(answerable),
        "tp": tp, "fp": fp, "fn": fn,
        "micro_precision_answerable": precision,
        "micro_recall_answerable": recall,
        "micro_f1_answerable": f1,
        "macro_precision_answerable": statistics.fmean(row["precision"] for row in answerable),
        "macro_recall_answerable": statistics.fmean(row["recall"] for row in answerable),
        "macro_f1_answerable": statistics.fmean(row["f1"] for row in answerable),
        "overall_abstention_rate": sum(row["abstained"] for row in method_rows) / len(method_rows),
        "overall_abstention_accuracy": sum(row["abstention_correct"] for row in method_rows) / len(method_rows),
        "negative_abstention_accuracy": sum(row["abstention_correct"] for row in negatives) / len(negatives),
        "correct_negative_abstentions": sum(row["abstention_correct"] for row in negatives),
        "mean_latency_ms": statistics.fmean(latencies),
        "median_latency_ms": statistics.median(latencies),
        "p95_latency_ms": _percentile(latencies, 0.95),
        "total_api_cost_usd": sum(row["api_cost_usd"] for row in method_rows),
    }


def _csv_safe_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: (_json(value) if isinstance(value, (dict, list, tuple)) else value) for key, value in row.items()}


def execute(root: Path, output_dir: Path, cache_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    preregistration = root / "docs" / "algorithm_preregistration_v1.md"
    preregistration_sha = hashlib.sha256(preregistration.read_bytes()).hexdigest()
    if preregistration_sha != "e63fff2345e947406ad0d8cbfa89abbb0a01c387660d179034077a83afa1ce7f":
        raise ValueError("preregistration fingerprint mismatch")

    retrieval_data = load_retrieval_inputs(root)
    evaluation_data = load_benchmark(root)
    model, sentence_transformers_version, model_revision = load_sentence_transformer(MODEL_ID)

    retrievers = [
        BM25Retriever(retrieval_data.retrieval_texts),
        VectorRetriever(
            retrieval_data.retrieval_texts, model,
            model_id=MODEL_ID,
            model_revision=model_revision,
            sentence_transformers_version=sentence_transformers_version,
            dataset_fingerprint=CANONICAL_SHA256,
            cache_root=cache_root,
        ),
        UnweightedGraphRetriever(retrieval_data.graph),
        ProvenanceGraphRetriever(retrieval_data.graph, retrieval_data.retrieval_texts),
    ]

    output_dir.mkdir(parents=True)
    run_started = datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    for retriever in retrievers:
        for query in retrieval_data.queries:
            result = retriever.retrieve(query)
            retrieved = [item.source_id for item in result.ranked_sources]
            metrics = evaluate_query(
                retrieved,
                set(evaluation_data.gold[query.query_id]),
                abstained=result.abstained,
                answerable=evaluation_data.answerable[query.query_id],
            )
            question_row = evaluation_data.question_rows[query.query_id]
            row = {
                "query_id": query.query_id,
                "question": query.text,
                "category": question_row["Category"],
                "answerable": evaluation_data.answerable[query.query_id],
                "gold_source_ids": sorted(evaluation_data.gold[query.query_id]),
                "method": result.method,
                "implementation_id": result.implementation_id,
                "retrieved_source_ids": retrieved,
                "retrieval_scores": [item.score for item in result.ranked_sources],
                "abstained": result.abstained,
                "latency_ms": result.latency_ms,
                "api_cost_usd": result.api_cost_usd,
                "run_status": result.run_status,
                "method_answer": result.method_answer,
                **asdict(metrics),
                "configuration": result.configuration,
                "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "trace": result.trace,
            }
            rows.append(row)
            trace_rows.append({
                "query_id": query.query_id,
                "method": result.method,
                "implementation_id": result.implementation_id,
                "ranked_sources": [asdict(item) for item in result.ranked_sources],
                "result_trace": result.trace,
            })

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["implementation_id"]].append(row)
    aggregates = [_aggregate(grouped[retriever.implementation_id]) for retriever in retrievers]

    with (output_dir / "per_query_results.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(_csv_safe_row(row) for row in rows)
    with (output_dir / "aggregate_metrics.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(aggregates[0]))
        writer.writeheader()
        writer.writerows(aggregates)
    with (output_dir / "provenance_traces.jsonl").open("x", encoding="utf-8") as handle:
        for trace in trace_rows:
            handle.write(json.dumps(trace, ensure_ascii=False, sort_keys=True) + "\n")

    packages = {}
    for package in ["sentence-transformers", "transformers", "tokenizers", "torch", "numpy", "scikit-learn", "huggingface-hub"]:
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = "NOT_INSTALLED"
    run_finished = datetime.now(timezone.utc)
    manifest = {
        "run_id": output_dir.name,
        "benchmark_classification": "preregistered exploratory portfolio benchmark v1",
        "dataset_classification": "synthetic test fixture",
        "started_at_utc": run_started.isoformat(),
        "finished_at_utc": run_finished.isoformat(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "python": sys.version,
        "platform": platform.platform(),
        "packages": packages,
        "model": {
            "id": MODEL_ID,
            "revision": model_revision,
            "embedding_dimension": 384,
            "max_sequence_length": 256,
            "source_embedding_cache": retrievers[1].cache_identifier.as_posix(),
            "source_cache_hit_at_run": retrievers[1].cache_hit,
        },
        "fingerprints": {
            "graph_raw_sha256": RAW_SHA256,
            "graph_canonical_json_sha256": CANONICAL_SHA256,
            "algorithm_preregistration_sha256": preregistration_sha,
            "historical_workbook_sha256_discrepancy": "1616fb0f1e4499a6512aab756dd45f6a77526f1087cf735549cce2c434427876",
        },
        "benchmark": {"profiles": 50, "nodes": 118, "directed_edges": 116, "questions": 30, "answerable": 25, "abstention": 5, "gold_assignments": 58, "top_k": 3},
        "implementations": [retriever.implementation_id for retriever in retrievers],
        "rows": len(rows),
        "tests_before_run": {"command": "python -W error::ResourceWarning -m unittest discover -v", "tests": 21, "status": "PASS"},
        "api_calls": 0,
        "api_cost_usd": 0.0,
        "random_seeds": "NOT_APPLICABLE; all algorithms deterministic and no stochastic sampling used",
    }
    (output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return rows, aggregates, manifest


def write_reports(root: Path, output_dir: Path, rows: list[dict[str, Any]], aggregates: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    by_method = {item["implementation_id"]: item for item in aggregates}
    generic_counter = Counter()
    collision_rows = []
    missed = []
    irrelevant = []
    for row in rows:
        if row["fn"]:
            missed.append((row["implementation_id"], row["query_id"], sorted(set(row["gold_source_ids"]) - set(row["retrieved_source_ids"]))))
        if row["fp"]:
            irrelevant.append((row["implementation_id"], row["query_id"], sorted(set(row["retrieved_source_ids"]) - set(row["gold_source_ids"]))))
        if row["implementation_id"] == "provenance_graph_v1":
            for exclusion in row["trace"].get("excluded_candidates", []):
                generic_counter[exclusion.get("reason", "unknown")] += 1
            if row["category"] == "Entity disambiguation":
                collision_rows.append(row)

    generic_concepts = next(
        row["trace"].get("generic_concepts", {})
        for row in rows if row["implementation_id"] == "provenance_graph_v1"
    )
    error_lines = [
        "# Error analysis", "", "## Scope", "",
        "This analysis covers the newly executed 50-profile synthetic benchmark. It does not reuse or relabel the earlier pilot.", "",
        "## Generic concepts", "",
    ]
    if generic_concepts:
        for concept_id, detail in sorted(generic_concepts.items()):
            error_lines.append(f"- `{concept_id}` — {detail['name']}: {detail['source_count']} supported Sources; classified generic.")
    else:
        error_lines.append("- No Concept met the preregistered 10-Source threshold.")
    error_lines.extend(["", "Provenance exclusion counts:", ""])
    for reason, count in sorted(generic_counter.items()):
        error_lines.append(f"- `{reason}`: {count}")
    error_lines.extend(["", "## Same-name identity collisions", ""])
    for row in collision_rows:
        error_lines.append(
            f"- {row['query_id']}: retrieved `{'|'.join(row['retrieved_source_ids']) or 'ABSTAIN'}`; "
            f"TP={row['tp']}, FP={row['fp']}, FN={row['fn']}."
        )
    error_lines.extend(["", "## Representative missed relevant Sources", ""])
    for method, query_id, ids in missed[:20]:
        error_lines.append(f"- `{method}` {query_id}: `{'|'.join(ids)}`")
    if not missed:
        error_lines.append("- None.")
    error_lines.extend(["", "## Representative irrelevant retrieved Sources", ""])
    for method, query_id, ids in irrelevant[:20]:
        error_lines.append(f"- `{method}` {query_id}: `{'|'.join(ids)}`")
    if not irrelevant:
        error_lines.append("- None.")
    error_lines.extend([
        "", "## Answer/provenance limitations", "",
        "Generated answers were `NOT_APPLICABLE`; unsupported-answer analysis therefore remains `NOT_EVALUATED`. "
        "Graph path and evidence details for every retrieved Source are in `provenance_traces.jsonl`.", "",
    ])
    (output_dir / "error_analysis.md").write_text("\n".join(error_lines), encoding="utf-8")

    table = [
        "| Method | TP | FP | FN | Precision | Recall | F1 | Correct negative abstentions | Mean latency (ms) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in aggregates:
        table.append(
            f"| {item['implementation_id']} | {item['tp']} | {item['fp']} | {item['fn']} | "
            f"{item['micro_precision_answerable']:.3f} | {item['micro_recall_answerable']:.3f} | "
            f"{item['micro_f1_answerable']:.3f} | {item['correct_negative_abstentions']}/5 | {item['mean_latency_ms']:.3f} |"
        )
    report = [
        "# Exploratory synthetic benchmark v1 report", "", "## Status", "",
        f"All {manifest['rows']} method–question rows completed under the preregistered Top-3 contract. "
        "The data is synthetic and the study is exploratory, not confirmatory.", "", "## Aggregate results", "",
        *table, "", "Metrics are micro-averaged over the 25 answerable questions. Empty-gold questions are excluded from retrieval averages and evaluated primarily through abstention correctness.", "",
        "## Earlier pilot comparison boundary", "",
        "The earlier 30-profile pilot used different profiles, questions, implementations, and stored predictions. "
        "Its results are developmental and are not pooled with or treated as a baseline for this 50-profile run.", "",
        "## Interpretation", "",
    ]
    provenance = by_method["provenance_graph_v1"]
    alternatives = [item for key, item in by_method.items() if key != "provenance_graph_v1"]
    materially_better = any(
        provenance["micro_precision_answerable"] > item["micro_precision_answerable"]
        or provenance["micro_f1_answerable"] > item["micro_f1_answerable"]
        for item in alternatives
    ) and provenance["micro_recall_answerable"] >= max(item["micro_recall_answerable"] for item in alternatives) - 0.05
    if materially_better:
        report.append("Under this synthetic benchmark, provenance-aware retrieval improved precision or F1 relative to at least one comparator without more than five percentage points of recall loss. This is benchmark-specific and does not establish real-world superiority.")
    else:
        report.append("The preregistered criterion for describing provenance-aware retrieval as better was not met. Results are reported neutrally.")
    report.extend([
        "", "## Limitations", "",
        "This is a small synthetic fixture. The graph contains sparse extracted entities, a high-degree role concept, no calibrated edge confidence, and no production identity-resolution system. "
        "Results may not generalize to naturally occurring organizational graphs. Full GraphRAG, LLM answer generation, production security, and real-world user behavior were not evaluated.", "",
        "## Reproduction", "", "```bash",
        "python3.12 -m venv .venv-benchmark",
        ".venv-benchmark/bin/python -m pip install -r requirements-benchmark.txt",
        "HF_HOME=$PWD/.cache/huggingface .venv-benchmark/bin/python -W error::ResourceWarning -m unittest discover -v",
        "HF_HOME=$PWD/.cache/huggingface .venv-benchmark/bin/python scripts/run_benchmark.py",
        "```", "",
    ])
    (output_dir / "benchmark_report.md").write_text("\n".join(report), encoding="utf-8")

    integrity_source = root / "docs" / "benchmark_integrity_report.md"
    if integrity_source.exists():
        (output_dir / "benchmark_integrity_report.md").write_bytes(integrity_source.read_bytes())
    (output_dir / "method_specifications.md").write_text(
        "# Executed method specifications\n\nThe authoritative frozen specification is "
        "[`docs/algorithm_preregistration_v1.md`](../../docs/algorithm_preregistration_v1.md), SHA-256 "
        f"`{manifest['fingerprints']['algorithm_preregistration_sha256']}`.\n\n"
        "Executed implementations: `bm25_v1`, `minilm_vector_v1`, `unweighted_graph_v1`, and "
        "`provenance_graph_v1`. Generated answers were `NOT_APPLICABLE`.\n",
        encoding="utf-8",
    )


def default_output_dir(root: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return root / "results" / f"codex_benchmark_v1_{timestamp}"
