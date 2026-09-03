from __future__ import annotations

import argparse
import csv
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]
BRIDGE_DIR = REPO_ROOT / "experiments" / "points2plans_bridge"
DEFAULT_TASK_SPECS = EXPERIMENT_DIR / "task_specs.json"
DEFAULT_OUTPUT = EXPERIMENT_DIR / "results" / "bt_candidate_evaluations.csv"
DEFAULT_DEMO_PICKLE = REPO_ROOT.parent / "datasets" / "ll4ma_isaac_minimal" / "demo_000001.pickle"

sys.path.insert(0, str(BRIDGE_DIR))

from generate_visual_demo import (  # noqa: E402
    apply_symbolic_effects,
    flatten_bt,
    load_kios_runtime,
)
from pickle_to_kios_world import convert_demo  # noqa: E402


SUPPORTED_CANDIDATE_TYPES = [
    "correct_bt",
    "missing_precondition_bt",
    "wrong_object_bt",
    "wrong_support_bt",
    "redundant_bt",
    "unsafe_or_invalid_bt",
    "center_place_bt",
    "edge_place_bt",
    "corner_place_bt",
    "over_edge_bt",
    "far_offset_bt",
    "stable_center_bt",
    "symbolic_edge_bt",
    "symbolic_corner_bt",
    "unstable_over_edge_bt",
    "collision_far_offset_bt",
    "narrow_edge_bt",
    "collision_risk_bt",
    "correct_order_bt",
    "wrong_order_bt",
    "missing_clear_bt",
    "redundant_repair_bt",
]

