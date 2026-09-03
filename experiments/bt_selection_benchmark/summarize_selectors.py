from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Callable

EXPERIMENT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = EXPERIMENT_DIR / "results" / "bt_candidate_evaluations.csv"
DEFAULT_SUMMARY = EXPERIMENT_DIR / "results" / "summary_by_selector.csv"
DEFAULT_CHOICES = EXPERIMENT_DIR / "results" / "selector_choices.csv"

SUMMARY_COLUMNS = [
    "selector",
    "group_count",
    "selected_success_rate",
    "selected_goal_satisfaction",
    "mean_selected_score",
    "mean_oracle_score",
    "mean_regret",
    "oracle_success_rate",
    "notes",
]

CHOICE_COLUMNS = [
    "selector",
    "task_id",
    "initial_state_id",
    "selected_candidate_id",
    "selected_candidate_type",
    "selected_symbolic_success",
    "selected_goal_satisfaction",
    "selected_score",
    "oracle_candidate_id",
    "oracle_candidate_type",
    "oracle_symbolic_success",
    "oracle_score",
    "regret",
]


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


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def group_rows(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["task_id"], row["initial_state_id"])].append(row)
    return dict(groups)


def candidate_score(row: dict[str, str]) -> float:
    return as_float(row, "score")


def rule_score(row: dict[str, str]) -> float:
    return (
        50.0 * as_int(row, "symbolic_success")
        + 20.0 * as_float(row, "goal_satisfaction")
        + 20.0 * as_float(row, "precondition_coverage", 1.0)
        - 1.0 * as_float(row, "action_count")
        - 0.5 * as_float(row, "tree_size")
        - 5.0 * as_float(row, "invalid_action_count")
        - 0.5 * as_float(row, "bt_ticks")
    )


def oracle_selector(rows: list[dict[str, str]]) -> dict[str, str]:
    return max(rows, key=lambda row: (candidate_score(row), as_int(row, "symbolic_success")))


def first_candidate_selector(rows: list[dict[str, str]]) -> dict[str, str]:
    return rows[0]


def shortest_tree_selector(rows: list[dict[str, str]]) -> dict[str, str]:
    return min(
        rows,
        key=lambda row: (
            as_float(row, "tree_size"),
            as_float(row, "action_count"),
            as_float(row, "bt_ticks"),
        ),
    )


def symbolic_success_selector(rows: list[dict[str, str]]) -> dict[str, str]:
    return max(
        rows,
        key=lambda row: (
            as_int(row, "symbolic_success"),
            as_float(row, "goal_satisfaction"),
            -as_float(row, "tree_size"),
            -as_float(row, "action_count"),
        ),
    )


def rule_based_selector(rows: list[dict[str, str]]) -> dict[str, str]:
    return max(rows, key=rule_score)


def make_choice_row(
    selector_name: str,
    selected: dict[str, str],
    oracle: dict[str, str],
) -> dict[str, Any]:
    selected_score = candidate_score(selected)
    oracle_score = candidate_score(oracle)
    return {
        "selector": selector_name,
        "task_id": selected["task_id"],
        "initial_state_id": selected["initial_state_id"],
        "selected_candidate_id": selected["candidate_id"],
        "selected_candidate_type": selected["candidate_type"],
        "selected_symbolic_success": as_int(selected, "symbolic_success"),
        "selected_goal_satisfaction": as_float(selected, "goal_satisfaction"),
        "selected_score": round(selected_score, 6),
        "oracle_candidate_id": oracle["candidate_id"],
        "oracle_candidate_type": oracle["candidate_type"],
        "oracle_symbolic_success": as_int(oracle, "symbolic_success"),
        "oracle_score": round(oracle_score, 6),
        "regret": round(oracle_score - selected_score, 6),
    }


