from typing import Dict, List, Optional

class Student:
    """
    A class to represent a student with name, ID, and grades.
    """

    def __init__(self, name: str, student_id: str):
        self.name = name
        self.student_id = student_id
        self.grades: Dict[str, float] = {}

    def add_grade(self, subject: str, grade: float) -> None:
        """
        Add or update a grade for a specific subject.

        :param subject: The subject for which the grade is being added.
        :param grade: The grade to be recorded.
        :raises ValueError: If the grade is not between 0 and 100.
        """
        if not (0 <= grade <= 100):
            raise ValueError("Grade must be between 0 and 100.")
        self.grades[subject] = grade

    def get_grades(self) -> Dict[str, float]:
        """
        Get the grades of the student.

        :return: A dictionary of subjects and their corresponding grades.
        """
        return self.grades


class GradeBook:
    """
    A class to manage a collection of students and their grades.
    """

    def __init__(self):
        self.students: Dict[str, Student] = {}

    def add_student(self, student: Student) -> None:
        """
        Add a student to the grade book.

        :param student: The student object to be added.
        """
        if student.student_id in self.students:
            raise ValueError(f"Student with ID {student.student_id} already exists.")
        self.students[student.student_id] = student

    def add_grade(self, student_id: str, subject: str, grade: float) -> None:
        """
        Add a grade for a specific student and subject.

        :param student_id: The ID of the student.
        :param subject: The subject for which the grade is being added.
        :param grade: The grade to be recorded.
        :raises KeyError: If the student ID does not exist.
        """
        if student_id not in self.students:
            raise KeyError(f"Student with ID {student_id} does not exist.")
        self.students[student_id].add_grade(subject, grade)

    def get_student_grades(self, student_id: str) -> Dict[str, float]:
        """
        Get the grades of a specific student.

        :param student_id: The ID of the student.
        :return: A dictionary of subjects and their corresponding grades.
        :raises KeyError: If the student ID does not exist.
        """
        if student_id not in self.students:
            raise KeyError(f"Student with ID {student_id} does not exist.")
        return self.students[student_id].get_grades()

    def calculate_average_grade(self) -> Optional[float]:
        """
        Calculate the average grade of all students.

        :return: The average grade or None if no grades are available.
        """
        total_grades = 0
        count = 0
        for student in self.students.values():
            for grade in student.grades.values():
                total_grades += grade
                count += 1
        return total_grades / count if count > 0 else None

    def find_highest_grade_student(self) -> Optional[str]:
        """
        Find the student with the highest average grade.

        :return: The name of the student with the highest average grade or None.
        """
        highest_average = -1
        highest_student_name = None
        for student in self.students.values():
            avg_grade = sum(student.grades.values()) / len(student.grades) if student.grades else 0
            if avg_grade > highest_average:
                highest_average = avg_grade
                highest_student_name = student.name
        return highest_student_name

    def find_lowest_grade_student(self) -> Optional[str]:
        """
        Find the student with the lowest average grade.

        :return: The name of the student with the lowest average grade or None.
        """
        lowest_average = float('inf')
        lowest_student_name = None
        for student in self.students.values():
            avg_grade = sum(student.grades.values()) / len(student.grades) if student.grades else 0
            if avg_grade < lowest_average:
                lowest_average = avg_grade
                lowest_student_name = student.name
        return lowest_student_name


def main():
    """
    Main function to test the GradeBook system.
    """
    grade_book = GradeBook()

    # Create students
    student1 = Student("Alice", "001")
    student2 = Student("Bob", "002")

    # Add students to the grade book
    grade_book.add_student(student1)
    grade_book.add_student(student2)

    # Add grades for each student
    grade_book.add_grade("001", "Math", 95)
    grade_book.add_grade("001", "Science", 88)
    grade_book.add_grade("002", "Math", 76)
    grade_book.add_grade("002", "Science", 92)

    # Query individual student grades
    print(f"Alice's grades: {grade_book.get_student_grades('001')}")
    print(f"Bob's grades: {grade_book.get_student_grades('002')}")

    # Calculate average grade
    print(f"Class average grade: {grade_book.calculate_average_grade()}")

    # Find highest and lowest grade students
    print(f"Highest grade student: {grade_book.find_highest_grade_student()}")
    print(f"Lowest grade student: {grade_book.find_lowest_grade_student()}")


if __name__ == "__main__":
    main()