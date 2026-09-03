#!/usr/bin/env python3
"""Export multiple selector/case demo payloads for the frontend dashboard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Tuple

import pandas as pd

import generate_frontend_demo_data as single


def load_choices_with_v5(path: Path) -> pd.DataFrame:
    choices = single.load_csv(path)
    v5_path = single.RESULTS_DIR / "v5_ensemble_selector_choices.csv"
    if v5_path.exists():
        v5 = pd.read_csv(v5_path)
        keep = ["selector_group_id", "selected_candidate", "oracle_candidate", "selected_sim_success", "selected_true_score", "oracle_true_score", "regret", "selector"]
        for column in keep:
            if column not in v5.columns:
                v5[column] = ""
        choices = pd.concat([v5[keep], choices], ignore_index=True, sort=False)
    return choices


DEFAULT_SELECTORS = "v5_ensemble,feature_only,transformer_fused,transformer_only,symbolic_only,shortest_tree,oracle"


def available_cases(choices: pd.DataFrame, selector: str, benchmark: str) -> List[Tuple[str, str]]:
    rows = choices[choices["selector"].astype(str) == selector].copy()
    cases: List[Tuple[str, str]] = []
    seen = set()
    if "selector_group_id" in rows.columns:
        for group in rows["selector_group_id"].astype(str):
            parts = group.split("::")
            if len(parts) != 3:
                continue
            bench, initial_state_id, task_id = parts
            if bench != benchmark:
                continue
            key = (task_id, initial_state_id)
            if key not in seen:
                seen.add(key)
                cases.append(key)
    elif {"task_id", "initial_state_id"}.issubset(rows.columns):
        for _, row in rows.iterrows():
            key = (str(row["task_id"]), str(row["initial_state_id"]))
            if key not in seen:
                seen.add(key)
                cases.append(key)
    return cases


def build_cases(selector: str, cases: List[Tuple[str, str]], args: argparse.Namespace, choices_path: Path) -> List[dict]:
    payloads = []
    for task_id, initial_state_id in cases:
        ns = SimpleNamespace(
            task_id=task_id,
            initial_state_id=initial_state_id,
            selector=selector,
            benchmark=args.benchmark,
            evaluations=args.evaluations,
            choices=choices_path,
            manifest=args.manifest,
            output=args.output,
            v5_scored=args.v5_scored,
        )
        payloads.append(single.build_payload(ns))
    return payloads


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selector", default="v5_ensemble")
    parser.add_argument("--selectors", default=DEFAULT_SELECTORS)
    parser.add_argument("--benchmark", default="v2b_physical_strategy")
    parser.add_argument("--case-count", type=int, default=20)
    parser.add_argument("--evaluations", type=Path, default=single.DEFAULT_EVALUATIONS)
    parser.add_argument("--choices", type=Path, default=single.DEFAULT_CHOICES)
    parser.add_argument("--manifest", type=Path, default=single.DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=single.DEFAULT_OUTPUT)
    parser.add_argument("--v5-scored", type=Path, default=single.DEFAULT_V5_SCORED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    choices = load_choices_with_v5(args.choices)
    combined_choices_path = args.output.parent / "combined_selector_choices_with_v5.csv"
    combined_choices_path.parent.mkdir(parents=True, exist_ok=True)
    choices.to_csv(combined_choices_path, index=False)
    selectors = [item.strip() for item in args.selectors.split(",") if item.strip()]
    if args.selector not in selectors:
        selectors.insert(0, args.selector)

    base_cases = available_cases(choices, args.selector, args.benchmark)
    if args.case_count > 0:
        base_cases = base_cases[: args.case_count]
    if not base_cases:
        raise SystemExit(f"No cases found for selector={args.selector}, benchmark={args.benchmark}")

    selector_sets: Dict[str, dict] = {}
    valid_selectors: List[str] = []
    for selector in selectors:
        try:
            payloads = build_cases(selector, base_cases, args, combined_choices_path)
        except Exception as exc:
            print(f"Skipping selector {selector}: {exc}")
            continue
        selector_sets[selector] = {"cases": payloads}
        valid_selectors.append(selector)

    if args.selector not in selector_sets:
        args.selector = valid_selectors[0]
    payloads = selector_sets[args.selector]["cases"]
    output = dict(payloads[0])
    output["cases"] = payloads
    output["case_count"] = len(payloads)
    output["selectors"] = valid_selectors
    output["selector_sets"] = selector_sets
    output["meta"] = dict(output.get("meta", {}))
    output["meta"]["case_count"] = len(payloads)
    output["meta"]["selectors"] = valid_selectors

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "result": "success",
        "output": str(args.output),
        "default_selector": args.selector,
        "selectors": valid_selectors,
        "benchmark": args.benchmark,
        "cases": len(payloads),
        "first_task_id": output["task"]["task_id"],
        "first_initial_state_id": output["task"]["initial_state_id"],
    }, indent=2))


if __name__ == "__main__":
    main()
