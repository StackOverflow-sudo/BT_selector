#!/usr/bin/env python3
"""Generate enhanced final figures for the BT selector experiments.

This script is intentionally independent from plot_final_results.py so the
basic figure pack remains reproducible. It reads the consolidated CSVs created
by plot_final_results.py when available, and falls back to source result files.
"""

from __future__ import annotations

import csv
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "experiments" / "bt_selection_benchmark" / "results"
OUT = RESULTS / "final_visualizations"

BENCHMARK_FILES = [
    ("V1 supported-by", RESULTS / "bt_candidate_evaluations_v1_supported_by_with_sim.csv"),
    ("V2 stacking probe", RESULTS / "bt_candidate_evaluations_v2_stacking_probe_with_sim.csv"),
    ("V2B physical strategy", RESULTS / "bt_candidate_evaluations_v2b_physical_strategy_with_sim.csv"),
    ("V6 hard cases", RESULTS / "bt_candidate_evaluations_v6_hard_cases_with_sim.csv"),
]

SUMMARY_FILES = [
    ("V1 supported-by", RESULTS / "summary_by_selector_v1_supported_by_with_sim.csv"),
    ("V2 stacking probe", RESULTS / "summary_by_selector_v2_stacking_probe_with_sim.csv"),
    ("V2B physical strategy", RESULTS / "summary_by_selector_v2b_physical_strategy_with_sim.csv"),
    ("V6 hard cases", RESULTS / "summary_by_selector_v6_hard_cases_with_sim.csv"),
    ("V4B transformer", RESULTS / "v4b_transformer_selector_summary.csv"),
    ("V5 manual ensemble", RESULTS / "v5_ensemble_selector_summary.csv"),
]

ABLATION = RESULTS / "v5_learned_ensemble_ablation.csv"
WEIGHTS = RESULTS / "v5_learned_ensemble_weights.csv"


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
        writer.writerows(rows)


