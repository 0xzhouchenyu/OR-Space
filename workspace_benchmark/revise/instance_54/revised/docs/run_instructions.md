To run the optimization for the revised problem:

1. Ensure you have Python 3 and the PuLP package installed.
   - You can install PuLP via: pip install pulp

2. From the project root directory (the folder containing the 'src' and 'data' directories), execute:
   - cd src
   - python current_heuristic.py

3. The script will solve the revised linear programming problem with CBC and print the optimal objective value in the format:
   OBJECTIVE_VALUE: <number>

All required parameters are defined in the CSV files inside the 'data' directory.