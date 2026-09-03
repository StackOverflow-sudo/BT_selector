# BT Selection Benchmark Report

Generated: 2026-07-16 05:22:36

## Inputs

- Candidate evaluations: `/home/theshy/projects/mycode/kios_baseline/experiments/bt_selection_benchmark/results/bt_candidate_evaluations.csv`
- Selector summary: `/home/theshy/projects/mycode/kios_baseline/experiments/bt_selection_benchmark/results/summary_by_selector.csv`
- Selector choices: `/home/theshy/projects/mycode/kios_baseline/experiments/bt_selection_benchmark/results/selector_choices.csv`

## Dataset Summary

| Metric | Value |
| --- | --- |
| Tasks | 3 |
| Initial states | 5 |
| Candidate BTs | 90 |
| Candidate types | 6 |
| Overall symbolic success | 61.1% |

## Candidate Type Performance

| Candidate type | Count | Symbolic success | Goal satisfaction | Mean score | Precondition coverage | Mean tree size | Mean ticks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| correct_bt | 15 | 100.0% | 1.000 | 66.000 | 1.000 | 6.00 | 3.67 |
| missing_precondition_bt | 15 | 100.0% | 1.000 | 56.500 | 0.500 | 5.00 | 3.67 |
| redundant_bt | 15 | 100.0% | 1.000 | 65.000 | 1.000 | 8.00 | 3.67 |
| unsafe_or_invalid_bt | 15 | 0.0% | 0.333 | -25.333 | 0.000 | 4.00 | 0.00 |
| wrong_object_bt | 15 | 33.3% | 0.333 | -6.667 | 0.000 | 6.00 | 7.00 |
| wrong_support_bt | 15 | 33.3% | 0.333 | 3.333 | 0.500 | 6.00 | 7.00 |

## Task-Level Summary

| Task | Candidates | Symbolic success | Best score | Mean score |
| --- | --- | --- | --- | --- |
| place_block1_on_block5 | 30 | 70.0% | 66.000 | 34.383 |
| place_block2_on_block6 | 30 | 50.0% | 66.000 | 16.583 |
| place_block3_on_block5 | 30 | 63.3% | 66.000 | 28.450 |

## Selector Baseline Summary

| Selector | Groups | Selected success | Goal satisfaction | Mean selected score | Mean regret |
| --- | --- | --- | --- | --- | --- |
| random_expected | 15 | 61.1% | 0.667 | 26.472 | 39.528 |
| first_candidate | 15 | 100.0% | 1.000 | 66.000 | 0.000 |
| shortest_tree | 15 | 0.0% | 0.333 | -25.333 | 91.333 |
| symbolic_success | 15 | 100.0% | 1.000 | 56.500 | 9.500 |
| rule_based | 15 | 100.0% | 1.000 | 66.000 | 0.000 |
| oracle | 15 | 100.0% | 1.000 | 66.000 | 0.000 |

## Selector Choices

