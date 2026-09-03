# V4B Lightweight Transformer BT Encoder Report

## Method

V4B replaces the TF-IDF BT-token encoder from V4A with a lightweight Transformer encoder.
The model is trained with pairwise ranking supervision derived from simulation-grounded true scores.

Architecture:

```text
BT JSON -> preorder tokens -> token ids -> Transformer Encoder -> mean pooling -> ranking score
```

Fused architecture:

```text
Transformer BT embedding + task/world/symbolic tabular embedding -> ranking score
```

Hyperparameters:

- d_model: 64
- heads: 2
- layers: 1
- max_len: 96
- epochs: 40

## Selector Comparison

selector,groups,success,mean_selected_true_score,mean_regret,pairwise_accuracy,pairwise_roc_auc,pairwise_examples
feature_only,110,0.5,103.14054809090908,1.0102685909090916,0.8103030303030303,0.926294214876033,3300
transformer_only,110,0.45454545454545453,98.58792340909089,5.562893272727273,0.816969696969697,0.9182494031221303,3300
transformer_fused,110,0.4909090909090909,102.19382295454545,1.956993727272727,0.8424242424242424,0.928023507805326,3300
symbolic_only,110,0.36363636363636365,89.85852413636366,14.292292545454544,,,0
shortest_tree,110,0.18181818181818182,37.02508168181818,67.12573499999999,,,0
oracle,110,0.509090909090909,104.1508166818182,0.0,,,0


## Feature Columns

initial_timestep, symbolic_success, goal_satisfaction, bt_ticks, action_count, condition_failure_count, invalid_action_count, tree_size, tree_depth, precondition_coverage, support_stability, validation_error_count, task_id, initial_state_id, candidate_type, task_instruction, target_predicate, moved_object, support_object, source_benchmark, benchmark

## Outputs

- Choices: `experiments/bt_selection_benchmark/results/v4b_transformer_selector_choices.csv`

## Interpretation

V4B is a compact Transformer prototype. Because the dataset is small, the main claim should be architectural feasibility rather than guaranteed improvement over the stronger linear pairwise selector.
