#!/usr/bin/env python3
"""Train V4B lightweight Transformer BT encoder selectors."""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import train_v3b_pairwise_selector as v3b  # noqa: E402
import train_v4a_bt_token_selector as v4a  # noqa: E402


PAD_ID = 0
UNK_ID = 1


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def dense_array(matrix) -> np.ndarray:
    if hasattr(matrix, "toarray"):
        return matrix.toarray().astype(np.float32)
    return np.asarray(matrix, dtype=np.float32)


def build_vocab(sequences: pd.Series, max_vocab_size: int = 512) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for sequence in sequences.fillna("bt_missing"):
        counts.update(str(sequence).split())
    vocab = {"<PAD>": PAD_ID, "<UNK>": UNK_ID}
    for token, _ in counts.most_common(max_vocab_size - len(vocab)):
        if token not in vocab:
            vocab[token] = len(vocab)
    return vocab


def encode_sequences(sequences: pd.Series, vocab: dict[str, int], max_len: int) -> np.ndarray:
    encoded = np.zeros((len(sequences), max_len), dtype=np.int64)
    for row, sequence in enumerate(sequences.fillna("bt_missing")):
        ids = [vocab.get(token, UNK_ID) for token in str(sequence).split()[:max_len]]
        if ids:
            encoded[row, : len(ids)] = ids
    return encoded


def make_pair_indices(frame: pd.DataFrame, eps: float = 1e-9) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    left_indices: list[int] = []
    right_indices: list[int] = []
    labels: list[float] = []
    for _, group in frame.groupby("selector_group_id", sort=False):
        positions = list(group.index)
        for i, left in enumerate(positions):
            for right in positions[i + 1 :]:
                delta = float(frame.loc[left, "true_score"] - frame.loc[right, "true_score"])
                if abs(delta) <= eps:
                    continue
                left_indices.append(left)
                right_indices.append(right)
                labels.append(1.0 if delta > 0 else 0.0)
                left_indices.append(right)
                right_indices.append(left)
                labels.append(1.0 if delta < 0 else 0.0)
    return (
        np.asarray(left_indices, dtype=np.int64),
        np.asarray(right_indices, dtype=np.int64),
        np.asarray(labels, dtype=np.float32),
    )


class BTTransformerRanker(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        tabular_dim: int = 0,
        max_len: int = 96,
        d_model: int = 64,
        nhead: int = 2,
        num_layers: int = 1,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.token_embedding = nn.Embedding(vocab_size, d_model, padding_idx=PAD_ID)
        self.position_embedding = nn.Embedding(max_len, d_model)
        layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 2,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=num_layers)
        self.tabular_dim = tabular_dim
        if tabular_dim:
            self.tabular_projection = nn.Sequential(
                nn.Linear(tabular_dim, d_model),
                nn.LayerNorm(d_model),
                nn.GELU(),
            )
            scorer_dim = d_model * 2
        else:
            self.tabular_projection = None
            scorer_dim = d_model
        self.scorer = nn.Sequential(
            nn.LayerNorm(scorer_dim),
            nn.Linear(scorer_dim, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, 1),
        )

    def forward(self, token_ids: torch.Tensor, tabular: torch.Tensor | None = None) -> torch.Tensor:
        batch_size, seq_len = token_ids.shape
        positions = torch.arange(seq_len, device=token_ids.device).unsqueeze(0).expand(batch_size, -1)
        mask = token_ids.eq(PAD_ID)
        x = self.token_embedding(token_ids) + self.position_embedding(positions)
        encoded = self.encoder(x, src_key_padding_mask=mask)
        valid = (~mask).unsqueeze(-1).float()
        pooled = (encoded * valid).sum(dim=1) / valid.sum(dim=1).clamp_min(1.0)
        if self.tabular_projection is not None:
            assert tabular is not None
            tabular_embedding = self.tabular_projection(tabular)
            pooled = torch.cat([pooled, tabular_embedding], dim=-1)
        return self.scorer(pooled).squeeze(-1)


