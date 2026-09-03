#!/usr/bin/env python3
"""Train and evaluate a learnable V5 ensemble BT selector.

The fixed V5 selector uses hand-set weights. This script learns those weights
from validation data using pairwise ranking supervision over candidate BTs from
same task/state groups.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import summarize_v5_ensemble_selector as fixed_v5  # noqa: E402
import train_v3b_pairwise_selector as v3b  # noqa: E402

DEFAULT_EVALUATIONS = Path("experiments/bt_selection_benchmark/results/learned_selector_dataset_v3a.csv")
DEFAULT_CHOICES = Path("experiments/bt_selection_benchmark/results/v4b_transformer_selector_choices.csv")
DEFAULT_SUMMARY = Path("experiments/bt_selection_benchmark/results/v5_learned_ensemble_summary.csv")
DEFAULT_CHOICES_OUT = Path("experiments/bt_selection_benchmark/results/v5_learned_ensemble_choices.csv")
DEFAULT_SCORED = Path("experiments/bt_selection_benchmark/results/v5_learned_ensemble_scored_candidates.csv")
DEFAULT_REPORT = Path("experiments/bt_selection_benchmark/results/v5_learned_ensemble_report.md")
DEFAULT_ABLATION = Path("experiments/bt_selection_benchmark/results/v5_learned_ensemble_ablation.csv")
DEFAULT_WEIGHTS = Path("experiments/bt_selection_benchmark/results/v5_learned_ensemble_weights.csv")

BASE_SELECTORS = ["feature_only", "transformer_fused", "transformer_only", "symbolic_only", "shortest_tree"]
TRANSFORMER_FEATURES = ["vote_transformer_fused", "vote_transformer_only"]
SYMBOLIC_FEATURES = ["symbolic_reliability_norm"]
SIMULATION_FEATURES = ["simulation_reliability_norm"]
VOTE_FEATURES = ["vote_feature_only", "vote_transformer_fused", "vote_transformer_only", "vote_symbolic_only", "vote_shortest_tree"]
FULL_FEATURES = VOTE_FEATURES + SYMBOLIC_FEATURES + SIMULATION_FEATURES

ABLATIONS = {
    "v5_learned_full": FULL_FEATURES,
    "v5_no_transformer_votes": [c for c in FULL_FEATURES if c not in TRANSFORMER_FEATURES],
    "v5_no_symbolic_reliability": [c for c in FULL_FEATURES if c not in SYMBOLIC_FEATURES],
    "v5_no_simulation_reliability": [c for c in FULL_FEATURES if c not in SIMULATION_FEATURES],
    "v5_votes_only": VOTE_FEATURES,
    "v5_reliability_only": SYMBOLIC_FEATURES + SIMULATION_FEATURES,
}


def ensure_group_id(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "selector_group_id" not in out.columns:
        out["selector_group_id"] = out.apply(
            lambda row: str(row.get("benchmark", row.get("source_benchmark", "")))
            + "::"
            + str(row["initial_state_id"])
            + "::"
            + str(row["task_id"]),
            axis=1,
        )
    return out


def base_true_score(df: pd.DataFrame) -> pd.Series:
    return fixed_v5.true_score(df)


def add_ensemble_features(evaluations: pd.DataFrame, choices: pd.DataFrame) -> pd.DataFrame:
    scored = fixed_v5.add_v5_scores(ensure_group_id(evaluations), choices)
    for selector in BASE_SELECTORS:
        scored[f"vote_{selector}"] = 0.0
    usable = choices[choices["selector"].isin(BASE_SELECTORS)].copy()
    vote_pairs = set((str(r.selector), str(r.selector_group_id), str(r.selected_candidate)) for r in usable.itertuples())
    for selector in BASE_SELECTORS:
        scored[f"vote_{selector}"] = [
            1.0 if (selector, str(group_id), str(candidate_id)) in vote_pairs else 0.0
            for group_id, candidate_id in zip(scored["selector_group_id"], scored["candidate_id"])
        ]
    scored["manual_v5_score"] = scored["v5_ensemble_score"]
    scored["oracle_score"] = scored["true_score"]
    return scored


def pairwise_matrix(frame: pd.DataFrame, feature_cols: list[str], eps: float = 1e-9) -> tuple[np.ndarray, np.ndarray]:
    rows: list[np.ndarray] = []
    labels: list[int] = []
    x = frame[feature_cols].fillna(0.0).to_numpy(dtype=float)
    true = frame["true_score"].to_numpy(dtype=float)
    index_positions = {idx: pos for pos, idx in enumerate(frame.index)}
    for _, group in frame.groupby("selector_group_id", sort=False):
        positions = [index_positions[idx] for idx in group.index]
        for left, right in itertools.combinations(positions, 2):
            delta = true[left] - true[right]
            if abs(delta) <= eps:
                continue
            rows.append(x[left] - x[right])
            labels.append(1 if delta > 0 else 0)
            rows.append(x[right] - x[left])
            labels.append(1 if delta < 0 else 0)
    if not rows:
        return np.zeros((0, len(feature_cols))), np.zeros((0,), dtype=int)
    return np.vstack(rows), np.asarray(labels, dtype=int)


def train_model(train: pd.DataFrame, feature_cols: list[str], sk):
    x_pair, y_pair = pairwise_matrix(train, feature_cols)
    if len(y_pair) == 0 or len(np.unique(y_pair)) < 2:
        raise ValueError("No valid pairwise training examples for learned ensemble.")
    model = sk["LogisticRegression"](max_iter=2000, class_weight="balanced", C=1.0)
    model.fit(x_pair, y_pair)
    return model, int(len(y_pair))


def score_with_model(model, frame: pd.DataFrame, feature_cols: list[str]) -> np.ndarray:
    x = frame[feature_cols].fillna(0.0).to_numpy(dtype=float)
    return np.asarray(x @ model.coef_.reshape(-1, 1)).ravel()


def pairwise_metrics(frame: pd.DataFrame, score_col: str, sk) -> dict[str, float]:
    labels: list[int] = []
    scores: list[float] = []
    for _, group in frame.groupby("selector_group_id", sort=False):
        ordered = group.reset_index(drop=True)
        for i in range(len(ordered)):
            for j in range(i + 1, len(ordered)):
                delta_true = float(ordered.loc[i, "true_score"] - ordered.loc[j, "true_score"])
                if abs(delta_true) <= 1e-9:
                    continue
                delta_pred = float(ordered.loc[i, score_col] - ordered.loc[j, score_col])
                labels.append(1 if delta_true > 0 else 0)
                scores.append(delta_pred)
                labels.append(1 if delta_true < 0 else 0)
                scores.append(-delta_pred)
    if not labels:
        return {"pairwise_accuracy": float("nan"), "pairwise_roc_auc": float("nan"), "pairwise_examples": 0}
    y = np.asarray(labels)
    s = np.asarray(scores)
    out = {"pairwise_accuracy": float(sk["accuracy_score"](y, s >= 0)), "pairwise_examples": int(len(y))}
    try:
        out["pairwise_roc_auc"] = float(sk["roc_auc_score"](y, s))
    except Exception:
        out["pairwise_roc_auc"] = float("nan")
    return out


def evaluate_named_selector(df: pd.DataFrame, score_col: str, selector: str) -> tuple[dict, pd.DataFrame]:
    row, choices = fixed_v5.evaluate_selector(df, score_col, selector)
    choices["selector"] = selector
    return row, choices


def evaluate_choice_selector(scored: pd.DataFrame, choices: pd.DataFrame, selector: str, group_ids: set[str]) -> tuple[dict, pd.DataFrame]:
    rows = []
    selected_rows = choices[(choices["selector"] == selector) & (choices["selector_group_id"].astype(str).isin(group_ids))]
    by_key = scored.set_index(["selector_group_id", "candidate_id"], drop=False)
    for _, choice in selected_rows.iterrows():
        group_id = str(choice["selector_group_id"])
        candidate_id = str(choice["selected_candidate"])
        group = scored[scored["selector_group_id"].astype(str) == group_id]
        if group.empty or (group_id, candidate_id) not in by_key.index:
            continue
        selected = by_key.loc[(group_id, candidate_id)]
        oracle = group.sort_values("true_score", ascending=False).iloc[0]
        benchmark, initial_state_id, task_id = fixed_v5.parse_group(group_id)
        rows.append({
            "selector_group_id": group_id,
            "benchmark": benchmark,
            "task_id": task_id,
            "initial_state_id": initial_state_id,
            "selected_candidate": candidate_id,
            "oracle_candidate": oracle.get("candidate_id", ""),
            "selected_sim_success": float(selected.get("sim_success", 0)),
            "selected_true_score": float(selected["true_score"]),
            "oracle_true_score": float(oracle["true_score"]),
            "regret": float(oracle["true_score"] - selected["true_score"]),
            "selector": selector,
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return {"selector": selector, "groups": 0, "success": float("nan"), "mean_selected_true_score": float("nan"), "mean_regret": float("nan"), "pairwise_accuracy": float("nan"), "pairwise_roc_auc": float("nan"), "pairwise_examples": 0}, out
    return {
        "selector": selector,
        "groups": int(len(out)),
        "success": float(out["selected_sim_success"].mean()),
        "mean_selected_true_score": float(out["selected_true_score"].mean()),
        "mean_regret": float(out["regret"].mean()),
        "pairwise_accuracy": float("nan"),
        "pairwise_roc_auc": float("nan"),
        "pairwise_examples": 0,
    }, out


def fixed_baseline_scores(scored: pd.DataFrame) -> pd.DataFrame:
    out = scored.copy()
    out["symbolic_only_score"] = 50 * fixed_v5.numeric(out, "symbolic_success") + 20 * fixed_v5.numeric(out, "goal_satisfaction") - 0.5 * fixed_v5.numeric(out, "tree_size") - 0.3 * fixed_v5.numeric(out, "tree_depth")
    out["shortest_tree_score"] = -fixed_v5.numeric(out, "tree_size", 9999)
    return out


def split_external(scored: pd.DataFrame, test_benchmark: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    source = scored["source_benchmark"].fillna(scored.get("benchmark", "")).astype(str)
    test_mask = source.eq(test_benchmark)
    return scored[~test_mask].copy(), scored[test_mask].copy()


def cross_validate(scored: pd.DataFrame, feature_sets: dict[str, list[str]], sk, n_splits: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    groups = scored["selector_group_id"].astype(str).to_numpy()
    unique = np.unique(groups)
    n_splits = min(n_splits, len(unique))
    if n_splits < 2:
        raise ValueError("Need at least two groups for cross-validation.")
    splitter = sk["GroupKFold"](n_splits=n_splits)
    scored_frames = []
    choice_frames = []
    rows = []
    for selector, cols in feature_sets.items():
        fold_frames = []
        pairwise_examples = 0
        for fold, (train_idx, test_idx) in enumerate(splitter.split(scored[cols], scored["sim_success"], groups)):
            train = scored.iloc[train_idx].copy()
            test = scored.iloc[test_idx].copy()
            model, examples = train_model(train, cols, sk)
            pairwise_examples += examples
            test = test.copy()
            test[f"{selector}_score"] = score_with_model(model, test, cols)
            test["cv_fold"] = fold
            fold_frames.append(test)
        cv_scored = pd.concat(fold_frames, ignore_index=True)
        metrics = pairwise_metrics(cv_scored, f"{selector}_score", sk)
        row, choices = evaluate_named_selector(cv_scored, f"{selector}_score", selector + "_cv")
        row.update(metrics)
        row["selector"] = selector + "_cv"
        rows.append(row)
        choices["selector"] = selector + "_cv"
        choice_frames.append(choices)
        scored_frames.append(cv_scored)
    return pd.DataFrame(rows), pd.concat(choice_frames, ignore_index=True)


def external_eval(scored: pd.DataFrame, choices: pd.DataFrame, feature_sets: dict[str, list[str]], sk, test_benchmark: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train, test = split_external(scored, test_benchmark)
    if train.empty or test.empty:
        raise ValueError(f"Invalid external split for benchmark {test_benchmark!r}.")
    test = fixed_baseline_scores(test)
    rows = []
    choice_frames = []
    weight_rows = []
    for selector, cols in feature_sets.items():
        model, examples = train_model(train, cols, sk)
        score_col = f"{selector}_score"
        test[score_col] = score_with_model(model, test, cols)
        metrics = pairwise_metrics(test, score_col, sk)
        row, selector_choices = evaluate_named_selector(test, score_col, selector)
        row.update(metrics)
        row["selector"] = selector
        row["train_groups"] = int(train["selector_group_id"].nunique())
        row["test_benchmark"] = test_benchmark
        row["pairwise_train_examples"] = examples
        rows.append(row)
        selector_choices["selector"] = selector
        choice_frames.append(selector_choices)
        for feature, weight in zip(cols, model.coef_.ravel()):
            weight_rows.append({"selector": selector, "feature": feature, "weight": float(weight)})
        weight_rows.append({"selector": selector, "feature": "intercept", "weight": float(model.intercept_[0])})

    group_ids = set(test["selector_group_id"].astype(str))
    for selector in ["feature_only", "transformer_fused", "transformer_only"]:
        row, selector_choices = evaluate_choice_selector(test, choices, selector, group_ids)
        rows.append(row)
        choice_frames.append(selector_choices)
    for selector, score_col in [("manual_v5", "manual_v5_score"), ("symbolic_only", "symbolic_only_score"), ("shortest_tree", "shortest_tree_score"), ("oracle", "true_score")]:
        row, selector_choices = evaluate_named_selector(test, score_col, selector)
        rows.append(row)
        choice_frames.append(selector_choices)

    return test, pd.DataFrame(rows), pd.concat(choice_frames, ignore_index=True), pd.DataFrame(weight_rows)


def write_report(path: Path, external_summary: pd.DataFrame, cv_summary: pd.DataFrame, weights: pd.DataFrame, ablation_path: Path, choices_path: Path, scored_path: Path, test_benchmark: str) -> None:
    learned = external_summary[external_summary["selector"] == "v5_learned_full"]
    manual = external_summary[external_summary["selector"] == "manual_v5"]
    best_line = ""
    if not learned.empty and not manual.empty:
        delta = float(manual.iloc[0]["mean_regret"] - learned.iloc[0]["mean_regret"])
        best_line = f"On `{test_benchmark}`, learned V5 changes mean regret by {delta:.3f} versus manual V5; positive means learned V5 is better."
    lines = [
        "# V5 Learnable Ensemble and Ablation Report",
        "",
        "## Method",
        "",
        "V5-learned replaces the hand-set V5 ensemble weights with a pairwise logistic ranking model.",
        "Each training example compares two candidate BTs from the same task and initial state.",
        "The target ranking is derived from the same simulation-grounded true score used by prior selector evaluations.",
        "",
        "Input features:",
        "",
        "- deployable selector votes: feature_only, transformer_fused, transformer_only, symbolic_only, shortest_tree",
        "- normalized symbolic reliability",
        "- normalized simulation reliability",
        "",
        "Oracle is not used as an input. It is reported only as an upper bound.",
        "",
        "## External Hard-Case Test",
        "",
        f"Train split: all sources except `{test_benchmark}`.",
        f"Test split: `{test_benchmark}` only.",
        "",
        external_summary.to_csv(index=False),
        "",
        best_line,
        "",
        "## Ablation Table",
        "",
        "The rows prefixed by `v5_` remove or isolate parts of the proposed ensemble input.",
        "Lower mean regret is better; oracle regret is zero by definition.",
        "",
        external_summary[external_summary["selector"].str.startswith("v5_")].to_csv(index=False),
        "",
        "## Cross-Validation Sanity Check",
        "",
        cv_summary.to_csv(index=False),
        "",
        "## Learned Weights",
        "",
        weights[weights["selector"] == "v5_learned_full"].to_csv(index=False),
        "",
        "## Outputs",
        "",
        f"- Ablation CSV: `{ablation_path}`",
        f"- Choices CSV: `{choices_path}`",
        f"- Scored candidates CSV: `{scored_path}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluations", type=Path, default=DEFAULT_EVALUATIONS)
    parser.add_argument("--choices", type=Path, default=DEFAULT_CHOICES)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--choices-output", type=Path, default=DEFAULT_CHOICES_OUT)
    parser.add_argument("--scored-output", type=Path, default=DEFAULT_SCORED)
    parser.add_argument("--ablation-output", type=Path, default=DEFAULT_ABLATION)
    parser.add_argument("--weights-output", type=Path, default=DEFAULT_WEIGHTS)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--test-benchmark", default="v6_hard_cases")
    parser.add_argument("--cv-splits", type=int, default=5)
    args = parser.parse_args()

    sk = v3b.load_sklearn()
    evaluations = pd.read_csv(args.evaluations)
    choices = pd.read_csv(args.choices)
    evaluations = evaluations[evaluations["sim_success"].isin([0, 1])].copy()
    evaluations["sim_success"] = evaluations["sim_success"].astype(int)
    scored = add_ensemble_features(evaluations, choices)
    scored = fixed_baseline_scores(scored)

    test_scored, external_summary, external_choices, weights = external_eval(scored, choices, ABLATIONS, sk, args.test_benchmark)
    cv_summary, cv_choices = cross_validate(scored, ABLATIONS, sk, args.cv_splits)

    summary = pd.concat([external_summary, cv_summary], ignore_index=True, sort=False)
    all_choices = pd.concat([external_choices, cv_choices], ignore_index=True, sort=False)

    for path in [args.summary_output, args.choices_output, args.scored_output, args.ablation_output, args.weights_output, args.report_output]:
        path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.summary_output, index=False)
    external_summary.to_csv(args.ablation_output, index=False)
    all_choices.to_csv(args.choices_output, index=False)
    scored.to_csv(args.scored_output, index=False)
    weights.to_csv(args.weights_output, index=False)
    write_report(args.report_output, external_summary, cv_summary, weights, args.ablation_output, args.choices_output, args.scored_output, args.test_benchmark)

    learned = external_summary[external_summary["selector"] == "v5_learned_full"].iloc[0].to_dict()
    print(json.dumps({
        "result": "success",
        "rows": int(len(scored)),
        "groups": int(scored["selector_group_id"].nunique()),
        "test_benchmark": args.test_benchmark,
        "summary_output": str(args.summary_output),
        "ablation_output": str(args.ablation_output),
        "choices_output": str(args.choices_output),
        "weights_output": str(args.weights_output),
        "report_output": str(args.report_output),
        "v5_learned_full": learned,
    }, indent=2))


if __name__ == "__main__":
    main()