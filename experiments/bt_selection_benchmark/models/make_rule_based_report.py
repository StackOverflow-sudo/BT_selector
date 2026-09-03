from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


MODEL_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = MODEL_DIR.parent
RESULTS_DIR = EXPERIMENT_DIR / "results"
DEFAULT_SELECTOR_SUMMARY = RESULTS_DIR / "summary_by_selector.csv"
DEFAULT_RULE_SUMMARY = RESULTS_DIR / "rule_based_selector_summary.csv"
DEFAULT_RULE_CHOICES = RESULTS_DIR / "rule_based_selector_choices.csv"
DEFAULT_OUTPUT = RESULTS_DIR / "rule_based_selector_report.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def as_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    if value in {"", None}:
        return default
    return float(value)


def pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        out.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(out)


def baseline_rows(summary: list[dict[str, str]]) -> list[list[Any]]:
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


def rule_rows(summary: list[dict[str, str]]) -> list[list[Any]]:
    rows = []
    for row in summary:
        sim = row.get("selected_sim_success_rate", "")
        rows.append(
            [
                row["selector"],
                row["group_count"],
                pct(as_float(row, "selected_symbolic_success_rate")),
                pct(float(sim)) if sim not in {"", None} else "N/A",
                pct(as_float(row, "selected_sim_success_coverage")) if row.get("selected_sim_success_coverage", "") not in {"", None} else "N/A",
                f"{as_float(row, 'selected_goal_satisfaction'):.3f}",
                f"{as_float(row, 'mean_selected_model_score'):.3f}",
                f"{as_float(row, 'mean_selected_true_score'):.3f}",
                f"{as_float(row, 'mean_regret'):.3f}",
            ]
        )
    return rows


def choice_preview(choices: list[dict[str, str]], limit: int = 8) -> list[list[Any]]:
    return [
        [
            row["selector"],
            row["task_id"],
            row["initial_state_id"],
            row["selected_candidate_type"],
            row["oracle_candidate_type"],
            row["regret"],
        ]
        for row in choices[:limit]
    ]


