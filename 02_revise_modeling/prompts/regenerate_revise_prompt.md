# Prompt for Regenerating L5-Complexity Revise Tasks

本 prompt 用于为 IndustryOR_Advanced 中的某道题（原题 build_id=X）生成**一条新的 Revise 任务**。
生成的 revise 必须在保持**业务语义清晰、题干表述无歧义**的前提下，通过**结构性改动**使建模难度达到 L5 (structural) 级别。

---

## 🎯 设计原则（必须严格遵守）

### 原则 1: 业务需求表述必须清晰、无歧义
- **不允许**靠模糊表述来制造"难度"（例如"添加一个惩罚"而不说明惩罚系数、作用域、计量单位）
- **所有新参数必须：**
  - 在 `general_parameters.csv` 或对应 CSV 中给出**具体数值**
  - 在 `business_requirement.md` 中**命名并解释**（单位、物理含义、作用范围）
  - 不出现"自行假设"、"合理取值"等字样
- **修改描述 (`revise_description`) 必须单义**：
  - 不使用经济学/工程学中多义的术语（"setup cost" 若是物理消耗必须写明"consumes N units of X"）
  - 任何 indicator / big-M / 分段 / max/min 逻辑必须显式描述对应的**数学关系**（"only if x>0"、"the smaller of A and B"）
  - 所用名词（"owned"、"in inventory"、"in pipeline"、"available"）必须在 business_requirement.md 中有**唯一定义**

### 原则 2: 难度来自建模的逻辑复杂度，不是描述的模糊度
建模难度应通过以下三种机制产生：
- **耦合级联性 (Coupling-Cascading)**：新增操作迫使已有模型结构同步改动。例："增加共享资源 → 需为所有已有活动添加容量分摊约束"。
- **组合逻辑性 (Combinatorial Logic)**：同时增删变量和约束，需保持全局一致性。例："引入新决策维度（地点/时间/技能）→ 所有与该维度相关的约束都需重写"。
- **隐含依赖性 (Implicit Dependency)**：修改看似独立，但实际影响其他组件。例："改变资源再生速度 → 影响库存平衡 → 影响订购节奏 → 影响目标中的持有成本"。

### 原则 3: 必须达到 L5 量化标准
令操作向量 `ops = (+var, -var, +constr, -constr, mod_constr, mod_obj, mod_data)`，记：
- `distinct_ops` = ops 中非零维度的数量（最多 6 维，不含 mod_data）
- `op_count` = ops 各元素之和
- `involves_coupling` = (增/删 var) ∧ (mod_constr 或 +constr)
- `cascading_effect` = (-var) ∨ (+constr ∧ -constr) ∨ (mod_constr ∧ +var)

**L5 判定**（满足其一）：
- (a) `distinct_ops ≥ 4`，**或**
- (b) `involves_coupling ∧ cascading_effect ∧ op_count ≥ 5`

### 原则 4: 修改必须符合真实商业场景
- 每条修改都需有明确的**业务动因**（合规、安全、可持续性、公平性、成本结构变化、市场约束、技术演进、供应链约束等）
- 不允许纯数学拼凑（"再随便加一个大于某数的约束"）
- 在 `revise_description` 开头用一句话说明业务动因（"Due to new environmental regulation..."; "To reflect seasonal workforce fluctuations..."; 等）

### 原则 5: 修改后的问题必须是**可行、有限最优**的
- 不能导致模型不可行或无界
- 修改后最优目标值 (`revised_ground_truth`) 必须与原最优 (`original_ground_truth`) **不同**（否则修改无效）
- 数据规模要确保 CBC 求解 < 60s

---

## 📥 输入（由用户提供）

1. **原题 JSON**：`IndustryOR_Advanced/IndustryOR_X.json`，包含 `original_workspace`（docs / data / src / run）及原题 ground_truth。
2. **保留名单中的一条 L5 revise 样例**：作为复杂度和风格基准（例如 `IndustryOR_Revise_100/IndustryOR_1_revise_1.json`）。

