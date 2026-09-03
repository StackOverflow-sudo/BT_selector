# Strict V6 Holdout Audit

## Finding

The dataset split has no task-state group overlap between development sources and V6.
The legacy V4B choices are group-level out-of-fold estimates over all 110 groups; a V6 choice can therefore come from a base model trained on other V6 groups.
They must not be described as a strict benchmark-level V6 holdout.

This audit retrains all preprocessing and base models on V1/V2/V2B before scoring any V6 candidate.
Vocabulary, scaling, categorical encoding, Transformer parameters, and V5 weights therefore exclude V6.

## Split Audit

source_benchmark,rows,groups,positive_sim_success
v1_supported_by,120,20,46
v2_stacking_probe,240,40,46
v2b_physical_strategy,120,20,41
v6_hard_cases,180,30,43

Task-state group overlap: 0
Transformer epochs: 10

## Strict External Results

selector,groups,success,mean_selected_true_score,mean_regret,pairwise_accuracy,pairwise_roc_auc,pairwise_examples,train_groups,test_groups,pairwise_train_examples,evaluation_mode
v5_strict_no_simulation,30,0.4,93.11233566666668,3.273548333333332,0.6244444444444445,0.7042222222222222,900,80.0,30.0,2400.0,pre_simulation
v5_strict_simulation_reranker,30,0.43333333333333335,96.35211783333332,0.033766166666664786,0.9066666666666666,0.942241975308642,900,80.0,30.0,2400.0,post_simulation
v5_learned_full,30,0.43333333333333335,96.35211783333332,0.033766166666664786,0.9066666666666666,0.942241975308642,900,80.0,30.0,2400.0,post_simulation
v5_no_transformer_votes,30,0.43333333333333335,96.23889283333332,0.14699116666666565,0.9022222222222223,0.9385975308641975,900,80.0,30.0,2400.0,post_simulation
v5_no_symbolic_reliability,30,0.43333333333333335,96.35211783333332,0.033766166666664786,0.8955555555555555,0.9352740740740741,900,80.0,30.0,2400.0,post_simulation
v5_no_simulation_reliability,30,0.4,93.11233566666668,3.273548333333332,0.6244444444444445,0.7042222222222222,900,80.0,30.0,2400.0,post_simulation
v5_votes_only,30,0.4,93.16707833333334,3.2188056666666642,0.6133333333333333,0.6907308641975307,900,80.0,30.0,2400.0,post_simulation
v5_reliability_only,30,0.43333333333333335,84.33802083333332,12.04786316666667,0.84,0.9023506172839506,900,80.0,30.0,2400.0,post_simulation
feature_only,30,0.4,93.16707833333334,3.2188056666666642,,,0,,,,pre_simulation
transformer_fused,30,0.4,93.13829383333334,3.2475901666666647,,,0,,,,pre_simulation
transformer_only,30,0.36666666666666664,89.80944266666665,6.5764413333333325,,,0,,,,pre_simulation
symbolic_only,30,0.3333333333333333,86.435199,9.950684999999998,,,0,,,,pre_simulation
shortest_tree,30,0.3333333333333333,86.435199,9.950684999999998,,,0,,,,pre_simulation
manual_v5,30,0.4,93.20363583333332,3.1822481666666635,,,0,,,,post_simulation
oracle,30,0.43333333333333335,96.38588399999999,0.0,,,0,,,,evaluation_upper_bound


## Interpretation Boundary

`v5_strict_no_simulation` uses base-selector votes and symbolic reliability only and is the valid pre-rollout result.
`v5_strict_simulation_reranker` also uses candidate simulation outcomes and is a simulate-then-select result, not zero-rollout prediction.
