# 第 4 章 实验设计与结果分析

## 4.1 本章概述

上一章介绍了本文提出的多候选行为树选择方法。本章通过多组机器人任务规划 benchmark 对所提出方法进行实验验证。实验重点关注以下问题：

1. 多候选行为树选择方法是否优于简单启发式 baseline；
2. KIOS 符号执行特征是否能够有效筛除不可执行候选；
3. BT token Transformer encoder 是否能够为行为树选择提供结构表示信息；
4. V5 hybrid learned selector 是否能够通过融合多源可靠性信息降低候选选择 regret；
5. Isaac Gym 仿真是否能够补充符号执行无法区分的物理策略差异。

围绕上述问题，本文构建了四组逐步增加难度的行为树选择任务，并比较了随机选择、最短行为树、符号成功优先、规则选择器、学习型选择器、Transformer 选择器以及 V5 ensemble 方法等多类 baseline。实验结果表明，简单启发式方法难以稳定选择高质量行为树，而融合符号可靠性、行为树结构表示和物理可靠性的 V5 selector 在困难任务中能够显著降低 mean regret，并更接近 oracle 上界。

## 4.2 实验任务设计

本文构建了四组行为树候选选择 benchmark，用于评估不同难度和不同物理约束下的候选选择性能。每个 benchmark 均由若干任务和初始状态组成。对于每个任务-状态组合，系统提供多个候选行为树，并要求 selector 从候选集合中选择一个最适合执行的行为树。

四组 benchmark 如表 4-1 所示。

| Benchmark | 目的 | 说明 |
| --- | --- | --- |
| V1 supported-by | 基础支持关系验证 | 主要测试 block 放置与 supported-by 关系 |
| V2 stacking probe | 堆叠任务探针 | 引入更长动作链和堆叠关系 |
| V2B physical strategy | 物理策略差异验证 | 用于区分符号相似但放置策略不同的候选 |
| V6 hard cases | 困难物理约束任务 | 包含边缘放置、不稳定支撑和更复杂的初始状态 |

V1 任务主要用于验证系统能否处理基础的支持关系目标，例如将某个 block 放置到另一个 block 上。V2 在此基础上引入 stacking 任务，用于测试较长动作链下的候选选择能力。V2B 重点设计了在符号层面较相似、但物理放置策略不同的候选行为树，例如中心放置和边缘放置。V6 hard cases 进一步引入困难物理约束，用于验证方法在更复杂场景中的鲁棒性。

图 4-1 展示了各 benchmark 的仿真覆盖情况。可以看到，本文实验不仅包含基础任务，还包含具有物理策略差异的复杂任务，从而能够更全面地评估 selector 在符号执行和物理执行层面的表现。

推荐插图：

```text
fig_candidate_simulation_outcomes.png
fig_dataset_simulation_coverage.png
```

## 4.3 对比方法

本文比较了多类候选选择方法。为了全面评估本文方法的有效性，对比方法既包括简单启发式 baseline，也包括学习型 selector 和 oracle 上界。

| 方法 | 类型 | 说明 |
| --- | --- | --- |
| random_expected | 随机 baseline | 随机选择候选行为树的期望结果 |
| first_candidate | 简单 baseline | 选择候选列表中的第一个行为树 |
| shortest_tree | 启发式 baseline | 选择节点数量最少的行为树 |
| symbolic_success | 符号 baseline | 优先选择 KIOS 符号执行成功的候选 |
| rule_based | 规则选择器 | 使用人工设计的符号和结构加权得分 |
| feature_only | 学习型 baseline | 使用 tabular features 的学习排序器 |
| transformer_only | 结构编码 baseline | 仅使用 BT token Transformer 表示 |
| transformer_fused | 融合学习选择器 | 融合 BT embedding 和 tabular features |
| v5_ensemble | 手工 V5 | 手工加权的多源 ensemble selector |
| v5_learned_full | 本文最终方法 | 学习得到的 V5 ensemble selector |
| oracle | 理论上界 | 基于真实得分选择最优候选，仅用于评价 |

其中，oracle 并不参与实际候选选择，只用于计算 selector 与最优选择之间的差距。本文的目标不是超过 oracle，而是在不直接访问真实最优答案的情况下尽可能接近 oracle。

## 4.4 评价指标

本文使用以下指标评价不同 selector 的表现。

