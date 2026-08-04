import os
import sys
from gurobi_pulp_compat import *
from utils import load_courses, load_parameters, match_prerequisite_course

# Data directory
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Load data
courses = load_courses(data_dir)
params, prereq_raw = load_parameters(data_dir)

min_required = params['min_courses_required']  # 2

# Build prerequisite mapping: course -> list of prerequisites
course_list = list(courses.keys())
prerequisites = {}

for prereq_key, prereq_value in prereq_raw.items():
    course_name = match_prerequisite_course(prereq_key, course_list)
    if course_name:
        if course_name not in prerequisites:
            prerequisites[course_name] = []
        prerequisites[course_name].append(prereq_value.strip())

print("Courses and categories:", courses)
print("Prerequisites:", prerequisites)
print("Min courses per category:", min_required)

# Get all categories
all_categories = set()
for cats in courses.values():
    for c in cats:
        all_categories.add(c)
print("Categories:", all_categories)

# Create optimization model
prob = LpProblem("CourseSelection", LpMinimize)

# Decision variables: binary, whether to take each course
x = {course: LpVariable(f"x_{course.replace(' ', '_')}", cat='Binary') for course in course_list}

# Objective: minimize total number of courses taken
prob += lpSum(x[course] for course in course_list), "TotalCourses"

# Constraint: at least min_required courses in each category
for category in all_categories:
    courses_in_cat = [course for course, cats in courses.items() if category in cats]
    prob += lpSum(x[course] for course in courses_in_cat) >= min_required, f"Min_{category.replace(' ', '_')}"

# Prerequisite constraints: if you take a course, you must take its prerequisites
for course, prereqs in prerequisites.items():
    for prereq in prereqs:
        # x[course] <= x[prereq]  (if you take course, you must take prereq)
        prob += x[course] <= x[prereq], f"Prereq_{course.replace(' ', '_')}_needs_{prereq.replace(' ', '_')}"

# Solve
prob.solve(GUROBI_CMD(msg=1))

print(f"\nStatus: {LpStatus[prob.status]}")
print("\nSelected courses:")
for course in course_list:
    if value(x[course]) > 0.5:
        print(f"  {course}: {courses[course]}")

obj_val = value(prob.objective)
print(f"\nOBJECTIVE_VALUE: {obj_val}")