# V2 Task Design

## Motivation

V1 supported_by is complete as an end-to-end benchmark:

- 100 simulation rows completed.
- 20 intentionally invalid rows skipped.
- `correct_bt` is the oracle candidate in every task-state group.

The main limitation is that V1 validates the pipeline but does not strongly separate symbolic and simulation-aware selection. The symbolic selector already chooses the oracle candidate, so simulation metrics improve scoring but not top-1 decisions.

## V1 Failure Signal

The useful failure signal is concentrated in movable-on-movable stacking:

| Task | Correct BT simulation success |
| --- | --- |
| place_block1_on_block5 | 5/5 |
| place_block2_on_block6 | 5/5 |
| place_block3_on_block5 | 5/5 |
| stack_block3_on_block1 | 1/5 |

This suggests that V2 should increase the number of stacking and constrained physical placement cases.

## V2A: Stacking Probe

`task_specs_v2_stacking_probe.json` is a low-risk extension that works with the current evaluator because it still uses `supported_by` goals.

It contains:

- 3 stable shelf-placement reference tasks.
- 5 movable-on-movable stacking probe tasks.
- 5 initial states per task.
- 6 candidate BTs per task.

Total:

```text
8 tasks x 5 initial states x 6 candidates = 240 rows
```

The purpose of V2A is to map which block-on-block relations are physically reliable in Isaac Gym.

## V2B: Selection-Separating Tasks

V2B should introduce candidate BTs where multiple candidates are symbolically valid but physically different.

Recommended candidate types:

| Candidate type | Intended behavior |
| --- | --- |
| stable_support_bt | Places the object on a physically stable support. |
| unstable_support_bt | Satisfies symbolic `supported_by`, but tends to fail in simulation. |
| clutter_disturbing_bt | Reaches the goal but displaces unrelated objects. |
| clearance_aware_bt | Adds extra motion/conditions to avoid nearby objects. |
| direct_retrieval_bt | Tries to retrieve an occluded target directly. |
| clear_then_retrieve_bt | Moves a blocker first, then retrieves the target. |

These candidates should make simulation metrics decisive:

- `sim_success`
- `final_position_error`
- `object_displacement_error`
- `contact_violation_proxy`

## Recommended Next Implementation

1. Run V2A symbolic evaluation.
2. Prepare V2A simulation jobs.
3. Run a small V2A Isaac Gym smoke test.
4. Use V2A results to identify stable and unstable block-on-block pairs.
5. Implement V2B candidate types that deliberately compare stable vs unstable physical strategies.

V1 should remain the reproducible sanity benchmark. V2A is the physical probe. V2B is the benchmark that should support the final claim about simulation-aware BT selection.
