
(function () {
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function fmt(value) {
    var num = Number(value);
    if (!Number.isFinite(num)) return "-";
    return num.toFixed(3).replace(/\.?0+$/, "");
  }

  function cell(row, text, className) {
    var td = el("td", className || "", text);
    row.appendChild(td);
    return td;
  }

  function tag(text, type) {
    return el("span", "tag " + (type || ""), text);
  }

  function installStyles() {
    if (document.getElementById("bt-demo-runtime-style")) return;
    var style = el("style");
    style.id = "bt-demo-runtime-style";
    style.textContent = [
      "[v-cloak] { display: block; }",
      "body { background: #f5f7fb; color: #1f2937; }",
      ".demo-shell { width: min(1440px, calc(100vw - 48px)); margin: 0 auto; padding: 28px 0 42px; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; }",
      ".demo-topbar { display: flex; align-items: center; justify-content: space-between; gap: 24px; margin-bottom: 18px; }",
      ".eyebrow { margin: 0; color: #0875cf; font-size: 13px; font-weight: 800; text-transform: uppercase; }",
      ".demo-topbar h1 { margin: 4px 0 0; font-size: 28px; line-height: 1.2; letter-spacing: 0; }",
      ".demo-actions { display: flex; align-items: center; gap: 12px; }",
      ".demo-button { border: 1px solid #88c2ff; border-radius: 8px; background: #fff; color: #0875cf; padding: 9px 14px; font-weight: 700; cursor: pointer; }",
      ".candidate-select, .case-select { height: 36px; min-width: 210px; border: 1px solid #c8d5e5; border-radius: 8px; background: #fff; color: #1f2937; padding: 0 10px; font-weight: 700; }",
      ".case-select { min-width: 310px; }",
      ".tag { display: inline-flex; align-items: center; min-height: 24px; border-radius: 999px; padding: 3px 10px; background: #eef2f7; color: #344054; font-size: 12px; font-weight: 800; }",
      ".tag.success { background: #5bbf3a; color: #fff; }",
      ".tag.warn { background: #fff1cf; color: #805900; }",
      ".tag.bad { background: #ffe4e4; color: #9a1c1c; }",
      ".status { min-height: 38px; border: 1px solid #d9e1ec; border-radius: 8px; background: #fff; padding: 9px 12px; color: #4b5563; margin-bottom: 16px; }",
      ".status.error { border-color: #f56c6c; color: #9a1c1c; }",
      ".generation-panel { border: 1px solid #d9e1ec; border-radius: 8px; background: #fff; padding: 16px; margin-bottom: 16px; }",
      ".generation-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 12px; }",
      ".generation-head h2 { margin: 0; font-size: 17px; }",
      ".candidate-chips { display: flex; flex-wrap: wrap; gap: 8px; }",
      ".candidate-chip { border: 1px solid #d9e1ec; border-radius: 999px; background: #f8fbff; padding: 6px 10px; font-size: 12px; font-weight: 800; color: #344054; }",
      ".candidate-chip.selected { border-color: #5bbf3a; background: #eef8f0; color: #216e12; }",
      ".generation-note { margin: 10px 0 0; color: #6b7280; font-size: 13px; }",
      ".logic-panel { border: 1px solid #d9e1ec; border-radius: 8px; background: #fff; padding: 16px; margin-bottom: 16px; }",
      ".logic-grid { display: grid; grid-template-columns: minmax(220px, .45fr) minmax(420px, 1fr); gap: 14px; }",
      ".logic-card { border: 1px solid #d9e1ec; border-radius: 8px; background: #fafcff; padding: 12px; }",
      ".logic-card h3 { margin: 0 0 8px; font-size: 14px; }",
      ".logic-card p { margin: 0 0 10px; color: #4b5563; line-height: 1.55; }",
      ".logic-formula { white-space: pre-wrap; overflow-wrap: anywhere; border: 1px solid #d9e1ec; border-radius: 8px; background: #101828; color: #eef6ff; padding: 12px; line-height: 1.45; margin: 0; }",
      ".breakdown-panel { border: 1px solid #d9e1ec; border-radius: 8px; background: #fff; padding: 16px; margin-bottom: 16px; }",
      ".breakdown-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 12px; }",
      ".breakdown-item { border: 1px solid #d9e1ec; border-radius: 8px; background: #fafcff; padding: 12px; }",
      ".breakdown-item span { display: block; color: #6b7280; font-size: 12px; margin-bottom: 8px; }",
      ".breakdown-item strong { display: block; font-size: 20px; overflow-wrap: anywhere; }",
      ".vote-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }",
      ".vote-detail { border: 1px solid #d9e1ec; border-radius: 999px; background: #f8fbff; padding: 6px 10px; font-size: 12px; font-weight: 800; color: #344054; }",
      ".breakdown-table-wrap { overflow: auto; border: 1px solid #d9e1ec; border-radius: 8px; margin-bottom: 12px; }",
      ".breakdown-table { width: 100%; border-collapse: collapse; font-size: 13px; background: #fff; }",
      ".breakdown-table th, .breakdown-table td { padding: 10px 12px; border-bottom: 1px solid #d9e1ec; text-align: left; vertical-align: top; }",
      ".breakdown-table th { background: #f3f6fa; color: #344054; font-weight: 800; white-space: nowrap; }",
      ".breakdown-table tr.total-row td { background: #eef8f0; font-weight: 800; }",
      ".breakdown-table td.numeric { font-variant-numeric: tabular-nums; white-space: nowrap; }",
      ".pipeline { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 16px; }",
      ".step { display: flex; align-items: center; gap: 10px; border: 1px solid #d9e1ec; border-radius: 8px; background: #fff; padding: 12px; }",
      ".step strong { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 50%; background: #1677c7; color: #fff; }",
      ".summary-grid, .main-grid { display: grid; gap: 16px; margin-bottom: 16px; }",
      ".summary-grid { grid-template-columns: 1.25fr 1fr; }",
      ".main-grid { grid-template-columns: minmax(660px, 1.25fr) minmax(430px, .85fr); }",
      ".panel { border: 1px solid #d9e1ec; border-radius: 8px; background: #fff; padding: 16px; min-width: 0; }",
      ".panel-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; }",
      ".panel h2 { margin: 0; font-size: 17px; line-height: 1.3; }",
      ".facts { display: grid; grid-template-columns: 140px minmax(0, 1fr); margin: 0; border: 1px solid #d9e1ec; border-radius: 8px; overflow: hidden; }",
      ".facts dt, .facts dd { margin: 0; padding: 10px 12px; border-bottom: 1px solid #d9e1ec; min-height: 40px; }",
      ".facts dt { background: #f3f6fa; color: #4b5563; font-weight: 700; }",
      ".facts dd { overflow-wrap: anywhere; }",
      ".metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 14px; }",
      ".metric { border: 1px solid #d9e1ec; border-radius: 8px; background: #fafcff; padding: 12px; min-height: 78px; }",
      ".metric span { display: block; color: #6b7280; font-size: 12px; margin-bottom: 9px; }",
      ".metric strong { display: block; font-size: 22px; line-height: 1.1; overflow-wrap: anywhere; }",
      ".selected-line { margin: 8px 0 0; }",
      ".muted { color: #6b7280; }",
      ".table-wrap { max-height: 468px; overflow: auto; border: 1px solid #d9e1ec; border-radius: 8px; }",
      ".candidate-table { width: 100%; border-collapse: collapse; font-size: 13px; }",
      ".candidate-table th, .candidate-table td { padding: 10px 12px; border-bottom: 1px solid #d9e1ec; text-align: left; vertical-align: top; white-space: nowrap; }",
      ".candidate-table th { position: sticky; top: 0; background: #f3f6fa; z-index: 1; }",
      ".candidate-table tr { cursor: pointer; }",
      ".candidate-table tr:hover { background: #f7fbff; }",
      ".candidate-table tr.selected { background: #eef8f0; }",
      ".candidate-name { display: grid; gap: 5px; }",
      ".candidate-name small { color: #6b7280; }",
      ".mini-tags { display: flex; gap: 6px; flex-wrap: wrap; }",
      ".tabs { display: flex; gap: 8px; margin-bottom: 12px; }",
      ".tab { border: 1px solid #d9e1ec; border-radius: 8px; background: #fff; padding: 8px 12px; cursor: pointer; }",
      ".tab.active { background: #1677c7; border-color: #1677c7; color: #fff; }",
      ".command-box, .tree-box { white-space: pre-wrap; overflow-wrap: anywhere; border: 1px solid #d9e1ec; border-radius: 8px; background: #101828; color: #eef6ff; padding: 14px; line-height: 1.5; max-height: 360px; overflow: auto; }",
      ".bt-tree { border: 1px solid #d9e1ec; border-radius: 8px; background: #fbfdff; padding: 12px; max-height: 360px; overflow: auto; }",
      ".bt-tree-row { display: flex; align-items: center; gap: 10px; min-height: 34px; border-bottom: 1px solid #eef2f7; }",
      ".bt-tree-row:last-child { border-bottom: 0; }",
      ".bt-tree-label { overflow-wrap: anywhere; }",
      "@media (max-width: 1180px) { .demo-shell { width: min(100% - 24px, 920px); } .summary-grid, .main-grid, .pipeline, .logic-grid, .breakdown-grid { grid-template-columns: 1fr; } .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }"
    ].join("\n");
    document.head.appendChild(style);
  }

  function treeView(node) {
    var wrap = el("div", "bt-tree");
    appendTreeNode(wrap, node, 0);
    return wrap;
  }

  function appendTreeNode(parent, node, depth) {
    var row = el("div", "bt-tree-row depth-" + depth);
    row.style.paddingLeft = String(depth * 22) + "px";
    row.appendChild(tag(node.type || "node", node.type === "action" ? "success" : node.type === "condition" ? "warn" : ""));
    row.appendChild(el("span", "bt-tree-label", node.label || "node"));
    parent.appendChild(row);
    var children = node.children || [];
    children.forEach(function (child) { appendTreeNode(parent, child, depth + 1); });
  }

  function selectorLogic(selector) {
    var map = {
      v5_ensemble: {
        kind: "V5 proposed ensemble selector",
        formula: [
          "score_v5(c) = 0.55*selector_vote_score(c) + 0.20*symbolic_reliability_norm(c) + 0.25*simulation_reliability_norm(c)",
          "selector_vote_score(c) = 0.30*I(feature_only selects c) + 0.35*I(transformer_fused selects c)",
          "                       + 0.15*I(transformer_only selects c) + 0.10*I(symbolic_only selects c) + 0.05*I(shortest_tree selects c)"
        ].join("\n"),
        note: "This is the proposed final algorithm. It does not use oracle as input; oracle is only used to compute regret. V5 combines agreement among deployable selectors with symbolic and physical reliability evidence."
      },
      feature_only: {
        kind: "Learned pairwise ranker",
        formula: ["score(c) = w dot phi(task, state, BT_candidate)", "training label: true_score(BT_i) > true_score(BT_j)"].join("\n"),
        note: "Uses tabular task/world/BT features such as symbolic_success, goal_satisfaction, tree_size, tree_depth, precondition_coverage, task_id, and candidate_type. Simulation-derived true_score is supervision, not direct input."
      },
      transformer_fused: {
        kind: "Transformer BT encoder + tabular feature ranker",
        formula: ["BT JSON -> preorder tokens -> Transformer Encoder -> mean pooling", "tabular features -> projection", "score(c) = MLP([BT_embedding ; tabular_embedding])"].join("\n"),
        note: "Combines learned BT-structure representation with engineered features. Trained with pairwise ranking loss."
      },
      transformer_only: {
        kind: "Transformer BT-token ranker",
        formula: "BT JSON -> preorder tokens -> token ids -> Transformer Encoder -> mean pooling -> MLP score",
        note: "Ranks candidates from BT token/structure sequence only, without tabular task/world features."
      },
      symbolic_only: {
        kind: "Symbolic heuristic baseline",
        formula: "score(c) = 50*symbolic_success + 20*goal_satisfaction - 0.5*tree_size - 0.3*tree_depth",
        note: "Uses KIOS symbolic execution and BT compactness only; ignores physical simulation errors."
      },
      shortest_tree: {
        kind: "Size heuristic baseline",
        formula: ["score(c) = -tree_size", "choose argmax score(c), i.e. the shortest BT"].join("\n"),
        note: "Tests whether smaller BTs are reliable. It is usually a weak baseline."
      },
      oracle: {
        kind: "Oracle upper bound",
        formula: ["true_score(c) = 100*sim_success + 50*symbolic_success + 20*goal_satisfaction", "              - 10*final_position_error - 5*object_displacement_error", "              - 10*contact_violation_proxy - 0.5*tree_size - 0.3*tree_depth"].join("\n"),
        note: "Not deployable. Uses ground-truth evaluation metrics and serves as an upper bound for regret."
      },
      rule_based_symbolic: {
        kind: "Weighted symbolic rule-based selector",
        formula: ["score(c) = 50*symbolic_success + 20*goal_satisfaction + 15*precondition_coverage", "           - 10*invalid_action_count - 5*condition_failure_count", "           - 0.5*tree_size - 0.3*tree_depth - 0.2*bt_ticks - 0.5*action_count"].join("\n"),
        note: "Manual reliability score over BT structure and KIOS execution metrics."
      },
      rule_based_simulation: {
        kind: "Simulation-aware weighted rule-based selector",
        formula: ["score(c) = symbolic_rule_score(c) + 100*sim_success", "           - 10*final_position_error - 5*object_displacement_error - 10*contact_violation_proxy"].join("\n"),
        note: "Adds Isaac Gym physical execution evidence to the symbolic rule score."
      }
    };
    return map[selector] || { kind: "Unknown selector", formula: "score(c) = unavailable", note: "No scoring description registered for this selector." };
  }

  function selectorLogicPanel(selector) {
    var info = selectorLogic(selector);
    var node = el("section", "logic-panel");
    var head = el("div", "panel-head");
    head.appendChild(el("h2", "", "Selector Scoring Logic"));
    head.appendChild(tag(selector || "selector", "success"));
    node.appendChild(head);
    var grid = el("div", "logic-grid");
    var desc = el("div", "logic-card");
    desc.appendChild(el("h3", "", info.kind));
    desc.appendChild(el("p", "", info.note));
    desc.appendChild(el("h3", "", "Selector-specific scoring rule"));
    desc.appendChild(el("p", "", "The selected candidate is the one with the highest selector-specific score within the same task/state group."));
    grid.appendChild(desc);
    grid.appendChild(el("pre", "logic-formula", info.formula));
    node.appendChild(grid);
    return node;
  }

  function num(value, fallback) {
    var n = Number(value);
    return Number.isFinite(n) ? n : (fallback || 0);
  }

  function addBreakdownRow(tbody, component, rawScore, weight, contribution, detail, className) {
    var row = el("tr", className || "");
    row.appendChild(el("td", "", component));
    row.appendChild(el("td", "numeric", rawScore));
    row.appendChild(el("td", "numeric", weight));
    row.appendChild(el("td", "numeric", contribution));
    row.appendChild(el("td", "", detail || "-"));
    tbody.appendChild(row);
  }

  function present(value) {
    return value !== undefined && value !== null && value !== "";
  }

  function numericCell(value) {
    return present(value) && Number.isFinite(Number(value)) ? fmt(Number(value)) : "-";
  }

  function selectorBreakdownRows(selector, selected) {
    var rows = [];
    function push(component, rawScore, weight, contribution, detail, className) {
      rows.push({ component: component, rawScore: rawScore, weight: weight, contribution: contribution, detail: detail, className: className || "" });
    }

    if (selector === "v5_ensemble") {
      var vote = num(selected.selector_vote_score);
      var symbolicNorm = num(selected.symbolic_reliability_norm);
      var simulationNorm = num(selected.simulation_reliability_norm);
      var symbolicRaw = present(selected.symbolic_reliability_score) ? fmt(selected.symbolic_reliability_score) : "-";
      var simulationRaw = present(selected.simulation_reliability_score) ? fmt(selected.simulation_reliability_score) : "-";
      var voteContribution = 0.55 * vote;
      var symbolicContribution = 0.20 * symbolicNorm;
      var simulationContribution = 0.25 * simulationNorm;
      var computedTotal = voteContribution + symbolicContribution + simulationContribution;
      var total = present(selected.v5_ensemble_score) ? num(selected.v5_ensemble_score) : computedTotal;
      push("Selector vote agreement", fmt(vote), "0.55", fmt(voteContribution), "Weighted vote from feature_only, transformer_fused, transformer_only, symbolic_only, and shortest_tree.");
      push("Symbolic reliability", fmt(symbolicNorm), "0.20", fmt(symbolicContribution), "Group-normalized symbolic score. Raw symbolic score: " + symbolicRaw + ".");
      push("Simulation reliability", fmt(simulationNorm), "0.25", fmt(simulationContribution), "Group-normalized Isaac Gym score. Raw simulation score: " + simulationRaw + ".");
      push("Final V5 ensemble score", "-", "-", fmt(total), "Weighted sum. Recomputed total: " + fmt(computedTotal) + ".", "total-row");
      return rows;
    }

    if (selector === "symbolic_only" || selector === "rule_based_symbolic") {
      var symbolicTotal = 0;
      [["Symbolic success", "symbolic_success", 50, "KIOS execution reaches symbolic success."], ["Goal satisfaction", "goal_satisfaction", 20, "Fraction of goal predicates satisfied."], ["Tree size penalty", "tree_size", -0.5, "Smaller trees are preferred when other scores tie."], ["Tree depth penalty", "tree_depth", -0.3, "Shallower trees are preferred when other scores tie."]].forEach(function (item) {
        var contribution = num(selected[item[1]]) * item[2];
        symbolicTotal += contribution;
        push(item[0], numericCell(selected[item[1]]), String(item[2]), fmt(contribution), item[3]);
      });
      push("Final symbolic score", "-", "-", fmt(symbolicTotal), "Selector chooses the candidate with the highest symbolic score.", "total-row");
      return rows;
    }

    if (selector === "shortest_tree") {
      var shortestScore = -num(selected.tree_size);
      push("Tree size", numericCell(selected.tree_size), "-1.00", fmt(shortestScore), "This selector ignores task/simulation quality and prefers the smallest BT.");
      push("Final shortest-tree score", "-", "-", fmt(shortestScore), "Highest score means smallest tree.", "total-row");
      return rows;
    }

    if (selector === "oracle") {
      var trueTotal = 0;
      [["Simulation success", "sim_success", 100, "Physical execution success in Isaac Gym."], ["Symbolic success", "symbolic_success", 50, "KIOS symbolic execution success."], ["Goal satisfaction", "goal_satisfaction", 20, "Symbolic goal completion ratio."], ["Final position error", "final_position_error", -10, "Lower final pose error is better."], ["Object displacement error", "object_displacement_error", -5, "Lower unintended object movement is better."], ["Contact violation proxy", "contact_violation_proxy", -10, "Lower contact violation proxy is better."], ["Tree size penalty", "tree_size", -0.5, "Compactness tie-breaker."], ["Tree depth penalty", "tree_depth", -0.3, "Depth tie-breaker."]].forEach(function (item) {
        var contribution = num(selected[item[1]]) * item[2];
        trueTotal += contribution;
        push(item[0], numericCell(selected[item[1]]), String(item[2]), fmt(contribution), item[3]);
      });
      var displayedTrue = present(selected.true_score) ? num(selected.true_score) : trueTotal;
      push("Final true score", "-", "-", fmt(displayedTrue), "Oracle uses ground-truth evaluation, so it is an upper-bound baseline.", "total-row");
      return rows;
    }

    if (selector === "rule_based_simulation") {
      var simAwareTotal = 0;
      [["Symbolic success", "symbolic_success", 50, "KIOS symbolic execution success."], ["Goal satisfaction", "goal_satisfaction", 20, "Symbolic goal completion ratio."], ["Precondition coverage", "precondition_coverage", 15, "Coverage of required preconditions."], ["Invalid action penalty", "invalid_action_count", -10, "Penalizes invalid symbolic actions."], ["Condition failure penalty", "condition_failure_count", -5, "Penalizes failed BT conditions."], ["Tree size penalty", "tree_size", -0.5, "Compactness penalty."], ["Tree depth penalty", "tree_depth", -0.3, "Depth penalty."], ["BT ticks penalty", "bt_ticks", -0.2, "Execution efficiency penalty."], ["Action count penalty", "action_count", -0.5, "Action efficiency penalty."], ["Simulation success", "sim_success", 100, "Adds Isaac Gym physical success evidence."], ["Final position error", "final_position_error", -10, "Physical precision penalty."], ["Object displacement error", "object_displacement_error", -5, "Unintended motion penalty."], ["Contact violation proxy", "contact_violation_proxy", -10, "Physical contact-risk penalty."]].forEach(function (item) {
        var contribution = num(selected[item[1]]) * item[2];
        simAwareTotal += contribution;
        push(item[0], numericCell(selected[item[1]]), String(item[2]), fmt(contribution), item[3]);
      });
      push("Final simulation-aware rule score", "-", "-", fmt(simAwareTotal), "Weighted hand-designed score using symbolic and physical evidence.", "total-row");
      return rows;
    }

    if (selector === "feature_only") {
      push("Tabular task/world features", "feature vector", "learned", "model output", "Uses task id, state id, object names, symbolic metrics, BT size/depth, and simulation-grounded labels.");
      push("Pairwise ranking objective", "candidate pairs", "learned", "rank score", "Learns which candidate should rank higher inside the same task/state group.");
      push("Selected candidate true score", numericCell(selected.true_score), "evaluation only", numericCell(selected.true_score), "Shown for explanation; this is not used as an input at test time.", "total-row");
      return rows;
    }

    if (selector === "transformer_only") {
      push("BT preorder tokens", "BT token sequence", "Transformer encoder", "BT embedding", "Converts the BT JSON into a token sequence and encodes structure/order.");
      push("Mean-pooled BT embedding", "embedding", "learned head", "rank score", "Ranks candidates from BT structure alone.");
      push("Selected candidate true score", numericCell(selected.true_score), "evaluation only", numericCell(selected.true_score), "Shown for explanation; this is not used as an input at test time.", "total-row");
      return rows;
    }

    if (selector === "transformer_fused") {
      push("Transformer BT embedding", "BT token sequence", "learned", "BT representation", "Encodes candidate BT structure with the lightweight Transformer.");
      push("Task/world/symbolic features", "tabular vector", "learned", "context representation", "Adds task, initial-state, symbolic, and physical-summary features.");
      push("Fusion ranking head", "BT + context", "learned", "rank score", "Ranks candidates after fusing the BT embedding and tabular context.");
      push("Selected candidate true score", numericCell(selected.true_score), "evaluation only", numericCell(selected.true_score), "Shown for explanation; this is not used as an input at test time.", "total-row");
      return rows;
    }

    push("Selector score", "unavailable", "unavailable", "unavailable", "No selector-specific breakdown has been registered for this selector.", "total-row");
    return rows;
  }

  function selectorBreakdownPanel(selector, selected) {
    var node = el("section", "breakdown-panel");
    var head = el("div", "panel-head");
    head.appendChild(el("h2", "", "Selector Score Breakdown"));
    head.appendChild(tag(selector || "selector", "success"));
    node.appendChild(head);

    var tableWrap = el("div", "breakdown-table-wrap");
    var table = el("table", "breakdown-table");
    var thead = el("thead");
    var headRow = el("tr");
    ["Component", "Raw score", "Weight", "Weighted contribution", "Detail"].forEach(function (name) { headRow.appendChild(el("th", "", name)); });
    thead.appendChild(headRow);
    table.appendChild(thead);
    var tbody = el("tbody");
    selectorBreakdownRows(selector, selected || {}).forEach(function (row) {
      addBreakdownRow(tbody, row.component, row.rawScore, row.weight, row.contribution, row.detail, row.className);
    });
    table.appendChild(tbody);
    tableWrap.appendChild(table);
    node.appendChild(tableWrap);

    if (selector === "v5_ensemble") {
      var details = selected.selector_vote_details || "";
      var note = el("p", "generation-note", details ? "Selector votes supporting this candidate:" : "No component selector voted for this candidate; its V5 score comes from reliability terms only.");
      node.appendChild(note);
      if (details) {
        var voteList = el("div", "vote-list");
        details.split(";").forEach(function (item) { if (item) voteList.appendChild(el("span", "vote-detail", item)); });
        node.appendChild(voteList);
      }
    }
    return node;
  }

  function candidateGenerationPanel(payload, candidates, selectedId) {
    var task = payload.task || {};
    var node = el("section", "generation-panel");
    var head = el("div", "generation-head");
    head.appendChild(el("h2", "", "Candidate Generation"));
    head.appendChild(tag(String(candidates.length) + " BTs generated from one task", "success"));
    node.appendChild(head);

    var chips = el("div", "candidate-chips");
    candidates.forEach(function (item) {
      var chip = el("button", "candidate-chip" + (item.candidate_id === selectedId ? " selected" : ""), item.candidate_id);
      chip.addEventListener("click", function () { render(document.getElementById("app"), payload, item.candidate_id, "tree"); });
      chips.appendChild(chip);
    });
    node.appendChild(chips);

    node.appendChild(el("p", "generation-note", "One task and one initial state are expanded into multiple candidate Behavior Trees. Each candidate is scored symbolically and physically; the selector chooses: " + (task.selected_candidate || "-") + "."));
    return node;
  }

  function facts(rows) {
    var dl = el("dl", "facts");
    rows.forEach(function (pair) {
      dl.appendChild(el("dt", "", pair[0]));
      dl.appendChild(el("dd", "", pair[1] === undefined || pair[1] === null || pair[1] === "" ? "-" : pair[1]));
    });
    return dl;
  }

  function metric(label, value) {
    var node = el("div", "metric");
    node.appendChild(el("span", "", label));
    node.appendChild(el("strong", "", value === undefined || value === null ? "-" : value));
    return node;
  }

  function panel(title, right) {
    var node = el("section", "panel");
    var head = el("div", "panel-head");
    head.appendChild(el("h2", "", title));
    if (right) head.appendChild(right);
    node.appendChild(head);
    return node;
  }

  function render(root, payload, selectedId, tabName) {
    var selectorSets = payload.selector_sets || window.__btSelectorSets || null;
    if (payload.selector_sets) window.__btSelectorSets = payload.selector_sets;
    else if (selectorSets) payload.selector_sets = selectorSets;
    var selectors = payload.selectors || window.__btSelectors || (selectorSets ? Object.keys(selectorSets) : []);
    if (payload.selectors) window.__btSelectors = payload.selectors;
    else if (selectors.length) payload.selectors = selectors;
    var allCases = payload.cases || window.__btDemoCases || [payload];
    if (payload.cases) window.__btDemoCases = payload.cases;
    else payload.cases = allCases;
    var task = payload.task || {};
    var summary = payload.summary || {};
    var candidates = payload.candidates || [];
    var selected = candidates[0] || {};
    candidates.forEach(function (item) { if (item.candidate_id === selectedId) selected = item; });
    if (!selectedId && selected.candidate_id) selectedId = selected.candidate_id;
    tabName = tabName || "score";

    root.textContent = "";
    var shell = el("main", "demo-shell");
    root.appendChild(shell);

    var top = el("section", "demo-topbar");
    var titleBlock = el("div");
    titleBlock.appendChild(el("p", "eyebrow", "KIOS + Transformer BT Selector"));
    titleBlock.appendChild(el("h1", "", "End-to-End BT Selection Demo"));
    top.appendChild(titleBlock);
    var actions = el("div", "demo-actions");
    actions.appendChild(tag("Selector: " + (task.selector || "selector"), "success"));

    if (selectors.length > 1 && selectorSets) {
      var switchSelector = el("button", "demo-button", "Switch Selector");
      switchSelector.addEventListener("click", function () {
        var current = selectors.indexOf(task.selector);
        var nextName = selectors[(current + 1 + selectors.length) % selectors.length];
        var nextCases = selectorSets[nextName].cases || [];
        var nextPayload = nextCases[0] || payload;
        for (var i = 0; i < nextCases.length; i += 1) {
          var nextTask = nextCases[i].task || {};
          if (nextTask.task_id === task.task_id && nextTask.initial_state_id === task.initial_state_id) {
            nextPayload = nextCases[i];
            break;
          }
        }
        nextPayload.selector_sets = selectorSets;
        nextPayload.selectors = selectors;
        nextPayload.cases = nextCases;
        var selectedForNext = nextPayload.task && nextPayload.task.selected_candidate ? nextPayload.task.selected_candidate : "";
        render(root, nextPayload, selectedForNext, "score");
      });
      actions.appendChild(switchSelector);
    }

    var cases = payload.cases || [payload];
    if (cases.length > 1) {
      var caseSelect = el("select", "case-select");
      cases.forEach(function (casePayload, index) {
        var caseTask = casePayload.task || {};
        var option = el("option", "", caseTask.task_id + " / " + caseTask.initial_state_id);
        option.value = String(index);
        if (caseTask.task_id === task.task_id && caseTask.initial_state_id === task.initial_state_id) option.selected = true;
        caseSelect.appendChild(option);
      });
      caseSelect.addEventListener("change", function () {
        var nextPayload = cases[Number(caseSelect.value)];
        nextPayload.selector_sets = selectorSets;
        nextPayload.selectors = selectors;
        nextPayload.cases = cases;
        var nextTask = nextPayload.task || {};
        var nextSelected = nextTask.selected_candidate || (nextPayload.candidates && nextPayload.candidates.length ? nextPayload.candidates[0].candidate_id : "");
        render(root, nextPayload, nextSelected, "score");
      });
      actions.appendChild(caseSelect);
    }

    var candidateSelect = el("select", "candidate-select");
    candidates.forEach(function (item) {
      var option = el("option", "", item.candidate_id);
      option.value = item.candidate_id;
      if (item.candidate_id === selected.candidate_id) option.selected = true;
      candidateSelect.appendChild(option);
    });
    candidateSelect.addEventListener("change", function () { render(root, payload, candidateSelect.value, tabName); });
    actions.appendChild(candidateSelect);

    var randomButton = el("button", "demo-button", "Random Task");
    randomButton.addEventListener("click", function () {
      var cases = payload.cases || [payload];
      if (!cases.length) return;
      var index = Math.floor(Math.random() * cases.length);
      var nextPayload = cases[index];
      nextPayload.selector_sets = selectorSets;
      nextPayload.selectors = selectors;
      nextPayload.cases = cases;
      var nextTask = nextPayload.task || {};
      var nextSelected = nextTask.selected_candidate || (nextPayload.candidates && nextPayload.candidates.length ? nextPayload.candidates[0].candidate_id : "");
      render(root, nextPayload, nextSelected, "score");
    });
    actions.appendChild(randomButton);

    var reload = el("button", "demo-button", "Refresh Data");
    reload.addEventListener("click", init);
    actions.appendChild(reload);
    top.appendChild(actions);
    shell.appendChild(top);

    shell.appendChild(el("section", "status", "Loaded " + (payload.cases ? payload.cases.length : 1) + " task cases and " + (selectors.length || 1) + " selectors. Current task/state generated " + candidates.length + " candidate BTs. Model selected: " + (task.selected_candidate || "-") + ". Viewing: " + (selected.candidate_id || "-")));

    var pipeline = el("section", "pipeline");
    ["Task Definition", "Generate Candidate BTs", "KIOS + Simulation Scoring", "Select and Execute"].forEach(function (label, index) {
      var step = el("div", "step");
      step.appendChild(el("strong", "", index + 1));
      step.appendChild(el("span", "", label));
      pipeline.appendChild(step);
    });
    shell.appendChild(pipeline);
    shell.appendChild(candidateGenerationPanel(payload, candidates, selected.candidate_id));
    shell.appendChild(selectorLogicPanel(task.selector));
    shell.appendChild(selectorBreakdownPanel(task.selector, selected));


    var summaryGrid = el("section", "summary-grid");
    var taskPanel = panel("Task Definition", tag(task.initial_state_id || "state"));
    taskPanel.appendChild(facts([
      ["Task ID", task.task_id],
      ["Instruction", task.instruction],
      ["Target", task.target_predicate],
      ["Objects", (task.moved_object || "-") + " -> " + (task.support_object || "-")]
    ]));
    summaryGrid.appendChild(taskPanel);

    var resultPanel = panel("Selection Result", tag("regret " + fmt(summary.regret), Number(summary.regret || 0) <= 0.001 ? "success" : "warn"));
    var metrics = el("div", "metric-grid");
    metrics.appendChild(metric("Candidate BTs", summary.candidate_count));
    metrics.appendChild(metric("Symbolic Success", summary.symbolic_success_count));
    metrics.appendChild(metric("Simulation Success", summary.sim_success_count));
    metrics.appendChild(metric("Best Score", fmt(summary.best_true_score)));
    resultPanel.appendChild(metrics);
    resultPanel.appendChild(el("p", "selected-line", "Selected: " + (task.selected_candidate || selected.candidate_id || "-")));
    resultPanel.appendChild(el("p", "selected-line muted", "Oracle：" + (task.oracle_candidate || "-")));
    summaryGrid.appendChild(resultPanel);
    shell.appendChild(summaryGrid);

    var main = el("section", "main-grid");
    var tablePanel = panel("Candidate BTs Rank");
    var wrap = el("div", "table-wrap");
    var table = el("table", "candidate-table");
    var thead = el("thead");
    var hrow = el("tr");
    ["BT", "True", "KIOS", "Sim", "Position Err", "Displace Err", "Size/Depth"].forEach(function (name) { hrow.appendChild(el("th", "", name)); });
    thead.appendChild(hrow);
    table.appendChild(thead);
    var tbody = el("tbody");
    candidates.slice().sort(function (a, b) { return Number(b.true_score || 0) - Number(a.true_score || 0); }).forEach(function (item) {
      var row = el("tr", item.candidate_id === selected.candidate_id ? "selected" : "");
      row.addEventListener("click", function () { render(root, payload, item.candidate_id, "score"); });
      var nameCell = el("td");
      var nameBox = el("div", "candidate-name");
      nameBox.appendChild(el("strong", "", item.candidate_id));
      nameBox.appendChild(el("small", "", item.candidate_type));
      var mini = el("div", "mini-tags");
      if (item.is_selected) mini.appendChild(tag("selected", "success"));
      if (item.is_oracle) mini.appendChild(tag("oracle", "warn"));
      nameBox.appendChild(mini);
      nameCell.appendChild(nameBox);
      row.appendChild(nameCell);
      cell(row, fmt(item.true_score));
      cell(row, item.symbolic_success ? "ok" : "fail");
      cell(row, item.sim_success ? "ok" : "no");
      cell(row, fmt(item.final_position_error));
      cell(row, fmt(item.object_displacement_error));
      cell(row, String(item.tree_size) + "/" + String(item.tree_depth));
      tbody.appendChild(row);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);
    tablePanel.appendChild(wrap);
    main.appendChild(tablePanel);

    var detailPanel = panel("Selected BT Details", tag(selected.candidate_id || "candidate"));
    var tabs = el("div", "tabs");
    ["score", "tree", "command"].forEach(function (name) {
      var label = name === "score" ? "Scores" : name === "tree" ? "Tree Structure" : "Simulation Command";
      var button = el("button", "tab" + (tabName === name ? " active" : ""), label);
      button.addEventListener("click", function () { render(root, payload, selected.candidate_id, name); });
      tabs.appendChild(button);
    });
    detailPanel.appendChild(tabs);
    if (tabName === "tree") {
      if (selected.tree) detailPanel.appendChild(treeView(selected.tree));
      else detailPanel.appendChild(el("pre", "tree-box", "The current result file does not contain full BT JSON. It can be loaded from bt_path later."));
    } else if (tabName === "command") {
      detailPanel.appendChild(el("pre", "command-box", selected.run_command || "No command found."));
    } else {
      detailPanel.appendChild(facts([
        ["Candidate", selected.candidate_id],
        ["True score", fmt(selected.true_score)],
        ["Goal satisfaction", fmt(selected.goal_satisfaction)],
        ["Precondition coverage", fmt(selected.precondition_coverage)],
        ["Final position error", fmt(selected.final_position_error)],
        ["Object displacement error", fmt(selected.object_displacement_error)],
        ["Execution", selected.execution_result]
      ]));
    }
    main.appendChild(detailPanel);
    shell.appendChild(main);
  }

  async function init() {
    installStyles();
    var root = document.getElementById("app");
    root.textContent = "";
    var shell = el("main", "demo-shell");
    root.appendChild(shell);
    var status = el("section", "status", "Loading demo_data.json...");
    shell.appendChild(status);
    try {
      var response = await fetch("./demo_data.json?v=" + Date.now(), { cache: "no-store" });
      if (!response.ok) throw new Error("demo_data.json HTTP " + response.status);
      var payload = await response.json();
      var selected = payload.task && payload.task.selected_candidate ? payload.task.selected_candidate : "";
      render(root, payload, selected, "score");
    } catch (err) {
      status.className = "status error";
      status.textContent = "Data loading failed: " + err.message + ". Please open the page through http://localhost:8088/ and make sure demo_data.json has been generated.";
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
