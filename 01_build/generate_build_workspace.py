"""
generate_solutions.py

Generate `current_heuristic.py` and `utils.py` for IndustryOR instances through
an OpenAI-compatible endpoint, then write the generated code back to JSON.

Usage:
    python generate_solutions.py [--start 1] [--end 100] [--max_retries 3]
"""

import os
import sys
import json
import glob
import re
import time
import argparse
from openai import OpenAI

# ============================================================
# API configuration
# ============================================================
API_KEY = os.environ.get("OR_SPACE_API_KEY", "REDACTED_SET_ENV_VAR")
BASE_URL = "https://api.modelverse.cn/v1/"
MODEL_NAME = "claude-opus-4-6"

# ============================================================
# Prompt template
# ============================================================

SYSTEM_PROMPT = """You are an expert Operations Research (OR) engineer and mathematical programmer.

Your task is to write a complete, self-contained Python solution for an optimization problem.

## Requirements
1. Read data from CSV files in the `data/` directory (use paths like `os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'filename.csv')`)
2. Formulate and solve the mathematical optimization model
3. Print the optimal objective value in this EXACT format on the LAST line: `OBJECTIVE_VALUE: <number>`

## Available Libraries
- `pulp` (PuLP) - for LP/MIP problems (PREFERRED)
- `scipy.optimize` - for continuous optimization
- Standard library: `csv`, `os`, `sys`, `itertools`, `math`, etc.
- Do NOT use gurobipy, coptpy, or pyomo (they may not be installed)

## Code Structure
You must provide TWO files:

### current_heuristic.py (MAIN solver script)
This is the main entry point. It should:
- Import from utils.py if needed
- Load data from CSV files
- Build and solve the optimization model
- Print `OBJECTIVE_VALUE: <number>` as the last output line

### utils.py (utility functions)
Helper functions for data loading, preprocessing, etc. Can be empty if not needed, but must be valid Python.

## CRITICAL Rules
- The code must be completely self-contained and runnable
- Use `os.path` to construct file paths relative to the script location
- Handle CSV parsing carefully (check headers, data types)
- For minimization problems, minimize; for maximization problems, maximize
- Always print OBJECTIVE_VALUE as the very last line of stdout
- Make sure numerical output matches expected precision

## Output Format
Provide your response in this EXACT format:

```python:current_heuristic.py
# code for current_heuristic.py
```

```python:utils.py
# code for utils.py
```
"""

def build_user_prompt(instance):
    """Build the user prompt from the requirement and data files."""
    blueprint = instance["workspace_blueprint"]
    ground_truth = instance.get("evaluation", {}).get("ground_truth")
    
    parts = []
    
    # Business requirement documents
    docs = blueprint.get("docs", {})
    for doc_name, doc_content in docs.items():
        if doc_content:
            parts.append(f"## Business Requirement ({doc_name})\n{doc_content}")
    
    # Data files
    data_files = blueprint.get("data", {})
    for data_name, data_content in data_files.items():
        if data_content:
            parts.append(f"## Data File: {data_name}\n```csv\n{data_content}\n```")
        else:
            parts.append(f"## Data File: {data_name}\n(empty file)")
    
    # Supply the expected scale as a generation-time consistency check.
    if ground_truth is not None:
        parts.append(f"\n## Hint\nThe expected optimal objective value should be approximately {ground_truth}. "
                     f"Use this to verify your solution is correct. "
                     f"A relative error within 1% is acceptable.")
    
    parts.append("\nPlease write the complete solution code for current_heuristic.py and utils.py.")
    
    return "\n\n".join(parts)


def extract_code_files(response_text):
    """Extract `current_heuristic.py` and `utils.py` from an LLM response."""
    
    heuristic_code = None
    utils_code = None
    
    # First match code blocks that include a filename marker.
    # Pattern 1: ```python:filename
    patterns_heuristic = [
        r'```python:current_heuristic\.py\s*\n(.*?)```',
        r'```python\s*\n#\s*current_heuristic\.py\s*\n(.*?)```',
        r'###\s*current_heuristic\.py.*?```python\s*\n(.*?)```',
        r'`current_heuristic\.py`.*?```python\s*\n(.*?)```',
        r'\*\*current_heuristic\.py\*\*.*?```python\s*\n(.*?)```',
    ]
    
    patterns_utils = [
        r'```python:utils\.py\s*\n(.*?)```',
        r'```python\s*\n#\s*utils\.py\s*\n(.*?)```',
        r'###\s*utils\.py.*?```python\s*\n(.*?)```',
        r'`utils\.py`.*?```python\s*\n(.*?)```',
        r'\*\*utils\.py\*\*.*?```python\s*\n(.*?)```',
    ]
    
    for pattern in patterns_heuristic:
        match = re.search(pattern, response_text, re.DOTALL)
        if match:
            heuristic_code = match.group(1).strip()
            break
    
    for pattern in patterns_utils:
        match = re.search(pattern, response_text, re.DOTALL)
        if match:
            utils_code = match.group(1).strip()
            break
    
    # Fall back to unlabelled Python code blocks.
    if heuristic_code is None:
        all_blocks = re.findall(r'```python\s*\n(.*?)```', response_text, re.DOTALL)
        if len(all_blocks) >= 2:
            # Treat the first block as the solver and the second as utilities.
            heuristic_code = all_blocks[0].strip()
            utils_code = all_blocks[1].strip()
        elif len(all_blocks) == 1:
            heuristic_code = all_blocks[0].strip()
            utils_code = "# utils.py - No utility functions needed for this problem\n"
    
    # Provide a valid empty utility module when none is returned.
    if utils_code is None:
        utils_code = "# utils.py - No utility functions needed for this problem\n"
    
    return heuristic_code, utils_code


