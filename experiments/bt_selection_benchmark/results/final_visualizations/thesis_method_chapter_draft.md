# 第 3 章 系统方法设计草稿

> 本文档用于整理毕业设计论文中的方法章节。建议与实验章节草稿
> `thesis_experiment_chapter_draft.md` 配合使用。

## 3.1 系统总体架构

本文提出一个面向机器人任务规划的多候选行为树选择系统。系统输入为自然语言任务指令和机器人当前世界状态，输出为一个被选择的行为树，并通过符号执行和物理仿真验证其可执行性。

整体流程如下：

```text
Task instruction + initial world state
        ↓
LLM / candidate generator
        ↓
Multiple BT candidates
        ↓
KIOS symbolic evaluation
        ↓
BT token Transformer encoder
        ↓
Hybrid V5 learned selector
        ↓
Selected BT
        ↓
Isaac Gym simulation validation
```

系统的核心思想是：不直接依赖 LLM 一次性生成唯一行为树，而是生成多个候选 BT，并通过多源评价信号选择更可靠的候选。这样可以缓解 LLM 输出不稳定、符号上可行但物理上不稳定、以及简单启发式无法区分候选质量等问题。

## 3.2 问题定义

给定一个任务指令 \(I\)、初始世界状态 \(S_0\)，候选生成器产生一组行为树候选：

```text
C = {c_1, c_2, ..., c_n}
```

其中每个候选 \(c_i\) 是一个行为树结构，包含条件节点、动作节点以及控制节点。系统目标是学习一个选择函数：

```text
f(I, S_0, c_i) -> score_i
```

并选择得分最高的候选：

```text
c* = argmax score_i
```

评价目标不是仅仅判断候选是否能在符号层面达到目标，而是希望选出的 BT 在符号执行和物理仿真中都具有更高可靠性，并尽可能接近 oracle 选择。

## 3.3 行为树候选生成

候选行为树可以来自三类来源：

1. 规则构造的候选 BT；
2. 已有 benchmark 中预定义的候选 BT；
3. LLM 根据任务指令在线生成的候选 BT。

在 LLM 生成模式下，系统要求模型返回结构化 JSON，包含多个候选行为树：

```json
{
  "candidates": [
    {
      "candidate_id": "stable_center",
      "rationale": "Use a stable center placement strategy.",
      "bt": {
        "type": "sequence",
        "children": []
      }
    }
  ]
}
```

与单次生成一个 BT 相比，多候选生成具有更高容错性。即使某些候选存在条件缺失、动作不稳定或物理策略较差，后续 selector 仍然可以从候选集合中选择更优解。

## 3.4 KIOS 符号执行与可靠性特征

KIOS 在系统中承担符号执行器和行为树验证器的角色。对于每个候选 BT，KIOS 根据初始世界状态执行行为树，并输出符号层面的执行结果和结构统计特征。

主要特征包括：

| 特征 | 含义 |
| --- | --- |
| symbolic_success | 行为树符号执行是否成功 |
| goal_satisfaction | 目标谓词满足程度 |
| bt_ticks | 行为树执行 tick 数 |
| action_count | 动作节点执行数量 |
| condition_failure_count | 条件节点失败次数 |
| invalid_action_count | 无效动作数量 |
| tree_size | 行为树节点数量 |
| tree_depth | 行为树深度 |
| precondition_coverage | 前置条件覆盖程度 |

这些特征可以用于构造 symbolic reliability score。其作用是快速筛除明显不可执行或结构质量较差的候选 BT。

## 3.5 BT Token Transformer Encoder

为了让模型利用行为树结构信息，本文设计了一个轻量级 BT token Transformer encoder。首先将行为树 JSON 按前序遍历转化为 token 序列：

```text
BT JSON -> preorder tokens
```

例如：

```text
sequence condition:is_free action:pick action:place
```

随后 token 被映射为 embedding，并加入位置编码：

```text
token ids -> token embedding + position embedding
```

Transformer encoder 对序列进行上下文建模：

```text
H = TransformerEncoder(E_token + E_position)
```

最后通过 mean pooling 得到行为树级别表示：

```text
z_bt = mean_pool(H)
```

该结构可以表示行为树中控制节点、条件节点和动作节点之间的组合关系。

### 3.5.1 Transformer-only Ranker

Transformer-only ranker 仅使用 BT token embedding 预测候选得分：

```text
score = MLP(z_bt)
```

该模型用于分析行为树结构信息本身的贡献。

### 3.5.2 Transformer-fused Ranker

