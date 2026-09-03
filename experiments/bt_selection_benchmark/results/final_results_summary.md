# Final Results Summary

Generated: 2026-08-15

## Project Claim

This project proposes a simulation-grounded Behavior Tree selection framework for robot task planning. Given a task, a symbolic world state, and multiple candidate Behavior Trees, the system evaluates symbolic executability with KIOS, collects physical executability labels with Isaac Gym, and trains learned ranking selectors to choose the best candidate BT.

The final method can be described as:

```text
Simulation-Grounded BT-Structure-Aware Transformer Ranking Selector
```

The core idea is not to generate a single BT directly, but to rank multiple candidate BTs using symbolic, structural, and simulation-grounded supervision signals.

## System Architecture

```text
Task input / symbolic goal
        |
        v
Scene state / LL4MA / point-cloud-derived object state
        |
        v
Points2Plans bridge -> KIOS symbolic world
        |
        v
Candidate BT generation
        |
        v
KIOS symbolic evaluation ----> symbolic features
        |
        v
Isaac Gym simulation --------> physical labels
        |
        v
Learned BT ranking selector
        |
        v
Selected executable Behavior Tree
```

## Components

| Component | Role |
| --- | --- |
| Points2Plans bridge | Converts scene/object states into KIOS-compatible symbolic predicates and constraints. |
| Candidate BT generator | Produces multiple BT candidates for the same task and initial state. |
| KIOS | Symbolically executes BTs and produces executability features such as goal satisfaction, precondition coverage, tree size, and failure counts. |
| Isaac Gym | Physically simulates BT execution and provides supervision labels such as `sim_success`, final position error, object displacement, and contact violation proxy. |
| Learned selector | Learns to rank candidate BTs using simulation-grounded labels. |
| BT token / Transformer encoder | Encodes BT structure explicitly from serialized BT JSON token sequences. |

## Experiment Stages

| Stage | Purpose | Output |
| --- | --- | --- |
| V1 supported_by | Validate the full symbolic-to-simulation pipeline on shelf/support tasks. | 120 candidate rows, 100 simulated, 20 skipped invalid. |
| V2A stacking probe | Test harder movable-on-movable stacking tasks. | 240 candidate rows, 200 simulated, 40 skipped invalid. |
| V2B physical strategy | Make candidates symbolically equivalent but physically different. | 120 candidate rows, all simulated. |
| V3A feature selector | Train a binary classifier for `sim_success`. | First learned selector baseline. |
| V3B pairwise ranker | Learn pairwise preference between BT candidates. | Strong learned ranking baseline. |
| V3C generalization + ablation | Test cross-benchmark, cross-task, and feature ablations. | Evidence that the model is not only memorizing candidate names. |
| V4A BT token encoder | Add explicit BT structure tokens using TF-IDF/n-gram features. | Lightweight structure-aware selector. |
| V4B Transformer encoder | Replace TF-IDF token encoder with a small Transformer encoder. | Transformer prototype for BT structure encoding. |

## Baseline Selector Results

### V1 Supported-By

| Selector | Groups | Success | Mean Score | Mean Regret |
| --- | ---: | ---: | ---: | ---: |
| random_expected | 20 | 0.625 | 63.987 | 80.655 |
| first_candidate | 20 | 1.000 | 144.642 | 0.000 |
| shortest_tree | 20 | 0.250 | -13.000 | 157.642 |
| symbolic_success | 20 | 1.000 | 103.076 | 41.566 |
| rule_based | 20 | 1.000 | 144.642 | 0.000 |
| oracle | 20 | 1.000 | 144.642 | 0.000 |

### V2A Stacking Probe

| Selector | Groups | Success | Mean Score | Mean Regret |
| --- | ---: | ---: | ---: | ---: |
| random_expected | 40 | 0.563 | 40.183 | 64.236 |
| first_candidate | 40 | 1.000 | 104.420 | 0.000 |
| shortest_tree | 40 | 0.125 | -23.000 | 127.420 |
| symbolic_success | 40 | 1.000 | 78.819 | 25.601 |
| rule_based | 40 | 1.000 | 104.420 | 0.000 |
| oracle | 40 | 1.000 | 104.420 | 0.000 |

