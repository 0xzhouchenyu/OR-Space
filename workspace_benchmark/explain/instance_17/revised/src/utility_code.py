import csv
import os

def load_data():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    # Load table_1.csv
    parts = []
    with open(os.path.join(base_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            parts.append({
                'id': int(row['Key_Part']),
                'distance': float(row['Distance_from_Airport_km']),
                'p_heavy': float(row['Probability_of_Destruction_per_Heavy_Bomb']),
                'p_light': float(row['Probability_of_Destruction_per_Light_Bomb']),
            })
    
    # Load general_parameters.csv
    params = {}
    with open(os.path.join(base_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name']] = float(row['Value'])
    
    return parts, params

def fuel_per_heavy_bomb(distance, params):
    """Fuel for one trip carrying a heavy bomb to target and returning empty."""
    eff_heavy = params['fuel_efficiency_heavy_bomb']  # 2 km/liter
    eff_empty = params['fuel_efficiency_empty']  # 4 km/liter
    takeoff_landing = params['fuel_takeoff_landing']  # 100 liters
    return distance / eff_heavy + distance / eff_empty + takeoff_landing

def fuel_per_light_bomb(distance, params):
    """Fuel for one trip carrying a light bomb to target and returning empty."""
    eff_light = params['fuel_efficiency_light_bomb']  # 3 km/liter
    eff_empty = params['fuel_efficiency_empty']  # 4 km/liter
    takeoff_landing = params['fuel_takeoff_landing']  # 100 liters
    return distance / eff_light + distance / eff_empty + takeoff_landing

def prob_destroy_part(x_heavy, x_light, p_heavy, p_light):
    """Probability of destroying a part given x_heavy heavy bombs and x_light light bombs."""
    return 1.0 - (1.0 - p_heavy) ** x_heavy * (1.0 - p_light) ** x_light

def prob_at_least_k(probs, k):
    """Probability that at least k out of n independent events occur."""
    n = len(probs)
    # Use DP to compute P(at least k successes)
    # dp[j] = probability of exactly j successes among first i events
    dp = [0.0] * (n + 1)
    dp[0] = 1.0
    for i in range(n):
        new_dp = [0.0] * (n + 1)
        for j in range(i + 2):
            # Event i does not occur
            new_dp[j] += dp[j] * (1.0 - probs[i])
            # Event i occurs
            if j > 0:
                new_dp[j] += dp[j - 1] * probs[i]
        dp = new_dp
    return sum(dp[j] for j in range(k, n + 1))