#!/usr/bin/env python3
"""Small GPT multi-candidate BT generation demo.

This demo is intentionally separate from the main benchmark. It shows the
LLM-compatible loop:

Task -> GPT/mock generates multiple BTs -> KIOS symbolic evaluation -> demo
selector score breakdown -> GUI data export -> optional Isaac Gym job command.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = ROOT / "experiments" / "gpt_candidate_demo"
BT_BENCH = ROOT / "experiments" / "bt_selection_benchmark"
MODELS_DIR = BT_BENCH / "models"
FRONTEND_DIR = DEMO_DIR / "frontend"
RESULTS_DIR = DEMO_DIR / "results"
DEFAULT_TASK_SPECS = BT_BENCH / "task_specs_v6_hard_cases.json"
DEFAULT_DEMO_PICKLE = ROOT.parent / "datasets" / "ll4ma_isaac_minimal" / "demo_000001.pickle"
DEFAULT_DATA_ROOT = ROOT.parent / "datasets" / "gpt_candidate_demo"
DEFAULT_LEARNED_DATASET = BT_BENCH / "results" / "learned_selector_dataset_v3a.csv"
DEFAULT_ONLINE_MODEL_DIR = DEMO_DIR / "models" / "online_v5"
DEFAULT_LEARNED_V5_WEIGHTS = BT_BENCH / "results" / "v5_learned_ensemble_weights.csv"

sys.path.insert(0, str(BT_BENCH))
sys.path.insert(0, str(MODELS_DIR))
from evaluate_bt_candidates import CSV_COLUMNS, evaluate_candidate, make_bt, make_initial_states, predicate_to_text, read_json, write_json  # noqa: E402
import train_v3b_pairwise_selector as v3b  # noqa: E402
import train_v4a_bt_token_selector as v4a  # noqa: E402
import train_v4b_transformer_selector as v4b  # noqa: E402
import prepare_simulation_jobs as sim_jobs  # noqa: E402
import collect_simulation_metrics as sim_metrics  # noqa: E402


COLUMNS = ["case_id", "generator", "llm_model", "rank", "demo_selector_score", "symbolic_reliability_score", "symbolic_reliability_norm", "physical_feasibility_score", *CSV_COLUMNS]

ACTION_AND_BT_PROMPT = """
Available action:
- place(object, support)
  Preconditions: is_movable(object), can_be_placed_on(object, support)
  Effects: is_supported_by(object, support), is_above(object, support)

Return only JSON, no Markdown. Use this schema:
{
  "candidates": [
    {
      "candidate_id": "short_unique_name",
      "rationale": "why this BT differs from the others",
      "behavior_tree": {
        "summary": "...",
        "name": "selector: ...",
        "identifier": 1,
        "type_name": "selector",
        "children": []
      }
    }
  ]
}

Each behavior_tree should use a selector root with:
1. a condition branch for the target already being satisfied;
2. a sequence branch checking preconditions and executing place(object, support).

Important schema rules:
- Condition nodes must use "conditions", never "condition".
- Condition/effect facts must use object_name, property_name, property_value, status.
- Do not use predicate/args/value inside conditions or effects.
- Example condition fact: {"object_name": "block_3", "property_name": "is_supported_by", "property_value": "block_5", "status": true}
- Example action effect fact: {"object_name": "block_3", "property_name": "is_above", "property_value": "block_5", "status": true}

For physical diversity, include placement metadata on action nodes when useful:
"metadata": {"placement": {"strategy": "stable_center", "target_xy_offset_ratio": [0.0, 0.0]}}
""".strip()


def clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def compact_world(world: dict[str, Any]) -> dict[str, Any]:
    return {"objects": world.get("objects", []), "relations": world.get("relations", []), "constraints": world.get("constraints", [])}


def build_prompt(task: dict[str, Any], world: dict[str, Any], candidate_count: int) -> str:
    target = "; ".join(predicate_to_text(p) for p in task.get("target_predicates", []))
    return f"""You are generating multiple candidate Behavior Trees for a robot task-planning selector demo.

Task instruction:
{task['instruction']}

Target predicate:
{target}

Initial symbolic world:
{json.dumps(compact_world(world), indent=2)}

Generate exactly {candidate_count} diverse candidate BTs. Include at least:
- one physically stable candidate,
- one symbolically plausible but physically risky candidate,
- one candidate with a missing or weak precondition,
- one redundant or less efficient candidate.

