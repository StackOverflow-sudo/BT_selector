#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python3 experiments/bt_selection_benchmark/generate_frontend_multi_demo_data.py "$@"

cat <<'EOF'

Element Plus demo dashboard data is ready.

Run the local page server:
  cd /home/theshy/projects/mycode/kios_baseline/experiments/bt_selection_benchmark/frontend_dashboard
  python3 -m http.server 8088

Open in your browser:
  http://localhost:8088/
EOF
