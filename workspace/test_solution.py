# === test_solution.py ===

from solution import Student, GradeBook

def test_student_add_grade():
    try:
        student = Student("Alice", "001")
        student.add_grade("Math", 95)
        assert student.get_grades() == {"Math": 95}
        print("PASS: test_student_add_grade")
    except AssertionError as e:
        print(f"FAIL: test_student_add_grade - {e}")
    except Exception as e:
        print(f"FAIL: test_student_add_grade - Unexpected error: {e}")

def test_student_add_invalid_grade():
    try:
        student = Student("Bob", "002")
        student.add_grade("Science", 105)  # Invalid grade
        assert False, "Expected ValueError"
    except ValueError as e:
        print("PASS: test_student_add_invalid_grade")
    except Exception as e:
        print(f"FAIL: test_student_add_invalid_grade - Unexpected error: {e}")

def test_gradebook_add_student():
    try:
        grade_book = GradeBook()
        student1 = Student("Charlie", "003")
        grade_book.add_student(student1)
        assert grade_book.students["003"].name == "Charlie"
        print("PASS: test_gradebook_add_student")
    except AssertionError as e:
        print(f"FAIL: test_gradebook_add_student - {e}")
    except Exception as e:
        print(f"FAIL: test_gradebook_add_student - Unexpected error: {e}")

def test_gradebook_add_existing_student():
    try:
        grade_book = GradeBook()
        student1 = Student("David", "004")
        grade_book.add_student(student1)
        grade_book.add_student(student1)  # Adding existing student
        assert False, "Expected ValueError"
    except ValueError as e:
        print("PASS: test_gradebook_add_existing_student")
    except Exception as e:
        print(f"FAIL: test_gradebook_add_existing_student - Unexpected error: {e}")

def test_gradebook_add_grade():
    try:
        grade_book = GradeBook()
        student1 = Student("Eve", "005")
        grade_book.add_student(student1)
        grade_book.add_grade("005", "History", 88)
        assert grade_book.students["005"].get_grades() == {"History": 88}
        print("PASS: test_gradebook_add_grade")
    except AssertionError as e:
        print(f"FAIL: test_gradebook_add_grade - {e}")
    except Exception as e:
        print(f"FAIL: test_gradebook_add_grade - Unexpected error: {e}")

def test_gradebook_add_grade_nonexistent_student():
    try:
        grade_book = GradeBook()
        grade_book.add_grade("006", "English", 92)  # Non-existent student
        assert False, "Expected KeyError"
    except KeyError as e:
        print("PASS: test_gradebook_add_grade_nonexistent_student")
    except Exception as e:
        print(f"FAIL: test_gradebook_add_grade_nonexistent_student - Unexpected error: {e}")

def main():
    tests = [
        test_student_add_grade,
        test_student_add_invalid_grade,
        test_gradebook_add_student,
        test_gradebook_add_existing_student,
        test_gradebook_add_grade,
        test_gradebook_add_grade_nonexistent_student
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"Test {test.__name__} failed with error: {e}")

    print(f"\nTests passed: {passed}/{total}")

if __name__ == "__main__":
    main()