## 📤 输出（模型必须返回单个 JSON，字段如下）

```json
{
  "instance_id": "IndustryOR_X_revise_Y",
  "original_instance_id": "IndustryOR_X",
  "revise_type": "<R1-R5>",
  "revise_type_name": "<one of: Parameter Perturbation | Objective Function Transformation | Constraint Modification | Penalty/Fixed Cost Addition | Scenario Restructuring>",
  "revise_description": "<English, <=250 chars, starts with business motivation, describes all additions/modifications precisely with parameter names>",
  "metadata": {
    "difficulty": "Hard",
    "source_dataset": "IndustryOR",
    "problem_type": "Operations Research",
    "diff": {
      "diff_summary": "<e.g. +2var, +4constr, mod_3constr, mod_obj, mod_1data>",
      "counts": {"+variable": 2, "-variable": 0, "+constraint": 4, "-constraint": 0, "modify_constraint": 3, "modify_objective": 1, "modify_data": 1},
      "op_count": 11,
      "distinct_ops": 4,
      "involves_coupling": true,
      "cascading_effect": true,
      "complexity_level": "L5",
      "level_name": "structural"
    }
  },
  "original_workspace": { "docs": {...}, "data": {...}, "src": {...}, "run": {...} },
  "revised_workspace": {
    "docs": {"business_requirement.md": "<updated, fully describes all changes, no ambiguity, all new parameters named and explained>"},
    "data": {"general_parameters.csv": "<updated with new parameters>", "table_1.csv": "<if modified>"},
    "src": {"current_heuristic.py": "<complete, runnable, correct Pulp/Gurobi code that solves the revised problem and prints OBJECTIVE_VALUE: <value>>"},
    "run": {"run.sh": "cd src && python current_heuristic.py"}
  },
  "evaluation": {
    "original_ground_truth": <float>,
    "revised_ground_truth": <float>,
    "tolerance": 0.01
  }
}
```

## 🧭 生成步骤（模型内部思考流程，不要输出）

1. **读原题**：理解业务、决策变量、约束、目标。
2. **选修改主题**：从以下 L5-friendly 主题中挑一个最贴合业务场景的：
   - **多层级决策 (hierarchical decisions)**：把一个决策拆成多阶段/多情景；例："生产决策 → 拆成生产 + 加班 + 外包"。
   - **共享资源 (shared resources)**：引入新的受限共享资源，所有活动争抢；例："新增共享设备/人力/预算池"。
   - **联动约束 (linked constraints)**：新增一类以"关系"为核心的约束；例："若 A 发生则 B 必须"、"每组至多 k 个同时开启"。
   - **动态参数 (dynamic parameters)**：某参数随时间/规模变化；例："单位成本随产量阶梯变化"。
   - **混合目标 (composite objective)**：主目标 + 次目标（带权和或字典序）；例："最小化成本 - λ·平衡指标"。
   - **可选模式切换 (mode switching)**：引入决策模式变量；例："每个班组在 {早班, 晚班, 休息} 中选其一"。
3. **起草修改描述**：确保主题带来：新变量 + 新约束 + 修改已有约束 + 可能 mod_obj，避免纯单一类型。
4. **量化 diff**：先用 `diff_summary` 估算 `op_count` 和 `distinct_ops`，检查是否达到 L5。若不够，增加耦合。
5. **更新 data**：把新参数写入 CSV；确保数值让问题仍可行且修改后 GT ≠ 原 GT。
6. **重写代码**：基于原 src/current_heuristic.py 改写完整的 pulp/gurobi 代码，打印 `OBJECTIVE_VALUE: <value>`。
7. **自检**：
   - [ ] `revised_ground_truth` 与代码运行结果一致（误差 < 1e-3）
   - [ ] `distinct_ops ≥ 4` 或 `coupling & cascading & op_count ≥ 5`
   - [ ] `revise_description` 中每个提到的新参数都能在 `data` 中找到数值
   - [ ] `business_requirement.md` 中每个数学关系都有文字说明，每个术语都有唯一定义
   - [ ] 修改的业务动因合理（不是"为了复杂而复杂"）