def summarize_choice_rows(
    selector_name: str,
    choice_rows: list[dict[str, Any]],
    notes: str,
) -> dict[str, Any]:
    return {
        "selector": selector_name,
        "group_count": len(choice_rows),
        "selected_success_rate": round(mean(float(row["selected_symbolic_success"]) for row in choice_rows), 6),
        "selected_goal_satisfaction": round(mean(float(row["selected_goal_satisfaction"]) for row in choice_rows), 6),
        "mean_selected_score": round(mean(float(row["selected_score"]) for row in choice_rows), 6),
        "mean_oracle_score": round(mean(float(row["oracle_score"]) for row in choice_rows), 6),
        "mean_regret": round(mean(float(row["regret"]) for row in choice_rows), 6),
        "oracle_success_rate": round(mean(float(row["oracle_symbolic_success"]) for row in choice_rows), 6),
        "notes": notes,
    }


def random_expected_summary(groups: dict[tuple[str, str], list[dict[str, str]]]) -> dict[str, Any]:
    per_group_success = []
    per_group_goal = []
    per_group_score = []
    per_group_oracle_score = []
    per_group_regret = []
    per_group_oracle_success = []

    for rows in groups.values():
        oracle = oracle_selector(rows)
        oracle_score = candidate_score(oracle)
        expected_score = mean(candidate_score(row) for row in rows)
        per_group_success.append(mean(as_int(row, "symbolic_success") for row in rows))
        per_group_goal.append(mean(as_float(row, "goal_satisfaction") for row in rows))
        per_group_score.append(expected_score)
        per_group_oracle_score.append(oracle_score)
        per_group_regret.append(oracle_score - expected_score)
        per_group_oracle_success.append(as_int(oracle, "symbolic_success"))

    return {
        "selector": "random_expected",
        "group_count": len(groups),
        "selected_success_rate": round(mean(per_group_success), 6),
        "selected_goal_satisfaction": round(mean(per_group_goal), 6),
        "mean_selected_score": round(mean(per_group_score), 6),
        "mean_oracle_score": round(mean(per_group_oracle_score), 6),
        "mean_regret": round(mean(per_group_regret), 6),
        "oracle_success_rate": round(mean(per_group_oracle_success), 6),
        "notes": "Expected value over uniform random candidate selection.",
    }


def run_selectors(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups = group_rows(rows)
    selectors: list[tuple[str, Callable[[list[dict[str, str]]], dict[str, str]], str]] = [
        ("first_candidate", first_candidate_selector, "Choose the first candidate in the CSV order."),
        ("shortest_tree", shortest_tree_selector, "Choose the smallest BT by tree_size."),
        ("symbolic_success", symbolic_success_selector, "Prefer candidates that passed symbolic evaluation."),
        ("rule_based", rule_based_selector, "Weighted symbolic metrics without using oracle score directly."),
        ("oracle", oracle_selector, "Upper bound using the true evaluated score."),
    ]

    summary_rows = [random_expected_summary(groups)]
    choice_rows: list[dict[str, Any]] = []

    for selector_name, selector_fn, notes in selectors:
        selector_choices = []
        for group in groups.values():
            oracle = oracle_selector(group)
            selected = selector_fn(group)
            row = make_choice_row(selector_name, selected, oracle)
            selector_choices.append(row)
            choice_rows.append(row)
        summary_rows.append(summarize_choice_rows(selector_name, selector_choices, notes))

    return summary_rows, choice_rows


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize selector baselines for BT candidate evaluations.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--choices-output", type=Path, default=DEFAULT_CHOICES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = load_rows(args.input)
    if not rows:
        raise SystemExit(f"No rows found in {args.input}")

    summary_rows, choice_rows = run_selectors(rows)
    write_csv(args.summary_output, summary_rows, SUMMARY_COLUMNS)
    write_csv(args.choices_output, choice_rows, CHOICE_COLUMNS)

    print(
        json.dumps(
            {
                "result": "success",
                "input": str(args.input),
                "groups": len(group_rows(rows)),
                "summary_output": str(args.summary_output),
                "choices_output": str(args.choices_output),
                "selectors": [row["selector"] for row in summary_rows],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())