"""
tests/test_academic_engine.py
Comprehensive unit tests for the Academic Calculation Engine & Grading System.
"""
import unittest
import pandas as pd

from data_engine.academic_engine import (
    ACADEMIC_CALCULATED_COLUMNS,
    COL_CALCULATED_CGPA,
    COL_CALCULATED_GRADE,
    COL_RESULT_STATUS,
    calculate_cgpa_from_percentage,
    calculate_grade,
    cgpa_to_percentage,
    enrich_dataset_with_academic_metrics,
    enrich_records,
    evaluate_result_status,
    extract_student_percentage,
)


class TestCalculateGrade(unittest.TestCase):
    """Test letter grade and grade point evaluation across all CBSE brackets and presets."""

    def test_cbse_brackets(self):
        # A1: 91 - 100%
        self.assertEqual(calculate_grade(100.0), ("A1", 10.0))
        self.assertEqual(calculate_grade(95.0), ("A1", 10.0))
        self.assertEqual(calculate_grade(91.0), ("A1", 10.0))

        # A2: 81 - 90%
        self.assertEqual(calculate_grade(90.0), ("A2", 9.0))
        self.assertEqual(calculate_grade(85.5), ("A2", 9.0))
        self.assertEqual(calculate_grade(81.0), ("A2", 9.0))

        # B1: 71 - 80%
        self.assertEqual(calculate_grade(80.0), ("B1", 8.0))
        self.assertEqual(calculate_grade(75.0), ("B1", 8.0))
        self.assertEqual(calculate_grade(71.0), ("B1", 8.0))

        # B2: 61 - 70%
        self.assertEqual(calculate_grade(70.0), ("B2", 7.0))
        self.assertEqual(calculate_grade(65.0), ("B2", 7.0))
        self.assertEqual(calculate_grade(61.0), ("B2", 7.0))

        # C1: 51 - 60%
        self.assertEqual(calculate_grade(60.0), ("C1", 6.0))
        self.assertEqual(calculate_grade(55.0), ("C1", 6.0))
        self.assertEqual(calculate_grade(51.0), ("C1", 6.0))

        # C2: 41 - 50%
        self.assertEqual(calculate_grade(50.0), ("C2", 5.0))
        self.assertEqual(calculate_grade(45.0), ("C2", 5.0))
        self.assertEqual(calculate_grade(41.0), ("C2", 5.0))

        # D: 33 - 40%
        self.assertEqual(calculate_grade(40.0), ("D", 4.0))
        self.assertEqual(calculate_grade(36.5), ("D", 4.0))
        self.assertEqual(calculate_grade(33.0), ("D", 4.0))

        # E / F: < 33%
        self.assertEqual(calculate_grade(32.9), ("E", 0.0))
        self.assertEqual(calculate_grade(15.0), ("E", 0.0))
        self.assertEqual(calculate_grade(0.0), ("E", 0.0))

    def test_max_score_normalization(self):
        # 45 / 50 = 90% -> A2 (9.0)
        self.assertEqual(calculate_grade(45, max_score=50), ("A2", 9.0))
        # 200 / 200 = 100% -> A1 (10.0)
        self.assertEqual(calculate_grade(200, max_score=200), ("A1", 10.0))
        # 16 / 50 = 32% -> E (0.0)
        self.assertEqual(calculate_grade(16, max_score=50), ("E", 0.0))

    def test_string_inputs(self):
        self.assertEqual(calculate_grade("95%"), ("A1", 10.0))
        self.assertEqual(calculate_grade(" 84.5 "), ("A2", 9.0))
        self.assertEqual(calculate_grade("invalid"), ("N/A", 0.0))

    def test_standard_preset(self):
        self.assertEqual(calculate_grade(95.0, preset="STANDARD"), ("A", 4.0))
        self.assertEqual(calculate_grade(85.0, preset="STANDARD"), ("B", 3.0))
        self.assertEqual(calculate_grade(75.0, preset="STANDARD"), ("C", 2.0))
        self.assertEqual(calculate_grade(65.0, preset="STANDARD"), ("D", 1.0))
        self.assertEqual(calculate_grade(45.0, preset="STANDARD"), ("F", 0.0))


