# V2B Physical Strategy Analysis

## Completion

- Done simulation rows: 120
- Pending rows: 0

## Main Finding

- Symbolic selector mean regret: 5.272.
- Simulation-aware selector mean regret: 0.003.
- Regret reduction: 5.269.
- Simulation-aware selected sim success: 55.0%.

V2B is the first benchmark variant where all candidates are symbolically successful, but simulation-aware scoring nearly matches the oracle by selecting physically better placement strategies.

## Strategy Summary

| Candidate | N | Sim success | Mean score | Mean pos error | Mean displacement |
| --- | --- | --- | --- | --- | --- |
| center_place_bt | 20 | 50.0% | 114.383 | 0.0429 | 0.5938 |
| corner_place_bt | 20 | 50.0% | 114.375 | 0.0426 | 0.5995 |
| correct_bt | 20 | 50.0% | 114.397 | 0.0396 | 0.6039 |
| edge_place_bt | 20 | 50.0% | 114.350 | 0.0446 | 0.6018 |
| far_offset_bt | 20 | 0.0% | 62.131 | 0.2637 | 0.6162 |
| over_edge_bt | 20 | 5.0% | 67.467 | 0.2282 | 0.6254 |

## Oracle Preference

| Oracle candidate | Groups |
| --- | --- |
| center_place_bt | 6 |
| corner_place_bt | 4 |
| correct_bt | 3 |
| edge_place_bt | 4 |
| far_offset_bt | 2 |
| over_edge_bt | 1 |

## Task-Strategy Summary

| Task | Candidate | Sim success | Mean score |
| --- | --- | --- | --- |
| place_block1_on_block5 | center_place_bt | 100.0% | 164.867 |
| place_block1_on_block5 | corner_place_bt | 100.0% | 164.743 |
| place_block1_on_block5 | correct_bt | 100.0% | 164.772 |
| place_block1_on_block5 | edge_place_bt | 100.0% | 164.904 |
| place_block1_on_block5 | far_offset_bt | 0.0% | 60.956 |
| place_block1_on_block5 | over_edge_bt | 0.0% | 60.984 |
| place_block3_on_block5 | center_place_bt | 100.0% | 164.880 |
| place_block3_on_block5 | corner_place_bt | 100.0% | 164.672 |
| place_block3_on_block5 | correct_bt | 100.0% | 164.609 |
| place_block3_on_block5 | edge_place_bt | 100.0% | 164.695 |
| place_block3_on_block5 | far_offset_bt | 0.0% | 60.952 |
| place_block3_on_block5 | over_edge_bt | 0.0% | 60.977 |
| stack_block1_on_block3 | center_place_bt | 0.0% | 63.845 |
| stack_block1_on_block3 | corner_place_bt | 0.0% | 64.037 |
| stack_block1_on_block3 | correct_bt | 0.0% | 63.954 |
| stack_block1_on_block3 | edge_place_bt | 0.0% | 63.948 |
| stack_block1_on_block3 | far_offset_bt | 0.0% | 62.625 |
| stack_block1_on_block3 | over_edge_bt | 20.0% | 84.098 |
| stack_block3_on_block1 | center_place_bt | 0.0% | 63.940 |
| stack_block3_on_block1 | corner_place_bt | 0.0% | 64.047 |
| stack_block3_on_block1 | correct_bt | 0.0% | 64.252 |
| stack_block3_on_block1 | edge_place_bt | 0.0% | 63.856 |
| stack_block3_on_block1 | far_offset_bt | 0.0% | 63.991 |
| stack_block3_on_block1 | over_edge_bt | 0.0% | 63.809 |

## Paper Claim

Simulation-grounded metrics reduce selector regret when candidate BTs are symbolically indistinguishable but physically different.
