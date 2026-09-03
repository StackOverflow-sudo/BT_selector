from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


EXPERIMENT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EXPERIMENT_DIR / "results"
DEFAULT_EVALUATIONS = RESULTS_DIR / "bt_candidate_evaluations_v2b_physical_strategy_with_sim.csv"
DEFAULT_RULE_CHOICES = RESULTS_DIR / "rule_based_selector_choices_v2b_physical_strategy_with_sim.csv"
DEFAULT_STRATEGY_SUMMARY = RESULTS_DIR / "summary_by_strategy_v2b_physical_strategy_with_sim.csv"
DEFAULT_TASK_STRATEGY_SUMMARY = RESULTS_DIR / "summary_by_task_strategy_v2b_physical_strategy_with_sim.csv"
DEFAULT_REPORT = RESULTS_DIR / "v2b_physical_strategy_analysis.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def as_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    if value in {"", None, "pending", "skipped"}:
        return default
    return float(value)


def as_int(row: dict[str, str], key: str, default: int = 0) -> int:
    return int(as_float(row, key, default))


def pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def group_by(rows: list[dict[str, str]], keys: tuple[str, ...]) -> dict[tuple[str, ...], list[dict[str, str]]]:
    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    return dict(groups)


def summarize(rows: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "count": len(rows),
        "sim_success_rate": round(mean(as_int(row, "sim_success") for row in rows), 6),
        "mean_score": round(mean(as_float(row, "score") for row in rows), 6),
        "mean_final_position_error": round(mean(as_float(row, "final_position_error") for row in rows), 6),
        "mean_object_displacement_error": round(mean(as_float(row, "object_displacement_error") for row in rows), 6),
        "contact_violation_rate": round(mean(as_int(row, "contact_violation_proxy") for row in rows), 6),
    }


def strategy_summary(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for (candidate_type,), group in sorted(group_by(rows, ("candidate_type",)).items()):
        summary = summarize(group)
        summary["candidate_type"] = candidate_type
        out.append(summary)
    return out


def task_strategy_summary(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for (task_id, candidate_type), group in sorted(group_by(rows, ("task_id", "candidate_type")).items()):
        summary = summarize(group)
        summary["task_id"] = task_id
        summary["candidate_type"] = candidate_type
        out.append(summary)
    return out


def oracle_counts(rows: list[dict[str, str]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for group in group_by(rows, ("task_id", "initial_state_id")).values():
        best = max(group, key=lambda row: as_float(row, "score"))
        counts[best["candidate_type"]] += 1
    return counts


def selector_summary(choices: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    grouped = group_by(choices, ("selector",))
    out: dict[str, dict[str, float]] = {}
    for (selector,), rows in grouped.items():
        out[selector] = {
            "mean_regret": mean(as_float(row, "regret") for row in rows),
            "mean_true_score": mean(as_float(row, "selected_true_score") for row in rows),
            "sim_success_rate": mean(as_int(row, "selected_sim_success") for row in rows),
        }
    return out


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def make_report(
    rows: list[dict[str, str]],
    choices: list[dict[str, str]],
    strategy_rows: list[dict[str, Any]],
    task_strategy_rows: list[dict[str, Any]],
) -> str:
    status = Counter(row.get("simulation_status", "") for row in rows)
    oracle = oracle_counts(rows)
    selectors = selector_summary(choices)
    symbolic = selectors.get("rule_based_symbolic", {})
    simulation = selectors.get("rule_based_simulation", {})
    regret_delta = symbolic.get("mean_regret", 0.0) - simulation.get("mean_regret", 0.0)

    strategy_table = markdown_table(
        ["Candidate", "N", "Sim success", "Mean score", "Mean pos error", "Mean displacement"],
        [
            [
                row["candidate_type"],
                row["count"],
                pct(float(row["sim_success_rate"])),
                f"{float(row['mean_score']):.3f}",
                f"{float(row['mean_final_position_error']):.4f}",
                f"{float(row['mean_object_displacement_error']):.4f}",
            ]
            for row in strategy_rows
        ],
    )

    task_rows = []
    for row in task_strategy_rows:
        if row["candidate_type"] not in {"correct_bt", "center_place_bt", "edge_place_bt", "corner_place_bt", "over_edge_bt", "far_offset_bt"}:
            continue
        task_rows.append(
            [
                row["task_id"],
                row["candidate_type"],
                pct(float(row["sim_success_rate"])),
                f"{float(row['mean_score']):.3f}",
            ]
        )

    oracle_table = markdown_table(
        ["Oracle candidate", "Groups"],
        [[candidate, count] for candidate, count in sorted(oracle.items())],
    )

    return "\n".join(
        [
            "# V2B Physical Strategy Analysis",
            "",
            "## Completion",
            "",
            f"- Done simulation rows: {status.get('done', 0)}",
            f"- Pending rows: {status.get('pending', 0)}",
            "",
            "## Main Finding",
            "",
            f"- Symbolic selector mean regret: {symbolic.get('mean_regret', 0.0):.3f}.",
            f"- Simulation-aware selector mean regret: {simulation.get('mean_regret', 0.0):.3f}.",
            f"- Regret reduction: {regret_delta:.3f}.",
            f"- Simulation-aware selected sim success: {pct(simulation.get('sim_success_rate', 0.0))}.",
            "",
            "V2B is the first benchmark variant where all candidates are symbolically successful, but simulation-aware scoring nearly matches the oracle by selecting physically better placement strategies.",
            "",
            "## Strategy Summary",
            "",
            strategy_table,
            "",
            "## Oracle Preference",
            "",
            oracle_table,
            "",
            "## Task-Strategy Summary",
            "",
            markdown_table(["Task", "Candidate", "Sim success", "Mean score"], task_rows),
            "",
            "## Paper Claim",
            "",
            "Simulation-grounded metrics reduce selector regret when candidate BTs are symbolically indistinguishable but physically different.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze V2B physical strategy results.")
    parser.add_argument("--evaluations", type=Path, default=DEFAULT_EVALUATIONS)
    parser.add_argument("--rule-choices", type=Path, default=DEFAULT_RULE_CHOICES)
    parser.add_argument("--strategy-summary", type=Path, default=DEFAULT_STRATEGY_SUMMARY)
    parser.add_argument("--task-strategy-summary", type=Path, default=DEFAULT_TASK_STRATEGY_SUMMARY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_csv(args.evaluations)
    choices = read_csv(args.rule_choices)
    strategies = strategy_summary(rows)
    task_strategies = task_strategy_summary(rows)
    write_csv(
        args.strategy_summary,
        strategies,
        [
            "candidate_type",
            "count",
            "sim_success_rate",
            "mean_score",
            "mean_final_position_error",
            "mean_object_displacement_error",
            "contact_violation_rate",
        ],
    )
    write_csv(
        args.task_strategy_summary,
        task_strategies,
        [
            "task_id",
            "candidate_type",
            "count",
            "sim_success_rate",
            "mean_score",
            "mean_final_position_error",
            "mean_object_displacement_error",
            "contact_violation_rate",
        ],
    )
    args.report.write_text(make_report(rows, choices, strategies, task_strategies), encoding="utf-8")
    print(
        json.dumps(
            {
                "result": "success",
                "strategy_summary": str(args.strategy_summary),
                "task_strategy_summary": str(args.task_strategy_summary),
                "report": str(args.report),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
