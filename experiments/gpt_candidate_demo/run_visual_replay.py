#!/usr/bin/env python3
"""Isaac Gym visual replay for the GPT BT selection demo.

This script is presentation-oriented: it replays the selected or oracle BT as
a smooth pick-and-place animation with a simple arm overlay. It does not replace
the LL4MA/Isaac Gym jobs used for scoring.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

from isaacgym import gymapi
from isaacgym import gymutil


HERE = Path(__file__).resolve().parent
DEFAULT_DATA = HERE / "frontend" / "demo_data.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Animated Isaac Gym replay for BT selector demos")
    parser.add_argument("--demo-data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--candidate", default="selected", help="selected, oracle, or a candidate_id")
    parser.add_argument("--frames", type=int, default=720)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--simple-arm", action="store_true", help="Use the lightweight line-and-joint arm overlay instead of the KUKA asset")
    return parser.parse_args()


def load_demo(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def choose_candidate(data: dict[str, Any], name: str) -> dict[str, Any]:
    candidates = data.get("candidates", [])
    summary = data.get("summary", {})
    if name == "selected":
        name = summary.get("selected_candidate") or data.get("task", {}).get("selected_candidate")
    elif name == "oracle":
        name = summary.get("oracle_candidate")
        if not name:
            raise SystemExit("Oracle is not available yet. Run the headless candidate jobs first.")
    for candidate in candidates:
        if candidate.get("candidate_id") == name:
            return candidate
    raise SystemExit(f"Candidate not found: {name}")


def task_objects(task: dict[str, Any]) -> tuple[str, str]:
    text = " ".join(str(task.get(k, "")) for k in ["task_id", "target_predicate", "instruction"])
    match = re.search(r"block[_ ]?(\d+).*block[_ ]?(\d+)", text)
    if match:
        return f"block_{match.group(1)}", f"block_{match.group(2)}"
    return "block_3", "block_5"


def placement_offset(candidate: dict[str, Any]) -> tuple[float, float]:
    strategy = str(candidate.get("placement_strategy", "")).lower()
    if "edge" in strategy:
        return 0.13, 0.09
    if "corner" in strategy:
        return 0.15, 0.15
    if "offset" in strategy:
        return 0.08, -0.08
    return 0.0, 0.0


def vec(x: float, y: float, z: float) -> gymapi.Vec3:
    return gymapi.Vec3(float(x), float(y), float(z))


def pose(x: float, y: float, z: float) -> gymapi.Transform:
    return gymapi.Transform(p=vec(x, y, z))


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def lerp(a: gymapi.Vec3, b: gymapi.Vec3, t: float) -> gymapi.Vec3:
    return vec(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, a.z + (b.z - a.z) * t)


def arc_path(start: gymapi.Vec3, end: gymapi.Vec3, progress: float) -> gymapi.Vec3:
    t = smoothstep(progress)
    p = lerp(start, end, t)
    p.y += math.sin(math.pi * t) * 0.28
    return p


def set_actor_pose(gym: gymapi.Gym, env: gymapi.Env, actor: int, p: gymapi.Vec3) -> None:
    states = gym.get_actor_rigid_body_states(env, actor, gymapi.STATE_NONE)
    states["pose"]["p"].fill((p.x, p.y, p.z))
    states["pose"]["r"].fill((0.0, 0.0, 0.0, 1.0))
    gym.set_actor_rigid_body_states(env, actor, states, gymapi.STATE_POS)


def add_actor(gym: gymapi.Gym, env: gymapi.Env, asset: gymapi.Asset, p: gymapi.Vec3, name: str, color: tuple[float, float, float]) -> int:
    handle = gym.create_actor(env, asset, gymapi.Transform(p=p), name, 0, 0)
    gym.set_rigid_body_color(env, handle, 0, gymapi.MESH_VISUAL_AND_COLLISION, vec(*color))
    return handle


def main() -> None:
    args = parse_args()
    data = load_demo(args.demo_data)
    task = data.get("task", {})
    selected = choose_candidate(data, args.candidate)
    moved_object, support_object = task_objects(task)
    dx, dz = placement_offset(selected)

    gym = gymapi.acquire_gym()
    sim_params = gymapi.SimParams()
    sim_params.dt = 1.0 / 60.0
    sim_params.substeps = 2
    sim_params.gravity = vec(0.0, -9.8, 0.0)
    sim_params.physx.solver_type = 1
    sim_params.physx.num_position_iterations = 4
    sim_params.physx.num_velocity_iterations = 1
    sim_params.use_gpu_pipeline = False
    sim = gym.create_sim(0, 0, gymapi.SIM_PHYSX, sim_params)
    if sim is None:
        raise SystemExit("Failed to create Isaac Gym sim")

    gym.add_ground(sim, gymapi.PlaneParams())
    viewer = gym.create_viewer(sim, gymapi.CameraProperties())
    if viewer is None:
        raise SystemExit("Failed to create Isaac Gym viewer")

    env = gym.create_env(sim, vec(-1.4, 0.0, -1.1), vec(1.4, 1.4, 1.1), 1)
    gym.viewer_camera_look_at(viewer, None, vec(1.65, 1.25, 1.65), vec(0.0, 0.35, 0.0))

    fixed = gymapi.AssetOptions()
    fixed.fix_base_link = True
    fixed.disable_gravity = True
    movable = gymapi.AssetOptions()
    movable.disable_gravity = True

    table_asset = gym.create_box(sim, 1.35, 0.06, 0.9, fixed)
    block_asset = gym.create_box(sim, 0.16, 0.16, 0.16, movable)
    marker_asset = gym.create_box(sim, 0.18, 0.008, 0.18, fixed)
    oracle_marker_asset = gym.create_box(sim, 0.21, 0.006, 0.21, fixed)
    joint_asset = gym.create_sphere(sim, 0.035, movable)
    gripper_palm_asset = gym.create_box(sim, 0.22, 0.025, 0.055, movable)
    gripper_finger_asset = gym.create_box(sim, 0.026, 0.12, 0.04, movable)

    robot_handle = None
    robot_num_dofs = 0
    robot_mid = None
    robot_amp = None
    robot_lower = None
    robot_upper = None
    robot_attractor_handle = None
    robot_attractor_body = None
    if not args.simple_arm:
        robot_options = gymapi.AssetOptions()
        robot_options.armature = 0.001
        robot_options.fix_base_link = True
        robot_options.thickness = 0.002
        robot_options.disable_gravity = True
        robot_options.mesh_normal_mode = gymapi.COMPUTE_PER_VERTEX
        asset_root = "/home/theshy/projects/mycode/isaacgym/assets"
        robot_file = "urdf/kuka_allegro_description/kuka_allegro.urdf"
        robot_asset = gym.load_asset(sim, asset_root, robot_file, robot_options)
        if robot_asset is not None:
            robot_pose = gymapi.Transform()
            robot_pose.p = vec(-0.68, 0.02, 0.34)
            robot_pose.r = gymapi.Quat(-0.707107, 0.0, 0.0, 0.707107)
            robot_handle = gym.create_actor(env, robot_asset, robot_pose, "kuka_allegro", 0, 1)
            dof_props = gym.get_actor_dof_properties(env, robot_handle)
            robot_num_dofs = len(dof_props)
            if robot_num_dofs:
                dof_props["driveMode"].fill(gymapi.DOF_MODE_NONE)
                dof_props["stiffness"].fill(0.0)
                dof_props["damping"].fill(80.0)
                if robot_num_dofs > 7:
                    dof_props["driveMode"][7:].fill(gymapi.DOF_MODE_POS)
                    dof_props["stiffness"][7:].fill(120.0)
                    dof_props["damping"][7:].fill(25.0)
                gym.set_actor_dof_properties(env, robot_handle, dof_props)
                lower = dof_props["lower"]
                upper = dof_props["upper"]
                robot_lower = lower
                robot_upper = upper
                robot_mid = 0.5 * (lower + upper)
                robot_amp = 0.18 * (upper - lower)
                robot_amp[robot_amp > 0.8] = 0.8
                robot_amp[robot_amp < 0.08] = 0.08
                dof_states = gym.get_actor_dof_states(env, robot_handle, gymapi.STATE_NONE)
                dof_states["pos"][:] = robot_mid
                gym.set_actor_dof_states(env, robot_handle, dof_states, gymapi.STATE_POS)
                gym.set_actor_dof_position_targets(env, robot_handle, robot_mid)

    table_y = 0.03
    block_y = 0.06 + 0.08
    support_top_y = 0.06 + 0.16
    start = vec(-0.45, block_y, -0.25)
    support = vec(0.24, block_y, 0.02)
    target = vec(support.x + dx, support_top_y + 0.08, support.z + dz)

    add_actor(gym, env, table_asset, vec(0.0, table_y, 0.0), "table", (0.50, 0.47, 0.40))
    add_actor(gym, env, block_asset, support, support_object, (0.20, 0.42, 0.92))
    moved_handle = add_actor(gym, env, block_asset, start, moved_object, (0.96, 0.45, 0.20))
    gripper_palm_handle = add_actor(gym, env, gripper_palm_asset, vec(start.x, start.y + 0.17, start.z), "visual_gripper_palm", (0.10, 0.12, 0.16))
    gripper_left_handle = add_actor(gym, env, gripper_finger_asset, vec(start.x - 0.075, start.y + 0.08, start.z), "visual_gripper_left", (0.95, 0.72, 0.18))
    gripper_right_handle = add_actor(gym, env, gripper_finger_asset, vec(start.x + 0.075, start.y + 0.08, start.z), "visual_gripper_right", (0.95, 0.72, 0.18))
    candidates = data.get("candidates", [])
    selected_id = selected.get("candidate_id")
    oracle_id = data.get("summary", {}).get("oracle_candidate")

    if oracle_id:
        oracle_candidate = next(
            (candidate for candidate in candidates if candidate.get("candidate_id") == oracle_id),
            None,
        )
        if oracle_candidate is not None:
            oracle_dx, oracle_dz = placement_offset(oracle_candidate)
            add_actor(
                gym,
                env,
                oracle_marker_asset,
                vec(support.x + oracle_dx, support_top_y + 0.003, support.z + oracle_dz),
                "oracle_target",
                (0.95, 0.75, 0.18),
            )

    add_actor(
        gym,
        env,
        marker_asset,
        vec(target.x, support_top_y + 0.008, target.z),
        "selected_target",
        (0.20, 0.75, 0.32),
    )

    for index, candidate in enumerate(candidates[:8]):
        candidate_id = candidate.get("candidate_id")
        if candidate_id in {selected_id, oracle_id}:
            continue
        cdx, cdz = placement_offset(candidate)
        color = (0.75, 0.76, 0.78)
        jitter = (index - min(len(candidates), 8) / 2.0) * 0.012
        add_actor(
            gym,
            env,
            marker_asset,
            vec(support.x + cdx + jitter, support_top_y + 0.012, support.z + cdz - jitter),
            f"candidate_marker_{index}",
            color,
        )

    base = vec(-0.82, 0.10, 0.42)
    shoulder = vec(-0.62, 0.64, 0.30)
    elbow_handle = None
    wrist_handle = None
    if robot_handle is not None:
        body_dict = gym.get_actor_rigid_body_dict(env, robot_handle)
        for body_name in ["palm_link", "iiwa7_link_7", "index_link_3"]:
            if body_name in body_dict:
                robot_attractor_body = body_name
                break
        if robot_attractor_body:
            attractor = gymapi.AttractorProperties()
            attractor.stiffness = 2.5e6
            attractor.damping = 1.2e4
            attractor.axes = gymapi.AXIS_TRANSLATION
            attractor.rigid_handle = gym.find_actor_rigid_body_handle(env, robot_handle, robot_attractor_body)
            attractor.target = gymapi.Transform(p=vec(start.x, start.y + 0.17, start.z))
            robot_attractor_handle = gym.create_rigid_body_attractor(env, attractor)
    else:
        elbow_handle = add_actor(gym, env, joint_asset, shoulder, "arm_elbow", (0.08, 0.45, 0.80))
        wrist_handle = add_actor(gym, env, joint_asset, vec(start.x, start.y + 0.18, start.z), "arm_wrist", (0.08, 0.45, 0.80))

    print(json.dumps({
        "visual_replay": "started",
        "candidate": selected.get("candidate_id"),
        "task": task.get("task_id"),
        "moved_object": moved_object,
        "support_object": support_object,
        "placement_strategy": selected.get("placement_strategy"),
        "robot_visual": "kuka_allegro_attractor" if robot_attractor_handle is not None else "kuka_allegro" if robot_handle is not None else "simple_overlay",
        "robot_attractor_body": robot_attractor_body,
        "note": "This is a presentation replay. Metrics still come from the LL4MA/Isaac Gym jobs.",
    }, indent=2))

    frame = 0
    while not gym.query_viewer_has_closed(viewer):
        if args.loop:
            local_frame = frame % max(args.frames, 1)
        else:
            local_frame = min(frame, max(args.frames - 1, 1))
        progress = local_frame / max(args.frames - 1, 1)
        block_pos = arc_path(start, target, progress)
        set_actor_pose(gym, env, moved_handle, block_pos)

        wrist = vec(block_pos.x, block_pos.y + 0.18, block_pos.z)
        elbow = vec((shoulder.x + wrist.x) * 0.5 - 0.08, max(shoulder.y, wrist.y) + 0.22, (shoulder.z + wrist.z) * 0.5)
        grip_close = smoothstep(progress / 0.14) * (1.0 - smoothstep((progress - 0.86) / 0.12))
        grip_gap = 0.155 - 0.045 * grip_close
        palm = vec(block_pos.x, block_pos.y + 0.17, block_pos.z)
        set_actor_pose(gym, env, gripper_palm_handle, palm)
        set_actor_pose(gym, env, gripper_left_handle, vec(block_pos.x - grip_gap * 0.5, block_pos.y + 0.075, block_pos.z))
        set_actor_pose(gym, env, gripper_right_handle, vec(block_pos.x + grip_gap * 0.5, block_pos.y + 0.075, block_pos.z))

        if robot_attractor_handle is not None:
            attractor = gym.get_attractor_properties(env, robot_attractor_handle)
            attractor.target = gymapi.Transform(p=palm)
            gym.set_attractor_target(env, robot_attractor_handle, attractor.target)
            if robot_num_dofs and robot_mid is not None and robot_lower is not None and robot_upper is not None:
                targets = robot_mid.copy()
                if robot_num_dofs > 7:
                    finger_value = 0.35 * (1.0 - grip_close)
                    for j in range(7, robot_num_dofs):
                        targets[j] = robot_mid[j] + finger_value * 0.08
                targets = targets.clip(robot_lower, robot_upper)
                gym.set_actor_dof_position_targets(env, robot_handle, targets)
        elif robot_handle is not None and robot_num_dofs and robot_mid is not None and robot_lower is not None and robot_upper is not None:
            phase = smoothstep(progress)
            targets = robot_mid.copy()
            if robot_num_dofs >= 7:
                targets[0] = robot_mid[0] + 0.16 * math.sin(phase * math.pi)
                targets[1] = robot_mid[1] - 0.25
                targets[2] = robot_mid[2] + 0.10 * math.sin(phase * math.pi)
                targets[3] = robot_mid[3] + 0.20 * math.sin(phase * math.pi)
            targets = targets.clip(robot_lower, robot_upper)
            gym.set_actor_dof_position_targets(env, robot_handle, targets)
        elif elbow_handle is not None and wrist_handle is not None:
            set_actor_pose(gym, env, elbow_handle, elbow)
            set_actor_pose(gym, env, wrist_handle, wrist)

        gym.simulate(sim)
        gym.fetch_results(sim, True)
        gym.step_graphics(sim)
        gym.clear_lines(viewer)

        blue = vec(0.05, 0.40, 0.85)
        green = vec(0.20, 0.78, 0.35)
        amber = vec(0.95, 0.70, 0.16)
        if robot_handle is None:
            gymutil.draw_line(base, shoulder, blue, gym, viewer, env)
            gymutil.draw_line(shoulder, elbow, blue, gym, viewer, env)
            gymutil.draw_line(elbow, wrist, blue, gym, viewer, env)
            gymutil.draw_line(vec(wrist.x - 0.055, wrist.y - 0.045, wrist.z), vec(wrist.x - 0.015, wrist.y - 0.105, wrist.z), amber, gym, viewer, env)
            gymutil.draw_line(vec(wrist.x + 0.055, wrist.y - 0.045, wrist.z), vec(wrist.x + 0.015, wrist.y - 0.105, wrist.z), amber, gym, viewer, env)
        else:
            robot_mount = vec(-0.50, 0.55, 0.34)
            if robot_attractor_handle is not None:
                attractor = gym.get_attractor_properties(env, robot_attractor_handle)
                gymutil.draw_lines(gymutil.AxesGeometry(0.09), gym, viewer, env, attractor.target)
            gymutil.draw_line(robot_mount, elbow, blue, gym, viewer, env)
            gymutil.draw_line(elbow, palm, blue, gym, viewer, env)
            gymutil.draw_line(vec(palm.x - grip_gap * 0.5, palm.y - 0.08, palm.z), vec(block_pos.x - 0.08, block_pos.y + 0.01, block_pos.z), amber, gym, viewer, env)
            gymutil.draw_line(vec(palm.x + grip_gap * 0.5, palm.y - 0.08, palm.z), vec(block_pos.x + 0.08, block_pos.y + 0.01, block_pos.z), amber, gym, viewer, env)
        gymutil.draw_line(vec(start.x, start.y + 0.02, start.z), vec(target.x, target.y + 0.02, target.z), green, gym, viewer, env)

        gym.draw_viewer(viewer, sim, True)
        gym.sync_frame_time(sim)
        frame += 1
        if not args.loop and frame >= args.frames + 120:
            break

    gym.destroy_viewer(viewer)
    gym.destroy_sim(sim)


if __name__ == "__main__":
    main()
