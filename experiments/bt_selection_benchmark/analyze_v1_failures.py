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
DEFAULT_INPUT = RESULTS_DIR / "bt_candidate_evaluations_v1_supported_by_with_sim.csv"
DEFAULT_CANDIDATE_SUMMARY = RESULTS_DIR / "summary_by_candidate_type_v1_supported_by_with_sim.csv"
DEFAULT_TASK_CANDIDATE_SUMMARY = RESULTS_DIR / "summary_by_task_candidate_v1_supported_by_with_sim.csv"
DEFAULT_FAILED_CORRECT = RESULTS_DIR / "failed_correct_bt_cases_v1_supported_by_with_sim.csv"
DEFAULT_REPORT = RESULTS_DIR / "v1_failure_analysis.md"


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


def summarize_group(rows: list[dict[str, str]]) -> dict[str, Any]:
    done_rows = [row for row in rows if row.get("simulation_status") == "done"]
    sim_values = [as_int(row, "sim_success") for row in done_rows]
    return {
        "count": len(rows),
        "done_count": len(done_rows),
        "skipped_count": sum(1 for row in rows if row.get("simulation_status") == "skipped"),
        "symbolic_success_rate": round(mean(as_int(row, "symbolic_success") for row in rows), 6),
        "sim_success_rate": round(mean(sim_values), 6) if sim_values else "",
        "mean_score": round(mean(as_float(row, "score") for row in rows), 6),
        "mean_final_position_error": round(mean(as_float(row, "final_position_error") for row in done_rows), 6)
        if done_rows
        else "",
        "mean_object_displacement_error": round(
            mean(as_float(row, "object_displacement_error") for row in done_rows), 6
        )
        if done_rows
        else "",
        "contact_violation_rate": round(
            mean(as_int(row, "contact_violation_proxy") for row in done_rows), 6
        )
        if done_rows
        else "",
    }


def group_by(rows: list[dict[str, str]], keys: tuple[str, ...]) -> dict[tuple[str, ...], list[dict[str, str]]]:
    grouped: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)
    return dict(grouped)