由于 BT 的执行质量不仅取决于树结构，也取决于任务、世界状态和符号执行反馈，因此本文进一步设计 fused ranker：

```text
z = concat(z_bt, z_tabular)
score = MLP(z)
```

其中 \(z_tabular\) 来自任务特征、候选特征和 KIOS 执行特征。实验表明，fused ranker 比 transformer-only 更适合当前数据规模下的 BT 选择任务。

## 3.6 V5 Hybrid Learned Selector

本文最终方法为 V5 hybrid learned selector。它不是依赖单一模型，而是融合多个互补信号：

1. selector agreement；
2. symbolic reliability；
3. physical / simulation reliability。

### 3.6.1 Selector Agreement

多个基础 selector 会分别对候选 BT 给出排序或得分，例如：

- feature_only；
- transformer_only；
- transformer_fused；
- symbolic_only；
- shortest_tree。

如果多个 selector 都倾向于选择同一个候选，说明该候选具有较高一致性。selector agreement score 用于刻画这种多模型一致性。

### 3.6.2 Symbolic Reliability

symbolic reliability 由 KIOS 执行指标构成，反映候选 BT 的符号可执行性。例如：

```text
symbolic reliability =
  + symbolic_success
  + goal_satisfaction
  + precondition_coverage
  - invalid_action_count
  - condition_failure_count
  - tree_size penalty
```

该部分强调候选 BT 在符号世界中是否逻辑正确。

### 3.6.3 Physical / Simulation Reliability

physical reliability 用于衡量候选 BT 的物理执行质量。对于已经完成 Isaac Gym 仿真的候选，可以使用：

- sim_success；
- final_position_error；
- object_displacement_error；
- contact_violation_proxy。

对于尚未仿真的候选，则可以使用物理策略先验或已有训练数据学习得到的可靠性估计。

### 3.6.4 V5 得分函数

V5 selector 可以表示为：

```text
score_V5(c) =
  w1 * selector_agreement(c)
  + w2 * symbolic_reliability(c)
  + w3 * physical_reliability(c)
```

其中权重可以手动设置，也可以通过已有 benchmark 数据学习得到。本文最终采用 learned V5 ensemble 作为主要方法。

## 3.7 训练目标

学习型 selector 使用 simulation-grounded true score 构造监督信号。对于同一个任务和初始状态下的两个候选 \(c_i\) 和 \(c_j\)，如果真实得分满足：

```text
true_score(c_i) > true_score(c_j)
```

则训练目标希望模型满足：

```text
score(c_i) > score(c_j)
```

因此可以构造 pairwise ranking loss：

```text
L = max(0, margin - score(c_i) + score(c_j))
```

这种 pairwise 训练方式比直接回归真实分数更适合候选选择任务，因为系统真正关心的是在同一任务组内选择相对更优的 BT。

## 3.8 Isaac Gym 仿真验证

Isaac Gym 用于提供物理层面的验证。KIOS 可以判断 BT 在符号状态上是否达到目标，但无法完全判断接触稳定性、边缘放置、物体偏移等物理现象。因此本文使用 Isaac Gym 对候选 BT 进行仿真，并提取仿真指标。

仿真验证的作用包括：

1. 作为最终 true score 的组成部分；
2. 用于训练 simulation-aware selector；
3. 用于分析符号成功但物理失败的候选；
4. 为 demo 页面提供可视化执行结果。

## 3.9 在线推理流程

在线推理阶段，系统流程如下：

1. 输入任务指令和初始状态；
2. 生成多个候选 BT；
3. 对每个 BT 运行 KIOS 符号执行；
4. 将 BT 转换为 token 序列并输入 Transformer encoder；
5. 提取 task/world/symbolic tabular feature；
6. 使用 V5 learned selector 计算候选得分；
7. 选择得分最高的 BT；
8. 可选地运行 Isaac Gym 仿真进行验证或展示。

该流程既支持离线 benchmark 评估，也支持在线 GPT candidate generation demo。

## 3.10 方法小结

本章提出了一个多候选行为树选择系统。与直接依赖 LLM 一次生成单个 BT 的方法不同，本文方法将任务规划拆解为候选生成、符号评估、结构编码、融合选择和仿真验证多个阶段。KIOS 提供低成本符号执行反馈，Transformer encoder 提供行为树结构表示，V5 learned selector 则融合多源可靠性信息进行最终选择。该设计提升了 LLM-generated BT 在机器人任务规划中的可执行性和鲁棒性。

