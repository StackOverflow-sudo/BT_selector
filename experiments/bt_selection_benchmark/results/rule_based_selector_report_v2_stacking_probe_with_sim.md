# Rule-Based Selector Report

Generated: 2026-08-15 02:32:32

## Inputs

- Selector baseline summary: `experiments/bt_selection_benchmark/results/summary_by_selector_v2_stacking_probe_with_sim.csv`
- Rule-based summary: `experiments/bt_selection_benchmark/results/rule_based_selector_summary_v2_stacking_probe_with_sim.csv`
- Rule-based choices: `experiments/bt_selection_benchmark/results/rule_based_selector_choices_v2_stacking_probe_with_sim.csv`

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
| random_expected | 40 | 56.2% | 0.562 | 40.183 | 64.236 |
| first_candidate | 40 | 100.0% | 1.000 | 104.420 | 0.000 |
| shortest_tree | 40 | 12.5% | 0.125 | -23.000 | 127.420 |
| symbolic_success | 40 | 100.0% | 1.000 | 78.819 | 25.601 |
| rule_based | 40 | 100.0% | 1.000 | 104.420 | 0.000 |
| oracle | 40 | 100.0% | 1.000 | 104.420 | 0.000 |

## Proposed Rule-Based Selectors

| Selector | Groups | Symbolic success | Simulation success | Sim coverage | Goal satisfaction | Model score | True score | Regret |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule_based_symbolic | 40 | 100.0% | 40.0% | 100.0% | 1.000 | 80.400 | 104.420 | 0.000 |
| rule_based_simulation | 40 | 100.0% | 40.0% | 100.0% | 1.000 | 107.143 | 104.420 | 0.000 |

## Choice Preview

| Selector | Task | Initial state | Selected | Oracle | Regret |
| --- | --- | --- | --- | --- | --- |
| rule_based_symbolic | place_block3_on_block5 | state_000_t0 | correct_bt | correct_bt | 0.0 |
| rule_based_symbolic | place_block1_on_block5 | state_000_t0 | correct_bt | correct_bt | 0.0 |
| rule_based_symbolic | place_block2_on_block6 | state_000_t0 | correct_bt | correct_bt | 0.0 |
| rule_based_symbolic | stack_block3_on_block1 | state_000_t0 | correct_bt | correct_bt | 0.0 |
| rule_based_symbolic | stack_block1_on_block3 | state_000_t0 | correct_bt | correct_bt | 0.0 |
| rule_based_symbolic | stack_block2_on_block1 | state_000_t0 | correct_bt | correct_bt | 0.0 |
| rule_based_symbolic | stack_block4_on_block1 | state_000_t0 | correct_bt | correct_bt | 0.0 |
| rule_based_symbolic | stack_block3_on_block2 | state_000_t0 | correct_bt | correct_bt | 0.0 |

## Interpretation

- The symbolic rule-based selector improves over uniform random selection by 43.8% symbolic success.
- The shortest-tree heuristic performs poorly in this benchmark (12.5% success), showing that smaller BTs are not necessarily reliable.
- Compared with selecting any symbolically successful BT, the weighted selector reduces mean regret by 25.601.
- The current rule-based selector matches the oracle upper bound on this symbolic benchmark, with mean regret 0.000.
- Simulation metrics are fully populated for selected cases. If symbolic and simulation-aware choices still match, the next useful step is to add harder tasks where physical execution can disambiguate symbolically valid BTs.

## Next Step

Add harder constrained-packing/retrieval tasks so that symbolic and simulation-aware scoring can be compared on cases where physical feasibility matters.
