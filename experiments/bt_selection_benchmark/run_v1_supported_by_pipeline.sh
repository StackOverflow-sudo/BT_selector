#!/usr/bin/env bash
set -eo pipefail

cd "$(dirname "$0")/../.."

EVAL_PATH="experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v1_supported_by.csv"
SIM_JOB_DIR="experiments/bt_selection_benchmark/simulation_jobs_v1_supported_by"
SIM_DATA_ROOT="/home/theshy/projects/datasets/bt_selection_benchmark_v1_supported_by"
SIM_PENDING_PATH="experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v1_supported_by_with_sim_pending.csv"

python3 experiments/bt_selection_benchmark/evaluate_bt_candidates.py \
  --task-specs experiments/bt_selection_benchmark/task_specs_v1_supported_by.json \
  --include-all-tasks \
  --initial-state-count 5 \
  --output "$EVAL_PATH"

python3 experiments/bt_selection_benchmark/prepare_simulation_jobs.py \
  --evaluations "$EVAL_PATH" \
  --output-dir "$SIM_JOB_DIR" \
  --data-root "$SIM_DATA_ROOT"

python3 experiments/bt_selection_benchmark/collect_simulation_metrics.py \
  --evaluations "$EVAL_PATH" \
  --manifest "$SIM_JOB_DIR/simulation_jobs_manifest.csv" \
  --output "$SIM_PENDING_PATH"

echo
echo "V1 symbolic evaluation and simulation job preparation are complete."
echo "Simulation jobs:"
echo "  $SIM_JOB_DIR/run_jobs.sh"
echo
echo "Before running simulation jobs, start the MoveIt service in another terminal:"
echo "  deactivate 2>/dev/null || true"
echo "  source /opt/ros/noetic/setup.bash"
echo "  source /home/theshy/projects/mycode/ll4ma_catkin_ws/devel/setup.bash"
echo "  roslaunch moveit_interface iiwa_reflex_moveit_interface_service.launch"
echo
echo "Then run a small smoke test:"
echo "  cd /home/theshy/projects/mycode/kios_baseline"
echo "  MAX_JOBS=3 bash $SIM_JOB_DIR/run_jobs.sh"
echo
echo "After simulations finish, collect real simulation metrics:"
echo "  python3 experiments/bt_selection_benchmark/collect_simulation_metrics.py \\"
echo "    --evaluations $EVAL_PATH \\"
echo "    --manifest $SIM_JOB_DIR/simulation_jobs_manifest.csv \\"
echo "    --output experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v1_supported_by_with_sim.csv"
