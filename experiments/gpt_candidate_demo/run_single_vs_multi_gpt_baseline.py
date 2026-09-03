#!/usr/bin/env python3
"""Run paired single-BT GPT baseline vs multi-BT + selector experiments.

The unit of comparison is one task/state/repeat pair:

* single: ask GPT for 1 BT, then execute the only returned candidate.
* multi: ask GPT for K BTs, score all candidates, then select with the demo
  selector pipeline.

This script intentionally calls the existing GPT demo runner as a subprocess so
the prompt, BT normalization, KIOS evaluation, learned V5 scoring, and frontend
payload stay identical to the demo page.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = ROOT / "experiments" / "gpt_candidate_demo"
RUNNER = DEMO_DIR / "run_gpt_candidate_demo.py"
DEFAULT_TASK_SPECS = ROOT / "experiments" / "bt_selection_benchmark" / "task_specs_v6_hard_cases.json"
DEFAULT_RESULTS_DIR = DEMO_DIR / "results"
DEFAULT_OUTPUT_DIR = DEMO_DIR / "single_vs_multi_outputs"


SELECTED_COLUMNS = [
    "comparison_id",
    "mode",
    "status",
    "error",
    "repeat",
    "task_id",
    "initial_state_id",
    "timestep",
    "generator",
    "model",
    "candidate_count_requested",
    "candidate_count_returned",
    "selector",
    "selected_candidate",
    "oracle_candidate",
    "selected_rank",
    "selected_score",
    "oracle_match",
    "symbolic_success",
    "goal_satisfaction",
    "sim_success",
    "true_score",
    "regret",
    "demo_selector_score",
    "v5_learned_no_simulation_score",
    "v5_learned_full_score",
    "manual_v5_score",
    "physical_feasibility_score",
    "symbolic_reliability_score",
    "tree_size",
    "tree_depth",
    "bt_ticks",
    "action_count",
    "invalid_action_count",
    "condition_failure_count",
    "run_dir",
    "frontend_payload",
]


CANDIDATE_COLUMNS = [
    "comparison_id",
    "mode",
    "repeat",
    "task_id",
    "initial_state_id",
    "candidate_id",
    "rank",
    "selector",
    "is_selected",
    "is_oracle",
    "selected_score",
    "symbolic_success",
    "goal_satisfaction",
    "sim_success",
    "true_score",
    "demo_selector_score",
    "v5_learned_no_simulation_score",
    "v5_learned_full_score",
    "manual_v5_score",
    "physical_feasibility_score",
    "symbolic_reliability_score",
    "tree_size",
    "tree_depth",
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_csv(path: Path, rows: List[Dict[str, Any]], columns: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out):
        return None
    return out


def as_int(value: Any) -> Optional[int]:
    number = as_float(value)
    if number is None:
        return None
    return int(number)


def metric(candidate: Dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in candidate and candidate[name] not in (None, ""):
            return candidate[name]
    metrics = candidate.get("metrics")
    if isinstance(metrics, dict):
        for name in names:
            if name in metrics and metrics[name] not in (None, ""):
                return metrics[name]
    return None


def first_number(candidate: Dict[str, Any], names: Iterable[str]) -> Optional[float]:
    for name in names:
        value = as_float(metric(candidate, name))
        if value is not None:
            return value
    return None


def normalize_task_list(spec: Any) -> List[Dict[str, Any]]:
    if isinstance(spec, list):
        tasks = spec
    elif isinstance(spec, dict):
        for key in ("tasks", "task_specs", "benchmarks"):
            if isinstance(spec.get(key), list):
                tasks = spec[key]
                break
        else:
            tasks = [spec]
    else:
        raise TypeError(f"Unsupported task spec format: {type(spec).__name__}")

    normalized: List[Dict[str, Any]] = []
    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        task_id = task.get("task_id") or task.get("id") or task.get("name")
        if not task_id:
            task_id = f"task_{idx:03d}"
        normalized.append({**task, "task_id": str(task_id)})
    return normalized


def build_cases(tasks: List[Dict[str, Any]], case_count: int, timesteps: List[int]) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    for timestep in timesteps:
        for task in tasks:
            cases.append({"task_id": task["task_id"], "timestep": timestep})
            if len(cases) >= case_count:
                return cases
    return cases


def candidate_id(candidate: Dict[str, Any]) -> str:
    value = candidate.get("candidate_id") or candidate.get("id") or candidate.get("name")
    return str(value or "")


def rank_value(candidate: Dict[str, Any], fallback: int) -> int:
    return as_int(candidate.get("rank")) or as_int(candidate.get("candidate_rank")) or fallback


def selected_score(candidate: Dict[str, Any], selector: str) -> Optional[float]:
    selector_key = f"{selector}_score"
    return first_number(
        candidate,
        [
            selector_key,
            "selected_score",
            "selector_score",
            "v5_learned_no_simulation_score",
            "v5_ensemble_score",
            "demo_selector_score",
            "score",
        ],
    )


def find_selected_candidate(payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], str]:
    task = payload.get("task") if isinstance(payload.get("task"), dict) else {}
    candidates = payload.get("candidates") if isinstance(payload.get("candidates"), list) else []
    selected_id = str(task.get("selected_candidate") or "")
    if selected_id:
        for candidate in candidates:
            if candidate_id(candidate) == selected_id:
                return candidate, selected_id
    for candidate in candidates:
        if candidate.get("is_selected") or candidate.get("selected"):
            return candidate, candidate_id(candidate)
    if candidates:
        return candidates[0], candidate_id(candidates[0])
    return None, selected_id


def run_one_demo(
    *,
    generator: str,
    model: str,
    task_id: str,
    timestep: int,
    candidate_count: int,
    run_dir: Path,
    task_specs: Path,
    learned_dataset: Optional[Path],
    model_dir: Optional[Path],
    online_epochs: int,
    force: bool,
) -> Dict[str, Any]:
    frontend_payload = run_dir / "frontend" / "demo_data.json"
    results_dir = run_dir / "results"
    output_dir = run_dir / "outputs"

    if frontend_payload.exists() and not force:
        return load_json(frontend_payload)

    cmd = [
        sys.executable,
        str(RUNNER),
        "--generator",
        generator,
        "--model",
        model,
        "--task-specs",
        str(task_specs),
        "--task-id",
        task_id,
        "--timestep",
        str(timestep),
        "--candidate-count",
        str(candidate_count),
        "--output-dir",
        str(output_dir),
        "--results-dir",
        str(results_dir),
        "--frontend-output",
        str(frontend_payload),
        "--online-epochs",
        str(online_epochs),
    ]
    if learned_dataset:
        cmd.extend(["--learned-dataset", str(learned_dataset)])
    if model_dir:
        cmd.extend(["--model-dir", str(model_dir)])

    run_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("OMP_NUM_THREADS", "4")
    env.setdefault("MKL_NUM_THREADS", "4")
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env, text=True, capture_output=True)
    (run_dir / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (run_dir / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(
            f"demo runner failed for {task_id} t={timestep} count={candidate_count}; "
            f"see {run_dir / 'stderr.log'}"
        )
    if not frontend_payload.exists():
        raise FileNotFoundError(f"Expected frontend payload was not written: {frontend_payload}")
    return load_json(frontend_payload)


def summarize_payload(
    *,
    payload: Dict[str, Any],
    comparison_id: str,
    mode: str,
    repeat: int,
    task_id: str,
    timestep: int,
    generator: str,
    model: str,
    candidate_count_requested: int,
    run_dir: Path,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    task = payload.get("task") if isinstance(payload.get("task"), dict) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    candidates = payload.get("candidates") if isinstance(payload.get("candidates"), list) else []
    selector = str(task.get("selector") or payload.get("default_selector") or summary.get("selector") or "selector")
    selected, selected_id = find_selected_candidate(payload)
    selected = selected or {}
    oracle_id = str(task.get("oracle_candidate") or summary.get("oracle_candidate") or "")
    initial_state_id = str(task.get("initial_state_id") or f"state_{timestep:03d}_t{timestep}")

    candidate_rows: List[Dict[str, Any]] = []
    for idx, candidate in enumerate(candidates, start=1):
        cid = candidate_id(candidate)
        candidate_rows.append(
            {
                "comparison_id": comparison_id,
                "mode": mode,
                "repeat": repeat,
                "task_id": task_id,
                "initial_state_id": initial_state_id,
                "candidate_id": cid,
                "rank": rank_value(candidate, idx),
                "selector": selector,
                "is_selected": int(cid == selected_id),
                "is_oracle": int(bool(oracle_id) and cid == oracle_id),
                "selected_score": selected_score(candidate, selector),
                "symbolic_success": first_number(candidate, ["symbolic_success"]),
                "goal_satisfaction": first_number(candidate, ["goal_satisfaction"]),
                "sim_success": first_number(candidate, ["sim_success"]),
                "true_score": first_number(candidate, ["true_score", "score"]),
                "demo_selector_score": first_number(candidate, ["demo_selector_score"]),
                "v5_learned_no_simulation_score": first_number(candidate, ["v5_learned_no_simulation_score"]),
                "v5_learned_full_score": first_number(candidate, ["v5_learned_full_score"]),
                "manual_v5_score": first_number(candidate, ["manual_v5_score", "v5_ensemble_score"]),
                "physical_feasibility_score": first_number(candidate, ["physical_feasibility_score"]),
                "symbolic_reliability_score": first_number(candidate, ["symbolic_reliability_score"]),
                "tree_size": first_number(candidate, ["tree_size"]),
                "tree_depth": first_number(candidate, ["tree_depth"]),
            }
        )

    selected_row = {
        "comparison_id": comparison_id,
        "mode": mode,
        "status": "ok",
        "error": "",
        "repeat": repeat,
        "task_id": task_id,
        "initial_state_id": initial_state_id,
        "timestep": timestep,
        "generator": generator,
        "model": model,
        "candidate_count_requested": candidate_count_requested,
        "candidate_count_returned": len(candidates),
        "selector": "single_first" if mode == "single" else selector,
        "selected_candidate": selected_id,
        "oracle_candidate": oracle_id,
        "selected_rank": rank_value(selected, 1) if selected else "",
        "selected_score": selected_score(selected, selector) if selected else None,
        "oracle_match": int(bool(oracle_id) and selected_id == oracle_id),
        "symbolic_success": first_number(selected, ["symbolic_success"]),
        "goal_satisfaction": first_number(selected, ["goal_satisfaction"]),
        "sim_success": first_number(selected, ["sim_success"]),
        "true_score": first_number(selected, ["true_score", "score"]),
        "regret": first_number(selected, ["regret"]) or as_float(summary.get("regret")),
        "demo_selector_score": first_number(selected, ["demo_selector_score"]),
        "v5_learned_no_simulation_score": first_number(selected, ["v5_learned_no_simulation_score"]),
        "v5_learned_full_score": first_number(selected, ["v5_learned_full_score"]),
        "manual_v5_score": first_number(selected, ["manual_v5_score", "v5_ensemble_score"]),
        "physical_feasibility_score": first_number(selected, ["physical_feasibility_score"]),
        "symbolic_reliability_score": first_number(selected, ["symbolic_reliability_score"]),
        "tree_size": first_number(selected, ["tree_size"]),
        "tree_depth": first_number(selected, ["tree_depth"]),
        "bt_ticks": first_number(selected, ["bt_ticks"]),
        "action_count": first_number(selected, ["action_count"]),
        "invalid_action_count": first_number(selected, ["invalid_action_count"]),
        "condition_failure_count": first_number(selected, ["condition_failure_count"]),
        "run_dir": str(run_dir),
        "frontend_payload": str(run_dir / "frontend" / "demo_data.json"),
    }
    return selected_row, candidate_rows


def failed_selected_row(
    *,
    comparison_id: str,
    mode: str,
    repeat: int,
    task_id: str,
    timestep: int,
    generator: str,
    model: str,
    candidate_count_requested: int,
    run_dir: Path,
    error: Exception,
) -> Dict[str, Any]:
    return {
        "comparison_id": comparison_id,
        "mode": mode,
        "status": "failed",
        "error": str(error),
        "repeat": repeat,
        "task_id": task_id,
        "initial_state_id": f"state_{timestep:03d}_t{timestep}",
        "timestep": timestep,
        "generator": generator,
        "model": model,
        "candidate_count_requested": candidate_count_requested,
        "candidate_count_returned": 0,
        "selector": "single_first" if mode == "single" else "v5_learned_no_simulation",
        "selected_candidate": "",
        "oracle_candidate": "",
        "selected_rank": "",
        "selected_score": "",
        "oracle_match": 0,
        "symbolic_success": 0,
        "goal_satisfaction": 0,
        "sim_success": "",
        "true_score": "",
        "regret": "",
        "demo_selector_score": "",
        "v5_learned_no_simulation_score": "",
        "v5_learned_full_score": "",
        "manual_v5_score": "",
        "physical_feasibility_score": "",
        "symbolic_reliability_score": "",
        "tree_size": "",
        "tree_depth": "",
        "bt_ticks": "",
        "action_count": "",
        "invalid_action_count": "",
        "condition_failure_count": "",
        "run_dir": str(run_dir),
        "frontend_payload": str(run_dir / "frontend" / "demo_data.json"),
    }


def mean(values: Iterable[Optional[float]]) -> Optional[float]:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def rate(values: Iterable[Optional[float]]) -> Optional[float]:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return sum(1 for v in clean if v > 0) / len(clean)


def summarize_selected(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["mode"])].append(row)

    output: List[Dict[str, Any]] = []
    for mode, mode_rows in sorted(grouped.items()):
        output.append(
            {
                "mode": mode,
                "runs": len(mode_rows),
                "successfully_evaluated_runs": sum(1 for r in mode_rows if r.get("status") == "ok"),
                "failed_runs": sum(1 for r in mode_rows if r.get("status") != "ok"),
                "mean_candidates_returned": mean(as_float(r.get("candidate_count_returned")) for r in mode_rows),
                "symbolic_success_rate": rate(as_float(r.get("symbolic_success")) for r in mode_rows),
                "sim_success_rate": rate(as_float(r.get("sim_success")) for r in mode_rows),
                "oracle_match_rate": rate(as_float(r.get("oracle_match")) for r in mode_rows),
                "mean_goal_satisfaction": mean(as_float(r.get("goal_satisfaction")) for r in mode_rows),
                "mean_selected_score": mean(as_float(r.get("selected_score")) for r in mode_rows),
                "mean_physical_feasibility": mean(as_float(r.get("physical_feasibility_score")) for r in mode_rows),
                "mean_symbolic_reliability": mean(as_float(r.get("symbolic_reliability_score")) for r in mode_rows),
                "mean_true_score": mean(as_float(r.get("true_score")) for r in mode_rows),
                "mean_regret": mean(as_float(r.get("regret")) for r in mode_rows),
            }
        )
    return output


def paired_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[str(row["comparison_id"])][str(row["mode"])] = row

    pairs = [pair for pair in grouped.values() if "single" in pair and "multi" in pair]

    def wins(metric_name: str) -> Tuple[int, int, int]:
        multi_wins = single_wins = ties = 0
        for pair in pairs:
            a = as_float(pair["multi"].get(metric_name))
            b = as_float(pair["single"].get(metric_name))
            if a is None or b is None:
                continue
            if a > b:
                multi_wins += 1
            elif b > a:
                single_wins += 1
            else:
                ties += 1
        return multi_wins, single_wins, ties

    out: Dict[str, Any] = {"paired_runs": len(pairs)}
    for metric_name in [
        "symbolic_success",
        "goal_satisfaction",
        "selected_score",
        "physical_feasibility_score",
        "true_score",
    ]:
        multi_wins, single_wins, ties = wins(metric_name)
        out[f"{metric_name}_multi_wins"] = multi_wins
        out[f"{metric_name}_single_wins"] = single_wins
        out[f"{metric_name}_ties"] = ties
    return out


def write_report(path: Path, args: argparse.Namespace, summary_rows: List[Dict[str, Any]], paired: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# GPT Single-BT Baseline vs Multi-BT Selector Report",
        "",
        "## Method",
        "",
        (
            "For each task/state/repeat pair, the single baseline asks GPT for one behavior tree. "
            "The proposed pipeline asks GPT for multiple candidate BTs, evaluates them with the existing "
            "KIOS/selector pipeline, and selects one candidate."
        ),
        "",
        f"- Generator: `{args.generator}`",
        f"- Model: `{args.model}`",
        f"- Cases: `{args.case_count}`",
        f"- Repeats: `{args.repeats}`",
        f"- Single candidate count: `1`",
        f"- Multi candidate count: `{args.multi_candidate_count}`",
        f"- Total GPT calls when `--mode both`: `{args.case_count * args.repeats * 2}`",
        "",
        "## Summary",
        "",
    ]
    if summary_rows:
        columns = list(summary_rows[0].keys())
        lines.append(",".join(columns))
        for row in summary_rows:
            lines.append(",".join("" if row.get(c) is None else str(row.get(c)) for c in columns))
    lines.extend(["", "## Paired Comparison", ""])
    for key, value in paired.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "Use symbolic and selector-score metrics as the fast evidence. If simulation columns are empty, "
                "the generated Isaac Gym jobs still need to be executed before making physical-success claims."
            ),
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generator", choices=["mock", "existing", "openai"], default="openai")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-5.4-mini"))
    parser.add_argument("--task-specs", type=Path, default=DEFAULT_TASK_SPECS)
    parser.add_argument("--case-count", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--multi-candidate-count", type=int, default=4)
    parser.add_argument("--timesteps", default="0,1,2,3,4,5,6,7,8,9")
    parser.add_argument("--mode", choices=["both", "single", "multi"], default="both")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--learned-dataset", type=Path, default=None)
    parser.add_argument("--model-dir", type=Path, default=None)
    parser.add_argument("--online-epochs", type=int, default=0)
    parser.add_argument("--force", action="store_true", help="Regenerate runs even if cached payloads exist.")
    parser.add_argument("--continue-on-error", action="store_true", help="Record failed demo runs and continue.")
    parser.add_argument("--dry-run", action="store_true", help="Only write the case manifest.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tasks = normalize_task_list(load_json(args.task_specs))
    timesteps = [int(x.strip()) for x in args.timesteps.split(",") if x.strip()]
    cases = build_cases(tasks, args.case_count, timesteps)
    if len(cases) < args.case_count:
        raise RuntimeError(f"Only built {len(cases)} cases from {args.task_specs}; requested {args.case_count}.")

    experiment_root = args.output_dir / f"{args.generator}_{args.model}_c{args.case_count}_r{args.repeats}_k{args.multi_candidate_count}"
    manifest = []
    for repeat in range(args.repeats):
        for case_index, case in enumerate(cases):
            comparison_id = f"{case['task_id']}__state_{case['timestep']:03d}_t{case['timestep']}__r{repeat:02d}"
            manifest.append({**case, "case_index": case_index, "repeat": repeat, "comparison_id": comparison_id})
    write_json(experiment_root / "case_manifest.json", manifest)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "result": "dry_run",
                    "manifest": str(experiment_root / "case_manifest.json"),
                    "cases": len(cases),
                    "repeats": args.repeats,
                    "planned_gpt_calls": len(manifest) * (2 if args.mode == "both" else 1),
                },
                indent=2,
            )
        )
        return

    modes = ["single", "multi"] if args.mode == "both" else [args.mode]
    selected_rows: List[Dict[str, Any]] = []
    candidate_rows: List[Dict[str, Any]] = []

    for item in manifest:
        for mode in modes:
            candidate_count = 1 if mode == "single" else args.multi_candidate_count
            run_dir = (
                experiment_root
                / f"repeat_{item['repeat']:02d}"
                / f"case_{item['case_index']:02d}_{item['task_id']}_t{item['timestep']}"
                / mode
            )
            try:
                payload = run_one_demo(
                    generator=args.generator,
                    model=args.model,
                    task_id=item["task_id"],
                    timestep=item["timestep"],
                    candidate_count=candidate_count,
                    run_dir=run_dir,
                    task_specs=args.task_specs,
                    learned_dataset=args.learned_dataset,
                    model_dir=args.model_dir,
                    online_epochs=args.online_epochs,
                    force=args.force,
                )
                selected, candidates = summarize_payload(
                    payload=payload,
                    comparison_id=item["comparison_id"],
                    mode=mode,
                    repeat=item["repeat"],
                    task_id=item["task_id"],
                    timestep=item["timestep"],
                    generator=args.generator,
                    model=args.model,
                    candidate_count_requested=candidate_count,
                    run_dir=run_dir,
                )
            except Exception as exc:
                if not args.continue_on_error:
                    raise
                selected = failed_selected_row(
                    comparison_id=item["comparison_id"],
                    mode=mode,
                    repeat=item["repeat"],
                    task_id=item["task_id"],
                    timestep=item["timestep"],
                    generator=args.generator,
                    model=args.model,
                    candidate_count_requested=candidate_count,
                    run_dir=run_dir,
                    error=exc,
                )
                candidates = []
            selected_rows.append(selected)
            candidate_rows.extend(candidates)
            print(
                json.dumps(
                    {
                        "mode": mode,
                        "comparison_id": item["comparison_id"],
                        "selected": selected["selected_candidate"],
                        "candidates": selected["candidate_count_returned"],
                    },
                    ensure_ascii=False,
                )
            )

    summary_rows = summarize_selected(selected_rows)
    paired = paired_summary(selected_rows)

    selected_output = args.results_dir / "single_vs_multi_gpt_baseline_selected.csv"
    candidate_output = args.results_dir / "single_vs_multi_gpt_baseline_candidates.csv"
    summary_output = args.results_dir / "single_vs_multi_gpt_baseline_summary.csv"
    report_output = args.results_dir / "single_vs_multi_gpt_baseline_report.md"
    paired_output = args.results_dir / "single_vs_multi_gpt_baseline_paired.json"

    write_csv(selected_output, selected_rows, SELECTED_COLUMNS)
    write_csv(candidate_output, candidate_rows, CANDIDATE_COLUMNS)
    write_csv(summary_output, summary_rows, list(summary_rows[0].keys()) if summary_rows else ["mode"])
    write_json(paired_output, paired)
    write_report(report_output, args, summary_rows, paired)

    print(
        json.dumps(
            {
                "result": "success",
                "selected_rows": len(selected_rows),
                "candidate_rows": len(candidate_rows),
                "paired_runs": paired.get("paired_runs"),
                "selected_output": str(selected_output),
                "candidate_output": str(candidate_output),
                "summary_output": str(summary_output),
                "report_output": str(report_output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
