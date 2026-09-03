#!/usr/bin/env bash
set -eo pipefail

cd "$(dirname "$0")/../.."

TASK_SPECS="experiments/bt_selection_benchmark/task_specs_v6_hard_cases.json"
CANDIDATE_ROOT="/home/theshy/projects/mycode/kios_baseline/experiments/bt_selection_benchmark/bt_candidates_v6_hard_cases"
EVAL_PATH="experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v6_hard_cases.csv"
SIM_JOB_DIR="experiments/bt_selection_benchmark/simulation_jobs_v6_hard_cases"
DATA_ROOT="/home/theshy/projects/datasets/bt_selection_benchmark_v6_hard_cases"

python3 experiments/bt_selection_benchmark/evaluate_bt_candidates.py \
  --task-specs "$TASK_SPECS" \
  --candidate-root "$CANDIDATE_ROOT" \
  --output "$EVAL_PATH" \
  --initial-state-count 5 \
  --include-all-tasks

python3 experiments/bt_selection_benchmark/prepare_simulation_jobs.py \
  --evaluations "$EVAL_PATH" \
  --output-dir "$SIM_JOB_DIR" \
  --data-root "$DATA_ROOT"

echo
echo "V6 hard-case benchmark is prepared:"
echo "  evaluations: $EVAL_PATH"
echo "  simulation jobs: $SIM_JOB_DIR/run_jobs.sh"
echo "  data root: $DATA_ROOT"
