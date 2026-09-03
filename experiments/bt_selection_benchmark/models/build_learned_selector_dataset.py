#!/usr/bin/env python3
"""Build a feature table for the V3A learned BT selector.

The dataset keeps simulation metrics as labels and excludes them from the
feature list used by the training script.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


DEFAULT_INPUTS = [
    "experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v1_supported_by_with_sim.csv",
    "experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v2_stacking_probe_with_sim.csv",
    "experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v2b_physical_strategy_with_sim.csv",
    "experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v6_hard_cases_with_sim.csv",
]


SIM_LABEL_COLUMNS = {
    "sim_success",
    "final_position_error",
    "object_displacement_error",
    "contact_violation_proxy",
}


def infer_benchmark_name(path: Path) -> str:
    name = path.name
    match = re.search(r"bt_candidate_evaluations_(.+?)_with_sim", name)
    if match:
        return match.group(1)
    return path.stem


def first_existing(row: pd.Series, names: list[str], default: str = "") -> str:
    for name in names:
        if name in row and pd.notna(row[name]) and str(row[name]) != "":
            return str(row[name])
    return default


def infer_group_id(row: pd.Series) -> str:
    benchmark = first_existing(row, ["benchmark", "dataset", "source_benchmark"], "unknown")
    task = first_existing(row, ["task", "task_name", "task_id"], "")
    initial_state = first_existing(row, ["initial_state", "initial_state_id", "state_id"], "")
    case_id = first_existing(row, ["case_id"], "")

    if task and initial_state:
        return f"{benchmark}::{initial_state}::{task}"

    if case_id:
        # Typical case id: place_block3_on_block5__state_000_t0__correct_bt
        parts = case_id.split("__")
        if len(parts) >= 2:
            return f"{benchmark}::{parts[1]}::{parts[0]}"
        return f"{benchmark}::{case_id}"

    return f"{benchmark}::{row.name}"


def normalize_sim_success(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "sim_success" not in out.columns:
        out["sim_success"] = pd.NA

    out["sim_success"] = pd.to_numeric(out["sim_success"], errors="coerce")

    # Invalid or skipped candidates are useful negative examples when the
    # symbolic/simulation status is explicit.
    status_cols = [c for c in ["simulation_status", "status", "execution_result"] if c in out.columns]
    if status_cols:
        status_text = out[status_cols].astype(str).agg(" ".join, axis=1).str.lower()
        negative_status = status_text.str.contains("skip|invalid|fail|error", regex=True, na=False)
        out.loc[out["sim_success"].isna() & negative_status, "sim_success"] = 0

    return out


def build_dataset(input_paths: list[Path]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in input_paths:
        if not path.exists():
            continue
        df = pd.read_csv(path)
        df["source_file"] = str(path)
        df["source_benchmark"] = infer_benchmark_name(path)
        if "benchmark" not in df.columns:
            df["benchmark"] = df["source_benchmark"]
        frames.append(df)

    if not frames:
        raise FileNotFoundError("No input CSV files were found.")

    data = pd.concat(frames, ignore_index=True, sort=False)
    data = normalize_sim_success(data)
    data["selector_group_id"] = data.apply(infer_group_id, axis=1)

    # Keep rows that have a usable binary simulation label.
    data = data[data["sim_success"].isin([0, 1])].copy()
    data["sim_success"] = data["sim_success"].astype(int)

    for col in SIM_LABEL_COLUMNS - {"sim_success"}:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    # A stable per-row id makes later debugging easier even if the source CSVs
    # use slightly different naming conventions.
    if "candidate_id" not in data.columns:
        candidate_cols = [c for c in ["candidate", "candidate_name", "bt_name", "bt_candidate"] if c in data.columns]
        if candidate_cols:
            data["candidate_id"] = data[candidate_cols[0]].astype(str)
        elif "case_id" in data.columns:
            data["candidate_id"] = data["case_id"].astype(str).str.split("__").str[-1]
        else:
            data["candidate_id"] = "candidate_" + data.index.astype(str)

    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", nargs="*", default=DEFAULT_INPUTS)
    parser.add_argument(
        "--output",
        default="experiments/bt_selection_benchmark/results/learned_selector_dataset_v3a.csv",
    )
    parser.add_argument(
        "--metadata-output",
        default="experiments/bt_selection_benchmark/results/learned_selector_dataset_v3a_metadata.json",
    )
    args = parser.parse_args()

    input_paths = [Path(p) for p in args.input]
    data = build_dataset(input_paths)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output, index=False)

    metadata = {
        "result": "success",
        "output": str(output),
        "rows": int(len(data)),
        "groups": int(data["selector_group_id"].nunique()),
        "positive_sim_success": int(data["sim_success"].sum()),
        "negative_sim_success": int((data["sim_success"] == 0).sum()),
        "sources": sorted(data["source_benchmark"].dropna().astype(str).unique().tolist()),
    }
    metadata_output = Path(args.metadata_output)
    metadata_output.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