### V2B Physical Strategy

| Selector | Groups | Success | Mean Score | Mean Regret |
| --- | ---: | ---: | ---: | ---: |
| random_expected | 20 | 1.000 | 97.850 | 21.818 |
| first_candidate | 20 | 1.000 | 114.397 | 5.272 |
| shortest_tree | 20 | 1.000 | 114.397 | 5.272 |
| symbolic_success | 20 | 1.000 | 114.397 | 5.272 |
| rule_based | 20 | 1.000 | 114.397 | 5.272 |
| oracle | 20 | 1.000 | 119.669 | 0.000 |

## Rule-Based Simulation-Aware Results

| Benchmark | Selector | Groups | Selected Sim Success | Mean True Score | Mean Regret |
| --- | --- | ---: | ---: | ---: | ---: |
| V1 | rule_based_symbolic | 20 | 0.800 | 144.642 | 0.000 |
| V1 | rule_based_simulation | 20 | 0.800 | 144.642 | 0.000 |
| V2A | rule_based_symbolic | 40 | 0.400 | 104.420 | 0.000 |
| V2A | rule_based_simulation | 40 | 0.400 | 104.420 | 0.000 |
| V2B | rule_based_symbolic | 20 | 0.500 | 114.397 | 5.272 |
| V2B | rule_based_simulation | 20 | 0.550 | 119.666 | 0.003 |

Key observation: V2B is the most important physical-strategy benchmark because symbolic selectors cannot distinguish physically different placement strategies. Adding simulation-aware scoring reduces regret from 5.272 to 0.003.

## Learned Selector Results

### V3A: Feature-Based Classification

| Selector | Groups | Success | Mean Selected True Score | Mean Regret |
| --- | ---: | ---: | ---: | ---: |
| learned_feature | 80 | 0.5375 | 106.614 | 0.449 |
| symbolic_only | 80 | 0.3750 | 91.142 | 15.920 |
| shortest_tree | 80 | 0.1250 | 18.496 | 88.566 |
| oracle | 80 | 0.5375 | 107.063 | 0.000 |

### V3B: Pairwise Ranking

| Selector | Groups | Success | Mean Selected True Score | Mean Regret |
| --- | ---: | ---: | ---: | ---: |
| learned_pairwise | 80 | 0.5375 | 106.883 | 0.180 |
| symbolic_only | 80 | 0.3750 | 91.142 | 15.920 |
| shortest_tree | 80 | 0.1250 | 18.496 | 88.566 |
| oracle | 80 | 0.5375 | 107.063 | 0.000 |

V3B is the strongest learned baseline. It directly optimizes candidate ordering and reduces mean regret from 15.920 for symbolic-only selection to 0.180.

## Generalization And Ablation

| Split Mode | Ablation | Success | Mean Regret | Pairwise Accuracy | Pairwise ROC-AUC |
| --- | --- | ---: | ---: | ---: | ---: |
| mixed_group_cv | full | 0.5375 | 0.180 | 0.833 | 0.942 |
| mixed_group_cv | no_candidate_type | 0.5375 | 0.161 | 0.841 | 0.947 |
| mixed_group_cv | no_symbolic_features | 0.5000 | 3.931 | 0.828 | 0.936 |
| leave_one_benchmark_out | full | 0.5375 | 0.161 | 0.833 | 0.941 |
| leave_one_benchmark_out | no_candidate_type | 0.5375 | 0.161 | 0.833 | 0.942 |
| leave_one_benchmark_out | no_symbolic_features | 0.5000 | 3.911 | 0.803 | 0.903 |
| leave_one_task_out | full | 0.5375 | 0.198 | 0.838 | 0.943 |
| leave_one_task_out | no_candidate_type | 0.5375 | 0.161 | 0.833 | 0.942 |
| leave_one_task_out | no_symbolic_features | 0.5000 | 3.963 | 0.827 | 0.932 |

Key observations:

- Removing `candidate_type` does not hurt performance, which suggests the model is not simply memorizing candidate names.
- Removing symbolic features increases regret, showing that KIOS-derived symbolic executability features are important.
- Leave-one-benchmark and leave-one-task results remain close to mixed cross-validation, supporting generalization.

## Structure-Aware Selector Results

### V4A: BT Token Encoder

| Selector | Success | Mean Regret | Pairwise Accuracy | Pairwise ROC-AUC |
| --- | ---: | ---: | ---: | ---: |
| feature_only | 0.5375 | 0.180 | 0.833 | 0.942 |
| bt_token_only | 0.5000 | 3.937 | 0.836 | 0.939 |
| fused | 0.5375 | 0.180 | 0.840 | 0.945 |
| symbolic_only | 0.3750 | 15.920 | n/a | n/a |
| oracle | 0.5375 | 0.000 | n/a | n/a |

V4A shows that BT token sequences contain useful structural information. The token-only model achieves high pairwise ROC-AUC, and the fused model improves pairwise ROC-AUC over feature-only.

### V4B: Lightweight Transformer Encoder

| Selector | Success | Mean Regret | Pairwise Accuracy | Pairwise ROC-AUC |
| --- | ---: | ---: | ---: | ---: |
| feature_only | 0.5375 | 0.180 | 0.833 | 0.942 |
| transformer_only | 0.5000 | 3.937 | 0.838 | 0.939 |
| transformer_fused | 0.5125 | 2.677 | 0.873 | 0.952 |
| symbolic_only | 0.3750 | 15.920 | n/a | n/a |
| oracle | 0.5375 | 0.000 | n/a | n/a |

V4B demonstrates that a Transformer BT encoder can learn useful pairwise preference signals. The fused Transformer model obtains the highest pairwise ROC-AUC, but it does not yet achieve the lowest top-1 selection regret. This is expected with the current small dataset.

## Final Interpretation

The strongest top-1 selector is the feature-based pairwise ranker from V3B:

```text
mean_regret = 0.180
```

The strongest pairwise preference model is the fused Transformer selector from V4B:

```text
pairwise ROC-AUC = 0.952
```

This supports the final thesis narrative:

```text
KIOS symbolic evaluation provides strong executability features.
Isaac Gym simulation provides physical supervision.
Pairwise ranking matches the BT selection objective.
BT token and Transformer encoders provide explicit structure-aware representations.
```

## Recommended Paper Positioning

Use this hierarchy in the thesis:

| Role | Method |
| --- | --- |
| Traditional baselines | random, first candidate, shortest tree, symbolic success |
| Strong symbolic baseline | rule-based symbolic selector |
| Simulation-aware upper-style baseline | rule-based simulation selector |
| Strong learned baseline | V3B feature-based pairwise ranker |
| Proposed structure-aware extension | V4A BT token encoder |
| Proposed Transformer prototype | V4B lightweight Transformer encoder |

The final method name should emphasize the full framework:

```text
Simulation-Grounded BT-Structure-Aware Ranking Framework
```

The Transformer version can be described as an extensible model variant:

```text
Lightweight Transformer BT Encoder for Simulation-Grounded Pairwise Ranking
```

## Main Claims For The Thesis

1. Symbolic evaluation alone is insufficient when BT candidates are symbolically valid but physically different.
2. Simulation-aware supervision substantially improves BT selection in physically sensitive tasks.
3. Pairwise ranking is better aligned with the BT selection problem than independent success classification.
4. The learned selector generalizes across tasks and benchmarks and does not rely only on candidate-name memorization.
5. BT token and Transformer encoders provide useful structure-aware signals, although larger datasets are needed for the Transformer model to outperform the strongest feature-based ranker in top-1 regret.

## Key Result To Highlight

The most important quantitative comparison is:

```text
symbolic_only regret:       15.920
V3B learned pairwise regret: 0.180
oracle regret:               0.000
```

And the most important Transformer result is:

```text
feature_only ROC-AUC:        0.942
transformer_fused ROC-AUC:   0.952
```

Together, these results show that the project has both a strong practical selector and a credible structure-aware Transformer extension.