def train_transformer_mode(
    train: pd.DataFrame,
    test: pd.DataFrame,
    mode: str,
    feature_cols: list[str],
    sk,
    args,
    device: torch.device,
) -> tuple[pd.DataFrame, list[float], list[int]]:
    vocab = build_vocab(train["bt_token_sequence"], max_vocab_size=args.max_vocab_size)
    train_tokens = encode_sequences(train["bt_token_sequence"], vocab, args.max_len)
    test_tokens = encode_sequences(test["bt_token_sequence"], vocab, args.max_len)

    tab_train = np.zeros((len(train), 0), dtype=np.float32)
    tab_test = np.zeros((len(test), 0), dtype=np.float32)
    if mode == "transformer_fused":
        numeric_cols = [c for c in feature_cols if pd.api.types.is_numeric_dtype(train[c])]
        categorical_cols = [c for c in feature_cols if c not in numeric_cols]
        preprocessor = v3b.make_preprocessor(numeric_cols, categorical_cols, sk)
        tab_train = dense_array(preprocessor.fit_transform(train[feature_cols]))
        tab_test = dense_array(preprocessor.transform(test[feature_cols]))

    left, right, labels = make_pair_indices(train)
    model = BTTransformerRanker(
        vocab_size=len(vocab),
        tabular_dim=tab_train.shape[1],
        max_len=args.max_len,
        d_model=args.d_model,
        nhead=args.nhead,
        num_layers=args.layers,
        dropout=args.dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    criterion = nn.BCEWithLogitsLoss()

    train_tokens_tensor = torch.tensor(train_tokens, dtype=torch.long)
    train_tab_tensor = torch.tensor(tab_train, dtype=torch.float32)
    dataset = TensorDataset(
        torch.tensor(left, dtype=torch.long),
        torch.tensor(right, dtype=torch.long),
        torch.tensor(labels, dtype=torch.float32),
    )
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)

    model.train()
    for _ in range(args.epochs):
        for left_batch, right_batch, label_batch in loader:
            left_index = left_batch
            right_index = right_batch
            label_batch = label_batch.to(device)
            left_tokens = train_tokens_tensor[left_index].to(device)
            right_tokens = train_tokens_tensor[right_index].to(device)
            left_tab = train_tab_tensor[left_index].to(device) if tab_train.shape[1] else None
            right_tab = train_tab_tensor[right_index].to(device) if tab_train.shape[1] else None
            left_score = model(left_tokens, left_tab)
            right_score = model(right_tokens, right_tab)
            logits = left_score - right_score
            loss = criterion(logits, label_batch)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

    test = test.copy()
    model.eval()
    with torch.no_grad():
        test_scores = []
        for start in range(0, len(test), args.batch_size):
            end = start + args.batch_size
            token_batch = torch.tensor(test_tokens[start:end], dtype=torch.long, device=device)
            tab_batch = None
            if tab_test.shape[1]:
                tab_batch = torch.tensor(tab_test[start:end], dtype=torch.float32, device=device)
            test_scores.extend(model(token_batch, tab_batch).detach().cpu().numpy().tolist())
    test["learned_score"] = test_scores

    pair_labels: list[int] = []
    pair_scores: list[float] = []
    for _, group in test.groupby("selector_group_id", sort=False):
        ordered = group.reset_index(drop=True)
        for i in range(len(ordered)):
            for j in range(i + 1, len(ordered)):
                delta_true = float(ordered.loc[i, "true_score"] - ordered.loc[j, "true_score"])
                if abs(delta_true) <= 1e-9:
                    continue
                delta_pred = float(ordered.loc[i, "learned_score"] - ordered.loc[j, "learned_score"])
                pair_labels.append(1 if delta_true > 0 else 0)
                pair_scores.append(delta_pred)
                pair_labels.append(1 if delta_true < 0 else 0)
                pair_scores.append(-delta_pred)

    return test, pair_scores, pair_labels


