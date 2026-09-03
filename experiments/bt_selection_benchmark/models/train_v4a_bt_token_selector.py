#!/usr/bin/env python3
"""Train V4A BT-token-aware pairwise ranking selectors."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import train_v3b_pairwise_selector as v3b  # noqa: E402


def load_extra_sklearn():
    sk = v3b.load_sklearn()
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("scikit-learn TfidfVectorizer is required for V4A.") from exc
    sk["TfidfVectorizer"] = TfidfVectorizer
    return sk


def normalize_token(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "none"
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "empty"


def object_role(name, moved_object: str, support_object: str) -> str:
    token = normalize_token(name)
    if token == normalize_token(moved_object):
        return "obj_moved"
    if token == normalize_token(support_object):
        return "obj_support"
    if token == "none":
        return "obj_none"
    return "obj_other"


def action_name_token(name: str) -> str:
    match = re.search(r"action:\s*([a-zA-Z0-9_]+)", str(name))
    if match:
        return normalize_token(match.group(1))
    match = re.search(r"([a-zA-Z0-9_]+)\s*\(", str(name))
    if match:
        return normalize_token(match.group(1))
    return normalize_token(name)


def sequence_name_token(name: str) -> str:
    match = re.search(r"sequence:\s*([a-zA-Z0-9_]+)", str(name))
    if match:
        return normalize_token(match.group(1))
    return "sequence"


def read_bt(path_value: str):
    if not path_value or pd.isna(path_value):
        return None
    path = Path(str(path_value))
    if not path.exists():
        root_path = Path("/home/theshy/projects/mycode/kios_baseline") / path
        path = root_path
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def tokenize_bt_node(node, moved_object: str, support_object: str, tokens: list[str], depth: int = 0) -> None:
    if not isinstance(node, dict):
        return

    type_name = normalize_token(node.get("type_name", "unknown"))
    tokens.append(f"type_{type_name}")
    tokens.append(f"depth_{min(depth, 6)}")

    if type_name == "sequence":
        tokens.append(f"seq_{sequence_name_token(node.get('name', ''))}")
    elif type_name == "selector":
        tokens.append("selector")
    elif type_name == "action":
        tokens.append(f"action_{action_name_token(node.get('name', ''))}")
    elif type_name == "condition":
        tokens.append("condition")

    for condition in node.get("conditions", []) or []:
        if not isinstance(condition, dict):
            continue
        predicate = normalize_token(condition.get("property_name"))
        value_role = object_role(condition.get("property_value"), moved_object, support_object)
        object_role_token = object_role(condition.get("object_name"), moved_object, support_object)
        tokens.extend(
            [
                f"cond_{predicate}",
                f"cond_obj_{object_role_token}",
                f"cond_val_{value_role}",
                f"cond_status_{normalize_token(condition.get('status'))}",
            ]
        )

    for effect in node.get("effects", []) or []:
        if not isinstance(effect, dict):
            continue
        predicate = normalize_token(effect.get("property_name"))
        value_role = object_role(effect.get("property_value"), moved_object, support_object)
        object_role_token = object_role(effect.get("object_name"), moved_object, support_object)
        tokens.extend(
            [
                f"effect_{predicate}",
                f"effect_obj_{object_role_token}",
                f"effect_val_{value_role}",
            ]
        )

    metadata = node.get("metadata", {}) or {}
    if isinstance(metadata, dict):
        placement = metadata.get("placement", {}) or {}
        if isinstance(placement, dict):
            strategy = normalize_token(placement.get("strategy"))
            if strategy != "none":
                tokens.append(f"placement_{strategy}")
            ratio = placement.get("target_xy_offset_ratio")
            if isinstance(ratio, (list, tuple)) and len(ratio) >= 2:
                try:
                    x = float(ratio[0])
                    y = float(ratio[1])
                    tokens.append(f"offset_x_{'neg' if x < 0 else 'pos' if x > 0 else 'zero'}")
                    tokens.append(f"offset_y_{'neg' if y < 0 else 'pos' if y > 0 else 'zero'}")
                except Exception:
                    pass

    for index, child in enumerate(node.get("children", []) or []):
        tokens.append(f"child_index_{min(index, 5)}")
        tokenize_bt_node(child, moved_object, support_object, tokens, depth + 1)


def bt_token_sequence(row: pd.Series) -> str:
    tree = read_bt(row.get("bt_path", ""))
    if tree is None:
        return "bt_missing"
    tokens: list[str] = []
    tokenize_bt_node(
        tree,
        str(row.get("moved_object", "")),
        str(row.get("support_object", "")),
        tokens,
    )
    return " ".join(tokens) if tokens else "bt_empty"


def prepare_dataset(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[df["sim_success"].isin([0, 1])].copy()
    df["sim_success"] = df["sim_success"].astype(int)
    df["true_score"] = df.apply(v3b.true_score, axis=1)
    df["bt_token_sequence"] = df.apply(bt_token_sequence, axis=1)
    return df.reset_index(drop=True)


def build_feature_matrix(train: pd.DataFrame, test: pd.DataFrame, feature_cols: list[str], mode: str, sk):
    matrices_train = []
    matrices_test = []

    if mode in {"feature_only", "fused"}:
        numeric_cols = [c for c in feature_cols if pd.api.types.is_numeric_dtype(train[c])]
        categorical_cols = [c for c in feature_cols if c not in numeric_cols]
        preprocessor = v3b.make_preprocessor(numeric_cols, categorical_cols, sk)
        matrices_train.append(preprocessor.fit_transform(train[feature_cols]))
        matrices_test.append(preprocessor.transform(test[feature_cols]))

    if mode in {"bt_token_only", "fused"}:
        vectorizer = sk["TfidfVectorizer"](
            tokenizer=str.split,
            preprocessor=None,
            token_pattern=None,
            lowercase=False,
            ngram_range=(1, 3),
            min_df=1,
        )
        matrices_train.append(vectorizer.fit_transform(train["bt_token_sequence"].fillna("bt_missing")))
        matrices_test.append(vectorizer.transform(test["bt_token_sequence"].fillna("bt_missing")))

    if len(matrices_train) == 1:
        return matrices_train[0], matrices_test[0]
    return sk["sparse"].hstack(matrices_train).tocsr(), sk["sparse"].hstack(matrices_test).tocsr()


def train_eval_mode(df: pd.DataFrame, mode: str, feature_cols: list[str], sk) -> tuple[pd.DataFrame, dict]:
    groups = df["selector_group_id"].astype(str).to_numpy()
    unique_groups = np.unique(groups)
    n_splits = min(5, len(unique_groups))
    scored_frames = []
    all_pair_labels = []
    all_pair_scores = []
    pairwise_examples = 0

    splitter = sk["GroupKFold"](n_splits=n_splits)
    for train_idx, test_idx in splitter.split(df, df["sim_success"], groups):
        train = df.iloc[train_idx].copy().reset_index(drop=True)
        test = df.iloc[test_idx].copy().reset_index(drop=True)
        x_train, x_test = build_feature_matrix(train, test, feature_cols, mode, sk)
        pair_x, pair_y = v3b.make_pairwise_examples(x_train, train, sk)

        test["learned_score"] = 0.0
        if pair_x is not None and len(np.unique(pair_y)) >= 2:
            model = sk["LogisticRegression"](max_iter=2000, class_weight="balanced")
            model.fit(pair_x, pair_y)
            single_scores = x_test @ model.coef_.reshape(-1, 1)
            test["learned_score"] = np.asarray(single_scores).ravel()

            test_pair_x, test_pair_y = v3b.make_pairwise_examples(x_test, test, sk)
            if test_pair_x is not None and len(test_pair_y):
                decision = model.decision_function(test_pair_x)
                all_pair_scores.extend(np.asarray(decision).ravel().tolist())
                all_pair_labels.extend(test_pair_y.tolist())
                pairwise_examples += int(len(test_pair_y))

        scored_frames.append(test)

    scored = pd.concat(scored_frames, ignore_index=True)
    row, choices = v3b.evaluate_selector(scored, "learned_score")
    row["selector"] = mode
    row["pairwise_examples"] = pairwise_examples
    if all_pair_labels:
        labels = np.array(all_pair_labels)
        scores = np.array(all_pair_scores)
        row["pairwise_accuracy"] = float(sk["accuracy_score"](labels, scores >= 0))
        try:
            row["pairwise_roc_auc"] = float(sk["roc_auc_score"](labels, scores))
        except Exception:
            row["pairwise_roc_auc"] = float("nan")
    else:
        row["pairwise_accuracy"] = float("nan")
        row["pairwise_roc_auc"] = float("nan")
    choices["selector"] = mode
    return choices, row


def write_report(path: Path, summary: pd.DataFrame, choices_path: Path, feature_cols: list[str]) -> None:
    lines = [
        "# V4A BT Token-Aware Pairwise Selector Report",
        "",
        "## Method",
        "",
        "V4A serializes each candidate Behavior Tree JSON into a structured token sequence and uses TF-IDF n-gram features as a lightweight BT encoder.",
        "The BT-token representation is evaluated alone and fused with the V3B tabular task/world/symbolic features.",
        "",
        "BT token encoder:",
        "",
        "```text",
        "BT JSON -> preorder tokens -> TF-IDF n-gram vector",
        "```",
        "",
        "Pairwise ranking target:",
        "",
        "```text",
        "label = 1 if true_score(BT_A) > true_score(BT_B) else 0",
        "```",
        "",
        "## Selector Comparison",
        "",
        summary.to_csv(index=False),
        "",
        "## Feature Columns",
        "",
        ", ".join(feature_cols),
        "",
        "## Outputs",
        "",
        f"- Choices: `{choices_path}`",
        "",
        "## Interpretation",
        "",
        "Compare `feature_only` with `fused`. If `fused` improves regret, explicit BT structure contributes beyond V3B features. If `bt_token_only` is competitive, the serialized BT itself carries useful executability signals.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="experiments/bt_selection_benchmark/results/learned_selector_dataset_v3a.csv")
    parser.add_argument("--summary-output", default="experiments/bt_selection_benchmark/results/v4a_bt_token_selector_summary.csv")
    parser.add_argument("--choices-output", default="experiments/bt_selection_benchmark/results/v4a_bt_token_selector_choices.csv")
    parser.add_argument("--report-output", default="experiments/bt_selection_benchmark/results/v4a_bt_token_selector_report.md")
    args = parser.parse_args()

    sk = load_extra_sklearn()
    df = prepare_dataset(args.input)
    feature_cols, _, _ = v3b.choose_columns(df)
    feature_cols = [c for c in feature_cols if c != "bt_token_sequence"]

    selector_rows = []
    choice_frames = []
    for mode in ["feature_only", "bt_token_only", "fused"]:
        choices, row = train_eval_mode(df, mode, feature_cols, sk)
        selector_rows.append(row)
        choice_frames.append(choices)

    scored = v3b.add_baseline_scores(df)
    for selector, score_col in [
        ("symbolic_only", "symbolic_score"),
        ("shortest_tree", "shortest_tree_score"),
        ("oracle", "true_score"),
    ]:
        row, choices = v3b.evaluate_selector(scored, score_col)
        row["selector"] = selector
        row["pairwise_examples"] = 0
        row["pairwise_accuracy"] = float("nan")
        row["pairwise_roc_auc"] = float("nan")
        selector_rows.append(row)
        choices["selector"] = selector
        choice_frames.append(choices)

    summary = pd.DataFrame(selector_rows)[
        [
            "selector",
            "groups",
            "success",
            "mean_selected_true_score",
            "mean_regret",
            "pairwise_accuracy",
            "pairwise_roc_auc",
            "pairwise_examples",
        ]
    ]

    summary_output = Path(args.summary_output)
    choices_output = Path(args.choices_output)
    report_output = Path(args.report_output)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_output, index=False)
    pd.concat(choice_frames, ignore_index=True).to_csv(choices_output, index=False)
    write_report(report_output, summary, choices_output, feature_cols)

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
                "selectors": summary["selector"].tolist(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
