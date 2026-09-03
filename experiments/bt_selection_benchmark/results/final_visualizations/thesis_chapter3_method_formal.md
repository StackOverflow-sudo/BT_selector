# 第 3 章 系统方法设计

## 3.1 本章概述

本章介绍本文提出的面向机器人任务规划的多候选行为树选择方法。针对大语言模型或规则生成器在生成机器人行为树时可能出现的结构不稳定、符号条件缺失以及物理执行可靠性不足等问题，本文将任务规划过程拆分为候选生成、符号评估、结构编码、融合选择和仿真验证五个阶段。系统不直接依赖单个生成结果，而是首先构造多个候选行为树，再通过 KIOS 符号执行、行为树结构编码以及物理可靠性估计对候选进行综合排序，最终选择更适合机器人执行的行为树。

本文方法的整体流程如图 3-1 所示。系统输入为任务指令和初始世界状态，输出为一个被选中的行为树。对于每个候选行为树，系统首先使用 KIOS 进行符号执行，获得目标满足度、前置条件覆盖率、动作执行次数和失败条件数量等指标；随后将行为树结构转化为 token 序列，并通过轻量级 Transformer encoder 得到行为树结构表示；最后，V5 hybrid learned selector 综合多个基础选择器的排序信息、KIOS 符号可靠性特征以及物理/仿真可靠性特征，计算候选行为树的最终得分。

```text
任务指令 + 初始世界状态
        -> 行为树候选生成
        -> KIOS 符号执行
        -> BT Token Transformer Encoder
        -> V5 Hybrid Learned Selector
        -> 被选中的行为树
        -> Isaac Gym 仿真验证
```

该设计的核心思想是通过多源信息融合提高行为树选择的鲁棒性。与仅依赖行为树长度、符号成功与否或单一神经网络得分的方法不同，本文方法同时考虑行为树结构、符号执行结果和物理执行反馈，从而更适合机器人任务规划中对可执行性和稳定性的要求。

## 3.2 问题定义

给定自然语言任务指令 \(I\) 和初始世界状态 \(S_0\)，候选生成器产生一组行为树候选：

```text
C = {c_1, c_2, ..., c_n}
```

其中 \(c_i\) 表示第 \(i\) 个候选行为树，\(n\) 为候选数量。每个行为树由控制节点、条件节点和动作节点组成，用于描述机器人完成任务所需的执行逻辑。本文的目标是学习或构造一个候选选择函数：

```text
F(I, S_0, c_i) -> score_i
```

使系统能够选择得分最高的候选：

```text
c^* = argmax_i F(I, S_0, c_i)
```

在该问题中，评价一个候选行为树的质量不能只依赖其是否在符号层面达到目标。对于机器人操作任务而言，两个候选行为树可能都能满足符号目标，但其物理执行效果不同。例如，候选行为树可能都能实现“将 block3 放到 block5 上”，但一个候选选择中心稳定放置，另一个候选选择边缘放置。二者在符号状态中可能均满足 supported-by 关系，但在物理仿真中后者更容易导致物体偏移或支撑不稳定。因此，本文将行为树选择问题定义为一个综合符号可靠性、结构合理性和物理可执行性的排序问题。

## 3.3 行为树候选生成

行为树候选生成阶段负责为同一任务产生多个可能的执行方案。本文系统支持三类候选来源。

第一类是规则构造的候选行为树。该方式根据任务模板和已知动作模式生成若干候选，适合构建可控 benchmark，并便于分析不同候选之间的结构和物理策略差异。

第二类是已有 benchmark 中预定义的候选行为树。本文在 V1、V2、V2B 和 V6 等任务集中构造了多组候选行为树，用于系统性评估不同选择器的性能。

