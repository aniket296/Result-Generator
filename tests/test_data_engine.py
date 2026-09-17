"""
tests/test_data_engine.py
Full-scale tests for data_engine: excel_loader, exceptions.
Covers normal flow, edge cases, and failure modes.
"""
import json
import os
import tempfile
import shutil
import unittest

import openpyxl


class TestExceptions(unittest.TestCase):
    """Verify all custom exception classes are properly defined and raisable."""

    def test_file_locked_error_is_exception(self):
        from data_engine.exceptions import FileLockedError
        with self.assertRaises(FileLockedError):
            raise FileLockedError("locked")

    def test_empty_cell_error_stores_metadata(self):
        from data_engine.exceptions import EmptyCellError
        try:
            raise EmptyCellError(3, "Physics")
        except EmptyCellError as e:
            self.assertEqual(e.row_num, 3)
            self.assertEqual(e.column_name, "Physics")
            self.assertIn("3", str(e))
            self.assertIn("Physics", str(e))

    def test_empty_cell_error_custom_message(self):
        from data_engine.exceptions import EmptyCellError
        exc = EmptyCellError(1, "Name", "Custom message")
        self.assertEqual(str(exc), "Custom message")

    def test_duplicate_unique_value_error(self):
        from data_engine.exceptions import DuplicateUniqueValueError
        try:
            raise DuplicateUniqueValueError("EnrollNo", ["EN001", "EN003"])
        except DuplicateUniqueValueError as e:
            self.assertEqual(e.column_name, "EnrollNo")
            self.assertIn("EN001", e.duplicate_values)
            self.assertIn("EN003", str(e))

    def test_dataset_mismatch_error_exists(self):
        from data_engine.exceptions import DatasetMismatchError
        exc = DatasetMismatchError("mismatch")
        self.assertIsInstance(exc, Exception)


