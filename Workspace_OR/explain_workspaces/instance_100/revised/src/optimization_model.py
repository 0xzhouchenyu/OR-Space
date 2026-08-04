import os
import csv
import gurobi_pulp_compat as pulp

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    filepath = os.path.join(data_dir, 'table_1.csv')
    
    nodes = []
    edges = {}
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        nodes = [h.strip() for h in header[1:]]
        
        for row in reader:
            u = row[0].strip()
            for j, val in enumerate(row[1:]):
                v = nodes[j]
                bw = int(val.strip())
                if bw > 0:
                    edges[(u, v)] = 100 - bw

    prob = pulp.LpProblem("Minimize_Routing_Cost", pulp.LpMinimize)
    
    x1 = pulp.LpVariable.dicts("x1", edges.keys(), cat='Binary')
    x2 = pulp.LpVariable.dicts("x2", edges.keys(), cat='Binary')
    
    prob += pulp.lpSum([edges[e] * (x1[e] + x2[e]) for e in edges])
    
    for n in nodes:
        in_flow1 = pulp.lpSum([x1[(u, n)] for u in nodes if (u, n) in edges])
        out_flow1 = pulp.lpSum([x1[(n, v)] for v in nodes if (n, v) in edges])
        if n == 'A':
            prob += out_flow1 - in_flow1 == 1
        elif n == 'C':
            prob += out_flow1 - in_flow1 == -1
        else:
            prob += out_flow1 - in_flow1 == 0
            
    for n in nodes:
        in_flow2 = pulp.lpSum([x2[(u, n)] for u in nodes if (u, n) in edges])
        out_flow2 = pulp.lpSum([x2[(n, v)] for v in nodes if (n, v) in edges])
        if n == 'C':
            prob += out_flow2 - in_flow2 == 1
        elif n == 'E':
            prob += out_flow2 - in_flow2 == -1
        else:
            prob += out_flow2 - in_flow2 == 0
            
    for n in nodes:
        in_flow_total = pulp.lpSum([x1[(u, n)] for u in nodes if (u, n) in edges]) + \
                        pulp.lpSum([x2[(u, n)] for u in nodes if (u, n) in edges])
        out_flow_total = pulp.lpSum([x1[(n, v)] for v in nodes if (n, v) in edges]) + \
                         pulp.lpSum([x2[(n, v)] for v in nodes if (n, v) in edges])
        
        if n == 'A':
            prob += in_flow_total == 0
            prob += out_flow_total == 1
        elif n == 'E':
            prob += in_flow_total == 1
            prob += out_flow_total == 0
        elif n == 'C':
            prob += in_flow_total == 1
            prob += out_flow_total == 1
        else:
            prob += in_flow_total <= 1
            prob += out_flow_total <= 1
            
    prob.solve(pulp.GUROBI_CMD(msg=False))
    
    print(f"OBJECTIVE_VALUE: {float(pulp.value(prob.objective))}")

if __name__ == '__main__':
    main()
