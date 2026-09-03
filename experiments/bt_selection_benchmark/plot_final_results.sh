#!/usr/bin/env bash
set -euo pipefail

cd /home/theshy/projects/mycode/kios_baseline
python3 experiments/bt_selection_benchmark/plot_final_results.py "$@"
