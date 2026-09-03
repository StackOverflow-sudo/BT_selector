# BT Selection Benchmark

This experiment turns the current KIOS + LL4MA Isaac Gym bridge into a benchmark for behavior-tree candidate selection.

The goal is not only to run one BT, but to compare multiple candidate BTs for the same task and select the most reliable one.

## Files

- `experiment_protocol.md`: research question, metrics, baselines, dataset format, and roadmap.
- `task_specs.json`: first task set for the LL4MA cupboard/block environment.
- `evaluate_bt_candidates.py`: symbolic-only evaluator for Stage 2A V0.
- `bt_candidates/`: candidate BT JSON files, grouped by task.
- `results/`: generated CSV/JSON evaluation outputs.
- `models/`: future rule-based and learned selector models.

## Run Symbolic-Only Evaluation

Default evaluation runs only tasks marked `v0_required` in `task_specs.json`:

```bash
cd /home/theshy/projects/mycode/kios_baseline
source .venv-kios-demo/bin/activate

python experiments/bt_selection_benchmark/evaluate_bt_candidates.py
```

Expected output:

```text
experiments/bt_selection_benchmark/results/bt_candidate_evaluations.csv
```

The evaluator also creates candidate BT files under:

```text
experiments/bt_selection_benchmark/bt_candidates/<task_id>/
```

## Run All Tasks

Some tasks are marked `v1_after_v0` because they need extra goal/evaluator support. To include them anyway:

```bash
python experiments/bt_selection_benchmark/evaluate_bt_candidates.py \
  --include-all-tasks \
  --output experiments/bt_selection_benchmark/results/bt_candidate_evaluations_all_tasks.csv
```


## Prepare Isaac Gym Simulation Jobs

After symbolic evaluation, generate Isaac Gym configs and a runnable shell script:

```bash
python experiments/bt_selection_benchmark/prepare_simulation_jobs.py
```

This writes:

```text
experiments/bt_selection_benchmark/simulation_jobs/simulation_jobs_manifest.csv
experiments/bt_selection_benchmark/simulation_jobs/run_jobs.sh
```

The manifest marks invalid candidates as `skipped`. Ready jobs get their own config directory and data root.

## Run Prepared Simulations

Open a ROS/MoveIt terminal first and keep it running:

```bash
deactivate 2>/dev/null || true
source /opt/ros/noetic/setup.bash
source /home/theshy/projects/mycode/ll4ma_catkin_ws/devel/setup.bash
roslaunch moveit_interface iiwa_reflex_moveit_interface_service.launch
```

Then run the generated jobs from another WSL terminal:

```bash
deactivate 2>/dev/null || true
bash experiments/bt_selection_benchmark/simulation_jobs/run_jobs.sh
```

This may take several minutes because it runs one Isaac Gym job per ready candidate.

## Collect Simulation Metrics

After the jobs finish, update the evaluation table with simulation metrics:

```bash
cd /home/theshy/projects/mycode/kios_baseline
source .venv-kios-demo/bin/activate

python experiments/bt_selection_benchmark/collect_simulation_metrics.py
```

This writes:

```text
experiments/bt_selection_benchmark/results/bt_candidate_evaluations_with_sim.csv
```

Rows whose pickle does not exist yet are marked `pending`; invalid candidates are marked `skipped`.

## V1 Supported-By Pipeline

For the current V1 task set with movable-on-movable stacking support, run:

```bash
cd /home/theshy/projects/mycode/kios_baseline
experiments/bt_selection_benchmark/run_v1_supported_by_pipeline.sh
```

This regenerates:

```text
experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v1_supported_by.csv
experiments/bt_selection_benchmark/simulation_jobs_v1_supported_by/simulation_jobs_manifest.csv
experiments/bt_selection_benchmark/simulation_jobs_v1_supported_by/run_jobs.sh
experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v1_supported_by_with_sim_pending.csv
```

Then start the MoveIt service in another terminal:

```bash
deactivate 2>/dev/null || true
source /opt/ros/noetic/setup.bash
source /home/theshy/projects/mycode/ll4ma_catkin_ws/devel/setup.bash
roslaunch moveit_interface iiwa_reflex_moveit_interface_service.launch
```

Run a short Isaac Gym smoke test:

```bash
cd /home/theshy/projects/mycode/kios_baseline
MAX_JOBS=3 bash experiments/bt_selection_benchmark/simulation_jobs_v1_supported_by/run_jobs.sh
```

The generated script skips jobs whose `demo_000001.pickle` already exists. `MAX_JOBS` limits newly executed unfinished jobs, not skipped completed jobs.

After simulation outputs are generated, collect metrics and regenerate selector summaries:

```bash
experiments/bt_selection_benchmark/summarize_v1_supported_by_with_sim.sh
```

The final simulation-aware report is:

```text
experiments/bt_selection_benchmark/results/rule_based_selector_report_v1_supported_by_with_sim.md
```

## Current Limitation

The V1 symbolic evaluator and Isaac Gym job generation are implemented. Rows remain marked as `pending` until the generated Isaac Gym jobs finish and write their output pickle files. After that, run `summarize_v1_supported_by_with_sim.sh` to populate `sim_success`, `final_position_error`, and `object_displacement_error`.

## Next Implementation Target

Add a selector summary script that compares:

- random selector
- first candidate selector
- shortest tree selector
- symbolic success selector
- oracle selector

Then connect the best candidates to the existing Isaac Gym headless pipeline.