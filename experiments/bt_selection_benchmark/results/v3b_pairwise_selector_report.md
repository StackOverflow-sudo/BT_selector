# V3B Pairwise Ranking BT Selector Report

## Method

V3B trains a pairwise ranking model over candidate behavior trees from the same task and initial state.
Simulation metrics are used only to compute the supervision score; they are excluded from model inputs.

Pairwise target:

```text
label = 1 if true_score(BT_A) > true_score(BT_B) else 0
```

Candidate score at inference:

```text
learned_pairwise_score = w dot feature(task, world, BT)
```

## Cross-Validation Metrics

- Rows: 480
- Groups: 80
- Pairwise training/eval examples: 2400
- Pairwise accuracy: 0.833
- Pairwise ROC-AUC: 0.942

## Selector Comparison

selector,groups,success,mean_selected_true_score,mean_regret
learned_pairwise,80,0.5375,106.882985375,0.17968106250000188
symbolic_only,80,0.375,91.14227106249999,15.920395375000002
shortest_tree,80,0.125,18.4962876875,88.56637875
oracle,80,0.5375,107.0626664375,0.0


## Feature Columns

initial_timestep, symbolic_success, goal_satisfaction, bt_ticks, action_count, condition_failure_count, invalid_action_count, tree_size, tree_depth, precondition_coverage, support_stability, validation_error_count, task_id, initial_state_id, candidate_type, task_instruction, target_predicate, moved_object, support_object, source_benchmark, benchmark

## Outputs

- Choices: `experiments/bt_selection_benchmark/results/v3b_pairwise_selector_choices.csv`

## Interpretation

V3B is closer to the real selector objective than V3A because it optimizes candidate ordering within each task/state group rather than independent success classification.
