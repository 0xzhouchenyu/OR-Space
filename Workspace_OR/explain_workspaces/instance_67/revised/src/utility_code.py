import os
import csv


def load_demand(data_dir):
    demand = {}
    with open(os.path.join(data_dir, "table_1.csv"), "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            month = row["Month"].strip()
            product = row["Product"].strip()
            demand[(month, product)] = float(row["Market_Demand_Units"])
    return demand


def load_parameters(data_dir):
    params = {}
    with open(os.path.join(data_dir, "general_parameters.csv"), "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["Parameter_Name"].strip()
            if not name:
                continue
            params[name] = float(row["Value"])
    return params
