"""
tests/test_preflight_sanitizer.py
Unit tests for data_engine/preflight_sanitizer.py and ui/dialogs/audit_dialog.py.
"""
import math
import unittest

from PyQt6.QtWidgets import QApplication

from data_engine.preflight_sanitizer import (
    AuditIssue,
    AuditReport,
    auto_sanitize_dataset,
    audit_dataset,
    clean_row_whitespace,
    is_empty_value,
)
from ui.dialogs.audit_dialog import AuditPreCheckDialog

# Ensure QApplication is initialized for UI tests
_app = QApplication.instance() or QApplication([])


class TestIsEmptyValue(unittest.TestCase):
    def test_empty_variants(self):
        self.assertTrue(is_empty_value(None))
        self.assertTrue(is_empty_value(""))
        self.assertTrue(is_empty_value("   "))
        self.assertTrue(is_empty_value("nan"))
        self.assertTrue(is_empty_value("NAN"))
        self.assertTrue(is_empty_value("none"))
        self.assertTrue(is_empty_value("null"))
        self.assertTrue(is_empty_value("<NA>"))
        self.assertTrue(is_empty_value("N/A"))
        self.assertTrue(is_empty_value(float("nan")))
        self.assertTrue(is_empty_value(float("inf")))

    def test_non_empty_values(self):
        self.assertFalse(is_empty_value("Aarav"))
        self.assertFalse(is_empty_value("0"))
        self.assertFalse(is_empty_value(0))
        self.assertFalse(is_empty_value(100))
        self.assertFalse(is_empty_value(95.5))
        self.assertFalse(is_empty_value("Passed"))


class TestCleanRowWhitespace(unittest.TestCase):
    def test_strips_leading_trailing_whitespace(self):
        raw = {
            "Roll No": "  101  ",
            "Name": "  John Doe  ",
            "Score": 95.0,
            "Remarks": None,
        }
        cleaned = clean_row_whitespace(raw)
        self.assertEqual(cleaned["Roll No"], "101")
        self.assertEqual(cleaned["Name"], "John Doe")
        self.assertEqual(cleaned["Score"], "95")
        self.assertEqual(cleaned["Remarks"], "")

    def test_handles_floats_and_nans(self):
        raw = {
            "Math": 88.5,
            "Physics": float("nan"),
            "Chemistry": 90.0,
        }
        cleaned = clean_row_whitespace(raw)
        self.assertEqual(cleaned["Math"], "88.5")
        self.assertEqual(cleaned["Physics"], "")
        self.assertEqual(cleaned["Chemistry"], "90")


class TestAuditDataset(unittest.TestCase):
    def test_clean_dataset_has_no_flaws(self):
        rows = [
            {"Roll No": "101", "Name": "Alice", "Math": "90"},
            {"Roll No": "102", "Name": "Bob", "Math": "85"},
        ]
        mapped_cols = ["Roll No", "Name", "Math"]
        cleaned_rows, report = audit_dataset(rows, mapped_cols, unique_col="Roll No")

        self.assertFalse(report.has_flaws)
        self.assertEqual(report.total_rows, 2)
        self.assertEqual(len(report.issues), 0)
        self.assertEqual(len(cleaned_rows), 2)
        self.assertEqual(cleaned_rows[0]["Roll No"], "101")

    def test_detects_empty_mapped_cells(self):
        rows = [
            {"Roll No": "101", "Name": "Alice", "Math": "90"},
            {"Roll No": "102", "Name": "   ", "Math": "85"},
            {"Roll No": "103", "Name": "Charlie", "Math": "nan"},
        ]
        mapped_cols = ["Roll No", "Name", "Math"]
        _, report = audit_dataset(rows, mapped_cols, unique_col="Roll No")

        self.assertTrue(report.has_flaws)
        self.assertEqual(report.empty_count, 2)
        self.assertEqual(report.duplicate_count, 0)
        self.assertEqual(report.affected_rows_count, 2)

        # Check issue details
        issues = report.issues
        self.assertEqual(issues[0].row_num, 2)
        self.assertEqual(issues[0].column_name, "Name")
        self.assertEqual(issues[0].issue_type, "Empty Cell")

        self.assertEqual(issues[1].row_num, 3)
        self.assertEqual(issues[1].column_name, "Math")
        self.assertEqual(issues[1].issue_type, "Empty Cell")

    def test_detects_duplicate_unique_identifiers(self):
        rows = [
            {"Roll No": "101", "Name": "Alice", "Math": "90"},
            {"Roll No": "102", "Name": "Bob", "Math": "85"},
            {"Roll No": "101", "Name": "Alice Duplicate", "Math": "92"},
            {"Roll No": "101", "Name": "Alice Triplicate", "Math": "88"},
        ]
        mapped_cols = ["Roll No", "Name", "Math"]
        _, report = audit_dataset(rows, mapped_cols, unique_col="Roll No")

        self.assertTrue(report.has_flaws)
        self.assertEqual(report.duplicate_count, 2)
        self.assertEqual(report.empty_count, 0)

        dup_issues = [i for i in report.issues if i.issue_type == "Duplicate Identifier"]
        self.assertEqual(len(dup_issues), 2)
        self.assertEqual(dup_issues[0].row_num, 3)
        self.assertIn("first seen at row 1", dup_issues[0].description)
        self.assertEqual(dup_issues[1].row_num, 4)

    def test_case_insensitive_column_matching(self):
        rows = [
            {"roll no": "101", "student name": "Alice"},
            {"roll no": "102", "student name": ""},
        ]
        mapped_cols = ["Roll No", "Student Name"]
        _, report = audit_dataset(rows, mapped_cols, unique_col="Roll No")

        self.assertTrue(report.has_flaws)
        self.assertEqual(report.empty_count, 1)
        self.assertEqual(report.issues[0].row_num, 2)