def num(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(out) else out


def first(row: Dict[str, Any], names: Iterable[str], default: Any = "") -> Any:
    for name in names:
        if name in row and row[name] not in ("", None):
            return row[name]
    return default


def short_selector(name: str) -> str:
    return (
        name.replace("rule_based_", "rule_")
        .replace("transformer_", "trans_")
        .replace("v5_learned_", "learned_")
        .replace("v5_no_", "no_")
    )


def plt_module():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def selector_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for source, path in SUMMARY_FILES:
        for row in read_csv(path):
            selector = str(first(row, ["selector", "method", "model"], ""))
            if not selector:
                continue
            rows.append(
                {
                    "source": source,
                    "selector": selector,
                    "groups": first(row, ["groups", "runs"], ""),
                    "success": first(row, ["success", "success_rate", "symbolic_success"], ""),
                    "true_score": first(row, ["mean_selected_true_score", "true_score", "mean_score"], ""),
                    "regret": first(row, ["mean_regret", "regret"], ""),
                    "pairwise_accuracy": first(row, ["pairwise_accuracy"], ""),
                    "roc_auc": first(row, ["pairwise_roc_auc", "roc_auc"], ""),
                }
            )
    return rows


def ablation_rows() -> List[Dict[str, Any]]:
    rows = []
    for row in read_csv(ABLATION):
        selector = str(first(row, ["selector", "variant", "method", "model"], ""))
        if selector:
            rows.append(
                {
                    "selector": selector,
                    "source": first(row, ["source", "benchmark", "test_source"], "learned_v5"),
                    "groups": first(row, ["groups", "runs"], ""),
                    "success": first(row, ["success", "success_rate"], ""),
                    "true_score": first(row, ["mean_selected_true_score", "true_score"], ""),
                    "regret": first(row, ["mean_regret", "regret"], ""),
                }
            )
    return rows


def coverage_rows() -> List[Dict[str, Any]]:
    rows = []
    for name, path in BENCHMARK_FILES:
        data = read_csv(path)
        if not data:
            continue
        groups = {(first(r, ["task_id"], ""), first(r, ["initial_state_id"], "")) for r in data}
        counts = Counter()
        for row in data:
            sim = num(first(row, ["sim_success"], ""))
            status = str(first(row, ["simulation_status", "sim_status"], "")).lower()
            ctype = str(first(row, ["candidate_type"], "")).lower()
            if sim is not None:
                counts["sim_success" if sim > 0 else "sim_failure"] += 1
            elif status == "skipped" or ctype == "skipped":
                counts["skipped"] += 1
            else:
                counts["pending_or_missing"] += 1
        rows.append(
            {
                "benchmark": name,
                "groups": len(groups),
                "candidate_rows": len(data),
                "sim_success": counts["sim_success"],
                "sim_failure": counts["sim_failure"],
                "skipped": counts["skipped"],
                "pending_or_missing": counts["pending_or_missing"],
            }
        )
    return rows


def selector_matrix(rows: List[Dict[str, Any]], value_key: str) -> Tuple[List[str], List[str], List[List[Optional[float]]]]:
    sources = list(dict.fromkeys(str(r["source"]) for r in rows if num(r.get(value_key)) is not None))
    priority = [
        "feature_only",
        "transformer_only",
        "transformer_fused",
        "symbolic_only",
        "shortest_tree",
        "rule_based",
        "v5_ensemble",
        "oracle",
    ]
    all_selectors = list(dict.fromkeys(str(r["selector"]) for r in rows if num(r.get(value_key)) is not None))
    selectors = [s for s in priority if s in all_selectors]
    selectors.extend([s for s in all_selectors if s not in selectors][: max(0, 12 - len(selectors))])
    lookup = {(str(r["source"]), str(r["selector"])): num(r.get(value_key)) for r in rows}
    matrix = [[lookup.get((source, selector)) for source in sources] for selector in selectors]
    return sources, selectors, matrix


def heatmap(rows: List[Dict[str, Any]], value_key: str, title: str, output: Path, cmap: str) -> Optional[Path]:
    sources, selectors, matrix = selector_matrix(rows, value_key)
    if not sources or not selectors or not any(v is not None for line in matrix for v in line):
        return None
    plt = plt_module()
    fig, ax = plt.subplots(figsize=(max(9, 1.2 * len(sources) + 3), max(5, 0.42 * len(selectors) + 2)), dpi=170)
    image_data = [[float("nan") if v is None else v for v in line] for line in matrix]
    im = ax.imshow(image_data, aspect="auto", cmap=cmap)
    ax.set_title(title)
    ax.set_xticks(range(len(sources)))
    ax.set_xticklabels(sources, rotation=25, ha="right")
    ax.set_yticks(range(len(selectors)))
    ax.set_yticklabels([short_selector(s) for s in selectors])
    for y, line in enumerate(matrix):
        for x, value in enumerate(line):
            if value is not None:
                ax.text(x, y, f"{value:.2f}", ha="center", va="center", color="white", fontsize=7)
    fig.colorbar(im, ax=ax, shrink=0.82)
    fig.tight_layout()
    fig.savefig(output)
    plt.close(fig)
    return output


def outcome_stacked(rows: List[Dict[str, Any]], output: Path) -> Optional[Path]:
    if not rows:
        return None
    plt = plt_module()
    labels = [r["benchmark"] for r in rows]
    fields = [
        ("sim_success", "#2f855a", "sim success"),
        ("sim_failure", "#c53030", "sim failure"),
        ("skipped", "#a0aec0", "skipped"),
        ("pending_or_missing", "#d69e2e", "pending/missing"),
    ]
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=170)
    x = list(range(len(labels)))
    bottom = [0.0] * len(labels)
    for key, color, label in fields:
        vals = [num(r.get(key)) or 0 for r in rows]
        ax.bar(x, vals, bottom=bottom, color=color, label=label)
        bottom = [a + b for a, b in zip(bottom, vals)]
    for i, total in enumerate(bottom):
        ax.text(i, total + max(bottom) * 0.015, str(int(total)), ha="center", fontsize=8)
    ax.set_title("Candidate Simulation Outcomes by Benchmark")
    ax.set_ylabel("candidate BT rows")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.legend(ncol=2, fontsize=8)
    ax.grid(axis="y", alpha=0.22)
    fig.tight_layout()
    fig.savefig(output)
    plt.close(fig)
    return output


