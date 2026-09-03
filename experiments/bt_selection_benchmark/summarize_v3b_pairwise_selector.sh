#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python3 experiments/bt_selection_benchmark/models/build_learned_selector_dataset.py
python3 experiments/bt_selection_benchmark/models/train_v3b_pairwise_selector.py

echo
echo "V3B pairwise ranking selector summary is complete:"
echo "  experiments/bt_selection_benchmark/results/v3b_pairwise_selector_report.md"
