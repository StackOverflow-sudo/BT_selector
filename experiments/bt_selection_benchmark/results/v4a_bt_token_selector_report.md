# V4A BT Token-Aware Pairwise Selector Report

## Method

V4A serializes each candidate Behavior Tree JSON into a structured token sequence and uses TF-IDF n-gram features as a lightweight BT encoder.
The BT-token representation is evaluated alone and fused with the V3B tabular task/world/symbolic features.

BT token encoder:

```text
BT JSON -> preorder tokens -> TF-IDF n-gram vector
```

Pairwise ranking target:

```text
label = 1 if true_score(BT_A) > true_score(BT_B) else 0
```

## Selector Comparison

selector,groups,success,mean_selected_true_score,mean_regret,pairwise_accuracy,pairwise_roc_auc,pairwise_examples
feature_only,80,0.5375,106.882985375,0.17968106250000188,0.8333333333333334,0.9415465277777777,2400
bt_token_only,80,0.5,103.12600375000002,3.9366626875000015,0.8358333333333333,0.9392027777777778,2400
fused,80,0.5375,106.882985375,0.17968106250000188,0.84,0.9452215277777779,2400
symbolic_only,80,0.375,91.14227106249999,15.920395375000002,,,0
shortest_tree,80,0.125,18.4962876875,88.56637875,,,0
oracle,80,0.5375,107.0626664375,0.0,,,0


## Feature Columns

initial_timestep, symbolic_success, goal_satisfaction, bt_ticks, action_count, condition_failure_count, invalid_action_count, tree_size, tree_depth, precondition_coverage, support_stability, validation_error_count, task_id, initial_state_id, candidate_type, task_instruction, target_predicate, moved_object, support_object, source_benchmark, benchmark

## Outputs

- Choices: `experiments/bt_selection_benchmark/results/v4a_bt_token_selector_choices.csv`

## Interpretation

Compare `feature_only` with `fused`. If `fused` improves regret, explicit BT structure contributes beyond V3B features. If `bt_token_only` is competitive, the serialized BT itself carries useful executability signals.
