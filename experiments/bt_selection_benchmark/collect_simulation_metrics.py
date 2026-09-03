from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]
PROJECT_ROOT = REPO_ROOT.parent
BRIDGE_DIR = REPO_ROOT / "experiments" / "points2plans_bridge"
DEFAULT_EVALUATIONS = EXPERIMENT_DIR / "results" / "bt_candidate_evaluations.csv"
DEFAULT_MANIFEST = EXPERIMENT_DIR / "simulation_jobs" / "simulation_jobs_manifest.csv"
DEFAULT_OUTPUT = EXPERIMENT_DIR / "results" / "bt_candidate_evaluations_with_sim.csv"
DEFAULT_DEMO_PICKLE = PROJECT_ROOT / "datasets" / "ll4ma_isaac_minimal" / "demo_000001.pickle"

sys.path.insert(0, str(BRIDGE_DIR))

from kios_place_to_sudo_action import compute_pickplace_action  # noqa: E402
from pickle_to_kios_world import convert_demo  # noqa: E402


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def as_float(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    if value in {"", None}:
        return default
    return float(value)


def as_int(row: dict[str, Any], key: str, default: int = 0) -> int:
    value = row.get(key, "")
    if value in {"", None}:
        return default
    return int(float(value))


def parse_predicate(text: str) -> dict[str, str]:
    match = re.fullmatch(r"\s*([A-Za-z_][A-Za-z0-9_]*)\(([^,]+),\s*([^\)]+)\)\s*", text)
    if match is None:
        raise ValueError(f"Cannot parse predicate: {text!r}")
    return {
        "name": match.group(1).strip(),
        "source": match.group(2).strip(),
        "target": match.group(3).strip(),
    }


def world_has_predicate(world: dict[str, Any], predicate: dict[str, str]) -> bool:
    name = predicate["name"]
    aliases = {name}
    if name == "supported_by":
        aliases.add("is_supported_by")
    if name == "is_supported_by":
        aliases.add("supported_by")
    for relation in world.get("relations", []):
        if (
            relation.get("source") == predicate["source"]
            and relation.get("target") == predicate["target"]
            and relation.get("name") in aliases
        ):
            return True
    return False


def object_positions(world: dict[str, Any]) -> dict[str, list[float]]:
    positions = {}
    for obj in world.get("objects", []):
        position = obj.get("metadata", {}).get("position")
        if position is not None:
            positions[obj["name"]] = [float(value) for value in position]
    return positions


def distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def label_from_score(score: float) -> str:
    if score >= 120.0:
        return "good"
    if score >= 60.0:
        return "medium"
    return "bad"


def recompute_score(row: dict[str, Any]) -> float:
    sim_success = as_int(row, "sim_success", 0)
    symbolic_success = as_int(row, "symbolic_success", 0)
    goal_satisfaction = as_float(row, "goal_satisfaction", 0.0)
    final_position_error = as_float(row, "final_position_error", 1.0)
    object_displacement_error = as_float(row, "object_displacement_error", 0.0)
    action_count = as_float(row, "action_count", 0.0)
    tree_size = as_float(row, "tree_size", 0.0)
    precondition_coverage = as_float(row, "precondition_coverage", 1.0)
    return (
        100.0 * sim_success
        + 50.0 * symbolic_success
        + 20.0 * goal_satisfaction
        - 10.0 * final_position_error
        - 2.0 * object_displacement_error
        - 1.0 * action_count
        - 0.5 * tree_size
        - 20.0 * (1.0 - precondition_coverage)
    )


def key_for(row: dict[str, str]) -> tuple[str, str, str]:
    return row["task_id"], row["initial_state_id"], row["candidate_id"]


def collect_metrics(args: argparse.Namespace) -> list[dict[str, Any]]:
    rows = read_csv(args.evaluations)
    manifest_rows = {key_for(row): row for row in read_csv(args.manifest)}
    initial_world_cache: dict[int, dict[str, Any]] = {}

    updated = []
    for row in rows:
        out = dict(row)
        manifest = manifest_rows.get(key_for(row))
        if manifest is None:
            out["simulation_status"] = "missing_manifest"
            updated.append(out)
            continue
        expected_pickle = manifest.get("expected_pickle", "")
        initial_timestep = int(float(row.get("initial_timestep") or args.timestep))
        if initial_timestep not in initial_world_cache:
            initial_world_cache[initial_timestep] = convert_demo(args.demo_pickle, initial_timestep)
        initial_world = initial_world_cache[initial_timestep]
        initial_positions = object_positions(initial_world)
        if manifest.get("status") != "ready":
            out["simulation_status"] = "skipped"
            out["sim_success"] = "0"
            out["support_stability"] = "0"
            out["contact_violation_proxy"] = "1"
            out["score"] = round(recompute_score(out), 6)
            out["label"] = label_from_score(float(out["score"]))
            updated.append(out)
            continue
        if not expected_pickle or not Path(expected_pickle).exists():
            out["simulation_status"] = "pending"
            updated.append(out)
            continue

        final_world = convert_demo(Path(expected_pickle), args.final_timestep)
        final_positions = object_positions(final_world)
        predicate = parse_predicate(row["target_predicate"].split(";")[0])
        sim_success = world_has_predicate(final_world, predicate)

        try:
            action_moved_object = manifest.get("action_moved_object") or row["moved_object"]
            action_support_object = manifest.get("action_support_object") or row["support_object"]
            target_x = manifest.get("target_x", "")
            target_y = manifest.get("target_y", "")
            target_x_value = None if target_x in {"", None} else float(target_x)
            target_y_value = None if target_y in {"", None} else float(target_y)
            target_action = compute_pickplace_action(
                world=initial_world,
                moved_object=action_moved_object,
                support_object=action_support_object,
                ee_z_offset=args.ee_z_offset,
                target_x=target_x_value,
                target_y=target_y_value,
            )
            desired_position = target_action["geometry"]["desired_position"]
            final_position = final_positions[action_moved_object]
            final_position_error = distance(final_position, desired_position)
        except Exception:
            final_position_error = 1.0

        unrelated_displacements = []
        moved_object = row["moved_object"]
        for name, start in initial_positions.items():
            if name == moved_object or name not in final_positions:
                continue
            if not name.startswith("block_"):
                continue
            unrelated_displacements.append(distance(start, final_positions[name]))
        object_displacement_error = max(unrelated_displacements) if unrelated_displacements else 0.0
        contact_violation_proxy = 1.0 if object_displacement_error > args.displacement_threshold else 0.0

        out["simulation_status"] = "done"
        out["sim_success"] = int(bool(sim_success))
        out["final_position_error"] = round(final_position_error, 6)
        out["object_displacement_error"] = round(object_displacement_error, 6)
        out["support_stability"] = int(bool(sim_success))
        out["contact_violation_proxy"] = int(bool(contact_violation_proxy))
        out["score"] = round(recompute_score(out), 6)
        out["label"] = label_from_score(float(out["score"]))
        updated.append(out)
    return updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Isaac Gym metrics for prepared BT candidate simulation jobs.")
    parser.add_argument("--evaluations", type=Path, default=DEFAULT_EVALUATIONS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--demo-pickle", type=Path, default=DEFAULT_DEMO_PICKLE)
    parser.add_argument("--timestep", type=int, default=0)
    parser.add_argument("--final-timestep", type=int, default=999999, help="Large default is clamped to final pickle timestep.")
    parser.add_argument("--ee-z-offset", type=float, default=0.10988)
    parser.add_argument("--displacement-threshold", type=float, default=0.02)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = collect_metrics(args)
    columns = list(rows[0].keys()) if rows else []
    if "simulation_status" not in columns:
        columns.append("simulation_status")
    write_csv(args.output, rows, columns)
    counts = {}
    for row in rows:
        status = row.get("simulation_status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    print(
        json.dumps(
            {
                "result": "success",
                "output": str(args.output),
                "rows": len(rows),
                "simulation_status": counts,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())