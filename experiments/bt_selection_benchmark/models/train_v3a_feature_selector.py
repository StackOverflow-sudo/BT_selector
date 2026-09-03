#!/usr/bin/env python3
"""Train and evaluate the V3A feature-based learned BT selector."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


LABEL_COLUMNS = {
    "sim_success",
    "final_position_error",
    "object_displacement_error",
    "contact_violation_proxy",
}

LEAKY_COLUMNS = LABEL_COLUMNS | {
    "score",
    "true_score",
    "oracle_score",
    "selected_score",
    "regret",
    "model_score",
    "label",
    "execution_result",
    "simulation_status",
    "status",
    "runtime_mode",
    "predicted_sim_success",
    "learned_score",
}

IDENTIFIER_COLUMNS = {
    "source_file",
    "case_id",
    "selector_group_id",
    "candidate_id",
    "simulation_output",
    "output",
    "result_path",
    "config_path",
    "job_path",
}


def load_sklearn():
    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
        from sklearn.model_selection import GroupKFold
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
    except Exception as exc:  # pragma: no cover - friendly runtime error
        raise RuntimeError(
            "scikit-learn is required for V3A. Install it in the project environment "
            "or run with an environment that already has sklearn."
        ) from exc

    return {
        "ColumnTransformer": ColumnTransformer,
        "SimpleImputer": SimpleImputer,
        "LogisticRegression": LogisticRegression,
        "accuracy_score": accuracy_score,
        "log_loss": log_loss,
        "roc_auc_score": roc_auc_score,
        "GroupKFold": GroupKFold,
        "Pipeline": Pipeline,
        "OneHotEncoder": OneHotEncoder,
        "StandardScaler": StandardScaler,
    }


def true_score(row: pd.Series) -> float:
    sim_success = float(row.get("sim_success", 0) or 0)
    final_position_error = float(row.get("final_position_error", 0) or 0)
    object_displacement_error = float(row.get("object_displacement_error", 0) or 0)
    contact_violation_proxy = float(row.get("contact_violation_proxy", 0) or 0)
    symbolic_success = float(row.get("symbolic_success", 0) or 0)
    goal_satisfaction = float(row.get("goal_satisfaction", 0) or 0)
    tree_size = float(row.get("tree_size", 0) or 0)
    tree_depth = float(row.get("tree_depth", 0) or 0)

    return (
        100 * sim_success
        + 50 * symbolic_success
        + 20 * goal_satisfaction
        - 10 * final_position_error
        - 5 * object_displacement_error
        - 10 * contact_violation_proxy
        - 0.5 * tree_size
        - 0.3 * tree_depth
    )


def choose_columns(df: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    forbidden = LEAKY_COLUMNS | IDENTIFIER_COLUMNS
    feature_cols = [c for c in df.columns if c not in forbidden]

    numeric_cols: list[str] = []
    categorical_cols: list[str] = []
    for col in feature_cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_cols.append(col)
        else:
            # Avoid exploding arbitrary long text columns such as full prompts.
            nunique = df[col].astype(str).nunique(dropna=True)
            if nunique <= max(100, len(df) // 2):
                categorical_cols.append(col)

    feature_cols = numeric_cols + categorical_cols
    return feature_cols, numeric_cols, categorical_cols


def make_model(numeric_cols: list[str], categorical_cols: list[str], sk):
    numeric_pipe = sk["Pipeline"](
        [
            ("imputer", sk["SimpleImputer"](strategy="median")),
            ("scaler", sk["StandardScaler"]()),
        ]
    )
    categorical_pipe = sk["Pipeline"](
        [
            ("imputer", sk["SimpleImputer"](strategy="most_frequent")),
            ("onehot", sk["OneHotEncoder"](handle_unknown="ignore")),
        ]
    )
    preprocessor = sk["ColumnTransformer"](
        [
            ("num", numeric_pipe, numeric_cols),
            ("cat", categorical_pipe, categorical_cols),
        ],
        remainder="drop",
    )
    return sk["Pipeline"](
        [
            ("features", preprocessor),
            ("model", sk["LogisticRegression"](max_iter=2000, class_weight="balanced")),
        ]
    )


def evaluate_selector(df: pd.DataFrame, score_col: str) -> dict[str, float]:
    choices = []
    for group_id, group in df.groupby("selector_group_id", sort=False):
        selected = group.sort_values(score_col, ascending=False).iloc[0]
        oracle = group.sort_values("true_score", ascending=False).iloc[0]
        choices.append(
            {
                "selector_group_id": group_id,
                "selected_candidate": selected.get("candidate_id", ""),
                "oracle_candidate": oracle.get("candidate_id", ""),
                "selected_sim_success": float(selected["sim_success"]),
                "selected_true_score": float(selected["true_score"]),
                "oracle_true_score": float(oracle["true_score"]),
                "regret": float(oracle["true_score"] - selected["true_score"]),
            }
        )

    choices_df = pd.DataFrame(choices)
    return {
        "groups": int(len(choices_df)),
        "success": float(choices_df["selected_sim_success"].mean()),
        "mean_selected_true_score": float(choices_df["selected_true_score"].mean()),
        "mean_regret": float(choices_df["regret"].mean()),
    }, choices_df


def baseline_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["learned_score"] = out["predicted_sim_success"]
    out["symbolic_score"] = (
        50 * pd.to_numeric(out.get("symbolic_success", 0), errors="coerce").fillna(0)
        + 20 * pd.to_numeric(out.get("goal_satisfaction", 0), errors="coerce").fillna(0)
        - 0.5 * pd.to_numeric(out.get("tree_size", 0), errors="coerce").fillna(0)
        - 0.3 * pd.to_numeric(out.get("tree_depth", 0), errors="coerce").fillna(0)
    )
    out["shortest_tree_score"] = -pd.to_numeric(out.get("tree_size", 0), errors="coerce").fillna(9999)
    return out


def write_report(path: Path, summary: pd.DataFrame, metrics: dict, feature_cols: list[str], choices_path: Path) -> None:
    lines = [
        "# V3A Feature-Based Learned BT Selector Report",
        "",
        "## Method",
        "",
        "V3A trains a lightweight feature-based selector. Isaac Gym simulation metrics are used as labels, not as model inputs.",
        "",
        "Prediction target:",
        "",
        "```text",
        "sim_success",
        "```",
        "",
        "Selector score:",
        "",
        "```text",
        "learned_score = P(sim_success | task, world, BT candidate features)",
        "```",
        "",
        "## Cross-Validation Metrics",
        "",
        f"- Rows: {metrics['rows']}",
        f"- Groups: {metrics['groups']}",
        f"- Positive labels: {metrics['positive_labels']}",
        f"- Negative labels: {metrics['negative_labels']}",
        f"- Accuracy: {metrics['accuracy']:.3f}",
        f"- ROC-AUC: {metrics['roc_auc']:.3f}" if not np.isnan(metrics["roc_auc"]) else "- ROC-AUC: n/a",
        f"- Log loss: {metrics['log_loss']:.3f}" if not np.isnan(metrics["log_loss"]) else "- Log loss: n/a",
        "",
        "## Selector Comparison",
        "",
        summary.to_csv(index=False),
        "",
        "## Feature Columns",
        "",
        ", ".join(feature_cols) if feature_cols else "No feature columns selected.",
        "",
        "## Outputs",
        "",
        f"- Choices: `{choices_path}`",
        "",
        "## Interpretation",
        "",
        "This is the first learned selector baseline. If it reduces regret relative to symbolic-only selection, it supports the claim that pre-simulation task/world/BT features can predict physical executability.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="experiments/bt_selection_benchmark/results/learned_selector_dataset_v3a.csv",
    )
    parser.add_argument(
        "--summary-output",
        default="experiments/bt_selection_benchmark/results/v3a_feature_selector_summary.csv",
    )
    parser.add_argument(
        "--choices-output",
        default="experiments/bt_selection_benchmark/results/v3a_feature_selector_choices.csv",
    )
    parser.add_argument(
        "--report-output",
        default="experiments/bt_selection_benchmark/results/v3a_feature_selector_report.md",
    )
    args = parser.parse_args()

    sk = load_sklearn()
    df = pd.read_csv(args.input)
    if "selector_group_id" not in df.columns:
        raise ValueError("Dataset must contain selector_group_id.")
    if "sim_success" not in df.columns:
        raise ValueError("Dataset must contain sim_success.")

    df = df[df["sim_success"].isin([0, 1])].copy()
    df["sim_success"] = df["sim_success"].astype(int)
    df["true_score"] = df.apply(true_score, axis=1)

    feature_cols, numeric_cols, categorical_cols = choose_columns(df)
    if not feature_cols:
        raise ValueError("No usable non-leaky feature columns were found.")

    groups = df["selector_group_id"].astype(str).to_numpy()
    y = df["sim_success"].to_numpy()
    x = df[feature_cols]
    unique_groups = np.unique(groups)
    n_splits = min(5, len(unique_groups))

    predictions = np.zeros(len(df), dtype=float)
    if n_splits >= 2 and len(np.unique(y)) == 2:
        splitter = sk["GroupKFold"](n_splits=n_splits)
        for train_idx, test_idx in splitter.split(x, y, groups):
            model = make_model(numeric_cols, categorical_cols, sk)
            model.fit(x.iloc[train_idx], y[train_idx])
            predictions[test_idx] = model.predict_proba(x.iloc[test_idx])[:, 1]
    else:
        # Degenerate fallback for very small debugging subsets.
        predictions[:] = float(y.mean())

    df["predicted_sim_success"] = predictions
    scored = baseline_scores(df)

    metrics = {
        "rows": int(len(scored)),
        "groups": int(scored["selector_group_id"].nunique()),
        "positive_labels": int(scored["sim_success"].sum()),
        "negative_labels": int((scored["sim_success"] == 0).sum()),
    }
    metrics["accuracy"] = float(sk["accuracy_score"](y, predictions >= 0.5))
    try:
        metrics["roc_auc"] = float(sk["roc_auc_score"](y, predictions))
    except Exception:
        metrics["roc_auc"] = float("nan")
    try:
        metrics["log_loss"] = float(sk["log_loss"](y, np.clip(predictions, 1e-6, 1 - 1e-6)))
    except Exception:
        metrics["log_loss"] = float("nan")

    selector_rows = []
    choices_frames = []
    for selector, score_col in [
        ("learned_feature", "learned_score"),
        ("symbolic_only", "symbolic_score"),
        ("shortest_tree", "shortest_tree_score"),
        ("oracle", "true_score"),
    ]:
        row, choices = evaluate_selector(scored, score_col)
        row["selector"] = selector
        selector_rows.append(row)
        choices["selector"] = selector
        choices_frames.append(choices)

    summary = pd.DataFrame(selector_rows)[
        ["selector", "groups", "success", "mean_selected_true_score", "mean_regret"]
    ]

    summary_output = Path(args.summary_output)
    choices_output = Path(args.choices_output)
    report_output = Path(args.report_output)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_output, index=False)
    pd.concat(choices_frames, ignore_index=True).to_csv(choices_output, index=False)
    write_report(report_output, summary, metrics, feature_cols, choices_output)

    print(
        json.dumps(
            {
                "result": "success",
                "input": args.input,
                "rows": metrics["rows"],
                "groups": metrics["groups"],
                "summary_output": str(summary_output),
                "choices_output": str(choices_output),
                "report_output": str(report_output),
                "accuracy": metrics["accuracy"],
                "roc_auc": metrics["roc_auc"],
                "selectors": summary["selector"].tolist(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
