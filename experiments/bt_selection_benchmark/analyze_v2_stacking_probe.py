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
DEFAULT_INPUT = RESULTS_DIR / "bt_candidate_evaluations_v2_stacking_probe_with_sim.csv"
DEFAULT_TASK_SUMMARY = RESULTS_DIR / "summary_by_task_v2_stacking_probe_with_sim.csv"
DEFAULT_CANDIDATE_SUMMARY = RESULTS_DIR / "summary_by_candidate_type_v2_stacking_probe_with_sim.csv"
DEFAULT_REPORT = RESULTS_DIR / "v2_stacking_probe_analysis.md"


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
    grouped: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)
    return dict(grouped)


def summarize(rows: list[dict[str, str]]) -> dict[str, Any]:
    done = [row for row in rows if row.get("simulation_status") == "done"]
    sim_values = [as_int(row, "sim_success") for row in done]
    return {
        "count": len(rows),
        "done_count": len(done),
        "skipped_count": sum(1 for row in rows if row.get("simulation_status") == "skipped"),
        "symbolic_success_rate": round(mean(as_int(row, "symbolic_success") for row in rows), 6),
        "sim_success_rate": round(mean(sim_values), 6) if sim_values else "",
        "mean_score": round(mean(as_float(row, "score") for row in rows), 6),
        "mean_final_position_error": round(mean(as_float(row, "final_position_error") for row in done), 6)
        if done
        else "",
        "mean_object_displacement_error": round(
            mean(as_float(row, "object_displacement_error") for row in done), 6
        )
        if done
        else "",
        "contact_violation_rate": round(mean(as_int(row, "contact_violation_proxy") for row in done), 6)
        if done
        else "",
    }


def task_summary(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for (task_id,), task_rows in sorted(group_by(rows, ("task_id",)).items()):
        correct_rows = [row for row in task_rows if row["candidate_type"] == "correct_bt"]
        correct_summary = summarize(correct_rows)
        all_summary = summarize(task_rows)
        task_class = "stacking" if task_id.startswith("stack_") else "shelf_placement"
        out.append(
            {
                "task_id": task_id,
                "task_class": task_class,
                "correct_done_count": correct_summary["done_count"],
                "correct_sim_success_rate": correct_summary["sim_success_rate"],
                "correct_mean_score": correct_summary["mean_score"],
                "correct_mean_final_position_error": correct_summary["mean_final_position_error"],
                "correct_mean_object_displacement_error": correct_summary["mean_object_displacement_error"],
                "all_candidate_sim_success_rate": all_summary["sim_success_rate"],
                "all_candidate_mean_score": all_summary["mean_score"],
            }
        )
    return out


def candidate_summary(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for (candidate_type,), candidate_rows in sorted(group_by(rows, ("candidate_type",)).items()):
        summary = summarize(candidate_rows)
        summary["candidate_type"] = candidate_type
        out.append(summary)
    return out


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def make_report(rows: list[dict[str, str]], task_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]]) -> str:
    status = Counter(row.get("simulation_status", "") for row in rows)
    shelf_tasks = [row for row in task_rows if row["task_class"] == "shelf_placement"]
    stacking_tasks = [row for row in task_rows if row["task_class"] == "stacking"]
    shelf_success = mean(float(row["correct_sim_success_rate"]) for row in shelf_tasks)
    stacking_success = mean(float(row["correct_sim_success_rate"]) for row in stacking_tasks)
    hard_stacking = [row for row in stacking_tasks if float(row["correct_sim_success_rate"]) == 0.0]

    task_table = markdown_table(
        [
            "Task",
            "Class",
            "Correct sim success",
            "Correct mean score",
            "Mean pos error",
            "Mean displacement",
        ],
        [
            [
                row["task_id"],
                row["task_class"],
                pct(float(row["correct_sim_success_rate"])),
                f"{float(row['correct_mean_score']):.3f}",
                f"{float(row['correct_mean_final_position_error']):.4f}",
                f"{float(row['correct_mean_object_displacement_error']):.4f}",
            ]
            for row in task_rows
        ],
    )

    candidate_table = markdown_table(
        ["Candidate", "Done", "Symbolic success", "Sim success", "Mean score"],
        [
            [
                row["candidate_type"],
                row["done_count"],
                pct(float(row["symbolic_success_rate"])),
                pct(float(row["sim_success_rate"])) if row["sim_success_rate"] != "" else "N/A",
                f"{float(row['mean_score']):.3f}",
            ]
            for row in candidate_rows
        ],
    )

    return "\n".join(
        [
            "# V2 Stacking Probe Analysis",
            "",
            "## Completion",
            "",
            f"- Done simulation rows: {status.get('done', 0)}",
            f"- Skipped invalid rows: {status.get('skipped', 0)}",
            f"- Pending rows: {status.get('pending', 0)}",
            "",
            "## Main Finding",
            "",
            f"- Shelf-placement `correct_bt` simulation success: {pct(shelf_success)}.",
            f"- Movable-on-movable stacking `correct_bt` simulation success: {pct(stacking_success)}.",
            f"- Fully failing stacking tasks: {len(hard_stacking)}/{len(stacking_tasks)}.",
            "",
            "V2A confirms the V1 failure signal: shelf placement is physically reliable, while block-on-block stacking is usually symbolically valid but physically unreliable in Isaac Gym.",
            "",
            "## Task-Level Results",
            "",
            task_table,
            "",
            "## Candidate-Type Results",
            "",
            candidate_table,
            "",
            "## Interpretation",
            "",
            "- The current candidate library still makes `correct_bt` the oracle in every task-state group because alternatives are mostly wrong-object, wrong-support, redundant, or missing-precondition variants.",
            "- Simulation metrics now expose task difficulty: stacking has low physical success even when symbolic execution succeeds.",
            "- The next benchmark version should create competing BTs that are both symbolically valid but physically different, such as stable-support versus unstable-support strategies.",
            "",
            "## Next Step",
            "",
            "Implement V2B candidate types that intentionally compare physically stable and unstable symbolic strategies, then rerun selector comparison on those candidates.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze V2 stacking probe simulation results.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--task-summary", type=Path, default=DEFAULT_TASK_SUMMARY)
    parser.add_argument("--candidate-summary", type=Path, default=DEFAULT_CANDIDATE_SUMMARY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_csv(args.input)
    tasks = task_summary(rows)
    candidates = candidate_summary(rows)
    write_csv(
        args.task_summary,
        tasks,
        [
            "task_id",
            "task_class",
            "correct_done_count",
            "correct_sim_success_rate",
            "correct_mean_score",
            "correct_mean_final_position_error",
            "correct_mean_object_displacement_error",
            "all_candidate_sim_success_rate",
            "all_candidate_mean_score",
        ],
    )
    write_csv(
        args.candidate_summary,
        candidates,
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
    args.report.write_text(make_report(rows, tasks, candidates), encoding="utf-8")
    print(
        json.dumps(
            {
                "result": "success",
                "input": str(args.input),
                "task_summary": str(args.task_summary),
                "candidate_summary": str(args.candidate_summary),
                "report": str(args.report),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