def tradeoff(rows: List[Dict[str, Any]], output: Path) -> Optional[Path]:
    data = [r for r in rows if num(r.get("success")) is not None and num(r.get("regret")) is not None]
    if not data:
        return None
    plt = plt_module()
    palette = ["#2f6fbb", "#38a169", "#b7791f", "#805ad5", "#c53030", "#4a5568"]
    colors: Dict[str, str] = {}
    fig, ax = plt.subplots(figsize=(10, 6), dpi=170)
    for row in data:
        source = str(row["source"])
        colors.setdefault(source, palette[len(colors) % len(palette)])
        x = num(row["regret"]) or 0
        y = num(row["success"]) or 0
        size = max(50, min(420, (num(row.get("groups")) or 30) * 2.2))
        ax.scatter(x, y, s=size, color=colors[source], alpha=0.75, edgecolor="white", linewidth=0.8)
        ax.text(x, y, short_selector(str(row["selector"])), fontsize=7, ha="left", va="bottom")
    ax.set_title("Selector Trade-off: Success Rate vs Mean Regret")
    ax.set_xlabel("mean regret, lower is better")
    ax.set_ylabel("success rate, higher is better")
    ax.grid(alpha=0.25)
    handles = [plt.Line2D([0], [0], marker="o", linestyle="", color=c, label=s) for s, c in colors.items()]
    ax.legend(handles=handles, fontsize=8)
    fig.tight_layout()
    fig.savefig(output)
    plt.close(fig)
    return output


def ablation_dual(rows: List[Dict[str, Any]], output: Path) -> Optional[Path]:
    data = [r for r in rows if num(r.get("regret")) is not None or num(r.get("success")) is not None]
    if not data:
        return None
    plt = plt_module()
    labels = [short_selector(str(r["selector"])) for r in data]
    regrets = [num(r.get("regret")) or 0 for r in data]
    successes = [num(r.get("success")) for r in data]
    fig, ax1 = plt.subplots(figsize=(max(10, 0.7 * len(labels) + 3), 5.4), dpi=170)
    x = list(range(len(labels)))
    ax1.bar(x, regrets, color="#2f6fbb", alpha=0.82, label="mean regret")
    ax1.set_ylabel("mean regret")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=35, ha="right")
    ax1.grid(axis="y", alpha=0.22)
    ax2 = ax1.twinx()
    if any(v is not None for v in successes):
        ax2.plot(x, [0 if v is None else v for v in successes], color="#c53030", marker="o", label="success")
    ax2.set_ylabel("success rate")
    ax1.set_title("Learned V5 Ablation: Regret and Success")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, fontsize=8)
    fig.tight_layout()
    fig.savefig(output)
    plt.close(fig)
    return output


def weights_plot(output: Path) -> Optional[Path]:
    rows = read_csv(WEIGHTS)
    if not rows:
        return None
    cols = list(rows[0].keys())
    name_col = next((c for c in cols if c.lower() in {"feature", "name", "component", "selector"}), cols[0])
    weight_col = next((c for c in cols if c.lower() in {"weight", "coef", "coefficient", "value"}), None)
    if weight_col is None:
        numeric = [c for c in cols if any(num(r.get(c)) is not None for r in rows)]
        if not numeric:
            return None
        weight_col = numeric[0]
    pairs = [(str(r.get(name_col, "")), num(r.get(weight_col))) for r in rows]
    pairs = [(n, v) for n, v in pairs if n and v is not None]
    if not pairs:
        return None
    pairs.sort(key=lambda item: abs(item[1]), reverse=True)
    pairs = list(reversed(pairs[:18]))
    plt = plt_module()
    fig, ax = plt.subplots(figsize=(9.5, max(5, 0.32 * len(pairs) + 2)), dpi=170)
    labels = [p[0] for p in pairs]
    values = [p[1] for p in pairs]
    colors = ["#2f855a" if v >= 0 else "#c53030" for v in values]
    ax.barh(range(len(labels)), values, color=colors)
    ax.axvline(0, color="#111827", linewidth=0.8)
    ax.set_title("Learned V5 Feature Weights")
    ax.set_xlabel("weight")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.grid(axis="x", alpha=0.22)
    fig.tight_layout()
    fig.savefig(output)
    plt.close(fig)
    return output


