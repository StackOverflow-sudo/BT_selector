#!/usr/bin/env python3
"""Create a designed 16:9 academic defense PDF.

The output is a PDF slide deck generated with matplotlib vector primitives.
It is intended as a visual/content reference for building the final PPT.
"""

from __future__ import annotations

import argparse
import csv
import math
import textwrap
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / "experiments" / "bt_selection_benchmark" / "results" / "final_visualizations"
DEFAULT_OUTPUT = ROOT / "pptx" / "bt_selector_defense_reference_academic_design.pdf"

NAVY = "#0f172a"
BLUE = "#2563eb"
CYAN = "#0891b2"
GREEN = "#16a34a"
AMBER = "#d97706"
RED = "#dc2626"
PURPLE = "#7c3aed"
SLATE = "#475569"
MUTED = "#64748b"
LINE = "#cbd5e1"
PALE = "#f8fafc"
WHITE = "#ffffff"


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def num(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(out) else out


def first(row: Dict[str, Any], names: Iterable[str], default: str = "") -> str:
    for name in names:
        if name in row and row[name] not in ("", None):
            return str(row[name])
    return default


def short(name: str) -> str:
    return (
        name.replace("v5_learned_", "Learned ")
        .replace("v5_no_", "No ")
        .replace("transformer_", "Transformer ")
        .replace("feature_only", "Feature-only")
        .replace("symbolic_only", "Symbolic-only")
        .replace("shortest_tree", "Shortest-tree")
        .replace("v5_ensemble", "Manual V5")
        .replace("oracle", "Oracle")
        .replace("_", " ")
    )


def wrap(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def setup_ax():
    fig = plt.figure(figsize=(16, 9), dpi=140)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 1, 1, facecolor=PALE, edgecolor="none"))
    ax.add_patch(Circle((0.93, 0.9), 0.24, facecolor="#dbeafe", edgecolor="none", alpha=0.65))
    ax.add_patch(Circle((0.08, 0.08), 0.18, facecolor="#ede9fe", edgecolor="none", alpha=0.55))
    return fig, ax


def title(ax, text: str, subtitle: str = ""):
    ax.text(0.055, 0.91, text, fontsize=26, fontweight="bold", color=NAVY, va="top")
    if subtitle:
        ax.text(0.057, 0.852, subtitle, fontsize=11, color=MUTED, va="top")
    ax.add_patch(Rectangle((0.055, 0.817), 0.89, 0.006, facecolor=BLUE, edgecolor="none"))


def footer(ax, label: str, page: int):
    ax.text(0.055, 0.035, label, fontsize=7.5, color=MUTED)
    ax.text(0.945, 0.035, str(page), fontsize=7.5, color=MUTED, ha="right")


def card(ax, x, y, w, h, head, body, color=BLUE):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.018", facecolor=WHITE, edgecolor=LINE, linewidth=0.9))
    ax.add_patch(Rectangle((x, y), 0.006, h, facecolor=color, edgecolor="none"))
    ax.text(x + 0.022, y + h - 0.048, head, fontsize=13, fontweight="bold", color=color, va="top")
    ax.text(x + 0.022, y + h - 0.095, wrap(body, max(24, int(w * 95))), fontsize=9.2, color=SLATE, va="top", linespacing=1.25)


def bullet_list(ax, items: Sequence[str], x, y, size=12, width=90, color=NAVY):
    yy = y
    for item in items:
        ax.text(x, yy, u"\u2022", fontsize=size + 3, color=BLUE, va="top")
        wrapped = wrap(item, width)
        ax.text(x + 0.022, yy, wrapped, fontsize=size, color=color, va="top", linespacing=1.25)
        yy -= 0.04 * (wrapped.count("\n") + 1) + 0.018


