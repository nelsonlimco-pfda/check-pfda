import csv


def write_student_data_to_csv(filename:str, classroom_csv:str,
                              student_txt_file:str) -> None:
    """Writes the dictionary of your team's student data to a csv file.

    :param filename: The name of the
    :type filename: str
    :param students: A list of student identifiers.
    :type students: list
    """
    students = remove_nonmatching_ids(classroom_csv, get_students(student_txt_file))
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, students[0].keys())
        writer.writeheader()
        writer.writerows(students)

    
def remove_nonmatching_ids(csv_filename:str, students:list) -> list:
    """Compares student roster identifiers with a given list of
    known correct roster identifiers.

    :param csv_filename: The file name of the csv file containing all
    students.
    :type csv_filename: str
    :param students: A list of student identifiers (NetID's) of your team's
    students.
    :type students: list
    :return: A sorted list of dictionaries containing student data from
    your team. Each dictionary contains the student's Net ID, their assignment
    grade, and a URL to their repository.
    :rtype: list
    """
    culled_assignment = []
    with open(csv_filename) as f:
        assignment = csv.DictReader(f)
        for student in assignment:
            if student["roster_identifier"] in students:
                student_info = {}
                student_info["net_id"] = student["roster_identifier"]
                student_info["grade"] = student["points_awarded"]
                student_info["repo_url"] = student["student_repository_url"]
                culled_assignment.append(student_info)
    return sorted(culled_assignment, key=lambda d: d['net_id'])


def get_students(filename:str) -> list:
    """Creates a list of student identifiers from a given txt file.
    Assumes that each identifier is delimited by a newline.

    :param filename: The filename of the txt file containing the student
    identifiers.
    :type filename: str
    :return: A list of student identifiers.
    :rtype: list
    """
    return open(filename).read().splitlines()
