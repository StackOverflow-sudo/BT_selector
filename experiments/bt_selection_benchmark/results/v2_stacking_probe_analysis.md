# V2 Stacking Probe Analysis

## Completion

- Done simulation rows: 200
- Skipped invalid rows: 40
- Pending rows: 0

## Main Finding

- Shelf-placement `correct_bt` simulation success: 100.0%.
- Movable-on-movable stacking `correct_bt` simulation success: 4.0%.
- Fully failing stacking tasks: 4/5.

V2A confirms the V1 failure signal: shelf placement is physically reliable, while block-on-block stacking is usually symbolically valid but physically unreliable in Isaac Gym.

## Task-Level Results

| Task | Class | Correct sim success | Correct mean score | Mean pos error | Mean displacement |
| --- | --- | --- | --- | --- | --- |
| place_block1_on_block5 | shelf_placement | 100.0% | 164.710 | 0.0060 | 0.6152 |
| place_block2_on_block6 | shelf_placement | 100.0% | 165.113 | 0.0030 | 0.4288 |
| place_block3_on_block5 | shelf_placement | 100.0% | 164.888 | 0.0031 | 0.5406 |
| stack_block1_on_block3 | stacking | 20.0% | 84.146 | 0.0657 | 0.5984 |
| stack_block2_on_block1 | stacking | 0.0% | 64.253 | 0.0733 | 0.5073 |
| stack_block3_on_block1 | stacking | 0.0% | 64.003 | 0.0678 | 0.6594 |
| stack_block3_on_block2 | stacking | 0.0% | 64.054 | 0.0783 | 0.5816 |
| stack_block4_on_block1 | stacking | 0.0% | 64.194 | 0.0726 | 0.5403 |

## Candidate-Type Results

| Candidate | Done | Symbolic success | Sim success | Mean score |
| --- | --- | --- | --- | --- |
| correct_bt | 40 | 100.0% | 40.0% | 104.420 |
| missing_precondition_bt | 40 | 100.0% | 37.5% | 92.335 |
| redundant_bt | 40 | 100.0% | 37.5% | 100.851 |
| unsafe_or_invalid_bt | 0 | 12.5% | N/A | -23.000 |
| wrong_object_bt | 40 | 12.5% | 0.0% | -21.832 |
| wrong_support_bt | 40 | 12.5% | 0.0% | -11.673 |

## Interpretation

- The current candidate library still makes `correct_bt` the oracle in every task-state group because alternatives are mostly wrong-object, wrong-support, redundant, or missing-precondition variants.
- Simulation metrics now expose task difficulty: stacking has low physical success even when symbolic execution succeeds.
- The next benchmark version should create competing BTs that are both symbolically valid but physically different, such as stable-support versus unstable-support strategies.

## Next Step

Implement V2B candidate types that intentionally compare physically stable and unstable symbolic strategies, then rerun selector comparison on those candidates.