def step(ax, x, y, w, h, text, color="#eff6ff"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.014", facecolor=color, edgecolor=LINE, linewidth=0.9))
    ax.text(x + w / 2, y + h / 2, text, fontsize=10.5, color=NAVY, ha="center", va="center", fontweight="bold")


def arrow(ax, x1, y1, x2, y2, color=BLUE):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=16, linewidth=1.8, color=color))


def table(ax, x, y, w, h, headers: Sequence[str], rows: Sequence[Sequence[str]], col_widths: Optional[Sequence[float]] = None, font=8.2):
    nrows = len(rows) + 1
    ncols = len(headers)
    if col_widths is None:
        col_widths = [1 / ncols] * ncols
    total = sum(col_widths)
    col_widths = [c / total for c in col_widths]
    row_h = h / nrows
    xx = x
    for c, head in enumerate(headers):
        cw = w * col_widths[c]
        ax.add_patch(Rectangle((xx, y + h - row_h), cw, row_h, facecolor=NAVY, edgecolor=WHITE, linewidth=0.8))
        ax.text(xx + 0.008, y + h - row_h / 2, head, fontsize=font, color=WHITE, va="center", fontweight="bold")
        xx += cw
    for r, row in enumerate(rows):
        yy = y + h - row_h * (r + 2)
        xx = x
        for c, value in enumerate(row):
            cw = w * col_widths[c]
            ax.add_patch(Rectangle((xx, yy), cw, row_h, facecolor=WHITE if r % 2 == 0 else "#f1f5f9", edgecolor=LINE, linewidth=0.55))
            ax.text(xx + 0.008, yy + row_h / 2, wrap(str(value), max(10, int(cw * 100))), fontsize=font - 0.2, color=NAVY, va="center")
            xx += cw


def bar_chart(ax, x, y, w, h, rows: Sequence[Tuple[str, float]], label: str, color=BLUE, lower_is_better=False):
    ax.text(x, y + h + 0.02, label, fontsize=12, fontweight="bold", color=NAVY)
    if not rows:
        ax.text(x, y + h / 2, "No data available", fontsize=11, color=MUTED)
        return
    max_v = max(v for _, v in rows) or 1
    row_h = h / len(rows)
    label_w = w * 0.42
    for i, (name, value) in enumerate(rows):
        yy = y + h - row_h * (i + 1)
        ax.text(x, yy + row_h * 0.53, short(name), fontsize=7.5, color=NAVY, va="center")
        ax.add_patch(Rectangle((x + label_w, yy + row_h * 0.30), w - label_w - 0.05, row_h * 0.35, facecolor="#e2e8f0", edgecolor="none"))
        ratio = value / max_v
        c = color
        if lower_is_better:
            c = GREEN if ratio < 0.25 else AMBER if ratio < 0.65 else RED
        ax.add_patch(Rectangle((x + label_w, yy + row_h * 0.30), max(0.003, (w - label_w - 0.05) * ratio), row_h * 0.35, facecolor=c, edgecolor="none"))
        ax.text(x + w - 0.04, yy + row_h * 0.53, f"{value:.2f}", fontsize=7.2, color=SLATE, ha="right", va="center")


def heatmap(ax, x, y, w, h, cols: Sequence[str], rows: Sequence[Tuple[str, Sequence[Optional[float]]]], label: str, lower_is_better=False):
    ax.text(x, y + h + 0.02, label, fontsize=12, fontweight="bold", color=NAVY)
    values = [v for _, vals in rows for v in vals if v is not None]
    if not values:
        return
    mn, mx = min(values), max(values)
    label_w = w * 0.34
    cell_w = (w - label_w) / max(1, len(cols))
    cell_h = h / (len(rows) + 1)
    for c, col in enumerate(cols):
        ax.text(x + label_w + c * cell_w + cell_w / 2, y + h - cell_h / 2, col, fontsize=7.3, color=SLATE, ha="center", va="center", fontweight="bold")
    for r, (name, vals) in enumerate(rows):
        yy = y + h - cell_h * (r + 2)
        ax.text(x, yy + cell_h / 2, short(name), fontsize=7.0, color=NAVY, va="center")
        for c, value in enumerate(vals):
            xx = x + label_w + c * cell_w
            if value is None:
                face = "#e2e8f0"
            else:
                t = 0.5 if mx == mn else (value - mn) / (mx - mn)
                if lower_is_better:
                    t = 1 - t
                face = (1 - t, 0.90 + 0.08 * t, 0.88 - 0.45 * t)
            ax.add_patch(Rectangle((xx, yy), cell_w, cell_h, facecolor=face, edgecolor=WHITE, linewidth=0.7))
            if value is not None:
                ax.text(xx + cell_w / 2, yy + cell_h / 2, f"{value:.2f}", fontsize=6.7, color=NAVY, ha="center", va="center", fontweight="bold")


