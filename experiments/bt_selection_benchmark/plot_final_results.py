#!/usr/bin/env python3
"""Create final result tables and figures for the BT selection project."""

from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[2]
BT_RESULTS = ROOT / "experiments" / "bt_selection_benchmark" / "results"
GPT_RESULTS = ROOT / "experiments" / "gpt_candidate_demo" / "results"
OUT = BT_RESULTS / "final_visualizations"


BENCHMARK_FILES = [
    ("V1 supported-by", BT_RESULTS / "bt_candidate_evaluations_v1_supported_by_with_sim.csv"),
    ("V2 stacking probe", BT_RESULTS / "bt_candidate_evaluations_v2_stacking_probe_with_sim.csv"),
    ("V2B physical strategy", BT_RESULTS / "bt_candidate_evaluations_v2b_physical_strategy_with_sim.csv"),
    ("V6 hard cases", BT_RESULTS / "bt_candidate_evaluations_v6_hard_cases_with_sim.csv"),
]

SELECTOR_SUMMARY_FILES = [
    ("V1 supported-by", BT_RESULTS / "summary_by_selector_v1_supported_by_with_sim.csv"),
    ("V2 stacking probe", BT_RESULTS / "summary_by_selector_v2_stacking_probe_with_sim.csv"),
    ("V2B physical strategy", BT_RESULTS / "summary_by_selector_v2b_physical_strategy_with_sim.csv"),
    ("V6 hard cases", BT_RESULTS / "summary_by_selector_v6_hard_cases_with_sim.csv"),
    ("V4B transformer", BT_RESULTS / "v4b_transformer_selector_summary.csv"),
    ("V5 manual ensemble", BT_RESULTS / "v5_ensemble_selector_summary.csv"),
]

LEARNED_ABLATION = BT_RESULTS / "v5_learned_ensemble_ablation.csv"
LEARNED_WEIGHTS = BT_RESULTS / "v5_learned_ensemble_weights.csv"
GPT_SINGLE_MULTI = GPT_RESULTS / "single_vs_multi_gpt_baseline_summary.csv"


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, Any]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out):
        return None
    return out


def first(row: Dict[str, Any], names: Iterable[str], default: Any = "") -> Any:
    for name in names:
        if name in row and row[name] not in ("", None):
            return row[name]
    return default


def fmt(value: Any, digits: int = 3) -> str:
    x = number(value)
    if x is None:
        return ""
    return f"{x:.{digits}f}"


def safe_name(value: str) -> str:
    keep = []
    for char in value.lower():
        keep.append(char if char.isalnum() else "_")
    return "_".join("".join(keep).split("_")).strip("_")


def group_key(row: Dict[str, str]) -> Tuple[str, str]:
    return (
        str(first(row, ["task_id", "task", "task_name"], "")),
        str(first(row, ["initial_state_id", "initial_state", "state_id"], "")),
    )


def summarize_benchmarks() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for benchmark, path in BENCHMARK_FILES:
        data = read_csv(path)
        if not data:
            continue
        status = Counter(str(first(row, ["simulation_status", "sim_status"], "unknown")) for row in data)
        if set(status) == {"unknown"}:
            done = sum(1 for row in data if number(first(row, ["sim_success"], "")) is not None)
            skipped = sum(1 for row in data if str(first(row, ["candidate_type"], "")).lower() == "skipped")
            status = Counter({"done": done, "skipped": skipped})
        groups = {group_key(row) for row in data}
        sim_success_values = [number(first(row, ["sim_success"], "")) for row in data]
        sim_success_values = [x for x in sim_success_values if x is not None]
        symbolic_values = [number(first(row, ["symbolic_success"], "")) for row in data]
        symbolic_values = [x for x in symbolic_values if x is not None]
        rows.append(
            {
                "benchmark": benchmark,
                "file": str(path),
                "candidate_rows": len(data),
                "task_state_groups": len(groups),
                "sim_done": status.get("done", 0),
                "sim_skipped": status.get("skipped", 0),
                "sim_pending": status.get("pending", 0),
                "symbolic_success_rate": sum(1 for x in symbolic_values if x > 0) / len(symbolic_values)
                if symbolic_values
                else "",
                "sim_success_rate": sum(1 for x in sim_success_values if x > 0) / len(sim_success_values)
                if sim_success_values
                else "",
            }
        )
    return rows


