#!/usr/bin/env python3
"""Generate a polished dashboard for the end-to-end BT selection demo."""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path("/home/theshy/projects/mycode/kios_baseline")


def resolve_path(path_value: str) -> Path:
    path = Path(str(path_value))
    return path if path.is_absolute() else ROOT / path


def read_json(path_value: str) -> dict:
    path = resolve_path(path_value)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def clean(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    return str(value)


def num(value, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "-"
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return clean(value)


def bool_label(value) -> str:
    try:
        return "yes" if int(value) == 1 else "no"
    except Exception:
        return clean(value)


def bt_node_label(node: dict) -> str:
    type_name = clean(node.get("type_name", "node"))
    name = clean(node.get("name") or node.get("summary") or type_name)
    return f"{type_name}: {name}"


def compact_node(node: dict) -> dict:
    if not isinstance(node, dict):
        return {}
    facts: list[str] = []
    for key in ["conditions", "effects"]:
        for item in node.get(key, []) or []:
            if not isinstance(item, dict):
                continue
            obj = clean(item.get("object_name"))
            prop = clean(item.get("property_name"))
            val = clean(item.get("property_value"))
            facts.append(f"{obj}.{prop}={val}")
    return {
        "label": bt_node_label(node),
        "type": clean(node.get("type_name", "node")),
        "facts": facts[:3],
        "children": [compact_node(child) for child in node.get("children", []) or []],
    }


def candidate_record(row: pd.Series, selected: str, oracle: str, manifest: pd.DataFrame) -> dict:
    job = manifest[
        (manifest["task_id"] == row["task_id"])
        & (manifest["initial_state_id"] == row["initial_state_id"])
        & (manifest["candidate_id"] == row["candidate_id"])
    ]
    job_row = job.iloc[0].to_dict() if not job.empty else {}
    tree = compact_node(read_json(str(row["bt_path"])))
    return {
        "candidate_id": clean(row["candidate_id"]),
        "candidate_type": clean(row["candidate_type"]),
        "bt_path": clean(row["bt_path"]),
        "tree": tree,
        "is_selected": clean(row["candidate_id"]) == selected,
        "is_oracle": clean(row["candidate_id"]) == oracle,
        "symbolic_success": int(row.get("symbolic_success", 0)),
        "sim_success": int(row.get("sim_success", 0)),
        "goal_satisfaction": float(row.get("goal_satisfaction", 0) or 0),
        "precondition_coverage": float(row.get("precondition_coverage", 0) or 0),
        "final_position_error": float(row.get("final_position_error", 0) or 0),
        "object_displacement_error": float(row.get("object_displacement_error", 0) or 0),
        "contact_violation_proxy": float(row.get("contact_violation_proxy", 0) or 0),
        "tree_size": int(row.get("tree_size", 0) or 0),
        "tree_depth": int(row.get("tree_depth", 0) or 0),
        "score": float(row.get("score", 0) or 0),
        "label": clean(row.get("label", "")),
        "simulation_status": clean(row.get("simulation_status", "")),
        "execution_result": clean(row.get("execution_result", "")),
        "placement_strategy": clean(job_row.get("placement_strategy", "")),
        "expected_pickle": clean(job_row.get("expected_pickle", "")),
        "config_path": clean(job_row.get("config_path", "")),
        "run_command": clean(job_row.get("run_command", "")),
    }


def choose_candidates(args: argparse.Namespace, group: pd.DataFrame, choices: pd.DataFrame) -> tuple[str, str]:
    selector_group_id = f"{args.benchmark}::{args.initial_state_id}::{args.task_id}"
    chosen = choices[
        (choices["selector"] == args.selector)
        & (choices["selector_group_id"] == selector_group_id)
    ]
    if not chosen.empty:
        row = chosen.iloc[0]
        return clean(row["selected_candidate"]), clean(row["oracle_candidate"])
    fallback = group.sort_values("score", ascending=False).iloc[0]
    return clean(fallback["candidate_id"]), clean(fallback["candidate_id"])


def generate(args: argparse.Namespace) -> None:
    evaluations = pd.read_csv(args.evaluations)
    choices = pd.read_csv(args.choices)
    manifest = pd.read_csv(args.manifest)
    group = evaluations[
        (evaluations["task_id"] == args.task_id)
        & (evaluations["initial_state_id"] == args.initial_state_id)
    ].copy()
    if group.empty:
        raise ValueError(f"No demo rows found for task={args.task_id}, state={args.initial_state_id}")

    selected, oracle = choose_candidates(args, group, choices)
    records = [
        candidate_record(row, selected, oracle, manifest)
        for _, row in group.sort_values("score", ascending=False).iterrows()
    ]
    task = group.iloc[0]
    selected_record = next((r for r in records if r["candidate_id"] == selected), records[0])
    oracle_record = next((r for r in records if r["candidate_id"] == oracle), selected_record)
    max_score = max(r["score"] for r in records) if records else 1
    min_score = min(r["score"] for r in records) if records else 0

    data = {
        "task": {
            "task_id": args.task_id,
            "initial_state_id": args.initial_state_id,
            "selector": args.selector,
            "instruction": clean(task["task_instruction"]),
            "target_predicate": clean(task["target_predicate"]),
            "moved_object": clean(task["moved_object"]),
            "support_object": clean(task["support_object"]),
            "selected": selected,
            "oracle": oracle,
        },
        "records": records,
        "score_min": min_score,
        "score_max": max_score,
        "selected": selected_record,
        "oracle": oracle_record,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_html(data), encoding="utf-8")
    print(
        json.dumps(
            {
                "result": "success",
                "output": str(output),
                "task_id": args.task_id,
                "initial_state_id": args.initial_state_id,
                "selector": args.selector,
                "selected_candidate": selected,
                "oracle_candidate": oracle,
            },
            indent=2,
        )
    )


def build_html(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    task = data["task"]
    selected = data["selected"]
    oracle_match = task["selected"] == task["oracle"]
    conclusion = (
        "Selector matches oracle and the selected BT is simulation-successful."
        if oracle_match and selected["sim_success"]
        else "Selector chooses a feasible BT, but it differs from the oracle candidate."
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BT Selection Demo Dashboard</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #f6f7fb;
      --fg: #161a24;
      --muted: #626b7f;
      --panel: #ffffff;
      --panel-2: #f0f4f8;
      --border: #d8deea;
      --blue: #2563eb;
      --green: #16803f;
      --orange: #b35c00;
      --red: #bd2b22;
      --purple: #6f42c1;
      --shadow: 0 10px 28px rgba(28, 35, 51, 0.08);
      --code: #eef2f7;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #0f1218;
        --fg: #edf0f7;
        --muted: #a5adbd;
        --panel: #171c25;
        --panel-2: #202633;
        --border: #303848;
        --blue: #83a8ff;
        --green: #77d994;
        --orange: #ffc06a;
        --red: #ff8b82;
        --purple: #c6a7ff;
        --shadow: none;
        --code: #202633;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--fg);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.45;
    }}
    main {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 24px;
    }}
    header {{
      display: grid;
      grid-template-columns: 1.5fr 1fr;
      gap: 16px;
      align-items: stretch;
      margin-bottom: 16px;
    }}
    h1, h2, h3 {{ margin: 0; font-weight: 600; }}
    h1 {{ font-size: 28px; }}
    h2 {{ font-size: 18px; margin-bottom: 10px; }}
    h3 {{ font-size: 15px; margin-bottom: 8px; }}
    p {{ margin: 6px 0 0; color: var(--muted); }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 16px;
    }}
    .summary {{
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      margin: 16px 0;
    }}
    .metric {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      min-height: 86px;
    }}
    .metric .label {{ color: var(--muted); font-size: 12px; }}
    .metric .value {{ font-size: 19px; font-weight: 600; margin-top: 4px; overflow-wrap: anywhere; }}
    .metric .sub {{ color: var(--muted); font-size: 12px; margin-top: 4px; }}
    .pipeline {{
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: 8px;
      margin-top: 12px;
    }}
    .stage {{
      background: var(--panel-2);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      min-height: 64px;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      font-size: 13px;
      color: var(--fg);
    }}
    .status-line {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 4px 9px;
      font-size: 12px;
      color: var(--muted);
      background: var(--panel-2);
    }}
    .chip.good {{ color: var(--green); }}
    .chip.warn {{ color: var(--orange); }}
    .chip.info {{ color: var(--blue); }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(360px, 0.85fr);
      gap: 16px;
      align-items: start;
    }}
    .candidate-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    button.candidate {{
      border: 1px solid var(--border);
      background: var(--panel);
      color: var(--fg);
      border-radius: 8px;
      text-align: left;
      padding: 11px;
      cursor: pointer;
      min-height: 112px;
      font: inherit;
    }}
    button.candidate[aria-pressed="true"] {{
      outline: 2px solid var(--blue);
      outline-offset: -2px;
    }}
    .candidate-top {{
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: start;
      margin-bottom: 8px;
    }}
    .candidate-name {{ font-weight: 600; overflow-wrap: anywhere; }}
    .tags {{ display: flex; flex-wrap: wrap; gap: 4px; justify-content: flex-end; }}
    .tag {{
      border-radius: 999px;
      border: 1px solid var(--border);
      padding: 2px 6px;
      font-size: 11px;
      color: var(--muted);
      background: var(--panel-2);
    }}
    .tag.selected {{ color: var(--green); }}
    .tag.oracle {{ color: var(--blue); }}
    .tag.fail {{ color: var(--red); }}
    .bars {{ display: grid; gap: 6px; }}
    .bar-row {{ display: grid; grid-template-columns: 82px 1fr 52px; gap: 8px; align-items: center; font-size: 12px; color: var(--muted); }}
    .bar-track {{ height: 8px; border-radius: 999px; background: var(--panel-2); overflow: hidden; }}
    .bar {{ height: 100%; border-radius: 999px; width: 0; background: var(--blue); }}
    .bar.score {{ background: var(--purple); }}
    .bar.sim {{ background: var(--green); }}
    .detail-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin: 12px 0;
    }}
    .mini {{
      background: var(--panel-2);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 9px;
    }}
    .mini .label {{ color: var(--muted); font-size: 11px; }}
    .mini .value {{ font-size: 15px; font-weight: 600; margin-top: 2px; overflow-wrap: anywhere; }}
    .bt-tree, .bt-tree ul {{ list-style: none; padding-left: 16px; margin: 0; }}
    .bt-tree li {{ border-left: 2px solid var(--border); margin: 7px 0; padding-left: 10px; }}
    .node-label {{ font-weight: 600; font-size: 13px; }}
    .fact {{ color: var(--muted); font-size: 12px; margin-top: 2px; }}
    pre {{
      background: var(--code);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      overflow-x: auto;
      white-space: pre-wrap;
      font-size: 12px;
      margin: 0;
    }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid var(--border); padding: 8px; text-align: left; font-size: 12px; }}
    th {{ color: var(--muted); font-weight: 600; }}
    .footer-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-top: 16px;
    }}
    @media (max-width: 980px) {{
      header, .layout, .footer-grid {{ grid-template-columns: 1fr; }}
      .candidate-grid, .summary {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .pipeline {{ grid-template-columns: repeat(3, 1fr); }}
    }}
    @media (max-width: 560px) {{
      main {{ padding: 14px; }}
      .candidate-grid, .summary, .detail-grid, .pipeline {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <section class="panel">
      <h1>BT Selection Demo Dashboard</h1>
      <p>{html.escape(task["instruction"])}</p>
      <div class="status-line">
        <span class="chip info">task: {html.escape(task["task_id"])}</span>
        <span class="chip info">state: {html.escape(task["initial_state_id"])}</span>
        <span class="chip info">selector: {html.escape(task["selector"])}</span>
        <span class="chip {'good' if oracle_match else 'warn'}">{html.escape(conclusion)}</span>
      </div>
      <div class="pipeline">
        <div class="stage">Task definition</div>
        <div class="stage">Candidate BTs</div>
        <div class="stage">KIOS scoring</div>
        <div class="stage">Isaac Gym metrics</div>
        <div class="stage">Ranking selector</div>
        <div class="stage">Selected BT</div>
      </div>
    </section>
    <section class="panel">
      <h2>Decision Summary</h2>
      <div class="detail-grid">
        <div class="mini"><div class="label">selected</div><div class="value" id="summary-selected">{html.escape(task["selected"])}</div></div>
        <div class="mini"><div class="label">oracle</div><div class="value">{html.escape(task["oracle"])}</div></div>
        <div class="mini"><div class="label">match</div><div class="value">{'yes' if oracle_match else 'no'}</div></div>
      </div>
      <p>Target: <strong>{html.escape(task["target_predicate"])}</strong></p>
      <p>Objects: <strong>{html.escape(task["moved_object"])}</strong> -> <strong>{html.escape(task["support_object"])}</strong></p>
    </section>
  </header>

  <section class="summary">
    <div class="metric"><div class="label">KIOS symbolic success</div><div class="value" id="m-symbolic">-</div><div class="sub">selected candidate</div></div>
    <div class="metric"><div class="label">Isaac Gym sim success</div><div class="value" id="m-sim">-</div><div class="sub">selected candidate</div></div>
    <div class="metric"><div class="label">Final position error</div><div class="value" id="m-error">-</div><div class="sub">lower is better</div></div>
    <div class="metric"><div class="label">True score</div><div class="value" id="m-score">-</div><div class="sub">simulation-grounded</div></div>
  </section>

  <div class="layout">
    <section class="panel">
      <h2>Candidate Ranking</h2>
      <div class="candidate-grid" id="candidate-grid"></div>
    </section>
    <aside class="panel">
      <h2 id="detail-title">Selected BT</h2>
      <div class="detail-grid">
        <div class="mini"><div class="label">candidate type</div><div class="value" id="d-type">-</div></div>
        <div class="mini"><div class="label">placement</div><div class="value" id="d-placement">-</div></div>
        <div class="mini"><div class="label">tree size/depth</div><div class="value" id="d-tree">-</div></div>
      </div>
      <h3>BT Structure</h3>
      <div id="bt-tree"></div>
    </aside>
  </div>

  <section class="footer-grid">
    <div class="panel">
      <h2>Selected Isaac Gym Job</h2>
      <div class="detail-grid">
        <div class="mini"><div class="label">simulation status</div><div class="value" id="job-status">-</div></div>
        <div class="mini"><div class="label">execution result</div><div class="value" id="job-result">-</div></div>
        <div class="mini"><div class="label">pickle</div><div class="value" id="job-pickle">-</div></div>
      </div>
      <pre><code id="job-command"></code></pre>
    </div>
    <div class="panel">
      <h2>Compact Score Table</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>candidate</th><th>sym</th><th>sim</th><th>error</th><th>score</th></tr>
          </thead>
          <tbody id="score-table"></tbody>
        </table>
      </div>
    </div>
  </section>
</main>
<script>
const DEMO = {payload};
let activeId = DEMO.task.selected;

function fmt(value, digits = 3) {{
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toFixed(digits);
}}

function yesNo(value) {{
  return Number(value) === 1 ? "yes" : "no";
}}

function escapeHtml(value) {{
  return String(value ?? "-")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}}

function scorePct(score) {{
  const min = DEMO.score_min;
  const max = DEMO.score_max;
  if (max <= min) return 100;
  return Math.max(0, Math.min(100, ((score - min) / (max - min)) * 100));
}}

function renderNode(node) {{
  if (!node || !node.label) return "";
  const facts = (node.facts || []).map(f => `<div class="fact">${{escapeHtml(f)}}</div>`).join("");
  const children = (node.children || []).map(renderNode).join("");
  return `<li><div class="node-label">${{escapeHtml(node.label)}}</div>${{facts}}${{children ? `<ul>${{children}}</ul>` : ""}}</li>`;
}}

function selectCandidate(id) {{
  activeId = id;
  const record = DEMO.records.find(r => r.candidate_id === id) || DEMO.selected;
  document.querySelectorAll("button.candidate").forEach(btn => {{
    btn.setAttribute("aria-pressed", btn.dataset.id === id ? "true" : "false");
  }});
  document.getElementById("summary-selected").textContent = record.candidate_id;
  document.getElementById("m-symbolic").textContent = yesNo(record.symbolic_success);
  document.getElementById("m-sim").textContent = yesNo(record.sim_success);
  document.getElementById("m-error").textContent = fmt(record.final_position_error);
  document.getElementById("m-score").textContent = fmt(record.score);
  document.getElementById("detail-title").textContent = record.candidate_id;
  document.getElementById("d-type").textContent = record.candidate_type;
  document.getElementById("d-placement").textContent = record.placement_strategy || "-";
  document.getElementById("d-tree").textContent = `${{record.tree_size}} / ${{record.tree_depth}}`;
  document.getElementById("bt-tree").innerHTML = `<ul class="bt-tree">${{renderNode(record.tree)}}</ul>`;
  document.getElementById("job-status").textContent = record.simulation_status || "-";
  document.getElementById("job-result").textContent = record.execution_result || "-";
  document.getElementById("job-pickle").textContent = record.expected_pickle || "-";
  document.getElementById("job-command").textContent =
    `deactivate 2>/dev/null || true\\nsource /opt/ros/noetic/setup.bash\\nsource /home/theshy/projects/mycode/ll4ma_catkin_ws/devel/setup.bash\\ncd /home/theshy/projects/mycode/ll4ma_isaac/ll4ma_isaacgym/src/ll4ma_isaacgym/scripts\\n${{record.run_command || ""}}`;
}}

function renderCandidates() {{
  const grid = document.getElementById("candidate-grid");
  grid.innerHTML = DEMO.records.map(record => {{
    const tags = [
      record.is_selected ? '<span class="tag selected">selected</span>' : "",
      record.is_oracle ? '<span class="tag oracle">oracle</span>' : "",
      Number(record.sim_success) === 0 ? '<span class="tag fail">sim fail</span>' : ""
    ].join("");
    return `<button type="button" class="candidate" data-id="${{escapeHtml(record.candidate_id)}}" aria-pressed="${{record.candidate_id === activeId ? "true" : "false"}}">
      <div class="candidate-top">
        <div><div class="candidate-name">${{escapeHtml(record.candidate_id)}}</div><div class="chip">${{escapeHtml(record.candidate_type)}}</div></div>
        <div class="tags">${{tags}}</div>
      </div>
      <div class="bars">
        <div class="bar-row"><span>true score</span><div class="bar-track"><div class="bar score" style="width:${{scorePct(record.score)}}%"></div></div><span>${{fmt(record.score, 1)}}</span></div>
        <div class="bar-row"><span>goal</span><div class="bar-track"><div class="bar" style="width:${{record.goal_satisfaction * 100}}%"></div></div><span>${{fmt(record.goal_satisfaction, 2)}}</span></div>
        <div class="bar-row"><span>sim</span><div class="bar-track"><div class="bar sim" style="width:${{Number(record.sim_success) * 100}}%"></div></div><span>${{yesNo(record.sim_success)}}</span></div>
      </div>
    </button>`;
  }}).join("");
  grid.querySelectorAll("button.candidate").forEach(btn => {{
    btn.addEventListener("click", () => selectCandidate(btn.dataset.id));
  }});
}}

function renderTable() {{
  document.getElementById("score-table").innerHTML = DEMO.records.map(record => `
    <tr>
      <td>${{escapeHtml(record.candidate_id)}}</td>
      <td>${{yesNo(record.symbolic_success)}}</td>
      <td>${{yesNo(record.sim_success)}}</td>
      <td>${{fmt(record.final_position_error)}}</td>
      <td>${{fmt(record.score, 1)}}</td>
    </tr>
  `).join("");
}}

renderCandidates();
renderTable();
selectCandidate(activeId);
</script>
</body>
</html>
"""


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
        default="experiments/bt_selection_benchmark/results/end_to_end_demo_dashboard.html",
    )
    generate(parser.parse_args())


if __name__ == "__main__":
    main()