def selector_rows():
    return read_csv(FINAL / "final_selector_comparison.csv")


def ablation_rows():
    return read_csv(FINAL / "final_v5_learned_ablation.csv")


def outcome_rows():
    rows = read_csv(FINAL / "enhanced_candidate_simulation_outcomes.csv")
    if not rows:
        rows = read_csv(FINAL / "final_dataset_coverage.csv")
    return rows


def selector_matrix(metric: str):
    sources = [
        ("V1", "summary_by_selector_v1_supported_by_with_sim.csv"),
        ("V2", "summary_by_selector_v2_stacking_probe_with_sim.csv"),
        ("V2B", "summary_by_selector_v2b_physical_strategy_with_sim.csv"),
        ("V6", "summary_by_selector_v6_hard_cases_with_sim.csv"),
        ("V4B", "v4b_transformer_selector_summary.csv"),
        ("V5", "v5_ensemble_selector_summary.csv"),
    ]
    triples = []
    for source, fname in sources:
        for row in read_csv(ROOT / "experiments" / "bt_selection_benchmark" / "results" / fname):
            selector = first(row, ["selector"])
            value = first(row, [metric, "mean_regret" if metric == "regret" else "success"])
            triples.append((source, selector, num(value)))
    cols = list(dict.fromkeys(t[0] for t in triples))
    priority = ["feature_only", "transformer_only", "transformer_fused", "symbolic_only", "shortest_tree", "rule_based", "v5_ensemble", "oracle"]
    all_selectors = list(dict.fromkeys(t[1] for t in triples if t[2] is not None))
    selectors = [s for s in priority if s in all_selectors]
    selectors.extend([s for s in all_selectors if s not in selectors][: max(0, 10 - len(selectors))])
    lookup = {(src, sel): val for src, sel, val in triples}
    return cols, [(sel, [lookup.get((col, sel)) for col in cols]) for sel in selectors]


def add_title_page(pdf, args):
    fig, ax = setup_ax()
    ax.text(0.055, 0.74, "KIOS + Transformer\nBehavior Tree Selector", fontsize=36, fontweight="bold", color=NAVY, va="top", linespacing=1.04)
    ax.text(0.058, 0.565, "A multi-candidate behavior tree selection system for robot task planning", fontsize=15, color=BLUE, fontweight="bold")
    card(ax, 0.055, 0.33, 0.38, 0.14, "Core idea", "Generate multiple BTs, evaluate them symbolically, encode structure, and select the most reliable candidate.", BLUE)
    card(ax, 0.465, 0.33, 0.38, 0.14, "Final method", "V5 learned ensemble combining selector agreement, symbolic reliability, and physical reliability.", PURPLE)
    ax.text(0.058, 0.14, f"{args.author}\n{args.department}\n{args.date}", fontsize=11, color=SLATE, va="top")
    footer(ax, "Academic defense reference PDF - vector layout", 1)
    pdf.savefig(fig)
    plt.close(fig)


