"""
tests/test_header_normalizer.py
Full-scale tests for data_engine/header_normalizer.py (Dynamic Header Aliasing Engine).
"""
import unittest

from data_engine.header_normalizer import (
    HEADER_ALIASES,
    auto_map_fields,
    find_matching_header,
    get_canonical_concept,
    normalize_header,
)


class TestNormalizeHeader(unittest.TestCase):
    def test_lowercase_and_strip(self):
        self.assertEqual(normalize_header("  Student Name  "), "student name")

    def test_replaces_underscores_and_hyphens(self):
        self.assertEqual(normalize_header("student_name"), "student name")
        self.assertEqual(normalize_header("roll-number"), "roll number")
        self.assertEqual(normalize_header("class/sec"), "class sec")

    def test_collapses_multiple_spaces(self):
        self.assertEqual(normalize_header("roll   no  "), "roll no")

    def test_empty_returns_empty(self):
        self.assertEqual(normalize_header(""), "")
        self.assertEqual(normalize_header(None), "")


class TestCanonicalConceptResolution(unittest.TestCase):
    def test_name_aliases(self):
        for alias in ["Name", "student name", "Student_Name", "FULL NAME", "candidate name", "Candidate_Name", "student"]:
            concept = get_canonical_concept(alias)
            self.assertEqual(concept, "Name", f"Alias '{alias}' failed to resolve to 'Name'")

    def test_roll_enrollment_aliases(self):
        for alias in ["roll no", "roll_no", "Roll Number", "Enrollment", "enrollment no", "reg no", "Reg_No", "id", "student id", "admission no"]:
            concept = get_canonical_concept(alias)
            self.assertEqual(concept, "Roll No", f"Alias '{alias}' failed to resolve to 'Roll No'")

    def test_class_aliases(self):
        for alias in ["Class", "grade", "STANDARD", "sec", "Section", "class_section", "class/sec"]:
            concept = get_canonical_concept(alias)
            self.assertEqual(concept, "Class", f"Alias '{alias}' failed to resolve to 'Class'")

    def test_unrecognized_returns_none(self):
        self.assertIsNone(get_canonical_concept("Physics Score"))
        self.assertIsNone(get_canonical_concept("Total Marks"))


class TestFindMatchingHeader(unittest.TestCase):
    def test_exact_match(self):
        headers = ["Student Name", "Physics", "Chemistry"]
        self.assertEqual(find_matching_header("Student Name", headers), "Student Name")

    def test_case_insensitive_match(self):
        headers = ["student name", "PHYSICS"]
        self.assertEqual(find_matching_header("Student Name", headers), "student name")

    def test_name_alias_candidate_name_to_student_name(self):
        headers = ["Candidate Name", "Roll_No", "Total"]
        # Field label is "Student Name", should match "Candidate Name"
        self.assertEqual(find_matching_header("Student Name", headers), "Candidate Name")

    def test_roll_alias_enrollment_to_roll_no(self):
        headers = ["Enrollment Number", "Candidate Name"]
        self.assertEqual(find_matching_header("Roll No", headers), "Enrollment Number")

    def test_class_alias_grade_to_class(self):
        headers = ["Grade", "Full Name", "ID"]
        self.assertEqual(find_matching_header("Class", headers), "Grade")

    def test_reg_no_to_student_id(self):
        headers = ["Reg No", "Full Name"]
        self.assertEqual(find_matching_header("ID", headers), "Reg No")

    def test_no_match_returns_none(self):
        headers = ["Math", "Physics", "Chemistry"]
        self.assertIsNone(find_matching_header("Student Name", headers))

    def test_empty_headers_returns_none(self):
        self.assertIsNone(find_matching_header("Name", []))


class TestAutoMapFields(unittest.TestCase):
    class DummyField:
        def __init__(self, label: str, mapped_column: str = ""):
            self.label = label
            self.mapped_column = mapped_column

    def test_auto_mapping_multiple_fields(self):
        fields = [
            self.DummyField("Student Name"),
            self.DummyField("Roll No"),
            self.DummyField("Class"),
            self.DummyField("Math"),
        ]
        available_headers = ["candidate_name", "enrollment_no", "section", "Math", "Science"]
        mapped = auto_map_fields(fields, available_headers)

        self.assertEqual(mapped["Student Name"], "candidate_name")
        self.assertEqual(mapped["Roll No"], "enrollment_no")
        self.assertEqual(mapped["Class"], "section")
        self.assertEqual(mapped["Math"], "Math")


class TestPdfValueExtractionWithAliasing(unittest.TestCase):
    def test_extract_field_value_uses_aliasing(self):
        from generation.pdf_generator import _extract_field_value

        row = {"Candidate Name": "Aarav Sharma", "Enrollment_No": "EN999", "Grade": "10-A"}

        # Field configured as "Student Name" with no mapped_column
        f1 = {"label": "Student Name", "mapped_column": ""}
        self.assertEqual(_extract_field_value(f1, row), "Aarav Sharma")

        # Field configured as "Roll No" with no mapped_column
        f2 = {"label": "Roll No", "mapped_column": ""}
        self.assertEqual(_extract_field_value(f2, row), "EN999")

        # Field configured as "Class" with no mapped_column
        f3 = {"label": "Class", "mapped_column": ""}
        self.assertEqual(_extract_field_value(f3, row), "10-A")


if __name__ == "__main__":
    unittest.main(verbosity=2)

