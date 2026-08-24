#!/usr/bin/env python3
"""Generate release SVG charts from the validated aggregate metrics CSV."""

from __future__ import annotations

import argparse
import csv
import html
from pathlib import Path


METHOD_LABELS = {
    "bm25_v1": "BM25",
    "minilm_vector_v1": "MiniLM vector",
    "unweighted_graph_v1": "Unweighted graph",
    "provenance_graph_v1": "Provenance-aware",
}
METRICS = [
    ("micro_precision_answerable", "Precision", "#2563EB"),
    ("micro_recall_answerable", "Recall", "#D97706"),
    ("micro_f1_answerable", "F1", "#4D7C0F"),
]
INK = "#172033"
MUTED = "#5B6474"
GRID = "#D8DEE8"


def load_metrics(path: Path) -> list[dict[str, object]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 4:
        raise ValueError(f"expected four method rows, found {len(rows)}")
    parsed = []
    for row in rows:
        implementation = row["implementation_id"]
        if implementation not in METHOD_LABELS:
            raise ValueError(f"unexpected implementation {implementation}")
        item: dict[str, object] = {"implementation_id": implementation, "label": METHOD_LABELS[implementation]}
        for field, _, _ in METRICS:
            value = float(row[field])
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{implementation} {field} outside [0, 1]")
            item[field] = value
        parsed.append(item)
    return parsed


def svg_document(width: int, height: int, title: str, description: str, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="chart-title chart-desc">
  <title id="chart-title">{html.escape(title)}</title>
  <desc id="chart-desc">{html.escape(description)}</desc>
  <rect width="100%" height="100%" fill="#FFFFFF"/>
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: {INK}; }}
    .mono {{ font-family: ui-monospace, "SFMono-Regular", Consolas, monospace; }}
  </style>
{body}
</svg>
'''


def grouped_chart(rows: list[dict[str, object]]) -> str:
    width, height = 1040, 620
    left, right, top, bottom = 88, 28, 112, 130
    plot_w, plot_h = width - left - right, height - top - bottom
    elements = [
        f'  <text x="{left}" y="42" font-size="25" font-weight="700">Top-3 retrieval performance</text>',
        f'  <text x="{left}" y="70" font-size="14" fill="{MUTED}">50-profile synthetic benchmark · micro metrics over 25 answerable questions</text>',
    ]
    for tick in range(0, 101, 20):
        y = top + plot_h * (1 - tick / 100)
        elements.append(f'  <line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
        elements.append(f'  <text class="mono" x="{left - 12}" y="{y + 5:.1f}" text-anchor="end" font-size="12" fill="{MUTED}">{tick}%</text>')
    legend_x = left + 500
    for index, (_, label, color) in enumerate(METRICS):
        x = legend_x + index * 122
        elements.append(f'  <rect x="{x}" y="37" width="16" height="16" rx="2" fill="{color}"/>')
        elements.append(f'  <text x="{x + 23}" y="50" font-size="13">{label}</text>')
    group_w = plot_w / len(rows)
    bar_w, gap = 42, 7
    bars_w = len(METRICS) * bar_w + (len(METRICS) - 1) * gap
    for row_index, row in enumerate(rows):
        group_x = left + row_index * group_w + (group_w - bars_w) / 2
        for metric_index, (field, label, color) in enumerate(METRICS):
            value = float(row[field])
            x = group_x + metric_index * (bar_w + gap)
            bar_h = value * plot_h
            y = top + plot_h - bar_h
            elements.append(f'  <rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{bar_h:.1f}" rx="2" fill="{color}" stroke="{INK}" stroke-width="0.6"/>')
            elements.append(f'  <text class="mono" x="{x + bar_w / 2:.1f}" y="{y - 7:.1f}" text-anchor="middle" font-size="11">{value:.1%}</text>')
        center = left + (row_index + 0.5) * group_w
        label = str(row["label"])
        elements.append(f'  <text x="{center:.1f}" y="{top + plot_h + 31}" text-anchor="middle" font-size="13" font-weight="600">{html.escape(label)}</text>')
    elements.extend([
        f'  <line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="{INK}"/>',
        f'  <line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="{INK}"/>',
        f'  <text x="{left}" y="{height - 28}" font-size="12" fill="{MUTED}">Source: validated aggregate_metrics.csv · retrieval only; no generated-answer evaluation</text>',
    ])
    return svg_document(
        width, height,
        "Top-3 retrieval performance",
        "Grouped bars compare precision, recall, and F1 for BM25, MiniLM vector, unweighted graph, and provenance-aware graph retrieval.",
        "\n".join(elements),
    )


def graph_tradeoff_chart(rows: list[dict[str, object]]) -> str:
    selected = {str(row["implementation_id"]): row for row in rows}
    graph_rows = [selected["unweighted_graph_v1"], selected["provenance_graph_v1"]]
    width, height = 800, 520
    left, right, top, bottom = 92, 42, 100, 82
    plot_w, plot_h = width - left - right, height - top - bottom
    x_min, x_max = 0.20, 0.40
    y_min, y_max = 0.40, 0.65
    elements = [
        f'  <text x="{left}" y="40" font-size="24" font-weight="700">Graph precision–recall trade-off</text>',
        f'  <text x="{left}" y="67" font-size="14" fill="{MUTED}">Provenance filtering raised precision and lowered recall</text>',
    ]
    for tick in [0.20, 0.25, 0.30, 0.35, 0.40]:
        x = left + (tick - x_min) / (x_max - x_min) * plot_w
        elements.append(f'  <line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + plot_h}" stroke="{GRID}"/>')
        elements.append(f'  <text class="mono" x="{x:.1f}" y="{top + plot_h + 24}" text-anchor="middle" font-size="12">{tick:.0%}</text>')
    for tick in [0.40, 0.45, 0.50, 0.55, 0.60, 0.65]:
        y = top + (y_max - tick) / (y_max - y_min) * plot_h
        elements.append(f'  <line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="{GRID}"/>')
        elements.append(f'  <text class="mono" x="{left - 12}" y="{y + 5:.1f}" text-anchor="end" font-size="12">{tick:.0%}</text>')
    points = []
    for row in graph_rows:
        x_value = float(row["micro_recall_answerable"])
        y_value = float(row["micro_precision_answerable"])
        x = left + (x_value - x_min) / (x_max - x_min) * plot_w
        y = top + (y_max - y_value) / (y_max - y_min) * plot_h
        points.append((x, y, row))
    elements.append(f'  <line x1="{points[0][0]:.1f}" y1="{points[0][1]:.1f}" x2="{points[1][0]:.1f}" y2="{points[1][1]:.1f}" stroke="{MUTED}" stroke-width="2" stroke-dasharray="6 5"/>')
    x, y, row = points[0]
    elements.append(f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="#FFFFFF" stroke="#2563EB" stroke-width="4"/>')
    elements.append(f'  <text x="{x + 15:.1f}" y="{y + 5:.1f}" font-size="13" font-weight="600">Unweighted ({float(row["micro_precision_answerable"]):.1%} P, {float(row["micro_recall_answerable"]):.1%} R)</text>')
    x, y, row = points[1]
    elements.append(f'  <rect x="{x - 8:.1f}" y="{y - 8:.1f}" width="16" height="16" fill="#D97706" stroke="{INK}" stroke-width="1"/>')
    elements.append(f'  <text x="{x + 15:.1f}" y="{y + 5:.1f}" font-size="13" font-weight="600">Provenance-aware ({float(row["micro_precision_answerable"]):.1%} P, {float(row["micro_recall_answerable"]):.1%} R)</text>')
    elements.extend([
        f'  <line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="{INK}"/>',
        f'  <line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="{INK}"/>',
        f'  <text x="{left + plot_w / 2}" y="{height - 28}" text-anchor="middle" font-size="13">Recall</text>',
        f'  <text x="24" y="{top + plot_h / 2}" text-anchor="middle" font-size="13" transform="rotate(-90 24 {top + plot_h / 2})">Precision</text>',
    ])
    return svg_document(
        width, height,
        "Graph precision–recall trade-off",
        "The provenance-aware point has higher precision and lower recall than the unweighted graph point.",
        "\n".join(elements),
    )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    default_input = root / "results" / "codex_benchmark_v1_20260824_204717" / "aggregate_metrics.csv"
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=default_input)
    parser.add_argument("--output-dir", type=Path, default=root / "docs" / "assets")
    args = parser.parse_args()
    rows = load_metrics(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        args.output_dir / "benchmark_metrics.svg": grouped_chart(rows),
        args.output_dir / "graph_precision_recall_tradeoff.svg": graph_tradeoff_chart(rows),
    }
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
