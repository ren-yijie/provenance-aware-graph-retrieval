#!/usr/bin/env python3
"""Reproduce archived Phase II work in a temporary layout; leave snapshots untouched."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"


def tracked_hashes() -> dict[str, str]:
    names = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files", "-z"], text=True
    ).rstrip("\0").split("\0")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    before = tracked_hashes()
    publication = json.loads((RESEARCH / "publication_manifest.json").read_text())
    for filename, expected in publication["artifacts"].items():
        assert hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() == expected, filename
    print(f"PASS {len(publication['artifacts'])} archived artifact fingerprints")
    with tempfile.TemporaryDirectory(prefix="practicum-phase2-") as directory:
        workspace = Path(directory)
        # Archived scripts expect the original sibling-folder layout.
        (workspace / "provenance-aware-graph-retrieval").symlink_to(ROOT, target_is_directory=True)
        for name in ("audit-2026-10-30", "research-2026-10-31"):
            shutil.copytree(RESEARCH / name, workspace / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        jobs = [
            ("audit-2026-10-30", "reproduce_audit.py"),
            ("research-2026-10-31", "test_experiments.py"),
            ("research-2026-10-31", "build_representation_evidence.py"),
            ("research-2026-10-31", "run_experiments.py"),
        ]
        # Archived runners parse line-delimited Git paths; disable path quoting for
        # their subprocesses so imported Chinese report filenames remain readable.
        child_env = os.environ.copy()
        config_index = int(child_env.get("GIT_CONFIG_COUNT", "0"))
        child_env["GIT_CONFIG_COUNT"] = str(config_index + 1)
        child_env[f"GIT_CONFIG_KEY_{config_index}"] = "core.quotePath"
        child_env[f"GIT_CONFIG_VALUE_{config_index}"] = "false"
        for folder, script in jobs:
            completed = subprocess.run(
                [sys.executable, str(workspace / folder / script)],
                cwd=workspace, capture_output=True, text=True, env=child_env,
            )
            if completed.returncode:
                print(completed.stdout, file=sys.stderr)
                print(completed.stderr, file=sys.stderr)
                raise SystemExit(completed.returncode)
            print(f"PASS {folder}/{script}")
        for folder, filename in (
            ("audit-2026-10-30", "all_120_method_audit.csv"),
            ("audit-2026-10-30", "fn_stage_partition.csv"),
            ("research-2026-10-31", "summary.csv"),
            ("research-2026-10-31", "per_query_results.csv"),
            ("research-2026-10-31", "changes.csv"),
        ):
            assert csv_rows(workspace / folder / filename) == csv_rows(RESEARCH / folder / filename), filename
        expected_facts = (RESEARCH / "research-2026-10-31/representation_facts.jsonl").read_bytes()
        assert (workspace / "research-2026-10-31/representation_facts.jsonl").read_bytes() == expected_facts
        # Wall-clock latency is expected to vary; all substantive trace fields must match.
        filename = "research-2026-10-31/traces.jsonl"
        old = [json.loads(line) for line in (RESEARCH / filename).read_text().splitlines()]
        new = [json.loads(line) for line in (workspace / filename).read_text().splitlines()]
        assert len(old) == len(new) == 276
        for expected, actual in zip(old, new):
            expected.pop("latency_ms")
            actual.pop("latency_ms")
            assert expected == actual, (expected["split"], expected["variant"], expected["query_id"])
    assert tracked_hashes() == before, "Tracked files changed during reproduction"
    print("PASS archived audit tables, experiment tables, 210 facts and 276 traces match")
    print("PASS all tracked repository files unchanged")


if __name__ == "__main__":
    main()