Action and BT format knowledge:
{ACTION_AND_BT_PROMPT}
"""


def extract_json(text: str) -> dict[str, Any]:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            raise
        return json.loads(candidate[start : end + 1])


def generate_openai(prompt: str, model: str) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai Python package is not installed. Install it or use --generator mock.") from exc
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set. Use --generator mock or export your API key.")
    client = OpenAI()
    response = client.responses.create(model=model, input=prompt)
    return response.output_text


def mock_candidates(task: dict[str, Any], candidate_count: int) -> list[dict[str, Any]]:
    candidate_types = ["stable_center_bt", "symbolic_edge_bt", "unstable_over_edge_bt", "missing_precondition_bt", "redundant_bt", "wrong_support_bt"]
    out = []
    for candidate_type in candidate_types[:candidate_count]:
        out.append({
            "candidate_id": candidate_type,
            "rationale": "Mock GPT candidate generated from a controlled candidate type: " + candidate_type,
            "behavior_tree": make_bt(task, candidate_type),
        })
    return out


def normalize_id(text: str, index: int) -> str:
    value = re.sub(r"[^A-Za-z0-9_]+", "_", str(text or "").strip()).strip("_").lower()
    return value or f"gpt_candidate_{index:02d}"

def canonical_property(predicate: Any) -> str:
    name = str(predicate or "").strip()
    aliases = {
        "supported_by": "is_supported_by",
        "above": "is_above",
        "movable": "is_movable",
        "free": "is_free",
        "clear": "is_free",
        "placeable_on": "can_be_placed_on",
        "can_place_on": "can_be_placed_on",
    }
    return aliases.get(name, name)


def fact_from_predicate_dict(data: Any, *, default_status: bool = True) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    if "object_name" in data and "property_name" in data:
        return {
            "object_name": data.get("object_name"),
            "property_name": canonical_property(data.get("property_name")),
            "property_value": data.get("property_value"),
            "status": bool(data.get("status", default_status)),
        }

    predicate = data.get("predicate") or data.get("name") or data.get("property")
    args = data.get("args") or data.get("arguments") or []
    if isinstance(args, str):
        args = [part.strip() for part in args.split(",") if part.strip()]
    if not isinstance(args, list):
        args = []
    if not predicate or not args:
        return None

    prop = canonical_property(predicate)
    status = data.get("status", data.get("value", default_status))
    return {
        "object_name": args[0] if len(args) >= 1 else None,
        "property_name": prop,
        "property_value": args[1] if len(args) >= 2 else None,
        "status": bool(status),
    }


def normalize_fact_list(value: Any, *, default_status: bool = True) -> list[dict[str, Any]]:
    items = value if isinstance(value, list) else [value]
    facts = []
    for item in items:
        fact = fact_from_predicate_dict(item, default_status=default_status)
        if fact and fact.get("object_name") and fact.get("property_name"):
            facts.append(fact)
    return facts


def infer_action_effects(node: dict[str, Any]) -> list[dict[str, Any]]:
    action_text = " ".join(str(node.get(key, "")) for key in ["name", "summary", "action"])
    match = re.search(r"place\s*\(?\s*([A-Za-z0-9_]+)\s*,\s*([A-Za-z0-9_]+)\s*\)?", action_text)
    if not match:
        return []
    moved, support = match.group(1), match.group(2)
    return [
        {"object_name": moved, "property_name": "is_free", "property_value": None, "status": False},
        {"object_name": moved, "property_name": "is_supported_by", "property_value": support, "status": True},
        {"object_name": moved, "property_name": "is_above", "property_value": support, "status": True},
    ]


def normalize_bt_schema(node: Any) -> tuple[Any, int]:
    if not isinstance(node, dict):
        return node, 0

    out = dict(node)
    changes = 0
    type_name = str(out.get("type_name") or "").lower()

    if "condition" in out and "conditions" not in out:
        facts = normalize_fact_list(out.pop("condition"), default_status=True)
        if facts:
            out["conditions"] = facts
            changes += 1

    if "conditions" in out:
        facts = normalize_fact_list(out.get("conditions"), default_status=True)
        if facts != out.get("conditions"):
            out["conditions"] = facts
            changes += 1

    if "effects" in out:
        facts = normalize_fact_list(out.get("effects"), default_status=True)
        if facts != out.get("effects"):
            out["effects"] = facts
            changes += 1
    elif type_name == "action":
        inferred = infer_action_effects(out)
        if inferred:
            out["effects"] = inferred
            changes += 1

    children = out.get("children")
    if isinstance(children, list):
        normalized_children = []
        for child in children:
            normalized_child, child_changes = normalize_bt_schema(child)
            normalized_children.append(normalized_child)
            changes += child_changes
        out["children"] = normalized_children

    return out, changes


def load_generated_candidates(generator: str, prompt: str, task: dict[str, Any], case_dir: Path, model: str, candidate_count: int) -> tuple[str, list[dict[str, Any]]]:
    raw_path = case_dir / "raw_response.txt"
    if generator == "mock":
        data = {"candidates": mock_candidates(task, candidate_count)}
        raw = json.dumps(data, indent=2)
    elif generator == "existing":
        raw = raw_path.read_text(encoding="utf-8")
        data = extract_json(raw)
    elif generator == "openai":
        raw = generate_openai(prompt, model)
        data = extract_json(raw)
    else:
        raise ValueError(f"Unsupported generator: {generator}")

    case_dir.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(raw, encoding="utf-8")
    candidates = data.get("candidates", []) if isinstance(data, dict) else []
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Generated JSON must contain a non-empty candidates list.")
    normalized = []
    for index, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            continue
        bt = item.get("behavior_tree") or item.get("bt") or item.get("tree")
        if not isinstance(bt, dict):
            continue
        candidate_id = normalize_id(item.get("candidate_id") or item.get("name"), index)
        bt, schema_changes = normalize_bt_schema(bt)
        normalized.append({"candidate_id": candidate_id, "rationale": str(item.get("rationale", "")), "behavior_tree": bt, "schema_changes": schema_changes})
    if not normalized:
        raise ValueError("No valid behavior_tree objects were found in generated candidates.")
    return raw, normalized[:candidate_count]


def iter_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = [node]
    for child in node.get("children", []) or []:
        if isinstance(child, dict):
            nodes.extend(iter_nodes(child))
    return nodes


def placement_strategy(bt: dict[str, Any]) -> str:
    for node in iter_nodes(bt):
        if node.get("type_name") == "action":
            placement = node.get("metadata", {}).get("placement", {})
            if isinstance(placement, dict) and placement.get("strategy"):
                return str(placement.get("strategy"))
    return "unspecified"


def physical_prior(strategy: str, row: dict[str, Any]) -> float:
    if int(float(row.get("invalid_action_count") or 0)) > 0:
        return 0.0
    s = strategy.lower()
    if any(key in s for key in ["stable", "center", "final_stack"]):
        return 1.0
    if "edge" in s and "over" not in s:
        return 0.55
    if "corner" in s:
        return 0.45
    if any(key in s for key in ["collision", "over_edge", "far"]):
        return 0.1
    return 0.65


def symbolic_score(row: dict[str, Any]) -> float:
    n = lambda key, default=0.0: float(row.get(key) if row.get(key) not in [None, ""] else default)
    return (
        50 * n("symbolic_success")
        + 20 * n("goal_satisfaction")
        + 15 * n("precondition_coverage")
        - 10 * n("invalid_action_count")
        - 5 * n("condition_failure_count")
        - 0.5 * n("tree_size")
        - 0.3 * n("tree_depth")
        - 0.2 * n("bt_ticks")
        - 0.5 * n("action_count")
    )

def tree_compactness_score(row: dict[str, Any]) -> float:
    size = float(row.get("tree_size") or 0)
    depth = float(row.get("tree_depth") or 0)
    action_count = float(row.get("action_count") or 0)
    penalty = 0.06 * max(size - 5.0, 0.0) + 0.08 * max(depth - 3.0, 0.0) + 0.05 * max(action_count - 1.0, 0.0)
    return round(max(0.0, min(1.0, 1.0 - penalty)), 6)


def normalize_score_map(raw_scores: dict[str, float]) -> dict[str, float]:
    if not raw_scores:
        return {}
    values = [float(v) for v in raw_scores.values()]
    lo, hi = min(values), max(values)
    if abs(hi - lo) < 1e-9:
        return {key: 0.5 for key in raw_scores}
    return {key: round((float(value) - lo) / (hi - lo), 6) for key, value in raw_scores.items()}


def prepare_online_frame(rows: list[dict[str, Any]], task: dict[str, Any], case_id: str) -> Any:
    import pandas as pd

    online = pd.DataFrame(rows).copy()
    target = "; ".join(predicate_to_text(p) for p in task.get("target_predicates", []))
    online["task_id"] = task["task_id"]
    online["task_instruction"] = task["instruction"]
    online["target_predicate"] = target
    online["moved_object"] = task.get("moved_object")
    online["support_object"] = task.get("support_object")
    online["source_benchmark"] = "gpt_candidate_demo"
    online["benchmark"] = "gpt_candidate_demo"
    online["selector_group_id"] = case_id
    online["candidate_type"] = "gpt_candidate"
    online["sim_success"] = 0
    online["true_score"] = 0.0
    online["bt_token_sequence"] = online.apply(v4a.bt_token_sequence, axis=1)
    return online


def pairwise_feature_scores(train: Any, online: Any, feature_cols: list[str], sk: dict[str, Any]) -> dict[str, float]:
    import numpy as np
    import pandas as pd

    for col in feature_cols:
        if col not in online.columns:
            online[col] = np.nan
    numeric_cols = [c for c in feature_cols if pd.api.types.is_numeric_dtype(train[c])]
    categorical_cols = [c for c in feature_cols if c not in numeric_cols]
    for col in numeric_cols:
        online[col] = pd.to_numeric(online[col], errors="coerce")
    preprocessor = v3b.make_preprocessor(numeric_cols, categorical_cols, sk)
    x_train = preprocessor.fit_transform(train[feature_cols])
    pair_x, pair_y = v3b.make_pairwise_examples(x_train, train, sk)
    if pair_x is None or len(np.unique(pair_y)) < 2:
        return {str(row.candidate_id): 0.0 for row in online.itertuples()}
    model = sk["LogisticRegression"](max_iter=2000, class_weight="balanced")
    model.fit(pair_x, pair_y)
    x_online = preprocessor.transform(online[feature_cols])
    scores = x_online @ model.coef_.reshape(-1, 1)
    scores = np.asarray(scores).ravel().tolist()
    return {str(cid): float(score) for cid, score in zip(online["candidate_id"], scores)}


def transformer_online_scores(
    train: Any,
    online: Any,
    mode: str,
    feature_cols: list[str],
    sk: dict[str, Any],
    epochs: int,
    seed: int,
) -> dict[str, float]:
    import numpy as np
    import pandas as pd
    import torch
    from torch.utils.data import DataLoader, TensorDataset

    v4b.set_seed(seed)
    torch.set_num_threads(min(4, max(1, os.cpu_count() or 1)))
    device = torch.device("cpu")
    max_len = 96
    vocab = v4b.build_vocab(train["bt_token_sequence"], max_vocab_size=512)
    train_tokens = v4b.encode_sequences(train["bt_token_sequence"], vocab, max_len)
    online_tokens = v4b.encode_sequences(online["bt_token_sequence"], vocab, max_len)

    tab_train = np.zeros((len(train), 0), dtype=np.float32)
    tab_online = np.zeros((len(online), 0), dtype=np.float32)
    if mode == "transformer_fused_online":
        for col in feature_cols:
            if col not in online.columns:
                online[col] = np.nan
        numeric_cols = [c for c in feature_cols if pd.api.types.is_numeric_dtype(train[c])]
        categorical_cols = [c for c in feature_cols if c not in numeric_cols]
        for col in numeric_cols:
            online[col] = pd.to_numeric(online[col], errors="coerce")
        preprocessor = v3b.make_preprocessor(numeric_cols, categorical_cols, sk)
        tab_train = v4b.dense_array(preprocessor.fit_transform(train[feature_cols]))
        tab_online = v4b.dense_array(preprocessor.transform(online[feature_cols]))

    left, right, labels = v4b.make_pair_indices(train)
    if len(labels) == 0:
        return {str(row.candidate_id): 0.0 for row in online.itertuples()}

    model = v4b.BTTransformerRanker(
        vocab_size=len(vocab),
        tabular_dim=tab_train.shape[1],
        max_len=max_len,
        d_model=64,
        nhead=2,
        num_layers=1,
        dropout=0.1,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    criterion = torch.nn.BCEWithLogitsLoss()
    train_tokens_tensor = torch.tensor(train_tokens, dtype=torch.long)
    train_tab_tensor = torch.tensor(tab_train, dtype=torch.float32)
    dataset = TensorDataset(
        torch.tensor(left, dtype=torch.long),
        torch.tensor(right, dtype=torch.long),
        torch.tensor(labels, dtype=torch.float32),
    )
    loader = DataLoader(dataset, batch_size=256, shuffle=True)

    model.train()
    for _ in range(max(1, int(epochs))):
        for left_batch, right_batch, label_batch in loader:
            left_tokens = train_tokens_tensor[left_batch].to(device)
            right_tokens = train_tokens_tensor[right_batch].to(device)
            left_tab = train_tab_tensor[left_batch].to(device) if tab_train.shape[1] else None
            right_tab = train_tab_tensor[right_batch].to(device) if tab_train.shape[1] else None
            logits = model(left_tokens, left_tab) - model(right_tokens, right_tab)
            loss = criterion(logits, label_batch.to(device))
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

    model.eval()
    with torch.no_grad():
        token_batch = torch.tensor(online_tokens, dtype=torch.long, device=device)
        tab_batch = torch.tensor(tab_online, dtype=torch.float32, device=device) if tab_online.shape[1] else None
        scores = model(token_batch, tab_batch).detach().cpu().numpy().tolist()
    return {str(cid): float(score) for cid, score in zip(online["candidate_id"], scores)}



def required_model_files(model_dir: Path) -> list[Path]:
    return [
        model_dir / "metadata.json",
        model_dir / "feature_only.pkl",
        model_dir / "transformer_only.pt",
        model_dir / "transformer_fused.pt",
    ]


def saved_online_models_available(model_dir: Path) -> bool:
    return all(path.exists() for path in required_model_files(model_dir))


def online_feature_columns(train: Any) -> tuple[list[str], list[str], list[str]]:
    import pandas as pd

    feature_cols, _, _ = v3b.choose_columns(train)
    feature_cols = [c for c in feature_cols if c != "bt_token_sequence"]
    numeric_cols = [c for c in feature_cols if pd.api.types.is_numeric_dtype(train[c])]
    categorical_cols = [c for c in feature_cols if c not in numeric_cols]
    return feature_cols, numeric_cols, categorical_cols


def coerce_online_columns(online: Any, feature_cols: list[str], numeric_cols: list[str]) -> Any:
    import numpy as np
    import pandas as pd

    out = online.copy()
    for col in feature_cols:
        if col not in out.columns:
            out[col] = np.nan
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def train_feature_artifact(train: Any, feature_cols: list[str], numeric_cols: list[str], categorical_cols: list[str], sk: dict[str, Any]) -> dict[str, Any]:
    import numpy as np

    preprocessor = v3b.make_preprocessor(numeric_cols, categorical_cols, sk)
    x_train = preprocessor.fit_transform(train[feature_cols])
    pair_x, pair_y = v3b.make_pairwise_examples(x_train, train, sk)
    model = sk["LogisticRegression"](max_iter=2000, class_weight="balanced")
    if pair_x is None or len(np.unique(pair_y)) < 2:
        model = None
    else:
        model.fit(pair_x, pair_y)
    return {"preprocessor": preprocessor, "model": model}


def train_transformer_artifact(
    train: Any,
    mode: str,
    feature_cols: list[str],
    numeric_cols: list[str],
    categorical_cols: list[str],
    sk: dict[str, Any],
    epochs: int,
    seed: int,
) -> dict[str, Any]:
    import numpy as np
    import torch
    from torch.utils.data import DataLoader, TensorDataset

    v4b.set_seed(seed)
    torch.set_num_threads(min(4, max(1, os.cpu_count() or 1)))
    max_len = 96
    device = torch.device("cpu")
    vocab = v4b.build_vocab(train["bt_token_sequence"], max_vocab_size=512)
    train_tokens = v4b.encode_sequences(train["bt_token_sequence"], vocab, max_len)

    preprocessor = None
    tab_train = np.zeros((len(train), 0), dtype=np.float32)
    if mode == "transformer_fused_online":
        preprocessor = v3b.make_preprocessor(numeric_cols, categorical_cols, sk)
        tab_train = v4b.dense_array(preprocessor.fit_transform(train[feature_cols]))

    left, right, labels = v4b.make_pair_indices(train)
    model = v4b.BTTransformerRanker(
        vocab_size=len(vocab),
        tabular_dim=tab_train.shape[1],
        max_len=max_len,
        d_model=64,
        nhead=2,
        num_layers=1,
        dropout=0.1,
    ).to(device)

    if len(labels):
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        criterion = torch.nn.BCEWithLogitsLoss()
        train_tokens_tensor = torch.tensor(train_tokens, dtype=torch.long)
        train_tab_tensor = torch.tensor(tab_train, dtype=torch.float32)
        dataset = TensorDataset(
            torch.tensor(left, dtype=torch.long),
            torch.tensor(right, dtype=torch.long),
            torch.tensor(labels, dtype=torch.float32),
        )
        loader = DataLoader(dataset, batch_size=256, shuffle=True)
        model.train()
        for _ in range(max(1, int(epochs))):
            for left_batch, right_batch, label_batch in loader:
                left_tokens = train_tokens_tensor[left_batch].to(device)
                right_tokens = train_tokens_tensor[right_batch].to(device)
                left_tab = train_tab_tensor[left_batch].to(device) if tab_train.shape[1] else None
                right_tab = train_tab_tensor[right_batch].to(device) if tab_train.shape[1] else None
                logits = model(left_tokens, left_tab) - model(right_tokens, right_tab)
                loss = criterion(logits, label_batch.to(device))
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

    return {
        "model": model,
        "vocab": vocab,
        "preprocessor": preprocessor,
        "tabular_dim": int(tab_train.shape[1]),
        "max_len": max_len,
        "d_model": 64,
        "nhead": 2,
        "num_layers": 1,
        "dropout": 0.1,
    }


def train_and_save_online_v5_models(learned_dataset: Path, model_dir: Path, epochs: int) -> dict[str, Any]:
    import pickle
    import torch

    sk = v4a.load_extra_sklearn()
    train = v4a.prepare_dataset(str(learned_dataset)).reset_index(drop=True)
    feature_cols, numeric_cols, categorical_cols = online_feature_columns(train)
    model_dir.mkdir(parents=True, exist_ok=True)

    feature_artifact = train_feature_artifact(train, feature_cols, numeric_cols, categorical_cols, sk)
    with (model_dir / "feature_only.pkl").open("wb") as file:
        pickle.dump(feature_artifact, file)

    transformer_only = train_transformer_artifact(train, "transformer_only_online", feature_cols, numeric_cols, categorical_cols, sk, epochs, seed=11)
    transformer_fused = train_transformer_artifact(train, "transformer_fused_online", feature_cols, numeric_cols, categorical_cols, sk, epochs, seed=17)

    for name, artifact in [("transformer_only", transformer_only), ("transformer_fused", transformer_fused)]:
        torch.save(
            {
                "state_dict": artifact["model"].state_dict(),
                "vocab": artifact["vocab"],
                "preprocessor": artifact["preprocessor"],
                "tabular_dim": artifact["tabular_dim"],
                "max_len": artifact["max_len"],
                "d_model": artifact["d_model"],
                "nhead": artifact["nhead"],
                "num_layers": artifact["num_layers"],
                "dropout": artifact["dropout"],
            },
            model_dir / f"{name}.pt",
        )

    metadata = {
        "result": "success",
        "model_dir": str(model_dir),
        "learned_dataset": str(learned_dataset),
        "rows": int(len(train)),
        "groups": int(train["selector_group_id"].nunique()),
        "feature_cols": feature_cols,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
        "online_epochs": int(epochs),
        "selectors": ["feature_only_online", "transformer_only_online", "transformer_fused_online"],
    }
    (model_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def score_feature_artifact(model_dir: Path, online: Any, feature_cols: list[str], numeric_cols: list[str]) -> dict[str, float]:
    import pickle
    import numpy as np

    with (model_dir / "feature_only.pkl").open("rb") as file:
        artifact = pickle.load(file)
    model = artifact.get("model")
    if model is None:
        return {str(row.candidate_id): 0.0 for row in online.itertuples()}
    online = coerce_online_columns(online, feature_cols, numeric_cols)
    x_online = artifact["preprocessor"].transform(online[feature_cols])
    scores = x_online @ model.coef_.reshape(-1, 1)
    scores = np.asarray(scores).ravel().tolist()
    return {str(cid): float(score) for cid, score in zip(online["candidate_id"], scores)}


def score_transformer_artifact(model_dir: Path, filename: str, online: Any, feature_cols: list[str], numeric_cols: list[str]) -> dict[str, float]:
    import torch

    artifact = torch.load(model_dir / filename, map_location="cpu", weights_only=False)
    online_tokens = v4b.encode_sequences(online["bt_token_sequence"], artifact["vocab"], int(artifact["max_len"]))
    tab_online = None
    if int(artifact.get("tabular_dim", 0)):
        online = coerce_online_columns(online, feature_cols, numeric_cols)
        tab_online = v4b.dense_array(artifact["preprocessor"].transform(online[feature_cols]))

    model = v4b.BTTransformerRanker(
        vocab_size=len(artifact["vocab"]),
        tabular_dim=int(artifact.get("tabular_dim", 0)),
        max_len=int(artifact["max_len"]),
        d_model=int(artifact["d_model"]),
        nhead=int(artifact["nhead"]),
        num_layers=int(artifact["num_layers"]),
        dropout=float(artifact["dropout"]),
    )
    model.load_state_dict(artifact["state_dict"])
    model.eval()
    with torch.no_grad():
        token_batch = torch.tensor(online_tokens, dtype=torch.long)
        tab_batch = torch.tensor(tab_online, dtype=torch.float32) if tab_online is not None else None
        scores = model(token_batch, tab_batch).detach().cpu().numpy().tolist()
    return {str(cid): float(score) for cid, score in zip(online["candidate_id"], scores)}


def score_saved_online_v5_models(rows: list[dict[str, Any]], task: dict[str, Any], case_id: str, model_dir: Path) -> dict[str, Any]:
    metadata = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
    online = prepare_online_frame(rows, task, case_id)
    feature_cols = list(metadata["feature_cols"])
    numeric_cols = list(metadata["numeric_cols"])
    raw_by_selector = {
        "feature_only_online": score_feature_artifact(model_dir, online.copy(), feature_cols, numeric_cols),
        "transformer_only_online": score_transformer_artifact(model_dir, "transformer_only.pt", online.copy(), feature_cols, numeric_cols),
        "transformer_fused_online": score_transformer_artifact(model_dir, "transformer_fused.pt", online.copy(), feature_cols, numeric_cols),
    }
    normalized_by_selector = {selector: normalize_score_map(scores) for selector, scores in raw_by_selector.items()}
    for row in rows:
        cid = str(row["candidate_id"])
        row["learned_model_scores"] = {selector: round(raw_by_selector[selector].get(cid, 0.0), 6) for selector in raw_by_selector}
        row["learned_model_scores_norm"] = {selector: normalized_by_selector[selector].get(cid, 0.0) for selector in normalized_by_selector}
    metadata = dict(metadata)
    metadata["runtime_mode"] = "loaded_saved_models"
    return metadata

def add_online_ranker_scores(
    rows: list[dict[str, Any]],
    task: dict[str, Any],
    case_id: str,
    learned_dataset: Path,
    online_epochs: int,
    model_dir: Path,
    force_train_ranker: bool = False,
) -> dict[str, Any]:
    if force_train_ranker or not saved_online_models_available(model_dir):
        metadata = train_and_save_online_v5_models(learned_dataset, model_dir, online_epochs)
        metadata["runtime_mode"] = "trained_and_saved_models"
    else:
        metadata = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
        metadata["runtime_mode"] = "loaded_saved_models"
    info = score_saved_online_v5_models(rows, task, case_id, model_dir)
    info["runtime_mode"] = metadata["runtime_mode"]
    return info




def safe_shell_command(command: str) -> str:
    return command


def prepare_gpt_simulation_jobs(
    eval_path: Path,
    demo_pickle: Path,
    timestep: int,
    case_id: str,
) -> dict[str, Any]:
    headless_dir = DEMO_DIR / "simulation_jobs" / case_id / "headless"
    gui_dir = DEMO_DIR / "simulation_jobs" / case_id / "gui"
    data_root = DEFAULT_DATA_ROOT / case_id

    base_kwargs = {
        "evaluations": eval_path,
        "demo_pickle": demo_pickle,
        "timestep": timestep,
        "base_config": sim_jobs.DEFAULT_BASE_CONFIG,
        "data_root": data_root,
        "ee_z_offset": 0.10988,
        "n_demos": 1,
    }
    headless_args = argparse.Namespace(**base_kwargs, output_dir=headless_dir, gui=False, headless=True)
    gui_args = argparse.Namespace(**base_kwargs, output_dir=gui_dir, gui=True, headless=False)
    headless_manifest = sim_jobs.prepare_jobs(headless_args)
    gui_manifest = sim_jobs.prepare_jobs(gui_args)

    metric_output = RESULTS_DIR / "gpt_candidate_evaluations_with_sim.csv"
    metric_args = argparse.Namespace(
        evaluations=eval_path,
        manifest=headless_dir / "simulation_jobs_manifest.csv",
        output=metric_output,
        demo_pickle=demo_pickle,
        timestep=timestep,
        final_timestep=999999,
        ee_z_offset=0.10988,
        displacement_threshold=0.02,
    )
    sim_rows = sim_metrics.collect_metrics(metric_args)
    sim_metrics.write_csv(metric_output, sim_rows, list(sim_rows[0].keys()) if sim_rows else [])

    by_candidate: dict[str, dict[str, Any]] = {}
    for row in headless_manifest:
        by_candidate.setdefault(row["candidate_id"], {})["headless"] = row
    for row in gui_manifest:
        by_candidate.setdefault(row["candidate_id"], {})["gui"] = row
    sim_by_candidate = {row["candidate_id"]: row for row in sim_rows}
    for candidate_id, value in by_candidate.items():
        value["metrics"] = sim_by_candidate.get(candidate_id, {})

    done_rows = [row for row in sim_rows if row.get("simulation_status") == "done"]
    oracle = None
    if done_rows:
        oracle_row = max(done_rows, key=lambda row: float(row.get("score") or 0.0))
        oracle = {
            "candidate_id": oracle_row.get("candidate_id"),
            "score": float(oracle_row.get("score") or 0.0),
            "sim_success": int(float(oracle_row.get("sim_success") or 0)),
            "simulation_status": oracle_row.get("simulation_status"),
        }

    return {
        "headless_dir": str(headless_dir),
        "gui_dir": str(gui_dir),
        "data_root": str(data_root),
        "headless_manifest": str(headless_dir / "simulation_jobs_manifest.csv"),
        "gui_manifest": str(gui_dir / "simulation_jobs_manifest.csv"),
        "headless_run_script": str(headless_dir / "run_jobs.sh"),
        "gui_run_script": str(gui_dir / "run_jobs.sh"),
        "metrics_output": str(metric_output),
        "run_all_headless": f"bash {headless_dir / 'run_jobs.sh'}",
        "run_all_gui": f"bash {gui_dir / 'run_jobs.sh'}",
        "candidates": by_candidate,
        "oracle": oracle,
        "simulation_status": {status: sum(1 for row in sim_rows if row.get("simulation_status") == status) for status in sorted({row.get("simulation_status") for row in sim_rows})},
    }


def enrich_rows_with_simulation(rows: list[dict[str, Any]], simulation: dict[str, Any]) -> None:
    for row in rows:
        info = simulation.get("candidates", {}).get(row["candidate_id"], {})
        metrics = info.get("metrics", {}) or {}
        row["simulation_status"] = metrics.get("simulation_status", row.get("simulation_status", "pending"))
        if metrics.get("sim_success") not in [None, ""]:
            row["sim_success"] = int(float(metrics.get("sim_success") or 0))
        for key in ["final_position_error", "object_displacement_error", "contact_violation_proxy", "support_stability", "score"]:
            if metrics.get(key) not in [None, ""]:
                try:
                    row[key] = float(metrics[key])
                except Exception:
                    row[key] = metrics[key]



def full_isaac_command(run_command: str) -> str:
    return " && ".join([
        "deactivate 2>/dev/null || true",
        "source /opt/ros/noetic/setup.bash",
        "source /home/theshy/projects/mycode/ll4ma_catkin_ws/devel/setup.bash",
        f"cd {sim_jobs.shell_quote(sim_jobs.LL4MA_SCRIPT_DIR)}",
        run_command,
    ])


def visual_replay_command(candidate: str = "selected") -> str:
    script = DEMO_DIR / "run_visual_replay.py"
    demo_data = FRONTEND_DIR / "demo_data.json"
    return " && ".join([
        "export PATH=/usr/lib/wsl/lib:$PATH",
        "export LD_LIBRARY_PATH=/usr/lib/wsl/lib:$LD_LIBRARY_PATH",
        "export VK_ICD_FILENAMES=${VK_ICD_FILENAMES:-/usr/share/vulkan/icd.d/dzn_icd.x86_64.json}",
        "export MESA_D3D12_DEFAULT_ADAPTER_NAME=${MESA_D3D12_DEFAULT_ADAPTER_NAME:-NVIDIA}",
        "unset LIBGL_ALWAYS_SOFTWARE",
        f"cd {sim_jobs.shell_quote(ROOT)}",
        f"python3 {sim_jobs.shell_quote(script)} --demo-data {sim_jobs.shell_quote(demo_data)} --candidate {sim_jobs.shell_quote(candidate)} --loop --simple-arm",
    ])

def add_oracle_scores(rows: list[dict[str, Any]], simulation: dict[str, Any]) -> bool:
    done = [row for row in rows if row.get("simulation_status") == "done" and row.get("score") not in [None, ""]]
    if not done:
        return False
    scores = {row["candidate_id"]: float(row.get("score") or 0.0) for row in done}
    normalized = normalize_score_map(scores)
    for row in rows:
        row.setdefault("selector_scores", {})
        if row["candidate_id"] in normalized:
            row["selector_scores"]["oracle"] = normalized[row["candidate_id"]]
        else:
            row["selector_scores"]["oracle"] = -1.0
    return True

def load_learned_v5_weights(path: Path) -> dict[str, dict[str, float]]:
    if not path.exists():
        return {}
    weights: dict[str, dict[str, float]] = {}
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for item in reader:
            selector = str(item.get("selector", ""))
            feature = str(item.get("feature", ""))
            if not selector or not feature:
                continue
            try:
                weight = float(item.get("weight", 0.0) or 0.0)
            except Exception:
                weight = 0.0
            weights.setdefault(selector, {})[feature] = weight
    return weights


def learned_v5_feature_values(row: dict[str, Any]) -> dict[str, float]:
    votes = row.get("selector_votes", {}) or {}
    symbolic = float(row.get("symbolic_reliability_norm") or 0.0)
    simulation = float(row.get("simulation_reliability_norm", row.get("physical_feasibility_score", 0.0)) or 0.0)
    return {
        "vote_feature_only": float(votes.get("feature_only_online", 0.0) or 0.0),
        "vote_transformer_fused": float(votes.get("transformer_fused_online", 0.0) or 0.0),
        "vote_transformer_only": float(votes.get("transformer_only_online", 0.0) or 0.0),
        "vote_symbolic_only": float(votes.get("symbolic_only", 0.0) or 0.0),
        "vote_shortest_tree": float(votes.get("shortest_tree", 0.0) or 0.0),
        "symbolic_reliability_norm": symbolic,
        "simulation_reliability_norm": simulation,
    }


def learned_v5_score_from_weights(row: dict[str, Any], weights: dict[str, float]) -> tuple[float, dict[str, float]]:
    values = learned_v5_feature_values(row)
    total = float(weights.get("intercept", 0.0) or 0.0)
    contributions = {"intercept": total}
    for feature, value in values.items():
        weight = float(weights.get(feature, 0.0) or 0.0)
        contribution = weight * value
        contributions[feature] = contribution
        total += contribution
    return total, contributions


def minmax_scores(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
    raw = {str(row["candidate_id"]): float(row.get(key, 0.0) or 0.0) for row in rows}
    return normalize_score_map(raw)


def add_simulation_reliability_norm(rows: list[dict[str, Any]]) -> None:
    sim_scores = []
    has_done = False
    for row in rows:
        status = str(row.get("simulation_status", ""))
        if status == "done" and row.get("sim_success") not in [None, ""]:
            has_done = True
            sim_success = float(row.get("sim_success") or 0.0)
            final_error = float(row.get("final_position_error") or 0.0)
            displacement = float(row.get("object_displacement_error") or 0.0)
            contact = float(row.get("contact_violation_proxy") or 0.0)
            score = 100 * sim_success - 10 * final_error - 5 * displacement - 10 * contact
        else:
            score = float(row.get("physical_feasibility_score") or 0.0)
        sim_scores.append(score)
    lo, hi = min(sim_scores), max(sim_scores)
    for row, score in zip(rows, sim_scores):
        if has_done and abs(hi - lo) > 1e-9:
            row["simulation_reliability_norm"] = round((score - lo) / (hi - lo), 6)
        else:
            row["simulation_reliability_norm"] = round(float(row.get("physical_feasibility_score") or 0.0), 6)
        row["simulation_reliability_score"] = round(score, 6)


def add_learned_v5_scores(rows: list[dict[str, Any]], weights_by_selector: dict[str, dict[str, float]]) -> None:
    selector_map = {
        "v5_learned_full": "v5_learned_full",
        "v5_learned_no_simulation": "v5_no_simulation_reliability",
        "v5_learned_no_transformer": "v5_no_transformer_votes",
        "v5_learned_no_symbolic": "v5_no_symbolic_reliability",
    }
    raw_by_selector: dict[str, dict[str, float]] = {}
    for public_name, weight_name in selector_map.items():
        weights = weights_by_selector.get(weight_name, {})
        if not weights:
            continue
        raw_by_selector[public_name] = {}
        for row in rows:
            raw_score, contributions = learned_v5_score_from_weights(row, weights)
            row.setdefault("learned_v5_raw_scores", {})[public_name] = round(raw_score, 6)
            row.setdefault("learned_v5_contributions", {})[public_name] = {k: round(v, 6) for k, v in contributions.items()}
            raw_by_selector[public_name][str(row["candidate_id"])] = raw_score
    for public_name, raw_scores in raw_by_selector.items():
        normalized = normalize_score_map(raw_scores)
        for row in rows:
            cid = str(row["candidate_id"] )
            row["selector_scores"][public_name] = round(normalized.get(cid, 0.0), 6)
    for row in rows:
        row["selector_scores"]["manual_v5"] = row["selector_scores"].get("v5_ensemble_online", 0.0)


def selector_scores(row: dict[str, Any]) -> dict[str, float]:
    symbolic = float(row.get("symbolic_reliability_norm") or 0.0)
    physical = float(row.get("physical_feasibility_score") or 0.0)
    compact = tree_compactness_score(row)
    learned_norm = row.get("learned_model_scores_norm", {}) or {}
    return {
        "feature_only_online": round(float(learned_norm.get("feature_only_online", 0.0)), 6),
        "transformer_only_online": round(float(learned_norm.get("transformer_only_online", 0.0)), 6),
        "transformer_fused_online": round(float(learned_norm.get("transformer_fused_online", 0.0)), 6),
        "gpt_demo_selector": round(0.55 * symbolic + 0.45 * physical, 6),
        "symbolic_only": round(symbolic, 6),
        "physical_only": round(physical, 6),
        "shortest_tree": round(compact, 6),
    }


def add_v5_ensemble_scores(rows: list[dict[str, Any]]) -> None:
    vote_weights = {
        "feature_only_online": 0.30,
        "transformer_fused_online": 0.35,
        "transformer_only_online": 0.15,
        "symbolic_only": 0.10,
        "shortest_tree": 0.05,
    }
    winner_by_selector = {}
    for selector in vote_weights:
        winner = max(rows, key=lambda item: item["selector_scores"].get(selector, 0.0))
        winner_by_selector[selector] = str(winner["candidate_id"])

    for row in rows:
        cid = str(row["candidate_id"])
        symbolic = float(row.get("symbolic_reliability_norm") or 0.0)
        physical = float(row.get("physical_feasibility_score") or 0.0)
        soft_vote = sum(weight * float(row["selector_scores"].get(selector, 0.0)) for selector, weight in vote_weights.items())
        gated_vote = soft_vote * max(0.0, min(1.0, symbolic))
        row["selector_vote_raw"] = round(soft_vote, 6)
        row["symbolic_gate"] = round(symbolic, 6)
        row["selector_vote_score"] = round(gated_vote, 6)
        row["selector_votes"] = {selector: 1 if winner == cid else 0 for selector, winner in winner_by_selector.items()}
        row["selector_vote_components"] = {
            selector: round(weight * float(row["selector_scores"].get(selector, 0.0)), 6)
            for selector, weight in vote_weights.items()
        }
        row["selector_scores"]["v5_ensemble_online"] = round(0.55 * gated_vote + 0.20 * symbolic + 0.25 * physical, 6)


def breakdown_for_selector(selector: str, row: dict[str, Any]) -> list[dict[str, Any]]:
    symbolic = float(row.get("symbolic_reliability_norm") or 0.0)
    physical = float(row.get("physical_feasibility_score") or 0.0)
    compact = tree_compactness_score(row)
    raw_symbolic = row.get("symbolic_reliability_score")
    learned_raw = row.get("learned_model_scores", {}) or {}
    learned_norm = row.get("learned_model_scores_norm", {}) or {}
    if selector in {"v5_learned_full", "v5_learned_no_simulation", "v5_learned_no_transformer", "v5_learned_no_symbolic"}:
        feature_values = learned_v5_feature_values(row)
        contributions = (row.get("learned_v5_contributions", {}) or {}).get(selector, {}) or {}
        raw_score = (row.get("learned_v5_raw_scores", {}) or {}).get(selector, 0.0)
        labels = {
            "vote_feature_only": "Feature-only selector vote",
            "vote_transformer_fused": "Transformer-fused selector vote",
            "vote_transformer_only": "Transformer-only selector vote",
            "vote_symbolic_only": "Symbolic-only selector vote",
            "vote_shortest_tree": "Shortest-tree selector vote",
            "symbolic_reliability_norm": "KIOS symbolic reliability",
            "simulation_reliability_norm": "Simulation/physical reliability",
            "intercept": "Learned intercept",
        }
        details = {
            "vote_feature_only": "1 if feature_only chose this candidate, otherwise 0.",
            "vote_transformer_fused": "1 if Transformer+tabular selector chose this candidate, otherwise 0.",
            "vote_transformer_only": "1 if BT-token Transformer selector chose this candidate, otherwise 0.",
            "vote_symbolic_only": "1 if symbolic-only selector chose this candidate, otherwise 0.",
            "vote_shortest_tree": "1 if shortest-tree baseline chose this candidate, otherwise 0.",
            "symbolic_reliability_norm": "Normalized symbolic/KIOS reliability within the generated candidate set.",
            "simulation_reliability_norm": "Uses Isaac Gym reliability when available; otherwise uses the demo physical prior.",
            "intercept": "Bias term learned from pairwise ranking supervision.",
        }
        rows_out = []
        for feature, contribution in contributions.items():
            raw_value = 1.0 if feature == "intercept" else feature_values.get(feature, 0.0)
            weight = contribution if feature == "intercept" else (contribution / raw_value if abs(float(raw_value or 0.0)) > 1e-12 else 0.0)
            rows_out.append({"component": labels.get(feature, feature), "raw": round(float(raw_value), 6), "weight": round(float(weight), 6), "contribution": round(float(contribution), 6), "detail": details.get(feature, "Learned V5 feature contribution.")})
        rows_out.append({"component": "Raw learned V5 score", "raw": "-", "weight": "-", "contribution": round(float(raw_score), 6), "detail": "Unnormalized linear score before per-candidate-set min-max normalization."})
        rows_out.append({"component": "Normalized selector score", "raw": "-", "weight": "-", "contribution": row["selector_scores"].get(selector, 0.0), "detail": "Score used for ranking in the GPT demo page."})
        return rows_out
    if selector == "manual_v5":
        selector = "v5_ensemble_online"
    if selector == "v5_ensemble_online":
        votes = row.get("selector_votes", {}) or {}
        return [
            {"component": "Selector vote score", "raw": row.get("selector_vote_score", 0.0), "weight": 0.55, "contribution": round(0.55 * float(row.get("selector_vote_score", 0.0)), 6), "detail": "Soft sub-selector agreement after KIOS symbolic safety gate."},
            {"component": "Raw soft vote", "raw": row.get("selector_vote_raw", 0.0), "weight": "gate", "contribution": row.get("symbolic_gate", 0.0), "detail": "The learned/Transformer vote is multiplied by symbolic reliability before entering V5."},
            {"component": "KIOS symbolic reliability", "raw": raw_symbolic, "weight": 0.20, "contribution": round(0.20 * symbolic, 6), "detail": "Symbolic execution success, goal satisfaction, precondition coverage, failures, and BT cost."},
            {"component": "Online physical reliability", "raw": physical, "weight": 0.25, "contribution": round(0.25 * physical, 6), "detail": "Physical feasibility prior for GPT candidates; Isaac Gym can replace this field after simulation."},
            {"component": "Hard winner flags", "raw": json.dumps(votes, sort_keys=True), "weight": "-", "contribution": "-", "detail": "For explanation only: 1 means this candidate was the top candidate under that sub-selector."},
            {"component": "Soft vote components", "raw": json.dumps(row.get("selector_vote_components", {}), sort_keys=True), "weight": "-", "contribution": "-", "detail": "Actual weighted sub-selector contributions used by online V5."},
            {"component": "Final V5 online score", "raw": "-", "weight": "-", "contribution": row["selector_scores"][selector], "detail": "This is the deployable online V5 selector used by the GPT demo."},
        ]
    if selector in {"feature_only_online", "transformer_only_online", "transformer_fused_online"}:
        names = {
            "feature_only_online": "Pairwise tabular feature ranker",
            "transformer_only_online": "BT-token Transformer ranker",
            "transformer_fused_online": "Transformer + tabular fused ranker",
        }
        return [
            {"component": names[selector], "raw": learned_raw.get(selector, 0.0), "weight": 1.0, "contribution": learned_norm.get(selector, 0.0), "detail": "Online score from a model trained on the full simulated benchmark dataset during this demo run."},
        ]
    if selector == "gpt_demo_selector":
        return [
            {"component": "Symbolic reliability", "raw": raw_symbolic, "weight": 0.55, "contribution": round(0.55 * symbolic, 6), "detail": "KIOS symbolic execution and precondition coverage."},
            {"component": "Physical feasibility", "raw": physical, "weight": 0.45, "contribution": round(0.45 * physical, 6), "detail": "Demo-time physical prior from placement strategy."},
            {"component": "Final demo score", "raw": "-", "weight": "-", "contribution": row["selector_scores"][selector], "detail": "Earlier lightweight GPT demo selector."},
        ]
    if selector == "symbolic_only":
        return [{"component": "Symbolic reliability only", "raw": raw_symbolic, "weight": 1.0, "contribution": symbolic, "detail": "Uses only KIOS symbolic metrics; physical placement risk and learned ranking are ignored."}]
    if selector == "physical_only":
        return [{"component": "Physical feasibility only", "raw": physical, "weight": 1.0, "contribution": physical, "detail": "Uses only placement strategy prior; symbolic BT quality and learned ranking are ignored."}]
    if selector == "shortest_tree":
        return [{"component": "BT compactness only", "raw": compact, "weight": 1.0, "contribution": compact, "detail": "A weak baseline that prefers smaller/shallower BTs."}]
    if selector == "oracle":
        return [
            {"component": "Isaac Gym true score", "raw": row.get("score", "pending"), "weight": "oracle", "contribution": row.get("selector_scores", {}).get("oracle", -1), "detail": "Oracle is available only after running candidate Isaac Gym jobs and collecting simulation metrics."},
            {"component": "Simulation success", "raw": row.get("sim_success", "pending"), "weight": "-", "contribution": "-", "detail": "Read from generated demo_000001.pickle when the job has finished."},
            {"component": "Simulation status", "raw": row.get("simulation_status", "pending"), "weight": "-", "contribution": "-", "detail": "pending means the command has been generated but the Isaac Gym job has not produced a result yet."},
        ]
    return []

def compact_tree(node: Any) -> dict[str, Any]:
    if not isinstance(node, dict):
        return {"label": str(node), "type": "value", "children": []}
    children = node.get("children") or []
    return {
        "label": str(node.get("summary") or node.get("name") or node.get("type_name") or "node"),
        "type": str(node.get("type_name") or "node"),
        "facts": [{"key": k, "value": node[k]} for k in ["conditions", "effects", "metadata"] if node.get(k) not in [None, "", [], {}]],
        "children": [compact_tree(child) for child in children if isinstance(child, dict)],
    }


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generator", choices=["mock", "existing", "openai"], default="mock")
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--task-specs", type=Path, default=DEFAULT_TASK_SPECS)
    parser.add_argument("--task-id", default="hard_physical_place_block3_on_block5")
    parser.add_argument("--demo-pickle", type=Path, default=DEFAULT_DEMO_PICKLE)
    parser.add_argument("--timestep", type=int, default=0)
    parser.add_argument("--candidate-count", type=int, default=4)
    parser.add_argument("--output-dir", type=Path, default=DEMO_DIR / "outputs")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--frontend-output", type=Path, default=FRONTEND_DIR / "demo_data.json")
    parser.add_argument("--learned-dataset", type=Path, default=DEFAULT_LEARNED_DATASET)
    parser.add_argument("--online-epochs", type=int, default=10)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_ONLINE_MODEL_DIR)
    parser.add_argument("--learned-v5-weights", type=Path, default=DEFAULT_LEARNED_V5_WEIGHTS)
    parser.add_argument("--force-train-ranker", action="store_true")
    args = parser.parse_args()

    task_specs = read_json(args.task_specs)
    tasks = {task["task_id"]: task for task in task_specs.get("tasks", [])}
    if args.task_id not in tasks:
        raise KeyError(f"Unknown task_id {args.task_id}. Available: {sorted(tasks)}")
    task = tasks[args.task_id]
    initial_state_id, initial_timestep, world = make_initial_states(args.demo_pickle, args.timestep, 1)[0]
    case_id = f"{task['task_id']}__{initial_state_id}"
    case_dir = args.output_dir / case_id
    prompt = build_prompt(task, world, args.candidate_count)
    prompt_path = case_dir / "prompt.txt"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")

    raw, generated = load_generated_candidates(args.generator, prompt, task, case_dir, args.model, args.candidate_count)
    candidate_root = case_dir / "candidates"
    rows = []
    bt_json_by_id = {}
    rationale_by_id = {}
    for item in generated:
        bt_path = candidate_root / f"{item['candidate_id']}.json"
        write_json(bt_path, item["behavior_tree"])
        entry = {"task": task, "candidate_id": item["candidate_id"], "candidate_type": "gpt_candidate", "bt_path": bt_path.resolve()}
        row = evaluate_candidate(entry, world, max_ticks=10, initial_state_id=initial_state_id, initial_timestep=initial_timestep)
        row["case_id"] = case_id
        row["generator"] = args.generator
        row["llm_model"] = args.model
        row["rank"] = 0
        rows.append(row)
        bt_json_by_id[item["candidate_id"]] = item["behavior_tree"]
        rationale_by_id[item["candidate_id"]] = item.get("rationale", "")
        row["schema_changes"] = item.get("schema_changes", 0)

    raw_symbolic = [symbolic_score(row) for row in rows]
    lo, hi = min(raw_symbolic), max(raw_symbolic)
    for row, raw_score in zip(rows, raw_symbolic):
        norm = 0.0 if abs(hi - lo) < 1e-9 else (raw_score - lo) / (hi - lo)
        strategy = placement_strategy(bt_json_by_id[row["candidate_id"]])
        prior = physical_prior(strategy, row)
        row["symbolic_reliability_score"] = round(raw_score, 6)
        row["symbolic_reliability_norm"] = round(norm, 6)
        row["physical_feasibility_score"] = round(prior, 6)

    online_ranker_info = add_online_ranker_scores(rows, task, case_id, args.learned_dataset, args.online_epochs, args.model_dir, args.force_train_ranker)
    learned_v5_weights = load_learned_v5_weights(args.learned_v5_weights)
    add_simulation_reliability_norm(rows)
    for row in rows:
        row["selector_scores"] = selector_scores(row)
    add_v5_ensemble_scores(rows)
    add_learned_v5_scores(rows, learned_v5_weights)
    for row in rows:
        row["demo_selector_score"] = row["selector_scores"].get("v5_learned_no_simulation", row["selector_scores"].get("v5_ensemble_online", 0.0))

    default_selector = "v5_learned_no_simulation"
    rows = sorted(rows, key=lambda item: item["selector_scores"][default_selector], reverse=True)
    for idx, row in enumerate(rows, start=1):
        row["rank"] = idx
    selected = rows[0]

    eval_path = args.results_dir / "gpt_candidate_evaluations.csv"
    write_csv(eval_path, rows, COLUMNS)
    simulation_info = prepare_gpt_simulation_jobs(eval_path, args.demo_pickle, args.timestep, case_id)
    enrich_rows_with_simulation(rows, simulation_info)
    add_simulation_reliability_norm(rows)
    add_learned_v5_scores(rows, learned_v5_weights)
    has_oracle = add_oracle_scores(rows, simulation_info)

    candidates_payload = []
    for row in rows:
        bt = bt_json_by_id[row["candidate_id"]]
        score_breakdowns = {name: breakdown_for_selector(name, row) for name in row["selector_scores"]}
        sim_detail = simulation_info.get("candidates", {}).get(row["candidate_id"], {})
        headless_job = sim_detail.get("headless", {}) or {}
        gui_job = sim_detail.get("gui", {}) or {}
        headless_command = full_isaac_command(headless_job.get("run_command", "")) if headless_job.get("run_command") else "Simulation job is not ready for this candidate."
        gui_command = full_isaac_command(gui_job.get("run_command", "")) if gui_job.get("run_command") else "GUI simulation job is not ready for this candidate."
        gui_pickle = gui_job.get("expected_pickle") or headless_job.get("expected_pickle") or ""
        gui_replay_command = f"rm -f {sim_jobs.shell_quote(gui_pickle)} && {gui_command}" if gui_job.get("run_command") and gui_pickle else gui_command
        sim_command = headless_command
        candidates_payload.append({
            **{key: clean(value) for key, value in row.items()},
            "rationale": rationale_by_id.get(row["candidate_id"], ""),
            "schema_changes": clean(row.get("schema_changes", 0)),
            "placement_strategy": placement_strategy(bt),
            "bt_tree": compact_tree(bt),
            "bt_json": bt,
            "selector_scores": row["selector_scores"],
            "score_breakdowns": score_breakdowns,
            "score_breakdown": score_breakdowns[default_selector],
            "simulation": {
                "status": row.get("simulation_status", "pending"),
                "headless_command": headless_command,
                "gui_command": gui_command,
                "gui_replay_command": gui_replay_command,
                "visual_replay_command": visual_replay_command(row["candidate_id"]),
                "headless_expected_pickle": headless_job.get("expected_pickle", ""),
                "gui_expected_pickle": gui_job.get("expected_pickle", ""),
                "headless_skip_reason": headless_job.get("skip_reason", ""),
                "gui_skip_reason": gui_job.get("skip_reason", ""),
                "metrics": sim_detail.get("metrics", {}) or {},
            },
            "run_command": sim_command,
        })

    payload = {
        "task": {
            "case_id": case_id,
            "task_id": task["task_id"],
            "instruction": task["instruction"],
            "initial_state_id": initial_state_id,
            "target_predicate": "; ".join(predicate_to_text(p) for p in task.get("target_predicates", [])),
            "selected_candidate": selected["candidate_id"],
            "selector": default_selector,
        },
        "generation": {
            "generator": args.generator,
            "model": args.model,
            "candidate_count": len(candidates_payload),
            "prompt_path": str(prompt_path),
            "raw_response_path": str(case_dir / "raw_response.txt"),
            "prompt": prompt,
            "raw_response": raw,
            "schema_adapter": "enabled",
        },
        "online_ranker": {**online_ranker_info, "learned_v5_weights": str(args.learned_v5_weights), "learned_v5_selectors": ["v5_learned_no_simulation", "v5_learned_full", "v5_learned_no_transformer", "v5_learned_no_symbolic", "manual_v5"]},
        "summary": {
            "candidate_count": len(candidates_payload),
            "selected_candidate": selected["candidate_id"],
            "selected_score": selected["selector_scores"][default_selector],
            "symbolic_success_count": sum(int(float(row.get("symbolic_success") or 0)) for row in rows),
            "oracle_candidate": simulation_info.get("oracle", {}).get("candidate_id") if simulation_info.get("oracle") else None,
            "oracle_score": simulation_info.get("oracle", {}).get("score") if simulation_info.get("oracle") else None,
        },
        "simulation": {
            **{key: value for key, value in simulation_info.items() if key != "candidates"},
            "oracle_available": bool(has_oracle),
            "visual_replay_selected": visual_replay_command("selected"),
            "visual_replay_oracle": visual_replay_command("oracle") if has_oracle else "",
        },
        "selectors": ["v5_learned_no_simulation", "v5_learned_full", "manual_v5", "v5_ensemble_online", "feature_only_online", "transformer_fused_online", "transformer_only_online", "v5_learned_no_transformer", "v5_learned_no_symbolic", "gpt_demo_selector", "symbolic_only", "physical_only", "shortest_tree"] + (["oracle"] if has_oracle else []),
        "candidates": candidates_payload,
        "outputs": {"evaluations_csv": str(eval_path), "frontend_json": str(args.frontend_output)},
    }
    args.frontend_output.parent.mkdir(parents=True, exist_ok=True)
    args.frontend_output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"result": "success", "case_id": case_id, "generator": args.generator, "candidates": len(rows), "selected_candidate": selected["candidate_id"], "selected_score": selected["selector_scores"][default_selector], "evaluations": str(eval_path), "frontend_data": str(args.frontend_output)}, indent=2))


if __name__ == "__main__":
    main()
