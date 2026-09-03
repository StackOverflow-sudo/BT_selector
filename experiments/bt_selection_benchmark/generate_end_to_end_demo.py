#!/usr/bin/env python3
"""Generate a self-contained end-to-end BT selection demo page."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import pandas as pd


ROOT = Path("/home/theshy/projects/mycode/kios_baseline")


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def resolve_path(path_value: str) -> Path:
    path = Path(str(path_value))
    if path.is_absolute():
        return path
    return ROOT / path


def node_label(node: dict) -> str:
    type_name = node.get("type_name", "node")
    name = node.get("name") or node.get("summary") or type_name
    return f"{type_name}: {name}"


def render_bt_node(node: dict) -> str:
    if not isinstance(node, dict):
        return ""
    children = node.get("children", []) or []
    details = []
    for key in ["conditions", "effects"]:
        values = node.get(key, []) or []
        for item in values:
            if not isinstance(item, dict):
                continue
            obj = item.get("object_name")
            prop = item.get("property_name")
            val = item.get("property_value")
            details.append(f"{key[:-1]}: {obj}.{prop}={val}")
    detail_html = "".join(f"<div class='bt-detail'>{html.escape(x)}</div>" for x in details[:4])
    child_html = "".join(render_bt_node(child) for child in children)
    if child_html:
        child_html = f"<ul>{child_html}</ul>"
    return f"<li><span>{html.escape(node_label(node))}</span>{detail_html}{child_html}</li>"


def render_bt_tree(path_value: str) -> tuple[str, str]:
    tree = read_json(resolve_path(path_value))
    if not tree:
        return "<p>BT JSON not found.</p>", ""
    summary = str(tree.get("summary") or tree.get("name") or "Behavior Tree")
    return f"<ul class='bt-tree'>{render_bt_node(tree)}</ul>", summary


def fmt(value, digits: int = 3) -> str:
    if pd.isna(value):
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def row_class(candidate_id: str, selected: str, oracle: str) -> str:
    classes = []
    if candidate_id == selected:
        classes.append("selected")
    if candidate_id == oracle:
        classes.append("oracle")
    return " ".join(classes)


def generate(args: argparse.Namespace) -> None:
    evaluations = pd.read_csv(args.evaluations)
    choices = pd.read_csv(args.choices)
    manifest = pd.read_csv(args.manifest)

    group = evaluations[
        (evaluations["task_id"] == args.task_id)
        & (evaluations["initial_state_id"] == args.initial_state_id)
    ].copy()
    if group.empty:
        raise ValueError(f"No rows found for task={args.task_id}, state={args.initial_state_id}")

    selector_group_id = f"{args.benchmark}::{args.initial_state_id}::{args.task_id}"
    selected_rows = choices[
        (choices["selector"] == args.selector)
        & (choices["selector_group_id"] == selector_group_id)
    ]
    if selected_rows.empty:
        selected_candidate = group.sort_values("score", ascending=False).iloc[0]["candidate_id"]
        oracle_candidate = selected_candidate
    else:
        selected_candidate = str(selected_rows.iloc[0]["selected_candidate"])
        oracle_candidate = str(selected_rows.iloc[0]["oracle_candidate"])

    group["is_selected"] = group["candidate_id"].astype(str) == selected_candidate
    group["is_oracle"] = group["candidate_id"].astype(str) == oracle_candidate
    selected_eval = group[group["is_selected"]].iloc[0]
    selected_manifest = manifest[
        (manifest["task_id"] == args.task_id)
        & (manifest["initial_state_id"] == args.initial_state_id)
        & (manifest["candidate_id"] == selected_candidate)
    ]
    selected_manifest_row = selected_manifest.iloc[0] if not selected_manifest.empty else None

    bt_tree_html, bt_summary = render_bt_tree(str(selected_eval["bt_path"]))
    run_command = ""
    expected_pickle = ""
    config_path = ""
    if selected_manifest_row is not None:
        run_command = str(selected_manifest_row.get("run_command", ""))
        expected_pickle = str(selected_manifest_row.get("expected_pickle", ""))
        config_path = str(selected_manifest_row.get("config_path", ""))

    full_run_command = f"""deactivate 2>/dev/null || true
