# V5 Ensemble BT Selector Report

## Method

V5 is the proposed final selector. It combines deployable selector agreement with symbolic and simulation reliability scores.
Oracle is not used as an input; it is used only as the evaluation upper bound for regret.

Formula:
score_v5(c) = 0.55 * selector_vote_score(c) + 0.20 * normalized_symbolic_reliability(c) + 0.25 * normalized_simulation_reliability(c)

Selector vote weights: feature_only=0.30, transformer_fused=0.35, transformer_only=0.15, symbolic_only=0.10, shortest_tree=0.05.

## Selector Comparison

selector,groups,success,mean_selected_true_score,mean_regret,pairwise_accuracy,pairwise_roc_auc,pairwise_examples
feature_only,110,0.5,103.14054809090908,1.0102685909090916,0.8103030303030303,0.926294214876033,3300
transformer_only,110,0.4545454545454545,98.58792340909088,5.562893272727273,0.816969696969697,0.9182494031221304,3300
transformer_fused,110,0.4909090909090909,102.19382295454544,1.956993727272727,0.8424242424242424,0.928023507805326,3300
symbolic_only,110,0.3636363636363636,89.85852413636366,14.292292545454544,,,0
shortest_tree,110,0.1818181818181818,37.02508168181818,67.12573499999999,,,0
oracle,110,0.509090909090909,104.1508166818182,0.0,,,0
v5_ensemble,110,0.5,103.16213640909092,0.9886802727272731,,,0


## Outputs

Choices: experiments/bt_selection_benchmark/results/v5_ensemble_selector_choices.csv
Scored candidates: experiments/bt_selection_benchmark/results/v5_ensemble_selector_scored_candidates.csv
