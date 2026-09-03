from __future__ import annotations

import argparse
import copy
import csv
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

import yaml

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]
PROJECT_ROOT = REPO_ROOT.parent
BRIDGE_DIR = REPO_ROOT / "experiments" / "points2plans_bridge"
DEFAULT_EVALUATIONS = EXPERIMENT_DIR / "results" / "bt_candidate_evaluations.csv"
DEFAULT_DEMO_PICKLE = PROJECT_ROOT / "datasets" / "ll4ma_isaac_minimal" / "demo_000001.pickle"
DEFAULT_BASE_CONFIG = (
    PROJECT_ROOT
    / "ll4ma_isaac"
    / "ll4ma_isaacgym"
    / "src"
    / "ll4ma_isaacgym"
    / "config"
    / "cupboard.yaml"
)
DEFAULT_OUTPUT_DIR = EXPERIMENT_DIR / "simulation_jobs"
DEFAULT_DATA_ROOT = PROJECT_ROOT / "datasets" / "bt_selection_benchmark"
LL4MA_SCRIPT_DIR = (
    PROJECT_ROOT
    / "ll4ma_isaac"
    / "ll4ma_isaacgym"
    / "src"
    / "ll4ma_isaacgym"
    / "scripts"
)

sys.path.insert(0, str(BRIDGE_DIR))

from kios_place_to_sudo_action import compute_pickplace_action  # noqa: E402
from pickle_to_kios_world import convert_demo  # noqa: E402

