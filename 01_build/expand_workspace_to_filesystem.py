#!/usr/bin/env python3
"""把 IndustryOR_Revise_100_business/*.json 拆成真实 workspace 文件夹结构

输出：
workspaces_revise/
    i001/
        docs/
            business_requirement.md
            revise_note.md          (从 JSON metadata 推导)
        data/
            *.csv                  (按文件名)
        src/
            current_heuristic.py    (original model)
            utils.py               (原 utils)
    i002/
    ...

保留 original_workspace 信息用于调试，不实际写入（因为 revise 任务只需要 revised）"""

import json
import os
import pathlib

INPUT_DIR = "IndustryOR_Revise_100_business"
OUTPUT_DIR = "workspaces_revise"


def extract_revise_note(json_obj):
    """从 JSON 元数据推导 revise_note.md"""
    return f"""# Revise Note

- Revise Type: {json_obj['revise_type_name']}
- Revise Description: {json_obj['revise_description']}
- Original Instance ID: {json_obj['original_instance_id']}
- Revised Instance ID: {json_obj['instance_id']}

You are in a workspace that contains an existing solving approach (src/current_heuristic.py).
Your task is to REVISE it to satisfy the business requirement (docs/business_requirement.md).
Use the data files in data/ as the source of truth for parameter values and structure.

## What's Changed

{json_obj['revise_description']}

Read the revised business requirement carefully and modify the model accordingly.
"""


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for fname in sorted(os.listdir(INPUT_DIR)):
        if not fname.endswith(".json"):
            continue

        num = int(fname.replace("IndustryOR_", "").replace("_revise_business.json", ""))
        workspace_id = f"i{num:03d}"
        workspace_dir = os.path.join(OUTPUT_DIR, workspace_id)

        # Load JSON
        with open(os.path.join(INPUT_DIR, fname)) as f:
            obj = json.load(f)

        revised = obj["revised_workspace"]

        # Create folders
        os.makedirs(os.path.join(workspace_dir, "docs"), exist_ok=True)
        os.makedirs(os.path.join(workspace_dir, "data"), exist_ok=True)
        os.makedirs(os.path.join(workspace_dir, "src"), exist_ok=True)

        # Write docs
        for doc_name, content in revised["docs"].items():
            with open(os.path.join(workspace_dir, "docs", doc_name), "w") as f:
                f.write(content)

        # Write revise_note.md
        with open(os.path.join(workspace_dir, "docs", "revise_note.md"), "w") as f:
            f.write(extract_revise_note(obj))

        # Write data
        for csv_name, content in revised["data"].items():
            with open(os.path.join(workspace_dir, "data", csv_name), "w") as f:
                f.write(content)

        # Write src (original model)
        for src_name, content in revised["src"].items():
            with open(os.path.join(workspace_dir, "src", src_name), "w") as f:
                f.write(content)

        # Write evaluation info for reference (not used by LLM)
        eval_info = {
            "revised_ground_truth": obj["evaluation"]["revised_ground_truth"],
            "original_ground_truth": obj["evaluation"]["original_ground_truth"],
            "tolerance": obj["evaluation"]["tolerance"]
        }
        with open(os.path.join(workspace_dir, "_eval_info.json"), "w") as f:
            json.dump(eval_info, f, indent=2)

        print(f"Prepared workspace: {workspace_id}")


if __name__ == "__main__":
    main()
