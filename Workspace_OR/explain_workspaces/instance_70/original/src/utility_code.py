import csv
import os


def load_distance_matrix(filepath):
    """Load distance matrix from CSV file.
    
    Returns:
        cities: list of city labels
        dist: 2D list of distances (dist[i][j] = distance from city i to city j)
    """
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        # header: ['City', '1', '2', '3', '4', ...]
        city_labels = header[1:]
        
        dist = []
        cities = []
        for row in reader:
            cities.append(row[0].strip())
            dist.append([float(x) for x in row[1:]])
    
    return cities, dist