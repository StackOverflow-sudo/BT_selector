#!/usr/bin/env python3
"""Evaluate V6 with a strict benchmark-level holdout.

All base-selector preprocessing and models are fitted on V1/V2/V2B before V6
is scored. Pre-simulation and post-simulation V5 modes are reported separately.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import torch

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import train_v3b_pairwise_selector as v3b  # noqa: E402
import train_v4a_bt_token_selector as v4a  # noqa: E402
import train_v4b_transformer_selector as v4b  # noqa: E402
import train_v5_learned_ensemble as v5  # noqa: E402


RESULTS_DIR = Path("experiments/bt_selection_benchmark/results")
DEFAULT_INPUT = RESULTS_DIR / "learned_selector_dataset_v3a.csv"


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def feature_external_choices(train, test, feature_cols, sk):
    train = train.reset_index(drop=True)
    test = test.reset_index(drop=True).copy()
    x_train, x_test = v4a.build_feature_matrix(train, test, feature_cols, "feature_only", sk)
    pair_x, pair_y = v3b.make_pairwise_examples(x_train, train, sk)
    if pair_x is None or len(np.unique(pair_y)) < 2:
        raise ValueError("No valid feature-only pairwise training examples.")
    model = sk["LogisticRegression"](max_iter=2000, class_weight="balanced")
    model.fit(pair_x, pair_y)
    test["learned_score"] = np.asarray(x_test @ model.coef_.reshape(-1, 1)).ravel()
    row, choices = v3b.evaluate_selector(test, "learned_score")
    row["selector"] = "feature_only"
    choices["selector"] = "feature_only"
    return choices, row


def transformer_external_choices(train, test, mode, feature_cols, sk, model_args):
    set_seed(model_args.seed)
    device = torch.device("cuda" if model_args.cuda and torch.cuda.is_available() else "cpu")
    scored, pair_scores, pair_labels = v4b.train_transformer_mode(
        train.reset_index(drop=True), test.reset_index(drop=True), mode,
        feature_cols, sk, model_args, device,
    )
    row, choices = v3b.evaluate_selector(scored, "learned_score")
    row["selector"] = mode
    row["pairwise_examples"] = len(pair_labels)
    if pair_labels:
        labels = np.asarray(pair_labels)
        scores = np.asarray(pair_scores)
        row["pairwise_accuracy"] = float(sk["accuracy_score"](labels, scores >= 0))
        row["pairwise_roc_auc"] = float(sk["roc_auc_score"](labels, scores))
    choices["selector"] = mode
    return choices, row


def baseline_choices(frame):
    scored = v3b.add_baseline_scores(frame.copy())
    outputs = []
    for selector, score_col in [("symbolic_only", "symbolic_score"), ("shortest_tree", "shortest_tree_score")]:
        _, choices = v3b.evaluate_selector(scored, score_col)
        choices["selector"] = selector
        outputs.append(choices)
    return outputs


def train_oof_base_choices(train, feature_cols, sk, model_args):
    frames = []
    choices, _ = v4a.train_eval_mode(train, "feature_only", feature_cols, sk)
    choices["selector"] = "feature_only"
    frames.append(choices)
    for mode in ["transformer_fused", "transformer_only"]:
        choices, _ = v4b.train_eval_transformer(train, mode, feature_cols, sk, model_args)
        choices["selector"] = mode
        frames.append(choices)
    frames.extend(baseline_choices(train))
    return pd.concat(frames, ignore_index=True, sort=False)


def test_external_base_choices(train, test, feature_cols, sk, model_args):
    frames = []
    choices, _ = feature_external_choices(train, test, feature_cols, sk)
    frames.append(choices)
    for mode in ["transformer_fused", "transformer_only"]:
        choices, _ = transformer_external_choices(train, test, mode, feature_cols, sk, model_args)
        frames.append(choices)
    frames.extend(baseline_choices(test))
    return pd.concat(frames, ignore_index=True, sort=False)


def learned_v5_results(train_scored, test_scored, sk):
    feature_sets = {
        "v5_strict_no_simulation": v5.VOTE_FEATURES + v5.SYMBOLIC_FEATURES,
        "v5_strict_simulation_reranker": v5.FULL_FEATURES,
        **v5.ABLATIONS,
    }
    rows, choice_frames, weight_rows = [], [], []
    for selector, cols in feature_sets.items():
        model, train_examples = v5.train_model(train_scored, cols, sk)
        score_col = selector + "_score"
        evaluated = test_scored.copy()
        evaluated[score_col] = v5.score_with_model(model, evaluated, cols)
        metrics = v5.pairwise_metrics(evaluated, score_col, sk)
        row, choices = v5.evaluate_named_selector(evaluated, score_col, selector)
        row.update(metrics)
        row.update({
            "train_groups": int(train_scored["selector_group_id"].nunique()),
            "test_groups": int(test_scored["selector_group_id"].nunique()),
            "pairwise_train_examples": train_examples,
            "evaluation_mode": "pre_simulation" if selector.endswith("no_simulation") else "post_simulation",
        })
        rows.append(row)
        choice_frames.append(choices)
        for feature, weight in zip(cols, model.coef_.ravel()):
            weight_rows.append({"selector": selector, "feature": feature, "weight": float(weight)})
        weight_rows.append({"selector": selector, "feature": "intercept", "weight": float(model.intercept_[0])})
    return rows, choice_frames, weight_rows


def write_report(path, summary, counts, overlap, epochs):
    lines = [
        "# Strict V6 Holdout Audit", "", "## Finding", "",
        "The dataset split has no task-state group overlap between development sources and V6.",
        "The legacy V4B choices are group-level out-of-fold estimates over all 110 groups; a V6 choice can therefore come from a base model trained on other V6 groups.",
        "They must not be described as a strict benchmark-level V6 holdout.", "",
        "This audit retrains all preprocessing and base models on V1/V2/V2B before scoring any V6 candidate.",
        "Vocabulary, scaling, categorical encoding, Transformer parameters, and V5 weights therefore exclude V6.",
        "", "## Split Audit", "", counts.to_csv(index=False),
        f"Task-state group overlap: {overlap}", f"Transformer epochs: {epochs}",
        "", "## Strict External Results", "", summary.to_csv(index=False),
        "", "## Interpretation Boundary", "",
        "`v5_strict_no_simulation` uses base-selector votes and symbolic reliability only and is the valid pre-rollout result.",
        "`v5_strict_simulation_reranker` also uses candidate simulation outcomes and is a simulate-then-select result, not zero-rollout prediction.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--test-benchmark", default="v6_hard_cases")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--cuda", action="store_true")
    parser.add_argument("--summary-output", type=Path, default=RESULTS_DIR / "v6_strict_holdout_summary.csv")
    parser.add_argument("--choices-output", type=Path, default=RESULTS_DIR / "v6_strict_holdout_choices.csv")
    parser.add_argument("--weights-output", type=Path, default=RESULTS_DIR / "v6_strict_holdout_weights.csv")
    parser.add_argument("--report-output", type=Path, default=RESULTS_DIR / "v6_strict_holdout_audit.md")
    args = parser.parse_args()

    set_seed(args.seed)
    sk = v4a.load_extra_sklearn()
    data = v4a.prepare_dataset(str(args.input))
    source = data["source_benchmark"].astype(str)
    train = data[source != args.test_benchmark].copy().reset_index(drop=True)
    test = data[source == args.test_benchmark].copy().reset_index(drop=True)
    if train.empty or test.empty:
        raise ValueError("Strict external split produced an empty partition.")
    train_groups = set(train["selector_group_id"].astype(str))
    test_groups = set(test["selector_group_id"].astype(str))
    overlap = len(train_groups & test_groups)
    if overlap:
        raise ValueError(f"Found {overlap} overlapping selector groups.")

    feature_cols, _, _ = v3b.choose_columns(data)
    feature_cols = [c for c in feature_cols if c != "bt_token_sequence"]
    model_args = SimpleNamespace(
        max_vocab_size=512, max_len=96, d_model=64, nhead=2, layers=1,
        dropout=0.1, epochs=args.epochs, batch_size=args.batch_size,
        lr=1e-3, weight_decay=1e-4, seed=args.seed, cuda=args.cuda,
    )

    train_choices = train_oof_base_choices(train, feature_cols, sk, model_args)
    test_choices = test_external_base_choices(train, test, feature_cols, sk, model_args)
    all_choices = pd.concat([train_choices, test_choices], ignore_index=True, sort=False)
    train_scored = v5.add_ensemble_features(train, all_choices)
    test_scored = v5.add_ensemble_features(test, all_choices)
    learned_rows, learned_choices, weight_rows = learned_v5_results(train_scored, test_scored, sk)

    test_ids = set(test["selector_group_id"].astype(str))
    baseline_rows, baseline_choices_out = [], []
    for selector in ["feature_only", "transformer_fused", "transformer_only", "symbolic_only", "shortest_tree"]:
        row, choices = v5.evaluate_choice_selector(test_scored, test_choices, selector, test_ids)
        row["evaluation_mode"] = "pre_simulation"
        baseline_rows.append(row)
        baseline_choices_out.append(choices)
    manual_row, manual_choices = v5.evaluate_named_selector(test_scored, "manual_v5_score", "manual_v5")
    manual_row["evaluation_mode"] = "post_simulation"
    baseline_rows.append(manual_row)
    baseline_choices_out.append(manual_choices)
    oracle_row, oracle_choices = v5.evaluate_named_selector(test_scored, "true_score", "oracle")
    oracle_row["evaluation_mode"] = "evaluation_upper_bound"

    summary = pd.DataFrame(learned_rows + baseline_rows + [oracle_row])
    choices = pd.concat(learned_choices + baseline_choices_out + [oracle_choices], ignore_index=True, sort=False)
    weights = pd.DataFrame(weight_rows)
    counts = data.groupby("source_benchmark", sort=False).agg(
        rows=("candidate_id", "size"), groups=("selector_group_id", "nunique"),
        positive_sim_success=("sim_success", "sum"),
    ).reset_index()
    for path in [args.summary_output, args.choices_output, args.weights_output, args.report_output]:
        path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.summary_output, index=False)
    choices.to_csv(args.choices_output, index=False)
    weights.to_csv(args.weights_output, index=False)
    write_report(args.report_output, summary, counts, overlap, args.epochs)
    print(json.dumps({
        "result": "success", "train_rows": int(len(train)), "train_groups": len(train_groups),
        "test_rows": int(len(test)), "test_groups": len(test_groups), "group_overlap": overlap,
        "summary_output": str(args.summary_output), "report_output": str(args.report_output),
    }, indent=2))


if __name__ == "__main__":
    main()
