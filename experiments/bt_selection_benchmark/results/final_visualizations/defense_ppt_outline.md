# 毕业设计答辩 PPT 结构设计

> 建议页数：14 页左右  
> 建议时长：8-12 分钟  
> 项目主题：面向机器人任务规划的多候选行为树选择方法

## Slide 1: 标题页

标题建议：

```text
基于 KIOS 与 Transformer 编码的机器人行为树候选选择方法
```

副标题：

```text
LLM-generated Behavior Tree Selection for Robot Task Planning
```

页面内容：

- 学生姓名
- 学号
- 指导老师
- 专业/学院
- 日期

讲解重点：

> 简单说明本项目关注机器人任务规划中“生成多个行为树后如何选择更可靠行为树”的问题。

预计时间：20 秒

## Slide 2: 研究背景

页面标题：

```text
研究背景：从语言任务到机器人可执行行为
```

页面内容：

- LLM 可以根据自然语言生成任务计划；
- 行为树 BT 适合表示机器人任务执行逻辑；
- 但 LLM 生成的 BT 可能存在结构错误、符号不可执行或物理不可执行；
- 因此需要候选生成与选择机制。

可配图：

```text
Task Instruction -> Behavior Tree -> Robot Execution
```

讲解重点：

> 语言模型擅长生成计划，但机器人执行需要更强的可靠性约束。

预计时间：40 秒

## Slide 3: 问题定义

页面标题：

```text
问题定义：多个候选 BT 中选择最优 BT
```

页面内容：

```text
Input:
  task instruction
  initial world state
  candidate BTs

Output:
  selected BT
```

公式：

```text
c* = argmax score(c_i)
```

讲解重点：

> 本项目不是只研究如何生成一个 BT，而是研究当系统有多个候选 BT 时，如何选择最适合执行的一个。

预计时间：40 秒

## Slide 4: 系统总体架构

页面标题：

```text
系统总体架构
```

页面内容：

使用 `system_architecture_mermaid.md` 中的 Overall System Architecture 转成图。

核心流程：

```text
Task + State
  -> BT Candidate Generator
  -> KIOS Symbolic Evaluation
  -> Transformer BT Encoder
  -> V5 Learned Selector
  -> Isaac Gym Validation
```

讲解重点：

> 系统由候选生成、符号评估、结构编码、融合选择和仿真验证五个部分组成。

预计时间：60 秒

## Slide 5: Baseline 论文与任务启发

页面标题：

```text
相关工作与任务设计依据
```

页面内容：

- LLM-as-BT-Planner：启发 LLM 到 BT 的生成流程；
- Points2Plans：启发从场景关系和几何状态到长时序规划；
- MuST / Transformer 类工作：启发 skill/token sequence representation；
- 本文结合以上思想，设计多候选 BT selection 系统。

讲解重点：

> 本项目不是直接复现单篇论文，而是将 LLM-BT 生成、关系任务规划和 Transformer 表示学习结合到 BT 选择问题中。

预计时间：50 秒

## Slide 6: KIOS 符号执行

页面标题：

```text
KIOS 符号执行与可靠性特征
```

页面内容：

列出 KIOS 输出特征：

```text
symbolic_success
goal_satisfaction
precondition_coverage
invalid_action_count
condition_failure_count
tree_size / tree_depth
```

讲解重点：

> KIOS 提供低成本的符号验证，可以快速判断 BT 是否逻辑上可执行，但它不能完全判断物理稳定性。

预计时间：50 秒

## Slide 7: Transformer BT Encoder

页面标题：

```text
BT Token Transformer Encoder
```

页面内容：

使用 `system_architecture_mermaid.md` 中的 Transformer BT Encoder 图。

结构：

```text
BT JSON
  -> preorder tokens
  -> token embeddings
  -> Transformer Encoder
  -> BT embedding
```

讲解重点：

> Transformer 用于编码行为树结构，而不是直接替代所有特征。实验中 fused model 会将 BT embedding 与任务/符号特征结合。

预计时间：60 秒

## Slide 8: V5 Hybrid Learned Selector

页面标题：

```text
V5 Hybrid Learned Selector
```

页面内容：

V5 三类输入：

```text
selector agreement
symbolic reliability
physical / simulation reliability
```

公式：

```text
score_V5(c) =
  w1 * selector_agreement(c)
  + w2 * symbolic_reliability(c)
  + w3 * physical_reliability(c)
```

