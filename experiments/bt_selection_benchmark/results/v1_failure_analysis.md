# V1 Failure Analysis

## Completion

- Done simulation rows: 100
- Skipped invalid rows: 20
- Pending rows: 0

## Main Finding

- `correct_bt` succeeds in simulation on 80.0% of cases.
- `correct_bt` is still the highest-scoring candidate in 100.0% of task-state groups.
- Alternative candidates beat `correct_bt` in 0 groups.

This means the V1 benchmark is complete and useful as an end-to-end validation, but it is not yet hard enough to separate symbolic and simulation-aware selection. The selector already chooses the oracle candidate on this task set.

## Candidate-Type Summary

| Candidate | Done | Symbolic success | Sim success | Mean score | Mean pos error | Mean displacement |
| --- | --- | --- | --- | --- | --- | --- |
| correct_bt | 20 | 100.0% | 80.0% | 144.642 | 0.0214 | 0.5723 |
| missing_precondition_bt | 20 | 100.0% | 75.0% | 130.098 | 0.0248 | 0.5768 |
| redundant_bt | 20 | 100.0% | 75.0% | 138.643 | 0.0211 | 0.5732 |
| unsafe_or_invalid_bt | 0 | 25.0% | N/A | -13.000 | N/A | N/A |
| wrong_object_bt | 20 | 25.0% | 0.0% | -13.972 | 0.6282 | 0.5953 |
| wrong_support_bt | 20 | 25.0% | 0.0% | -2.490 | 0.4841 | 0.5745 |

## Correct BT by Task

| Task | Done | Sim success | Mean score | Mean pos error | Mean displacement |
| --- | --- | --- | --- | --- | --- |
| place_block1_on_block5 | 5 | 100.0% | 164.718 | 0.0064 | 0.6094 |
| place_block2_on_block6 | 5 | 100.0% | 165.022 | 0.0038 | 0.4703 |
| place_block3_on_block5 | 5 | 100.0% | 164.810 | 0.0032 | 0.5787 |
| stack_block3_on_block1 | 5 | 20.0% | 84.017 | 0.0721 | 0.6307 |

## Failed Correct BT Cases

| Task | State | Target | Pos error | Displacement | Contact proxy | Score |
| --- | --- | --- | --- | --- | --- | --- |
| stack_block3_on_block1 | state_000_t0 | supported_by(block_3, block_1) | 0.079779 | 0.548682 | 1 | 64.104846 |
| stack_block3_on_block1 | state_002_t2 | supported_by(block_3, block_1) | 0.089849 | 0.620543 | 1 | 63.860424 |
| stack_block3_on_block1 | state_003_t3 | supported_by(block_3, block_1) | 0.092335 | 0.632041 | 1 | 63.812568 |
| stack_block3_on_block1 | state_004_t4 | supported_by(block_3, block_1) | 0.085926 | 0.614936 | 1 | 63.910868 |

## V2 Task Direction

- Add tasks where multiple BTs are symbolically valid but physically different.
- Prefer cluttered placement, stacked supports, constrained retrieval, and occluded-object cases.
- Make simulation metrics decisive: final position error, unrelated displacement, and contact violation should affect the oracle ranking.
- Keep the current V1 as the reproducible pipeline sanity benchmark.
