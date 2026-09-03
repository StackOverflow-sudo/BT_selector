# V3C Generalization and Ablation Report

## Method

V3C evaluates the V3B pairwise BT ranker under stricter splits and feature ablations.
Simulation metrics are still used only to compute supervision scores, not as model inputs.

Split modes:

- `mixed_group_cv`: grouped cross-validation over task/state groups.
- `leave_one_benchmark_out`: train on two benchmarks and test on the held-out benchmark.
- `leave_one_task_out`: train on all other tasks and test on the held-out task.

Ablations:

- `full`: all non-leaky pre-simulation features.
- `no_candidate_type`: removes explicit candidate identity.
- `no_symbolic_features`: removes symbolic execution metrics.
- `no_benchmark_id`: removes benchmark/source identifiers.
- `task_world_only`: keeps only task/world identifiers.
- `structure_only`: keeps only BT structural metrics.

## Summary

split_mode,ablation,splits,groups,success,mean_selected_true_score,mean_regret,pairwise_accuracy,pairwise_roc_auc,pairwise_examples,feature_count
mixed_group_cv,full,5,80,0.5375,106.882985375,0.17968106250000188,0.8333333333333334,0.941529861111111,2400,21
mixed_group_cv,no_candidate_type,5,80,0.5375,106.9016535625,0.16101287500000067,0.84125,0.9468315972222222,2400,20
mixed_group_cv,no_symbolic_features,5,80,0.5,103.1321014375,3.9305650000000014,0.8275,0.936425,2400,12
mixed_group_cv,no_benchmark_id,5,80,0.5375,106.882985375,0.17968106250000188,0.8333333333333334,0.941529861111111,2400,19
mixed_group_cv,task_world_only,5,80,0.525,105.34898612500001,1.7136803124999993,0.5,0.5,2400,7
mixed_group_cv,structure_only,5,80,0.5,102.05726424999997,5.0054021875000005,0.52,0.5492666666666667,2400,5
leave_one_benchmark_out,full,3,80,0.5375,106.9016535625,0.16101287500000067,0.8325,0.9406166666666667,2400,21
leave_one_benchmark_out,no_candidate_type,3,80,0.5375,106.9016535625,0.16101287500000067,0.8329166666666666,0.9421246527777778,2400,20
leave_one_benchmark_out,no_symbolic_features,3,80,0.5,103.15142981249998,3.911236625,0.8033333333333333,0.902986111111111,2400,12
leave_one_benchmark_out,no_benchmark_id,3,80,0.5375,106.9016535625,0.16101287500000067,0.8325,0.9406166666666667,2400,19
leave_one_benchmark_out,task_world_only,3,80,0.525,105.34898612499998,1.7136803124999993,0.5,0.5,2400,7
leave_one_benchmark_out,structure_only,3,80,0.5,102.05726425,5.0054021875000005,0.52,0.5558611111111111,2400,5
leave_one_task_out,full,8,80,0.5375,106.86515281249999,0.19751362500000144,0.8375,0.9426388888888888,2400,21
leave_one_task_out,no_candidate_type,8,80,0.5375,106.9016535625,0.16101287500000067,0.8329166666666666,0.9418371527777779,2400,20
leave_one_task_out,no_symbolic_features,8,80,0.5,103.099963125,3.9627033125000013,0.8270833333333333,0.9323732638888889,2400,12
leave_one_task_out,no_benchmark_id,8,80,0.5375,106.86515281249999,0.19751362500000144,0.8375,0.9426388888888888,2400,19
leave_one_task_out,task_world_only,8,80,0.525,105.34898612499998,1.7136803124999993,0.5,0.5,2400,7
leave_one_task_out,structure_only,8,80,0.5,102.05726424999999,5.0054021875000005,0.52,0.5489097222222222,2400,5


## Base Feature Columns

initial_timestep, symbolic_success, goal_satisfaction, bt_ticks, action_count, condition_failure_count, invalid_action_count, tree_size, tree_depth, precondition_coverage, support_stability, validation_error_count, task_id, initial_state_id, candidate_type, task_instruction, target_predicate, moved_object, support_object, source_benchmark, benchmark

## Outputs

- Choices: `experiments/bt_selection_benchmark/results/v3c_generalization_ablation_choices.csv`

## Interpretation

The most important rows are `leave_one_benchmark_out/full` and `leave_one_benchmark_out/no_candidate_type`. They indicate whether the learned selector generalizes beyond memorized candidate names or benchmark-specific patterns.
