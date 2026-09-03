#!/usr/bin/env python3
"""Export one BT-selection demo case for the Element Plus dashboard."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = ROOT / "experiments" / "bt_selection_benchmark"
RESULTS_DIR = BENCH_DIR / "results"
FRONTEND_DIR = BENCH_DIR / "frontend_dashboard"


DEFAULT_EVALUATIONS = RESULTS_DIR / "bt_candidate_evaluations_v2b_physical_strategy_with_sim.csv"
DEFAULT_CHOICES = RESULTS_DIR / "v4b_transformer_selector_choices.csv"
DEFAULT_MANIFEST = BENCH_DIR / "simulation_jobs_v2b_physical_strategy" / "simulation_jobs_manifest.csv"
DEFAULT_OUTPUT = FRONTEND_DIR / "demo_data.json"
DEFAULT_V5_SCORED = RESULTS_DIR / "v5_ensemble_selector_scored_candidates.csv"


TREE_COLUMNS = (
    "bt_json",
    "behavior_tree",
    "behavior_tree_json",
    "candidate_bt_json",
    "tree_json",
    "bt",
)


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        missing = pd.isna(value)
        if isinstance(missing, bool) and missing:
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (int, float, str, bool)):
        return value
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            pass
    return str(value)


def number(value: Any, default: float = 0.0) -> float:
    value = clean_value(value)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def first_present(row: pd.Series, names: Iterable[str], default: Any = None) -> Any:
    for name in names:
        if name in row.index:
            value = clean_value(row[name])
            if value is not None and value != "":
                return value
    return default


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return pd.read_csv(path)


def parse_bt_json(row: pd.Series) -> Optional[Any]:
    for column in TREE_COLUMNS:
        if column not in row.index:
            continue
        raw = clean_value(row[column])
        if not raw:
            continue
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                continue
        return raw

    bt_path = clean_value(first_present(row, ("bt_path",), None))
    if bt_path:
        path = Path(str(bt_path))
        if not path.is_absolute():
            path = ROOT / path
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
    return None


def compact_tree(node: Any) -> Dict[str, Any]:
    if not isinstance(node, dict):
        return {"label": str(node), "type": "value", "children": []}

    node_type = first_from_dict(node, ("type", "node_type", "type_name", "class"), "node")
    label = first_from_dict(
        node,
        ("label", "summary", "name", "action", "condition", "predicate"),
        node_type,
    )

    facts = []
    for key in ("conditions", "effects", "metadata", "target", "object", "reference", "arguments", "args", "preconditions"):
        value = node.get(key)
        if value not in (None, "", [], {}):
            facts.append({"key": key, "value": value})

    children_raw = node.get("children")
    if children_raw is None:
        children_raw = node.get("child")
    if children_raw is None:
        children = []
    elif isinstance(children_raw, list):
        children = [compact_tree(child) for child in children_raw]
    else:
        children = [compact_tree(children_raw)]

    return {
        "label": str(label),
        "type": str(node_type),
        "facts": facts,
        "children": children,
    }


def first_from_dict(data: Dict[str, Any], names: Iterable[str], default: Any = None) -> Any:
    for name in names:
        value = data.get(name)
        if value not in (None, "", [], {}):
            return value
    return default


def build_run_command(config_dir: Optional[str], data_root: Optional[str]) -> Optional[str]:
    if not config_dir or not data_root:
        return None
    return (
        "python3 run_isaacgym.py --config cupboard_candidate.yaml "
        f"--config_dir {config_dir} --n_envs 1 --n_demos 1 "
        f"--data_root {data_root} --headless --no_render_graphics"
    )


def manifest_lookup(manifest: pd.DataFrame) -> Dict[tuple, pd.Series]:
    lookup: Dict[tuple, pd.Series] = {}
    for _, row in manifest.iterrows():
        key = (
            str(first_present(row, ("task_id", "task"), "")),
            str(first_present(row, ("initial_state_id", "initial_state"), "")),
            str(first_present(row, ("candidate_id", "candidate", "candidate_name"), "")),
        )
        lookup[key] = row
    return lookup


def select_choice(choices: pd.DataFrame, selector: str, task_id: str, initial_state_id: str, benchmark: str = "") -> pd.Series:
    selector_mask = choices["selector"].astype(str) == selector
    if {"task_id", "initial_state_id"}.issubset(choices.columns):
        filtered = choices[
            selector_mask
            & (choices["task_id"].astype(str) == task_id)
            & (choices["initial_state_id"].astype(str) == initial_state_id)
        ]
    elif "selector_group_id" in choices.columns:
        group = choices["selector_group_id"].astype(str)
        exact = f"{benchmark}::{initial_state_id}::{task_id}" if benchmark else ""
        suffix = f"::{initial_state_id}::{task_id}"
        filtered = choices[selector_mask & (group == exact)] if exact else choices.iloc[0:0]
        if filtered.empty:
            filtered = choices[selector_mask & group.str.endswith(suffix)]
    else:
        raise ValueError(f"Unsupported choices schema: {choices.columns.tolist()}")
    if filtered.empty:
        preview_columns = [name for name in ("selector", "selector_group_id", "task_id", "initial_state_id") if name in choices.columns]
        available = choices[preview_columns].drop_duplicates().head(12)
        message = (
            f"No selector choice found for selector={selector}, task_id={task_id}, "
            f"initial_state_id={initial_state_id}. Available examples: {available.to_string(index=False)}"
        )
        raise ValueError(message)
    return filtered.iloc[0]


def candidate_rows(evaluations: pd.DataFrame, task_id: str, initial_state_id: str) -> pd.DataFrame:
    filtered = evaluations[
        (evaluations["task_id"].astype(str) == task_id)
        & (evaluations["initial_state_id"].astype(str) == initial_state_id)
    ].copy()
    if filtered.empty:
        raise ValueError(f"No candidate rows found for {task_id}/{initial_state_id}")
    score_column = "true_score" if "true_score" in filtered.columns else "score"
    if score_column in filtered.columns:
        filtered = filtered.sort_values(score_column, ascending=False)
    return filtered


def v5_score_lookup(path: Path) -> Dict[tuple, Dict[str, Any]]:
    if not path.exists():
        return {}
    frame = pd.read_csv(path)
    lookup: Dict[tuple, Dict[str, Any]] = {}
    for _, row in frame.iterrows():
        key = (
            str(first_present(row, ("selector_group_id",), "")),
            str(first_present(row, ("candidate_id",), "")),
        )
        lookup[key] = {
            "v5_ensemble_score": clean_value(first_present(row, ("v5_ensemble_score",), None)),
            "selector_vote_score": clean_value(first_present(row, ("selector_vote_score",), None)),
            "selector_vote_details": clean_value(first_present(row, ("selector_vote_details",), "")),
            "symbolic_reliability_score": clean_value(first_present(row, ("symbolic_reliability_score",), None)),
            "simulation_reliability_score": clean_value(first_present(row, ("simulation_reliability_score",), None)),
            "symbolic_reliability_norm": clean_value(first_present(row, ("symbolic_reliability_norm",), None)),
            "simulation_reliability_norm": clean_value(first_present(row, ("simulation_reliability_norm",), None)),
        }
    return lookup


def candidate_payload(row: pd.Series, selected: str, oracle: str, manifest_rows: Dict[tuple, pd.Series], v5_scores: Dict[tuple, Dict[str, Any]], benchmark: str) -> Dict[str, Any]:
    task_id = str(row["task_id"])
    initial_state_id = str(row["initial_state_id"])
    candidate_id = str(first_present(row, ("candidate_id", "candidate", "candidate_name"), "unknown"))
    manifest = manifest_rows.get((task_id, initial_state_id, candidate_id))

    config_dir = first_present(row, ("config_dir",), None)
    data_root = first_present(row, ("data_root",), None)
    expected_pickle = first_present(row, ("expected_pickle", "pickle_path", "demo_pickle"), None)
    if manifest is not None:
        config_dir = config_dir or first_present(manifest, ("config_dir", "job_dir"), None)
        data_root = data_root or first_present(manifest, ("data_root", "output_dir"), None)
        expected_pickle = expected_pickle or first_present(manifest, ("expected_pickle", "pickle_path"), None)

    tree = parse_bt_json(row)
    selector_group_id = str(first_present(row, ("selector_group_id",), ""))
    if not selector_group_id:
        selector_group_id = f"{benchmark}::{initial_state_id}::{task_id}"
    v5 = v5_scores.get((selector_group_id, candidate_id), {})
    payload = {
        "candidate_id": candidate_id,
        "candidate_type": str(first_present(row, ("candidate_type",), candidate_id)),
        "is_selected": candidate_id == selected,
        "is_oracle": candidate_id == oracle,
        "symbolic_success": number(first_present(row, ("symbolic_success",), 0)),
        "sim_success": number(first_present(row, ("sim_success",), 0)),
        "goal_satisfaction": number(first_present(row, ("goal_satisfaction",), 0)),
        "true_score": number(first_present(row, ("true_score", "score"), 0)),
        "model_score": clean_value(first_present(row, ("model_score", "predicted_score", "rank_score"), None)),
        "tree_size": number(first_present(row, ("tree_size",), 0)),
        "tree_depth": number(first_present(row, ("tree_depth",), 0)),
        "bt_ticks": number(first_present(row, ("bt_ticks",), 0)),
        "action_count": number(first_present(row, ("action_count",), 0)),
        "invalid_action_count": number(first_present(row, ("invalid_action_count",), 0)),
        "condition_failure_count": number(first_present(row, ("condition_failure_count",), 0)),
        "precondition_coverage": number(first_present(row, ("precondition_coverage",), 0)),
        "support_stability": clean_value(first_present(row, ("support_stability",), None)),
        "final_position_error": clean_value(first_present(row, ("final_position_error",), None)),
        "object_displacement_error": clean_value(first_present(row, ("object_displacement_error",), None)),
        "contact_violation_proxy": clean_value(first_present(row, ("contact_violation_proxy",), None)),
        "execution_result": clean_value(first_present(row, ("execution_result",), None)),
        "simulation_status": clean_value(first_present(row, ("simulation_status", "sim_status"), None)),
        "placement_strategy": clean_value(first_present(row, ("placement_strategy", "strategy"), None)),
        "bt_path": clean_value(first_present(row, ("bt_path",), None)),
        "expected_pickle": clean_value(expected_pickle),
        "config_dir": clean_value(config_dir),
        "data_root": clean_value(data_root),
        "run_command": build_run_command(clean_value(config_dir), clean_value(data_root)),
        "tree": compact_tree(tree) if tree is not None else None,
    }
    payload.update(v5)
    return payload


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    evaluations = load_csv(args.evaluations)
    choices = load_csv(args.choices)
    manifest = load_csv(args.manifest) if args.manifest.exists() else pd.DataFrame()
    manifest_rows = manifest_lookup(manifest) if not manifest.empty else {}
    v5_scores = v5_score_lookup(args.v5_scored)

    choice = select_choice(choices, args.selector, args.task_id, args.initial_state_id, args.benchmark)
    selected = str(first_present(choice, ("selected_candidate", "selected_candidate_id", "candidate_id", "selected"), ""))
    oracle = str(first_present(choice, ("oracle_candidate", "oracle_candidate_id", "oracle"), ""))
    regret = number(first_present(choice, ("regret",), 0))

    rows = candidate_rows(evaluations, args.task_id, args.initial_state_id)
    candidates = [
        candidate_payload(row, selected, oracle, manifest_rows, v5_scores, args.benchmark)
        for _, row in rows.iterrows()
    ]
    selected_candidate = next((item for item in candidates if item["candidate_id"] == selected), candidates[0])

    first_row = rows.iloc[0]
    summary = {
        "candidate_count": len(candidates),
        "symbolic_success_count": int(sum(item["symbolic_success"] > 0 for item in candidates)),
        "sim_success_count": int(sum(item["sim_success"] > 0 for item in candidates)),
        "best_true_score": max(item["true_score"] for item in candidates),
        "selected_true_score": selected_candidate["true_score"],
        "regret": regret,
    }

    return {
        "meta": {
            "title": "BT Selection Demo",
            "benchmark": args.benchmark,
            "evaluations": str(args.evaluations),
            "choices": str(args.choices),
            "manifest": str(args.manifest),
        },
        "task": {
            "task_id": args.task_id,
            "initial_state_id": args.initial_state_id,
            "selector": args.selector,
            "instruction": clean_value(first_present(first_row, ("task_instruction", "instruction"), args.task_id)),
            "target_predicate": clean_value(first_present(first_row, ("target_predicate",), None)),
            "moved_object": clean_value(first_present(first_row, ("moved_object",), None)),
            "support_object": clean_value(first_present(first_row, ("support_object",), None)),
            "selected_candidate": selected,
            "oracle_candidate": oracle,
        },
        "summary": summary,
        "candidates": candidates,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", default="place_block3_on_block5")
    parser.add_argument("--initial-state-id", default="state_000_t0")
    parser.add_argument("--selector", default="feature_only")
    parser.add_argument("--benchmark", default="v2b_physical_strategy")
    parser.add_argument("--evaluations", type=Path, default=DEFAULT_EVALUATIONS)
    parser.add_argument("--choices", type=Path, default=DEFAULT_CHOICES)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--v5-scored", type=Path, default=DEFAULT_V5_SCORED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_payload(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "result": "success",
        "output": str(args.output),
        "task_id": payload["task"]["task_id"],
        "initial_state_id": payload["task"]["initial_state_id"],
        "selector": payload["task"]["selector"],
        "selected_candidate": payload["task"]["selected_candidate"],
        "candidate_count": payload["summary"]["candidate_count"],
    }, indent=2))


if __name__ == "__main__":
    main()
