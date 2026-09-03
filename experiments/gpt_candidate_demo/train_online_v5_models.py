#!/usr/bin/env python3
"""Train and save online V5 selector models for the GPT candidate demo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
DEFAULT_LEARNED_DATASET = ROOT / "experiments" / "bt_selection_benchmark" / "results" / "learned_selector_dataset_v3a.csv"
DEFAULT_MODEL_DIR = SCRIPT_DIR / "models" / "online_v5"

import sys
sys.path.insert(0, str(SCRIPT_DIR))
from run_gpt_candidate_demo import train_and_save_online_v5_models  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--learned-dataset", type=Path, default=DEFAULT_LEARNED_DATASET)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--epochs", type=int, default=10)
    args = parser.parse_args()

    metadata = train_and_save_online_v5_models(args.learned_dataset, args.model_dir, args.epochs)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