def normalize_selector_summaries() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen = set()
    for source, path in SELECTOR_SUMMARY_FILES:
        for row in read_csv(path):
            selector = str(first(row, ["selector", "model", "method"], ""))
            if not selector:
                continue
            out = {
                "source": source,
                "selector": selector,
                "groups": first(row, ["groups", "n_groups", "runs"], ""),
                "success": first(row, ["success", "symbolic_success", "success_rate"], ""),
                "mean_selected_true_score": first(row, ["mean_selected_true_score", "true_score", "mean_score"], ""),
                "mean_regret": first(row, ["mean_regret", "regret"], ""),
                "pairwise_accuracy": first(row, ["pairwise_accuracy"], ""),
                "pairwise_roc_auc": first(row, ["pairwise_roc_auc", "roc_auc"], ""),
            }
            key = tuple(out.items())
            if key not in seen:
                seen.add(key)
                rows.append(out)
    return rows


def normalize_ablation() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in read_csv(LEARNED_ABLATION):
        name = str(first(row, ["selector", "ablation", "variant", "model", "method"], ""))
        if not name:
            continue
        rows.append(
            {
                "selector": name,
                "source": first(row, ["source", "test_source", "benchmark"], "learned_v5"),
                "groups": first(row, ["groups", "runs"], ""),
                "success": first(row, ["success", "success_rate"], ""),
                "mean_selected_true_score": first(row, ["mean_selected_true_score", "true_score"], ""),
                "mean_regret": first(row, ["mean_regret", "regret"], ""),
            }
        )
    return rows


def final_selector_table(selector_rows: List[Dict[str, Any]], ablation_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    preferred_sources = ["V5 manual ensemble", "V4B transformer", "V6 hard cases"]
    rows: List[Dict[str, Any]] = []
    for source in preferred_sources:
        rows.extend(row for row in selector_rows if row["source"] == source)

    learned_names = {
        "v5_learned_full",
        "v5_learned_no_simulation",
        "v5_no_simulation_reliability",
        "v5_no_transformer_votes",
        "v5_no_symbolic_reliability",
    }
    for row in ablation_rows:
        if str(row["selector"]) in learned_names or "learned" in str(row["selector"]):
            rows.append({**row, "pairwise_accuracy": "", "pairwise_roc_auc": ""})

    compact: List[Dict[str, Any]] = []
    seen = set()
    for row in rows:
        key = (row.get("source"), row.get("selector"))
        if key in seen:
            continue
        seen.add(key)
        compact.append(row)
    return compact


def import_matplotlib():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        return plt
    except Exception as exc:  # pragma: no cover - user-facing fallback
        raise RuntimeError("matplotlib is required to generate figures. Install python3-matplotlib.") from exc


def bar_plot(
    rows: List[Dict[str, Any]],
    *,
    label_col: str,
    value_col: str,
    title: str,
    ylabel: str,
    output: Path,
    top_n: int = 14,
) -> Optional[Path]:
    pairs = []
    for row in rows:
        value = number(row.get(value_col))
        label = str(row.get(label_col, ""))
        if value is not None and label:
            pairs.append((label, value))
    if not pairs:
        return None
    pairs = pairs[:top_n]
    labels, values = zip(*pairs)
    plt = import_matplotlib()
    width = max(8, min(16, 0.55 * len(labels) + 4))
    fig, ax = plt.subplots(figsize=(width, 4.8), dpi=160)
    colors = ["#2f6fbb" if "oracle" not in label.lower() else "#6b7280" for label in labels]
    ax.bar(range(len(labels)), values, color=colors)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)
    return output


