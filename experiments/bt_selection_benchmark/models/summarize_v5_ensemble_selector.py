#!/usr/bin/env python3
"""Evaluate V5 ensemble BT selector."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_EVALUATIONS = Path("experiments/bt_selection_benchmark/results/learned_selector_dataset_v3a.csv")
DEFAULT_CHOICES = Path("experiments/bt_selection_benchmark/results/v4b_transformer_selector_choices.csv")
DEFAULT_SUMMARY = Path("experiments/bt_selection_benchmark/results/v5_ensemble_selector_summary.csv")
DEFAULT_CHOICES_OUT = Path("experiments/bt_selection_benchmark/results/v5_ensemble_selector_choices.csv")
DEFAULT_SCORED = Path("experiments/bt_selection_benchmark/results/v5_ensemble_selector_scored_candidates.csv")
DEFAULT_REPORT = Path("experiments/bt_selection_benchmark/results/v5_ensemble_selector_report.md")

DEPLOYABLE_VOTE_WEIGHTS = {
    "feature_only": 0.30,
    "transformer_fused": 0.35,
    "transformer_only": 0.15,
    "symbolic_only": 0.10,
    "shortest_tree": 0.05,
}
VOTE_WEIGHT = 0.55
SYMBOLIC_WEIGHT = 0.20
SIMULATION_WEIGHT = 0.25

def numeric(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)

def true_score(frame: pd.DataFrame) -> pd.Series:
    return (100 * numeric(frame, "sim_success") + 50 * numeric(frame, "symbolic_success") + 20 * numeric(frame, "goal_satisfaction") - 10 * numeric(frame, "final_position_error") - 5 * numeric(frame, "object_displacement_error") - 10 * numeric(frame, "contact_violation_proxy") - 0.5 * numeric(frame, "tree_size") - 0.3 * numeric(frame, "tree_depth"))

def symbolic_score(frame: pd.DataFrame) -> pd.Series:
    return (50 * numeric(frame, "symbolic_success") + 20 * numeric(frame, "goal_satisfaction") + 15 * numeric(frame, "precondition_coverage") - 10 * numeric(frame, "invalid_action_count") - 5 * numeric(frame, "condition_failure_count") - 0.5 * numeric(frame, "tree_size") - 0.3 * numeric(frame, "tree_depth") - 0.2 * numeric(frame, "bt_ticks") - 0.5 * numeric(frame, "action_count"))

def simulation_score(frame: pd.DataFrame) -> pd.Series:
    return (100 * numeric(frame, "sim_success") - 10 * numeric(frame, "final_position_error") - 5 * numeric(frame, "object_displacement_error") - 10 * numeric(frame, "contact_violation_proxy"))

def minmax_by_group(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
    mins = values.groupby(frame["selector_group_id"]).transform("min")
    maxs = values.groupby(frame["selector_group_id"]).transform("max")
    denom = (maxs - mins).replace(0, np.nan)
    return ((values - mins) / denom).fillna(0.0)

def parse_group(group_id: str) -> tuple[str, str, str]:
    parts = str(group_id).split("::")
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    return "", "", str(group_id)

def selector_votes(choices: pd.DataFrame) -> dict[tuple[str, str], dict[str, float]]:
    votes: dict[tuple[str, str], dict[str, float]] = {}
    for _, row in choices.iterrows():
        selector = str(row.get("selector", ""))
        if selector not in DEPLOYABLE_VOTE_WEIGHTS:
            continue
        key = (str(row["selector_group_id"]), str(row["selected_candidate"]))
        votes.setdefault(key, {})[selector] = float(DEPLOYABLE_VOTE_WEIGHTS[selector])
    return votes

def add_v5_scores(df: pd.DataFrame, choices: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "selector_group_id" not in out.columns:
        out["selector_group_id"] = out.apply(lambda row: str(row.get("benchmark", "")) + "::" + str(row["initial_state_id"]) + "::" + str(row["task_id"]), axis=1)
    out["true_score"] = true_score(out)
    out["symbolic_reliability_score"] = symbolic_score(out)
    out["simulation_reliability_score"] = simulation_score(out)
    out["symbolic_reliability_norm"] = minmax_by_group(out, "symbolic_reliability_score")
    out["simulation_reliability_norm"] = minmax_by_group(out, "simulation_reliability_score")
    votes = selector_votes(choices)
    vote_scores = []
    vote_details = []
    for _, row in out.iterrows():
        detail = votes.get((str(row["selector_group_id"]), str(row["candidate_id"])), {})
        vote_scores.append(sum(detail.values()))
        vote_details.append(";".join(name + ":" + format(weight, ".2f") for name, weight in sorted(detail.items())))
    out["selector_vote_score"] = vote_scores
    out["selector_vote_details"] = vote_details
    out["v5_ensemble_score"] = VOTE_WEIGHT * out["selector_vote_score"] + SYMBOLIC_WEIGHT * out["symbolic_reliability_norm"] + SIMULATION_WEIGHT * out["simulation_reliability_norm"]
    return out

def evaluate_selector(df: pd.DataFrame, score_col: str, selector: str) -> tuple[dict, pd.DataFrame]:
    rows = []
    for group_id, group in df.groupby("selector_group_id", sort=False):
        selected = group.sort_values(score_col, ascending=False).iloc[0]
        oracle = group.sort_values("true_score", ascending=False).iloc[0]
        benchmark, initial_state_id, task_id = parse_group(group_id)
        rows.append({
            "selector_group_id": group_id,
            "benchmark": benchmark,
            "task_id": task_id,
            "initial_state_id": initial_state_id,
            "selected_candidate": selected.get("candidate_id", ""),
            "oracle_candidate": oracle.get("candidate_id", ""),
            "selected_sim_success": float(selected.get("sim_success", 0)),
            "selected_true_score": float(selected["true_score"]),
            "oracle_true_score": float(oracle["true_score"]),
            "regret": float(oracle["true_score"] - selected["true_score"]),
            "selected_v5_ensemble_score": float(selected.get("v5_ensemble_score", 0)),
            "selector_vote_score": float(selected.get("selector_vote_score", 0)),
            "symbolic_reliability_norm": float(selected.get("symbolic_reliability_norm", 0)),
            "simulation_reliability_norm": float(selected.get("simulation_reliability_norm", 0)),
            "selector_vote_details": selected.get("selector_vote_details", ""),
            "selector": selector,
        })
    choices = pd.DataFrame(rows)
    return {
        "selector": selector,
        "groups": int(len(choices)),
        "success": float(choices["selected_sim_success"].mean()),
        "mean_selected_true_score": float(choices["selected_true_score"].mean()),
        "mean_regret": float(choices["regret"].mean()),
        "pairwise_accuracy": float("nan"),
        "pairwise_roc_auc": float("nan"),
        "pairwise_examples": 0,
    }, choices

def write_report(path: Path, summary: pd.DataFrame, choices_path: Path, scored_path: Path) -> None:
    lines = [
        "# V5 Ensemble BT Selector Report",
        "",
        "## Method",
        "",
        "V5 is the proposed final selector. It combines deployable selector agreement with symbolic and simulation reliability scores.",
        "Oracle is not used as an input; it is used only as the evaluation upper bound for regret.",
        "",
        "Formula:",
        "score_v5(c) = 0.55 * selector_vote_score(c) + 0.20 * normalized_symbolic_reliability(c) + 0.25 * normalized_simulation_reliability(c)",
        "",
        "Selector vote weights: feature_only=0.30, transformer_fused=0.35, transformer_only=0.15, symbolic_only=0.10, shortest_tree=0.05.",
        "",
        "## Selector Comparison",
        "",
        summary.to_csv(index=False),
        "",
        "## Outputs",
        "",
        "Choices: " + str(choices_path),
        "Scored candidates: " + str(scored_path),
    ]
    path.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluations", type=Path, default=DEFAULT_EVALUATIONS)
    parser.add_argument("--choices", type=Path, default=DEFAULT_CHOICES)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--choices-output", type=Path, default=DEFAULT_CHOICES_OUT)
    parser.add_argument("--scored-output", type=Path, default=DEFAULT_SCORED)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    evaluations = pd.read_csv(args.evaluations)
    choices = pd.read_csv(args.choices)
    scored = add_v5_scores(evaluations, choices)
    row, v5_choices = evaluate_selector(scored, "v5_ensemble_score", "v5_ensemble")
    existing_summary = pd.read_csv("experiments/bt_selection_benchmark/results/v4b_transformer_selector_summary.csv")
    summary = pd.concat([existing_summary, pd.DataFrame([row])], ignore_index=True, sort=False)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.summary_output, index=False)
    v5_choices.to_csv(args.choices_output, index=False)
    scored.to_csv(args.scored_output, index=False)
    write_report(args.report_output, summary, args.choices_output, args.scored_output)
    print(json.dumps({"result": "success", "rows": int(len(scored)), "groups": int(scored["selector_group_id"].nunique()), "summary_output": str(args.summary_output), "choices_output": str(args.choices_output), "scored_output": str(args.scored_output), "report_output": str(args.report_output), "v5": row}, indent=2))

if __name__ == "__main__":
    main()