def train_eval_transformer(df: pd.DataFrame, mode: str, feature_cols: list[str], sk, args) -> tuple[pd.DataFrame, dict]:
    device = torch.device("cuda" if args.cuda and torch.cuda.is_available() else "cpu")
    groups = df["selector_group_id"].astype(str).to_numpy()
    splitter = sk["GroupKFold"](n_splits=min(5, len(np.unique(groups))))
    scored_frames = []
    all_pair_scores: list[float] = []
    all_pair_labels: list[int] = []

    for fold, (train_idx, test_idx) in enumerate(splitter.split(df, df["sim_success"], groups)):
        set_seed(args.seed + fold)
        train = df.iloc[train_idx].copy().reset_index(drop=True)
        test = df.iloc[test_idx].copy().reset_index(drop=True)
        scored, pair_scores, pair_labels = train_transformer_mode(
            train, test, mode, feature_cols, sk, args, device
        )
        scored_frames.append(scored)
        all_pair_scores.extend(pair_scores)
        all_pair_labels.extend(pair_labels)

    scored_all = pd.concat(scored_frames, ignore_index=True)
    row, choices = v3b.evaluate_selector(scored_all, "learned_score")
    row["selector"] = mode
    row["pairwise_examples"] = len(all_pair_labels)
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


def write_report(path: Path, summary: pd.DataFrame, choices_path: Path, feature_cols: list[str], args) -> None:
    lines = [
        "# V4B Lightweight Transformer BT Encoder Report",
        "",
        "## Method",
        "",
        "V4B replaces the TF-IDF BT-token encoder from V4A with a lightweight Transformer encoder.",
        "The model is trained with pairwise ranking supervision derived from simulation-grounded true scores.",
        "",
        "Architecture:",
        "",
        "```text",
        "BT JSON -> preorder tokens -> token ids -> Transformer Encoder -> mean pooling -> ranking score",
        "```",
        "",
        "Fused architecture:",
        "",
        "```text",
        "Transformer BT embedding + task/world/symbolic tabular embedding -> ranking score",
        "```",
        "",
        "Hyperparameters:",
        "",
        f"- d_model: {args.d_model}",
        f"- heads: {args.nhead}",
        f"- layers: {args.layers}",
        f"- max_len: {args.max_len}",
        f"- epochs: {args.epochs}",
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
        "V4B is a compact Transformer prototype. Because the dataset is small, the main claim should be architectural feasibility rather than guaranteed improvement over the stronger linear pairwise selector.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="experiments/bt_selection_benchmark/results/learned_selector_dataset_v3a.csv")
    parser.add_argument("--summary-output", default="experiments/bt_selection_benchmark/results/v4b_transformer_selector_summary.csv")
    parser.add_argument("--choices-output", default="experiments/bt_selection_benchmark/results/v4b_transformer_selector_choices.csv")
    parser.add_argument("--report-output", default="experiments/bt_selection_benchmark/results/v4b_transformer_selector_report.md")
    parser.add_argument("--max-len", type=int, default=96)
    parser.add_argument("--max-vocab-size", type=int, default=512)
    parser.add_argument("--d-model", type=int, default=64)
    parser.add_argument("--nhead", type=int, default=2)
    parser.add_argument("--layers", type=int, default=1)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--cuda", action="store_true")
    args = parser.parse_args()

    set_seed(args.seed)
    sk = v4a.load_extra_sklearn()
    df = v4a.prepare_dataset(args.input)
    feature_cols, _, _ = v3b.choose_columns(df)
    feature_cols = [c for c in feature_cols if c != "bt_token_sequence"]

    selector_rows = []
    choice_frames = []

    feature_choices, feature_row = v4a.train_eval_mode(df, "feature_only", feature_cols, sk)
    selector_rows.append(feature_row)
    choice_frames.append(feature_choices)

    for mode in ["transformer_only", "transformer_fused"]:
        choices, row = train_eval_transformer(df, mode, feature_cols, sk, args)
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
    write_report(report_output, summary, choices_output, feature_cols, args)

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