def grouped_selector_plot(rows: List[Dict[str, Any]], value_col: str, title: str, ylabel: str, output: Path) -> Optional[Path]:
    filtered = [row for row in rows if number(row.get(value_col)) is not None]
    if not filtered:
        return None
    sources = []
    selectors = []
    values = defaultdict(dict)
    for row in filtered:
        source = str(row["source"])
        selector = str(row["selector"])
        sources.append(source)
        selectors.append(selector)
        values[source][selector] = number(row[value_col])
    sources = list(dict.fromkeys(sources))
    selectors = list(dict.fromkeys(selectors))
    if len(selectors) > 8:
        priority = ["feature_only", "transformer_only", "transformer_fused", "symbolic_only", "shortest_tree", "v5_ensemble", "oracle"]
        selectors = [s for s in priority if s in selectors] + [s for s in selectors if s not in priority][: max(0, 8 - len(priority))]

    plt = import_matplotlib()
    fig, ax = plt.subplots(figsize=(max(9, 1.3 * len(sources) + 4), 5.2), dpi=160)
    width = 0.8 / max(1, len(selectors))
    x = list(range(len(sources)))
    palette = ["#2f6fbb", "#38a169", "#b7791f", "#805ad5", "#e53e3e", "#4a5568", "#718096", "#0f766e"]
    for idx, selector in enumerate(selectors):
        offset = (idx - (len(selectors) - 1) / 2) * width
        ys = [values[source].get(selector, 0.0) for source in sources]
        ax.bar([i + offset for i in x], ys, width=width, label=selector, color=palette[idx % len(palette)])
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(sources, rotation=20, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)
    return output


def benchmark_coverage_plot(rows: List[Dict[str, Any]], output: Path) -> Optional[Path]:
    if not rows:
        return None
    plt = import_matplotlib()
    labels = [row["benchmark"] for row in rows]
    done = [number(row.get("sim_done")) or 0 for row in rows]
    skipped = [number(row.get("sim_skipped")) or 0 for row in rows]
    pending = [number(row.get("sim_pending")) or 0 for row in rows]
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=160)
    x = list(range(len(labels)))
    ax.bar(x, done, label="done", color="#2f6fbb")
    ax.bar(x, skipped, bottom=done, label="skipped", color="#a0aec0")
    bottoms = [a + b for a, b in zip(done, skipped)]
    ax.bar(x, pending, bottom=bottoms, label="pending", color="#e53e3e")
    ax.set_title("Simulation Coverage by Benchmark")
    ax.set_ylabel("candidate rows")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)
    return output