| 指标 | 含义 |
| --- | --- |
| Success Rate | 被选中行为树是否达到成功标准 |
| Mean Selected True Score | 被选中行为树的平均真实得分 |
| Mean Regret | oracle 得分与 selector 得分的差距 |
| Pairwise Accuracy | 学习排序模型判断候选相对优劣的准确率 |
| ROC-AUC | 学习排序模型对候选优劣的区分能力 |
| Simulation Success | Isaac Gym 仿真是否成功 |

其中，mean regret 是本文最重要的候选选择质量指标。对于同一任务组，oracle 选择真实得分最高的候选，而某一 selector 选择的候选可能低于 oracle。二者得分差即为 regret：

```text
regret = score_oracle - score_selector
```

mean regret 越低，说明 selector 越接近 oracle。与单纯 success rate 相比，regret 能更细致地反映候选之间的质量差异，尤其适合分析多个候选在符号层面均成功但物理执行质量不同的情况。

## 4.5 数据规模与仿真覆盖

本文主要实验结果来自四组 benchmark 的候选级评估文件。每个候选行为树均记录 KIOS 符号执行结果、结构统计信息以及可用的 Isaac Gym 仿真指标。V6 hard cases 的加入使得最终数据集包含更高比例的困难物理策略样本。

图 4-1 展示了各 benchmark 中候选行为树的仿真结果分布，包括仿真成功、仿真失败、跳过以及缺失状态。该图说明本文并非只在符号环境中评估行为树，而是进一步使用 Isaac Gym 对候选进行物理层面的验证。

推荐插图：

```text
fig_candidate_simulation_outcomes.png
```

推荐表格：

```text
final_dataset_coverage.csv
enhanced_candidate_simulation_outcomes.csv
```

## 4.6 总体实验结果

总体 selector 对比结果如图 4-2 和图 4-3 所示。图 4-2 展示了不同 selector 在 success rate 与 mean regret 之间的权衡关系，图 4-3 通过 heatmap 展示了各 selector 在不同 benchmark 上的 regret 表现。

推荐插图：

```text
fig_success_regret_tradeoff.png
fig_selector_regret_heatmap.png
fig_selector_success_heatmap.png
```

从实验结果可以观察到以下现象。

首先，`shortest_tree` baseline 的表现较弱，说明行为树节点数量较少并不一定意味着执行更可靠。在机器人任务中，过短的行为树可能缺少必要的条件检查或前置动作，从而导致目标无法满足或物理执行不稳定。

其次，`symbolic_success` 和 `rule_based` 方法能够利用 KIOS 符号执行信息筛除明显失败的候选，因此相比最短树启发式更可靠。然而，这类方法主要依赖符号层面的执行结果，难以充分区分符号上均成功但物理策略不同的候选。

再次，`feature_only` 和 `transformer_fused` 方法在多个 benchmark 上表现较稳定。`feature_only` 能够利用任务、世界状态和 KIOS metrics 等 tabular features；`transformer_fused` 则进一步加入行为树结构表示，使模型能够考虑 BT 节点序列和控制结构信息。

最后，V5 ensemble 方法在 mean regret 上更接近 oracle。尤其在 V6 hard cases 中，融合符号可靠性、物理可靠性和基础 selector 一致性的信息能够有效降低错误选择的概率，说明多源评价信号对于困难物理任务具有重要作用。

## 4.7 Transformer BT Encoder 分析

为了分析行为树结构表示的作用，本文比较了 `transformer_only` 和 `transformer_fused` 两种模型。`transformer_only` 仅使用行为树 token 序列经过 Transformer encoder 得到的 embedding 进行排序；`transformer_fused` 则将 BT embedding 与任务特征、世界状态特征和 KIOS 符号执行特征进行融合。

推荐表格：

```text
v4b_transformer_selector_summary.csv
```

推荐插图：

```text
fig_selector_success_by_benchmark.png
fig_selector_regret_by_benchmark.png
```

实验结果表明，仅依赖 Transformer 结构表示的 selector 在当前数据规模下表现有限。这一现象是合理的，因为行为树选择不仅取决于树结构本身，还与具体任务目标、初始状态和符号执行结果密切相关。相比之下，`transformer_fused` 在多个指标上更稳定，说明 BT token encoder 提供的结构信息需要与环境和执行特征结合，才能更有效地服务候选选择。

