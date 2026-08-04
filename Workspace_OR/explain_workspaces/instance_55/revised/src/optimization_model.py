import os
import csv
from gurobi_pulp_compat import LpProblem, LpMinimize, LpVariable, lpSum, GUROBI_CMD, LpBinary, value


def normalize_name(text):
    return text.strip().lower().replace('_', ' ')


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    courses = {}
    with open(os.path.join(data_dir, 'table_1.csv'), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            course = row['Course'].strip()
            categories = [c.strip() for c in row['Category'].split(';') if c.strip()]
            courses[course] = categories

    params = {}
    prerequisites = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name'].strip()
            val = row['Value'].strip()
            if name.startswith('prerequisite_'):
                course_key = normalize_name(name[len('prerequisite_'):])
                matched_course = None
                for c in courses:
                    if normalize_name(c) == course_key:
                        matched_course = c
                        break
                if matched_course is not None:
                    prerequisites.setdefault(matched_course, []).append(val)
            else:
                params[name] = val

    min_required = int(float(params['min_courses_required']))
    cs_category_name = params['cs_category_name']
    mandatory_foundation = params['mandatory_foundation_for_cs_counting']

    course_list = list(courses.keys())
    categories = sorted({cat for cat_list in courses.values() for cat in cat_list})

    prob = LpProblem('CourseSelectionDistinctAssignments', LpMinimize)

    x = {course: LpVariable(f"take_{course.replace(' ', '_')}", cat=LpBinary) for course in course_list}
    y = {}
    for course in course_list:
        for cat in courses[course]:
            y[(course, cat)] = LpVariable(f"assign_{course.replace(' ', '_')}_to_{cat.replace(' ', '_')}", cat=LpBinary)

    z = {cat: LpVariable(f"activate_{cat.replace(' ', '_')}", cat=LpBinary) for cat in categories}

    prob += lpSum(x[c] for c in course_list), 'MinimizeNumberOfCourses'

    for course in course_list:
        prob += lpSum(y[(course, cat)] for cat in courses[course]) <= x[course], f"AssignOnlyIfTaken_{course.replace(' ', '_')}"

    for cat in categories:
        eligible = [course for course in course_list if cat in courses[course]]
        prob += lpSum(y[(course, cat)] for course in eligible) >= min_required, f"MinDistinctCount_{cat.replace(' ', '_')}"
        prob += lpSum(y[(course, cat)] for course in eligible) >= z[cat], f"ActivateLB_{cat.replace(' ', '_')}"
        prob += lpSum(y[(course, cat)] for course in eligible) <= len(eligible) * z[cat], f"ActivateUB_{cat.replace(' ', '_')}"

    for course, prereqs in prerequisites.items():
        for prereq in prereqs:
            prob += x[course] <= x[prereq], f"Prereq_{course.replace(' ', '_')}_needs_{prereq.replace(' ', '_')}"

    prob += x[mandatory_foundation] >= z[cs_category_name], 'MandatoryFoundationForCSCoverage'

    prob.solve(GUROBI_CMD(msg=0))

    print(f"OBJECTIVE_VALUE: {float(value(prob.objective))}")


if __name__ == '__main__':
    main()
