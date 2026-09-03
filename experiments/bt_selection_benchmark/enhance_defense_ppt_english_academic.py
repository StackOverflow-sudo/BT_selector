#!/usr/bin/env python3
"""Create a richer academic English defense deck.

This version adds more academic content than the compact defense deck:
background, references, method details, experiment tables, limitations, project
management, and thesis-ready interpretation notes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import enhance_defense_ppt_english as base  # noqa: E402


ROOT = base.ROOT
FINAL = base.FINAL
DEFAULT_INPUT = Path("/mnt/c/Users/lenovo/Desktop/bt_selector_defense_presentation.pptx")
DEFAULT_OUTPUT = Path("/mnt/c/Users/lenovo/Desktop/bt_selector_defense_presentation_academic_en.pptx")


def metric(row, *names):
    return base.first(row, names, "")


def compact_metric(value, digits=3):
    x = base.n(value)
    if x is None:
        return "-"
    return f"{x:.{digits}f}"


def add_research_context_slide(prs, page):
    slide = prs.slides.add_slide(base.blank(prs))
    base.title(slide, "Research Context", "Why behavior tree selection matters for robot task planning")
    base.card(
        slide,
        "LLM-based planning",
        "Large language models can produce high-level task plans, but raw generated plans often require grounding, validation, and repair before robot execution.",
        1.3,
        3.0,
        9.5,
        3.6,
        base.BLUE,
    )
    base.card(
        slide,
        "Behavior Trees",
        "Behavior Trees provide a modular and interpretable execution structure, making them suitable for robot task execution and monitoring.",
        12.0,
        3.0,
        9.5,
        3.6,
        base.GREEN,
    )
    base.card(
        slide,
        "Physical executability",
        "Symbolic goal satisfaction is not enough. Physical stability, contacts, placement strategy, and object displacement must also be considered.",
        22.7,
        3.0,
        9.5,
        3.6,
        base.AMBER,
    )
    base.table(
        slide,
        ["Challenge", "Why it appears", "How this project responds"],
        [
            ["Invalid BT nodes", "LLM output may not match the action vocabulary", "Restrict action/condition schema and validate with KIOS"],
            ["Symbolic-physical gap", "A symbolic relation may not imply stable execution", "Use Isaac Gym metrics and physical reliability features"],
            ["Multiple plausible plans", "Different BTs can satisfy the same task", "Rank candidates with V5 learned selector"],
        ],
        1.4,
        8.2,
        30.6,
        4.8,
    )
    base.footer(slide, page)
    return page + 1


def add_references_slide(prs, page):
    slide = prs.slides.add_slide(base.blank(prs))
    base.title(slide, "Literature Basis", "How prior work shaped the system design")
    base.table(
        slide,
        ["Paper / Direction", "Key idea used in this project", "Role in my design"],
        [
            ["LLM-as-BT-Planner", "Generate Behavior Trees from language instructions", "Baseline motivation for LLM-to-BT generation"],
            ["Points2Plans", "Plan from scene relations and long-horizon object dynamics", "Motivates relational task/state benchmark design"],
            ["MuST", "Transformer over skill sequences and long-horizon manipulation", "Motivates sequence-based BT/skill representation"],
            ["Hypergraph Transformer", "Model high-order interaction events", "Inspires future graph/hypergraph extensions"],
            ["Behavior Tree robotics literature", "Modular, reactive and interpretable execution", "Supports choosing BT as the execution representation"],
        ],
        1.2,
        2.8,
        31.0,
        7.2,
    )
    base.bullets(
        slide,
        [
            "This work is not a direct reproduction of one paper; it combines LLM-style BT generation, symbolic executability checking, and learned candidate selection.",
            "The main research contribution is the selector pipeline: multi-candidate BTs are evaluated and ranked using symbolic, structural, and physical evidence.",
        ],
        1.7,
        11.2,
        29.0,
        2.5,
        16,
    )
    base.footer(slide, page)
    return page + 1


def add_method_detail_slide(prs, page):
    slide = prs.slides.add_slide(base.blank(prs))
    base.title(slide, "Method Details", "Features used for candidate scoring")
    base.table(
        slide,
        ["Feature group", "Examples", "Purpose"],
        [
            ["BT structure", "tree_size, tree_depth, preorder tokens", "Represent candidate complexity and control structure"],
            ["KIOS symbolic metrics", "symbolic_success, goal_satisfaction, precondition_coverage", "Check whether the BT is logically executable"],
            ["Execution diagnostics", "invalid_action_count, condition_failure_count, bt_ticks", "Penalize brittle or invalid candidates"],
            ["Physical metrics", "sim_success, final_position_error, object_displacement_error", "Capture stability and physical executability"],
            ["Selector agreement", "feature_only, transformer_fused, symbolic_only votes", "Use consensus across complementary selectors"],
        ],
        1.2,
        2.7,
        31.0,
        7.0,
    )
    base.card(
        slide,
        "Key design decision",
        "The final method is not a pure Transformer model. The Transformer is used as a BT structure encoder, while V5 performs robust fusion of multiple reliability signals.",
        2.0,
        11.0,
        13.0,
        3.0,
        base.PURPLE,
    )
    base.card(
        slide,
        "Why this matters",
        "Robotic execution failures can come from different sources. Multi-source features make the selector less dependent on any single imperfect signal.",
        17.0,
        11.0,
        13.0,
        3.0,
        base.BLUE,
    )
    base.footer(slide, page)
    return page + 1


def add_training_objective_slide(prs, page):
    slide = prs.slides.add_slide(base.blank(prs))
    base.title(slide, "Learning Objective", "Pairwise ranking from simulation-grounded scores")
    base.step(slide, "Task-state group", 2.0, 4.2, 5.8, 1.3)
    base.step(slide, "Candidate pair\n(ci, cj)", 10.0, 4.2, 5.8, 1.3)
    base.step(slide, "True score\ncomparison", 18.0, 4.2, 5.8, 1.3)
    base.step(slide, "Ranking loss", 26.0, 4.2, 4.8, 1.3, base.rgb_lerp(base.PURPLE, base.WHITE, 0.55))
    base.arrow(slide, 7.8, 4.85, 10.0, 4.85)
    base.arrow(slide, 15.8, 4.85, 18.0, 4.85)
    base.arrow(slide, 23.8, 4.85, 26.0, 4.85)
    base.textbox(slide, "If true_score(ci) > true_score(cj), the model should learn F(ci) > F(cj).", 3.0, 7.3, 26.5, 0.7, 18, base.NAVY, True, base.PP_ALIGN.CENTER)
    base.textbox(slide, "L = max(0, margin - F(ci) + F(cj))", 5.0, 9.0, 22.5, 0.8, 22, base.BLUE, True, base.PP_ALIGN.CENTER)
    base.bullets(
        slide,
        [
            "Pairwise ranking is suitable because the selector only needs to choose the best candidate within the same task group.",
            "Simulation-grounded scores provide stronger supervision than symbolic success alone.",
            "The learned V5 ensemble uses existing benchmark results rather than rewriting the algorithm at the final stage.",
        ],
        3.0,
        11.3,
        26.0,
        3.2,
        16,
    )
    base.footer(slide, page)
    return page + 1


def add_experiment_summary_table_slide(prs, page):
    slide = prs.slides.add_slide(base.blank(prs))
    base.title(slide, "Final Experiment Tables", "Main quantitative artifacts used in the thesis")
    selector_rows = base.read_csv(FINAL / "final_selector_comparison.csv")
    selected = []
    priority = ["feature_only", "transformer_only", "transformer_fused", "symbolic_only", "shortest_tree", "v5_ensemble", "oracle"]
    for name in priority:
        for r in selector_rows:
            if metric(r, "selector") == name:
                selected.append([
                    base.short(name),
                    metric(r, "source"),
                    metric(r, "groups"),
                    compact_metric(metric(r, "success")),
                    compact_metric(metric(r, "mean_selected_true_score")),
                    compact_metric(metric(r, "mean_regret")),
                ])
                break
    base.table(
        slide,
        ["Selector", "Source", "Groups", "Success", "True score", "Regret"],
        selected[:8],
        1.0,
        2.7,
        31.7,
        6.3,
    )
    base.bullets(
        slide,
        [
            "The thesis should discuss every figure and table included in the report.",
            "Mean regret is the main selection-quality metric because it measures distance from the oracle choice.",
            "The GPT single-vs-multi experiment is treated as a pilot due to API rate limits and invalid JSON responses.",
        ],
        2.0,
        10.4,
        28.0,
        3.0,
        16,
    )
    base.footer(slide, page)
    return page + 1


def add_ablation_table_slide(prs, page):
    slide = prs.slides.add_slide(base.blank(prs))
    base.title(slide, "Ablation Results", "Evidence for multi-source fusion")
    rows = base.read_csv(FINAL / "final_v5_learned_ablation.csv")
    display = []
    for r in rows[:10]:
        display.append([
            base.short(metric(r, "selector")),
            metric(r, "groups"),
            compact_metric(metric(r, "success")),
            compact_metric(metric(r, "mean_selected_true_score", "true_score")),
            compact_metric(metric(r, "mean_regret", "regret")),
        ])
    base.table(
        slide,
        ["Variant", "Groups", "Success", "True score", "Regret"],
        display,
        1.0,
        2.6,
        19.5,
        7.8,
    )
    base.card(slide, "Interpretation", "Removing symbolic or simulation reliability increases regret, showing that V5 benefits from complementary evidence sources.", 22.0, 3.0, 9.0, 3.2, base.PURPLE)
    base.card(slide, "Deployment note", "The no-simulation variant is useful when full simulation is unavailable before online selection.", 22.0, 7.0, 9.0, 3.0, base.AMBER)
    base.footer(slide, page)
    return page + 1


def add_project_management_detailed_slide(prs, page):
    slide = prs.slides.add_slide(base.blank(prs))
    base.title(slide, "Project Management", "Managing complexity, risk, and decisions")
    base.table(
        slide,
        ["Project issue", "Decision made", "Reason"],
        [
            ["Large system complexity", "Split work into staged versions V1, V2, V2B, V4B, V5 and V6", "Made progress measurable and reduced debugging scope"],
            ["Expensive Isaac Gym simulation", "Cached simulation outputs and summarized them incrementally", "Avoided rerunning completed jobs"],
            ["Unstable GPT online calls", "Kept GPT baseline as pilot and focused main claims on completed benchmarks", "Avoided API limits affecting thesis conclusions"],
            ["Algorithm scope", "Stopped major code changes at the final stage", "Focused on results, figures and writing as requested"],
            ["Communication", "Used weekly progress updates, design discussions and supervisor feedback", "Kept decisions aligned with project goals"],
        ],
        1.1,
        2.6,
        31.3,
        8.8,
    )
    base.bullets(
        slide,
        [
            "This section is included because project management is assessed.",
            "The final stage prioritizes thesis writing, vector figures, result interpretation, and template compliance.",
        ],
        1.8,
        12.5,
        29.0,
        2.0,
        16,
    )
    base.footer(slide, page)
    return page + 1


def add_limitations_slide(prs, page):
    slide = prs.slides.add_slide(base.blank(prs))
    base.title(slide, "Limitations and Scope", "What the results do and do not claim")
    base.card(slide, "Transformer scope", "The Transformer encoder is lightweight and should be interpreted as a structural feature module, not as a standalone dominant model.", 1.5, 3.1, 9.5, 4.0, base.PURPLE)
    base.card(slide, "GPT baseline", "The single-vs-multi GPT comparison was implemented, but the completed run includes API rate-limit and invalid JSON failures.", 12.2, 3.1, 9.5, 4.0, base.AMBER)
    base.card(slide, "Simulation scope", "Isaac Gym validation improves physical evidence, but it is still a simulation rather than a real robot deployment.", 22.9, 3.1, 9.5, 4.0, base.BLUE)
    base.bullets(
        slide,
        [
            "Main claims are based on completed benchmark results and ablation studies.",
            "Future work can expand the dataset, improve online GPT schema enforcement, and transfer selected BTs to real robots.",
        ],
        2.0,
        9.5,
        28.0,
        3.0,
        18,
    )
    base.footer(slide, page)
    return page + 1


def build_academic_deck(args):
    prs = base.new_prs(args.input)
    page = 1

    page = base.title_slide(prs, page, args)
    page = add_research_context_slide(prs, page)
    page = add_references_slide(prs, page)

    # Reuse the strong core slides from the previous enhanced deck, but add more
    # academic detail around them.
    temp = base.build_deck(args)
    for idx in range(2, min(12, len(temp.slides))):
        # python-pptx does not support direct slide cloning reliably without
        # private XML copying. Instead, rebuild the key extra slides below.
        pass

    # Rebuild core method/result slides using the shared helper functions.
    slide = prs.slides.add_slide(base.blank(prs)); base.title(slide, "Problem Formulation", "Select one reliable BT from a candidate set")
    base.step(slide, "Task Instruction I", 1.7, 4.0, 4.5, 1.2); base.step(slide, "Initial State S0", 1.7, 6.0, 4.5, 1.2)
    base.step(slide, "Candidate Set\nC = {c1, c2, ..., cn}", 8.2, 4.9, 6.2, 1.5, base.rgb_lerp(base.BLUE, base.WHITE, 0.82))
    base.step(slide, "Score F(I, S0, ci)", 17.0, 4.9, 5.5, 1.5, base.rgb_lerp(base.PURPLE, base.WHITE, 0.82))
    base.step(slide, "Selected BT\nc* = argmax F", 25.0, 4.9, 5.5, 1.5, base.rgb_lerp(base.GREEN, base.WHITE, 0.75))
    base.arrow(slide, 6.2, 4.6, 8.2, 5.45); base.arrow(slide, 6.2, 6.6, 8.2, 5.75); base.arrow(slide, 14.4, 5.65, 17.0, 5.65); base.arrow(slide, 22.5, 5.65, 25.0, 5.65)
    base.bullets(slide, ["The goal is group-wise selection, not isolated BT classification.", "Regret measures the quality gap between the selected candidate and the oracle candidate.", "A candidate can be symbolically successful but physically unstable."], 2.0, 10.0, 27.5, 4.0, 18)
    base.footer(slide, page); page += 1

    slide = prs.slides.add_slide(base.blank(prs)); base.title(slide, "System Architecture", "End-to-end candidate evaluation and selection")
    nodes = [("Task + State", 1.4), ("BT Candidates", 6.5), ("KIOS Metrics", 11.8), ("BT Encoder", 17.1), ("V5 Selector", 22.4), ("Selected BT", 27.3)]
    for label, x in nodes:
        base.step(slide, label, x, 5.0, 4.2, 1.3)
    for i in range(len(nodes) - 1):
        base.arrow(slide, nodes[i][1] + 4.2, 5.65, nodes[i + 1][1], 5.65)
    base.step(slide, "Isaac Gym\nValidation", 21.3, 8.6, 5.4, 1.4, base.rgb_lerp(base.AMBER, base.WHITE, 0.75))
    base.arrow(slide, 29.0, 6.3, 24.0, 8.6, base.AMBER)
    base.bullets(slide, ["The architecture separates low-cost symbolic evaluation from high-cost simulation validation.", "The selector receives evidence from BT structure, symbolic execution and physical reliability."], 2.0, 12.2, 27.5, 2.4, 18)
    base.footer(slide, page); page += 1

    page = add_method_detail_slide(prs, page)
    page = add_training_objective_slide(prs, page)

    slide = prs.slides.add_slide(base.blank(prs)); base.title(slide, "Benchmark Design", "Progressively harder task groups")
    base.table(slide, ["Benchmark", "Goal", "Purpose"], [
        ["V1 supported-by", "Basic support relation", "Check basic placing behavior"],
        ["V2 stacking probe", "Stacking tasks", "Test longer action chains"],
        ["V2B physical strategy", "Stable vs risky placement", "Separate symbolic and physical quality"],
        ["V6 hard cases", "Hard physical constraints", "Stress-test the final selector"],
    ], 1.4, 3.0, 19.0, 5.7)
    outcomes = base.load_outcomes()
    outcome_data = []
    for r in outcomes:
        label = base.first(r, ["benchmark"])
        val = base.n(base.first(r, ["sim_success"])) or base.n(base.first(r, ["sim_done"])) or 0
        outcome_data.append((label, val))
    base.bar_chart(slide, outcome_data[:6], 22.0, 4.0, 9.8, 5.6, "Simulation coverage", base.BLUE)
    base.footer(slide, page); page += 1

    page = add_experiment_summary_table_slide(prs, page)
    page = add_ablation_table_slide(prs, page)

    slide = prs.slides.add_slide(base.blank(prs)); base.title(slide, "Selector Robustness Across Benchmarks", "Mean regret heatmap")
    cols, mat = base.selector_matrix("regret")
    base.heatmap(slide, cols, mat, 1.4, 3.0, 22.5, 10.2, "Mean regret by selector and benchmark", lower_is_better=True)
    base.bullets(slide, ["Heatmap highlights where each selector is reliable or brittle.", "Hard cases make physical reliability more important.", "Every figure included in the final report should be explicitly discussed in text."], 24.8, 4.2, 7.0, 5.5, 15)
    base.footer(slide, page); page += 1

    slide = prs.slides.add_slide(base.blank(prs)); base.title(slide, "Simulation Validation", "Why Isaac Gym is used")
    outcome_bars = []
    for r in outcomes:
        total = (base.n(base.first(r, ["sim_success"])) or 0) + (base.n(base.first(r, ["sim_failure"])) or 0)
        outcome_bars.append((base.first(r, ["benchmark"]), total))
    base.bar_chart(slide, outcome_bars, 1.4, 3.3, 14.0, 8.5, "Simulated candidate outcomes", base.CYAN)
    base.bullets(slide, ["KIOS checks abstract symbolic execution.", "Isaac Gym exposes physical issues: unstable support, edge placement, displacement and contact violations.", "Simulation metrics provide supervision for learned selectors and evidence for evaluation."], 17.8, 4.0, 12.8, 5.3, 17)
    base.footer(slide, page); page += 1

    page = add_project_management_detailed_slide(prs, page)
    page = add_limitations_slide(prs, page)

    slide = prs.slides.add_slide(base.blank(prs)); base.title(slide, "Main Contributions")
    base.card(slide, "System", "An end-to-end BT selection pipeline combining KIOS, Transformer encoding, V5 selection and Isaac Gym validation.", 1.8, 3.2, 9.2, 4.0, base.BLUE)
    base.card(slide, "Benchmarks", "Four task groups covering supported-by relations, stacking probes, physical strategy differences and hard cases.", 12.3, 3.2, 9.2, 4.0, base.GREEN)
    base.card(slide, "Algorithm", "A hybrid learned V5 selector that fuses selector agreement, symbolic reliability and physical reliability.", 22.8, 3.2, 9.2, 4.0, base.PURPLE)
    base.card(slide, "Evaluation", "Final tables, vector-based figures, ablation analysis and simulation-backed validation for thesis reporting.", 7.0, 9.0, 19.8, 3.2, base.AMBER)
    base.footer(slide, page); page += 1

    slide = prs.slides.add_slide(base.blank(prs)); base.title(slide, "Future Work")
    base.bullets(slide, ["Complete a larger GPT single-vs-multi comparison once API limits are no longer a bottleneck.", "Add more long-horizon manipulation tasks and randomized initial states.", "Explore graph or hypergraph encoders for richer BT and object-relation structure.", "Close the loop with BT repair and online feedback from failed executions.", "Transfer the selected BTs to more realistic robot settings."], 2.0, 3.0, 27.0, 7.5, 19)
    base.footer(slide, page); page += 1

    slide = prs.slides.add_slide(base.blank(prs))
    base.textbox(slide, "Thank You", 1.4, 5.7, 31.0, 1.0, 36, base.NAVY, True, base.PP_ALIGN.CENTER)
    base.textbox(slide, "Questions?", 1.4, 7.2, 31.0, 0.8, 24, base.BLUE, True, base.PP_ALIGN.CENTER)
    base.textbox(slide, "KIOS + Transformer BT Selector for Robot Task Planning", 1.4, 11.8, 31.0, 0.5, 14, base.SLATE, align=base.PP_ALIGN.CENTER)
    base.footer(slide, page)

    return prs


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--author", default="Your Name")
    parser.add_argument("--department", default="Your Department")
    parser.add_argument("--date", default="2026")
    return parser.parse_args()


def main():
    args = parse_args()
    # Patch compatibility with the previous helper script if it has not been
    # manually patched yet.
    if not hasattr(base, "GRAY"):
        base.GRAY = base.MUTED
    prs = build_academic_deck(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(args.output)
    print({"result": "success", "output": str(args.output), "slides": len(prs.slides)})


if __name__ == "__main__":
    main()
