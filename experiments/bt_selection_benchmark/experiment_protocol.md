# BT Selection Benchmark Experiment Protocol

## 1. Research Question

Can symbolic behavior-tree execution traces and simulation-grounded feedback improve the selection of reliable behavior trees from multiple LLM-generated candidates for household robot task planning?

The project studies candidate selection rather than single-plan generation. Given a task, an initial world state, and several candidate behavior trees (BTs), the system should select the BT most likely to complete the task safely and efficiently.

## 2. Current Baseline

The current working baseline connects:

```text
LL4MA Isaac Gym pickle
  -> KIOS symbolic world
  -> KIOS BT execution trace
  -> Isaac Gym config
  -> headless simulation result
  -> HTML visualization
```

This baseline is currently a simulation-grounded object-placement baseline. It validates task-level object relations, but it does not yet execute full robot arm pick-and-place trajectories.

## 3. Stage 2A Goal

Stage 2A turns the current single-task demo into a benchmark for BT candidate evaluation.

The minimum viable benchmark should contain:

```text
5 tasks
x 5 initial states
x 5 BT candidates per task
= 125 evaluation samples
```

Each sample corresponds to:

```text
task_id + initial_state_id + candidate_bt_id + symbolic evaluation + simulation evaluation + metrics
```

## 4. Task Set V0

The first task set should use the LL4MA cupboard/block environment because it is already connected to the KIOS bridge.

Initial V0 tasks:

| task_id | Instruction | Target Predicate | Notes |
| --- | --- | --- | --- |
| place_block3_on_block5 | place block_3 on block_5 | supported_by(block_3, block_5) | Current working demo task |
| place_block1_on_block5 | place block_1 on block_5 | supported_by(block_1, block_5) | Same support, different movable object |
| place_block2_on_block6 | place block_2 on block_6 | supported_by(block_2, block_6) | Different shelf level |
| stack_block3_on_block1 | stack block_3 on block_1 | supported_by(block_3, block_1) | Movable-on-movable relation |
| move_block4_to_shelf_region | move block_4 to the shelf region | in_region(block_4, shelf_region) | Region goal, weaker than support relation |

The first implementation can support only the `supported_by` tasks, then add region goals once the evaluator is stable.

## 5. Candidate BT Types

Each task should have several candidate BTs. The first benchmark version uses controlled synthetic candidates, then later includes LLM-generated candidates.

| candidate_type | Expected Quality | Purpose |
| --- | --- | --- |
| correct_bt | Good | Should satisfy the target predicate |
| missing_precondition_bt | Medium/Bad | Omits an important condition check |
| wrong_object_bt | Bad | Moves or checks the wrong object |
| wrong_support_bt | Bad | Places the object on the wrong support |
| redundant_bt | Medium | Succeeds but contains unnecessary checks/actions |
| unsafe_or_invalid_bt | Bad | Contains invalid or physically risky action choices |

These candidates create the ranking problem: the selector must prefer reliable, efficient BTs over invalid or redundant ones.

## 6. Evaluation Layers

The benchmark evaluates each candidate BT at three levels.

### 6.1 Symbolic BT Evaluation

Computed from KIOS execution and the BT JSON structure.

| Metric | Type | Meaning |
| --- | --- | --- |
| symbolic_success | bool | KIOS final world satisfies the target predicate |
| goal_satisfaction | float | Fraction of target predicates satisfied |
| bt_ticks | int | Number of BT ticks before success/failure/timeout |
| action_count | int | Number of action nodes executed |
| condition_failure_count | int | Number of failed condition checks |
| invalid_action_count | int | Number of actions with missing/invalid preconditions |
| tree_size | int | Number of nodes in the candidate BT |
| tree_depth | int | Maximum depth of the BT |

### 6.2 Simulation Evaluation

Computed from Isaac Gym output pickle and converted KIOS world state.

| Metric | Type | Meaning |
| --- | --- | --- |
| sim_success | bool | Final simulation state satisfies the target relation |
| final_position_error | float | Distance between object final position and target position |
| object_displacement_error | float | Movement of unrelated objects |
| support_stability | float | Whether the placed object remains stable on the support |
| contact_violation_proxy | float | Proxy for unintended contact/collision |
| sim_steps | int | Number of simulation frames/steps recorded |

