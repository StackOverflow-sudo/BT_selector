from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


MODEL_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = MODEL_DIR.parent
DEFAULT_INPUT = EXPERIMENT_DIR / "results" / "bt_candidate_evaluations.csv"
DEFAULT_CHOICES = EXPERIMENT_DIR / "results" / "rule_based_selector_choices.csv"
DEFAULT_SUMMARY = EXPERIMENT_DIR / "results" / "rule_based_selector_summary.csv"


CHOICE_COLUMNS = [
    "selector",
    "task_id",
    "initial_state_id",
    "selected_candidate_id",
    "selected_candidate_type",
    "selected_symbolic_success",
    "selected_sim_success",
    "selected_goal_satisfaction",
    "selected_model_score",
    "selected_true_score",
    "oracle_candidate_id",
    "oracle_candidate_type",
    "oracle_symbolic_success",
    "oracle_sim_success",
    "oracle_true_score",
    "regret",
]

SUMMARY_COLUMNS = [
    "selector",
    "group_count",
    "selected_symbolic_success_rate",
    "selected_sim_success_rate",
    "selected_sim_success_count",
    "selected_sim_success_coverage",
    "selected_goal_satisfaction",
    "mean_selected_model_score",
    "mean_selected_true_score",
    "mean_oracle_true_score",
    "mean_regret",
    "notes",
]


def as_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    if value in {"", None, "pending", "skipped"}:
        return default
    return float(value)


def as_int(row: dict[str, str], key: str, default: int = 0) -> int:
    value = row.get(key, "")
    if value in {"", None, "pending", "skipped"}:
        return default
    return int(float(value))


def maybe_int(row: dict[str, str], key: str) -> int | None:
    value = row.get(key, "")
    if value in {"", None, "pending", "skipped"}:
        return None
    return int(float(value))


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def group_rows(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["task_id"], row["initial_state_id"])].append(row)
    return dict(groups)


def true_score(row: dict[str, str]) -> float:
    return as_float(row, "score")


def symbolic_reliability_score(row: dict[str, str]) -> float:
    return (
        50.0 * as_int(row, "symbolic_success")
        + 20.0 * as_float(row, "goal_satisfaction")
        + 15.0 * as_float(row, "precondition_coverage", 1.0)
        - 10.0 * as_float(row, "invalid_action_count")
        - 5.0 * as_float(row, "condition_failure_count")
        - 0.5 * as_float(row, "tree_size")
        - 0.3 * as_float(row, "tree_depth")
        - 0.2 * as_float(row, "bt_ticks")
        - 0.5 * as_float(row, "action_count")
    )


def simulation_reliability_score(row: dict[str, str]) -> float:
    score = symbolic_reliability_score(row)
    sim_success = maybe_int(row, "sim_success")
    if sim_success is not None:
        score += 100.0 * sim_success
    score -= 10.0 * as_float(row, "final_position_error")
    score -= 5.0 * as_float(row, "object_displacement_error")
    score -= 10.0 * as_float(row, "contact_violation_proxy")
    return score


def oracle(rows: list[dict[str, str]]) -> dict[str, str]:
    return max(
        rows,
        key=lambda row: (
            true_score(row),
            as_int(row, "symbolic_success"),
            as_float(row, "goal_satisfaction"),
        ),
    )


def select_by_score(rows: list[dict[str, str]], selector: str) -> tuple[dict[str, str], float]:
    if selector == "rule_based_symbolic":
        selected = max(rows, key=symbolic_reliability_score)
        return selected, symbolic_reliability_score(selected)
    if selector == "rule_based_simulation":
        selected = max(rows, key=simulation_reliability_score)
        return selected, simulation_reliability_score(selected)
    raise ValueError(f"Unknown selector: {selector}")


def make_choice_row(
    selector: str,
    selected: dict[str, str],
    selected_model_score: float,
    oracle_row: dict[str, str],
) -> dict[str, Any]:
    selected_true_score = true_score(selected)
    oracle_true_score = true_score(oracle_row)
    return {
        "selector": selector,
        "task_id": selected["task_id"],
        "initial_state_id": selected["initial_state_id"],
        "selected_candidate_id": selected["candidate_id"],
        "selected_candidate_type": selected["candidate_type"],
        "selected_symbolic_success": as_int(selected, "symbolic_success"),
        "selected_sim_success": selected.get("sim_success", ""),
        "selected_goal_satisfaction": as_float(selected, "goal_satisfaction"),
        "selected_model_score": round(selected_model_score, 6),
        "selected_true_score": round(selected_true_score, 6),
        "oracle_candidate_id": oracle_row["candidate_id"],
        "oracle_candidate_type": oracle_row["candidate_type"],
        "oracle_symbolic_success": as_int(oracle_row, "symbolic_success"),
        "oracle_sim_success": oracle_row.get("sim_success", ""),
        "oracle_true_score": round(oracle_true_score, 6),
        "regret": round(oracle_true_score - selected_true_score, 6),
    }


def summarize(selector: str, rows: list[dict[str, Any]], notes: str) -> dict[str, Any]:
    sim_values = [
        float(row["selected_sim_success"])
        for row in rows
        if row["selected_sim_success"] not in {"", None, "pending", "skipped"}
    ]
    return {
        "selector": selector,
        "group_count": len(rows),
        "selected_symbolic_success_rate": round(
            mean(float(row["selected_symbolic_success"]) for row in rows), 6
        ),
        "selected_sim_success_rate": round(mean(sim_values), 6) if sim_values else "",
        "selected_sim_success_count": len(sim_values),
        "selected_sim_success_coverage": round(len(sim_values) / len(rows), 6) if rows else "",
        "selected_goal_satisfaction": round(
            mean(float(row["selected_goal_satisfaction"]) for row in rows), 6
        ),
        "mean_selected_model_score": round(
            mean(float(row["selected_model_score"]) for row in rows), 6
        ),
        "mean_selected_true_score": round(
            mean(float(row["selected_true_score"]) for row in rows), 6
        ),
        "mean_oracle_true_score": round(
            mean(float(row["oracle_true_score"]) for row in rows), 6
        ),
        "mean_regret": round(mean(float(row["regret"]) for row in rows), 6),
        "notes": notes,
    }


def run(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups = group_rows(rows)
    selectors = [
        ("rule_based_symbolic", "Uses BT structure and KIOS symbolic execution metrics only."),
        ("rule_based_simulation", "Adds available simulation metrics to the symbolic reliability score."),
    ]
    all_choices = []
    summary_rows = []
    for selector, notes in selectors:
        selector_choices = []
        for group in groups.values():
            oracle_row = oracle(group)
            selected, selected_model_score = select_by_score(group, selector)
            choice = make_choice_row(selector, selected, selected_model_score, oracle_row)
            selector_choices.append(choice)
            all_choices.append(choice)
        summary_rows.append(summarize(selector, selector_choices, notes))
    return summary_rows, all_choices


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run rule-based BT candidate selectors.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--choices-output", type=Path, default=DEFAULT_CHOICES)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = load_rows(args.input)
    if not rows:
        raise SystemExit(f"No rows found in {args.input}")
    summary_rows, choice_rows = run(rows)
    write_csv(args.choices_output, choice_rows, CHOICE_COLUMNS)
    write_csv(args.summary_output, summary_rows, SUMMARY_COLUMNS)
    print(
        json.dumps(
            {
                "result": "success",
                "input": str(args.input),
                "groups": len(group_rows(rows)),
                "choices_output": str(args.choices_output),
                "summary_output": str(args.summary_output),
                "selectors": [row["selector"] for row in summary_rows],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
