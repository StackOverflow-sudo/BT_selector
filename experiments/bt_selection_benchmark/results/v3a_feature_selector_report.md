# V3A Feature-Based Learned BT Selector Report

## Method

V3A trains a lightweight feature-based selector. Isaac Gym simulation metrics are used as labels, not as model inputs.

Prediction target:

```text
sim_success
```

Selector score:

```text
learned_score = P(sim_success | task, world, BT candidate features)
```

## Cross-Validation Metrics

- Rows: 480
- Groups: 80
- Positive labels: 133
- Negative labels: 347
- Accuracy: 1.000
- ROC-AUC: 1.000
- Log loss: 0.008

## Selector Comparison

selector,groups,success,mean_selected_true_score,mean_regret
learned_feature,80,0.5375,106.61379187499999,0.4488745624999993
symbolic_only,80,0.375,91.14227106249999,15.920395375000002
shortest_tree,80,0.125,18.4962876875,88.56637875
oracle,80,0.5375,107.0626664375,0.0


## Feature Columns

initial_timestep, symbolic_success, goal_satisfaction, bt_ticks, action_count, condition_failure_count, invalid_action_count, tree_size, tree_depth, precondition_coverage, support_stability, validation_error_count, task_id, initial_state_id, candidate_type, bt_path, task_instruction, target_predicate, moved_object, support_object, source_benchmark, benchmark

## Outputs

- Choices: `experiments/bt_selection_benchmark/results/v3a_feature_selector_choices.csv`

## Interpretation

This is the first learned selector baseline. If it reduces regret relative to symbolic-only selection, it supports the claim that pre-simulation task/world/BT features can predict physical executability.
