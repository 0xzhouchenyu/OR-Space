"""
analyze_revise_complexity.py

分析现有100道Revise任务的操作复杂度，并为metadata添加新的标签。
输出：
  1. 控制台打印分析结果
  2. CSV文件：revise_complexity_analysis.csv
  3. 更新JSON文件中的metadata（可选）
"""

import json
import os
import re
import csv
import difflib
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, '..')
REVISE_DIR = os.path.join(BASE_DIR, 'IndustryOR_Revise_100')
OUTPUT_CSV = os.path.join(BASE_DIR, 'revise_complexity_analysis_v2.csv')


def count_variables(code):
    """Count decision variable declarations in code."""
    # PuLP style
    pulp_vars = re.findall(r'LpVariable(?:\.dicts|Dict)?', code)
    # Gurobi style
    grb_vars = re.findall(r'model\.addVar(?:s)?', code)
    # scipy/cvxpy style
    cvx_vars = re.findall(r'cp\.Variable', code)
    return len(pulp_vars) + len(grb_vars) + len(cvx_vars)


def count_constraints(code):
    """Count constraint additions in code."""
    # PuLP: prob += ... (but not objective)
    # We look for lines with prob += that have >= or <= or ==
    pulp_constrs = len(re.findall(r'prob\s*\+=.*(?:>=|<=|==)', code))
    # Also count prob += with named constraints
    pulp_constrs2 = len(re.findall(r'prob\s*\+=\s*\(', code))
    # Gurobi
    grb_constrs = len(re.findall(r'model\.addConstr', code))
    # subject_to
    subj_constrs = len(re.findall(r'subject_to', code))
    return max(pulp_constrs, pulp_constrs2) + grb_constrs + subj_constrs


def analyze_code_diff(orig_code, rev_code):
    """Analyze the diff between original and revised code to identify operations."""
    operations = {
        '+constraint': 0,
        '-constraint': 0,
        '+variable': 0,
        '-variable': 0,
        'modify_constraint': 0,
        'modify_objective': 0,
        'modify_data': 0,
    }
    
    # Variable count changes
    orig_vars = count_variables(orig_code)
    rev_vars = count_variables(rev_code)
    if rev_vars > orig_vars:
        operations['+variable'] = rev_vars - orig_vars
    elif rev_vars < orig_vars:
        operations['-variable'] = orig_vars - rev_vars
    
    # Constraint count changes
    orig_constrs = count_constraints(orig_code)
    rev_constrs = count_constraints(rev_code)
    if rev_constrs > orig_constrs:
        operations['+constraint'] = rev_constrs - orig_constrs
    elif rev_constrs < orig_constrs:
        operations['-constraint'] = orig_constrs - rev_constrs
    
    # Use difflib to analyze line-level changes
    orig_lines = orig_code.splitlines()
    rev_lines = rev_code.splitlines()
    
    differ = difflib.unified_diff(orig_lines, rev_lines, lineterm='')
    added_lines = []
    removed_lines = []
    for line in differ:
        if line.startswith('+') and not line.startswith('+++'):
            added_lines.append(line[1:])
        elif line.startswith('-') and not line.startswith('---'):
            removed_lines.append(line[1:])
    
    # Check if objective function was modified
    obj_keywords = ['maximize', 'minimize', 'LpMaximize', 'LpMinimize', 'objective', 'lpSum', 'GRB.MAXIMIZE', 'GRB.MINIMIZE']
    obj_modified = any(any(kw.lower() in line.lower() for kw in obj_keywords) for line in added_lines + removed_lines)
    if obj_modified:
        operations['modify_objective'] = 1
    
    # Check if existing constraints were modified (not just added)
    # If we see both removed and added constraint lines, some were modified
    removed_constr_lines = [l for l in removed_lines if any(kw in l for kw in ['prob +=', 'addConstr', 'subject_to', '>=', '<=', '=='])]
    added_constr_lines = [l for l in added_lines if any(kw in l for kw in ['prob +=', 'addConstr', 'subject_to', '>=', '<=', '=='])]
    
    if removed_constr_lines and added_constr_lines:
        # Some constraints were modified (removed old, added new version)
        operations['modify_constraint'] = min(len(removed_constr_lines), len(added_constr_lines))
    
    return operations


def classify_complexity(operations):
    """Classify the complexity level based on operations."""
    op_count = sum(v for v in operations.values())
    
    has_add_var = operations['+variable'] > 0
    has_del_var = operations['-variable'] > 0
    has_add_constr = operations['+constraint'] > 0
    has_del_constr = operations['-constraint'] > 0
    has_modify_constr = operations['modify_constraint'] > 0
    has_modify_obj = operations['modify_objective'] > 0
    
    # Count distinct operation types
    distinct_ops = sum([
        has_add_var, has_del_var, has_add_constr, has_del_constr,
        has_modify_constr, has_modify_obj
    ])
    
    # Coupling: adding/removing variables that affect existing constraints
    involves_coupling = (has_add_var or has_del_var) and (has_modify_constr or has_add_constr)
    
    # Cascading: changes that force other changes
    cascading = has_del_var or (has_del_constr and has_add_constr) or (has_modify_constr and has_add_var)
    
    if distinct_ops >= 4 or (involves_coupling and cascading and op_count >= 5):
        level = 'L5'
        level_name = 'structural'
    elif distinct_ops >= 3 or (involves_coupling and op_count >= 4):
        level = 'L4'
        level_name = 'coupled'
    elif distinct_ops >= 2 or op_count >= 3:
        level = 'L3'
        level_name = 'cross-component'
    elif op_count >= 2:
        level = 'L2'
        level_name = 'multi-step'
    else:
        level = 'L1'
        level_name = 'atomic'
    
    return level, level_name, involves_coupling, cascading


