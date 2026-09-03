# 实验部分答辩讲解提纲

## 1. 实验目标

我这部分实验主要验证一个问题：当 LLM 或规则系统生成多个候选行为树时，如何选择一个真正适合机器人执行的 BT。

核心不是只看 BT 是否符号上成功，而是同时考虑：

- 行为树结构是否合理；
- KIOS 符号执行是否可靠；
- 物理放置策略是否稳定；
- Isaac Gym 仿真结果是否支持该选择。

## 2. Benchmark 设计

我设计了四组任务：

- V1：基础 supported-by 放置任务；
- V2：stacking probe，用于测试堆叠任务；
- V2B：physical strategy，用于区分不同物理放置策略；
- V6：hard cases，加入边缘放置、不稳定支撑和更困难的物理约束。

这里可以展示：

- `fig_candidate_simulation_outcomes.png`
- `fig_dataset_simulation_coverage.png`

讲解重点：

> 任务难度是逐步增加的，不是只在简单 block placing 上验证算法。

## 3. Selector 对比

我比较了多个 baseline：

- shortest_tree：选择最短 BT；
- symbolic_only：只看 KIOS 符号成功；
- feature_only：使用人工特征学习排序；
- transformer_only：只使用 BT token Transformer encoder；
- transformer_fused：Transformer + tabular feature；
- V5 learned ensemble：本文最终方法；
- oracle：只作为理论上界。

这里可以展示：

- `fig_success_regret_tradeoff.png`
- `fig_selector_regret_heatmap.png`

讲解重点：

> shortest_tree 表现较差，说明 BT 越短不代表越可靠。symbolic_only 能筛除明显错误，但无法区分物理策略。V5 learned ensemble 在 regret 上更接近 oracle。

## 4. Transformer 的作用

Transformer 部分不是直接替代所有特征，而是作为 BT 结构编码器。

输入：

```text
BT JSON -> preorder tokens -> Transformer encoder -> BT embedding
```

融合：

```text
BT embedding + task/world/symbolic features -> ranking score
```

讲解重点：

> 单独使用 Transformer 受限于数据规模，但 fused model 说明 BT 结构表示对选择任务是有帮助的。

## 5. V5 Learned Ensemble

V5 是最终方法，它融合三类信息：

1. selector agreement；
2. symbolic reliability；
3. physical/simulation reliability。

这里可以展示：

- `fig_v5_ablation_dual_axis.png`
- `fig_v5_learned_weights.png`

讲解重点：

> 消融实验说明，每个模块都有作用。去掉 symbolic 或 simulation reliability 后，mean regret 会明显上升。

## 6. 仿真验证

Isaac Gym 的作用是验证物理执行效果。

KIOS 可以判断行为树逻辑上是否达到目标，但 Isaac Gym 可以进一步反映：

- 放置位置是否稳定；
- 物体是否发生明显偏移；
- 支撑关系是否物理可行；
- 边缘放置是否容易失败。

讲解重点：

> 本项目不是只做文本规划，而是把 BT 生成、符号执行、候选选择和物理仿真连成了完整链路。

## 7. 最终结论

可以这样总结：

> 实验表明，单一启发式或单一模型难以稳定选择最优行为树。本文提出的 V5 learned ensemble 通过融合 BT 结构表示、KIOS 符号执行反馈和仿真可靠性信息，在困难物理任务中降低了 regret，并更接近 oracle 上界。

## 推荐答辩展示顺序

1. `fig_candidate_simulation_outcomes.png`
2. `fig_success_regret_tradeoff.png`
3. `fig_selector_regret_heatmap.png`
4. `fig_v5_ablation_dual_axis.png`
5. `fig_final_dashboard.png`