class TestCGPAConverter(unittest.TestCase):
    """Test CBSE 10-Point CGPA scale converter & percentage conversion."""

    def test_cbse_9_5_formula(self):
        # 95 / 9.5 = 10.0
        self.assertEqual(calculate_cgpa_from_percentage(95.0), 10.0)
        # 100 / 9.5 = 10.526 -> capped at 10.0
        self.assertEqual(calculate_cgpa_from_percentage(100.0), 10.0)
        # 76 / 9.5 = 8.00
        self.assertEqual(calculate_cgpa_from_percentage(76.0), 8.0)
        # 0 / 9.5 = 0.0
        self.assertEqual(calculate_cgpa_from_percentage(0.0), 0.0)

    def test_cgpa_from_string(self):
        self.assertEqual(calculate_cgpa_from_percentage("85.5%"), 9.0)
        self.assertEqual(calculate_cgpa_from_percentage(""), 0.0)

    def test_cgpa_grade_point_method(self):
        self.assertEqual(calculate_cgpa_from_percentage(95.0, method="grade_point"), 10.0)
        self.assertEqual(calculate_cgpa_from_percentage(85.0, method="grade_point"), 9.0)
        self.assertEqual(calculate_cgpa_from_percentage(30.0, method="grade_point"), 0.0)

    def test_cgpa_to_percentage(self):
        self.assertEqual(cgpa_to_percentage(10.0), 95.0)
        self.assertEqual(cgpa_to_percentage(8.0), 76.0)
        self.assertEqual(cgpa_to_percentage("9.0"), 85.5)


class TestResultStatus(unittest.TestCase):
    """Test pass/fail evaluation."""

    def test_pass_fail(self):
        self.assertEqual(evaluate_result_status(33.0), "PASSED")
        self.assertEqual(evaluate_result_status(85.0), "PASSED")
        self.assertEqual(evaluate_result_status(32.99), "FAILED")
        self.assertEqual(evaluate_result_status(0.0), "FAILED")
        self.assertEqual(evaluate_result_status("invalid"), "FAILED")


class TestRecordIntrospection(unittest.TestCase):
    """Test automatic student score / percentage extraction."""

    def test_explicit_percentage_column(self):
        row = {"Name": "Alice", "Percentage": "88.5"}
        pct = extract_student_percentage(row)
        self.assertEqual(pct, 88.5)

    def test_total_marks_column(self):
        row = {"Name": "Bob", "Total Marks": "450", "Max Marks": "500"}
        pct = extract_student_percentage(row)
        self.assertEqual(pct, 90.0)

    def test_subject_columns_aggregation(self):
        row = {"Name": "Charlie", "Roll No": "101", "Maths": "90", "Science": "80", "English": "70"}
        pct = extract_student_percentage(row)
        self.assertEqual(pct, 80.0)


class TestDatasetEnrichment(unittest.TestCase):
    """Test adding calculated columns directly into records and DataFrames."""

    def test_enrich_records(self):
        headers = ["Roll No", "Name", "Percentage"]
        records = [
            {"Roll No": "1", "Name": "Aarav", "Percentage": "95"},
            {"Roll No": "2", "Name": "Diya", "Percentage": "82"},
            {"Roll No": "3", "Name": "Rohan", "Percentage": "30"},
        ]

        new_headers, enriched = enrich_records(headers, records)

        self.assertIn(COL_CALCULATED_GRADE, new_headers)
        self.assertIn(COL_CALCULATED_CGPA, new_headers)
        self.assertIn(COL_RESULT_STATUS, new_headers)

        # Row 1 (95%)
        self.assertEqual(enriched[0][COL_CALCULATED_GRADE], "A1")
        self.assertEqual(enriched[0][COL_CALCULATED_CGPA], "10.00")
        self.assertEqual(enriched[0][COL_RESULT_STATUS], "PASSED")

        # Row 2 (82%)
        self.assertEqual(enriched[1][COL_CALCULATED_GRADE], "A2")
        self.assertEqual(enriched[1][COL_CALCULATED_CGPA], "8.63")
        self.assertEqual(enriched[1][COL_RESULT_STATUS], "PASSED")

        # Row 3 (30%)
        self.assertEqual(enriched[2][COL_CALCULATED_GRADE], "E")
        self.assertEqual(enriched[2][COL_CALCULATED_CGPA], "3.16")
        self.assertEqual(enriched[2][COL_RESULT_STATUS], "FAILED")

    def test_enrich_dataframe(self):
        df = pd.DataFrame([
            {"Name": "Student A", "Score": 92},
            {"Name": "Student B", "Score": 55},
        ])

        enriched_df = enrich_dataset_with_academic_metrics(df, score_column="Score")

        self.assertIn("Calculated_Grade", enriched_df.columns)
        self.assertIn("Calculated_CGPA", enriched_df.columns)
        self.assertIn("Result_Status", enriched_df.columns)

        self.assertEqual(enriched_df.iloc[0]["Calculated_Grade"], "A1")
        self.assertEqual(enriched_df.iloc[0]["Result_Status"], "PASSED")

        self.assertEqual(enriched_df.iloc[1]["Calculated_Grade"], "C1")
        self.assertEqual(enriched_df.iloc[1]["Result_Status"], "PASSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)