class TestCheckFileLocked(unittest.TestCase):
    """Test the _check_file_locked helper."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_non_existent_file_passes(self):
        from data_engine.excel_loader import _check_file_locked
        # Should not raise
        _check_file_locked(os.path.join(self.tmp, "ghost.xlsx"))

    def test_normal_file_passes(self):
        from data_engine.excel_loader import _check_file_locked
        p = os.path.join(self.tmp, "test.xlsx")
        with open(p, "w") as f:
            f.write("dummy")
        _check_file_locked(p)  # Should not raise

    def test_shadow_lock_raises(self):
        from data_engine.excel_loader import _check_file_locked
        from data_engine.exceptions import FileLockedError
        p = os.path.join(self.tmp, "test.xlsx")
        shadow = os.path.join(self.tmp, "~$test.xlsx")
        open(p, "w").close()
        open(shadow, "w").close()
        with self.assertRaises(FileLockedError):
            _check_file_locked(p)


class TestLoadExcel(unittest.TestCase):
    """Test load_excel across formats and edge cases."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_xlsx(self, rows, headers, filename="test.xlsx"):
        path = os.path.join(self.tmp, filename)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(headers)
        for row in rows:
            ws.append(row)
        wb.save(path)
        return path

    def test_load_simple_xlsx(self):
        from data_engine.excel_loader import load_excel
        p = self._make_xlsx([["EN001", "Alice", "90"], ["EN002", "Bob", "85"]],
                            ["EnrollNo", "Name", "Score"])
        headers, rows = load_excel(p)
        self.assertEqual(headers, ["EnrollNo", "Name", "Score"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["Name"], "Alice")
        self.assertEqual(rows[1]["Score"], "85")

    def test_all_values_are_strings(self):
        from data_engine.excel_loader import load_excel
        p = self._make_xlsx([[1001, 3.14, True]], ["IntCol", "FloatCol", "BoolCol"])
        _, rows = load_excel(p)
        self.assertIsInstance(rows[0]["IntCol"], str)
        self.assertIsInstance(rows[0]["FloatCol"], str)

    def test_empty_cell_becomes_empty_string(self):
        from data_engine.excel_loader import load_excel
        p = self._make_xlsx([["EN001", None, "90"]], ["EnrollNo", "Name", "Score"])
        _, rows = load_excel(p)
        self.assertEqual(rows[0]["Name"], "")

    def test_whitespace_only_cell_stripped_to_empty(self):
        from data_engine.excel_loader import load_excel
        p = self._make_xlsx([["EN001", "  ", "90"]], ["EnrollNo", "Name", "Score"])
        _, rows = load_excel(p)
        self.assertEqual(rows[0]["Name"], "")

    def test_header_whitespace_stripped(self):
        from data_engine.excel_loader import load_excel
        p = self._make_xlsx([["v"]], ["  Name  "])
        headers, _ = load_excel(p)
        self.assertEqual(headers[0], "Name")

    def test_empty_file_returns_empty_rows(self):
        from data_engine.excel_loader import load_excel
        p = self._make_xlsx([], ["A", "B"])
        headers, rows = load_excel(p)
        self.assertEqual(headers, ["A", "B"])
        self.assertEqual(rows, [])

    def test_single_row_single_column(self):
        from data_engine.excel_loader import load_excel
        p = self._make_xlsx([["Hello World"]], ["Note"])
        headers, rows = load_excel(p)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Note"], "Hello World")

    def test_unicode_content(self):
        from data_engine.excel_loader import load_excel
        p = self._make_xlsx([["Aarav", "सिंह", "95"]], ["First", "Last", "Score"])
        _, rows = load_excel(p)
        self.assertEqual(rows[0]["Last"], "सिंह")

    def test_many_rows(self):
        from data_engine.excel_loader import load_excel
        data = [[f"EN{i:04d}", f"Student_{i}", str(i % 100)] for i in range(500)]
        p = self._make_xlsx(data, ["ID", "Name", "Score"])
        _, rows = load_excel(p)
        self.assertEqual(len(rows), 500)
        self.assertEqual(rows[499]["ID"], "EN0499")

    def test_invalid_file_raises_ioerror(self):
        from data_engine.excel_loader import load_excel
        p = os.path.join(self.tmp, "corrupt.xlsx")
        with open(p, "wb") as f:
            f.write(b"NOT AN EXCEL FILE")
        with self.assertRaises(IOError):
            load_excel(p)


class TestValidateRow(unittest.TestCase):
    def test_valid_row_passes(self):
        from data_engine.excel_loader import validate_row
        validate_row({"ID": "EN001", "Name": "Alice", "Score": "90"}, 1)

    def test_empty_string_raises(self):
        from data_engine.excel_loader import validate_row
        from data_engine.exceptions import EmptyCellError
        with self.assertRaises(EmptyCellError) as ctx:
            validate_row({"ID": "EN001", "Name": "", "Score": "90"}, 2)
        self.assertEqual(ctx.exception.row_num, 2)
        self.assertEqual(ctx.exception.column_name, "Name")

    def test_whitespace_raises(self):
        from data_engine.excel_loader import validate_row
        from data_engine.exceptions import EmptyCellError
        with self.assertRaises(EmptyCellError):
            validate_row({"Score": "   "}, 5)

    def test_none_value_raises(self):
        from data_engine.excel_loader import validate_row
        from data_engine.exceptions import EmptyCellError
        with self.assertRaises(EmptyCellError):
            validate_row({"Score": None}, 1)


class TestValidateAllRows(unittest.TestCase):
    def test_all_clean_returns_empty_list(self):
        from data_engine.excel_loader import validate_all_rows
        rows = [{"ID": "1", "N": "A"}, {"ID": "2", "N": "B"}]
        errors = validate_all_rows(rows)
        self.assertEqual(errors, [])

    def test_detects_all_empty_cells(self):
        from data_engine.excel_loader import validate_all_rows
        rows = [
            {"ID": "1", "Name": "Alice", "Score": ""},
            {"ID": "",  "Name": "Bob",   "Score": "90"},
            {"ID": "3", "Name": "",      "Score": ""},
        ]
        errors = validate_all_rows(rows)
        # row1: Score empty(1), row2: ID empty(1), row3: Name+Score empty(2) = 4 total
        # Recount: row1: Score empty (1), row2: ID empty (1), row3: Name+Score (2) = 4
        self.assertEqual(len(errors), 4)

    def test_row_numbers_1_indexed(self):
        from data_engine.excel_loader import validate_all_rows
        rows = [{"A": ""}, {"A": "val"}, {"A": ""}]
        errors = validate_all_rows(rows)
        row_nums = [e[0] for e in errors]
        self.assertIn(1, row_nums)
        self.assertNotIn(2, row_nums)
        self.assertIn(3, row_nums)

    def test_empty_dataset_returns_empty(self):
        from data_engine.excel_loader import validate_all_rows
        self.assertEqual(validate_all_rows([]), [])


class TestValidateUniqueColumn(unittest.TestCase):
    def test_all_unique_passes(self):
        from data_engine.excel_loader import validate_unique_column
        rows = [{"ID": "A"}, {"ID": "B"}, {"ID": "C"}]
        validate_unique_column(rows, "ID")  # no raise

    def test_duplicates_raise(self):
        from data_engine.excel_loader import validate_unique_column
        from data_engine.exceptions import DuplicateUniqueValueError
        rows = [{"ID": "A"}, {"ID": "B"}, {"ID": "A"}, {"ID": "C"}, {"ID": "B"}]
        with self.assertRaises(DuplicateUniqueValueError) as ctx:
            validate_unique_column(rows, "ID")
        self.assertIn("A", ctx.exception.duplicate_values)
        self.assertIn("B", ctx.exception.duplicate_values)

    def test_empty_values_are_skipped(self):
        from data_engine.excel_loader import validate_unique_column
        rows = [{"ID": ""}, {"ID": ""}, {"ID": "A"}]
        validate_unique_column(rows, "ID")  # blanks skip, no raise

    def test_case_sensitive(self):
        from data_engine.excel_loader import validate_unique_column
        rows = [{"ID": "abc"}, {"ID": "ABC"}, {"ID": "Abc"}]
        validate_unique_column(rows, "ID")  # all distinct case-sensitively

    def test_single_row_passes(self):
        from data_engine.excel_loader import validate_unique_column
        validate_unique_column([{"ID": "X"}], "ID")

    def test_missing_column_skips_gracefully(self):
        from data_engine.excel_loader import validate_unique_column
        rows = [{"Other": "A"}, {"Other": "A"}]
        validate_unique_column(rows, "ID")  # missing col → all empty → skip


class TestExportBlankExcelTemplate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_creates_xlsx_file(self):
        from data_engine.excel_loader import export_blank_excel_template
        p = os.path.join(self.tmp, "blank.xlsx")
        export_blank_excel_template(p, ["ID", "Name", "Score"])
        self.assertTrue(os.path.exists(p))

    def test_headers_match(self):
        from data_engine.excel_loader import export_blank_excel_template, load_excel
        headers_in = ["EnrollNo", "Student_Name", "Physics", "Chemistry", "Maths", "Total"]
        p = os.path.join(self.tmp, "blank.xlsx")
        export_blank_excel_template(p, headers_in)
        loaded_headers, rows = load_excel(p)
        self.assertEqual(loaded_headers, headers_in)
        self.assertEqual(rows, [])  # No data rows

    def test_single_column_template(self):
        from data_engine.excel_loader import export_blank_excel_template, load_excel
        p = os.path.join(self.tmp, "single.xlsx")
        export_blank_excel_template(p, ["OnlyField"])
        headers, _ = load_excel(p)
        self.assertEqual(headers, ["OnlyField"])

    def test_many_columns(self):
        from data_engine.excel_loader import export_blank_excel_template, load_excel
        cols = [f"Col_{i}" for i in range(30)]
        p = os.path.join(self.tmp, "wide.xlsx")
        export_blank_excel_template(p, cols)
        headers, _ = load_excel(p)
        self.assertEqual(headers, cols)

    def test_unicode_headers(self):
        from data_engine.excel_loader import export_blank_excel_template, load_excel
        cols = ["नाम", "रोल_नं", "अंक"]
        p = os.path.join(self.tmp, "unicode.xlsx")
        export_blank_excel_template(p, cols)
        headers, _ = load_excel(p)
        self.assertEqual(headers, cols)


class TestDatasetBackup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _sample_rows(self):
        return [
            {"ID": "EN001", "Name": "Alice", "Score": "95"},
            {"ID": "EN002", "Name": "Bob",   "Score": "88"},
        ]

    def test_backup_creates_file(self):
        from data_engine.excel_loader import export_dataset_backup
        p = os.path.join(self.tmp, "data.dataset.backup")
        export_dataset_backup(p, self._sample_rows(), ["ID", "Name", "Score"])
        self.assertTrue(os.path.exists(p))

    def test_backup_is_valid_json(self):
        from data_engine.excel_loader import export_dataset_backup
        p = os.path.join(self.tmp, "data.dataset.backup")
        export_dataset_backup(p, self._sample_rows(), ["ID", "Name", "Score"])
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["format_version"], "1.0")
        self.assertEqual(data["record_count"], 2)

    def test_backup_roundtrip(self):
        from data_engine.excel_loader import export_dataset_backup, import_dataset_backup
        headers = ["ID", "Name", "Score"]
        rows = self._sample_rows()
        meta = {"template_name": "Grade10", "template_id": "abc-123"}
        p = os.path.join(self.tmp, "data.dataset.backup")
        export_dataset_backup(p, rows, headers, meta)
        imp_headers, imp_rows, imp_meta = import_dataset_backup(p)
        self.assertEqual(imp_headers, headers)
        self.assertEqual(len(imp_rows), 2)
        self.assertEqual(imp_rows[1]["Name"], "Bob")
        self.assertEqual(imp_meta["template_name"], "Grade10")

    def test_backup_unicode(self):
        from data_engine.excel_loader import export_dataset_backup, import_dataset_backup
        rows = [{"नाम": "आर्यन", "अंक": "९५"}]
        p = os.path.join(self.tmp, "unicode.dataset.backup")
        export_dataset_backup(p, rows, ["नाम", "अंक"])
        _, imp_rows, _ = import_dataset_backup(p)
        self.assertEqual(imp_rows[0]["नाम"], "आर्यन")

    def test_backup_empty_rows(self):
        from data_engine.excel_loader import export_dataset_backup, import_dataset_backup
        p = os.path.join(self.tmp, "empty.dataset.backup")
        export_dataset_backup(p, [], ["A", "B"])
        _, rows, _ = import_dataset_backup(p)
        self.assertEqual(rows, [])

    def test_backup_no_metadata(self):
        from data_engine.excel_loader import export_dataset_backup, import_dataset_backup
        p = os.path.join(self.tmp, "nometa.dataset.backup")
        export_dataset_backup(p, self._sample_rows(), ["ID", "Name", "Score"])
        _, _, meta = import_dataset_backup(p)
        self.assertEqual(meta, {})

