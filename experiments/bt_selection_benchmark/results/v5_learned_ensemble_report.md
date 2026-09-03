# V5 Learnable Ensemble and Ablation Report

## Method

V5-learned replaces the hand-set V5 ensemble weights with a pairwise logistic ranking model.
Each training example compares two candidate BTs from the same task and initial state.
The target ranking is derived from the same simulation-grounded true score used by prior selector evaluations.

Input features:

- deployable selector votes: feature_only, transformer_fused, transformer_only, symbolic_only, shortest_tree
- normalized symbolic reliability
- normalized simulation reliability

Oracle is not used as an input. It is reported only as an upper bound.

## External Hard-Case Test

Train split: all sources except `v6_hard_cases`.
Test split: `v6_hard_cases` only.

selector,groups,success,mean_selected_true_score,mean_regret,pairwise_accuracy,pairwise_roc_auc,pairwise_examples,train_groups,test_benchmark,pairwise_train_examples
v5_learned_full,30,0.43333333333333335,96.33720783333334,0.04867616666666521,0.8933333333333333,0.9378271604938271,900,80.0,v6_hard_cases,2400.0
v5_no_transformer_votes,30,0.43333333333333335,96.26280683333333,0.1230771666666655,0.9066666666666666,0.9424395061728394,900,80.0,v6_hard_cases,2400.0
v5_no_symbolic_reliability,30,0.43333333333333335,94.03523216666666,2.350651833333331,0.8822222222222222,0.9308987654320987,900,80.0,v6_hard_cases,2400.0
v5_no_simulation_reliability,30,0.4,93.08761866666667,3.2982653333333327,0.6011111111111112,0.6802148148148148,900,80.0,v6_hard_cases,2400.0
v5_votes_only,30,0.4,92.93666283333332,3.449221166666666,0.5822222222222222,0.6533530864197531,900,80.0,v6_hard_cases,2400.0
v5_reliability_only,30,0.43333333333333335,84.33802083333332,12.04786316666667,0.84,0.9023506172839506,900,80.0,v6_hard_cases,2400.0
feature_only,30,0.4,93.13020566666665,3.2556783333333312,,,0,,,
transformer_fused,30,0.4,92.93666283333332,3.449221166666666,,,0,,,
transformer_only,30,0.3333333333333333,86.45606700000002,9.929816999999998,,,0,,,
manual_v5,30,0.4,93.15073833333332,3.235145666666665,,,0,,,
symbolic_only,30,0.3333333333333333,86.435199,9.950684999999998,,,0,,,
shortest_tree,30,0.3333333333333333,86.435199,9.950684999999998,,,0,,,
oracle,30,0.43333333333333335,96.38588399999999,0.0,,,0,,,


On `v6_hard_cases`, learned V5 changes mean regret by 3.186 versus manual V5; positive means learned V5 is better.

## Ablation Table

The rows prefixed by `v5_` remove or isolate parts of the proposed ensemble input.
Lower mean regret is better; oracle regret is zero by definition.

selector,groups,success,mean_selected_true_score,mean_regret,pairwise_accuracy,pairwise_roc_auc,pairwise_examples,train_groups,test_benchmark,pairwise_train_examples
v5_learned_full,30,0.43333333333333335,96.33720783333334,0.04867616666666521,0.8933333333333333,0.9378271604938271,900,80.0,v6_hard_cases,2400.0
v5_no_transformer_votes,30,0.43333333333333335,96.26280683333333,0.1230771666666655,0.9066666666666666,0.9424395061728394,900,80.0,v6_hard_cases,2400.0
v5_no_symbolic_reliability,30,0.43333333333333335,94.03523216666666,2.350651833333331,0.8822222222222222,0.9308987654320987,900,80.0,v6_hard_cases,2400.0
v5_no_simulation_reliability,30,0.4,93.08761866666667,3.2982653333333327,0.6011111111111112,0.6802148148148148,900,80.0,v6_hard_cases,2400.0
v5_votes_only,30,0.4,92.93666283333332,3.449221166666666,0.5822222222222222,0.6533530864197531,900,80.0,v6_hard_cases,2400.0
v5_reliability_only,30,0.43333333333333335,84.33802083333332,12.04786316666667,0.84,0.9023506172839506,900,80.0,v6_hard_cases,2400.0


## Cross-Validation Sanity Check

selector,groups,success,mean_selected_true_score,mean_regret,pairwise_accuracy,pairwise_roc_auc,pairwise_examples
v5_learned_full_cv,110,0.509090909090909,104.07278945454546,0.07802722727272737,0.9006060606060606,0.964099173553719,3300
v5_no_transformer_votes_cv,110,0.509090909090909,104.06128022727273,0.08953645454545486,0.9109090909090909,0.9648400367309458,3300
v5_no_symbolic_reliability_cv,110,0.509090909090909,104.08270204545454,0.06811463636363635,0.9084848484848485,0.9634303030303031,3300
v5_no_simulation_reliability_cv,110,0.4909090909090909,102.22057204545453,1.930244636363637,0.7790909090909091,0.8693158861340679,3300
v5_votes_only_cv,110,0.4818181818181818,101.32870159090908,2.8221150909090915,0.6703030303030303,0.7681395775941229,3300
v5_reliability_only_cv,110,0.509090909090909,101.87779004545457,2.273026636363637,0.883030303030303,0.9478372819100092,3300


## Learned Weights

selector,feature,weight
v5_learned_full,vote_feature_only,0.4268227494147918
v5_learned_full,vote_transformer_fused,0.7835498616853893
v5_learned_full,vote_transformer_only,0.42279626158037004
v5_learned_full,vote_symbolic_only,0.5787231366867082
v5_learned_full,vote_shortest_tree,0.021577717428458397
v5_learned_full,symbolic_reliability_norm,0.7422060074598272
v5_learned_full,simulation_reliability_norm,8.719712178380771
v5_learned_full,intercept,2.393319483186272e-13


## Outputs

- Ablation CSV: `experiments/bt_selection_benchmark/results/v5_learned_ensemble_ablation.csv`
- Choices CSV: `experiments/bt_selection_benchmark/results/v5_learned_ensemble_choices.csv`
- Scored candidates CSV: `experiments/bt_selection_benchmark/results/v5_learned_ensemble_scored_candidates.csv`