def generate_solution_for_instance(client, instance, max_retries=3):
    """Generate solver code for one instance."""
    
    instance_id = instance.get("instance_id", "unknown")
    user_prompt = build_user_prompt(instance)
    
    for attempt in range(max_retries):
        try:
            print(f"  Calling API (attempt {attempt + 1}/{max_retries})...")
            
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=8192,
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Extract generated files.
            heuristic_code, utils_code = extract_code_files(response_text)
            
            if heuristic_code and len(heuristic_code) > 50:
                # Record token usage when the provider returns it.
                usage = response.usage
                tokens_used = usage.total_tokens if usage else 0
                print(f"  Generation succeeded (solver: {len(heuristic_code)} chars, utilities: {len(utils_code)} chars, tokens: {tokens_used})")
                return heuristic_code, utils_code, response_text
            else:
                print("  No valid solver code was extracted; retrying...")
                
        except Exception as e:
            print(f"  API call failed: {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"  Waiting {wait_time}s before retrying...")
                time.sleep(wait_time)
    
    return None, None, None


def natural_sort_key(s):
    """Return a key for natural alphanumeric sorting."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]


def main():
    parser = argparse.ArgumentParser(description="Generate solver code for IndustryOR instances")
    parser.add_argument("--data_dir", type=str, 
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "IndustryOR_Advanced"),
                        help="Directory containing source JSON files")
    parser.add_argument("--start", type=int, default=1, help="First instance number")
    parser.add_argument("--end", type=int, default=100, help="Last instance number")
    parser.add_argument("--max_retries", type=int, default=3, help="Maximum attempts per instance")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between instances in seconds")
    parser.add_argument("--log_dir", type=str, default=None, help="Directory for raw API responses")
    
    args = parser.parse_args()
    
    # Initialize the API client.
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
    )
    
    # Create the response-log directory.
    if args.log_dir is None:
        args.log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generation_logs")
    os.makedirs(args.log_dir, exist_ok=True)
    
    # Load and process instances.
    data_dir = args.data_dir
    success_count = 0
    fail_count = 0
    total = 0
    
    print("=" * 70)
    print("🚀 OR-Space Solution Generator")
    print(f"  Model: {MODEL_NAME}")
    print(f"  Data directory: {data_dir}")
    print(f"  Range: IndustryOR_{args.start} through IndustryOR_{args.end}")
    print("=" * 70)
    
    for i in range(args.start, args.end + 1):
        json_path = os.path.join(data_dir, f"IndustryOR_{i}.json")
        
        if not os.path.exists(json_path):
            print(f"\nMissing file: {json_path}; skipping")
            continue
        
        total += 1
        
        # Load the instance.
        with open(json_path, 'r', encoding='utf-8') as f:
            instance = json.load(f)
        
        instance_id = instance.get("instance_id", f"IndustryOR_{i}")
        ground_truth = instance.get("evaluation", {}).get("ground_truth")
        
        print(f"\n[{total}] Processing {instance_id} (ground_truth: {ground_truth})")
        
        # Skip instances that already contain solver code.
        src = instance.get("workspace_blueprint", {}).get("src", {})
        if src.get("current_heuristic.py") and src["current_heuristic.py"] is not None:
            print("  Solver code already exists; skipping")
            success_count += 1
            continue
        
        # Generate solver code.
        heuristic_code, utils_code, raw_response = generate_solution_for_instance(
            client, instance, max_retries=args.max_retries
        )
        
        if heuristic_code:
            # Write generated code back to the source JSON.
            instance["workspace_blueprint"]["src"]["current_heuristic.py"] = heuristic_code
            instance["workspace_blueprint"]["src"]["utils.py"] = utils_code
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(instance, f, ensure_ascii=False, indent=4)
            
            print(f"  Saved to {json_path}")
            success_count += 1
            
            # Preserve the raw response when requested.
            if raw_response:
                log_path = os.path.join(args.log_dir, f"{instance_id}_response.txt")
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write(raw_response)
        else:
            print("  Generation failed")
            fail_count += 1
        
        # Delay between calls to reduce provider rate-limit pressure.
        if i < args.end:
            time.sleep(args.delay)
    
    # Summary
    print("\n" + "=" * 70)
    print("Generation summary")
    print(f"  Total: {total}")
    print(f"  Succeeded: {success_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Success rate: {success_count/total*100:.1f}%" if total > 0 else "  Success rate: N/A")
    print("=" * 70)


if __name__ == "__main__":
    main()