The first implementation can use `sim_success`, `final_position_error`, and `object_displacement_error`; more physical safety metrics can be added later.

### 6.3 Selection Evaluation

Computed after scoring/ranking candidates for the same task and initial state.

| Metric | Type | Meaning |
| --- | --- | --- |
| selected_success_rate | float | Success rate of the selector's top-1 chosen BT |
| oracle_success_rate | float | Success rate if the best available candidate is always chosen |
| random_success_rate | float | Expected success rate of random candidate selection |
| first_candidate_success_rate | float | Success rate of always selecting the first candidate |
| regret | float | Difference between oracle score and selected score |
| top_k_recall | float | Whether the oracle-best candidate appears in top-k |
| ranking_correlation | float | Correlation between predicted and true candidate rankings |

## 7. Initial Score Definition

For benchmark V0, define a simple scalar score for each candidate:

```text
score =
  100.0 * sim_success
+  50.0  * symbolic_success
+  20.0  * goal_satisfaction
-  10.0  * final_position_error
-   2.0  * object_displacement_error
-   1.0  * action_count
-   0.5  * tree_size
```

This score is a practical starting point, not a final theoretical claim. Later experiments should report individual metrics as well as the aggregate score.

## 8. Baselines

The benchmark should compare at least the following selectors:

| Selector | Description |
| --- | --- |
| random_selector | Randomly choose one candidate BT |
| first_candidate_selector | Choose the first generated candidate |
| shortest_tree_selector | Choose the candidate with the smallest tree_size |
| symbolic_success_selector | Prefer candidates that pass symbolic evaluation |
| rule_based_selector | Hand-coded weighted score using symbolic metrics |
| learned_selector | Train a model to predict success or score |
| oracle_selector | Choose the best candidate by true evaluation score; upper bound only |

## 9. Dataset Format

The main training/evaluation table should be:

```text
results/bt_candidate_evaluations.csv
```

One row equals one evaluated candidate under one task and initial state.

Required columns:

```text
task_id
initial_state_id
candidate_id
candidate_type
bt_path
task_instruction
target_predicate
moved_object
support_object
symbolic_success
sim_success
goal_satisfaction
bt_ticks
action_count
condition_failure_count
invalid_action_count
tree_size
tree_depth
final_position_error
object_displacement_error
support_stability
contact_violation_proxy
score
label
```

Labels can be derived from score:

```text
good: score >= 120
medium: 60 <= score < 120
bad: score < 60
```

These thresholds can be revised after seeing the first real evaluation results.

## 10. Model Training Plan

Stage 3 starts after enough rows exist in `bt_candidate_evaluations.csv`.

Recommended model progression:

1. Logistic regression on structured features.
2. Random forest or gradient-boosted trees on structured features.
3. MLP selector on numeric + categorical features.
4. Transformer BT encoder using preorder BT token sequences.
5. Multi-input selector combining task, world state, BT structure, and symbolic trace.

The first learned target should be either:

```text
sim_success
```

or:

```text
score
```

For candidate selection, ranking metrics are more important than raw classification accuracy.

## 11. Implementation Roadmap

### Step 1: Protocol and Specs

Create:

```text
experiment_protocol.md
task_specs.json
results/README.md
```

### Step 2: Candidate BT Library

Create one folder per task under:

```text
bt_candidates/<task_id>/
```

Each folder should contain candidate BT JSON files and a small manifest.

### Step 3: Symbolic Evaluator

Implement:

```text
evaluate_bt_candidates.py
```

The first version should run only KIOS symbolic evaluation and produce a CSV.

### Step 4: Isaac Gym Hook

Extend the evaluator to generate Isaac Gym configs, run headless simulation, and compute simulation metrics.

### Step 5: Selector Models

Implement rule-based and learned selectors under:

```text
models/
```

### Step 6: Paper Tables

Generate aggregate tables:

```text
results/summary_by_selector.csv
results/summary_by_task.csv
```

## 12. Paper Claim Supported by This Benchmark

The intended paper claim is:

```text
Simulation-grounded symbolic traces improve behavior-tree candidate selection for robot task planning compared with random, first-candidate, and simple rule-based selection baselines.
```

The benchmark should make this claim measurable and reproducible.
