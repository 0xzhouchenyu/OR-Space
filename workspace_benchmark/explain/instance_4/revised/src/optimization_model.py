import os
import gurobi_pulp_compat as pulp
from utils import load_parameters

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))

cow_price = params['cow_selling_price']
sheep_price = params['sheep_selling_price']
chicken_price = params['chicken_selling_price']

cow_feed = params['cow_feed_cost']
sheep_feed = params['sheep_feed_cost']
chicken_feed = params['chicken_feed_cost']

cow_manure = params['cow_manure_production']
sheep_manure = params['sheep_manure_production']
chicken_manure = params['chicken_manure_production']

max_manure = params['max_manure_capacity']
max_chickens = int(params['max_chickens'])
min_cows = int(params['min_cows'])
min_sheep = int(params['min_sheep'])
max_total = int(params['max_total_animals'])

premium_capacity_multiplier = params['premium_capacity_multiplier']
premium_manure_multiplier = params['premium_manure_multiplier']
expansion_cost = params['expansion_cost']
premium_feed_multiplier = params['premium_feed_multiplier']

base_land_usage_cow = params['base_land_usage_cow']
base_land_usage_sheep = params['base_land_usage_sheep']
base_land_usage_chicken = params['base_land_usage_chicken']
base_land_capacity = params['base_land_capacity']
expansion_land_increase = params['expansion_land_increase']

prob = pulp.LpProblem("FarmProfit_Revised", pulp.LpMaximize)

cows_regular = pulp.LpVariable("cows_regular", lowBound=0, cat='Integer')
cows_premium = pulp.LpVariable("cows_premium", lowBound=0, cat='Integer')
sheep_regular = pulp.LpVariable("sheep_regular", lowBound=0, cat='Integer')
sheep_premium = pulp.LpVariable("sheep_premium", lowBound=0, cat='Integer')
chickens_regular = pulp.LpVariable("chickens_regular", lowBound=0, cat='Integer')
chickens_premium = pulp.LpVariable("chickens_premium", lowBound=0, cat='Integer')

z_expand = pulp.LpVariable("z_expand", cat='Binary')

cows_total = cows_regular + cows_premium
sheep_total = sheep_regular + sheep_premium
chickens_total = chickens_regular + chickens_premium

prob += cows_total >= min_cows
prob += sheep_total >= min_sheep
prob += chickens_total <= max_chickens

prob += cows_total + sheep_total + chickens_total <= max_total + (premium_capacity_multiplier * max_total - max_total) * z_expand

prob += cow_manure * cows_total + sheep_manure * sheep_total + chicken_manure * chickens_total <= max_manure + (premium_manure_multiplier * max_manure - max_manure) * z_expand

prob += base_land_usage_cow * cows_total + base_land_usage_sheep * sheep_total + base_land_usage_chicken * chickens_total <= base_land_capacity + expansion_land_increase * z_expand

prob += cows_premium <= premium_capacity_multiplier * max_total * z_expand
prob += sheep_premium <= premium_capacity_multiplier * max_total * z_expand
prob += chickens_premium <= max_chickens * z_expand

cow_profit_reg = cow_price - cow_feed
cow_profit_prem = cow_price - premium_feed_multiplier * cow_feed
sheep_profit_reg = sheep_price - sheep_feed
sheep_profit_prem = sheep_price - premium_feed_multiplier * sheep_feed
chicken_profit_reg = chicken_price - chicken_feed
chicken_profit_prem = chicken_price - premium_feed_multiplier * chicken_feed

prob += (cow_profit_reg * cows_regular + cow_profit_prem * cows_premium
         + sheep_profit_reg * sheep_regular + sheep_profit_prem * sheep_premium
         + chicken_profit_reg * chickens_regular + chicken_profit_prem * chickens_premium
         - expansion_cost * z_expand)

prob.solve(pulp.GUROBI_CMD(msg=0))

obj_val = pulp.value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")