第三类是由大语言模型生成的候选行为树。在该模式下，系统将任务指令、可用动作、可用条件和输出格式要求组织为 prompt，要求模型返回结构化 JSON 格式的候选集合。与一次只生成一个行为树相比，多候选生成可以提供更大的选择空间。当部分候选存在结构缺陷、条件缺失或物理策略较差时，后续选择器仍有机会从候选集合中选择更可靠的行为树。

LLM 候选输出的基本格式如下：

```json
{
  "candidates": [
    {
      "candidate_id": "stable_center",
      "rationale": "Use a stable placement strategy.",
      "bt": {
        "type": "sequence",
        "children": []
      }
    }
  ]
}
```

其中 `candidate_id` 用于标识候选，`rationale` 用于保存生成理由，`bt` 字段保存行为树结构。为了保证后续 KIOS 解析和执行的稳定性，生成阶段需要限制可用动作集合和条件集合，避免模型产生系统不支持的行为节点。

## 3.4 KIOS 符号执行与特征提取

KIOS 在本文系统中承担符号执行器和行为树验证器的作用。对于每个候选行为树 \(c_i\)，KIOS 根据初始世界状态 \(S_0\) 执行行为树，并输出候选在符号层面的执行结果。该过程可以快速判断行为树是否满足任务目标、是否调用了无效动作，以及是否存在前置条件缺失等问题。

KIOS 输出的主要特征如表 3-1 所示。

| 特征 | 含义 |
| --- | --- |
| symbolic_success | 行为树符号执行是否成功 |
| goal_satisfaction | 目标谓词满足程度 |
| bt_ticks | 行为树执行 tick 次数 |
| action_count | 执行动作节点数量 |
| condition_failure_count | 条件节点失败次数 |
| invalid_action_count | 无效动作数量 |
| tree_size | 行为树节点数量 |
| tree_depth | 行为树最大深度 |
| precondition_coverage | 前置条件覆盖程度 |

基于上述指标，本文构造符号可靠性特征。直观上，一个可靠的行为树应当满足目标谓词、覆盖必要前置条件，并尽量减少无效动作和条件失败。因此，符号可靠性可表示为：

```text
R_sym(c) =
  alpha_1 * symbolic_success
  + alpha_2 * goal_satisfaction
  + alpha_3 * precondition_coverage
  - alpha_4 * invalid_action_count
  - alpha_5 * condition_failure_count
  - alpha_6 * tree_size_penalty
```

其中 \(\alpha\) 为不同特征的权重。该得分不一定作为最终选择结果，而是作为 V5 selector 的输入特征之一。KIOS 的优势在于计算成本较低，可以在仿真之前快速筛除明显不可执行的候选；但其局限是无法完整表达接触、稳定性和物体偏移等物理因素。因此，本文进一步引入行为树结构编码和仿真可靠性信息。

## 3.5 行为树 Token Transformer Encoder

行为树具有层次结构，包含控制节点、条件节点和动作节点。仅使用节点数量或树深度等统计特征难以完整表达行为树内部结构。为此，本文设计了一个轻量级 BT token Transformer encoder，用于将行为树结构编码为连续向量表示。

### 3.5.1 行为树序列化

首先，系统对行为树进行前序遍历，将树结构转化为 token 序列：

```text
BT JSON -> preorder tokens
```

例如，一个简单的行为树可以被序列化为：

```text
sequence condition:is_free action:pick action:place
```

其中控制节点、条件节点和动作节点均被转化为离散 token。随后，token 序列被截断或填充到固定长度 \(L\)，并映射为 token id：

```text
tokens -> token ids
```

### 3.5.2 Transformer 编码

对于 token id 序列，模型首先计算 token embedding 和 position embedding：

```text
E = E_token + E_position
```

然后使用 Transformer encoder 进行上下文建模：

```text
H = TransformerEncoder(E)
```

最后，通过 mean pooling 得到行为树级别的结构表示：

```text
z_bt = MeanPooling(H)
```

