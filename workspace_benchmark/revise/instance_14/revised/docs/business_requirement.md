Mary is now planning both lunch and dinner for a single day. She wants to choose a combination of protein and vegetable items that jointly serve these two meals while maximizing her total protein intake.

Each item listed in table_1.csv represents a food type that Mary can buy in units of 100 grams. For each item, the following attributes are defined:
- Protein_Content_per_100g: grams of protein per 100 grams of that item.
- Cost_per_100g: monetary cost per 100 grams of that item, in USD.
- Type: either "Protein" or "Vegetable".
- Calories_per_100g: calories per 100 grams of that item, in kilocalories.
- Sodium_mg_per_100g: milligrams of sodium per 100 grams of that item.

Mary prepares exactly two meals: lunch and dinner. For each meal:
- The meal has a prescribed portion weight of 300 grams. That means the total grams of food assigned to lunch must be exactly 300 grams, and the total grams of food assigned to dinner must be exactly 300 grams.
- The meal contains an integer number of 100 gram units of each item (0, 100, 200 grams, etc.).

Mary buys items once for the whole day and then allocates the purchased items between lunch and dinner:
- For each item i, let purchase_units[i] be the number of 100 gram units Mary purchases in total for that day. These units can be split between lunch and dinner.
- Let lunch_units[i] be the number of 100 gram units of item i that are used in lunch.
- Let dinner_units[i] be the number of 100 gram units of item i that are used in dinner.

Linking of purchase and meal assignment is defined as:
- For every item i, purchase_units[i] >= lunch_units[i] + dinner_units[i]. Any purchased amount not assigned to lunch or dinner is unused.
- All variables purchase_units[i], lunch_units[i], and dinner_units[i] are nonnegative integers measured in units of 100 grams.

Mary must respect the following daily constraints:
1. Total daily budget:
- Let max_budget be the maximum amount of money Mary can spend on all purchased items. This parameter is given in general_parameters.csv as max_budget and measured in USD.
- The total cost of all purchases equals the sum over all items i of (Cost_per_100g(i) * purchase_units[i]). This total must be less than or equal to max_budget.

2. Total daily weight limit:
- Let total_weight_limit be the maximum total weight (in grams) Mary is allowed to purchase for the day. This parameter is given in general_parameters.csv.
- The total purchased grams equals 100 * sum_{i} purchase_units[i] and must be less than or equal to total_weight_limit.

3. Minimum number of vegetable types per meal:
- Let min_vegetable_types be the minimum number of distinct vegetable types that must appear in each meal.
- A vegetable type appears in lunch if and only if lunch_units[i] > 0 for an item i of Type="Vegetable". Similarly, a vegetable type appears in dinner if and only if dinner_units[i] > 0.
- For each meal (lunch and dinner separately), the number of distinct vegetable items with strictly positive assigned units must be at least min_vegetable_types.

4. Per-meal weight balance:
- For lunch: the total weight equals exactly 300 grams. Thus, sum_{i} (100 * lunch_units[i]) = 300.
- For dinner: the total weight equals exactly 300 grams. Thus, sum_{i} (100 * dinner_units[i]) = 300.

5. Daily calorie intake bounds:
- Each item i has a calorie density given by Calories_per_100g(i) in table_1.csv (unit: kcal per 100 grams).
- Let min_daily_calories (kcal) be the minimum total calorie intake Mary wants from the combination of lunch and dinner.
- Let max_daily_calories (kcal) be the maximum total calorie intake Mary must not exceed.
- The total daily calories are computed only from assigned units (lunch and dinner), not from unused purchased items:
  total_calories = sum_{i} Calories_per_100g(i) * (lunch_units[i] + dinner_units[i]).
  This total_calories must satisfy:
  min_daily_calories <= total_calories <= max_daily_calories.

6. Daily sodium intake bound:
- Each item i has a sodium density given by Sodium_mg_per_100g(i) in table_1.csv (unit: milligrams per 100 grams).
- Let max_daily_sodium be the maximum total sodium intake Mary must not exceed in the day.
- The total daily sodium, computed only from assigned units, is:
  total_sodium = sum_{i} Sodium_mg_per_100g(i) * (lunch_units[i] + dinner_units[i]).
  This total_sodium must be less than or equal to max_daily_sodium.

7. Purchase selection linkage:
- For each item i, a binary variable select_item[i] indicates whether Mary purchases item i at all.
- If select_item[i] = 0, then purchase_units[i] = 0 and lunch_units[i] = 0 and dinner_units[i] = 0 (Mary does not buy or use that item).
- If select_item[i] = 1, then purchase_units[i] may be positive.
- The linkage is enforced by big-M constraints:
  purchase_units[i] <= max_units * select_item[i],
  lunch_units[i] <= max_meal_units * select_item[i],
  dinner_units[i] <= max_meal_units * select_item[i].

Definitions of capacity-related parameters:
- max_units is defined as total_weight_limit / 100, rounded down to an integer. It represents an upper bound on daily purchase_units[i] per item, consistent with the original problem.
- Each meal uses exactly 3 units in total (because 300 grams per meal / 100 grams per unit = 3). Let max_meal_units be defined as 3. This quantity is used as a big-M constant for lunch_units[i] and dinner_units[i] per item.

Additional meal-level vegetable coverage constraints:
- For each vegetable item i, a binary variable lunch_veg_selected[i] indicates whether lunch_units[i] > 0.
- For each vegetable item i, a binary variable dinner_veg_selected[i] indicates whether dinner_units[i] > 0.
- These are linked via:
  lunch_units[i] >= lunch_veg_selected[i],
  dinner_units[i] >= dinner_veg_selected[i],
  lunch_units[i] <= max_meal_units * lunch_veg_selected[i],
  dinner_units[i] <= max_meal_units * dinner_veg_selected[i].
- For lunch: sum over vegetable items i of lunch_veg_selected[i] >= min_vegetable_types.
- For dinner: sum over vegetable items i of dinner_veg_selected[i] >= min_vegetable_types.

Objective function:
- The objective is to maximize the total protein consumed in lunch and dinner combined.
- Total consumed protein is defined as:
  total_protein = sum_{i} Protein_Content_per_100g(i) * (lunch_units[i] + dinner_units[i]).
- Only assigned units contribute to protein; unused purchased units do not contribute.

All decision variables and constraints above must be modeled as a mixed-integer linear program:
- purchase_units[i], lunch_units[i], dinner_units[i] are nonnegative integers.
- select_item[i], lunch_veg_selected[i], and dinner_veg_selected[i] are binary variables.

All numerical parameters are given either in table_1.csv or in general_parameters.csv and must be used exactly as defined without additional assumptions.