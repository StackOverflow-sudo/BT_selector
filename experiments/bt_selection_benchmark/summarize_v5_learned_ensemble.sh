#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

python3 experiments/bt_selection_benchmark/models/train_v5_learned_ensemble.py "$@"

echo
echo "V5 learned ensemble and ablation summary is complete:"
echo "  experiments/bt_selection_benchmark/results/v5_learned_ensemble_report.md"
echo "  experiments/bt_selection_benchmark/results/v5_learned_ensemble_ablation.csv"