def make_report(
    selector_summary: list[dict[str, str]],
    rule_summary: list[dict[str, str]],
    rule_choices: list[dict[str, str]],
    selector_summary_path: Path,
    rule_summary_path: Path,
    rule_choices_path: Path,
) -> str:
    by_selector = {row["selector"]: row for row in selector_summary}
    random_row = by_selector.get("random_expected")
    shortest_row = by_selector.get("shortest_tree")
    symbolic_row = by_selector.get("symbolic_success")
    oracle_row = by_selector.get("oracle")
    rule_symbolic = next(
        (row for row in rule_summary if row["selector"] == "rule_based_symbolic"),
        None,
    )
    rule_simulation = next(
        (row for row in rule_summary if row["selector"] == "rule_based_simulation"),
        None,
    )

    interpretation = []
    next_step = "Populate simulation metrics and add harder constrained-packing/retrieval tasks so that symbolic and simulation-aware scoring can be compared meaningfully."
    if random_row and rule_symbolic:
        delta = as_float(rule_symbolic, "selected_symbolic_success_rate") - as_float(
            random_row, "selected_success_rate"
        )
        interpretation.append(
            f"- The symbolic rule-based selector improves over uniform random selection by {pct(delta)} symbolic success."
        )
    if shortest_row:
        interpretation.append(
            f"- The shortest-tree heuristic performs poorly in this benchmark ({pct(as_float(shortest_row, 'selected_success_rate'))} success), showing that smaller BTs are not necessarily reliable."
        )
    if symbolic_row and rule_symbolic:
        regret_delta = as_float(symbolic_row, "mean_regret") - as_float(
            rule_symbolic, "mean_regret"
        )
        interpretation.append(
            f"- Compared with selecting any symbolically successful BT, the weighted selector reduces mean regret by {regret_delta:.3f}."
        )
    if oracle_row and rule_symbolic:
        symbolic_regret = as_float(rule_symbolic, "mean_regret")
        if symbolic_regret <= 1e-9:
            interpretation.append(
                "- The symbolic rule-based selector matches the oracle upper bound on this benchmark."
            )
        else:
            interpretation.append(
                f"- The symbolic rule-based selector does not match the oracle on this benchmark; its mean regret is {symbolic_regret:.3f}."
            )
    if rule_simulation:
        sim_coverage = as_float(rule_simulation, "selected_sim_success_coverage")
        sim_count = int(as_float(rule_simulation, "selected_sim_success_count"))
        group_count = int(as_float(rule_simulation, "group_count"))
        if sim_count == 0:
            interpretation.append(
                "- Simulation-aware scoring is implemented, but no selected cases have completed simulation metrics yet, so it is not distinguishable from symbolic scoring."
            )
        elif sim_coverage < 1.0:
            interpretation.append(
                f"- Simulation metrics are partially populated for selected cases ({sim_count}/{group_count}, {pct(sim_coverage)} coverage). The simulation-aware model score has started to differ, but the comparison is not final until the remaining Isaac Gym jobs finish."
            )
            next_step = "Finish the remaining Isaac Gym jobs, then rerun `summarize_v1_supported_by_with_sim.sh` before making final simulation-aware claims."
        else:
            sim_regret = as_float(rule_simulation, "mean_regret")
            symbolic_regret = as_float(rule_symbolic, "mean_regret") if rule_symbolic else 0.0
            if symbolic_regret > sim_regret + 1e-9:
                interpretation.append(
                    f"- Simulation metrics are fully populated and reduce mean regret from {symbolic_regret:.3f} to {sim_regret:.3f}. This indicates that simulation-aware scoring is helping choose physically better BT candidates."
                )
                next_step = "Analyze which placement strategies the simulation-aware selector prefers, then turn the V2B result into paper tables."
            else:
                interpretation.append(
                    "- Simulation metrics are fully populated for selected cases. If symbolic and simulation-aware choices still match, the next useful step is to add harder tasks where physical execution can disambiguate symbolically valid BTs."
                )
                next_step = "Add harder constrained-packing/retrieval tasks so that symbolic and simulation-aware scoring can be compared on cases where physical feasibility matters."

    return "\n".join(
        [
            "# Rule-Based Selector Report",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Inputs",
            "",
            f"- Selector baseline summary: `{selector_summary_path}`",
            f"- Rule-based summary: `{rule_summary_path}`",
            f"- Rule-based choices: `{rule_choices_path}`",
            "",
            "## Method",
            "",
            "The selector ranks candidate behavior trees for the same task and initial state. The symbolic version uses BT structure and KIOS execution metrics; the simulation-aware version adds available LL4MA/Isaac Gym metrics.",
            "",
            "Symbolic score:",
            "",
            "```text",
            "50 * symbolic_success",
            "+ 20 * goal_satisfaction",
            "+ 15 * precondition_coverage",
            "- 10 * invalid_action_count",
            "- 5  * condition_failure_count",
            "- 0.5 * tree_size",
            "- 0.3 * tree_depth",
            "- 0.2 * bt_ticks",
            "- 0.5 * action_count",
            "```",
            "",
            "Simulation-aware additions:",
            "",
            "```text",
            "+ 100 * sim_success",
            "- 10 * final_position_error",
            "- 5  * object_displacement_error",
            "- 10 * contact_violation_proxy",
            "```",
            "",
            "## Existing Selector Baselines",
            "",
            markdown_table(
                [
                    "Selector",
                    "Groups",
                    "Success",
                    "Goal satisfaction",
                    "Mean selected score",
                    "Mean regret",
                ],
                baseline_rows(selector_summary),
            ),
            "",
            "## Proposed Rule-Based Selectors",
            "",
            markdown_table(
                [
                    "Selector",
                    "Groups",
                    "Symbolic success",
                    "Simulation success",
                    "Sim coverage",
                    "Goal satisfaction",
                    "Model score",
                    "True score",
                    "Regret",
                ],
                rule_rows(rule_summary),
            ),
            "",
            "## Choice Preview",
            "",
            markdown_table(
                [
                    "Selector",
                    "Task",
                    "Initial state",
                    "Selected",
                    "Oracle",
                    "Regret",
                ],
                choice_preview(rule_choices),
            ),
            "",
            "## Interpretation",
            "",
            "\n".join(interpretation),
            "",
            "## Next Step",
            "",
            next_step,
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a report for the rule-based selector.")
    parser.add_argument("--selector-summary", type=Path, default=DEFAULT_SELECTOR_SUMMARY)
    parser.add_argument("--rule-summary", type=Path, default=DEFAULT_RULE_SUMMARY)
    parser.add_argument("--rule-choices", type=Path, default=DEFAULT_RULE_CHOICES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selector_summary = read_csv(args.selector_summary)
    rule_summary = read_csv(args.rule_summary)
    rule_choices = read_csv(args.rule_choices)
    report = make_report(
        selector_summary,
        rule_summary,
        rule_choices,
        args.selector_summary,
        args.rule_summary,
        args.rule_choices,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "result": "success",
                "output": str(args.output),
                "baseline_selectors": len(selector_summary),
                "rule_selectors": len(rule_summary),
                "choice_rows": len(rule_choices),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