讲解重点：

> 最终方法不是单一 Transformer，而是融合多源信息的 learned ensemble。这样更符合机器人执行可靠性要求。

预计时间：70 秒

## Slide 9: Benchmark 设计

页面标题：

```text
实验任务设计
```

页面内容：

表格：

| Benchmark | 目标 |
| --- | --- |
| V1 supported-by | 基础支持关系 |
| V2 stacking probe | 堆叠任务 |
| V2B physical strategy | 物理策略差异 |
| V6 hard cases | 困难物理约束 |

推荐图：

```text
fig_candidate_simulation_outcomes.png
```

讲解重点：

> 任务难度逐步增加，V6 用于验证方法在困难物理约束下的表现。

预计时间：60 秒

## Slide 10: Selector 总体对比

页面标题：

```text
总体结果：Success 与 Regret 权衡
```

推荐图：

```text
fig_success_regret_tradeoff.png
```

讲解重点：

> 横轴是 mean regret，越低越好；纵轴是 success rate，越高越好。V5 方法相比简单启发式更接近 oracle。

预计时间：70 秒

## Slide 11: 不同 Benchmark 上的表现

页面标题：

```text
不同任务难度下的 Selector 表现
```

推荐图：

```text
fig_selector_regret_heatmap.png
```

可选补充：

```text
fig_selector_success_heatmap.png
```

讲解重点：

> 热力图展示 selector 在不同 benchmark 上的表现。hard cases 中更能体现物理可靠性和融合选择的重要性。

预计时间：70 秒

## Slide 12: V5 消融实验

页面标题：

```text
V5 消融实验
```

推荐图：

```text
fig_v5_ablation_dual_axis.png
```

讲解重点：

> 去除 symbolic reliability 或 simulation reliability 后，regret 明显上升，说明 V5 的性能来自多源信息融合，而不是单一模块。

预计时间：70 秒

## Slide 13: Demo 展示

页面标题：

```text
系统 Demo：从任务到 BT 选择与仿真
```

页面内容：

展示 Web demo 截图或现场打开：

```text
http://localhost:8091/
```

展示内容：

- 任务定义；
- 多个候选 BT；
- 不同 selector 分数；
- V5 选择结果；
- top-down placement view；
- Isaac Gym replay command。

讲解重点：

> Demo 展示完整链路：任务输入、多候选 BT、选择器评分、最终选择和仿真验证。

预计时间：90 秒

## Slide 14: 总结与贡献

页面标题：

```text
总结与主要贡献
```

页面内容：

主要贡献：

1. 构建了 LLM/BT/KIOS/Isaac Gym 结合的机器人任务规划系统；
2. 设计了多组 BT selection benchmark；
3. 实现了 BT token Transformer encoder；
4. 提出了 V5 hybrid learned selector；
5. 通过仿真和消融实验验证了方法有效性。

讲解重点：

> 本文核心贡献是将多候选生成、符号执行、结构编码和物理可靠性融合到统一的 BT 选择框架中。

预计时间：50 秒

## Slide 15: 展望

页面标题：

```text
未来工作
```

页面内容：

- 补充更大规模 GPT single-vs-multi baseline；
- 增加更多真实机器人或更复杂仿真任务；
- 使用更大规模 Transformer 或图结构模型；
- 引入闭环 BT repair 与在线反馈；
- 将仿真结果用于主动学习和数据扩充。

讲解重点：

> 当前系统已经完成端到端链路，后续可以向更大规模任务、更真实物理环境和闭环修复方向扩展。

预计时间：40 秒

## 推荐总时间分配

| 部分 | 页数 | 时间 |
| --- | ---: | ---: |
| 背景与问题 | 1-3 | 1.5 分钟 |
| 方法设计 | 4-8 | 4 分钟 |
| 实验结果 | 9-12 | 3.5 分钟 |
| Demo 与总结 | 13-15 | 2 分钟 |

总计约 11 分钟。

## 推荐现场演示命令

启动 Web demo：

```bash
cd /home/theshy/projects/mycode/kios_baseline/experiments/gpt_candidate_demo/frontend
python3 -m http.server 8091
```

打开：

```text
http://localhost:8091/
```

如果要刷新 demo 数据：

```bash
cd /home/theshy/projects/mycode/kios_baseline
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 python3 experiments/gpt_candidate_demo/run_gpt_candidate_demo.py \
  --generator existing \
  --candidate-count 4
```