MANIFEST_COLUMNS = [
    "task_id",
    "initial_state_id",
    "initial_timestep",
    "candidate_id",
    "candidate_type",
    "symbolic_success",
    "action_moved_object",
    "action_support_object",
    "placement_strategy",
    "target_x",
    "target_y",
    "status",
    "skip_reason",
    "config_path",
    "config_dir",
    "data_root",
    "expected_pickle",
    "run_command",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def block_to_object_id(name: str) -> int:
    match = re.fullmatch(r"block_(\d+)", name or "")
    if match is None:
        raise ValueError(f"Expected a block_N object name, got {name!r}.")
    return int(match.group(1)) - 1


def fixed_range(value: float) -> list[float]:
    value = float(value)
    return [value, value]


def iter_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = [node]
    for child in node.get("children", []):
        nodes.extend(iter_nodes(child))
    return nodes


def extract_place_actions(bt: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    actions = []
    for node in iter_nodes(bt):
        if node.get("type_name") != "action":
            continue
        for effect in node.get("effects", []):
            if (
                effect.get("property_name") == "is_supported_by"
                and effect.get("status") is True
                and effect.get("property_value") is not None
            ):
                placement = node.get("metadata", {}).get("placement", {})
                actions.append((str(effect.get("object_name")), str(effect.get("property_value")), placement))
                break
    if not actions:
        raise ValueError("No place action effect `is_supported_by(moved, support)` found.")
    return actions


def extract_place_action(bt: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    return extract_place_actions(bt)[0]


def object_metadata(world: dict[str, Any], object_name: str) -> dict[str, Any]:
    for obj in world.get("objects", []):
        if obj.get("name") == object_name:
            return obj.get("metadata", {})
    raise ValueError(f"Object {object_name!r} not found in world.")


def placement_target_xy(world: dict[str, Any], support_object: str, placement: dict[str, Any]) -> tuple[float | None, float | None]:
    ratio = placement.get("target_xy_offset_ratio")
    if not ratio:
        return None, None
    metadata = object_metadata(world, support_object)
    position = metadata.get("position")
    extents = metadata.get("extents")
    if position is None or extents is None:
        raise ValueError(f"Support object {support_object!r} has no position/extents metadata.")
    return (
        float(position[0]) + float(ratio[0]) * float(extents[0]),
        float(position[1]) + float(ratio[1]) * float(extents[1]),
    )


def make_config(
    base_config: dict[str, Any],
    action_specs: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    resetobjects = dict(config.get("resetobjects", {}))
    resetobjects["total_steps"] = len(action_specs)
    reset_actions = {}
    for index, action in enumerate(action_specs, start=1):
        desired_position = action["desired_position"]
        reset_actions[f"step_{index}"] = {
            "obj_id": [block_to_object_id(action["moved_object"])],
            "skill_id": 0,
            "position_ranges": [
                fixed_range(desired_position[0]),
                fixed_range(desired_position[1]),
                fixed_range(desired_position[2]),
            ],
        }
    resetobjects["actions"] = reset_actions
    config["resetobjects"] = resetobjects
    config_metadata = dict(config.get("metadata", {}))
    config_metadata.update(metadata)
    config["metadata"] = config_metadata
    return config


def shell_quote(path: Path | str) -> str:
    return shlex.quote(str(path))


def make_run_command(config_path: Path, data_root: Path, n_demos: int, headless: bool) -> str:
    parts = [
        "python3",
        "run_isaacgym.py",
        "--config",
        config_path.name,
        "--config_dir",
        str(config_path.parent.resolve()),
        "--n_envs",
        "1",
        "--n_demos",
        str(n_demos),
        "--data_root",
        str(data_root.resolve()),
    ]
    if headless:
        parts.extend(["--headless", "--no_render_graphics"])
    return " ".join(shlex.quote(part) for part in parts)


def write_jobs_script(path: Path, commands: list[str]) -> None:
    lines = [
        "#!/usr/bin/env bash",
        "set -o pipefail",
        "deactivate 2>/dev/null || true",
        "source /opt/ros/noetic/setup.bash",
        "source /home/theshy/projects/mycode/ll4ma_catkin_ws/devel/setup.bash",
        f"cd {shell_quote(LL4MA_SCRIPT_DIR)}",
        f"TOTAL_JOBS={len(commands)}",
        'MAX_JOBS="${MAX_JOBS:-0}"',
        f'FAILED_JOBS_LOG="${{FAILED_JOBS_LOG:-{path.parent.resolve() / "failed_jobs.log"}}}"',
        'echo "[bt-selection] failed jobs will be logged to $FAILED_JOBS_LOG"',
        "run_count=0",
        "skip_count=0",
        "fail_count=0",
        "",
        "find_data_root() {",
        "  previous_arg=",
        '  for arg in "$@"; do',
        '    if [ "$previous_arg" = "--data_root" ]; then',
        '      echo "$arg"',
        "      return 0",
        "    fi",
        '    previous_arg="$arg"',
        "  done",
        "  return 1",
        "}",
        "",
        "run_job() {",
        '  data_root="$(find_data_root "$@" || true)"',
        '  if [ -n "$data_root" ] && [ -f "$data_root/demo_000001.pickle" ]; then',
        "    skip_count=$((skip_count + 1))",
        '    echo "[bt-selection] skipping completed job ${skip_count}: $data_root/demo_000001.pickle"',
        "    return 0",
        "  fi",
        "  run_count=$((run_count + 1))",
        '  if [ "$MAX_JOBS" -gt 0 ] && [ "$run_count" -gt "$MAX_JOBS" ]; then',
        '    echo "[bt-selection] reached MAX_JOBS=$MAX_JOBS new jobs, stopping."',
        "    exit 0",
        "  fi",
        '  echo "[bt-selection] running new job ${run_count}/${TOTAL_JOBS}: $*"',
        '  "$@"',
        '  status="$?"',
        '  if [ "$status" -eq 0 ] && [ -n "$data_root" ] && [ -f "$data_root/demo_000001.pickle" ]; then',
        "    return 0",
        "  fi",
        "  fail_count=$((fail_count + 1))",
        '  if [ "$status" -eq 0 ]; then',
        '    echo "[bt-selection] job finished but did not write demo_000001.pickle: $*" | tee -a "$FAILED_JOBS_LOG"',
        "  else",
        '    echo "[bt-selection] job failed with exit code $status: $*" | tee -a "$FAILED_JOBS_LOG"',
        "  fi",
        '  if [ -n "$data_root" ]; then',
        '    echo "$data_root" >> "$FAILED_JOBS_LOG"',
        "  fi",
        "  return 0",
        "}",
        "",
    ]
    lines.extend(f"run_job {command}" for command in commands)
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    path.chmod(0o755)


def prepare_jobs(args: argparse.Namespace) -> list[dict[str, Any]]:
    rows = read_csv(args.evaluations)
    world_cache: dict[int, dict[str, Any]] = {}
    with args.base_config.open("r", encoding="utf-8") as file:
        base_config = yaml.safe_load(file)

    manifest_rows = []
    run_commands = []

    for row in rows:
        task_id = row["task_id"]
        initial_state_id = row.get("initial_state_id", "state_000_t0")
        initial_timestep = int(float(row.get("initial_timestep") or args.timestep))
        candidate_id = row["candidate_id"]
        candidate_type = row["candidate_type"]
        bt_path = REPO_ROOT / row["bt_path"]
        job_dir = args.output_dir / initial_state_id / task_id / candidate_id
        config_path = job_dir / "cupboard_candidate.yaml"
        data_root = args.data_root / initial_state_id / task_id / candidate_id
        expected_pickle = data_root / "demo_000001.pickle"

        manifest = {
            "task_id": task_id,
            "initial_state_id": row.get("initial_state_id", ""),
            "initial_timestep": initial_timestep,
            "candidate_id": candidate_id,
            "candidate_type": candidate_type,
            "symbolic_success": row.get("symbolic_success", ""),
            "action_moved_object": "",
            "action_support_object": "",
            "placement_strategy": "",
            "target_x": "",
            "target_y": "",
            "status": "skipped",
            "skip_reason": "",
            "config_path": "",
            "config_dir": "",
            "data_root": "",
            "expected_pickle": "",
            "run_command": "",
        }

        try:
            bt = read_json(bt_path)
            if initial_timestep not in world_cache:
                world_cache[initial_timestep] = convert_demo(args.demo_pickle, initial_timestep)
            world = world_cache[initial_timestep]
            place_actions = extract_place_actions(bt)
            target_action = place_actions[-1]
            for candidate_action in reversed(place_actions):
                if candidate_action[0] == row.get("moved_object") and candidate_action[1] == row.get("support_object"):
                    target_action = candidate_action
                    break

            action_specs = []
            action_metadata = []
            for moved_object, support_object, placement in place_actions:
                block_to_object_id(moved_object)
                block_to_object_id(support_object)
                target_x, target_y = placement_target_xy(world, support_object, placement)
                action = compute_pickplace_action(
                    world=world,
                    moved_object=moved_object,
                    support_object=support_object,
                    ee_z_offset=args.ee_z_offset,
                    target_x=target_x,
                    target_y=target_y,
                )
                desired_position = action["geometry"]["desired_position"]
                action_specs.append({"moved_object": moved_object, "desired_position": desired_position})
                action_metadata.append({
                    "moved_object": moved_object,
                    "support_object": support_object,
                    "placement_strategy": placement.get("strategy", "center") if placement else "center",
                    "target_x": "" if target_x is None else round(float(target_x), 6),
                    "target_y": "" if target_y is None else round(float(target_y), 6),
                    "desired_position": [float(value) for value in desired_position],
                })

            moved_object, support_object, placement = target_action
            target_x, target_y = placement_target_xy(world, support_object, placement)
            manifest["action_moved_object"] = moved_object
            manifest["action_support_object"] = support_object
            manifest["placement_strategy"] = placement.get("strategy", "center") if placement else "center"
            manifest["target_x"] = "" if target_x is None else round(float(target_x), 6)
            manifest["target_y"] = "" if target_y is None else round(float(target_y), 6)
        except Exception as exc:
            manifest["skip_reason"] = f"{type(exc).__name__}: {exc}"
            manifest_rows.append(manifest)
            continue

        metadata = {
            "source": "bt_selection_benchmark",
            "task_id": task_id,
            "initial_timestep": initial_timestep,
            "candidate_id": candidate_id,
            "candidate_type": candidate_type,
            "symbolic_success": row.get("symbolic_success"),
            "bt_path": str(bt_path),
            "moved_object": moved_object,
            "support_object": support_object,
            "placement_strategy": manifest["placement_strategy"],
            "target_x": manifest["target_x"],
            "target_y": manifest["target_y"],
            "desired_position": action_metadata[-1]["desired_position"] if action_metadata else [],
            "action_sequence": action_metadata,
        }
        config = make_config(base_config, action_specs, metadata)
        job_dir.mkdir(parents=True, exist_ok=True)
        with config_path.open("w", encoding="utf-8") as file:
            yaml.safe_dump(config, file, sort_keys=False)

        run_command = make_run_command(config_path, data_root, args.n_demos, args.headless)
        run_commands.append(run_command)
        manifest.update(
            {
                "status": "ready",
                "skip_reason": "",
                "config_path": str(config_path),
                "config_dir": str(config_path.parent.resolve()),
                "data_root": str(data_root.resolve()),
                "expected_pickle": str(expected_pickle),
                "run_command": run_command,
            }
        )
        manifest_rows.append(manifest)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "simulation_jobs_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(manifest_rows)

    write_jobs_script(args.output_dir / "run_jobs.sh", run_commands)
    return manifest_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Isaac Gym simulation jobs for BT candidate evaluations.")
    parser.add_argument("--evaluations", type=Path, default=DEFAULT_EVALUATIONS)
    parser.add_argument("--demo-pickle", type=Path, default=DEFAULT_DEMO_PICKLE)
    parser.add_argument("--timestep", type=int, default=0)
    parser.add_argument("--base-config", type=Path, default=DEFAULT_BASE_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--ee-z-offset", type=float, default=0.10988)
    parser.add_argument("--n-demos", type=int, default=1)
    parser.add_argument("--gui", action="store_true", help="Generate GUI run commands instead of headless commands.")
    args = parser.parse_args()
    args.headless = not args.gui
    return args


def main() -> int:
    args = parse_args()
    manifest_rows = prepare_jobs(args)
    ready = sum(1 for row in manifest_rows if row["status"] == "ready")
    skipped = len(manifest_rows) - ready
    print(
        json.dumps(
            {
                "result": "success",
                "jobs": len(manifest_rows),
                "ready": ready,
                "skipped": skipped,
                "manifest": str(args.output_dir / "simulation_jobs_manifest.csv"),
                "run_script": str(args.output_dir / "run_jobs.sh"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
