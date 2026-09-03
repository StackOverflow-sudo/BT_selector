# 方法章节算法伪代码

## Algorithm 1: Multi-candidate BT Selection Pipeline

```text
Input:
  task instruction I
  initial world state S0
  candidate generator G
  symbolic executor KIOS
  learned selector F

Output:
  selected behavior tree c*

1. C <- G(I, S0)
2. for each candidate c_i in C do
3.     m_i <- KIOS.execute(c_i, S0)
4.     t_i <- preorder_tokenize(c_i)
5.     z_i <- BTTransformerEncoder(t_i)
6.     x_i <- build_tabular_features(I, S0, c_i, m_i)
7.     score_i <- F(z_i, x_i, m_i)
8. end for
9. c* <- argmax_i score_i
10. return c*
```

## Algorithm 2: BT Token Transformer Encoder

```text
Input:
  behavior tree c
  vocabulary V
  max sequence length L

Output:
  BT embedding z_bt

1. tokens <- preorder_traversal(c)
2. tokens <- truncate_or_pad(tokens, L)
3. ids <- map_tokens_to_ids(tokens, V)
4. E <- token_embedding(ids) + position_embedding(ids)
5. H <- TransformerEncoder(E)
6. z_bt <- mean_pool(H, mask)
7. return z_bt
```

## Algorithm 3: Learned V5 Ensemble Selector

```text
Input:
  candidate c
  selector scores S(c)
  KIOS symbolic metrics M_sym(c)
  physical or simulation metrics M_phy(c)
  learned weights w

Output:
  final score score_V5(c)

1. v_vote <- selector_agreement_features(S(c))
2. v_sym <- symbolic_reliability_features(M_sym(c))
3. v_phy <- physical_reliability_features(M_phy(c))
4. v <- concat(v_vote, v_sym, v_phy)
5. score_V5(c) <- dot(w, v)
6. return score_V5(c)
```

## Algorithm 4: Pairwise Ranking Training

```text
Input:
  training groups D
  true score y(c)
  ranking model F
  margin gamma

Output:
  trained model F

1. for each task-state group g in D do
2.     for each pair (c_i, c_j) in g do
3.         if y(c_i) > y(c_j) then
4.             positive <- c_i
5.             negative <- c_j
6.         else
7.             positive <- c_j
8.             negative <- c_i
9.         end if
10.        s_pos <- F(positive)
11.        s_neg <- F(negative)
12.        loss <- max(0, gamma - s_pos + s_neg)
13.        update F by minimizing loss
14.    end for
15. end for
16. return F
```

## Algorithm 5: Simulation-aware Evaluation

```text
Input:
  selected behavior tree c*
  Isaac Gym environment E
  initial world state S0

Output:
  simulation metrics M_sim

1. initialize Isaac Gym environment E with S0
2. load behavior tree c*
3. execute BT actions in simulation
4. record object poses, contacts, and final state
5. compute:
       sim_success
       final_position_error
       object_displacement_error
       contact_violation_proxy
6. return M_sim
```