CSV_COLUMNS = [
    "task_id",
    "initial_state_id",
    "initial_timestep",
    "candidate_id",
    "candidate_type",
    "bt_path",
    "task_instruction",
    "target_predicate",
    "moved_object",
    "support_object",
    "symbolic_success",
    "sim_success",
    "goal_satisfaction",
    "bt_ticks",
    "action_count",
    "condition_failure_count",
    "invalid_action_count",
    "tree_size",
    "tree_depth",
    "precondition_coverage",
    "final_position_error",
    "object_displacement_error",
    "support_stability",
    "contact_violation_proxy",
    "score",
    "label",
    "execution_result",
    "validation_error_count",
    "runtime_mode",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def predicate_to_text(predicate: dict[str, Any]) -> str:
    return f"{predicate['name']}({predicate['source']}, {predicate['target']})"


def world_has_predicate(world: dict[str, Any], predicate: dict[str, Any]) -> bool:
    name = predicate.get("name")
    source = predicate.get("source")
    target = predicate.get("target")
    aliases = {name}
    if name == "supported_by":
        aliases.add("is_supported_by")
    if name == "is_supported_by":
        aliases.add("supported_by")

    for relation in world.get("relations", []):
        if (
            relation.get("source") == source
            and relation.get("target") == target
            and relation.get("name") in aliases
        ):
            return True

    if target is None:
        for obj in world.get("objects", []):
            if obj.get("name") == source and name in obj.get("properties", []):
                return True
    return False


def goal_satisfaction(world: dict[str, Any], predicates: list[dict[str, Any]]) -> float:
    if not predicates:
        return 0.0
    hits = sum(1 for predicate in predicates if world_has_predicate(world, predicate))
    return hits / len(predicates)


def next_identifier() -> Any:
    counter = {"value": 0}

    def allocate() -> int:
        counter["value"] += 1
        return counter["value"]

    return allocate


def condition_node(identifier: int, summary: str, obj: str, prop: str, value: str | None = None) -> dict[str, Any]:
    if value is None:
        text = f"{prop}({obj})"
    else:
        text = f"{prop}({obj}, {value})"
    return {
        "summary": summary,
        "name": f"condition: {text}",
        "identifier": identifier,
        "type_name": "condition",
        "conditions": [
            {
                "object_name": obj,
                "property_name": prop,
                "property_value": value,
                "status": True,
            }
        ],
    }


def action_node(
    identifier: int,
    moved: str,
    support: str,
    summary_suffix: str = "",
    placement: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = f"place {moved} on {support}{summary_suffix}"
    node = {
        "summary": summary,
        "name": f"action: place({moved}, {support})",
        "identifier": identifier,
        "type_name": "action",
        "effects": [
            {
                "object_name": moved,
                "property_name": "is_free",
                "property_value": None,
                "status": False,
            },
            {
                "object_name": moved,
                "property_name": "is_supported_by",
                "property_value": support,
                "status": True,
            },
            {
                "object_name": moved,
                "property_name": "is_above",
                "property_value": support,
                "status": True,
            },
        ],
    }
    if placement:
        node["metadata"] = {"placement": placement}
    return node


def plan_steps_for_candidate(task: dict[str, Any], candidate_type: str) -> list[dict[str, Any]]:
    steps = deepcopy(task.get("plan_steps") or [])
    if not steps:
        return []

    if candidate_type == "wrong_order_bt":
        steps = list(reversed(steps))
    elif candidate_type == "missing_clear_bt" and len(steps) > 1:
        steps = steps[1:]
    elif candidate_type == "redundant_repair_bt":
        steps = steps + [deepcopy(steps[-1])]
    elif candidate_type == "wrong_support_bt":
        steps[-1] = deepcopy(steps[-1])
        support = steps[-1].get("support_object")
        steps[-1]["support_object"] = "block_6" if support != "block_6" else "block_5"
    elif candidate_type == "unsafe_or_invalid_bt":
        steps[-1] = deepcopy(steps[-1])
        steps[-1]["support_object"] = "missing_support"
    return steps


def make_plan_bt(task: dict[str, Any], candidate_type: str) -> dict[str, Any]:
    allocate = next_identifier()
    steps = plan_steps_for_candidate(task, candidate_type)
    if not steps:
        raise ValueError(f"Task {task['task_id']} does not define plan_steps for {candidate_type}.")

    sequence_children = []
    for step in steps:
        moved = step["moved_object"]
        support = step["support_object"]
        if candidate_type != "missing_clear_bt":
            sequence_children.append(condition_node(allocate(), f"{moved} precondition is_movable", moved, "is_movable"))
            sequence_children.append(condition_node(allocate(), f"{moved} precondition can_be_placed_on", moved, "can_be_placed_on", support))
        sequence_children.append(action_node(allocate(), moved, support, placement=step.get("placement")))

    target = task["target_predicates"][0]
    target_prop = "is_supported_by" if target["name"] == "supported_by" else target["name"]
    return {
        "summary": f"{candidate_type}: {task['instruction']}",
        "name": f"selector: {candidate_type} for {task['task_id']}",
        "identifier": allocate(),
        "type_name": "selector",
        "children": [
            condition_node(allocate(), "target is already satisfied", target["source"], target_prop, target["target"]),
            {
                "summary": f"multi-step sequence for {task['task_id']}",
                "name": f"sequence: {candidate_type} for {task['task_id']}",
                "identifier": allocate(),
                "type_name": "sequence",
                "children": sequence_children,
            },
        ],
    }


def make_bt(task: dict[str, Any], candidate_type: str) -> dict[str, Any]:
    if candidate_type in {
        "correct_order_bt",
        "wrong_order_bt",
        "missing_clear_bt",
        "redundant_repair_bt",
    } and task.get("plan_steps"):
        return make_plan_bt(task, candidate_type)

    moved = task["moved_object"]
    support = task.get("support_object") or "shelf_region"
    allocate = next_identifier()

    action_moved = moved
    action_support = support
    preconditions = ["is_movable", "can_be_placed_on"]
    duplicate_checks = 0
    include_target_check = True
    placement: dict[str, Any] | None = None

    if candidate_type == "missing_precondition_bt":
        preconditions = ["is_movable"]
    elif candidate_type == "wrong_object_bt":
        action_moved = "block_1" if moved != "block_1" else "block_2"
    elif candidate_type == "wrong_support_bt":
        action_support = "block_6" if support != "block_6" else "block_5"
    elif candidate_type == "redundant_bt":
        duplicate_checks = 2
    elif candidate_type == "unsafe_or_invalid_bt":
        action_moved = moved
        action_support = "missing_support"
        preconditions = ["can_be_placed_on"]
        include_target_check = False
    elif candidate_type == "center_place_bt":
        placement = {"strategy": "center", "target_xy_offset_ratio": [0.0, 0.0]}
    elif candidate_type == "stable_center_bt":
        placement = {"strategy": "stable_center", "target_xy_offset_ratio": [0.0, 0.0]}
    elif candidate_type == "edge_place_bt":
        placement = {"strategy": "edge_x", "target_xy_offset_ratio": [0.35, 0.0]}
    elif candidate_type == "symbolic_edge_bt":
        placement = {"strategy": "symbolic_edge_x", "target_xy_offset_ratio": [0.42, 0.0]}
    elif candidate_type == "corner_place_bt":
        placement = {"strategy": "corner_xy", "target_xy_offset_ratio": [0.32, 0.32]}
    elif candidate_type == "symbolic_corner_bt":
        placement = {"strategy": "symbolic_corner_xy", "target_xy_offset_ratio": [0.38, 0.38]}
    elif candidate_type == "narrow_edge_bt":
        placement = {"strategy": "narrow_edge_y", "target_xy_offset_ratio": [0.0, 0.48]}
    elif candidate_type == "collision_risk_bt":
        placement = {"strategy": "collision_risk_xy", "target_xy_offset_ratio": [-0.48, 0.35]}
    elif candidate_type == "over_edge_bt":
        placement = {"strategy": "over_edge_x", "target_xy_offset_ratio": [0.65, 0.0]}
    elif candidate_type == "unstable_over_edge_bt":
        placement = {"strategy": "unstable_over_edge_x", "target_xy_offset_ratio": [0.68, 0.0]}
    elif candidate_type == "far_offset_bt":
        placement = {"strategy": "far_offset_xy", "target_xy_offset_ratio": [0.85, 0.85]}
    elif candidate_type == "collision_far_offset_bt":
        placement = {"strategy": "collision_far_offset_xy", "target_xy_offset_ratio": [0.9, -0.9]}

    target_source = task["target_predicates"][0]["source"]
    target_name = task["target_predicates"][0]["name"]
    target_prop = "is_supported_by" if target_name == "supported_by" else target_name
    target_value = task["target_predicates"][0]["target"]

    sequence_children = []
    for prop in preconditions:
        value = action_support if prop == "can_be_placed_on" else None
        sequence_children.append(
            condition_node(
                allocate(),
                f"{action_moved} precondition {prop}",
                action_moved,
                prop,
                value,
            )
        )
    for idx in range(duplicate_checks):
        sequence_children.append(
            condition_node(
                allocate(),
                f"redundant check {idx + 1}: {action_moved} is movable",
                action_moved,
                "is_movable",
                None,
            )
        )
    sequence_children.append(action_node(allocate(), action_moved, action_support, placement=placement))

    children = []
    if include_target_check:
        children.append(
            condition_node(
                allocate(),
                "target is already satisfied",
                target_source,
                target_prop,
                target_value,
            )
        )
    children.append(
        {
            "summary": f"place sequence for {action_moved} on {action_support}",
            "name": f"sequence: place({action_moved}, {action_support})",
            "identifier": allocate(),
            "type_name": "sequence",
            "children": sequence_children,
        }
    )

    return {
        "summary": f"{candidate_type}: {task['instruction']}",
        "name": f"selector: {candidate_type} for {task['task_id']}",
        "identifier": allocate(),
        "type_name": "selector",
        "children": children,
    }


def ensure_candidate_library(task_specs: dict[str, Any], candidate_root: Path) -> list[dict[str, Any]]:
    candidates = []
    for task in task_specs.get("tasks", []):
        candidate_types = task.get("candidate_types") or task_specs.get("candidate_types") or SUPPORTED_CANDIDATE_TYPES
        task_dir = candidate_root / task["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "task_id": task["task_id"],
            "candidates": [],
        }
        for candidate_type in candidate_types:
            if candidate_type not in SUPPORTED_CANDIDATE_TYPES:
                continue
            bt_path = task_dir / f"{candidate_type}.json"
            if not bt_path.exists():
                write_json(bt_path, make_bt(task, candidate_type))
            entry = {
                "task": task,
                "candidate_id": candidate_type,
                "candidate_type": candidate_type,
                "bt_path": bt_path,
            }
            candidates.append(entry)
            manifest["candidates"].append(
                {
                    "candidate_id": candidate_type,
                    "candidate_type": candidate_type,
                    "bt_path": bt_path.name,
                }
            )
        write_json(task_dir / "manifest.json", manifest)
    return candidates


def iter_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = [node]
    for child in node.get("children", []):
        nodes.extend(iter_nodes(child))
    return nodes


def tree_depth(node: dict[str, Any]) -> int:
    children = node.get("children", [])
    if not children:
        return 1
    return 1 + max(tree_depth(child) for child in children)


def count_condition_failures(tick_trace: list[dict[str, Any]]) -> int:
    count = 0
    for tick in tick_trace:
        for node in tick.get("tree_nodes", []):
            if node.get("type_name") == "condition" and node.get("status") == "failure":
                count += 1
    return count


def count_actions_in_tick_trace(tick_trace: list[dict[str, Any]]) -> int:
    count = 0
    seen = set()
    for tick in tick_trace:
        for node in tick.get("tree_nodes", []):
            if node.get("type_name") != "action" or node.get("status") != "success":
                continue
            key = (tick.get("tick"), node.get("name"))
            if key not in seen:
                seen.add(key)
                count += 1
    return count


def count_invalid_actions(bt: dict[str, Any], world: dict[str, Any]) -> int:
    object_names = {obj.get("name") for obj in world.get("objects", [])}
    invalid = 0
    for node in iter_nodes(bt):
        if node.get("type_name") != "action":
            continue
        for effect in node.get("effects", []):
            if effect.get("object_name") not in object_names:
                invalid += 1
            target = effect.get("property_value")
            if isinstance(target, str) and target not in object_names and target != "shelf_region":
                invalid += 1
    return invalid


def precondition_coverage(bt: dict[str, Any], task: dict[str, Any]) -> float:
    moved = task.get("moved_object")
    support = task.get("support_object")
    if not moved or not support:
        return 1.0

    expected = {
        (moved, "is_movable", None),
        (moved, "can_be_placed_on", support),
    }
    observed = set()
    for node in iter_nodes(bt):
        if node.get("type_name") != "condition":
            continue
        for condition in node.get("conditions", []):
            observed.add(
                (
                    condition.get("object_name"),
                    condition.get("property_name"),
                    condition.get("property_value"),
                )
            )
    return len(expected & observed) / len(expected)


def execute_symbolic(world: dict[str, Any], bt: dict[str, Any], max_ticks: int) -> tuple[dict[str, Any], list[str], str, str | None]:
    validate_baseline, run_minimal_baseline, runtime_error = load_kios_runtime()
    if validate_baseline is not None and run_minimal_baseline is not None:
        validation_errors = validate_baseline.validate(world, bt)
        if validation_errors:
            return {"result": "invalid", "ticks": 0, "world_state": world, "tick_trace": []}, validation_errors, "kios_dummy_executor", runtime_error
        execution = run_minimal_baseline.run(world_state=world, behavior_tree=bt, max_ticks=max_ticks)
        return execution, [], "kios_dummy_executor", runtime_error

    final_world = apply_symbolic_effects(world, bt)
    execution = {
        "result": "success",
        "ticks": 1,
        "world_state": final_world,
        "tick_trace": [],
    }
    return execution, [], "fallback_symbolic_effects", runtime_error


def label_from_score(score: float) -> str:
    if score >= 120.0:
        return "good"
    if score >= 60.0:
        return "medium"
    return "bad"


def evaluate_candidate(
    entry: dict[str, Any],
    base_world: dict[str, Any],
    max_ticks: int,
    initial_state_id: str,
    initial_timestep: int,
) -> dict[str, Any]:
    task = entry["task"]
    bt_path = entry["bt_path"]
    bt = read_json(bt_path)
    world = deepcopy(base_world)
    execution, validation_errors, runtime_mode, _runtime_error = execute_symbolic(world, bt, max_ticks)
    final_world = execution.get("world_state", world)
    predicates = task.get("target_predicates", [])
    satisfaction = goal_satisfaction(final_world, predicates)
    symbolic_success = satisfaction >= 1.0 and execution.get("result") == "success"

    flat_nodes = flatten_bt(bt)
    nodes = iter_nodes(bt)
    tick_trace = execution.get("tick_trace", []) or []
    action_count = count_actions_in_tick_trace(tick_trace)
    if action_count == 0 and execution.get("result") == "success":
        action_count = sum(1 for node in nodes if node.get("type_name") == "action")

    condition_failure_count = count_condition_failures(tick_trace)
    invalid_action_count = count_invalid_actions(bt, world)
    tree_size = len(flat_nodes)
    depth = tree_depth(bt)
    coverage = precondition_coverage(bt, task)

    sim_success = ""
    final_position_error = 0.0 if symbolic_success else 1.0
    object_displacement_error = 0.0
    support_stability = ""
    contact_violation_proxy = ""

    score = (
        100.0 * 0.0
        + 50.0 * float(symbolic_success)
        + 20.0 * satisfaction
        - 10.0 * final_position_error
        - 2.0 * object_displacement_error
        - 1.0 * action_count
        - 0.5 * tree_size
        - 20.0 * (1.0 - coverage)
    )

    return {
        "task_id": task["task_id"],
        "initial_state_id": initial_state_id,
        "initial_timestep": initial_timestep,
        "candidate_id": entry["candidate_id"],
        "candidate_type": entry["candidate_type"],
        "bt_path": str(bt_path.relative_to(REPO_ROOT)),
        "task_instruction": task["instruction"],
        "target_predicate": ";".join(predicate_to_text(p) for p in predicates),
        "moved_object": task.get("moved_object", ""),
        "support_object": task.get("support_object") or "",
        "symbolic_success": int(bool(symbolic_success)),
        "sim_success": sim_success,
        "goal_satisfaction": round(satisfaction, 6),
        "bt_ticks": execution.get("ticks", 0),
        "action_count": action_count,
        "condition_failure_count": condition_failure_count,
        "invalid_action_count": invalid_action_count,
        "tree_size": tree_size,
        "tree_depth": depth,
        "precondition_coverage": round(coverage, 6),
        "final_position_error": final_position_error,
        "object_displacement_error": object_displacement_error,
        "support_stability": support_stability,
        "contact_violation_proxy": contact_violation_proxy,
        "score": round(score, 6),
        "label": label_from_score(score),
        "execution_result": execution.get("result", "unknown"),
        "validation_error_count": len(validation_errors),
        "runtime_mode": runtime_mode,
    }


def make_initial_states(demo_pickle: Path, base_timestep: int, count: int) -> list[tuple[str, int, dict[str, Any]]]:
    if count < 1:
        raise ValueError("initial-state-count must be at least 1")
    probe_world = convert_demo(demo_pickle, base_timestep)
    timestep_count = int(probe_world.get("metadata", {}).get("timestep_count", 1))
    states = []
    for idx in range(count):
        timestep = min(base_timestep + idx, max(0, timestep_count - 1))
        state_id = f"state_{idx:03d}_t{timestep}"
        states.append((state_id, timestep, convert_demo(demo_pickle, timestep)))
    return states


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate BT candidates for the Stage 2A benchmark.")
    parser.add_argument("--task-specs", type=Path, default=DEFAULT_TASK_SPECS)
    parser.add_argument("--demo-pickle", type=Path, default=DEFAULT_DEMO_PICKLE)
    parser.add_argument("--timestep", type=int, default=0)
    parser.add_argument("--initial-state-count", type=int, default=1)
    parser.add_argument("--candidate-root", type=Path, default=EXPERIMENT_DIR / "bt_candidates")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-ticks", type=int, default=10)
    parser.add_argument(
        "--include-all-tasks",
        action="store_true",
        help="Evaluate v1/experimental tasks as well as v0_required tasks.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task_specs = read_json(args.task_specs)
    selected_tasks = task_specs.get("tasks", [])
    if not args.include_all_tasks:
        selected_tasks = [
            task for task in selected_tasks if task.get("priority") == "v0_required"
        ]
    task_specs = {**task_specs, "tasks": selected_tasks}

    candidates = ensure_candidate_library(task_specs, args.candidate_root)
    initial_states = make_initial_states(args.demo_pickle, args.timestep, args.initial_state_count)
    rows = []
    for initial_state_id, initial_timestep, base_world in initial_states:
        for entry in candidates:
            rows.append(
                evaluate_candidate(
                    entry,
                    base_world,
                    args.max_ticks,
                    initial_state_id,
                    initial_timestep,
                )
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "result": "success",
        "tasks": len(task_specs.get("tasks", [])),
        "initial_states": args.initial_state_count,
        "candidates": len(rows),
        "output": str(args.output),
        "symbolic_success_count": sum(int(row["symbolic_success"]) for row in rows),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())