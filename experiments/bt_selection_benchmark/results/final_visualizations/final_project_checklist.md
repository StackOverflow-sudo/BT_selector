# 毕业设计项目最终清单

> 项目路径：
> `/home/theshy/projects/mycode/kios_baseline`

## 1. 项目当前状态

当前项目已经完成从行为树候选生成、KIOS 符号执行、Transformer BT 编码、V5 learned selector、Isaac Gym 仿真验证到最终实验图表整理的主要链路。

一句话总结：

> 本项目实现了一个面向机器人任务规划的多候选行为树选择系统，通过融合 BT 结构表示、KIOS 符号执行反馈和物理/仿真可靠性信息，从多个候选行为树中选择更适合执行的 BT。

## 2. 已完成模块

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| 文献调研 | 已完成 | 已阅读 LLM-as-BT-Planner、Points2Plans、MuST、HGT 等相关论文 |
| Baseline 复现 | 已完成 | 实现 LLM 单候选/已有候选 BT baseline、规则 selector、启发式 selector |
| KIOS 符号评估 | 已完成 | 可对候选 BT 进行符号执行并提取 metrics |
| V1 benchmark | 已完成 | supported-by 基础任务 |
| V2 benchmark | 已完成 | stacking probe |
| V2B benchmark | 已完成 | physical strategy 任务 |
| V6 hard cases | 已完成 | 困难物理约束任务，仿真已完成 |
| Feature-only selector | 已完成 | 基于 tabular feature 的学习 selector |
| Transformer BT encoder | 已完成 | V4B lightweight Transformer BT ranker |
| V5 manual ensemble | 已完成 | 手工权重 ensemble selector |
| V5 learned ensemble | 已完成 | 学习型 ensemble selector 和消融实验 |
| Isaac Gym 仿真 | 已完成 | 已完成主要 benchmark 的仿真结果汇总 |
| Web demo | 已完成 | 支持任务、候选 BT、selector 分数、top-down view 和 replay command 展示 |
| GPT candidate demo | 部分完成 | demo 链路已实现，但 single-vs-multi baseline 受 API rate limit 影响，暂不作为主结果 |
| 最终图表 | 已完成 | 基础图和增强版图表均已生成 |
| 方法章节草稿 | 已完成 | 已生成第 3 章方法草稿 |
| 实验章节草稿 | 已完成 | 已生成第 4 章实验草稿 |

## 3. 核心实验结果文件

### 3.1 原始候选评估结果

```text
experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v1_supported_by_with_sim.csv
experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v2_stacking_probe_with_sim.csv
experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v2b_physical_strategy_with_sim.csv
experiments/bt_selection_benchmark/results/bt_candidate_evaluations_v6_hard_cases_with_sim.csv
```

### 3.2 Selector 对比结果

```text
experiments/bt_selection_benchmark/results/v4b_transformer_selector_summary.csv
experiments/bt_selection_benchmark/results/v5_ensemble_selector_summary.csv
experiments/bt_selection_benchmark/results/v5_learned_ensemble_report.md
experiments/bt_selection_benchmark/results/v5_learned_ensemble_ablation.csv
experiments/bt_selection_benchmark/results/v5_learned_ensemble_weights.csv
```

### 3.3 最终图表与总表

```text
experiments/bt_selection_benchmark/results/final_visualizations/
```

核心文件：

```text
final_results_report.md
final_dataset_coverage.csv
final_selector_comparison.csv
final_v5_learned_ablation.csv
final_v5_learned_weights.csv
enhanced_visualization_report.md
```

## 4. 推荐论文正文图表

建议正文优先使用：

```text
fig_candidate_simulation_outcomes.png
fig_success_regret_tradeoff.png
fig_selector_regret_heatmap.png
fig_v5_ablation_dual_axis.png
fig_final_dashboard.png
```

建议附录或补充材料使用：

```text
fig_selector_success_heatmap.png
fig_v5_learned_weights.png
fig_final_selector_regret.png
fig_final_selector_success.png
fig_v5_ablation_regret.png
fig_v5_ablation_success.png
fig_dataset_simulation_coverage.png
```

## 5. 论文材料文件

```text
experiments/bt_selection_benchmark/results/final_visualizations/thesis_method_chapter_draft.md
experiments/bt_selection_benchmark/results/final_visualizations/thesis_experiment_chapter_draft.md
experiments/bt_selection_benchmark/results/final_visualizations/method_algorithms_pseudocode.md
experiments/bt_selection_benchmark/results/final_visualizations/system_architecture_mermaid.md
experiments/bt_selection_benchmark/results/final_visualizations/presentation_experiment_talking_points.md
```

建议论文结构：

