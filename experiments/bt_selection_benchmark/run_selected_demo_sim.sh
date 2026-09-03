#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

deactivate 2>/dev/null || true

python3 experiments/bt_selection_benchmark/run_selected_demo_sim.py "$@"
