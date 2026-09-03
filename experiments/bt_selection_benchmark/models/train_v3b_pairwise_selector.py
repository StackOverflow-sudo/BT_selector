#!/usr/bin/env python3
"""Train and evaluate the V3B pairwise ranking BT selector."""

from __future__ import annotations

import argparse
import itertools
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
    "learned_pairwise_score",
}

IDENTIFIER_COLUMNS = {
    "source_file",
    "case_id",
    "selector_group_id",
    "candidate_id",
    "bt_path",
    "simulation_output",
    "output",
    "result_path",
    "config_path",
    "job_path",
}


def load_sklearn():
    try:
        from scipy import sparse
        from sklearn.compose import ColumnTransformer
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, roc_auc_score
        from sklearn.model_selection import GroupKFold
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "scikit-learn and scipy are required for V3B. Use the same environment used for V3A."
        ) from exc

    return {
        "sparse": sparse,
        "ColumnTransformer": ColumnTransformer,
        "SimpleImputer": SimpleImputer,
        "LogisticRegression": LogisticRegression,
        "accuracy_score": accuracy_score,
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
            nunique = df[col].astype(str).nunique(dropna=True)
            if nunique <= max(100, len(df) // 2):
                categorical_cols.append(col)
    return numeric_cols + categorical_cols, numeric_cols, categorical_cols


def make_preprocessor(numeric_cols: list[str], categorical_cols: list[str], sk):
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
    return sk["ColumnTransformer"](
        [
            ("num", numeric_pipe, numeric_cols),
            ("cat", categorical_pipe, categorical_cols),
        ],
        remainder="drop",
    )


def make_pairwise_examples(transformed, frame: pd.DataFrame, sk, eps: float = 1e-9):
    rows = []
    labels = []

    def row_delta(left: int, right: int):
        delta = transformed[left] - transformed[right]
        if sk["sparse"].issparse(delta):
            return delta
        return sk["sparse"].csr_matrix(np.asarray(delta).reshape(1, -1))
    for _, group in frame.groupby("selector_group_id", sort=False):
        positions = list(group.index)
        for left, right in itertools.combinations(positions, 2):
            left_score = float(frame.loc[left, "true_score"])
            right_score = float(frame.loc[right, "true_score"])
            delta = left_score - right_score
            if abs(delta) <= eps:
                continue
            rows.append(row_delta(left, right))
            labels.append(1 if delta > 0 else 0)
            rows.append(row_delta(right, left))
            labels.append(1 if delta < 0 else 0)
    if not rows:
        return None, np.array([], dtype=int)
    return sk["sparse"].vstack(rows), np.array(labels, dtype=int)


def numeric_series(df: pd.DataFrame, name: str, default: float = 0) -> pd.Series:
    if name not in df.columns:
        return pd.Series(default, index=df.index, dtype=float)
    return pd.to_numeric(df[name], errors="coerce").fillna(default)


def add_baseline_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["symbolic_score"] = (
        50 * numeric_series(out, "symbolic_success")
        + 20 * numeric_series(out, "goal_satisfaction")
        - 0.5 * numeric_series(out, "tree_size")
        - 0.3 * numeric_series(out, "tree_depth")
    )
    out["shortest_tree_score"] = -numeric_series(out, "tree_size", 9999)
    return out


def evaluate_selector(df: pd.DataFrame, score_col: str) -> tuple[dict[str, float], pd.DataFrame]:
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


def write_report(path: Path, summary: pd.DataFrame, metrics: dict, feature_cols: list[str], choices_path: Path) -> None:
    lines = [
        "# V3B Pairwise Ranking BT Selector Report",
        "",
        "## Method",
        "",
        "V3B trains a pairwise ranking model over candidate behavior trees from the same task and initial state.",
        "Simulation metrics are used only to compute the supervision score; they are excluded from model inputs.",
        "",
        "Pairwise target:",
        "",
        "```text",
        "label = 1 if true_score(BT_A) > true_score(BT_B) else 0",
        "```",
        "",
        "Candidate score at inference:",
        "",
        "```text",
        "learned_pairwise_score = w dot feature(task, world, BT)",
        "```",
        "",
        "## Cross-Validation Metrics",
        "",
        f"- Rows: {metrics['rows']}",
        f"- Groups: {metrics['groups']}",
        f"- Pairwise training/eval examples: {metrics['pairwise_examples']}",
        f"- Pairwise accuracy: {metrics['pairwise_accuracy']:.3f}",
        f"- Pairwise ROC-AUC: {metrics['pairwise_roc_auc']:.3f}" if not np.isnan(metrics["pairwise_roc_auc"]) else "- Pairwise ROC-AUC: n/a",
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
        "V3B is closer to the real selector objective than V3A because it optimizes candidate ordering within each task/state group rather than independent success classification.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="experiments/bt_selection_benchmark/results/learned_selector_dataset_v3a.csv")
    parser.add_argument("--summary-output", default="experiments/bt_selection_benchmark/results/v3b_pairwise_selector_summary.csv")
    parser.add_argument("--choices-output", default="experiments/bt_selection_benchmark/results/v3b_pairwise_selector_choices.csv")
    parser.add_argument("--report-output", default="experiments/bt_selection_benchmark/results/v3b_pairwise_selector_report.md")
    args = parser.parse_args()

    sk = load_sklearn()
    df = pd.read_csv(args.input)
    df = df[df["sim_success"].isin([0, 1])].copy()
    df["sim_success"] = df["sim_success"].astype(int)
    df["true_score"] = df.apply(true_score, axis=1)
    df = df.reset_index(drop=True)

    feature_cols, numeric_cols, categorical_cols = choose_columns(df)
    if not feature_cols:
        raise ValueError("No usable non-leaky feature columns were found.")

    groups = df["selector_group_id"].astype(str).to_numpy()
    unique_groups = np.unique(groups)
    n_splits = min(5, len(unique_groups))
    df["learned_pairwise_score"] = 0.0

    all_pair_labels = []
    all_pair_scores = []
    pairwise_examples = 0

    if n_splits >= 2:
        splitter = sk["GroupKFold"](n_splits=n_splits)
        for train_idx, test_idx in splitter.split(df[feature_cols], df["sim_success"], groups):
            train = df.iloc[train_idx].copy().reset_index(drop=True)
            test = df.iloc[test_idx].copy().reset_index(drop=True)
            preprocessor = make_preprocessor(numeric_cols, categorical_cols, sk)
            x_train = preprocessor.fit_transform(train[feature_cols])
            pair_x, pair_y = make_pairwise_examples(x_train, train, sk)
            if pair_x is None or len(np.unique(pair_y)) < 2:
                df.loc[test_idx, "learned_pairwise_score"] = 0.0
                continue
            model = sk["LogisticRegression"](max_iter=2000, class_weight="balanced")
            model.fit(pair_x, pair_y)

            x_test = preprocessor.transform(test[feature_cols])
            single_scores = x_test @ model.coef_.reshape(-1, 1)
            df.loc[test_idx, "learned_pairwise_score"] = np.asarray(single_scores).ravel()

            test_pair_x, test_pair_y = make_pairwise_examples(x_test, test, sk)
            if test_pair_x is not None and len(test_pair_y):
                decision = model.decision_function(test_pair_x)
                all_pair_scores.extend(np.asarray(decision).ravel().tolist())
                all_pair_labels.extend(test_pair_y.tolist())
                pairwise_examples += int(len(test_pair_y))

    metrics = {
        "rows": int(len(df)),
        "groups": int(df["selector_group_id"].nunique()),
        "pairwise_examples": int(pairwise_examples),
    }
    if all_pair_labels:
        labels = np.array(all_pair_labels)
        scores = np.array(all_pair_scores)
        metrics["pairwise_accuracy"] = float(sk["accuracy_score"](labels, scores >= 0))
        try:
            metrics["pairwise_roc_auc"] = float(sk["roc_auc_score"](labels, scores))
        except Exception:
            metrics["pairwise_roc_auc"] = float("nan")
    else:
        metrics["pairwise_accuracy"] = float("nan")
        metrics["pairwise_roc_auc"] = float("nan")

    scored = add_baseline_scores(df)
    selector_rows = []
    choice_frames = []
    for selector, score_col in [
        ("learned_pairwise", "learned_pairwise_score"),
        ("symbolic_only", "symbolic_score"),
        ("shortest_tree", "shortest_tree_score"),
        ("oracle", "true_score"),
    ]:
        row, choices = evaluate_selector(scored, score_col)
        row["selector"] = selector
        selector_rows.append(row)
        choices["selector"] = selector
        choice_frames.append(choices)

    summary = pd.DataFrame(selector_rows)[["selector", "groups", "success", "mean_selected_true_score", "mean_regret"]]

    summary_output = Path(args.summary_output)
    choices_output = Path(args.choices_output)
    report_output = Path(args.report_output)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_output, index=False)
    pd.concat(choice_frames, ignore_index=True).to_csv(choices_output, index=False)
    write_report(report_output, summary, metrics, feature_cols, choices_output)

    print(json.dumps({
        "result": "success",
        "input": args.input,
        "rows": metrics["rows"],
        "groups": metrics["groups"],
        "pairwise_examples": metrics["pairwise_examples"],
        "pairwise_accuracy": metrics["pairwise_accuracy"],
        "pairwise_roc_auc": metrics["pairwise_roc_auc"],
        "summary_output": str(summary_output),
        "choices_output": str(choices_output),
        "report_output": str(report_output),
        "selectors": summary["selector"].tolist(),
    }, indent=2))


if __name__ == "__main__":
    main()
