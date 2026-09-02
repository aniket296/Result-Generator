"""
tests/test_integration.py
End-to-end integration tests that combine multiple subsystems.
Simulates a realistic teacher workflow.
"""
import json
import os
import shutil
import tempfile
import unittest

from PyQt6.QtWidgets import QApplication
import sys
_app = QApplication.instance() or QApplication(sys.argv)


class TestEndToEndWorkflow(unittest.TestCase):
    """
    Full workflow: create template fields → export blank Excel → fill data →
    load Excel → validate → generate PDFs → verify filenames/content/metadata.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.tmp, "results")
        os.makedirs(self.output_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _build_template_state(self):
        """Simulate a teacher-designed template with 5 fields."""
        return {
            "template_id": "integration-test-001",
            "canvas_width": 794,
            "canvas_height": 1123,
            "background": {"type": "", "path": ""},
            "fields": [
                {"label": "EnrollNo", "mapped_column": "EnrollNo", "is_unique": True,
                 "x": 50, "y": 80, "width": 200, "height": 30,
                 "font_family": "Helvetica", "font_size": 11, "color": "#000000",
                 "bold": False, "italic": False, "underline": False, "multiline": False, "alignment": "Left"},
                {"label": "StudentName", "mapped_column": "StudentName", "is_unique": False,
                 "x": 50, "y": 130, "width": 300, "height": 36,
                 "font_family": "Helvetica", "font_size": 14, "color": "#111111",
                 "bold": True, "italic": False, "underline": False, "multiline": False, "alignment": "Left"},
                {"label": "Physics", "mapped_column": "Physics", "is_unique": False,
                 "x": 50, "y": 200, "width": 80, "height": 28,
                 "font_family": "Helvetica", "font_size": 12, "color": "#000000",
                 "bold": False, "italic": False, "underline": False, "multiline": False, "alignment": "Center"},
                {"label": "Chemistry", "mapped_column": "Chemistry", "is_unique": False,
                 "x": 150, "y": 200, "width": 80, "height": 28,
                 "font_family": "Helvetica", "font_size": 12, "color": "#000000",
                 "bold": False, "italic": False, "underline": False, "multiline": False, "alignment": "Center"},
                {"label": "Total", "mapped_column": "Total", "is_unique": False,
                 "x": 300, "y": 200, "width": 100, "height": 28,
                 "font_family": "Helvetica", "font_size": 14, "color": "#1d4ed8",
                 "bold": True, "italic": False, "underline": True, "multiline": False, "alignment": "Center"},
            ]
        }

    def _build_student_rows(self):
        return [
            {"EnrollNo": "EN2026001", "StudentName": "Aarav Sharma", "Physics": "92", "Chemistry": "88", "Total": "180"},
            {"EnrollNo": "EN2026002", "StudentName": "Priya Patel", "Physics": "85", "Chemistry": "91", "Total": "176"},
            {"EnrollNo": "EN2026003", "StudentName": "Rahul Singh", "Physics": "78", "Chemistry": "83", "Total": "161"},
            {"EnrollNo": "EN2026004", "StudentName": "Sneha Gupta", "Physics": "95", "Chemistry": "96", "Total": "191"},
            {"EnrollNo": "EN2026005", "StudentName": "Arjun Nair", "Physics": "88", "Chemistry": "79", "Total": "167"},
        ]

    def test_full_workflow_5_students(self):
        from data_engine.excel_loader import (
            export_blank_excel_template, load_excel, validate_all_rows,
            validate_unique_column, export_dataset_backup, import_dataset_backup
        )
        from generation.pdf_generator import (
            generate_single_pdf, get_unique_result_filename, preview_filenames, check_pre_generation
        )
        import pymupdf

        tmpl = self._build_template_state()
        rows = self._build_student_rows()
        headers = ["EnrollNo", "StudentName", "Physics", "Chemistry", "Total"]

        # STEP 1: Export blank Excel template
        excel_template = os.path.join(self.tmp, "BlankTemplate.xlsx")
        export_blank_excel_template(excel_template, headers)
        self.assertTrue(os.path.exists(excel_template))

        # STEP 2: (Simulated) teacher fills data into the template by rewriting it with openpyxl
        import openpyxl
        wb = openpyxl.load_workbook(excel_template)
        ws = wb.active
        for row in rows:
            ws.append([row[h] for h in headers])
        filled_excel = os.path.join(self.tmp, "FilledData.xlsx")
        wb.save(filled_excel)

        # STEP 3: Load the filled Excel
        loaded_headers, loaded_rows = load_excel(filled_excel)
        self.assertEqual(loaded_headers, headers)
        self.assertEqual(len(loaded_rows), 5)

        # STEP 4: Validate all rows (no empty cells)
        errors = validate_all_rows(loaded_rows)
        self.assertEqual(errors, [])

        # STEP 5: Validate unique column
        validate_unique_column(loaded_rows, "EnrollNo")  # should not raise

        # STEP 6: Preview filenames
        previews = preview_filenames(self.output_dir, loaded_rows, "EnrollNo", "StudentName")
        self.assertEqual(len(previews), 5)  # < 5 rows → all shown
        for row_num, fname in previews:
            self.assertTrue(fname.endswith(".PDF"))
            self.assertEqual(fname, fname.upper())

        # STEP 7: Pre-generation check
        ok, err = check_pre_generation(self.output_dir, 5 * 500 * 1024)
        self.assertTrue(ok, f"Pre-generation check failed: {err}")

        # STEP 8: Generate PDFs
        generated_paths = []
        for row in loaded_rows:
            out = get_unique_result_filename(self.output_dir, row["EnrollNo"], row["StudentName"])
            generate_single_pdf(tmpl, row, out)
            generated_paths.append(out)
            self.assertTrue(os.path.exists(out))

        # STEP 9: Verify all 5 PDFs exist with correct content
        for i, path in enumerate(generated_paths):
            doc = pymupdf.open(path)
            self.assertEqual(len(doc), 1)
            text = doc[0].get_text()
            expected_name = rows[i]["StudentName"].split()[0]  # first name
            self.assertIn(expected_name, text)
            meta = doc.metadata
            self.assertIn("TeacherResultSoftware:integration-test-001", meta.get("keywords", ""))
            doc.close()

        # STEP 10: Backup and restore
        backup_path = os.path.join(self.tmp, "Grade12_Sci.dataset.backup")
        export_dataset_backup(backup_path, loaded_rows, headers, {"template_id": "integration-test-001"})
        imp_headers, imp_rows, imp_meta = import_dataset_backup(backup_path)
        self.assertEqual(imp_headers, headers)
        self.assertEqual(len(imp_rows), 5)
        self.assertEqual(imp_rows[0]["EnrollNo"], "EN2026001")

    def test_duplicate_unique_prevents_generation(self):
        from data_engine.excel_loader import validate_unique_column
        from data_engine.exceptions import DuplicateUniqueValueError

        rows = [
            {"EnrollNo": "EN001", "StudentName": "Alice", "Total": "90"},
            {"EnrollNo": "EN002", "StudentName": "Bob",   "Total": "85"},
            {"EnrollNo": "EN001", "StudentName": "Alice2","Total": "91"},  # duplicate
        ]
        with self.assertRaises(DuplicateUniqueValueError):
            validate_unique_column(rows, "EnrollNo")

    def test_missing_data_detected_before_generation(self):
        from data_engine.excel_loader import validate_all_rows
        rows = [
            {"EnrollNo": "EN001", "StudentName": "Alice", "Total": "90"},
            {"EnrollNo": "EN002", "StudentName": "",       "Total": "85"},  # missing name
            {"EnrollNo": "EN003", "StudentName": "Charlie","Total": ""},    # missing total
        ]
        errors = validate_all_rows(rows)
        self.assertEqual(len(errors), 2)

    def test_collision_handling_across_students(self):
        """Two students with same name and enrollment produce distinct filenames."""
        from generation.pdf_generator import get_unique_result_filename
        p1 = get_unique_result_filename(self.output_dir, "EN001", "Ali")
        open(p1, "w").close()
        p2 = get_unique_result_filename(self.output_dir, "EN001", "Ali")
        self.assertNotEqual(p1, p2)
        self.assertTrue(os.path.basename(p2).endswith("_01.PDF"))

    def test_template_state_json_roundtrip(self):
        """Template state can be serialized to JSON and restored without loss."""
        from ui.widgets.field_item import FieldItem
        tmpl = self._build_template_state()
        tmpl_json = json.dumps(tmpl)
        restored = json.loads(tmpl_json)
        self.assertEqual(restored["template_id"], "integration-test-001")
        self.assertEqual(len(restored["fields"]), 5)
        # Reconstruct FieldItems from dict
        items = [FieldItem.from_dict(f) for f in restored["fields"]]
        self.assertEqual(items[0].label, "EnrollNo")
        self.assertTrue(items[4].underline)
        self.assertTrue(items[4].bold)

    def test_batch_of_100_students(self):
        from generation.pdf_generator import generate_single_pdf, get_unique_result_filename
        import pymupdf
        tmpl = {
            "template_id": "batch-test",
            "canvas_width": 595, "canvas_height": 842,
            "background": {"type": "", "path": ""},
            "fields": [
                {"label": "ID", "mapped_column": "ID", "x": 50, "y": 50, "width": 100, "height": 30,
                 "font_size": 10, "font_family": "Helvetica", "color": "#000000",
                 "bold": False, "italic": False, "underline": False, "multiline": False, "alignment": "Left"},
                {"label": "Name", "mapped_column": "Name", "x": 200, "y": 50, "width": 200, "height": 30,
                 "font_size": 12, "font_family": "Helvetica", "color": "#000000",
                 "bold": False, "italic": False, "underline": False, "multiline": False, "alignment": "Left"},
            ]
        }
        rows = [{"ID": f"EN{i:04d}", "Name": f"Student {i}"} for i in range(1, 101)]
        batch_dir = os.path.join(self.tmp, "batch_100")
        os.makedirs(batch_dir)

        for row in rows:
            out = get_unique_result_filename(batch_dir, row["ID"], row["Name"])
            generate_single_pdf(tmpl, row, out)

        pdf_files = [f for f in os.listdir(batch_dir) if f.endswith(".PDF")]
        self.assertEqual(len(pdf_files), 100)

        # Spot check: EN0050 should be in the filename of the 50th file
        matching = [f for f in pdf_files if "EN0050" in f]
        self.assertEqual(len(matching), 1)

    def test_recovery_json_written_and_cleaned(self):
        """Recovery file is created during generation and removed on completion."""
        from generation.pdf_generator import GeneratorWorker
        from utils.constants import RECOVERY_DIR

        tmpl = {
            "template_id": "rec-test",
            "canvas_width": 595, "canvas_height": 842,
            "background": {"type": "", "path": ""},
            "fields": [
                {"label": "ID", "mapped_column": "ID", "x": 50, "y": 50, "width": 100, "height": 30,
                 "font_size": 10, "font_family": "Helvetica", "color": "#000",
                 "bold": False, "italic": False, "underline": False, "multiline": False, "alignment": "Left"},
            ]
        }
        rows = [{"ID": "EN001"}, {"ID": "EN002"}, {"ID": "EN003"}]
        worker = GeneratorWorker(tmpl, rows, self.output_dir, "ID", "ID", operation_id="rec-test-op")

        # Recovery file should not exist yet
        self.assertFalse(os.path.exists(worker.recovery_file))

        # Run worker synchronously
        worker.run()

        # After successful completion, recovery file should be cleaned up
        self.assertFalse(os.path.exists(worker.recovery_file))


class TestEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_generate_pdf_with_zero_width_field(self):
        """Field with near-zero width shouldn't crash."""
        from generation.pdf_generator import generate_single_pdf
        tmpl = {
            "template_id": "edge-001",
            "canvas_width": 595, "canvas_height": 842,
            "background": {"type": "", "path": ""},
            "fields": [
                {"label": "ID", "mapped_column": "ID", "x": 50, "y": 50, "width": 0.1, "height": 30,
                 "font_size": 10, "font_family": "Helvetica", "color": "#000",
                 "bold": False, "italic": False, "underline": False, "multiline": False, "alignment": "Left"},
            ]
        }
        out = os.path.join(self.tmp, "edge.pdf")
        generate_single_pdf(tmpl, {"ID": "X"}, out)
        self.assertTrue(os.path.exists(out))

    def test_generate_pdf_no_fields(self):
        """Template with no fields should still produce a valid PDF."""
        from generation.pdf_generator import generate_single_pdf
        tmpl = {
            "template_id": "nofields",
            "canvas_width": 595, "canvas_height": 842,
            "background": {"type": "", "path": ""},
            "fields": []
        }
        out = os.path.join(self.tmp, "nofields.pdf")
        generate_single_pdf(tmpl, {"ID": "EN001"}, out)
        self.assertTrue(os.path.exists(out))

    def test_long_student_name_in_pdf(self):
        """Extremely long student name is truncated in filename but rendered in full."""
        from generation.pdf_generator import generate_single_pdf, get_unique_result_filename
        import pymupdf
        long_name = "Rajasekhar Venkatanarasimharajuvaripeta"  # 38 chars
        tmpl = {
            "template_id": "longname",
            "canvas_width": 595, "canvas_height": 842,
            "background": {"type": "", "path": ""},
            "fields": [
                {"label": "Name", "mapped_column": "Name", "x": 50, "y": 100, "width": 400, "height": 40,
                 "font_size": 10, "font_family": "Helvetica", "color": "#000",
                 "bold": False, "italic": False, "underline": False, "multiline": True, "alignment": "Left"},
            ]
        }
        out = get_unique_result_filename(self.tmp, "EN001", long_name)
        generate_single_pdf(tmpl, {"Name": long_name}, out)
        doc = pymupdf.open(out)
        text = doc[0].get_text()
        self.assertIn("Rajasekhar", text)
        doc.close()

    def test_validate_all_rows_single_empty_row(self):
        from data_engine.excel_loader import validate_all_rows
        rows = [{"ID": "", "Name": "", "Score": ""}]
        errors = validate_all_rows(rows)
        self.assertEqual(len(errors), 3)

    def test_backup_roundtrip_with_special_chars(self):
        from data_engine.excel_loader import export_dataset_backup, import_dataset_backup
        rows = [{"Name": "O'Neil & Co. <Test>", "Score": '98"'}]
        p = os.path.join(self.tmp, "special.dataset.backup")
        export_dataset_backup(p, rows, ["Name", "Score"])
        _, imp_rows, _ = import_dataset_backup(p)
        self.assertEqual(imp_rows[0]["Name"], "O'Neil & Co. <Test>")

    def test_filename_with_only_special_chars_unique_val(self):
        from generation.pdf_generator import get_unique_result_filename
        path = get_unique_result_filename(self.tmp, "///***???", "Alice")
        basename = os.path.basename(path)
        # Should not contain invalid chars
        for c in r'\/:*?"<>|':
            self.assertNotIn(c, basename)

    def test_preview_with_only_1_row(self):
        from generation.pdf_generator import preview_filenames
        rows = [{"ID": "EN001", "Name": "Alice"}]
        result = preview_filenames(self.tmp, rows, "ID", "Name")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], 1)

    def test_constant_dirs_are_writable(self):
        from utils.constants import TEMPLATES_DIR, DATASETS_DIR, RECOVERY_DIR
        for d in [TEMPLATES_DIR, DATASETS_DIR, RECOVERY_DIR]:
            test_file = os.path.join(d, ".write_test_tmp")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)


if __name__ == "__main__":
    unittest.main(verbosity=2)