source /opt/ros/noetic/setup.bash
source /home/theshy/projects/mycode/ll4ma_catkin_ws/devel/setup.bash
cd /home/theshy/projects/mycode/ll4ma_isaac/ll4ma_isaacgym/src/ll4ma_isaacgym/scripts
{run_command}""".strip()

    candidate_rows = []
    for _, row in group.sort_values("candidate_id").iterrows():
        candidate_id = str(row["candidate_id"])
        cls = row_class(candidate_id, selected_candidate, oracle_candidate)
        tags = []
        if candidate_id == selected_candidate:
            tags.append("<span class='tag selected-tag'>selected</span>")
        if candidate_id == oracle_candidate:
            tags.append("<span class='tag oracle-tag'>oracle</span>")
        candidate_rows.append(
            f"""
            <tr class="{cls}">
              <td><strong>{html.escape(candidate_id)}</strong><div class="tags">{''.join(tags)}</div></td>
              <td>{html.escape(str(row.get("candidate_type", "")))}</td>
              <td>{fmt(row.get("symbolic_success"))}</td>
              <td>{fmt(row.get("sim_success"))}</td>
              <td>{fmt(row.get("goal_satisfaction"))}</td>
              <td>{fmt(row.get("precondition_coverage"))}</td>
              <td>{fmt(row.get("final_position_error"))}</td>
              <td>{fmt(row.get("object_displacement_error"))}</td>
              <td>{fmt(row.get("contact_violation_proxy"))}</td>
              <td>{fmt(row.get("tree_size"), 0)}</td>
              <td>{fmt(row.get("tree_depth"), 0)}</td>
              <td>{fmt(row.get("score"))}</td>
            </tr>
            """
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>End-to-End BT Selection Demo</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #f8fafc;
      --fg: #172033;
      --muted: #5d667a;
      --panel: #ffffff;
      --border: #d9dfeb;
      --blue: #2563eb;
      --green: #14843b;
      --orange: #b45309;
      --red: #b42318;
      --code: #f1f5f9;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #10131a;
        --fg: #e8ecf5;
        --muted: #a9b1c2;
        --panel: #171b24;
        --border: #2a3140;
        --blue: #7aa2ff;
        --green: #6dd58c;
        --orange: #f1b45a;
        --red: #ff8a80;
        --code: #202633;
      }}
    }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--bg);
      color: var(--fg);
      line-height: 1.45;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1, h2, h3 {{
      margin: 0 0 12px;
      font-weight: 600;
    }}
    h1 {{
      font-size: 28px;
    }}
    h2 {{
      font-size: 20px;
      margin-top: 24px;
    }}
    p {{
      margin: 0 0 10px;
      color: var(--muted);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin: 16px 0;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px;
    }}
    .label {{
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 4px;
    }}
    .value {{
      font-size: 18px;
      font-weight: 600;
      overflow-wrap: anywhere;
    }}
    .flow {{
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: 8px;
      margin: 16px 0;
    }}
    .step {{
      border: 1px solid var(--border);
      background: var(--panel);
      border-radius: 8px;
      padding: 10px;
      text-align: center;
      font-size: 13px;
      min-height: 54px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
    }}
    th, td {{
      padding: 9px;
      border-bottom: 1px solid var(--border);
      text-align: left;
      font-size: 13px;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
      white-space: nowrap;
    }}
    tr.selected {{
      outline: 2px solid var(--green);
      outline-offset: -2px;
    }}
    tr.oracle td:first-child {{
      color: var(--blue);
    }}
    .tag {{
      display: inline-block;
      padding: 2px 6px;
      border-radius: 999px;
      font-size: 11px;
      margin: 4px 4px 0 0;
      border: 1px solid var(--border);
    }}
    .selected-tag {{
      color: var(--green);
    }}
    .oracle-tag {{
      color: var(--blue);
    }}
    .split {{
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 16px;
      margin-top: 14px;
    }}
    .bt-tree, .bt-tree ul {{
      list-style: none;
      padding-left: 18px;
    }}
    .bt-tree li {{
      margin: 8px 0;
      border-left: 2px solid var(--border);
      padding-left: 10px;
    }}
    .bt-tree span {{
      font-weight: 600;
    }}
    .bt-detail {{
      color: var(--muted);
      font-size: 12px;
      margin-top: 2px;
    }}
    pre {{
      background: var(--code);
      padding: 12px;
      border-radius: 8px;
      overflow-x: auto;
      border: 1px solid var(--border);
      font-size: 13px;
    }}
    code {{
      font-family: Consolas, Monaco, monospace;
    }}
    .table-wrap {{
      overflow-x: auto;
      border-radius: 8px;
    }}
    @media (max-width: 860px) {{
      .grid, .flow, .split {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
<main>
  <h1>End-to-End Behavior Tree Selection Demo</h1>
  <p>This page shows one complete chain: task definition, candidate BTs, KIOS scores, Isaac Gym scores, selector decision, and the command to execute the selected simulation job.</p>

  <div class="flow">
    <div class="step">Task definition</div>
    <div class="step">Generate candidate BTs</div>
    <div class="step">KIOS symbolic scoring</div>
    <div class="step">Isaac Gym metrics</div>
    <div class="step">Selector ranking</div>
    <div class="step">Execute selected BT</div>
  </div>

  <h2>Task</h2>
  <div class="grid">
    <div class="card"><div class="label">Instruction</div><div class="value">{html.escape(str(selected_eval["task_instruction"]))}</div></div>
    <div class="card"><div class="label">Initial state</div><div class="value">{html.escape(args.initial_state_id)}</div></div>
    <div class="card"><div class="label">Target predicate</div><div class="value">{html.escape(str(selected_eval["target_predicate"]))}</div></div>
    <div class="card"><div class="label">Selector</div><div class="value">{html.escape(args.selector)}</div></div>
  </div>

  <h2>Candidate Scores</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Candidate</th>
          <th>Type</th>
          <th>KIOS success</th>
          <th>Sim success</th>
          <th>Goal</th>
          <th>Preconditions</th>
          <th>Final error</th>
          <th>Displacement</th>
          <th>Contact</th>
          <th>Size</th>
          <th>Depth</th>
          <th>True score</th>
        </tr>
      </thead>
      <tbody>
        {''.join(candidate_rows)}
      </tbody>
    </table>
  </div>

  <h2>Selected BT</h2>
  <div class="grid">
    <div class="card"><div class="label">Selected candidate</div><div class="value">{html.escape(selected_candidate)}</div></div>
    <div class="card"><div class="label">Oracle candidate</div><div class="value">{html.escape(oracle_candidate)}</div></div>
    <div class="card"><div class="label">Selected score</div><div class="value">{fmt(selected_eval.get("score"))}</div></div>
    <div class="card"><div class="label">Expected pickle</div><div class="value">{html.escape(expected_pickle or "-")}</div></div>
  </div>

  <div class="split">
    <div class="card">
      <h3>Behavior Tree Structure</h3>
      <p>{html.escape(bt_summary)}</p>
      {bt_tree_html}
    </div>
    <div class="card">
      <h3>Selected Isaac Gym Job</h3>
      <p>Config: <code>{html.escape(config_path or "-")}</code></p>
      <pre><code>{html.escape(full_run_command)}</code></pre>
    </div>
  </div>

  <h2>How To Demo Live</h2>
  <pre><code>cd /home/theshy/projects/mycode/kios_baseline
python3 experiments/bt_selection_benchmark/generate_end_to_end_demo.py

# In another terminal, keep ROS/MoveIt running:
deactivate 2&gt;/dev/null || true
source /opt/ros/noetic/setup.bash
source /home/theshy/projects/mycode/ll4ma_catkin_ws/devel/setup.bash
roslaunch moveit_interface iiwa_reflex_moveit_interface_service.launch

# Then copy the selected Isaac Gym command from this page.</code></pre>
</main>
</body>
</html>
""",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "result": "success",
                "output": str(output),
                "task_id": args.task_id,
                "initial_state_id": args.initial_state_id,
                "selector": args.selector,
                "selected_candidate": selected_candidate,
                "oracle_candidate": oracle_candidate,
                "expected_pickle": expected_pickle,
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="v2b_physical_strategy")
    parser.add_argument("--task-id", default="place_block3_on_block5")
    parser.add_argument("--initial-state-id", default="state_000_t0")
    parser.add_argument("--selector", default="feature_only")
    parser.add_argument(
        "--evaluations",
        default="experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v2b_physical_strategy_with_sim.csv",
    )
    parser.add_argument(
        "--choices",
        default="experiments/bt_selection_benchmark/results/v4b_transformer_selector_choices.csv",
    )
    parser.add_argument(
        "--manifest",
        default="experiments/bt_selection_benchmark/simulation_jobs_v2b_physical_strategy/simulation_jobs_manifest.csv",
    )
    parser.add_argument(
        "--output",
        default="experiments/bt_selection_benchmark/results/end_to_end_demo.html",
    )
    generate(parser.parse_args())


if __name__ == "__main__":
    main()
