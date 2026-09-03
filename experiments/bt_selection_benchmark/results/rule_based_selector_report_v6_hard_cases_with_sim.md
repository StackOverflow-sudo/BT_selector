# Rule-Based Selector Report

Generated: 2026-08-17 08:22:52

## Inputs

- Selector baseline summary: `experiments/bt_selection_benchmark/results/summary_by_selector_v6_hard_cases_with_sim.csv`
- Rule-based summary: `experiments/bt_selection_benchmark/results/rule_based_selector_summary_v6_hard_cases_with_sim.csv`
- Rule-based choices: `experiments/bt_selection_benchmark/results/rule_based_selector_choices_v6_hard_cases_with_sim.csv`

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
| random_expected | 30 | 88.9% | 0.889 | 75.704 | 31.009 |
| first_candidate | 30 | 100.0% | 1.000 | 96.652 | 10.061 |
| shortest_tree | 30 | 100.0% | 1.000 | 88.095 | 18.618 |
| symbolic_success | 30 | 100.0% | 1.000 | 88.095 | 18.618 |
| rule_based | 30 | 100.0% | 1.000 | 96.652 | 10.061 |
| oracle | 30 | 100.0% | 1.000 | 106.713 | 0.000 |

## Proposed Rule-Based Selectors

| Selector | Groups | Symbolic success | Simulation success | Sim coverage | Goal satisfaction | Model score | True score | Regret |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule_based_symbolic | 30 | 100.0% | 33.3% | 100.0% | 1.000 | 79.733 | 96.652 | 10.061 |
| rule_based_simulation | 30 | 100.0% | 43.3% | 100.0% | 1.000 | 109.445 | 106.700 | 0.013 |

## Choice Preview

| Selector | Task | Initial state | Selected | Oracle | Regret |
| --- | --- | --- | --- | --- | --- |
| rule_based_symbolic | hard_physical_place_block3_on_block5 | state_000_t0 | stable_center_bt | stable_center_bt | 0.0 |
| rule_based_symbolic | hard_physical_place_block1_on_block5 | state_000_t0 | stable_center_bt | stable_center_bt | 0.0 |
| rule_based_symbolic | long_horizon_clear_then_stack_block2_on_block3 | state_000_t0 | correct_order_bt | wrong_order_bt | 0.020656 |
| rule_based_symbolic | long_horizon_prepare_then_stack_block1_on_block3 | state_000_t0 | correct_order_bt | wrong_order_bt | 0.062366 |
| rule_based_symbolic | constrained_support_block3_on_block1 | state_000_t0 | stable_center_bt | narrow_edge_bt | 100.6388 |
| rule_based_symbolic | constrained_support_block1_on_block3 | state_000_t0 | stable_center_bt | symbolic_edge_bt | 100.64538 |
| rule_based_symbolic | hard_physical_place_block3_on_block5 | state_001_t1 | stable_center_bt | stable_center_bt | 0.0 |
| rule_based_symbolic | hard_physical_place_block1_on_block5 | state_001_t1 | stable_center_bt | symbolic_corner_bt | 0.021168 |

## Interpretation

- The symbolic rule-based selector improves over uniform random selection by 11.1% symbolic success.
- The shortest-tree heuristic performs poorly in this benchmark (100.0% success), showing that smaller BTs are not necessarily reliable.
- Compared with selecting any symbolically successful BT, the weighted selector reduces mean regret by 8.557.
- The symbolic rule-based selector does not match the oracle on this benchmark; its mean regret is 10.061.
- Simulation metrics are fully populated and reduce mean regret from 10.061 to 0.013. This indicates that simulation-aware scoring is helping choose physically better BT candidates.

## Next Step

Analyze which placement strategies the simulation-aware selector prefers, then turn the V2B result into paper tables.