class TestSheetDetectionAndSelection(unittest.TestCase):
    """Test get_sheet_names and multi-sheet loading in excel_loader."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_multi_sheet_xlsx(self, sheets_data: dict[str, tuple[list[str], list[list]]], filename="multi.xlsx") -> str:
        path = os.path.join(self.tmp, filename)
        wb = openpyxl.Workbook()
        # Remove default sheet
        wb.remove(wb.active)

        for sheet_title, (headers, rows) in sheets_data.items():
            ws = wb.create_sheet(title=sheet_title)
            ws.append(headers)
            for row in rows:
                ws.append(row)

        wb.save(path)
        return path

    def test_single_sheet_names(self):
        from data_engine.excel_loader import get_sheet_names
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Class_10A"
        ws.append(["ID", "Name"])
        p = os.path.join(self.tmp, "single.xlsx")
        wb.save(p)

        names = get_sheet_names(p)
        self.assertEqual(names, ["Class_10A"])

    def test_multi_sheet_names(self):
        from data_engine.excel_loader import get_sheet_names
        p = self._make_multi_sheet_xlsx({
            "Section_A": (["ID", "Name"], [["1", "Alice"]]),
            "Section_B": (["ID", "Name"], [["2", "Bob"]]),
            "Section_C": (["ID", "Name"], [["3", "Charlie"]]),
        })
        names = get_sheet_names(p)
        self.assertEqual(names, ["Section_A", "Section_B", "Section_C"])

    def test_load_specific_sheet_by_name(self):
        from data_engine.excel_loader import load_excel
        p = self._make_multi_sheet_xlsx({
            "Section_A": (["ID", "Name"], [["1", "Alice"]]),
            "Section_B": (["Roll", "Student"], [["101", "Bob"]]),
        })
        headers_b, rows_b = load_excel(p, sheet_name="Section_B")
        self.assertEqual(headers_b, ["Roll", "Student"])
        self.assertEqual(len(rows_b), 1)
        self.assertEqual(rows_b[0]["Student"], "Bob")

        headers_a, rows_a = load_excel(p, sheet_name="Section_A")
        self.assertEqual(headers_a, ["ID", "Name"])
        self.assertEqual(rows_a[0]["Name"], "Alice")

    def test_load_default_loads_first_sheet(self):
        from data_engine.excel_loader import load_excel
        p = self._make_multi_sheet_xlsx({
            "FirstSheet": (["A", "B"], [["val1", "val2"]]),
            "SecondSheet": (["X", "Y"], [["val3", "val4"]]),
        })
        headers, rows = load_excel(p)
        self.assertEqual(headers, ["A", "B"])
        self.assertEqual(rows[0]["A"], "val1")

    def test_sheet_selection_dialog_ui(self):
        import sys
        from PyQt6.QtWidgets import QApplication
        from ui.dialogs.sheet_selection_dialog import SheetSelectionDialog

        _app = QApplication.instance() or QApplication(sys.argv)
        dlg = SheetSelectionDialog(["Sheet1", "Sheet2", "Sheet3"], filename="test.xlsx")
        self.assertEqual(dlg.sheet_names, ["Sheet1", "Sheet2", "Sheet3"])
        self.assertEqual(dlg.get_selected_sheet(), "Sheet1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
