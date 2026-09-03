# Final Experiment Results

This folder contains consolidated tables and figures generated from the existing benchmark CSV files.

## Dataset Coverage

| Benchmark | Candidate rows | Task-state groups | Sim done | Sim skipped | Sim pending |
| --- | ---: | ---: | ---: | ---: | ---: |
| V1 supported-by | 120 | 20 | 100 | 20 | 0 |
| V2 stacking probe | 240 | 40 | 200 | 40 | 0 |
| V2B physical strategy | 120 | 20 | 120 | 0 | 0 |
| V6 hard cases | 180 | 30 | 170 | 10 | 0 |

## Final Selector Table

| Source | Selector | Groups | Success | Mean true score | Mean regret | Pairwise acc. | ROC-AUC |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V5 manual ensemble | feature_only | 110 | 0.500 | 103.141 | 1.010 | 0.810 | 0.926 |
| V5 manual ensemble | transformer_only | 110 | 0.455 | 98.588 | 5.563 | 0.817 | 0.918 |
| V5 manual ensemble | transformer_fused | 110 | 0.491 | 102.194 | 1.957 | 0.842 | 0.928 |
| V5 manual ensemble | symbolic_only | 110 | 0.364 | 89.859 | 14.292 |  |  |
| V5 manual ensemble | shortest_tree | 110 | 0.182 | 37.025 | 67.126 |  |  |
| V5 manual ensemble | oracle | 110 | 0.509 | 104.151 | 0.000 |  |  |
| V5 manual ensemble | v5_ensemble | 110 | 0.500 | 103.162 | 0.989 |  |  |
| V4B transformer | feature_only | 110 | 0.500 | 103.141 | 1.010 | 0.810 | 0.926 |
| V4B transformer | transformer_only | 110 | 0.455 | 98.588 | 5.563 | 0.817 | 0.918 |
| V4B transformer | transformer_fused | 110 | 0.491 | 102.194 | 1.957 | 0.842 | 0.928 |
| V4B transformer | symbolic_only | 110 | 0.364 | 89.859 | 14.292 |  |  |
| V4B transformer | shortest_tree | 110 | 0.182 | 37.025 | 67.126 |  |  |
| V4B transformer | oracle | 110 | 0.509 | 104.151 | 0.000 |  |  |
| V6 hard cases | random_expected |  |  |  | 31.009 |  |  |
| V6 hard cases | first_candidate |  |  |  | 10.061 |  |  |
| V6 hard cases | shortest_tree |  |  |  | 18.618 |  |  |
| V6 hard cases | symbolic_success |  |  |  | 18.618 |  |  |
| V6 hard cases | rule_based |  |  |  | 10.061 |  |  |
| V6 hard cases | oracle |  |  |  | 0.000 |  |  |
| learned_v5 | v5_learned_full | 30 | 0.433 | 96.337 | 0.049 |  |  |
| learned_v5 | v5_no_transformer_votes | 30 | 0.433 | 96.263 | 0.123 |  |  |
| learned_v5 | v5_no_symbolic_reliability | 30 | 0.433 | 94.035 | 2.351 |  |  |
| learned_v5 | v5_no_simulation_reliability | 30 | 0.400 | 93.088 | 3.298 |  |  |

## Learned V5 Ablation

| Variant | Source | Groups | Success | Mean true score | Mean regret |
| --- | --- | ---: | ---: | ---: | ---: |
| v5_learned_full | learned_v5 | 30 | 0.433 | 96.337 | 0.049 |
| v5_no_transformer_votes | learned_v5 | 30 | 0.433 | 96.263 | 0.123 |
| v5_no_symbolic_reliability | learned_v5 | 30 | 0.433 | 94.035 | 2.351 |
| v5_no_simulation_reliability | learned_v5 | 30 | 0.400 | 93.088 | 3.298 |
| v5_votes_only | learned_v5 | 30 | 0.400 | 92.937 | 3.449 |
| v5_reliability_only | learned_v5 | 30 | 0.433 | 84.338 | 12.048 |
| feature_only | learned_v5 | 30 | 0.400 | 93.130 | 3.256 |
| transformer_fused | learned_v5 | 30 | 0.400 | 92.937 | 3.449 |
| transformer_only | learned_v5 | 30 | 0.333 | 86.456 | 9.930 |
| manual_v5 | learned_v5 | 30 | 0.400 | 93.151 | 3.235 |
| symbolic_only | learned_v5 | 30 | 0.333 | 86.435 | 9.951 |
| shortest_tree | learned_v5 | 30 | 0.333 | 86.435 | 9.951 |
| oracle | learned_v5 | 30 | 0.433 | 96.386 | 0.000 |

## Figures

- `fig_dataset_simulation_coverage.png`
- `fig_selector_success_by_benchmark.png`
- `fig_selector_regret_by_benchmark.png`
- `fig_final_selector_regret.png`
- `fig_final_selector_success.png`
- `fig_v5_ablation_regret.png`
- `fig_v5_ablation_success.png`

## GPT Single-vs-Multi Note

A GPT single-vs-multi summary file exists, but it should only be used if API rate-limit failures have been excluded or rerun successfully.