该表示 \(z_bt\) 用于描述行为树整体结构。相比手工统计特征，Transformer encoder 能够建模 token 之间的上下文关系，例如条件节点与后续动作节点之间的组合模式、控制节点嵌套关系以及动作序列顺序。

### 3.5.3 Transformer-only 与 Transformer-fused

本文实现了两种基于 Transformer 的排序模型。第一种是 Transformer-only ranker，其仅使用行为树结构表示预测候选得分：

```text
score = MLP(z_bt)
```

该模型用于分析行为树结构信息本身对候选选择的贡献。

第二种是 Transformer-fused ranker。由于候选行为树质量不仅取决于树结构，也取决于任务目标、初始状态和符号执行反馈，因此 fused ranker 将 BT embedding 与 tabular feature 进行拼接：

```text
z = concat(z_bt, z_tabular)
score = MLP(z)
```

其中 \(z_tabular\) 包含任务特征、世界状态特征、KIOS 符号执行指标以及行为树统计特征。实验结果表明，在当前数据规模下，Transformer-only 的提升有限，而 Transformer-fused 能更稳定地利用行为树结构信息。因此，本文将 Transformer encoder 作为结构表示模块，并将其输出融入最终的 V5 selector。

## 3.6 V5 Hybrid Learned Selector

本文最终采用 V5 hybrid learned selector 作为主要候选选择方法。该方法并不依赖单一模型或单一启发式规则，而是融合多个互补信号，包括基础选择器一致性、符号可靠性和物理可靠性。

### 3.6.1 基础选择器一致性

系统首先构建多个基础选择器，例如：

| Selector | 说明 |
| --- | --- |
| feature_only | 使用 tabular feature 的学习排序器 |
| transformer_only | 仅使用 BT token Transformer 表示 |
| transformer_fused | 融合 BT embedding 与 tabular feature |
| symbolic_only | 主要依赖 KIOS 符号执行结果 |
| shortest_tree | 选择节点数量较少的行为树 |

不同基础选择器从不同角度评价候选行为树。如果多个选择器倾向于选择同一个候选，则说明该候选在多种评价标准下都具有较高一致性。因此，本文构造 selector agreement feature，用于刻画候选在多个选择器中的排序情况和得分情况。

### 3.6.2 符号可靠性

符号可靠性来自 KIOS 执行结果，反映行为树在符号状态空间中的逻辑可执行性。该部分特征包括 symbolic_success、goal_satisfaction、precondition_coverage、invalid_action_count 和 condition_failure_count 等。符号可靠性能够有效筛除目标不满足、前置条件缺失或动作非法的候选。

### 3.6.3 物理与仿真可靠性

对于机器人操作任务，仅有符号成功并不足以保证物理执行稳定。本文进一步引入物理可靠性特征。对于已经完成 Isaac Gym 仿真的候选，可以使用以下指标：

| 指标 | 含义 |
| --- | --- |
| sim_success | 仿真是否成功 |
| final_position_error | 最终目标位置误差 |
| object_displacement_error | 物体偏移误差 |
| contact_violation_proxy | 接触违规代理指标 |

对于尚未完成仿真的候选，可以使用物理策略先验或从历史数据中学习得到的仿真可靠性估计。这样可以在保持在线推理效率的同时，引入物理层面的选择偏好。

### 3.6.4 V5 得分函数

V5 selector 的最终得分可以表示为：

```text
score_V5(c) =
  w_1 * R_vote(c)
  + w_2 * R_sym(c)
  + w_3 * R_phy(c)
```

其中 \(R_vote(c)\) 表示基础选择器一致性，\(R_sym(c)\) 表示符号可靠性，\(R_phy(c)\) 表示物理或仿真可靠性，\(w_1, w_2, w_3\) 为融合权重。本文实现了手工权重版本和 learned V5 版本。手工版本用于验证融合策略的合理性，learned V5 则通过已有 benchmark 数据学习各类特征的权重，作为最终方法。

