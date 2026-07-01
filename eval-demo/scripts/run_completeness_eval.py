#!/usr/bin/env python3
"""Run a lightweight completeness eval over versioned dataset files.

The script intentionally has no third-party dependencies so it can run in
GitHub Actions without an install step. It supports CSV, JSON, and JSONL rows.
Rows may include a model output column. If no output is supplied, the script
uses a deterministic local demo output based on the expected/reference answer.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import sys
from pathlib import Path
from typing import Any


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


def main() -> int:
    args = parse_args()
    judge = json.loads(Path(args.judge).read_text(encoding="utf-8"))
    threshold = float(args.threshold) if args.threshold else float(judge.get("threshold", 0.75))
    dataset_paths = expand_dataset_paths(args.datasets)
    if not dataset_paths:
        print(f"No dataset files matched: {args.datasets}", file=sys.stderr)
        return 2

    all_results = []
    for path in dataset_paths:
        rows = load_rows(path)
        for index, row in enumerate(rows, start=1):
            result = score_row(path, index, row, threshold)
            all_results.append(result)

    report = make_report(judge, threshold, all_results)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    markdown_path = Path(args.markdown)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(report), encoding="utf-8")

    print(render_console(report))
    return 0 if report["passed"] else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run completeness evals for versioned datasets.")
    parser.add_argument("--datasets", default="eval-demo/datasets/*.jsonl", help="Dataset path or glob.")
    parser.add_argument("--judge", default="eval-demo/judges/completeness.json", help="Completeness judge JSON.")
    parser.add_argument("--threshold", default="", help="Optional pass threshold override.")
    parser.add_argument("--out", default="eval-demo/reports/completeness-report.json", help="JSON report path.")
    parser.add_argument("--markdown", default="eval-demo/reports/completeness-report.md", help="Markdown report path.")
    return parser.parse_args()


def expand_dataset_paths(patterns: str) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns.split(","):
        pattern = pattern.strip()
        if not pattern:
            continue
        matches = glob.glob(pattern)
        if matches:
            paths.extend(Path(match) for match in matches)
        else:
            paths.append(Path(pattern))
    return sorted(path for path in paths if path.exists() and path.is_file())


def load_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        rows = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip():
                rows.append(json.loads(line))
        return rows
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
        for key in ("rows", "examples", "data"):
            if isinstance(payload.get(key), list):
                return payload[key]
        raise ValueError(f"{path} must be an array or contain rows/examples/data.")
    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    raise ValueError(f"Unsupported dataset format: {path}")


def score_row(path: Path, index: int, row: dict[str, Any], threshold: float) -> dict[str, Any]:
    input_text = first_value(row, "input", "prompt", "question")
    expected = first_value(row, "expected", "reference", "ideal", "answer")
    output = first_value(row, "output", "response", "model_output", "actual")
    if not output:
        output = local_demo_output(expected)

    expected_terms = content_terms(expected)
    output_terms = content_terms(output)
    coverage = len(expected_terms & output_terms) / max(1, len(expected_terms))
    detail_bonus = min(0.18, len(output_terms) / 140)
    empty_penalty = 0.35 if not expected.strip() else 0
    score = round(max(0, min(1, 0.2 + (coverage * 0.68) + detail_bonus - empty_penalty)), 3)
    passed = score >= threshold

    if not expected_terms:
        rationale = "No reference answer was supplied, so completeness cannot be strongly verified."
    elif passed:
        rationale = "Output covers the main reference requirements with enough detail for the demo threshold."
    else:
        missing = sorted(expected_terms - output_terms)[:6]
        rationale = f"Output misses expected concepts: {', '.join(missing) or 'material coverage'}."

    return {
        "dataset": str(path),
        "row": index,
        "id": str(row.get("id") or row.get("example_id") or f"{path.stem}-{index}"),
        "input": input_text,
        "expected": expected,
        "output": output,
        "score": score,
        "passed": passed,
        "rationale": rationale,
    }


def first_value(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def local_demo_output(expected: str) -> str:
    if expected.strip():
        return f"{expected.strip()} The answer includes the core requested details and is ready for review."
    return "No reference answer supplied. The response gives a concise best-effort answer."


def content_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9-]{2,}", text.lower())
        if token not in STOPWORDS
    }


def make_report(judge: dict[str, Any], threshold: float, results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed_count = sum(1 for result in results if result["passed"])
    avg_score = round(sum(result["score"] for result in results) / max(1, total), 3)
    pass_rate = round(passed_count / max(1, total), 3)
    return {
        "judge": {
            "id": judge.get("id"),
            "name": judge.get("name"),
            "version": judge.get("version"),
            "threshold": threshold,
        },
        "total_examples": total,
        "passed_examples": passed_count,
        "failed_examples": total - passed_count,
        "average_score": avg_score,
        "pass_rate": pass_rate,
        "passed": total > 0 and passed_count == total,
        "results": results,
    }


def render_console(report: dict[str, Any]) -> str:
    status = "PASS" if report["passed"] else "FAIL"
    return (
        f"{status} completeness eval: "
        f"{report['passed_examples']}/{report['total_examples']} passed, "
        f"avg={report['average_score']}, pass_rate={report['pass_rate']}"
    )


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Completeness Eval Report",
        "",
        f"- Judge: `{report['judge']['name']}` `{report['judge']['version']}`",
        f"- Threshold: `{report['judge']['threshold']}`",
        f"- Average score: `{report['average_score']}`",
        f"- Pass rate: `{report['pass_rate']}`",
        f"- Passed examples: `{report['passed_examples']}/{report['total_examples']}`",
        "",
        "| Dataset | Row | Score | Result | Rationale |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for result in report["results"]:
        status = "pass" if result["passed"] else "review"
        rationale = result["rationale"].replace("|", "\\|")
        lines.append(
            f"| `{result['dataset']}` | {result['row']} | {result['score']} | {status} | {rationale} |"
        )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
