# 第 4 章 实验设计与结果分析草稿

> 本文档用于整理毕业设计论文中的实验章节。图表路径均位于：
> `experiments/bt_selection_benchmark/results/final_visualizations/`

## 4.1 实验目标

本章实验旨在验证本文提出的行为树候选选择方法在机器人长时序任务规划中的有效性。给定一个任务指令和初始世界状态，系统首先生成多个候选行为树，然后分别通过符号执行、行为树结构编码、物理可行性估计以及仿真验证等信息对候选进行排序，最终选择一个更适合执行的行为树。

实验主要回答以下问题：

1. 多候选行为树选择是否优于简单启发式 baseline？
2. 基于 Transformer 的行为树 token encoder 是否能够为候选排序提供有效信息？
3. 符号可靠性、物理可行性和 learned ensemble 是否能够共同降低选择 regret？
4. 在更困难的物理约束任务中，本文方法是否仍然接近 oracle 上界？
5. Isaac Gym 仿真结果是否能够补充纯符号执行无法区分的候选差异？

## 4.2 实验任务与数据集

本文构建了四组逐步增强难度的 BT selection benchmark：

| Benchmark | 目的 | 说明 |
| --- | --- | --- |
| V1 supported-by | 基础支持关系任务 | 验证系统能否处理基本放置与 supported-by 关系 |
| V2 stacking probe | 堆叠任务探针 | 引入更长的动作链和堆叠关系 |
| V2B physical strategy | 物理策略差异 | 候选 BT 在符号层面可能相似，但物理放置策略不同 |
| V6 hard cases | 困难物理约束任务 | 加入边缘放置、不稳定支撑、遮挡/清理后再堆叠等困难情况 |

推荐插图：

- `fig_dataset_simulation_coverage.png`
- `fig_candidate_simulation_outcomes.png`

推荐写法：

> 如图 4-x 所示，本文实验覆盖了从基础支持关系到困难物理策略选择的多组任务。V1/V2/V2B 用于验证候选选择流程的基本可靠性，V6 hard cases 则用于评估算法在更复杂物理约束下的泛化能力。通过候选级别的 Isaac Gym 仿真结果，可以进一步区分符号成功但物理执行质量不同的行为树。

## 4.3 对比方法

本文比较以下 selector：

| 方法 | 类型 | 说明 |
| --- | --- | --- |
| random_expected | baseline | 随机选择候选行为树的期望表现 |
| first_candidate | baseline | 选择候选列表中的第一个 BT |
| shortest_tree | heuristic | 选择节点数最少的 BT |
| symbolic_success | symbolic baseline | 优先选择 KIOS 符号执行成功的 BT |
| rule_based | rule-based selector | 人工设计的符号/结构加权规则 |
| feature_only | learned baseline | 使用 tabular feature 的学习排序模型 |
| transformer_only | learned baseline | 仅使用 BT token Transformer encoder |
| transformer_fused | learned selector | Transformer BT embedding 与 tabular feature 融合 |
| v5_ensemble | proposed manual V5 | 手工加权 ensemble selector |
| v5_learned_full | proposed learned V5 | 学习得到的 ensemble 权重，融合 selector vote、符号可靠性和仿真可靠性 |
| oracle | upper bound | 基于真实得分选择最优候选，仅用于评价上界 |

需要强调：

> Oracle 不参与实际选择，只作为 regret 计算的上界。本文方法的目标不是超过 oracle，而是在不直接访问真实最优答案的情况下尽可能接近 oracle。

## 4.4 评价指标

本文使用以下指标：

| 指标 | 含义 |
| --- | --- |
| Success Rate | selector 选中候选是否达到成功标准 |
| Mean Selected True Score | 被选中 BT 的平均真实得分 |
| Mean Regret | oracle 得分与 selector 得分的差距，越低越好 |
| Pairwise Accuracy | 学习排序模型对候选对优劣关系的判断准确率 |
| ROC-AUC | 候选排序模型的二分类区分能力 |
| Simulation Success | Isaac Gym 仿真是否成功 |

推荐说明：

> Mean regret 是本文最重要的选择质量指标。与单纯 success rate 相比，regret 能进一步衡量 selector 距离 oracle 最优选择的差距。当多个候选都能符号成功时，regret 可以反映候选之间的物理策略差异和执行质量差异。

## 4.5 总体结果分析

推荐插图：

- `fig_final_dashboard.png`
- `fig_success_regret_tradeoff.png`
- `fig_selector_regret_heatmap.png`
- `fig_selector_success_heatmap.png`

推荐表格：

- `final_selector_comparison.csv`

推荐写法：

> 从整体结果可以看到，简单启发式方法如 shortest_tree 在多个 benchmark 上表现不稳定，说明较小的行为树并不一定更可靠。symbolic_only 和 rule_based 方法能够利用 KIOS 执行信息筛除明显失败的候选，但在符号层面无法充分区分物理策略优劣。相比之下，feature_only、transformer_fused 以及 V5 ensemble 方法能够综合利用结构、任务和执行特征，在 mean regret 上明显接近 oracle。

需要重点突出：

1. `shortest_tree` 是弱 baseline，说明 BT 复杂度不能直接代表可执行性。
2. `symbolic_only` 能提升基础成功率，但对物理策略区分不足。
3. `transformer_fused` 通常优于 `transformer_only`，说明 BT token 结构需要与 task/world feature 融合。
4. `v5_learned_full` 在 hard cases 上 regret 很低，是本文最终方法的核心结果。

