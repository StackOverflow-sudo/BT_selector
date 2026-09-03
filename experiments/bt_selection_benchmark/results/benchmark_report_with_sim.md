# BT Selection Benchmark Report

Generated: 2026-07-12 04:13:10

## Inputs

- Candidate evaluations: `experiments/bt_selection_benchmark/results/bt_candidate_evaluations_with_sim.csv`
- Selector summary: `experiments/bt_selection_benchmark/results/summary_by_selector_with_sim.csv`
- Selector choices: `experiments/bt_selection_benchmark/results/selector_choices_with_sim.csv`

## Dataset Summary

| Metric | Value |
| --- | --- |
| Tasks | 3 |
| Initial states | 1 |
| Candidate BTs | 18 |
| Candidate types | 6 |
| Overall symbolic success | 50.0% |

## Candidate Type Performance

| Candidate type | Count | Symbolic success | Goal satisfaction | Mean score | Precondition coverage | Mean tree size | Mean ticks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| correct_bt | 3 | 100.0% | 1.000 | 165.160 | 1.000 | 6.00 | 5.00 |
| missing_precondition_bt | 3 | 100.0% | 1.000 | 155.833 | 0.500 | 5.00 | 5.00 |
| redundant_bt | 3 | 100.0% | 1.000 | 131.161 | 1.000 | 8.00 | 5.00 |
| unsafe_or_invalid_bt | 3 | 0.0% | 0.000 | -32.000 | 0.000 | 4.00 | 0.00 |
| wrong_object_bt | 3 | 0.0% | 0.000 | -31.303 | 0.000 | 6.00 | 10.00 |
| wrong_support_bt | 3 | 0.0% | 0.000 | -18.206 | 0.500 | 6.00 | 10.00 |

## Task-Level Summary

| Task | Candidates | Symbolic success | Best score | Mean score |
| --- | --- | --- | --- | --- |
| place_block1_on_block5 | 6 | 50.0% | 165.080 | 67.376 |
| place_block2_on_block6 | 6 | 50.0% | 165.419 | 50.350 |
| place_block3_on_block5 | 6 | 50.0% | 164.980 | 67.596 |

## Selector Baseline Summary

| Selector | Groups | Selected success | Goal satisfaction | Mean selected score | Mean regret |
| --- | --- | --- | --- | --- | --- |
| random_expected | 3 | 50.0% | 0.500 | 61.774 | 103.386 |
| first_candidate | 3 | 100.0% | 1.000 | 165.160 | 0.000 |
| shortest_tree | 3 | 0.0% | 0.000 | -32.000 | 197.160 |
| symbolic_success | 3 | 100.0% | 1.000 | 155.833 | 9.326 |
| rule_based | 3 | 100.0% | 1.000 | 165.160 | 0.000 |
| oracle | 3 | 100.0% | 1.000 | 165.160 | 0.000 |

## Selector Choices

| Selector | Task | Selected candidate | Selected success | Oracle candidate | Regret |
| --- | --- | --- | --- | --- | --- |
| first_candidate | place_block3_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| first_candidate | place_block1_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| first_candidate | place_block2_on_block6 | correct_bt | 1 | correct_bt | 0.0 |
| shortest_tree | place_block3_on_block5 | unsafe_or_invalid_bt | 0 | correct_bt | 196.979938 |
| shortest_tree | place_block1_on_block5 | unsafe_or_invalid_bt | 0 | correct_bt | 197.080314 |
| shortest_tree | place_block2_on_block6 | unsafe_or_invalid_bt | 0 | correct_bt | 197.419192 |
| symbolic_success | place_block3_on_block5 | missing_precondition_bt | 1 | correct_bt | 8.99808 |
| symbolic_success | place_block1_on_block5 | missing_precondition_bt | 1 | correct_bt | 9.601644 |
| symbolic_success | place_block2_on_block6 | missing_precondition_bt | 1 | correct_bt | 9.37976 |
| rule_based | place_block3_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| rule_based | place_block1_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| rule_based | place_block2_on_block6 | correct_bt | 1 | correct_bt | 0.0 |

## Interpretation

- The oracle upper bound reaches 100.0% symbolic success, while uniform random selection reaches 50.0%.
- The rule-based selector improves over random selection by 50.0% symbolic success in this V0 setting.
- The symbolic-success selector reaches 100.0%, showing that KIOS execution traces already provide useful selection signals.
- The current benchmark contains 18 evaluated candidates across 3 tasks and 6 candidate types.
- Simulation metrics are still placeholders; the next stage should connect the selected candidates to Isaac Gym headless validation.

## Current Limitations

- This report is symbolic-only; Isaac Gym metrics are not populated yet.
- Candidate BTs are controlled synthetic candidates, not yet LLM-generated candidates.
- Only tasks marked `v0_required` are included in the default report.

## Next Step

Connect the evaluator to the existing Isaac Gym headless pipeline so that `sim_success`, `final_position_error`, and `object_displacement_error` become real simulation-grounded metrics.
