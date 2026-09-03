#!/usr/bin/env python3
"""Run the Isaac Gym job selected by the end-to-end demo selector."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from pathlib import Path

import pandas as pd


ISAAC_SCRIPT_DIR = Path(
    "/home/theshy/projects/mycode/ll4ma_isaac/ll4ma_isaacgym/src/ll4ma_isaacgym/scripts"
)


def choose_candidate(args: argparse.Namespace) -> tuple[str, str]:
    evaluations = pd.read_csv(args.evaluations)
    choices = pd.read_csv(args.choices)
    group_id = f"{args.benchmark}::{args.initial_state_id}::{args.task_id}"
    selected_rows = choices[
        (choices["selector"] == args.selector)
        & (choices["selector_group_id"] == group_id)
    ]
    if not selected_rows.empty:
        row = selected_rows.iloc[0]
        return str(row["selected_candidate"]), str(row["oracle_candidate"])

    group = evaluations[
        (evaluations["task_id"] == args.task_id)
        & (evaluations["initial_state_id"] == args.initial_state_id)
    ].copy()
    if group.empty:
        raise ValueError(f"No candidate rows for task={args.task_id}, state={args.initial_state_id}")
    fallback = str(group.sort_values("score", ascending=False).iloc[0]["candidate_id"])
    return fallback, fallback


def build_command(args: argparse.Namespace, candidate_id: str) -> tuple[list[str], pd.Series]:
    manifest = pd.read_csv(args.manifest)
    rows = manifest[
        (manifest["task_id"] == args.task_id)
        & (manifest["initial_state_id"] == args.initial_state_id)
        & (manifest["candidate_id"] == candidate_id)
    ]
    if rows.empty:
        raise ValueError(
            f"No simulation job for task={args.task_id}, state={args.initial_state_id}, candidate={candidate_id}"
        )
    row = rows.iloc[0]
    if str(row.get("status", "")) != "ready":
        raise ValueError(f"Selected candidate is not ready for simulation: {row.get('skip_reason', '')}")
    command = shlex.split(str(row["run_command"]))
    return command, row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="v2b_physical_strategy")
    parser.add_argument("--task-id", default="place_block3_on_block5")
    parser.add_argument("--initial-state-id", default="state_000_t0")
    parser.add_argument("--selector", default="feature_only")
    parser.add_argument(
        "--evaluations",
        default="experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v2b_physical_strategy_with_sim.csv",
    )
    parser.add_argument(
        "--choices",
        default="experiments/bt_selection_benchmark/results/v4b_transformer_selector_choices.csv",
    )
    parser.add_argument(
        "--manifest",
        default="experiments/bt_selection_benchmark/simulation_jobs_v2b_physical_strategy/simulation_jobs_manifest.csv",
    )
    parser.add_argument("--force", action="store_true", help="Run even if expected pickle already exists.")
    parser.add_argument("--dry-run", action="store_true", help="Print the selected job without executing it.")
    args = parser.parse_args()

    selected_candidate, oracle_candidate = choose_candidate(args)
    command, job = build_command(args, selected_candidate)
    expected_pickle = Path(str(job["expected_pickle"]))

    info = {
        "task_id": args.task_id,
        "initial_state_id": args.initial_state_id,
        "selector": args.selector,
        "selected_candidate": selected_candidate,
        "oracle_candidate": oracle_candidate,
        "expected_pickle": str(expected_pickle),
        "command": " ".join(shlex.quote(part) for part in command),
    }
    print(json.dumps(info, indent=2))

    if expected_pickle.exists() and not args.force:
        print(f"\nExisting simulation result found, skipping run:\n  {expected_pickle}")
        print("Use --force to run the Isaac Gym job again.")
        return

    if args.dry_run:
        print("\nDry run only. Isaac Gym job was not executed.")
        return

    if not ISAAC_SCRIPT_DIR.exists():
        raise FileNotFoundError(f"Isaac Gym script directory not found: {ISAAC_SCRIPT_DIR}")

    env = os.environ.copy()
    result = subprocess.run(command, cwd=str(ISAAC_SCRIPT_DIR), env=env)
    if result.returncode:
        raise SystemExit(result.returncode)
    if expected_pickle.exists():
        print(f"\nSimulation result written:\n  {expected_pickle}")
    else:
        raise FileNotFoundError(f"Isaac Gym command finished but expected pickle was not found: {expected_pickle}")


if __name__ == "__main__":
    main()
