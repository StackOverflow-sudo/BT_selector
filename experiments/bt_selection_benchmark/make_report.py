from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

EXPERIMENT_DIR = Path(__file__).resolve().parent
DEFAULT_EVALUATIONS = EXPERIMENT_DIR / "results" / "bt_candidate_evaluations.csv"
DEFAULT_SUMMARY = EXPERIMENT_DIR / "results" / "summary_by_selector.csv"
DEFAULT_CHOICES = EXPERIMENT_DIR / "results" / "selector_choices.csv"
DEFAULT_OUTPUT = EXPERIMENT_DIR / "results" / "benchmark_report.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def as_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    if value in {"", None}:
        return default
    return float(value)


def as_int(row: dict[str, str], key: str, default: int = 0) -> int:
    value = row.get(key, "")
    if value in {"", None}:
        return default
    return int(float(value))


def pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        out.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(out)


def candidate_type_rows(evaluations: list[dict[str, str]]) -> list[list[Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in evaluations:
        grouped[row["candidate_type"]].append(row)

    rows = []
    for candidate_type in sorted(grouped):
        group = grouped[candidate_type]
        rows.append(
            [
                candidate_type,
                len(group),
                pct(mean(as_int(row, "symbolic_success") for row in group)),
                f"{mean(as_float(row, 'goal_satisfaction') for row in group):.3f}",
                f"{mean(as_float(row, 'score') for row in group):.3f}",
                f"{mean(as_float(row, 'precondition_coverage', 1.0) for row in group):.3f}",
                f"{mean(as_float(row, 'tree_size') for row in group):.2f}",
                f"{mean(as_float(row, 'bt_ticks') for row in group):.2f}",
            ]
        )
    return rows


def task_rows(evaluations: list[dict[str, str]]) -> list[list[Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in evaluations:
        grouped[row["task_id"]].append(row)

    rows = []
    for task_id in sorted(grouped):
        group = grouped[task_id]
        rows.append(
            [
                task_id,
                len(group),
                pct(mean(as_int(row, "symbolic_success") for row in group)),
                f"{max(as_float(row, 'score') for row in group):.3f}",
                f"{mean(as_float(row, 'score') for row in group):.3f}",
            ]
        )
    return rows


def selector_rows(summary: list[dict[str, str]]) -> list[list[Any]]:
    rows = []
    for row in summary:
        rows.append(
            [
                row["selector"],
                row["group_count"],
                pct(as_float(row, "selected_success_rate")),
                f"{as_float(row, 'selected_goal_satisfaction'):.3f}",
                f"{as_float(row, 'mean_selected_score'):.3f}",
                f"{as_float(row, 'mean_regret'):.3f}",
            ]
        )
    return rows


def choice_rows(choices: list[dict[str, str]]) -> list[list[Any]]:
    rows = []
    for row in choices:
        if row["selector"] == "oracle":
            continue
        rows.append(
            [
                row["selector"],
                row["task_id"],
                row["selected_candidate_type"],
                row["selected_symbolic_success"],
                row["oracle_candidate_type"],
                row["regret"],
            ]
        )
    return rows


def make_interpretation(summary: list[dict[str, str]], evaluations: list[dict[str, str]]) -> list[str]:
    by_selector = {row["selector"]: row for row in summary}
    oracle = by_selector.get("oracle")
    random_expected = by_selector.get("random_expected")
    rule_based = by_selector.get("rule_based")
    symbolic_success = by_selector.get("symbolic_success")

    lines = []
    if oracle and random_expected:
        lines.append(
            f"- The oracle upper bound reaches {pct(as_float(oracle, 'selected_success_rate'))} symbolic success, while uniform random selection reaches {pct(as_float(random_expected, 'selected_success_rate'))}."
        )
    if rule_based and random_expected:
        delta = as_float(rule_based, "selected_success_rate") - as_float(random_expected, "selected_success_rate")
        lines.append(
            f"- The rule-based selector improves over random selection by {pct(delta)} symbolic success in this V0 setting."
        )
    if symbolic_success:
        lines.append(
            f"- The symbolic-success selector reaches {pct(as_float(symbolic_success, 'selected_success_rate'))}, showing that KIOS execution traces already provide useful selection signals."
        )

    candidate_counts = Counter(row["candidate_type"] for row in evaluations)
    lines.append(
        f"- The current benchmark contains {len(evaluations)} evaluated candidates across {len(set(row['task_id'] for row in evaluations))} tasks and {len(candidate_counts)} candidate types."
    )
    lines.append(
        "- Simulation metrics are still placeholders; the next stage should connect the selected candidates to Isaac Gym headless validation."
    )
    return lines


def make_report(
    evaluations: list[dict[str, str]],
    summary: list[dict[str, str]],
    choices: list[dict[str, str]],
    evaluations_path: Path,
    summary_path: Path,
    choices_path: Path,
) -> str:
    task_count = len(set(row["task_id"] for row in evaluations))
    initial_state_count = len(set(row["initial_state_id"] for row in evaluations))
    candidate_count = len(evaluations)
    candidate_type_count = len(set(row["candidate_type"] for row in evaluations))
    symbolic_success_rate = mean(as_int(row, "symbolic_success") for row in evaluations)

    parts = [
        "# BT Selection Benchmark Report",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Inputs",
        "",
        f"- Candidate evaluations: `{evaluations_path}`",
        f"- Selector summary: `{summary_path}`",
        f"- Selector choices: `{choices_path}`",
        "",
        "## Dataset Summary",
        "",
        markdown_table(
            ["Metric", "Value"],
            [
                ["Tasks", task_count],
                ["Initial states", initial_state_count],
                ["Candidate BTs", candidate_count],
                ["Candidate types", candidate_type_count],
                ["Overall symbolic success", pct(symbolic_success_rate)],
            ],
        ),
        "",
        "## Candidate Type Performance",
        "",
        markdown_table(
            [
                "Candidate type",
                "Count",
                "Symbolic success",
                "Goal satisfaction",
                "Mean score",
                "Precondition coverage",
                "Mean tree size",
                "Mean ticks",
            ],
            candidate_type_rows(evaluations),
        ),
        "",
        "## Task-Level Summary",
        "",
        markdown_table(
            ["Task", "Candidates", "Symbolic success", "Best score", "Mean score"],
            task_rows(evaluations),
        ),
        "",
        "## Selector Baseline Summary",
        "",
        markdown_table(
            [
                "Selector",
                "Groups",
                "Selected success",
                "Goal satisfaction",
                "Mean selected score",
                "Mean regret",
            ],
            selector_rows(summary),
        ),
        "",
        "## Selector Choices",
        "",
        markdown_table(
            [
                "Selector",
                "Task",
                "Selected candidate",
                "Selected success",
                "Oracle candidate",
                "Regret",
            ],
            choice_rows(choices),
        ),
        "",
        "## Interpretation",
        "",
        "\n".join(make_interpretation(summary, evaluations)),
        "",
        "## Current Limitations",
        "",
        "- This report is symbolic-only; Isaac Gym metrics are not populated yet.",
        "- Candidate BTs are controlled synthetic candidates, not yet LLM-generated candidates.",
        "- Only tasks marked `v0_required` are included in the default report.",
        "",
        "## Next Step",
        "",
        "Connect the evaluator to the existing Isaac Gym headless pipeline so that `sim_success`, `final_position_error`, and `object_displacement_error` become real simulation-grounded metrics.",
        "",
    ]
    return "\n".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a Markdown report for BT selector benchmark results.")
    parser.add_argument("--evaluations", type=Path, default=DEFAULT_EVALUATIONS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--choices", type=Path, default=DEFAULT_CHOICES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    evaluations = read_csv(args.evaluations)
    summary = read_csv(args.summary)
    choices = read_csv(args.choices)
    report = make_report(evaluations, summary, choices, args.evaluations, args.summary, args.choices)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "result": "success",
                "output": str(args.output),
                "tasks": len(set(row["task_id"] for row in evaluations)),
                "candidates": len(evaluations),
                "selectors": len(summary),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())