## 4.6 Transformer BT Encoder 分析

推荐插图：

- `fig_selector_success_by_benchmark.png`
- `fig_selector_regret_by_benchmark.png`

推荐表格：

- `v4b_transformer_selector_summary.csv`

模型结构描述：

```text
BT JSON
  -> preorder token sequence
  -> token embedding + position embedding
  -> Transformer Encoder
  -> mean pooling
  -> ranking score
```

融合模型结构：

```text
Transformer BT embedding
  + task/world/symbolic tabular feature embedding
  -> ranking score
```

推荐写法：

> V4B 使用轻量级 Transformer encoder 对行为树的前序 token 序列进行编码。实验结果表明，单独使用 Transformer token embedding 的效果有限，这与当前训练数据规模较小有关；但当 Transformer embedding 与任务、世界状态和符号执行特征融合后，模型的 pairwise accuracy 与 ROC-AUC 有所提升。这说明 BT 结构信息本身具有价值，但需要与环境和执行反馈结合，才能更好地服务候选选择。

注意表述：

> 不建议声称 Transformer 单独显著优于所有 baseline。更稳妥的结论是：Transformer encoder 提供了可扩展的结构表示接口，并在 fused selector 中贡献了排序信息。

## 4.7 V5 Ensemble 与消融实验

推荐插图：

- `fig_v5_ablation_dual_axis.png`
- `fig_v5_ablation_regret.png`
- `fig_v5_learned_weights.png`

推荐表格：

- `final_v5_learned_ablation.csv`
- `final_v5_learned_weights.csv`

V5 方法可以描述为：

```text
score_V5(c) =
  selector agreement score
  + symbolic reliability score
  + simulation / physical reliability score
```

推荐写法：

> V5 ensemble 的核心思想是将多个互补信号进行融合。selector vote 提供不同排序模型之间的一致性信息，symbolic reliability 提供 KIOS 执行层面的可靠性判断，simulation reliability 则补充物理执行层面的反馈。消融实验表明，去除符号可靠性或仿真可靠性都会显著增加 regret，说明本文方法的性能并非来自单一模型，而是来自多源评价信号的互补融合。

可以强调：

1. `v5_learned_full` 是最终方法。
2. `v5_no_simulation_reliability` 可作为部署前版本，因为真实在线选择时未必有仿真结果。
3. `v5_no_symbolic_reliability` regret 上升，说明 KIOS 符号执行仍是重要组成。
4. `v5_no_transformer_votes` 与 full 的差距可以用于分析 Transformer/learned selector 的边际贡献。

## 4.8 仿真验证分析

推荐插图：

- `fig_candidate_simulation_outcomes.png`
- `fig_dataset_simulation_coverage.png`

推荐写法：

> Isaac Gym 仿真用于验证候选 BT 在物理环境中的可执行性。与 KIOS 符号执行不同，仿真可以体现放置位置、接触稳定性、物体偏移和支撑关系等物理因素。因此，在 V2B 和 V6 中，即使多个候选在符号层面都能达到目标，仿真指标仍然可以区分稳定放置和边缘放置等策略差异。

需要注意：

> 仿真结果不是用来替代符号执行，而是作为更高成本但更接近真实物理执行的验证信号。本文的选择器设计体现了“低成本符号筛选 + 高价值物理反馈”的分层思想。

## 4.9 GPT Single-BT Baseline 说明

当前 GPT single-vs-multi baseline 实验由于 OpenAI API TPM rate limit，未形成稳定完整结果。因此建议在论文中暂时不作为主结果，只作为后续工作或补充实验说明。

推荐写法：

> 本文还初步设计了 GPT single-BT baseline，用于比较“LLM 一次生成单个 BT”和“LLM 生成多个候选 BT 后由 selector 选择”的差异。但由于在线 API 调用存在 rate limit，当前实验未作为主要定量结果。该实验设计仍可作为后续工作，用于进一步验证多候选生成与选择机制相较于单次生成的鲁棒性优势。

如果之后补齐实验，可以加入：

- `single_vs_multi_gpt_baseline_summary.csv`
- `single_vs_multi_gpt_baseline_report.md`

## 4.10 本章小结

推荐总结：

> 本章通过四组 BT selection benchmark 验证了本文方法的有效性。实验结果表明，单纯依赖行为树规模或符号成功信息难以稳定选择物理可执行性最优的候选；Transformer BT encoder 能够提供结构表示能力，但需要与任务、世界状态和符号执行特征融合；最终的 V5 learned ensemble 通过融合 selector agreement、symbolic reliability 和 simulation reliability，在困难物理约束任务中显著降低 mean regret，并接近 oracle 上界。整体结果说明，多候选生成与多源评价融合是提升 LLM-generated behavior tree 可执行性的有效途径。

## 推荐正文图表顺序

1. `fig_candidate_simulation_outcomes.png`
2. `fig_success_regret_tradeoff.png`
3. `fig_selector_regret_heatmap.png`
4. `fig_v5_ablation_dual_axis.png`
5. `fig_final_dashboard.png`

## 推荐附录图表

1. `fig_selector_success_heatmap.png`
2. `fig_v5_learned_weights.png`
3. `fig_final_selector_regret.png`
4. `fig_final_selector_success.png`
5. `fig_v5_ablation_regret.png`
6. `fig_v5_ablation_success.png`