def write_markdown_report(
    path: Path,
    benchmark_rows: List[Dict[str, Any]],
    final_rows: List[Dict[str, Any]],
    ablation_rows: List[Dict[str, Any]],
    figures: List[Path],
) -> None:
    lines = [
        "# Final Experiment Results",
        "",
        "This folder contains consolidated tables and figures generated from the existing benchmark CSV files.",
        "",
        "## Dataset Coverage",
        "",
        "| Benchmark | Candidate rows | Task-state groups | Sim done | Sim skipped | Sim pending |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in benchmark_rows:
        lines.append(
            f"| {row['benchmark']} | {row['candidate_rows']} | {row['task_state_groups']} | "
            f"{row['sim_done']} | {row['sim_skipped']} | {row['sim_pending']} |"
        )
    lines.extend(
        [
            "",
            "## Final Selector Table",
            "",
            "| Source | Selector | Groups | Success | Mean true score | Mean regret | Pairwise acc. | ROC-AUC |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in final_rows:
        lines.append(
            f"| {row.get('source','')} | {row.get('selector','')} | {row.get('groups','')} | "
            f"{fmt(row.get('success'))} | {fmt(row.get('mean_selected_true_score'))} | "
            f"{fmt(row.get('mean_regret'))} | {fmt(row.get('pairwise_accuracy'))} | "
            f"{fmt(row.get('pairwise_roc_auc'))} |"
        )
    if ablation_rows:
        lines.extend(
            [
                "",
                "## Learned V5 Ablation",
                "",
                "| Variant | Source | Groups | Success | Mean true score | Mean regret |",
                "| --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in ablation_rows:
            lines.append(
                f"| {row.get('selector','')} | {row.get('source','')} | {row.get('groups','')} | "
                f"{fmt(row.get('success'))} | {fmt(row.get('mean_selected_true_score'))} | {fmt(row.get('mean_regret'))} |"
            )
    lines.extend(["", "## Figures", ""])
    for fig in figures:
        lines.append(f"- `{fig.name}`")
    if GPT_SINGLE_MULTI.exists():
        lines.extend(
            [
                "",
                "## GPT Single-vs-Multi Note",
                "",
                (
                    "A GPT single-vs-multi summary file exists, but it should only be used if API rate-limit "
                    "failures have been excluded or rerun successfully."
                ),
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    benchmark_rows = summarize_benchmarks()
    selector_rows = normalize_selector_summaries()
    ablation_rows = normalize_ablation()
    final_rows = final_selector_table(selector_rows, ablation_rows)

    write_csv(
        OUT / "final_dataset_coverage.csv",
        benchmark_rows,
        [
            "benchmark",
            "file",
            "candidate_rows",
            "task_state_groups",
            "sim_done",
            "sim_skipped",
            "sim_pending",
            "symbolic_success_rate",
            "sim_success_rate",
        ],
    )
    write_csv(
        OUT / "final_selector_comparison.csv",
        final_rows,
        [
            "source",
            "selector",
            "groups",
            "success",
            "mean_selected_true_score",
            "mean_regret",
            "pairwise_accuracy",
            "pairwise_roc_auc",
        ],
    )
    if ablation_rows:
        write_csv(
            OUT / "final_v5_learned_ablation.csv",
            ablation_rows,
            ["selector", "source", "groups", "success", "mean_selected_true_score", "mean_regret"],
        )
    if LEARNED_WEIGHTS.exists():
        weights = read_csv(LEARNED_WEIGHTS)
        if weights:
            write_csv(OUT / "final_v5_learned_weights.csv", weights, list(weights[0].keys()))
    if GPT_SINGLE_MULTI.exists():
        gpt_rows = read_csv(GPT_SINGLE_MULTI)
        if gpt_rows:
            write_csv(OUT / "final_gpt_single_vs_multi_summary.csv", gpt_rows, list(gpt_rows[0].keys()))

    figures: List[Path] = []
    for fig in [
        benchmark_coverage_plot(benchmark_rows, OUT / "fig_dataset_simulation_coverage.png"),
        grouped_selector_plot(selector_rows, "success", "Selector Success Rate Across Benchmarks", "success rate", OUT / "fig_selector_success_by_benchmark.png"),
        grouped_selector_plot(selector_rows, "mean_regret", "Selector Mean Regret Across Benchmarks", "mean regret", OUT / "fig_selector_regret_by_benchmark.png"),
        bar_plot(final_rows, label_col="selector", value_col="mean_regret", title="Final Selector Mean Regret", ylabel="mean regret", output=OUT / "fig_final_selector_regret.png"),
        bar_plot(final_rows, label_col="selector", value_col="success", title="Final Selector Success Rate", ylabel="success rate", output=OUT / "fig_final_selector_success.png"),
        bar_plot(ablation_rows, label_col="selector", value_col="mean_regret", title="Learned V5 Ablation: Mean Regret", ylabel="mean regret", output=OUT / "fig_v5_ablation_regret.png"),
        bar_plot(ablation_rows, label_col="selector", value_col="success", title="Learned V5 Ablation: Success Rate", ylabel="success rate", output=OUT / "fig_v5_ablation_success.png"),
    ]:
        if fig is not None:
            figures.append(fig)

    write_markdown_report(OUT / "final_results_report.md", benchmark_rows, final_rows, ablation_rows, figures)

    print(
        {
            "result": "success",
            "output_dir": str(OUT),
            "dataset_rows": len(benchmark_rows),
            "selector_rows": len(final_rows),
            "ablation_rows": len(ablation_rows),
            "figures": [str(fig) for fig in figures],
            "report": str(OUT / "final_results_report.md"),
        }
    )


if __name__ == "__main__":
    main()