```text
第 1 章 绪论
第 2 章 相关工作
第 3 章 系统方法设计
第 4 章 实验设计与结果分析
第 5 章 系统演示与实现
第 6 章 总结与展望
```

## 6. 常用运行命令

### 6.1 重新生成基础最终图表

```bash
cd /home/theshy/projects/mycode/kios_baseline
bash experiments/bt_selection_benchmark/plot_final_results.sh
```

### 6.2 重新生成增强版图表

```bash
cd /home/theshy/projects/mycode/kios_baseline
bash experiments/bt_selection_benchmark/plot_final_results_enhanced.sh
```

### 6.3 重新训练/汇总 V4B Transformer selector

```bash
cd /home/theshy/projects/mycode/kios_baseline
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 python3 experiments/bt_selection_benchmark/models/train_v4b_transformer_selector.py --epochs 10
```

### 6.4 重新汇总 V5 ensemble

```bash
cd /home/theshy/projects/mycode/kios_baseline
python3 experiments/bt_selection_benchmark/models/summarize_v5_ensemble_selector.py
```

### 6.5 Web demo

```bash
cd /home/theshy/projects/mycode/kios_baseline/experiments/gpt_candidate_demo/frontend
python3 -m http.server 8091
```

浏览器打开：

```text
http://localhost:8091/
```

### 6.6 GPT candidate demo

使用已有/mock 数据：

```bash
cd /home/theshy/projects/mycode/kios_baseline
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 python3 experiments/gpt_candidate_demo/run_gpt_candidate_demo.py \
  --generator existing \
  --candidate-count 4
```

使用 OpenAI API：

```bash
cd /home/theshy/projects/mycode/kios_baseline
export OPENAI_API_KEY="your_key"
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 python3 experiments/gpt_candidate_demo/run_gpt_candidate_demo.py \
  --generator openai \
  --model gpt-5.4-mini \
  --candidate-count 4
```

### 6.7 Isaac Gym visual replay

稳定演示版本：

```bash
cd /home/theshy/projects/mycode/kios_baseline
python3 experiments/gpt_candidate_demo/run_visual_replay.py --candidate selected --loop --simple-arm
```

如果要尝试完整 KUKA 模型：

```bash
python3 experiments/gpt_candidate_demo/run_visual_replay.py --candidate selected --loop
```

## 7. 当前暂缓内容

### GPT single-vs-multi baseline

该实验脚本已实现：

```text
experiments/gpt_candidate_demo/run_single_vs_multi_gpt_baseline.py
experiments/gpt_candidate_demo/run_single_vs_multi_gpt_baseline.sh
```

但当前运行时遇到 OpenAI TPM rate limit：

```text
Rate limit reached for gpt-5.4-mini
```

因此该实验暂不作为论文主结果。建议论文中将其作为后续工作或补充实验设计说明。

如果之后继续跑：

```bash
cd /home/theshy/projects/mycode/kios_baseline
export OPENAI_API_KEY="your_key"
bash experiments/gpt_candidate_demo/run_single_vs_multi_gpt_baseline.sh \
  --task-specs experiments/gpt_candidate_demo/task_specs_single_vs_multi_supported.json \
  --case-count 10 \
  --repeats 3 \
  --multi-candidate-count 4 \
  --continue-on-error
```

## 8. 剩余工作优先级

### 高优先级

1. 将第 3 章方法草稿改写成正式论文语言。
2. 将第 4 章实验草稿改写成正式论文语言。
3. 从 final_visualizations 中挑选 4-5 张图放入正文。
4. 制作答辩 PPT 的方法页、实验页和 demo 页。
5. 整理 README，确保别人能复现实验和打开 demo。

### 中优先级

1. 将 Mermaid 架构图转换为论文可用 PNG/SVG。
2. 对 final_selector_comparison.csv 做一张论文总表。
3. 检查图表中 selector 名称是否需要美化。
4. 补充一段关于 GPT single-vs-multi baseline 未完成原因的说明。

### 低优先级

1. 继续补 GPT single-vs-multi baseline 实验。
2. 进一步优化 Isaac Gym GUI 演示效果。
3. 增加更多任务或更多随机初始状态。
4. 尝试更大的 Transformer encoder。

## 9. 最终贡献总结

论文可以总结为以下贡献：

1. 构建了一个 LLM/BT/KIOS/Isaac Gym 结合的机器人任务规划实验系统。
2. 设计了多组 BT selection benchmark，从基础 supported-by 到困难物理约束任务。
3. 提出了 BT token Transformer encoder，用于行为树结构表示。
4. 提出了 V5 hybrid learned selector，融合 selector agreement、symbolic reliability 和 physical reliability。
5. 通过 Isaac Gym 仿真验证了符号成功与物理可执行性之间的差异。
6. 通过消融实验说明了 V5 各组成模块的贡献。

