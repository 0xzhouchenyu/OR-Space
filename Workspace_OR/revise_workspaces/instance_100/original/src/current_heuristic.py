from gurobi_execution_record import install_gurobi_objective_recorder
install_gurobi_objective_recorder('Advanced_100')
import os
import csv
from itertools import product

def main():
    # Load the bandwidth table
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    filepath = os.path.join(data_dir, 'table_1.csv')
    
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        # Strip whitespace from headers
        nodes = [h.strip() for h in header[1:]]
        
        bandwidth = {}
        for row in reader:
            row_node = row[0].strip()
            for j, val in enumerate(row[1:]):
                col_node = nodes[j]
                bw = int(val.strip())
                bandwidth[(row_node, col_node)] = bw
    
    print(f"Nodes: {nodes}")
    print(f"Bandwidth matrix loaded: {len(bandwidth)} entries")
    
    # We need path from A to E passing through C, no loops
    # Find all simple paths A->C, then all simple paths C->E with no shared intermediate nodes
    
    source = 'A'
    intermediate = 'C'
    target = 'E'
    
    def find_all_simple_paths(start, end, nodes, bandwidth):
        """Find all simple paths from start to end, returns list of (path, min_bandwidth)"""
        results = []
        # DFS
        stack = [(start, [start], float('inf'))]
        while stack:
            current, path, min_bw = stack.pop()
            if current == end:
                results.append((path, min_bw))
                continue
            for next_node in nodes:
                if next_node in path:
                    continue
                bw = bandwidth.get((current, next_node), 0)
                if bw > 0:
                    new_min = min(min_bw, bw)
                    stack.append((next_node, path + [next_node], new_min))
        return results
    
    # Find all simple paths A -> C
    paths_ac = find_all_simple_paths(source, intermediate, nodes, bandwidth)
    # Find all simple paths C -> E
    paths_ce = find_all_simple_paths(intermediate, target, nodes, bandwidth)
    
    print(f"Paths A->C: {len(paths_ac)}")
    for p, bw in paths_ac:
        print(f"  {' -> '.join(p)}, min_bw = {bw}")
    
    print(f"Paths C->E: {len(paths_ce)}")
    for p, bw in paths_ce:
        print(f"  {' -> '.join(p)}, min_bw = {bw}")
    
    # Combine: no repeated nodes (except C which is endpoint of both)
    best_bw = 0
    best_path = None
    
    for path_ac, bw_ac in paths_ac:
        for path_ce, bw_ce in paths_ce:
            # Check no overlapping nodes except C
            nodes_ac = set(path_ac)  # includes A and C
            nodes_ce_interior = set(path_ce) - {intermediate}  # nodes in C->E path except C
            if nodes_ac & nodes_ce_interior:
                continue  # overlap, skip
            
            combined_bw = min(bw_ac, bw_ce)
            if combined_bw > best_bw:
                best_bw = combined_bw
                best_path = path_ac + path_ce[1:]  # merge, avoiding duplicate C
    
    print(f"\nBest path: {' -> '.join(best_path)}")
    print(f"Maximum bandwidth: {best_bw}")
    
    print(f"\nOBJECTIVE_VALUE: {best_bw}")

if __name__ == '__main__':
    main()