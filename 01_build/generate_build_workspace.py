"""
generate_solutions.py

调用 Claude API 为每个 IndustryOR 实例生成 current_heuristic.py 和 utils.py，
然后将生成的代码写回 JSON 文件中。

用法：
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
# API 配置
# ============================================================
API_KEY = os.environ.get("OR_SPACE_API_KEY", "REDACTED_SET_ENV_VAR")
BASE_URL = "https://api.modelverse.cn/v1/"
MODEL_NAME = "claude-opus-4-6"

# ============================================================
# Prompt 模板
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
    """构建用户 prompt，包含问题描述和数据"""
    blueprint = instance["workspace_blueprint"]
    ground_truth = instance.get("evaluation", {}).get("ground_truth")
    
    parts = []
    
    # 业务需求文档
    docs = blueprint.get("docs", {})
    for doc_name, doc_content in docs.items():
        if doc_content:
            parts.append(f"## Business Requirement ({doc_name})\n{doc_content}")
    
    # 数据文件
    data_files = blueprint.get("data", {})
    for data_name, data_content in data_files.items():
        if data_content:
            parts.append(f"## Data File: {data_name}\n```csv\n{data_content}\n```")
        else:
            parts.append(f"## Data File: {data_name}\n(empty file)")
    
    # 提示期望的目标值范围（帮助模型理解问题规模）
    if ground_truth is not None:
        parts.append(f"\n## Hint\nThe expected optimal objective value should be approximately {ground_truth}. "
                     f"Use this to verify your solution is correct. "
                     f"A relative error within 1% is acceptable.")
    
    parts.append("\nPlease write the complete solution code for current_heuristic.py and utils.py.")
    
    return "\n\n".join(parts)


def extract_code_files(response_text):
    """从 LLM 回复中提取 current_heuristic.py 和 utils.py 的代码"""
    
    heuristic_code = None
    utils_code = None
    
    # 尝试匹配带文件名标记的代码块
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
    
    # 如果没有找到带标记的代码块，尝试提取所有 python 代码块
    if heuristic_code is None:
        all_blocks = re.findall(r'```python\s*\n(.*?)```', response_text, re.DOTALL)
        if len(all_blocks) >= 2:
            # 假设第一个是 heuristic，第二个是 utils
            heuristic_code = all_blocks[0].strip()
            utils_code = all_blocks[1].strip()
        elif len(all_blocks) == 1:
            heuristic_code = all_blocks[0].strip()
            utils_code = "# utils.py - No utility functions needed for this problem\n"
    
    # 如果 utils 仍然为空，提供默认值
    if utils_code is None:
        utils_code = "# utils.py - No utility functions needed for this problem\n"
    
    return heuristic_code, utils_code


def generate_solution_for_instance(client, instance, max_retries=3):
    """为单个实例生成解决方案代码"""
    
    instance_id = instance.get("instance_id", "unknown")
    user_prompt = build_user_prompt(instance)
    
    for attempt in range(max_retries):
        try:
            print(f"  🤖 调用 API (尝试 {attempt + 1}/{max_retries})...")
            
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
            
            # 提取代码
            heuristic_code, utils_code = extract_code_files(response_text)
            
            if heuristic_code and len(heuristic_code) > 50:
                # Token 统计
                usage = response.usage
                tokens_used = usage.total_tokens if usage else 0
                print(f"  ✅ 代码生成成功 (heuristic: {len(heuristic_code)} chars, utils: {len(utils_code)} chars, tokens: {tokens_used})")
                return heuristic_code, utils_code, response_text
            else:
                print(f"  ⚠️ 未能提取到有效代码，重试...")
                
        except Exception as e:
            print(f"  ❌ API 调用失败: {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"  ⏳ 等待 {wait_time}s 后重试...")
                time.sleep(wait_time)
    
    return None, None, None


def natural_sort_key(s):
    """自然排序"""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]


def main():
    parser = argparse.ArgumentParser(description="为 IndustryOR 实例生成求解代码")
    parser.add_argument("--data_dir", type=str, 
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "IndustryOR_Advanced"),
                        help="JSON 数据目录")
    parser.add_argument("--start", type=int, default=1, help="起始实例编号")
    parser.add_argument("--end", type=int, default=100, help="结束实例编号")
    parser.add_argument("--max_retries", type=int, default=3, help="每个实例最大重试次数")
    parser.add_argument("--delay", type=float, default=2.0, help="每个实例之间的延迟(秒)")
    parser.add_argument("--log_dir", type=str, default=None, help="保存 API 原始回复的目录")
    
    args = parser.parse_args()
    
    # 初始化 API 客户端
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
    )
    
    # 创建日志目录
    if args.log_dir is None:
        args.log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generation_logs")
    os.makedirs(args.log_dir, exist_ok=True)
    
    # 加载并处理实例
    data_dir = args.data_dir
    success_count = 0
    fail_count = 0
    total = 0
    
    print("=" * 70)
    print("🚀 OR-Space Solution Generator")
    print(f"  模型: {MODEL_NAME}")
    print(f"  数据目录: {data_dir}")
    print(f"  范围: IndustryOR_{args.start} ~ IndustryOR_{args.end}")
    print("=" * 70)
    
    for i in range(args.start, args.end + 1):
        json_path = os.path.join(data_dir, f"IndustryOR_{i}.json")
        
        if not os.path.exists(json_path):
            print(f"\n⚠️ 文件不存在: {json_path}, 跳过")
            continue
        
        total += 1
        
        # 加载实例
        with open(json_path, 'r', encoding='utf-8') as f:
            instance = json.load(f)
        
        instance_id = instance.get("instance_id", f"IndustryOR_{i}")
        ground_truth = instance.get("evaluation", {}).get("ground_truth")
        
        print(f"\n[{total}] 处理 {instance_id} (ground_truth: {ground_truth})")
        
        # 检查是否已经有代码
        src = instance.get("workspace_blueprint", {}).get("src", {})
        if src.get("current_heuristic.py") and src["current_heuristic.py"] is not None:
            print(f"  ℹ️ 已有代码，跳过")
            success_count += 1
            continue
        
        # 生成代码
        heuristic_code, utils_code, raw_response = generate_solution_for_instance(
            client, instance, max_retries=args.max_retries
        )
        
        if heuristic_code:
            # 写回 JSON
            instance["workspace_blueprint"]["src"]["current_heuristic.py"] = heuristic_code
            instance["workspace_blueprint"]["src"]["utils.py"] = utils_code
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(instance, f, ensure_ascii=False, indent=4)
            
            print(f"  💾 已保存到 {json_path}")
            success_count += 1
            
            # 保存原始回复日志
            if raw_response:
                log_path = os.path.join(args.log_dir, f"{instance_id}_response.txt")
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write(raw_response)
        else:
            print(f"  ❌ 生成失败!")
            fail_count += 1
        
        # 延迟，避免 API 限流
        if i < args.end:
            time.sleep(args.delay)
    
    # 汇总
    print("\n" + "=" * 70)
    print("📊 生成汇总")
    print(f"  总计: {total}")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  成功率: {success_count/total*100:.1f}%" if total > 0 else "  N/A")
    print("=" * 70)


if __name__ == "__main__":
    main()
