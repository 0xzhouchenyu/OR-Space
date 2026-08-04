# Empirical difficulty methodology

OR-Space assigns difficulty from observed model performance rather than from a
manual judgment of problem complexity.

## Evaluation evidence

The calculation uses actual benchmark evaluations under a fixed model panel.
All instances within a task use the same evaluation panel and protocol.

## Task-specific signals

- **Build:** empirical percentage of evaluated Build runs that pass executable
  objective evaluation.
- **Revise:** empirical percentage of evaluated Revise-code runs that pass
  executable objective evaluation.
- **Explain:** empirical mean final rubric score across evaluated Explain runs.
  Explain has a
  continuous score and no binary pass/fail threshold, so it is not converted
  into an artificial error count.

Higher values always indicate an easier instance.

## Difficulty partition

Instances are sorted within each task by the corresponding empirical signal.
Two boundaries are selected to make the three groups as close as possible to
equal size while preserving all score ties. Among boundaries between unique
score levels, the release minimizes the squared deviation of the three group
sizes from `100 / 3`. Instances with the same empirical score are never split
across labels.

This produces the following distribution:

| Task | Easy | Medium | Hard |
| --- | ---: | ---: | ---: |
| Build | 35 | 32 | 33 |
| Revise | 39 | 30 | 31 |
| Explain | 33 | 33 | 34 |

## Released fields

`empirical_difficulty.csv` contains:

- `workspace_id`, `task_type`, and `instance_number`;
- the derived `difficulty` label;
- the task-specific `metric` and `empirical_score`;
- `rank_within_task`.

The same label and core evidence are copied into each workspace's
`metadata.json` for convenient task-local access. The CSV is the authoritative
aggregate difficulty index.