def dashboard(cov: List[Dict[str, Any]], selectors: List[Dict[str, Any]], abl: List[Dict[str, Any]], output: Path) -> Optional[Path]:
    if not cov and not selectors and not abl:
        return None
    plt = plt_module()
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 8.4), dpi=170)
    axes = axes.ravel()
    if cov:
        labels = [r["benchmark"] for r in cov]
        success = [num(r.get("sim_success")) or 0 for r in cov]
        failure = [num(r.get("sim_failure")) or 0 for r in cov]
        axes[0].bar(range(len(labels)), success, color="#2f855a", label="success")
        axes[0].bar(range(len(labels)), failure, bottom=success, color="#c53030", label="failure")
        axes[0].set_title("Simulation Outcomes")
        axes[0].set_xticks(range(len(labels)))
        axes[0].set_xticklabels(labels, rotation=25, ha="right", fontsize=8)
        axes[0].legend(fontsize=8)
        axes[0].grid(axis="y", alpha=0.2)
    final = [r for r in selectors if num(r.get("regret")) is not None][:10]
    if final:
        labels = [short_selector(str(r["selector"])) for r in final]
        axes[1].bar(range(len(labels)), [num(r["regret"]) or 0 for r in final], color="#805ad5")
        axes[1].set_title("Selector Mean Regret")
        axes[1].set_xticks(range(len(labels)))
        axes[1].set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
        axes[1].grid(axis="y", alpha=0.2)
    final_success = [r for r in selectors if num(r.get("success")) is not None][:10]
    if final_success:
        labels = [short_selector(str(r["selector"])) for r in final_success]
        vals = [num(r["success"]) or 0 for r in final_success]
        axes[2].bar(range(len(labels)), vals, color="#38a169")
        axes[2].set_title("Selector Success Rate")
        axes[2].set_ylim(0, max(1.0, max(vals) * 1.15))
        axes[2].set_xticks(range(len(labels)))
        axes[2].set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
        axes[2].grid(axis="y", alpha=0.2)
    abl_regret = [r for r in abl if num(r.get("regret")) is not None][:10]
    if abl_regret:
        labels = [short_selector(str(r["selector"])) for r in abl_regret]
        axes[3].bar(range(len(labels)), [num(r["regret"]) or 0 for r in abl_regret], color="#b7791f")
        axes[3].set_title("V5 Ablation Regret")
        axes[3].set_xticks(range(len(labels)))
        axes[3].set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
        axes[3].grid(axis="y", alpha=0.2)
    fig.suptitle("BT Selection Final Experiment Dashboard", y=0.995)
    fig.tight_layout()
    fig.savefig(output)
    plt.close(fig)
    return output


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    selectors = selector_rows()
    abl = ablation_rows()
    cov = coverage_rows()
    write_csv(
        OUT / "enhanced_candidate_simulation_outcomes.csv",
        cov,
        ["benchmark", "groups", "candidate_rows", "sim_success", "sim_failure", "skipped", "pending_or_missing"],
    )

    figures = []
    for fig in [
        dashboard(cov, selectors, abl, OUT / "fig_final_dashboard.png"),
        heatmap(selectors, "success", "Selector Success Heatmap", OUT / "fig_selector_success_heatmap.png", "viridis"),
        heatmap(selectors, "regret", "Selector Mean Regret Heatmap", OUT / "fig_selector_regret_heatmap.png", "magma_r"),
        outcome_stacked(cov, OUT / "fig_candidate_simulation_outcomes.png"),
        tradeoff(selectors, OUT / "fig_success_regret_tradeoff.png"),
        ablation_dual(abl, OUT / "fig_v5_ablation_dual_axis.png"),
        weights_plot(OUT / "fig_v5_learned_weights.png"),
    ]:
        if fig is not None:
            figures.append(fig)

    report = OUT / "enhanced_visualization_report.md"
    report.write_text(
        "# Enhanced Final Visualizations\n\n"
        + "Generated enhanced figures for thesis and presentation use.\n\n"
        + "\n".join(f"- `{fig.name}`" for fig in figures)
        + "\n",
        encoding="utf-8",
    )

    print(
        {
            "result": "success",
            "output_dir": str(OUT),
            "figures": [str(fig) for fig in figures],
            "report": str(report),
        }
    )


if __name__ == "__main__":
    main()
