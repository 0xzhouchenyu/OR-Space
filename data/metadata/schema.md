# OR-Space Metadata Schema

## Identifiers

Each task instance has a stable `workspace_id`:

```text
or_space_<three_digit_instance>_<task>
```

Examples:

```text
or_space_001_build
or_space_001_revise
or_space_001_explain
```

## Metadata Index

`metadata/workspace_index.csv` is the release index. It has 300 rows: 100 Build,
100 Revise, and 100 Explain instances.

| Field | Type | Applies To | Description |
| --- | --- | --- | --- |
| `workspace_id` | string | all | Stable benchmark identifier |
| `task_type` | enum | all | `build`, `revise`, or `explain` |
| `instance_number` | int | all | Base topology number |
| `instance_id` | string | all | Source/topology identifier |
| `metadata_path` | path | all | Path to per-instance metadata inside the archive |
| `workspace_path` | path | all | Path to the workspace root inside the archive |
| `difficulty` | string | Build/Revise | Difficulty label when available |
| `original_instance_id` | string | Revise | Source instance identifier for the original requirement |
| `revise_type` | string | Revise | Revision type code |
| `revise_type_name` | string | Revise | Human-readable revision type |
| `diff_summary` | string | Revise | Static summary of source changes |
| `source_revise_instance` | string | Revise/Explain | Linked revise instance |
| `domain` | string | Explain | OR domain label |
| `difficulty_level` | string | Explain | Difficulty label |
| `explain_dimension` | string | Explain | Explanation capability tested |
| `question` | string | Explain | Prompt question |

The participant index deliberately omits reference objectives, Explain
checklists, and expected answers. Those evaluator-only records are published
separately as `oracle/build_revise_objectives.csv` and
`explain_rubrics/rubrics.jsonl`.

## Workspace Archive

The archive expands to:

```text
build-revise-explain_workspaces/
  build_workspaces/
  revise_workspaces/
  explain_workspaces/
```

Build workspaces expose documents, data, sanitized metadata, and an empty
`src/`. The default Revise-code view exposes original/revised documents and
data, the correct original heuristic plus its utility/runtime helpers, and an
empty revised `src/`; it does not expose the formal model or revised reference
implementation. Explain contains validated original and revised documents,
data, reference code, execution logs, and solver records, while its participant
metadata contains the question but no scoring labels.

## Reference Objective Record

Each Build/Revise oracle CSV row includes:

```json
workspace_id,task_type,instance_number,instance_id,reference_objective,relative_tolerance
or_space_001_build,build,1,IndustryOR_1,219816.0,0.01
```

## Versioning

Any change to workspace files, objective values, Explain questions, scoring
rubrics, or `croissant.json` should produce a new Hub commit and, for public
paper results, an immutable release tag.
