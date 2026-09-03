#!/usr/bin/env bash
set -eo pipefail

cd "$(dirname "$0")/../.."

EVAL_PATH="experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v2_stacking_probe.csv"
SIM_JOB_DIR="experiments/bt_selection_benchmark/simulation_jobs_v2_stacking_probe"
SIM_EVAL_PATH="experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v2_stacking_probe_with_sim.csv"
SELECTOR_SUMMARY="experiments/bt_selection_benchmark/results/summary_by_selector_v2_stacking_probe_with_sim.csv"
SELECTOR_CHOICES="experiments/bt_selection_benchmark/results/selector_choices_v2_stacking_probe_with_sim.csv"
RULE_SUMMARY="experiments/bt_selection_benchmark/results/rule_based_selector_summary_v2_stacking_probe_with_sim.csv"
RULE_CHOICES="experiments/bt_selection_benchmark/results/rule_based_selector_choices_v2_stacking_probe_with_sim.csv"
REPORT_PATH="experiments/bt_selection_benchmark/results/rule_based_selector_report_v2_stacking_probe_with_sim.md"

python3 experiments/bt_selection_benchmark/collect_simulation_metrics.py \
  --evaluations "$EVAL_PATH" \
  --manifest "$SIM_JOB_DIR/simulation_jobs_manifest.csv" \
  --output "$SIM_EVAL_PATH"

python3 experiments/bt_selection_benchmark/summarize_selectors.py \
  --input "$SIM_EVAL_PATH" \
  --summary-output "$SELECTOR_SUMMARY" \
  --choices-output "$SELECTOR_CHOICES"

python3 experiments/bt_selection_benchmark/models/rule_based_selector.py \
  --input "$SIM_EVAL_PATH" \
  --summary-output "$RULE_SUMMARY" \
  --choices-output "$RULE_CHOICES"

python3 experiments/bt_selection_benchmark/models/make_rule_based_report.py \
  --selector-summary "$SELECTOR_SUMMARY" \
  --rule-summary "$RULE_SUMMARY" \
  --rule-choices "$RULE_CHOICES" \
  --output "$REPORT_PATH"

echo
echo "V2 stacking probe simulation-aware summary is complete:"
echo "  $REPORT_PATH"
