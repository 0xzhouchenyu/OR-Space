import csv
import os

def load_courses(data_dir):
    """Load course data from table_1.csv"""
    filepath = os.path.join(data_dir, 'table_1.csv')
    courses = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            course = row['Course'].strip()
            categories = [c.strip() for c in row['Category'].split(';')]
            courses[course] = categories
    return courses

def load_parameters(data_dir):
    """Load general parameters from general_parameters.csv"""
    filepath = os.path.join(data_dir, 'general_parameters.csv')
    params = {}
    prerequisites = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name'].strip()
            value = row['Value'].strip()
            if name == 'min_courses_required':
                params['min_courses_required'] = int(value)
            elif name.startswith('prerequisite_'):
                # Extract the course name from the parameter name
                course_key = name[len('prerequisite_'):]
                # Convert underscore-separated name back to course name
                # We'll need to match this against actual course names
                prerequisites[course_key] = value
    return params, prerequisites

def match_prerequisite_course(prereq_key, course_list):
    """Match a prerequisite key (like 'computer_simulation') to actual course name"""
    key_lower = prereq_key.lower().replace('_', ' ')
    for course in course_list:
        if course.lower() == key_lower:
            return course
    return None