V5 的优势在于，它将结构表示、符号执行反馈和物理执行信息统一到同一选择框架中。即使某一类特征存在噪声，其他特征仍可提供补充信息，从而提升候选选择的鲁棒性。

## 3.7 学习目标与训练方法

学习型选择器的监督信号来自 simulation-grounded true score。对于同一任务和同一初始状态下的候选集合，系统根据符号执行结果、仿真结果和候选质量指标计算每个候选的真实得分。训练目标是使模型在同一候选组内为更优候选分配更高得分。

对于候选 \(c_i\) 和 \(c_j\)，若真实得分满足：

```text
y(c_i) > y(c_j)
```

则模型应满足：

```text
F(c_i) > F(c_j)
```

因此，本文使用 pairwise ranking 方式构造训练样本，并采用 margin ranking loss：

```text
L = max(0, margin - F(c_i) + F(c_j))
```

其中 \(c_i\) 为正样本候选，\(c_j\) 为负样本候选。相较于直接回归绝对分数，pairwise ranking 更符合候选选择问题的本质，因为系统最终关注的是在同一任务组内选择相对更优的行为树。

## 3.8 在线推理流程

在在线推理阶段，系统按照以下步骤选择行为树：

1. 输入任务指令 \(I\) 和初始状态 \(S_0\)；
2. 生成或加载多个候选行为树；
3. 对每个候选运行 KIOS 符号执行；
4. 提取符号执行特征和行为树统计特征；
5. 将行为树转化为前序 token 序列，并输入 Transformer encoder；
6. 计算基础选择器得分和 selector agreement feature；
7. 使用 V5 learned selector 计算最终得分；
8. 选择得分最高的候选行为树；
9. 可选地运行 Isaac Gym 仿真进行验证或展示。

该流程同时支持离线 benchmark 评估和在线 demo 展示。在离线实验中，系统可以使用完整仿真结果评估选择质量；在在线 demo 中，系统可以先根据符号可靠性和 learned selector 选择候选，再根据需要运行仿真验证。

## 3.9 Isaac Gym 仿真验证

Isaac Gym 在本文中用于提供物理层面的验证。KIOS 符号执行能够判断行为树是否在抽象状态中满足目标，但无法完整模拟机器人操作中的接触、碰撞、支撑稳定性和物体偏移。因此，对于候选行为树，本文进一步在 Isaac Gym 中运行仿真，并记录物理执行指标。

仿真验证主要有三方面作用。

首先，仿真结果用于构造 simulation-grounded true score，从而为学习型 selector 提供训练和评价依据。其次，仿真指标可以区分符号上均成功但物理策略不同的候选，例如中心放置与边缘放置。最后，仿真结果也用于系统 demo，使用户能够直观观察被选择行为树的执行效果。

在本文系统中，仿真并不替代符号执行，而是作为更高成本但更接近真实机器人执行的验证信号。系统整体采用分层策略：先利用 KIOS 进行低成本符号筛选，再通过仿真指标提供物理反馈，最终由 V5 selector 融合多源信息完成候选选择。

## 3.10 本章小结

本章提出了一个面向机器人任务规划的多候选行为树选择方法。系统首先生成多个候选行为树，再通过 KIOS 符号执行获得可靠性特征，通过 BT token Transformer encoder 获得结构表示，并通过 V5 hybrid learned selector 融合基础选择器一致性、符号可靠性和物理可靠性，最终选择更适合执行的行为树。

与直接依赖 LLM 一次性生成单个行为树的方法相比，本文方法通过多候选生成和多源评价融合提高了系统鲁棒性。与单一启发式或单一神经网络 selector 相比，V5 selector 能够同时利用行为树结构、符号执行反馈和物理仿真信息，更适合处理机器人任务规划中符号可行但物理执行质量不同的候选选择问题。下一章将通过多组 benchmark 和 Isaac Gym 仿真实验验证本文方法的有效性。