class TestAutoSanitizeDataset(unittest.TestCase):
    def test_auto_sanitizes_empty_cells_and_duplicates(self):
        rows = [
            {"Roll No": "101", "Name": "Alice", "Math": "90"},
            {"Roll No": "102", "Name": "   ", "Math": "85"},
            {"Roll No": "101", "Name": "Bob", "Math": ""},
            {"Roll No": "101", "Name": "Charlie", "Math": "95"},
        ]
        mapped_cols = ["Roll No", "Name", "Math"]
        sanitized = auto_sanitize_dataset(
            rows,
            mapped_cols,
            unique_col="Roll No",
            default_empty_fill="N/A",
        )

        self.assertEqual(len(sanitized), 4)

        # Row 1: untouched
        self.assertEqual(sanitized[0]["Roll No"], "101")
        self.assertEqual(sanitized[0]["Name"], "Alice")
        self.assertEqual(sanitized[0]["Math"], "90")

        # Row 2: empty name filled with N/A
        self.assertEqual(sanitized[1]["Roll No"], "102")
        self.assertEqual(sanitized[1]["Name"], "N/A")
        self.assertEqual(sanitized[1]["Math"], "85")

        # Row 3: duplicate Roll No resolved to 101_DUP1, Math filled with N/A
        self.assertEqual(sanitized[2]["Roll No"], "101_DUP1")
        self.assertEqual(sanitized[2]["Name"], "Bob")
        self.assertEqual(sanitized[2]["Math"], "N/A")

        # Row 4: duplicate Roll No resolved to 101_DUP2
        self.assertEqual(sanitized[3]["Roll No"], "101_DUP2")
        self.assertEqual(sanitized[3]["Name"], "Charlie")
        self.assertEqual(sanitized[3]["Math"], "95")


class TestAuditDialog(unittest.TestCase):
    def test_dialog_initialization(self):
        report = AuditReport(
            total_rows=3,
            issues=[
                AuditIssue(row_num=2, column_name="Name", issue_type="Empty Cell", description="Empty name"),
                AuditIssue(row_num=3, column_name="Roll No", issue_type="Duplicate Identifier", description="Duplicate ID"),
            ]
        )
        dialog = AuditPreCheckDialog(report)
        self.assertEqual(dialog._table.rowCount(), 2)
        self.assertEqual(dialog._table.item(0, 0).text(), "Row 2")
        self.assertEqual(dialog._table.item(0, 1).text(), "Name")
        self.assertEqual(dialog._table.item(0, 2).text(), "Empty Cell")
        self.assertEqual(dialog._table.item(1, 0).text(), "Row 3")
        self.assertEqual(dialog._table.item(1, 1).text(), "Roll No")
        self.assertEqual(dialog._table.item(1, 2).text(), "Duplicate Identifier")


if __name__ == "__main__":
    unittest.main(verbosity=2)