| Selector | Task | Selected candidate | Selected success | Oracle candidate | Regret |
| --- | --- | --- | --- | --- | --- |
| first_candidate | place_block3_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| first_candidate | place_block1_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| first_candidate | place_block2_on_block6 | correct_bt | 1 | correct_bt | 0.0 |
| first_candidate | place_block3_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| first_candidate | place_block1_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| first_candidate | place_block2_on_block6 | correct_bt | 1 | correct_bt | 0.0 |
| first_candidate | place_block3_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| first_candidate | place_block1_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| first_candidate | place_block2_on_block6 | correct_bt | 1 | correct_bt | 0.0 |
| first_candidate | place_block3_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| first_candidate | place_block1_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| first_candidate | place_block2_on_block6 | correct_bt | 1 | correct_bt | 0.0 |
| first_candidate | place_block3_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| first_candidate | place_block1_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| first_candidate | place_block2_on_block6 | correct_bt | 1 | correct_bt | 0.0 |
| shortest_tree | place_block3_on_block5 | unsafe_or_invalid_bt | 0 | correct_bt | 98.0 |
| shortest_tree | place_block1_on_block5 | unsafe_or_invalid_bt | 0 | correct_bt | 98.0 |
| shortest_tree | place_block2_on_block6 | unsafe_or_invalid_bt | 0 | correct_bt | 98.0 |
| shortest_tree | place_block3_on_block5 | unsafe_or_invalid_bt | 0 | correct_bt | 98.0 |
| shortest_tree | place_block1_on_block5 | unsafe_or_invalid_bt | 0 | correct_bt | 98.0 |
| shortest_tree | place_block2_on_block6 | unsafe_or_invalid_bt | 0 | correct_bt | 98.0 |
| shortest_tree | place_block3_on_block5 | unsafe_or_invalid_bt | 0 | correct_bt | 98.0 |
| shortest_tree | place_block1_on_block5 | unsafe_or_invalid_bt | 0 | correct_bt | 78.0 |
| shortest_tree | place_block2_on_block6 | unsafe_or_invalid_bt | 0 | correct_bt | 98.0 |
| shortest_tree | place_block3_on_block5 | unsafe_or_invalid_bt | 0 | correct_bt | 78.0 |
| shortest_tree | place_block1_on_block5 | unsafe_or_invalid_bt | 0 | correct_bt | 78.0 |
| shortest_tree | place_block2_on_block6 | unsafe_or_invalid_bt | 0 | correct_bt | 98.0 |
| shortest_tree | place_block3_on_block5 | unsafe_or_invalid_bt | 0 | correct_bt | 78.0 |
| shortest_tree | place_block1_on_block5 | unsafe_or_invalid_bt | 0 | correct_bt | 78.0 |
| shortest_tree | place_block2_on_block6 | unsafe_or_invalid_bt | 0 | correct_bt | 98.0 |
| symbolic_success | place_block3_on_block5 | missing_precondition_bt | 1 | correct_bt | 9.5 |
| symbolic_success | place_block1_on_block5 | missing_precondition_bt | 1 | correct_bt | 9.5 |
| symbolic_success | place_block2_on_block6 | missing_precondition_bt | 1 | correct_bt | 9.5 |
| symbolic_success | place_block3_on_block5 | missing_precondition_bt | 1 | correct_bt | 9.5 |
| symbolic_success | place_block1_on_block5 | missing_precondition_bt | 1 | correct_bt | 9.5 |
| symbolic_success | place_block2_on_block6 | missing_precondition_bt | 1 | correct_bt | 9.5 |
| symbolic_success | place_block3_on_block5 | missing_precondition_bt | 1 | correct_bt | 9.5 |
| symbolic_success | place_block1_on_block5 | missing_precondition_bt | 1 | correct_bt | 9.5 |
| symbolic_success | place_block2_on_block6 | missing_precondition_bt | 1 | correct_bt | 9.5 |
| symbolic_success | place_block3_on_block5 | missing_precondition_bt | 1 | correct_bt | 9.5 |
| symbolic_success | place_block1_on_block5 | missing_precondition_bt | 1 | correct_bt | 9.5 |
| symbolic_success | place_block2_on_block6 | missing_precondition_bt | 1 | correct_bt | 9.5 |
| symbolic_success | place_block3_on_block5 | missing_precondition_bt | 1 | correct_bt | 9.5 |
| symbolic_success | place_block1_on_block5 | missing_precondition_bt | 1 | correct_bt | 9.5 |
| symbolic_success | place_block2_on_block6 | missing_precondition_bt | 1 | correct_bt | 9.5 |
| rule_based | place_block3_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| rule_based | place_block1_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| rule_based | place_block2_on_block6 | correct_bt | 1 | correct_bt | 0.0 |
| rule_based | place_block3_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| rule_based | place_block1_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| rule_based | place_block2_on_block6 | correct_bt | 1 | correct_bt | 0.0 |
| rule_based | place_block3_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| rule_based | place_block1_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| rule_based | place_block2_on_block6 | correct_bt | 1 | correct_bt | 0.0 |
| rule_based | place_block3_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| rule_based | place_block1_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| rule_based | place_block2_on_block6 | correct_bt | 1 | correct_bt | 0.0 |
| rule_based | place_block3_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| rule_based | place_block1_on_block5 | correct_bt | 1 | correct_bt | 0.0 |
| rule_based | place_block2_on_block6 | correct_bt | 1 | correct_bt | 0.0 |

## Interpretation

- The oracle upper bound reaches 100.0% symbolic success, while uniform random selection reaches 61.1%.
- The rule-based selector improves over random selection by 38.9% symbolic success in this V0 setting.
- The symbolic-success selector reaches 100.0%, showing that KIOS execution traces already provide useful selection signals.
- The current benchmark contains 90 evaluated candidates across 3 tasks and 6 candidate types.
- Simulation metrics are still placeholders; the next stage should connect the selected candidates to Isaac Gym headless validation.

## Current Limitations

- This report is symbolic-only; Isaac Gym metrics are not populated yet.
- Candidate BTs are controlled synthetic candidates, not yet LLM-generated candidates.
- Only tasks marked `v0_required` are included in the default report.

## Next Step

Connect the evaluator to the existing Isaac Gym headless pipeline so that `sim_success`, `final_position_error`, and `object_displacement_error` become real simulation-grounded metrics.
