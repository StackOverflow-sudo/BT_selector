# Rule-Based Selector Report

Generated: 2026-08-15 03:41:07

## Inputs

- Selector baseline summary: `experiments/bt_selection_benchmark/results/summary_by_selector_v2b_physical_strategy_with_sim.csv`
- Rule-based summary: `experiments/bt_selection_benchmark/results/rule_based_selector_summary_v2b_physical_strategy_with_sim.csv`
- Rule-based choices: `experiments/bt_selection_benchmark/results/rule_based_selector_choices_v2b_physical_strategy_with_sim.csv`

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
| random_expected | 20 | 100.0% | 1.000 | 97.850 | 21.818 |
| first_candidate | 20 | 100.0% | 1.000 | 114.397 | 5.272 |
| shortest_tree | 20 | 100.0% | 1.000 | 114.397 | 5.272 |
| symbolic_success | 20 | 100.0% | 1.000 | 114.397 | 5.272 |
| rule_based | 20 | 100.0% | 1.000 | 114.397 | 5.272 |
| oracle | 20 | 100.0% | 1.000 | 119.669 | 0.000 |

## Proposed Rule-Based Selectors

| Selector | Groups | Symbolic success | Simulation success | Sim coverage | Goal satisfaction | Model score | True score | Regret |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule_based_symbolic | 20 | 100.0% | 50.0% | 100.0% | 1.000 | 80.400 | 114.397 | 5.272 |
| rule_based_simulation | 20 | 100.0% | 55.0% | 100.0% | 1.000 | 122.477 | 119.666 | 0.003 |

## Choice Preview

| Selector | Task | Initial state | Selected | Oracle | Regret |
| --- | --- | --- | --- | --- | --- |
| rule_based_symbolic | place_block3_on_block5 | state_000_t0 | correct_bt | center_place_bt | 0.418164 |
| rule_based_symbolic | place_block1_on_block5 | state_000_t0 | correct_bt | edge_place_bt | 0.028472 |
| rule_based_symbolic | stack_block1_on_block3 | state_000_t0 | correct_bt | corner_place_bt | 0.045484 |
| rule_based_symbolic | stack_block3_on_block1 | state_000_t0 | correct_bt | correct_bt | 0.0 |
| rule_based_symbolic | place_block3_on_block5 | state_001_t1 | correct_bt | center_place_bt | 0.453392 |
| rule_based_symbolic | place_block1_on_block5 | state_001_t1 | correct_bt | corner_place_bt | 0.282494 |
| rule_based_symbolic | stack_block1_on_block3 | state_001_t1 | correct_bt | far_offset_bt | 0.829434 |
| rule_based_symbolic | stack_block3_on_block1 | state_001_t1 | correct_bt | far_offset_bt | 0.98982 |

## Interpretation

- The symbolic rule-based selector improves over uniform random selection by 0.0% symbolic success.
- The shortest-tree heuristic performs poorly in this benchmark (100.0% success), showing that smaller BTs are not necessarily reliable.
- Compared with selecting any symbolically successful BT, the weighted selector reduces mean regret by 0.000.
- The symbolic rule-based selector does not match the oracle on this benchmark; its mean regret is 5.272.
- Simulation metrics are fully populated and reduce mean regret from 5.272 to 0.003. This indicates that simulation-aware scoring is helping choose physically better BT candidates.

## Next Step

Analyze which placement strategies the simulation-aware selector prefers, then turn the V2B result into paper tables.
