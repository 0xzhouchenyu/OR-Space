import csv


def load_processing_times(filepath):
    processing_times = []
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            times = [int(val) for val in row[1:]]
            processing_times.append(times)
    return processing_times
