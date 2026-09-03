# 10 分钟答辩压缩版 PPT

如果答辩时间较短，建议压缩为 10 页。

## Slide 1: 标题页

```text
基于 KIOS 与 Transformer 编码的机器人行为树候选选择方法
```

时间：20 秒

## Slide 2: 背景与问题

合并原 Slide 2 和 Slide 3。

核心讲法：

> LLM 可以生成机器人任务计划，但生成的 BT 可能存在结构错误、符号不可执行或物理不可执行。因此本文研究如何从多个候选 BT 中选择更可靠的一个。

时间：60 秒

## Slide 3: 系统总体架构

使用总体架构图。

核心讲法：

```text
Candidate generation -> KIOS -> Transformer -> V5 selector -> Isaac Gym
```

时间：80 秒

## Slide 4: KIOS + Transformer 表示

合并 KIOS 符号执行和 Transformer encoder。

核心讲法：

> KIOS 提供符号可靠性，Transformer encoder 提供 BT 结构表示，二者共同为候选选择提供特征。

时间：80 秒

## Slide 5: V5 Learned Selector

展示 V5 三类输入：

```text
selector agreement
symbolic reliability
physical reliability
```

时间：80 秒

## Slide 6: Benchmark 设计

展示四组 benchmark：

```text
V1, V2, V2B, V6
```

推荐图：

```text
fig_candidate_simulation_outcomes.png
```

时间：70 秒

## Slide 7: 总体实验结果

推荐图：

```text
fig_success_regret_tradeoff.png
```

核心讲法：

> V5 learned selector 在 success-regret trade-off 上更接近 oracle。

时间：90 秒

## Slide 8: 消融实验

推荐图：

```text
fig_v5_ablation_dual_axis.png
```

核心讲法：

> 去掉 symbolic 或 simulation reliability 后 regret 上升，说明多源融合有效。

时间：80 秒

## Slide 9: 系统 Demo

展示 Web demo 或截图。

内容：

```text
任务、多候选 BT、选择分数、top-down view、仿真 replay
```

时间：100 秒

## Slide 10: 总结与展望

贡献：

1. 多候选 BT 选择系统；
2. KIOS + Transformer + V5 selector；
3. 多组 benchmark 与 Isaac Gym 验证；
4. 消融实验说明多源融合有效。

时间：60 秒

## 总时间

约 9.5-10 分钟。