def build_pdf(args):
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sels = selector_rows()
    abls = ablation_rows()
    outs = outcome_rows()
    with PdfPages(args.output) as pdf:
        add_title_page(pdf, args)

        fig, ax = setup_ax(); title(ax, "1. Research Context", "Why behavior tree selection matters for robot task planning")
        card(ax, 0.06, 0.58, 0.27, 0.17, "LLM-based planning", "LLMs can generate high-level task plans, but raw plans require grounding, validation, and repair before execution.", BLUE)
        card(ax, 0.365, 0.58, 0.27, 0.17, "Behavior Trees", "BTs provide modular and interpretable execution logic, making them suitable for robot task execution and monitoring.", GREEN)
        card(ax, 0.67, 0.58, 0.27, 0.17, "Physical executability", "Symbolic goal satisfaction does not guarantee stable placement, contact behavior, or low displacement.", AMBER)
        table(ax, 0.06, 0.20, 0.88, 0.27, ["Challenge", "Why it appears", "Project response"], [
            ["Invalid BT nodes", "LLM output may not match action vocabulary", "Restrict schema and validate with KIOS"],
            ["Symbolic-physical gap", "Relations do not imply stable execution", "Use Isaac Gym and physical reliability"],
            ["Multiple plausible plans", "Several BTs can satisfy one task", "Rank candidates with learned V5 selector"],
        ], [0.23, 0.34, 0.43], 7.7)
        footer(ax, "Research context", 2); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax(); title(ax, "2. Literature Basis", "The system combines BT planning, relational dynamics, and Transformer sequence representation")
        table(ax, 0.06, 0.34, 0.88, 0.40, ["Paper / Direction", "Key idea", "Role in this project"], [
            ["LLM-as-BT-Planner", "Generate BTs from language instructions", "Motivates LLM-to-BT candidate generation"],
            ["Points2Plans", "Relational dynamics for long-horizon plans", "Motivates object-relation benchmark design"],
            ["MuST", "Transformer over skill sequences", "Motivates token-based BT representation"],
            ["Hypergraph Transformer", "High-order interaction modeling", "Future graph/hypergraph selector extension"],
            ["BT robotics literature", "Modular and reactive execution", "Supports BT as execution representation"],
        ], [0.25, 0.33, 0.42], 7.6)
        bullet_list(ax, ["This project is not a direct reproduction of one paper.", "The contribution is a selector pipeline that uses symbolic, structural, and physical evidence."], 0.08, 0.22, 11.5, 104)
        footer(ax, "References and positioning", 3); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax(); title(ax, "3. Problem Formulation", "Select one reliable BT from a candidate set")
        step(ax, 0.07, 0.56, 0.15, 0.08, "Task I"); step(ax, 0.07, 0.44, 0.15, 0.08, "State S0")
        step(ax, 0.30, 0.50, 0.19, 0.10, "Candidate Set\nC={c1,...,cn}", "#eff6ff")
        step(ax, 0.58, 0.50, 0.16, 0.10, "Score\nF(I,S0,ci)", "#f5f3ff")
        step(ax, 0.81, 0.50, 0.13, 0.10, "Selected BT\nc*", "#dcfce7")
        arrow(ax, 0.22, 0.60, 0.30, 0.56); arrow(ax, 0.22, 0.48, 0.30, 0.54); arrow(ax, 0.49, 0.55, 0.58, 0.55); arrow(ax, 0.74, 0.55, 0.81, 0.55)
        ax.text(0.20, 0.35, "c* = argmax_i F(I, S0, ci)", fontsize=23, color=BLUE, fontweight="bold")
        bullet_list(ax, ["The target is group-wise selection, not isolated BT classification.", "Regret measures the quality gap between selected candidate and oracle.", "A BT can be symbolically successful but physically unstable."], 0.08, 0.24, 12, 95)
        footer(ax, "Problem definition", 4); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax(); title(ax, "4. System Architecture", "Candidate generation, symbolic evaluation, learned selection, and simulation validation")
        labels = ["Task + State", "BT Candidates", "KIOS Metrics", "BT Encoder", "V5 Selector", "Selected BT"]
        xs = [0.055, 0.215, 0.375, 0.535, 0.695, 0.855]
        for x, lab in zip(xs, labels):
            step(ax, x, 0.57, 0.115, 0.08, lab)
        for i in range(len(xs)-1):
            arrow(ax, xs[i]+0.115, 0.61, xs[i+1], 0.61)
        step(ax, 0.655, 0.39, 0.15, 0.08, "Isaac Gym\nValidation", "#fff7ed")
        arrow(ax, 0.91, 0.57, 0.75, 0.47, AMBER)
        card(ax, 0.08, 0.20, 0.38, 0.13, "Low-cost symbolic screening", "KIOS checks executability before simulation-heavy validation.", GREEN)
        card(ax, 0.54, 0.20, 0.38, 0.13, "Multi-source selector", "V5 combines model agreement, symbolic reliability, and physical reliability.", PURPLE)
        footer(ax, "Pipeline overview", 5); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax(); title(ax, "5. Method Details", "Features used for candidate scoring")
        table(ax, 0.06, 0.30, 0.88, 0.45, ["Feature group", "Examples", "Purpose"], [
            ["BT structure", "tree_size, tree_depth, preorder tokens", "Represent candidate complexity and control structure"],
            ["KIOS metrics", "symbolic_success, goal_satisfaction", "Check logical executability"],
            ["Diagnostics", "invalid_action_count, condition_failure_count", "Penalize brittle or invalid candidates"],
            ["Physical metrics", "sim_success, displacement error", "Capture stability and physical executability"],
            ["Selector agreement", "feature, transformer, symbolic votes", "Use consensus across complementary selectors"],
        ], [0.23, 0.36, 0.41], 7.6)
        card(ax, 0.08, 0.13, 0.38, 0.12, "Key design decision", "The final method is not a pure Transformer. Transformer is used as a BT structure encoder inside a hybrid selector.", PURPLE)
        card(ax, 0.54, 0.13, 0.38, 0.12, "Why this matters", "Robot execution failures come from different sources, so robust selection needs multiple evidence streams.", BLUE)
        footer(ax, "Method details", 6); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax(); title(ax, "6. BT Token Transformer Encoder", "Encoding behavior tree structure as a sequence")
        chain = [("BT JSON", 0.07), ("Preorder Tokens", 0.25), ("Token IDs", 0.43), ("Transformer Encoder", 0.61), ("BT Embedding", 0.81)]
        for lab, x in chain:
            step(ax, x, 0.55, 0.13, 0.08, lab, "#f5f3ff")
        for i in range(len(chain)-1):
            arrow(ax, chain[i][1]+0.13, 0.59, chain[i+1][1], 0.59, PURPLE)
        card(ax, 0.07, 0.31, 0.25, 0.13, "Transformer-only", "Uses only BT token sequence to produce a ranking score.", PURPLE)
        card(ax, 0.375, 0.31, 0.25, 0.13, "Transformer-fused", "Combines BT embedding with task, world, and KIOS features.", GREEN)
        card(ax, 0.68, 0.31, 0.25, 0.13, "Interpretation", "The encoder is a structural feature module, not the only decision maker.", BLUE)
        footer(ax, "Transformer encoder", 7); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax(); title(ax, "7. V5 Hybrid Learned Selector", "The final algorithm fuses complementary reliability signals")
        step(ax, 0.08, 0.62, 0.20, 0.08, "Selector Agreement", "#eff6ff")
        step(ax, 0.08, 0.49, 0.20, 0.08, "Symbolic Reliability", "#f0fdf4")
        step(ax, 0.08, 0.36, 0.20, 0.08, "Physical Reliability", "#fff7ed")
        step(ax, 0.43, 0.49, 0.20, 0.10, "Learned Fusion", "#f5f3ff")
        step(ax, 0.76, 0.49, 0.16, 0.10, "Final BT Score", "#dcfce7")
        arrow(ax, 0.28, 0.66, 0.43, 0.55); arrow(ax, 0.28, 0.53, 0.43, 0.54); arrow(ax, 0.28, 0.40, 0.43, 0.52); arrow(ax, 0.63, 0.54, 0.76, 0.54)
        ax.text(0.18, 0.20, "score_V5(c) = w1 R_vote(c) + w2 R_sym(c) + w3 R_phy(c)", fontsize=20, color=NAVY, fontweight="bold")
        footer(ax, "V5 selector", 8); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax(); title(ax, "8. Learning Objective", "Pairwise ranking from simulation-grounded true scores")
        step(ax, 0.08, 0.58, 0.16, 0.08, "Task-state group")
        step(ax, 0.31, 0.58, 0.16, 0.08, "Candidate pair\n(ci, cj)")
        step(ax, 0.54, 0.58, 0.16, 0.08, "True score\ncomparison")
        step(ax, 0.77, 0.58, 0.14, 0.08, "Ranking loss", "#f5f3ff")
        arrow(ax, 0.24, 0.62, 0.31, 0.62); arrow(ax, 0.47, 0.62, 0.54, 0.62); arrow(ax, 0.70, 0.62, 0.77, 0.62)
        ax.text(0.16, 0.43, "If true_score(ci) > true_score(cj), learn F(ci) > F(cj).", fontsize=16, color=NAVY, fontweight="bold")
        ax.text(0.27, 0.32, "L = max(0, margin - F(ci) + F(cj))", fontsize=21, color=BLUE, fontweight="bold")
        bullet_list(ax, ["Pairwise ranking matches the group-wise selection problem.", "Simulation-grounded scores provide stronger supervision than symbolic success alone."], 0.12, 0.22, 11.5, 94)
        footer(ax, "Training objective", 9); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax(); title(ax, "9. Benchmark Design", "Tasks become progressively harder")
        table(ax, 0.06, 0.39, 0.58, 0.32, ["Benchmark", "Goal", "Purpose"], [
            ["V1 supported-by", "Basic support relation", "Check placing behavior"],
            ["V2 stacking probe", "Stacking tasks", "Test longer action chains"],
            ["V2B physical strategy", "Stable vs risky placement", "Separate symbolic and physical quality"],
            ["V6 hard cases", "Hard physical constraints", "Stress-test final selector"],
        ], [0.31, 0.29, 0.40], 7.4)
        bars = []
        for r in outs:
            lab = first(r, ["benchmark"])
            val = num(first(r, ["sim_success"])) or num(first(r, ["sim_done"])) or 0
            bars.append((lab, val))
        bar_chart(ax, 0.69, 0.39, 0.25, 0.32, bars, "Simulation success rows", BLUE)
        footer(ax, "Benchmark design", 10); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax(); title(ax, "10. Evaluation Metrics and Baselines", "How selector quality is measured")
        table(ax, 0.06, 0.40, 0.42, 0.31, ["Metric", "Meaning"], [
            ["Success rate", "Whether selected BT reaches success criteria"],
            ["Mean true score", "Average score of selected BT"],
            ["Mean regret", "Oracle score minus selected score"],
            ["Pairwise accuracy", "Ranking model pairwise correctness"],
            ["Simulation success", "Physical execution success in Isaac Gym"],
        ], [0.35, 0.65], 7.5)
        table(ax, 0.53, 0.40, 0.41, 0.31, ["Selector", "Role"], [
            ["Shortest-tree", "Simple heuristic baseline"],
            ["Symbolic-only", "KIOS-centered baseline"],
            ["Feature-only", "Tabular learned baseline"],
            ["Transformer-fused", "BT embedding + tabular features"],
            ["V5 learned", "Final hybrid selector"],
            ["Oracle", "Evaluation upper bound only"],
        ], [0.42, 0.58], 7.5)
        footer(ax, "Metrics and baselines", 11); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax(); title(ax, "11. Overall Results", "Success-regret trade-off")
        data = []
        for r in sels:
            success = num(first(r, ["success"]))
            regret = num(first(r, ["mean_regret", "regret"]))
            groups = num(first(r, ["groups"])) or 30
            if success is not None and regret is not None:
                data.append((first(r, ["selector"]), success, regret, groups))
        if data:
            max_reg = max(d[2] for d in data) or 1
            ax.add_patch(Rectangle((0.07, 0.22), 0.56, 0.50, facecolor=WHITE, edgecolor=LINE))
            for label, success, regret, groups in data[:18]:
                px = 0.09 + (regret / max_reg) * 0.50
                py = 0.25 + min(1.0, success) * 0.42
                color = SLATE if "oracle" in label else PURPLE if "v5" in label else GREEN if ("transformer" in label or "feature" in label) else AMBER
                ax.add_patch(Circle((px, py), 0.008 + min(0.018, groups / 8000), facecolor=color, edgecolor=WHITE, linewidth=0.8))
                ax.text(px + 0.008, py, short(label), fontsize=6.7, color=SLATE, va="center")
            ax.text(0.28, 0.18, "Mean regret (lower is better)", fontsize=8, color=MUTED)
            ax.text(0.08, 0.74, "Success rate", fontsize=8, color=MUTED)
        bullet_list(ax, ["Mean regret is the main selection-quality metric.", "V5 methods are closer to oracle than simple heuristics.", "Shortest-tree performs poorly: compact BTs are not necessarily reliable."], 0.68, 0.62, 11.5, 43)
        footer(ax, "Overall selector comparison", 12); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax(); title(ax, "12. Selector Robustness Heatmap", "Mean regret by selector and benchmark")
        cols, mat = selector_matrix("regret")
        heatmap(ax, 0.07, 0.22, 0.68, 0.52, cols, mat, "Mean regret heatmap", lower_is_better=True)
        bullet_list(ax, ["Heatmaps show where each selector is reliable or brittle.", "Hard cases make physical reliability more important.", "Every figure used in the dissertation should be discussed in the text."], 0.79, 0.62, 11, 34)
        footer(ax, "Robustness across benchmarks", 13); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax(); title(ax, "13. V5 Ablation Study", "Evidence for multi-source fusion")
        ab_data = []
        display = []
        for r in abls[:10]:
            reg = num(first(r, ["mean_regret", "regret"]))
            if reg is not None:
                ab_data.append((first(r, ["selector"]), reg))
            display.append([short(first(r, ["selector"])), first(r, ["groups"], "-"), f"{num(first(r, ['success'])) or 0:.3f}", f"{reg:.3f}" if reg is not None else "-"])
        bar_chart(ax, 0.06, 0.23, 0.38, 0.48, ab_data, "Mean regret after ablation", PURPLE, lower_is_better=True)
        table(ax, 0.49, 0.26, 0.45, 0.42, ["Variant", "Groups", "Success", "Regret"], display[:8], [0.44, 0.16, 0.18, 0.22], 6.9)
        footer(ax, "Ablation study", 14); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax(); title(ax, "14. Simulation Validation", "Why Isaac Gym is part of the evaluation")
        outcome_bars = []
        for r in outs:
            total = (num(first(r, ["sim_success"])) or 0) + (num(first(r, ["sim_failure"])) or 0)
            outcome_bars.append((first(r, ["benchmark"]), total))
        bar_chart(ax, 0.07, 0.28, 0.38, 0.42, outcome_bars, "Simulated candidate outcomes", CYAN)
        card(ax, 0.54, 0.53, 0.36, 0.13, "What simulation adds", "KIOS checks abstract execution, while Isaac Gym reveals unstable support, edge placement, object displacement, and contact violations.", AMBER)
        card(ax, 0.54, 0.34, 0.36, 0.13, "How it is used", "Simulation metrics construct true scores, train simulation-aware selectors, and support visual demonstrations.", BLUE)
        footer(ax, "Simulation validation", 15); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax(); title(ax, "15. GUI Demonstration", "End-to-end workflow for presentation")
        labels = ["Task definition", "BT candidates", "Selector scores", "Selected / Oracle BT", "Replay command"]
        xs = [0.06, 0.245, 0.43, 0.615, 0.80]
        for x, lab in zip(xs, labels):
            step(ax, x, 0.56, 0.14, 0.08, lab, "#eff6ff" if x < 0.615 else "#dcfce7")
        for i in range(len(xs)-1):
            arrow(ax, xs[i]+0.14, 0.60, xs[i+1], 0.60)
        card(ax, 0.10, 0.30, 0.35, 0.13, "Web demo", "Shows task, candidate BTs, selector scores, top-down placement view, and replay commands.", BLUE)
        card(ax, 0.55, 0.30, 0.35, 0.13, "Visual replay", "Provides a presentation-friendly Isaac Gym style execution view.", AMBER)
        ax.text(0.30, 0.20, "Demo URL: http://localhost:8091/", fontsize=16, color=NAVY, fontweight="bold")
        footer(ax, "System demo", 16); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax(); title(ax, "16. Project Management", "Managing complexity, risk, and decisions")
        table(ax, 0.06, 0.26, 0.88, 0.48, ["Project issue", "Decision made", "Reason"], [
            ["Large system complexity", "Split into staged versions V1, V2, V2B, V4B, V5, V6", "Made progress measurable"],
            ["Expensive simulation", "Cached outputs and summarized incrementally", "Avoided rerunning completed jobs"],
            ["Unstable GPT calls", "Kept single-vs-multi as pilot", "Avoided API limits affecting main claims"],
            ["Final-stage risk", "Limited new code changes", "Focused on writing, results, and figures"],
            ["Communication", "Used progress updates and design discussions", "Kept decisions aligned with goals"],
        ], [0.27, 0.39, 0.34], 7.2)
        footer(ax, "Project management", 17); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax(); title(ax, "17. Limitations, Contributions, and Future Work", "A careful final claim")
        card(ax, 0.06, 0.56, 0.27, 0.14, "Limitation", "The GPT single-vs-multi experiment was affected by API rate limits and invalid JSON outputs, so it is not a main quantitative claim.", RED)
        card(ax, 0.365, 0.56, 0.27, 0.14, "Contribution", "A complete BT selection pipeline with KIOS symbolic evaluation, Transformer structure encoding, V5 fusion, and simulation validation.", GREEN)
        card(ax, 0.67, 0.56, 0.27, 0.14, "Future work", "Scale candidate generation, add more long-horizon tasks, explore graph encoders, and close the loop with BT repair.", BLUE)
        bullet_list(ax, ["Main claim: multi-source BT selection reduces reliance on fragile single signals.", "The thesis should now prioritize writing, vector figures, and discussing every included figure."], 0.10, 0.34, 13, 86)
        footer(ax, "Final synthesis", 18); pdf.savefig(fig); plt.close(fig)

        fig, ax = setup_ax()
        ax.text(0.5, 0.56, "Thank You", fontsize=38, color=NAVY, fontweight="bold", ha="center")
        ax.text(0.5, 0.45, "Questions?", fontsize=24, color=BLUE, fontweight="bold", ha="center")
        ax.text(0.5, 0.32, "KIOS + Transformer BT Selector for Robot Task Planning", fontsize=13, color=SLATE, ha="center")
        footer(ax, "Q&A", 19); pdf.savefig(fig); plt.close(fig)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--author", default="Your Name")
    parser.add_argument("--department", default="Your Department")
    parser.add_argument("--date", default="2026")
    return parser.parse_args()


def main():
    args = parse_args()
    build_pdf(args)
    print({"result": "success", "output": str(args.output), "pages": 19})


if __name__ == "__main__":
    main()
