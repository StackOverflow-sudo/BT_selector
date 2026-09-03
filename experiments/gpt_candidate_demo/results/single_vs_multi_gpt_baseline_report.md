# GPT Single-BT Baseline vs Multi-BT Selector Report

## Method

For each task/state/repeat pair, the single baseline asks GPT for one behavior tree. The proposed pipeline asks GPT for multiple candidate BTs, evaluates them with the existing KIOS/selector pipeline, and selects one candidate.

- Generator: `openai`
- Model: `gpt-5.4-mini`
- Cases: `10`
- Repeats: `3`
- Single candidate count: `1`
- Multi candidate count: `4`
- Total GPT calls when `--mode both`: `60`

## Summary

mode,runs,successfully_evaluated_runs,failed_runs,mean_candidates_returned,symbolic_success_rate,sim_success_rate,oracle_match_rate,mean_goal_satisfaction,mean_selected_score,mean_physical_feasibility,mean_symbolic_reliability,mean_true_score,mean_regret
multi,30,30,0,4.0,0.9333333333333333,0.3333333333333333,0.03333333333333333,0.9333333333333333,1.0,0.8500000000000002,68.45666666666669,54.41776806666667,
single,30,29,1,0.9666666666666667,0.9,0.0,0.0,0.9,0.5,1.0,67.12068965517244,49.46551724137931,

## Paired Comparison

- paired_runs: 30
- symbolic_success_multi_wins: 3
- symbolic_success_single_wins: 2
- symbolic_success_ties: 25
- goal_satisfaction_multi_wins: 3
- goal_satisfaction_single_wins: 2
- goal_satisfaction_ties: 25
- selected_score_multi_wins: 29
- selected_score_single_wins: 0
- selected_score_ties: 0
- physical_feasibility_score_multi_wins: 0
- physical_feasibility_score_single_wins: 10
- physical_feasibility_score_ties: 19
- true_score_multi_wins: 14
- true_score_single_wins: 10
- true_score_ties: 5

## Interpretation

Use symbolic and selector-score metrics as the fast evidence. If simulation columns are empty, the generated Isaac Gym jobs still need to be executed before making physical-success claims.
