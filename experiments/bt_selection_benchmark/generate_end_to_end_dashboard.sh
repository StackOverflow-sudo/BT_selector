#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python3 experiments/bt_selection_benchmark/generate_end_to_end_dashboard.py "$@"

echo
echo "Open this dashboard in Windows:"
echo "\\\\wsl.localhost\\Ubuntu-20.04\\home\\theshy\\projects\\mycode\\kios_baseline\\experiments\\bt_selection_benchmark\\results\\end_to_end_demo_dashboard.html"