因此，本文并不将 Transformer 作为唯一决策模块，而是将其定位为行为树结构表示组件。其作用是为 V5 selector 提供补充的结构特征，使最终选择器能够同时考虑 BT 结构、符号执行结果和物理可靠性。

## 4.8 V5 Learned Ensemble 与消融实验

本文最终方法为 V5 hybrid learned selector。该方法融合三类信息：

1. selector agreement；
2. symbolic reliability；
3. physical / simulation reliability。

为了验证各组成模块的贡献，本文进行了消融实验。消融实验结果如图 4-4 所示。

推荐插图：

```text
fig_v5_ablation_dual_axis.png
fig_v5_ablation_regret.png
fig_v5_learned_weights.png
```

推荐表格：

```text
final_v5_learned_ablation.csv
final_v5_learned_weights.csv
```

从消融结果可以看出，完整的 `v5_learned_full` 在 regret 上表现最好或接近最优。当去除 simulation reliability 时，模型难以充分区分符号成功但物理策略不同的候选，导致 regret 上升。当去除 symbolic reliability 时，模型对符号不可执行候选的抑制能力下降，也会影响选择质量。仅使用 selector votes 或仅使用 reliability features 的模型均无法达到完整模型的表现，说明 V5 的优势来自多源信号的互补融合。

需要指出的是，simulation reliability 在离线实验中能够提供更强监督信号，但在实际在线部署中，系统可能无法在选择前对所有候选运行完整仿真。因此，`v5_learned_no_simulation` 可以作为部署前版本，而 `v5_learned_full` 则用于分析在具有仿真反馈时 selector 可达到的性能上界。

## 4.9 Isaac Gym 仿真验证分析

KIOS 符号执行能够判断行为树是否在抽象状态中满足目标，但无法完整表达接触稳定性、物体偏移和边缘放置等物理现象。因此，本文使用 Isaac Gym 对候选行为树进行物理仿真验证。

推荐插图：

```text
fig_candidate_simulation_outcomes.png
fig_dataset_simulation_coverage.png
```

仿真验证结果表明，在 V2B physical strategy 和 V6 hard cases 中，多个候选行为树可能在符号层面均满足目标，但其物理执行质量存在明显差异。例如，中心放置策略通常比边缘放置策略更加稳定；缺少必要条件检查或采用不稳定支撑关系的行为树更容易在仿真中出现物体偏移或执行失败。

因此，仿真结果不是对 KIOS 的替代，而是对符号执行的补充。本文系统采用分层评价思想：先利用 KIOS 进行低成本符号筛选，再通过仿真或物理可靠性估计补充物理执行信息，最终由 V5 selector 融合多源信号完成候选选择。

## 4.10 GPT Single-BT Baseline 补充说明

本文还设计了 GPT single-BT baseline，用于比较“大语言模型一次生成单个行为树”和“大语言模型生成多个候选行为树后由 selector 选择”的差异。该实验流程已经实现，但在实际运行时受到 OpenAI API 请求限制和 token 限制影响，部分调用出现 rate limit。此外，少量调用存在 JSON 输出格式不合法的问题。

因此，该实验目前仅作为补充实验设计和初步分析，不作为本文主要定量结果。该现象也说明，在实际系统中直接依赖 LLM 一次性输出单个 BT 具有一定不稳定性。后续工作可在更稳定的 API 配额或本地模型环境下补充完整的 single-vs-multi 定量比较。

## 4.11 本章小结

本章通过四组行为树候选选择 benchmark 对本文方法进行了系统实验验证。实验结果表明，简单启发式方法如 shortest_tree 无法稳定选择高质量行为树；仅依赖 KIOS 符号成功信息可以筛除明显失败候选，但难以区分物理策略差异；BT token Transformer encoder 能够提供行为树结构表示，但需要与任务、世界状态和符号执行特征融合才能发挥更稳定作用。

最终的 V5 hybrid learned selector 通过融合 selector agreement、symbolic reliability 和 physical reliability，在多个 benchmark 上降低了 mean regret，并在困难物理约束任务中更接近 oracle 上界。消融实验进一步说明，符号可靠性和仿真可靠性均是最终性能的重要来源。整体结果验证了本文提出的多候选生成与多源评价融合框架在机器人行为树选择任务中的有效性。

