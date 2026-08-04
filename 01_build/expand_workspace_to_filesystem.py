#!/usr/bin/env python3
"""Expand Revise JSON records into on-disk workspace directories.

Output layout::

    workspaces_revise/
      i001/
        docs/
          business_requirement.md
          revise_note.md
        data/
          *.csv
        src/
          current_heuristic.py
          utils.py

The script retains original-workspace metadata in the source JSON for
debugging, but materializes only the revised task view.
"""

import json
import os


INPUT_DIR = "IndustryOR_Revise_100_business"
OUTPUT_DIR = "workspaces_revise"


def extract_revise_note(json_obj):
    """Derive the participant-facing revision note from JSON metadata."""
    return f"""# Revise Note

- Revise Type: {json_obj['revise_type_name']}
- Revise Description: {json_obj['revise_description']}
- Original Instance ID: {json_obj['original_instance_id']}
- Revised Instance ID: {json_obj['instance_id']}

This workspace contains an existing solution approach in
`src/current_heuristic.py`. Revise it to satisfy the updated business
requirement in `docs/business_requirement.md`. Treat the files under `data/`
as the source of truth for parameter values and schema.

## What Changed

{json_obj['revise_description']}

Read the revised business requirement carefully and update the model
accordingly.
"""


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for filename in sorted(os.listdir(INPUT_DIR)):
        if not filename.endswith(".json"):
            continue

        number = int(
            filename.replace("IndustryOR_", "").replace(
                "_revise_business.json", ""
            )
        )
        workspace_id = f"i{number:03d}"
        workspace_dir = os.path.join(OUTPUT_DIR, workspace_id)

        with open(os.path.join(INPUT_DIR, filename), encoding="utf-8") as handle:
            record = json.load(handle)

        revised = record["revised_workspace"]
        for directory in ("docs", "data", "src"):
            os.makedirs(os.path.join(workspace_dir, directory), exist_ok=True)

        for name, content in revised["docs"].items():
            with open(
                os.path.join(workspace_dir, "docs", name), "w", encoding="utf-8"
            ) as handle:
                handle.write(content)

        with open(
            os.path.join(workspace_dir, "docs", "revise_note.md"),
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(extract_revise_note(record))

        for name, content in revised["data"].items():
            with open(
                os.path.join(workspace_dir, "data", name), "w", encoding="utf-8"
            ) as handle:
                handle.write(content)

        for name, content in revised["src"].items():
            with open(
                os.path.join(workspace_dir, "src", name), "w", encoding="utf-8"
            ) as handle:
                handle.write(content)

        evaluation = {
            "revised_ground_truth": record["evaluation"]["revised_ground_truth"],
            "original_ground_truth": record["evaluation"]["original_ground_truth"],
            "tolerance": record["evaluation"]["tolerance"],
        }
        with open(
            os.path.join(workspace_dir, "_eval_info.json"),
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(evaluation, handle, indent=2)

        print(f"Prepared workspace: {workspace_id}")


if __name__ == "__main__":
    main()
