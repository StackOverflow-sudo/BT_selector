#!/usr/bin/env python3
"""Run V3C generalization and ablation studies for the learned BT selector."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import train_v3b_pairwise_selector as v3b  # noqa: E402


SYMBOLIC_FEATURES = {
    "symbolic_success",
    "goal_satisfaction",
    "bt_ticks",
    "action_count",
    "condition_failure_count",
    "invalid_action_count",
    "precondition_coverage",
    "support_stability",
    "validation_error_count",
}

STRUCTURE_FEATURES = {
    "tree_size",
    "tree_depth",
    "bt_ticks",
    "action_count",
    "condition_failure_count",
}

TASK_WORLD_FEATURES = {
    "initial_timestep",
    "task_id",
    "initial_state_id",
    "task_instruction",
    "target_predicate",
    "moved_object",
    "support_object",
}


ABLATIONS = {
    "full": None,
    "no_candidate_type": {"drop": {"candidate_type"}},
    "no_symbolic_features": {"drop": SYMBOLIC_FEATURES},
    "no_benchmark_id": {"drop": {"source_benchmark", "benchmark"}},
    "task_world_only": {"keep": TASK_WORLD_FEATURES},
    "structure_only": {"keep": STRUCTURE_FEATURES},
}


def feature_subset(feature_cols: list[str], ablation: str) -> list[str]:
    rule = ABLATIONS[ablation]
    if rule is None:
        return list(feature_cols)
    if "keep" in rule:
        keep = rule["keep"]
        return [c for c in feature_cols if c in keep]
    drop = rule.get("drop", set())
    return [c for c in feature_cols if c not in drop]


def split_mixed_group_cv(df: pd.DataFrame, n_splits: int = 5):
    sk = v3b.load_sklearn()
    groups = df["selector_group_id"].astype(str).to_numpy()
    unique_groups = np.unique(groups)
    split_count = min(n_splits, len(unique_groups))
    if split_count < 2:
        return []
    splitter = sk["GroupKFold"](n_splits=split_count)
    return list(splitter.split(df, df["sim_success"], groups))


def split_leave_one_column(df: pd.DataFrame, column: str):
    splits = []
    for value in sorted(df[column].dropna().astype(str).unique()):
        test_idx = df.index[df[column].astype(str) == value].to_numpy()
        train_idx = df.index[df[column].astype(str) != value].to_numpy()
        if len(train_idx) and len(test_idx):
            splits.append((train_idx, test_idx, value))
    return splits


def pairwise_eval_for_frame(scored: pd.DataFrame, sk) -> tuple[float, float, int]:
    all_labels = []
    all_scores = []
    examples = 0
    for _, group in scored.groupby("selector_group_id", sort=False):
        ordered = group.reset_index(drop=True)
        for i in range(len(ordered)):
            for j in range(i + 1, len(ordered)):
                delta_true = float(ordered.loc[i, "true_score"] - ordered.loc[j, "true_score"])
                if abs(delta_true) <= 1e-9:
                    continue
                delta_pred = float(
                    ordered.loc[i, "learned_pairwise_score"]
                    - ordered.loc[j, "learned_pairwise_score"]
                )
                all_labels.append(1 if delta_true > 0 else 0)
                all_scores.append(delta_pred)
                all_labels.append(1 if delta_true < 0 else 0)
                all_scores.append(-delta_pred)
                examples += 2
    if not all_labels:
        return float("nan"), float("nan"), 0
    labels = np.array(all_labels)
    scores = np.array(all_scores)
    accuracy = float(sk["accuracy_score"](labels, scores >= 0))
    try:
        auc = float(sk["roc_auc_score"](labels, scores))
    except Exception:
        auc = float("nan")
    return accuracy, auc, examples


def train_predict_pairwise(
    df: pd.DataFrame,
    train_idx,
    test_idx,
    feature_cols: list[str],
    numeric_cols: list[str],
    categorical_cols: list[str],
    sk,
) -> pd.DataFrame:
    train = df.iloc[train_idx].copy().reset_index(drop=True)
    test = df.iloc[test_idx].copy().reset_index(drop=True)

    preprocessor = v3b.make_preprocessor(numeric_cols, categorical_cols, sk)
    x_train = preprocessor.fit_transform(train[feature_cols])
    pair_x, pair_y = v3b.make_pairwise_examples(x_train, train, sk)

    test["learned_pairwise_score"] = 0.0
    if pair_x is None or len(np.unique(pair_y)) < 2:
        return test

    model = sk["LogisticRegression"](max_iter=2000, class_weight="balanced")
    model.fit(pair_x, pair_y)

    x_test = preprocessor.transform(test[feature_cols])
    single_scores = x_test @ model.coef_.reshape(-1, 1)
    test["learned_pairwise_score"] = np.asarray(single_scores).ravel()
    return test


def evaluate_splits(
    df: pd.DataFrame,
    splits,
    split_mode: str,
    ablation: str,
    base_feature_cols: list[str],
    sk,
) -> tuple[dict, pd.DataFrame]:
    feature_cols = feature_subset(base_feature_cols, ablation)
    numeric_cols = [c for c in feature_cols if pd.api.types.is_numeric_dtype(df[c])]
    categorical_cols = [c for c in feature_cols if c not in numeric_cols]
    if not feature_cols:
        raise ValueError(f"No features left for ablation: {ablation}")

    scored_frames = []
    split_labels = []
    for split in splits:
        if len(split) == 2:
            train_idx, test_idx = split
            label = f"fold_{len(split_labels)}"
        else:
            train_idx, test_idx, label = split
        scored = train_predict_pairwise(
            df,
            train_idx,
            test_idx,
            feature_cols,
            numeric_cols,
            categorical_cols,
            sk,
        )
        scored["split_label"] = str(label)
        scored_frames.append(scored)
        split_labels.append(str(label))

    if not scored_frames:
        empty = pd.DataFrame()
        return {
            "split_mode": split_mode,
            "ablation": ablation,
            "splits": 0,
            "groups": 0,
            "success": float("nan"),
            "mean_selected_true_score": float("nan"),
            "mean_regret": float("nan"),
            "pairwise_accuracy": float("nan"),
            "pairwise_roc_auc": float("nan"),
            "pairwise_examples": 0,
            "feature_count": len(feature_cols),
        }, empty

    scored_all = pd.concat(scored_frames, ignore_index=True)
    row, choices = v3b.evaluate_selector(scored_all, "learned_pairwise_score")
    pair_acc, pair_auc, pair_examples = pairwise_eval_for_frame(scored_all, sk)
    row.update(
        {
            "split_mode": split_mode,
            "ablation": ablation,
            "splits": len(split_labels),
            "pairwise_accuracy": pair_acc,
            "pairwise_roc_auc": pair_auc,
            "pairwise_examples": pair_examples,
            "feature_count": len(feature_cols),
        }
    )
    choices["split_mode"] = split_mode
    choices["ablation"] = ablation
    return row, choices


def write_report(path: Path, summary: pd.DataFrame, choices_path: Path, feature_cols: list[str]) -> None:
    lines = [
        "# V3C Generalization and Ablation Report",
        "",
        "## Method",
        "",
        "V3C evaluates the V3B pairwise BT ranker under stricter splits and feature ablations.",
        "Simulation metrics are still used only to compute supervision scores, not as model inputs.",
        "",
        "Split modes:",
        "",
        "- `mixed_group_cv`: grouped cross-validation over task/state groups.",
        "- `leave_one_benchmark_out`: train on two benchmarks and test on the held-out benchmark.",
        "- `leave_one_task_out`: train on all other tasks and test on the held-out task.",
        "",
        "Ablations:",
        "",
        "- `full`: all non-leaky pre-simulation features.",
        "- `no_candidate_type`: removes explicit candidate identity.",
        "- `no_symbolic_features`: removes symbolic execution metrics.",
        "- `no_benchmark_id`: removes benchmark/source identifiers.",
        "- `task_world_only`: keeps only task/world identifiers.",
        "- `structure_only`: keeps only BT structural metrics.",
        "",
        "## Summary",
        "",
        summary.to_csv(index=False),
        "",
        "## Base Feature Columns",
        "",
        ", ".join(feature_cols),
        "",
        "## Outputs",
        "",
        f"- Choices: `{choices_path}`",
        "",
        "## Interpretation",
        "",
        "The most important rows are `leave_one_benchmark_out/full` and `leave_one_benchmark_out/no_candidate_type`. They indicate whether the learned selector generalizes beyond memorized candidate names or benchmark-specific patterns.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="experiments/bt_selection_benchmark/results/learned_selector_dataset_v3a.csv")
    parser.add_argument("--summary-output", default="experiments/bt_selection_benchmark/results/v3c_generalization_ablation_summary.csv")
    parser.add_argument("--choices-output", default="experiments/bt_selection_benchmark/results/v3c_generalization_ablation_choices.csv")
    parser.add_argument("--report-output", default="experiments/bt_selection_benchmark/results/v3c_generalization_ablation_report.md")
    args = parser.parse_args()

    sk = v3b.load_sklearn()
    df = pd.read_csv(args.input)
    df = df[df["sim_success"].isin([0, 1])].copy()
    df["sim_success"] = df["sim_success"].astype(int)
    df["true_score"] = df.apply(v3b.true_score, axis=1)
    df = df.reset_index(drop=True)

    base_feature_cols, _, _ = v3b.choose_columns(df)
    split_sets = [
        ("mixed_group_cv", split_mixed_group_cv(df)),
        ("leave_one_benchmark_out", split_leave_one_column(df, "source_benchmark")),
        ("leave_one_task_out", split_leave_one_column(df, "task_id")),
    ]

    rows = []
    choices = []
    for split_mode, splits in split_sets:
        for ablation in ABLATIONS:
            row, choice = evaluate_splits(df, splits, split_mode, ablation, base_feature_cols, sk)
            rows.append(row)
            if not choice.empty:
                choices.append(choice)

    summary = pd.DataFrame(rows)[
        [
            "split_mode",
            "ablation",
            "splits",
            "groups",
            "success",
            "mean_selected_true_score",
            "mean_regret",
            "pairwise_accuracy",
            "pairwise_roc_auc",
            "pairwise_examples",
            "feature_count",
        ]
    ]

    summary_output = Path(args.summary_output)
    choices_output = Path(args.choices_output)
    report_output = Path(args.report_output)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_output, index=False)
    if choices:
        pd.concat(choices, ignore_index=True).to_csv(choices_output, index=False)
    else:
        pd.DataFrame().to_csv(choices_output, index=False)
    write_report(report_output, summary, choices_output, base_feature_cols)

    print(
        json.dumps(
            {
                "result": "success",
                "input": args.input,
                "rows": int(len(df)),
                "groups": int(df["selector_group_id"].nunique()),
                "summary_output": str(summary_output),
                "choices_output": str(choices_output),
                "report_output": str(report_output),
                "experiments": int(len(summary)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
