# Rule-Based Selector Report

Generated: 2026-08-12 04:03:51

## Inputs

- Selector baseline summary: `experiments/bt_selection_benchmark/results/summary_by_selector_v1_supported_by.csv`
- Rule-based summary: `experiments/bt_selection_benchmark/results/rule_based_selector_summary_v1_supported_by.csv`
- Rule-based choices: `experiments/bt_selection_benchmark/results/rule_based_selector_choices_v1_supported_by.csv`

## Method

The selector ranks candidate behavior trees for the same task and initial state. The symbolic version uses BT structure and KIOS execution metrics; the simulation-aware version adds available LL4MA/Isaac Gym metrics.

Symbolic score:

```text
50 * symbolic_success
+ 20 * goal_satisfaction
+ 15 * precondition_coverage
- 10 * invalid_action_count
- 5  * condition_failure_count
- 0.5 * tree_size
- 0.3 * tree_depth
- 0.2 * bt_ticks
- 0.5 * action_count
```

Simulation-aware additions:

```text
+ 100 * sim_success
- 10 * final_position_error
- 5  * object_displacement_error
- 10 * contact_violation_proxy
```

## Existing Selector Baselines

| Selector | Groups | Success | Goal satisfaction | Mean selected score | Mean regret |
| --- | --- | --- | --- | --- | --- |
| random_expected | 20 | 62.5% | 0.625 | 26.083 | 39.917 |
| first_candidate | 20 | 100.0% | 1.000 | 66.000 | 0.000 |
| shortest_tree | 20 | 25.0% | 0.250 | -13.000 | 79.000 |
| symbolic_success | 20 | 100.0% | 1.000 | 54.125 | 11.875 |
| rule_based | 20 | 100.0% | 1.000 | 66.000 | 0.000 |
| oracle | 20 | 100.0% | 1.000 | 66.000 | 0.000 |

## Proposed Rule-Based Selectors

| Selector | Groups | Symbolic success | Simulation success | Goal satisfaction | Model score | True score | Regret |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rule_based_symbolic | 20 | 100.0% | N/A | 1.000 | 80.400 | 66.000 | 0.000 |
| rule_based_simulation | 20 | 100.0% | N/A | 1.000 | 80.400 | 66.000 | 0.000 |

## Choice Preview

| Selector | Task | Initial state | Selected | Oracle | Regret |
| --- | --- | --- | --- | --- | --- |
| rule_based_symbolic | place_block3_on_block5 | state_000_t0 | correct_bt | correct_bt | 0.0 |
| rule_based_symbolic | place_block1_on_block5 | state_000_t0 | correct_bt | correct_bt | 0.0 |
| rule_based_symbolic | place_block2_on_block6 | state_000_t0 | correct_bt | correct_bt | 0.0 |
| rule_based_symbolic | stack_block3_on_block1 | state_000_t0 | correct_bt | correct_bt | 0.0 |
| rule_based_symbolic | place_block3_on_block5 | state_001_t1 | correct_bt | correct_bt | 0.0 |
| rule_based_symbolic | place_block1_on_block5 | state_001_t1 | correct_bt | correct_bt | 0.0 |
| rule_based_symbolic | place_block2_on_block6 | state_001_t1 | correct_bt | correct_bt | 0.0 |
| rule_based_symbolic | stack_block3_on_block1 | state_001_t1 | correct_bt | correct_bt | 0.0 |

## Interpretation

- The symbolic rule-based selector improves over uniform random selection by 37.5% symbolic success.
- The shortest-tree heuristic performs poorly in this benchmark (25.0% success), showing that smaller BTs are not necessarily reliable.
- Compared with selecting any symbolically successful BT, the weighted selector reduces mean regret by 11.875.
- The current rule-based selector matches the oracle upper bound on this symbolic benchmark, with mean regret 0.000.
- Simulation-aware scoring is implemented, but current `sim_success` fields are not populated, so the simulation-aware selector is not yet distinguishable from symbolic scoring.

## Next Step

Populate simulation metrics and add harder constrained-packing/retrieval tasks so that symbolic and simulation-aware scoring can be compared meaningfully.