def candidate_summary(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for (candidate_type,), group in sorted(group_by(rows, ("candidate_type",)).items()):
        summary = summarize_group(group)
        summary["candidate_type"] = candidate_type
        out.append(summary)
    return out


def task_candidate_summary(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for (task_id, candidate_type), group in sorted(group_by(rows, ("task_id", "candidate_type")).items()):
        summary = summarize_group(group)
        summary["task_id"] = task_id
        summary["candidate_type"] = candidate_type
        out.append(summary)
    return out


def failed_correct_cases(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    failures = []
    for row in rows:
        if row["candidate_type"] != "correct_bt":
            continue
        if as_int(row, "sim_success") == 1:
            continue
        failures.append(
            {
                "task_id": row["task_id"],
                "initial_state_id": row["initial_state_id"],
                "target_predicate": row["target_predicate"],
                "moved_object": row["moved_object"],
                "support_object": row["support_object"],
                "symbolic_success": row["symbolic_success"],
                "sim_success": row.get("sim_success", ""),
                "final_position_error": row.get("final_position_error", ""),
                "object_displacement_error": row.get("object_displacement_error", ""),
                "contact_violation_proxy": row.get("contact_violation_proxy", ""),
                "score": row.get("score", ""),
            }
        )
    return failures


def compare_correct_with_alternatives(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    comparisons = []
    for (task_id, state_id), group in sorted(group_by(rows, ("task_id", "initial_state_id")).items()):
        correct = next((row for row in group if row["candidate_type"] == "correct_bt"), None)
        if correct is None:
            continue
        alternatives = [row for row in group if row["candidate_type"] != "correct_bt"]
        best = max(group, key=lambda row: as_float(row, "score"))
        best_alt = max(alternatives, key=lambda row: as_float(row, "score"))
        comparisons.append(
            {
                "task_id": task_id,
                "initial_state_id": state_id,
                "correct_sim_success": as_int(correct, "sim_success"),
                "correct_score": round(as_float(correct, "score"), 6),
                "best_candidate_type": best["candidate_type"],
                "best_score": round(as_float(best, "score"), 6),
                "best_alternative_type": best_alt["candidate_type"],
                "best_alternative_sim_success": as_int(best_alt, "sim_success"),
                "best_alternative_score": round(as_float(best_alt, "score"), 6),
            }
        )
    return comparisons


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def make_report(
    rows: list[dict[str, str]],
    candidate_rows: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
) -> str:
    status_counts = Counter(row.get("simulation_status", "") for row in rows)
    total_done = status_counts.get("done", 0)
    total_skipped = status_counts.get("skipped", 0)
    correct_rows = [row for row in rows if row["candidate_type"] == "correct_bt"]
    correct_sim_rate = mean(as_int(row, "sim_success") for row in correct_rows)
    best_is_correct = mean(1 if row["best_candidate_type"] == "correct_bt" else 0 for row in comparisons)
    alt_wins = [row for row in comparisons if row["best_candidate_type"] != "correct_bt"]

    candidate_table = markdown_table(
        [
            "Candidate",
            "Done",
            "Symbolic success",
            "Sim success",
            "Mean score",
            "Mean pos error",
            "Mean displacement",
        ],
        [
            [
                row["candidate_type"],
                row["done_count"],
                pct(row["symbolic_success_rate"]),
                pct(row["sim_success_rate"]) if row["sim_success_rate"] != "" else "N/A",
                f"{row['mean_score']:.3f}",
                f"{row['mean_final_position_error']:.4f}" if row["mean_final_position_error"] != "" else "N/A",
                f"{row['mean_object_displacement_error']:.4f}"
                if row["mean_object_displacement_error"] != ""
                else "N/A",
            ]
            for row in candidate_rows
        ],
    )

    failed_table = markdown_table(
        [
            "Task",
            "State",
            "Target",
            "Pos error",
            "Displacement",
            "Contact proxy",
            "Score",
        ],
        [
            [
                row["task_id"],
                row["initial_state_id"],
                row["target_predicate"],
                row["final_position_error"],
                row["object_displacement_error"],
                row["contact_violation_proxy"],
                row["score"],
            ]
            for row in failures
        ],
    )

    task_focus = []
    for row in task_rows:
        if row["candidate_type"] != "correct_bt":
            continue
        task_focus.append(
            [
                row["task_id"],
                row["done_count"],
                pct(row["sim_success_rate"]) if row["sim_success_rate"] != "" else "N/A",
                f"{row['mean_score']:.3f}",
                f"{row['mean_final_position_error']:.4f}" if row["mean_final_position_error"] != "" else "N/A",
                f"{row['mean_object_displacement_error']:.4f}"
                if row["mean_object_displacement_error"] != ""
                else "N/A",
            ]
        )

    return "\n".join(
        [
            "# V1 Failure Analysis",
            "",
            "## Completion",
            "",
            f"- Done simulation rows: {total_done}",
            f"- Skipped invalid rows: {total_skipped}",
            f"- Pending rows: {status_counts.get('pending', 0)}",
            "",
            "## Main Finding",
            "",
            f"- `correct_bt` succeeds in simulation on {pct(correct_sim_rate)} of cases.",
            f"- `correct_bt` is still the highest-scoring candidate in {pct(best_is_correct)} of task-state groups.",
            f"- Alternative candidates beat `correct_bt` in {len(alt_wins)} groups.",
            "",
            "This means the V1 benchmark is complete and useful as an end-to-end validation, but it is not yet hard enough to separate symbolic and simulation-aware selection. The selector already chooses the oracle candidate on this task set.",
            "",
            "## Candidate-Type Summary",
            "",
            candidate_table,
            "",
            "## Correct BT by Task",
            "",
            markdown_table(
                ["Task", "Done", "Sim success", "Mean score", "Mean pos error", "Mean displacement"],
                task_focus,
            ),
            "",
            "## Failed Correct BT Cases",
            "",
            failed_table if failures else "No failed `correct_bt` cases.",
            "",
            "## V2 Task Direction",
            "",
            "- Add tasks where multiple BTs are symbolically valid but physically different.",
            "- Prefer cluttered placement, stacked supports, constrained retrieval, and occluded-object cases.",
            "- Make simulation metrics decisive: final position error, unrelated displacement, and contact violation should affect the oracle ranking.",
            "- Keep the current V1 as the reproducible pipeline sanity benchmark.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze V1 supported_by simulation failures.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--candidate-summary", type=Path, default=DEFAULT_CANDIDATE_SUMMARY)
    parser.add_argument("--task-candidate-summary", type=Path, default=DEFAULT_TASK_CANDIDATE_SUMMARY)
    parser.add_argument("--failed-correct", type=Path, default=DEFAULT_FAILED_CORRECT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_csv(args.input)
    candidate_rows = candidate_summary(rows)
    task_rows = task_candidate_summary(rows)
    failures = failed_correct_cases(rows)
    comparisons = compare_correct_with_alternatives(rows)

    write_csv(
        args.candidate_summary,
        candidate_rows,
        [
            "candidate_type",
            "count",
            "done_count",
            "skipped_count",
            "symbolic_success_rate",
            "sim_success_rate",
            "mean_score",
            "mean_final_position_error",
            "mean_object_displacement_error",
            "contact_violation_rate",
        ],
    )
    write_csv(
        args.task_candidate_summary,
        task_rows,
        [
            "task_id",
            "candidate_type",
            "count",
            "done_count",
            "skipped_count",
            "symbolic_success_rate",
            "sim_success_rate",
            "mean_score",
            "mean_final_position_error",
            "mean_object_displacement_error",
            "contact_violation_rate",
        ],
    )
    write_csv(
        args.failed_correct,
        failures,
        [
            "task_id",
            "initial_state_id",
            "target_predicate",
            "moved_object",
            "support_object",
            "symbolic_success",
            "sim_success",
            "final_position_error",
            "object_displacement_error",
            "contact_violation_proxy",
            "score",
        ],
    )
    args.report.write_text(
        make_report(rows, candidate_rows, task_rows, failures, comparisons),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "result": "success",
                "input": str(args.input),
                "candidate_summary": str(args.candidate_summary),
                "task_candidate_summary": str(args.task_candidate_summary),
                "failed_correct": str(args.failed_correct),
                "report": str(args.report),
                "failed_correct_count": len(failures),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