def analyze_data_diff(orig_data, rev_data):
    """Check if data files were modified."""
    new_files = set(rev_data.keys()) - set(orig_data.keys())
    removed_files = set(orig_data.keys()) - set(rev_data.keys())
    modified_files = set()
    for fname in set(orig_data.keys()) & set(rev_data.keys()):
        if orig_data[fname] != rev_data[fname]:
            modified_files.add(fname)
    return len(new_files), len(removed_files), len(modified_files)


def main():
    results = []
    
    for fname in sorted(os.listdir(REVISE_DIR)):
        if not fname.endswith('.json'):
            continue
        
        fpath = os.path.join(REVISE_DIR, fname)
        with open(fpath) as f:
            data = json.load(f)
        
        orig_code = data['original_workspace']['src'].get('current_heuristic.py', '')
        rev_code = data['revised_workspace']['src'].get('current_heuristic.py', '')
        
        # Analyze code diff
        operations = analyze_code_diff(orig_code, rev_code)
        
        # Analyze data diff
        orig_data = data['original_workspace'].get('data', {})
        rev_data = data['revised_workspace'].get('data', {})
        new_data, removed_data, modified_data = analyze_data_diff(orig_data, rev_data)
        if new_data + removed_data + modified_data > 0:
            operations['modify_data'] = new_data + removed_data + modified_data
        
        # Classify
        level, level_name, coupling, cascading = classify_complexity(operations)
        
        # Extract problem info
        instance_id = data.get('instance_id', fname)
        # Parse build_id and revise_id from filename
        # Supports both legacy "IndustryOR_<N>_revise_<k>.json" and the new
        # post-rename "IndustryOR_<N>_revise.json".
        m_new = re.match(r'IndustryOR_(\d+)_revise(?:_(\d+))?\.json$', fname)
        build_id = int(m_new.group(1)) if m_new else 0
        revise_id = int(m_new.group(2)) if (m_new and m_new.group(2)) else 1
        
        # Operation summary string
        op_parts = []
        if operations['+variable'] > 0:
            op_parts.append(f"+{operations['+variable']}var")
        if operations['-variable'] > 0:
            op_parts.append(f"-{operations['-variable']}var")
        if operations['+constraint'] > 0:
            op_parts.append(f"+{operations['+constraint']}constr")
        if operations['-constraint'] > 0:
            op_parts.append(f"-{operations['-constraint']}constr")
        if operations['modify_constraint'] > 0:
            op_parts.append(f"mod_{operations['modify_constraint']}constr")
        if operations['modify_objective'] > 0:
            op_parts.append("mod_obj")
        if operations['modify_data'] > 0:
            op_parts.append(f"mod_{operations['modify_data']}data")
        op_summary = ', '.join(op_parts) if op_parts else 'minimal'
        
        results.append({
            'file': fname,
            'build_id': build_id,
            'revise_id': revise_id,
            'revise_type': data.get('revise_type', ''),
            'revise_type_name': data.get('revise_type_name', ''),
            'old_difficulty': data['metadata'].get('difficulty', ''),
            'new_level': level,
            'level_name': level_name,
            'involves_coupling': coupling,
            'cascading_effect': cascading,
            'operation_summary': op_summary,
            'op_count': sum(v for v in operations.values()),
            **{f'op_{k}': v for k, v in operations.items()},
            'revise_description': data.get('revise_description', '')[:120],
        })
    
    # Print summary
    print("=" * 80)
    print("REVISE COMPLEXITY ANALYSIS")
    print("=" * 80)
    
    level_counts = {}
    for r in results:
        level_counts[r['new_level']] = level_counts.get(r['new_level'], 0) + 1
    
    print("\n=== New Level Distribution ===")
    for level in ['L1', 'L2', 'L3', 'L4', 'L5']:
        count = level_counts.get(level, 0)
        print(f"  {level}: {count} ({count}%)")
    
    print("\n=== Level vs Old Difficulty ===")
    cross = {}
    for r in results:
        key = (r['new_level'], r['old_difficulty'])
        cross[key] = cross.get(key, 0) + 1
    for level in ['L1', 'L2', 'L3', 'L4', 'L5']:
        parts = []
        for diff in ['Easy', 'Medium', 'Hard']:
            parts.append(f"{diff}={cross.get((level, diff), 0)}")
        print(f"  {level}: {', '.join(parts)}")
    
    print("\n=== Coupling & Cascading ===")
    coupling_count = sum(1 for r in results if r['involves_coupling'])
    cascading_count = sum(1 for r in results if r['cascading_effect'])
    print(f"  Involves coupling: {coupling_count}")
    print(f"  Cascading effect: {cascading_count}")
    
    print("\n=== Sample Problems by Level ===")
    for level in ['L1', 'L2', 'L3', 'L4', 'L5']:
        examples = [r for r in results if r['new_level'] == level][:3]
        print(f"\n  {level}:")
        for ex in examples:
            print(f"    {ex['file']}: [{ex['operation_summary']}] {ex['revise_description'][:80]}")
    
    # Write CSV
    fieldnames = ['file', 'build_id', 'revise_id', 'revise_type', 'revise_type_name',
                  'old_difficulty', 'new_level', 'level_name', 'involves_coupling',
                  'cascading_effect', 'operation_summary', 'op_count',
                  'op_+constraint', 'op_-constraint', 'op_+variable', 'op_-variable',
                  'op_modify_constraint', 'op_modify_objective', 'op_modify_data',
                  'revise_description']
    
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n\nResults saved to {OUTPUT_CSV}")
    
    return results


if __name__ == '__main__':
    main()
