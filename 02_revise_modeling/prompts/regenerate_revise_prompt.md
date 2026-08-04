# Prompt for Regenerating L5 Revise Tasks

Use this prompt to create one new Revise task for an `IndustryOR_Advanced`
instance with `build_id=X`. The revision must reach L5 structural complexity
through genuine modelling changes while remaining precise, unambiguous, and
business-grounded.

## Design requirements

### 1. Write precise business requirements

- Do not create difficulty through vague language. A phrase such as "add a
  penalty" must identify its coefficient, scope, and unit.
- Give every new parameter a concrete value in `general_parameters.csv` or the
  relevant data file. Name and explain the same parameter, including its unit,
  physical meaning, and scope, in `business_requirement.md`.
- Do not ask the modeller to choose a "reasonable" value or make an unstated
  assumption.
- Make `revise_description` unambiguous. Define terms such as "owned", "in
  inventory", "in pipeline", and "available" exactly once.
- State the mathematical relationship behind every indicator, big-M,
  piecewise, minimum, or maximum rule. For example, distinguish "only if
  `x > 0`" from "the smaller of A and B".
- Do not call a physical resource consumption a setup cost. If activation
  consumes a resource, state that it "consumes N units of X".

### 2. Create logical modelling complexity

The revision should use one or more of these mechanisms:

- **Coupling and cascading:** a new decision changes several existing model
  components. For example, a shared resource requires capacity-allocation
  constraints for every existing activity.
- **Combinatorial logic:** adding or removing variables and constraints
  requires globally consistent changes. For example, a new location, time, or
  skill dimension propagates through all related constraints.
- **Implicit dependency:** a local change affects downstream components. For
  example, a changed replenishment rate alters inventory balance, ordering
  timing, and holding cost.

### 3. Meet the L5 threshold

Let
`ops = (+var, -var, +constr, -constr, mod_constr, mod_obj, mod_data)`.

- `distinct_ops` is the number of nonzero operation types, excluding
  `mod_data`, with a maximum of six.
- `op_count` is the sum of all operation counts.
- `involves_coupling = (add_or_remove_variable) AND
  (modify_constraint OR add_constraint)`.
- `cascading_effect = remove_variable OR
  (add_constraint AND remove_constraint) OR
  (modify_constraint AND add_variable)`.

The task is L5 when either:

1. `distinct_ops >= 4`; or
2. `involves_coupling AND cascading_effect AND op_count >= 5`.

### 4. Use a credible business motivation

- Begin `revise_description` with a concrete motivation such as regulation,
  safety, sustainability, fairness, a changed cost structure, a market rule,
  technical evolution, or a supply-chain restriction.
- Do not add mathematically arbitrary constraints.

### 5. Preserve a valid optimization problem

- The revised model must remain feasible and bounded.
- `revised_ground_truth` must differ from `original_ground_truth`.
- CBC must solve the chosen data scale within 60 seconds.

## Inputs

1. The original JSON file, `IndustryOR_Advanced/IndustryOR_X.json`, containing
   the original `docs`, `data`, `src`, `run`, and ground truth.
2. One retained L5 Revise example as a complexity and style reference, such as
   `IndustryOR_Revise_100/IndustryOR_1_revise_1.json`.

## Required output

Return exactly one JSON object with this structure:

```json
{
  "instance_id": "IndustryOR_X_revise_Y",
  "original_instance_id": "IndustryOR_X",
  "revise_type": "<R1-R5>",
  "revise_type_name": "<Parameter Perturbation | Objective Function Transformation | Constraint Modification | Penalty/Fixed Cost Addition | Scenario Restructuring>",
  "revise_description": "<English, at most 250 characters, beginning with the business motivation and naming every change and parameter>",
  "metadata": {
    "difficulty": "Hard",
    "source_dataset": "IndustryOR",
    "problem_type": "Operations Research",
    "diff": {
      "diff_summary": "+2var, +4constr, mod_3constr, mod_obj, mod_1data",
      "counts": {"+variable": 2, "-variable": 0, "+constraint": 4, "-constraint": 0, "modify_constraint": 3, "modify_objective": 1, "modify_data": 1},
      "op_count": 11,
      "distinct_ops": 4,
      "involves_coupling": true,
      "cascading_effect": true,
      "complexity_level": "L5",
      "level_name": "structural"
    }
  },
  "original_workspace": {"docs": {}, "data": {}, "src": {}, "run": {}},
  "revised_workspace": {
    "docs": {"business_requirement.md": "<complete revised requirement>"},
    "data": {"general_parameters.csv": "<updated parameters>", "table_1.csv": "<updated table if needed>"},
    "src": {"current_heuristic.py": "<complete runnable implementation that prints OBJECTIVE_VALUE: <value>>"},
    "run": {"run.sh": "cd src && python current_heuristic.py"}
  },
  "evaluation": {
    "original_ground_truth": 0.0,
    "revised_ground_truth": 0.0,
    "tolerance": 0.01
  }
}
```

## Internal generation procedure

Do not include this reasoning in the output.

1. Read the original requirement, variables, constraints, objective, and data.
2. Choose a business-appropriate structural theme: hierarchical decisions,
   shared resources, linked constraints, dynamic parameters, a composite
   objective, or mode switching.
3. Draft a revision that adds variables and constraints and modifies existing
   components; avoid a change with only one operation type.
4. Estimate `op_count` and `distinct_ops`. Add meaningful coupling if the
   proposal does not reach L5.
5. Add every new parameter to the data and select values that preserve
   feasibility while changing the optimum.
6. Rewrite the complete implementation and print `OBJECTIVE_VALUE: <value>`.
7. Verify all of the following:
   - the implementation matches `revised_ground_truth` within `1e-3`;
   - the revision satisfies an L5 rule;
   - every parameter in `revise_description` exists in the data;
   - every mathematical relationship and business term is defined in
     `business_requirement.md`; and
   - the motivation is credible rather than complexity for its own sake.

## Prohibited patterns

- Vague penalties, setup costs, averages, or "reasonable" values.
- Parameters present in data but absent from the requirement, or vice versa.
- A changed description without a corresponding code change.
- An unchanged optimum, an infeasible model, or an unbounded model.
- References to nonexistent parameters.
- Logic that cannot be represented as an LP, MILP, or integer program.

## Examples

Bad:

> Introduced a fixed setup cost for initiating pilot training in year 1,
> which consumes available jets. Added a penalty for any trained pilots that
> remain unused in year 2.

This confuses cost with physical consumption, leaves "unused" undefined, and
does not mention the added `min_pilots_year2` parameter.

Good:

> Added a mutual-exclusion rule under which the factory may produce either
> Food I or Food II, but not both, in each week.

This statement defines the time scope and disjunction, introduces no undefined
parameters, and clearly implies a binary indicator with coupled big-M bounds.

## Final instruction

Generate exactly one L5 Revise task for `build_id=X`. Return only the required
JSON object. Before responding, verify every requirement above and ensure that
`current_heuristic.py` executes successfully and matches
`revised_ground_truth`.