## 🚫 禁止事项

- ❌ 使用模糊术语：如仅写 "add a penalty" / "add a setup cost" 而不给系数和作用域
- ❌ 引入"平均"、"合理"、"适当"等主观字样
- ❌ 数据文件里新增参数但 docs 里没提及（或反之）
- ❌ 不改代码只改描述（会使 evaluation 无效）
- ❌ 修改后 GT 等于原 GT（说明修改空载）
- ❌ 修改导致问题不可行或无界
- ❌ `revise_description` 引用不存在的参数名
- ❌ 用自然语言描述一个无法被 MILP/LP/IP 建模的复杂逻辑（必须落到线性/整数约束）

## ✅ 好例 vs 坏例

**坏例（OR_2_R4 现状，勿复现）**：
> "Introduced a fixed setup cost for initiating pilot training in year 1, which consumes available jets. Added a penalty for any trained pilots that remain unused in year 2."

问题：
- "setup cost" 不是 cost 而是物理消耗——语义错位
- "unused" 的定义没给，需要用 max(0, P-C) 但描述里看不出
- 修改后数据新增了 `min_pilots_year2=17` 但描述里完全没提

**好例（OR_1_R1 现状，可参考）**：
> "Added a mutual exclusion constraint stating that the factory can only produce one type of food (either Food I or Food II) in any given week."

为什么好：
- 单义：mutual exclusion → 显然是 `y_I + y_II ≤ 1`（每周）
- 具体：明确说"each week"、"either…or…"
- 参数完备：不引入任何未定义的数值
- 影响明确：需要引入二值指示变量 y、对产量变量加 big-M 耦合 → 触发 cascading

## 📝 触发 L5 的常见模式模板

模板 A（多阶段决策 + 共享资源，典型 op: +2var, +3constr, mod_2constr, mod_1data → distinct_ops=4）：
> "To model workforce flexibility, the problem now distinguishes between regular-time and overtime production for each product. Overtime production is bounded by `overtime_cap_hours` per week (new parameter in general_parameters.csv, value=X) and costs `overtime_premium_ratio` times the regular unit cost. All existing production-capacity constraints are rewritten to count only regular-time hours, while a new set of constraints caps total overtime hours per week. The objective now includes the overtime premium term."

模板 B（联动 if-then 约束 + 新维度，典型 op: +1var, +2constr, mod_1constr, mod_obj → distinct_ops=4）：
> "An environmental regulation requires that if any quantity of material M is processed at facility F in a given period, a one-time activation fee `activation_fee` must be paid (new parameter), and the total processed amount at F must be at least `min_batch_size` (economies-of-scale rule). Introduce a binary activation variable z[F,t]. All existing capacity constraints at F are modified to link x[F,t] ≤ capacity · z[F,t]. The objective adds the activation cost."

模板 C（分段目标 + 删除变量合并，典型 op: -1var, +1var, +3constr, mod_obj, mod_1data → distinct_ops=4, coupled=True, cascading=True）：
> "The firm reorganized its two previously separate shipping modes (air and truck) into a single aggregated variable `flow[i,j]` with a new tiered cost: 0..100 units cost c1 per unit, 101..500 cost c2, above 500 cost c3 (piecewise linear, three segments). Remove the per-mode shipment variables. Introduce segment-selection binary variables and segment-quantity variables. All per-mode capacity constraints are removed; a single tiered capacity constraint is added."

---

## 🔧 给 LLM 的最终指令（放在 user 消息末尾）

> 基于以上原则和模板，为 build_id=X 生成**一条** L5 级 revise。严格按输出 JSON 模板返回，不要输出任何解释性文字。生成前先 mental-check 是否满足所有 ✅ 条件。确保 `current_heuristic.py` 实际可运行且输出与 `revised_ground_truth` 完全一致。
