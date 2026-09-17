"""
tests/test_pdf_generator.py
Full-scale tests for generation/pdf_generator.py.
Covers: sanitization, filenames, reserved names, collisions, preview,
pre-generation checks, PDF rendering, metadata, worker state machine.
"""
import datetime
import os
import shutil
import tempfile
import unittest

from PyQt6.QtWidgets import QApplication
import sys
_app = QApplication.instance() or QApplication(sys.argv)


class TestSanitizeFilenamePart(unittest.TestCase):
    def test_clean_text_unchanged(self):
        from generation.pdf_generator import sanitize_filename_part
        self.assertEqual(sanitize_filename_part("Alice"), "Alice")

    def test_replaces_backslash(self):
        from generation.pdf_generator import sanitize_filename_part
        self.assertNotIn("\\", sanitize_filename_part("a\\b"))

    def test_replaces_forward_slash(self):
        from generation.pdf_generator import sanitize_filename_part
        self.assertNotIn("/", sanitize_filename_part("EN2026/047"))

    def test_replaces_colon(self):
        from generation.pdf_generator import sanitize_filename_part
        self.assertNotIn(":", sanitize_filename_part("A:B"))

    def test_replaces_star(self):
        from generation.pdf_generator import sanitize_filename_part
        self.assertNotIn("*", sanitize_filename_part("A*B"))

    def test_replaces_question_mark(self):
        from generation.pdf_generator import sanitize_filename_part
        self.assertNotIn("?", sanitize_filename_part("A?B"))

    def test_replaces_double_quote(self):
        from generation.pdf_generator import sanitize_filename_part
        self.assertNotIn('"', sanitize_filename_part('A"B'))

    def test_replaces_angle_brackets(self):
        from generation.pdf_generator import sanitize_filename_part
        result = sanitize_filename_part("<Top> <Student>")
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)

    def test_replaces_pipe(self):
        from generation.pdf_generator import sanitize_filename_part
        self.assertNotIn("|", sanitize_filename_part("A|B"))

    def test_collapses_multiple_underscores(self):
        from generation.pdf_generator import sanitize_filename_part
        result = sanitize_filename_part("A///B")
        self.assertNotIn("__", result)

    def test_strips_leading_trailing_underscores(self):
        from generation.pdf_generator import sanitize_filename_part
        result = sanitize_filename_part("___hello___")
        self.assertFalse(result.startswith("_"))
        self.assertFalse(result.endswith("_"))

    def test_strips_leading_trailing_periods(self):
        from generation.pdf_generator import sanitize_filename_part
        result = sanitize_filename_part("...hello...")
        self.assertFalse(result.startswith("."))
        self.assertFalse(result.endswith("."))

    def test_empty_string_returns_unnamed(self):
        from generation.pdf_generator import sanitize_filename_part
        self.assertEqual(sanitize_filename_part(""), "UNNAMED")

    def test_all_invalid_chars_returns_unnamed(self):
        from generation.pdf_generator import sanitize_filename_part
        result = sanitize_filename_part("///***???")
        # After sanitization, everything stripped → UNNAMED
        self.assertEqual(result, "UNNAMED")

    def test_spaces_become_underscore(self):
        from generation.pdf_generator import sanitize_filename_part
        result = sanitize_filename_part("Rahul Sharma")
        self.assertNotIn(" ", result)

    def test_unicode_text_preserved(self):
        from generation.pdf_generator import sanitize_filename_part
        result = sanitize_filename_part("Aarav_सिंह")
        self.assertIn("Aarav", result)

    def test_control_characters_removed(self):
        from generation.pdf_generator import sanitize_filename_part
        result = sanitize_filename_part("A\x00B\x1fC")
        self.assertNotIn("\x00", result)
        self.assertNotIn("\x1f", result)


class TestGetUniqueResultFilename(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_basic_filename_structure(self):
        from generation.pdf_generator import get_unique_result_filename
        path = get_unique_result_filename(self.tmp, "EN001", "Alice Smith", ".PDF")
        basename = os.path.basename(path)
        self.assertTrue(basename.startswith("EN001_"))
        self.assertIn("ALICE", basename)
        self.assertTrue(basename.endswith(".PDF"))

    def test_uppercase_enforcement(self):
        from generation.pdf_generator import get_unique_result_filename
        path = get_unique_result_filename(self.tmp, "en001", "alice smith")
        self.assertEqual(os.path.basename(path), os.path.basename(path).upper())

    def test_returns_full_path(self):
        from generation.pdf_generator import get_unique_result_filename
        path = get_unique_result_filename(self.tmp, "EN001", "Alice")
        self.assertTrue(os.path.isabs(path))
        self.assertTrue(path.startswith(self.tmp))

    def test_no_collision_no_suffix(self):
        from generation.pdf_generator import get_unique_result_filename
        path = get_unique_result_filename(self.tmp, "EN001", "Alice")
        basename = os.path.basename(path)
        self.assertNotIn("_01", basename)

    def test_collision_adds_01_suffix(self):
        from generation.pdf_generator import get_unique_result_filename
        p1 = get_unique_result_filename(self.tmp, "EN001", "Alice")
        open(p1, "w").close()
        p2 = get_unique_result_filename(self.tmp, "EN001", "Alice")
        self.assertTrue(os.path.basename(p2).endswith("_01.PDF"))

    def test_collision_adds_02_suffix(self):
        from generation.pdf_generator import get_unique_result_filename
        p1 = get_unique_result_filename(self.tmp, "EN001", "Alice")
        open(p1, "w").close()
        p2 = get_unique_result_filename(self.tmp, "EN001", "Alice")
        open(p2, "w").close()
        p3 = get_unique_result_filename(self.tmp, "EN001", "Alice")
        self.assertTrue(os.path.basename(p3).endswith("_02.PDF"))

    def test_collision_zero_padded_under_100(self):
        from generation.pdf_generator import get_unique_result_filename
        for i in range(10):
            p = get_unique_result_filename(self.tmp, "ZERO", "PAD")
            open(p, "w").close()
        final = get_unique_result_filename(self.tmp, "ZERO", "PAD")
        basename = os.path.basename(final)
        # _10.PDF should be zero-padded to _10 (2 digits already)
        self.assertRegex(basename, r"_\d{2}\.PDF$")

    def test_reserved_name_CON(self):
        from generation.pdf_generator import get_unique_result_filename
        path = get_unique_result_filename(self.tmp, "CON", "Alice")
        self.assertTrue(os.path.basename(path).startswith("RESULT_CON"))

    def test_reserved_name_PRN(self):
        from generation.pdf_generator import get_unique_result_filename
        path = get_unique_result_filename(self.tmp, "PRN", "Bob")
        self.assertTrue(os.path.basename(path).startswith("RESULT_PRN"))

    def test_reserved_name_AUX(self):
        from generation.pdf_generator import get_unique_result_filename
        path = get_unique_result_filename(self.tmp, "AUX", "Charlie")
        self.assertTrue(os.path.basename(path).startswith("RESULT_AUX"))

    def test_reserved_name_NUL(self):
        from generation.pdf_generator import get_unique_result_filename
        path = get_unique_result_filename(self.tmp, "NUL", "Dave")
        self.assertTrue(os.path.basename(path).startswith("RESULT_NUL"))

    def test_reserved_name_COM1(self):
        from generation.pdf_generator import get_unique_result_filename
        path = get_unique_result_filename(self.tmp, "COM1", "Eve")
        self.assertTrue(os.path.basename(path).startswith("RESULT_COM1"))

    def test_reserved_name_LPT9(self):
        from generation.pdf_generator import get_unique_result_filename
        path = get_unique_result_filename(self.tmp, "LPT9", "Faye")
        self.assertTrue(os.path.basename(path).startswith("RESULT_LPT9"))

    def test_non_reserved_not_prefixed(self):
        from generation.pdf_generator import get_unique_result_filename
        path = get_unique_result_filename(self.tmp, "CONSOLE", "Test")
        self.assertFalse(os.path.basename(path).startswith("RESULT_CONSOLE"))

    def test_student_name_truncated_to_40_chars(self):
        from generation.pdf_generator import get_unique_result_filename
        long_name = "A" * 100
        path = get_unique_result_filename(self.tmp, "EN001", long_name)
        basename = os.path.basename(path).replace(".PDF", "")
        name_part = basename.split("_", 1)[1]
        self.assertLessEqual(len(name_part), 40)

    def test_ext_auto_uppercased(self):
        from generation.pdf_generator import get_unique_result_filename
        path = get_unique_result_filename(self.tmp, "EN001", "Alice", ".pdf")
        self.assertTrue(path.endswith(".PDF"))

    def test_ext_without_dot(self):
        from generation.pdf_generator import get_unique_result_filename
        path = get_unique_result_filename(self.tmp, "EN001", "Alice", "pdf")
        self.assertTrue(path.endswith(".PDF"))

    def test_invalid_chars_in_unique_val(self):
        from generation.pdf_generator import get_unique_result_filename
        path = get_unique_result_filename(self.tmp, "EN/2026:047", "Alice")
        basename = os.path.basename(path)
        self.assertNotIn("/", basename)
        self.assertNotIn(":", basename)

    def test_invalid_chars_in_name(self):
        from generation.pdf_generator import get_unique_result_filename
        path = get_unique_result_filename(self.tmp, "EN001", 'Rahul "Top" <Scorer>')
        basename = os.path.basename(path)
        self.assertNotIn('"', basename)
        self.assertNotIn("<", basename)
        self.assertNotIn(">", basename)


class TestPreviewFilenames(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _rows(self, n):
        return [{"ID": f"EN{i:03d}", "Name": f"Student_{i}"} for i in range(1, n+1)]

    def test_empty_rows_returns_empty(self):
        from generation.pdf_generator import preview_filenames
        result = preview_filenames(self.tmp, [], "ID", "Name")
        self.assertEqual(result, [])

    def test_one_row_preview(self):
        from generation.pdf_generator import preview_filenames
        result = preview_filenames(self.tmp, self._rows(1), "ID", "Name")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], 1)

    def test_two_rows_preview(self):
        from generation.pdf_generator import preview_filenames
        result = preview_filenames(self.tmp, self._rows(2), "ID", "Name")
        self.assertEqual(len(result), 2)

    def test_four_rows_preview(self):
        from generation.pdf_generator import preview_filenames
        result = preview_filenames(self.tmp, self._rows(4), "ID", "Name")
        self.assertEqual(len(result), 4)

    def test_five_rows_first3_last2(self):
        from generation.pdf_generator import preview_filenames
        result = preview_filenames(self.tmp, self._rows(5), "ID", "Name")
        self.assertEqual(len(result), 5)
        row_nums = [r[0] for r in result]
        self.assertEqual(row_nums, [1, 2, 3, 4, 5])

    def test_ten_rows_first3_last2(self):
        from generation.pdf_generator import preview_filenames
        result = preview_filenames(self.tmp, self._rows(10), "ID", "Name")
        self.assertEqual(len(result), 5)
        row_nums = [r[0] for r in result]
        self.assertEqual(row_nums[0], 1)
        self.assertEqual(row_nums[1], 2)
        self.assertEqual(row_nums[2], 3)
        self.assertEqual(row_nums[3], 9)
        self.assertEqual(row_nums[4], 10)

    def test_hundred_rows_first3_last2(self):
        from generation.pdf_generator import preview_filenames
        result = preview_filenames(self.tmp, self._rows(100), "ID", "Name")
        self.assertEqual(len(result), 5)
        row_nums = [r[0] for r in result]
        self.assertIn(1, row_nums)
        self.assertIn(100, row_nums)
        self.assertIn(99, row_nums)

    def test_preview_filenames_are_uppercase(self):
        from generation.pdf_generator import preview_filenames
        result = preview_filenames(self.tmp, self._rows(5), "ID", "Name")
        for _, fname in result:
            self.assertEqual(fname, fname.upper())

    def test_preview_collision_simulation(self):
        from generation.pdf_generator import preview_filenames
        # Pre-create a file so collision suffix should appear in preview
        rows = [{"ID": "EN001", "Name": "Alice"}, {"ID": "EN002", "Name": "Bob"}]
        # Create EN001_ALICE.PDF to force collision
        open(os.path.join(self.tmp, "EN001_ALICE.PDF"), "w").close()
        result = preview_filenames(self.tmp, rows, "ID", "Name")
        first = result[0][1]
        self.assertIn("_01", first)


class TestCheckPreGeneration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_valid_dir_passes(self):
        from generation.pdf_generator import check_pre_generation
        ok, err = check_pre_generation(self.tmp, 1024)
        self.assertTrue(ok)
        self.assertEqual(err, "")

    def test_creates_dir_if_not_exists(self):
        from generation.pdf_generator import check_pre_generation
        new_dir = os.path.join(self.tmp, "new_subdir")
        ok, err = check_pre_generation(new_dir, 1024)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(new_dir))

    def test_excessive_size_fails(self):
        from generation.pdf_generator import check_pre_generation
        # Require 10 TB – should fail on any normal disk
        ok, err = check_pre_generation(self.tmp, 10 * 1024**4)
        self.assertFalse(ok)
        self.assertIn("Insufficient disk space", err)

    def test_path_too_long_fails(self):
        from generation.pdf_generator import check_pre_generation
        long_path = "C:\\" + "a" * 250
        ok, err = check_pre_generation(long_path, 1024)
        self.assertFalse(ok)
        self.assertIn("too long", err)

    def test_write_test_file_cleaned_up(self):
        from generation.pdf_generator import check_pre_generation
        before = set(os.listdir(self.tmp))
        check_pre_generation(self.tmp, 1024)
        after = set(os.listdir(self.tmp))
        # No .tmp write_test file should remain
        new_files = after - before
        tmp_files = [f for f in new_files if f.startswith(".write_test")]
        self.assertEqual(tmp_files, [])

    def test_returns_false_with_error_string(self):
        from generation.pdf_generator import check_pre_generation
        ok, err = check_pre_generation(self.tmp, 10 * 1024**4)
        self.assertIsInstance(err, str)
        self.assertGreater(len(err), 0)


class TestHexToRgbFloat(unittest.TestCase):
    def test_black(self):
        from generation.pdf_generator import _hex_to_rgb_float
        self.assertEqual(_hex_to_rgb_float("#000000"), (0.0, 0.0, 0.0))

    def test_white(self):
        from generation.pdf_generator import _hex_to_rgb_float
        r, g, b = _hex_to_rgb_float("#FFFFFF")
        self.assertAlmostEqual(r, 1.0)
        self.assertAlmostEqual(g, 1.0)
        self.assertAlmostEqual(b, 1.0)

    def test_red(self):
        from generation.pdf_generator import _hex_to_rgb_float
        r, g, b = _hex_to_rgb_float("#FF0000")
        self.assertAlmostEqual(r, 1.0)
        self.assertAlmostEqual(g, 0.0)
        self.assertAlmostEqual(b, 0.0)

    def test_lowercase_hex(self):
        from generation.pdf_generator import _hex_to_rgb_float
        r, g, b = _hex_to_rgb_float("#ff0000")
        self.assertAlmostEqual(r, 1.0)

    def test_invalid_returns_black(self):
        from generation.pdf_generator import _hex_to_rgb_float
        self.assertEqual(_hex_to_rgb_float("#ZZZZZZ"), (0.0, 0.0, 0.0))


class TestGenerateSinglePdf(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _simple_template(self, fields=None, template_id="test-001"):
        return {
            "template_id": template_id,
            "canvas_width": 595,
            "canvas_height": 842,
            "background": {"type": "", "path": ""},
            "fields": fields or [
                {
                    "label": "Name",
                    "mapped_column": "Name",
                    "x": 50, "y": 100, "width": 300, "height": 36,
                    "font_family": "Helvetica", "font_size": 14,
                    "color": "#111111", "bold": False, "italic": False,
                    "underline": False, "multiline": False, "alignment": "Left"
                }
            ]
        }

    def test_creates_pdf_file(self):
        from generation.pdf_generator import generate_single_pdf
        out = os.path.join(self.tmp, "test.pdf")
        generate_single_pdf(self._simple_template(), {"Name": "Alice"}, out)
        self.assertTrue(os.path.exists(out))

    def test_pdf_has_one_page(self):
        import pymupdf
        from generation.pdf_generator import generate_single_pdf
        out = os.path.join(self.tmp, "test.pdf")
        generate_single_pdf(self._simple_template(), {"Name": "Alice"}, out)
        doc = pymupdf.open(out)
        self.assertEqual(len(doc), 1)
        doc.close()

    def test_text_in_output(self):
        import pymupdf
        from generation.pdf_generator import generate_single_pdf
        out = os.path.join(self.tmp, "test.pdf")
        generate_single_pdf(self._simple_template(), {"Name": "Priya Sharma"}, out)
        doc = pymupdf.open(out)
        text = doc[0].get_text()
        self.assertIn("Priya Sharma", text)
        doc.close()

    def test_template_id_in_metadata(self):
        import pymupdf
        from generation.pdf_generator import generate_single_pdf
        out = os.path.join(self.tmp, "test.pdf")
        generate_single_pdf(self._simple_template(template_id="uuid-xyz-999"), {"Name": "Alice"}, out)
        doc = pymupdf.open(out)
        meta = doc.metadata
        self.assertIn("TeacherResultSoftware:uuid-xyz-999", meta.get("keywords", ""))
        doc.close()

    def test_producer_in_metadata(self):
        import pymupdf
        from generation.pdf_generator import generate_single_pdf
        out = os.path.join(self.tmp, "test.pdf")
        generate_single_pdf(self._simple_template(), {"Name": "Alice"}, out)
        doc = pymupdf.open(out)
        self.assertIn("TeacherResultSoftware", doc.metadata.get("producer", ""))
        doc.close()

    def test_bold_field(self):
        import pymupdf
        from generation.pdf_generator import generate_single_pdf
        tmpl = self._simple_template(fields=[{
            "label": "Title", "mapped_column": "Title",
            "x": 50, "y": 50, "width": 200, "height": 40,
            "font_family": "Helvetica", "font_size": 12,
            "color": "#000000", "bold": True, "italic": False,
            "underline": False, "multiline": False, "alignment": "Left"
        }])
        out = os.path.join(self.tmp, "bold.pdf")
        generate_single_pdf(tmpl, {"Title": "BOLD TITLE"}, out)
        doc = pymupdf.open(out)
        self.assertEqual(len(doc), 1)
        doc.close()

    def test_multiline_field(self):
        import pymupdf
        from generation.pdf_generator import generate_single_pdf
        tmpl = self._simple_template(fields=[{
            "label": "Address", "mapped_column": "Address",
            "x": 50, "y": 200, "width": 300, "height": 80,
            "font_family": "Helvetica", "font_size": 11,
            "color": "#000000", "bold": False, "italic": False,
            "underline": False, "multiline": True, "alignment": "Left"
        }])
        out = os.path.join(self.tmp, "multiline.pdf")
        long_text = "123 Main Street, Sector 5, New Delhi, Delhi - 110001, India"
        generate_single_pdf(tmpl, {"Address": long_text}, out)
        doc = pymupdf.open(out)
        text = doc[0].get_text()
        self.assertIn("Main Street", text)
        doc.close()

    def test_center_alignment(self):
        from generation.pdf_generator import generate_single_pdf
        tmpl = self._simple_template(fields=[{
            "label": "Score", "mapped_column": "Score",
            "x": 100, "y": 150, "width": 200, "height": 36,
            "font_family": "Helvetica", "font_size": 18,
            "color": "#000000", "bold": False, "italic": False,
            "underline": False, "multiline": False, "alignment": "Center"
        }])
        out = os.path.join(self.tmp, "center.pdf")
        generate_single_pdf(tmpl, {"Score": "95/100"}, out)
        self.assertTrue(os.path.exists(out))

    def test_right_alignment(self):
        from generation.pdf_generator import generate_single_pdf
        tmpl = self._simple_template(fields=[{
            "label": "Date", "mapped_column": "Date",
            "x": 400, "y": 50, "width": 150, "height": 30,
            "font_family": "Helvetica", "font_size": 10,
            "color": "#333333", "bold": False, "italic": False,
            "underline": False, "multiline": False, "alignment": "Right"
        }])
        out = os.path.join(self.tmp, "right.pdf")
        generate_single_pdf(tmpl, {"Date": "01/09/2026"}, out)
        self.assertTrue(os.path.exists(out))

    def test_multiple_fields(self):
        import pymupdf
        from generation.pdf_generator import generate_single_pdf
        fields = [
            {"label": "ID", "mapped_column": "ID", "x": 50, "y": 50, "width": 100, "height": 30,
             "font_family": "Helvetica", "font_size": 10, "color": "#000000",
             "bold": False, "italic": False, "underline": False, "multiline": False, "alignment": "Left"},
            {"label": "Name", "mapped_column": "Name", "x": 200, "y": 50, "width": 200, "height": 30,
             "font_family": "Helvetica", "font_size": 12, "color": "#000000",
             "bold": True, "italic": False, "underline": False, "multiline": False, "alignment": "Left"},
            {"label": "Score", "mapped_column": "Score", "x": 50, "y": 120, "width": 100, "height": 30,
             "font_family": "Helvetica", "font_size": 14, "color": "#cc0000",
             "bold": False, "italic": False, "underline": False, "multiline": False, "alignment": "Center"},
        ]
        tmpl = self._simple_template(fields=fields)
        out = os.path.join(self.tmp, "multi.pdf")
        generate_single_pdf(tmpl, {"ID": "EN001", "Name": "Aarav Singh", "Score": "A+"}, out)
        doc = pymupdf.open(out)
        text = doc[0].get_text()
        self.assertIn("EN001", text)
        self.assertIn("Aarav", text)
        doc.close()

    def test_empty_value_does_not_crash(self):
        from generation.pdf_generator import generate_single_pdf
        out = os.path.join(self.tmp, "empty.pdf")
        generate_single_pdf(self._simple_template(), {"Name": ""}, out)
        self.assertTrue(os.path.exists(out))

    def test_unicode_text_in_pdf(self):
        import pymupdf
        from generation.pdf_generator import generate_single_pdf
        out = os.path.join(self.tmp, "unicode.pdf")
        generate_single_pdf(self._simple_template(), {"Name": "Aarav • Sharma"}, out)
        doc = pymupdf.open(out)
        text = doc[0].get_text()
        self.assertIn("Aarav", text)
        doc.close()

    def test_no_background_no_crash(self):
        from generation.pdf_generator import generate_single_pdf
        tmpl = self._simple_template()
        tmpl["background"] = {"type": "", "path": ""}
        out = os.path.join(self.tmp, "nobg.pdf")
        generate_single_pdf(tmpl, {"Name": "Alice"}, out)
        self.assertTrue(os.path.exists(out))

    def test_large_batch_pdf_generation(self):
        from generation.pdf_generator import generate_single_pdf
        for i in range(50):
            out = os.path.join(self.tmp, f"student_{i:03d}.pdf")
            generate_single_pdf(
                self._simple_template(),
                {"Name": f"Student {i}"},
                out
            )
        pdf_files = [f for f in os.listdir(self.tmp) if f.endswith(".pdf")]
        self.assertEqual(len(pdf_files), 50)


class TestGeneratorWorkerInit(unittest.TestCase):
    def test_worker_initializes(self):
        from generation.pdf_generator import GeneratorWorker
        tmpl = {"template_id": "x", "canvas_width": 595, "canvas_height": 842,
                "background": {"type": "", "path": ""}, "fields": []}
        rows = [{"ID": "1", "Name": "Alice"}]
        worker = GeneratorWorker(tmpl, rows, "/tmp", "ID", "Name")
        self.assertIsNotNone(worker)
        self.assertEqual(worker.rows, rows)
        self.assertEqual(worker.unique_col, "ID")
        self.assertEqual(worker.name_col, "Name")

    def test_worker_retry_counts_starts_empty(self):
        from generation.pdf_generator import GeneratorWorker
        worker = GeneratorWorker({}, [], "/tmp", "ID", "Name")
        self.assertEqual(worker.retry_counts, {})

    def test_worker_generated_files_starts_empty(self):
        from generation.pdf_generator import GeneratorWorker
        worker = GeneratorWorker({}, [], "/tmp", "ID", "Name")
        self.assertEqual(worker.generated_files, [])

    def test_worker_failed_records_starts_empty(self):
        from generation.pdf_generator import GeneratorWorker
        worker = GeneratorWorker({}, [], "/tmp", "ID", "Name")
        self.assertEqual(worker.failed_records, [])

    def test_worker_has_operation_id(self):
        from generation.pdf_generator import GeneratorWorker
        worker = GeneratorWorker({}, [], "/tmp", "ID", "Name")
        self.assertTrue(len(worker.operation_id) > 0)

    def test_worker_custom_operation_id(self):
        from generation.pdf_generator import GeneratorWorker
        worker = GeneratorWorker({}, [], "/tmp", "ID", "Name", operation_id="custom-op-123")
        self.assertEqual(worker.operation_id, "custom-op-123")

    def test_action_constants(self):
        from generation.pdf_generator import GeneratorWorker
        self.assertEqual(GeneratorWorker.ACTION_RETRY, 1)
        self.assertEqual(GeneratorWorker.ACTION_SKIP, 2)
        self.assertEqual(GeneratorWorker.ACTION_CANCEL, 3)


class TestReservedNamesSet(unittest.TestCase):
    def test_all_reserved_names_present(self):
        from generation.pdf_generator import RESERVED_WINDOWS_NAMES
        expected = {"CON", "PRN", "AUX", "NUL",
                    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
                    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}
        for name in expected:
            self.assertIn(name, RESERVED_WINDOWS_NAMES)

    def test_non_reserved_not_in_set(self):
        from generation.pdf_generator import RESERVED_WINDOWS_NAMES
        self.assertNotIn("RESULT", RESERVED_WINDOWS_NAMES)
        self.assertNotIn("STUDENT", RESERVED_WINDOWS_NAMES)
class TestFieldExactPositioning(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_text_positioned_at_exact_field_coordinates(self):
        import pymupdf
        from generation.pdf_generator import generate_single_pdf

        template = {
            "template_id": "pos-test-1",
            "canvas_width": 595,
            "canvas_height": 842,
            "background": {"type": "", "path": ""},
            "fields": [
                {
                    "label": "Student_Name",
                    "mapped_column": "Student_Name",
                    "x": 120.0,
                    "y": 250.0,
                    "width": 200.0,
                    "height": 36.0,
                    "font_family": "Helvetica",
                    "font_size": 12,
                    "color": "#000000",
                    "bold": False,
                    "italic": False,
                    "underline": False,
                    "multiline": False,
                    "alignment": "Left",
                }
            ],
        }

        out_pdf = os.path.join(self.tmp, "pos_test.pdf")
        generate_single_pdf(template, {"Student_Name": "Priya"}, out_pdf)

        doc = pymupdf.open(out_pdf)
        words = doc[0].get_text("words")
        doc.close()

        self.assertTrue(len(words) > 0)
        word_x0, word_y0, word_x1, word_y1, text, *_ = words[0]
        self.assertEqual(text, "Priya")
        self.assertAlmostEqual(word_x0, 120.0, delta=2.0)
        self.assertAlmostEqual(word_y0, 250.0, delta=2.0)

    def test_text_positioned_vertical_alignment_middle(self):
        import pymupdf
        from generation.pdf_generator import generate_single_pdf

        template = {
            "template_id": "pos-test-mid",
            "canvas_width": 595,
            "canvas_height": 842,
            "background": {"type": "", "path": ""},
            "fields": [
                {
                    "label": "Student_Name",
                    "mapped_column": "Student_Name",
                    "x": 100.0,
                    "y": 200.0,
                    "width": 200.0,
                    "height": 60.0,
                    "font_family": "Helvetica",
                    "font_size": 12,
                    "color": "#000000",
                    "bold": False,
                    "italic": False,
                    "underline": False,
                    "multiline": False,
                    "alignment": "Left",
                    "v_alignment": "Middle",
                }
            ],
        }

        out_pdf = os.path.join(self.tmp, "pos_test_mid.pdf")
        generate_single_pdf(template, {"Student_Name": "Priya"}, out_pdf)

        doc = pymupdf.open(out_pdf)
        words = doc[0].get_text("words")
        doc.close()

        self.assertTrue(len(words) > 0)
        word_x0, word_y0, word_x1, word_y1, text, *_ = words[0]
        self.assertEqual(text, "Priya")
        self.assertAlmostEqual(word_x0, 100.0, delta=2.0)
        # Expected y0 is around 200 + (60 - 12*1.15)/2 = ~223.1
        self.assertGreater(word_y0, 215.0)
        self.assertLess(word_y0, 235.0)


class TestFormatFilenameFromPattern(unittest.TestCase):
    def test_default_pattern_substitution(self):
        from generation.pdf_generator import format_filename_from_pattern
        row = {"Enrollment number": "EN-2026", "Name": "Aarav Sharma"}
        fname = format_filename_from_pattern("[Enrollment number]_[Name].pdf", row, row_index=1)
        self.assertEqual(fname, "EN-2026_AARAV_SHARMA.PDF")

    def test_case_insensitive_token_matching(self):
        from generation.pdf_generator import format_filename_from_pattern
        row = {"roll_no": "101", "student_name": "Diya Patel"}
        fname = format_filename_from_pattern("[Roll No]_[Student Name].pdf", row, row_index=1)
        self.assertEqual(fname, "101_DIYA_PATEL.PDF")

    def test_strips_illegal_windows_characters(self):
        from generation.pdf_generator import format_filename_from_pattern
        row = {"ID": "A/B:C*D?E<F>G|H", "Name": 'Test "Student"'}
        fname = format_filename_from_pattern("[ID] - [Name].pdf", row, row_index=1)
        self.assertNotIn("/", fname)
        self.assertNotIn(":", fname)
        self.assertNotIn("*", fname)
        self.assertNotIn("?", fname)
        self.assertNotIn("<", fname)
        self.assertNotIn(">", fname)
        self.assertNotIn("|", fname)
        self.assertNotIn('"', fname)

    def test_missing_or_blank_token_fallback(self):
        from generation.pdf_generator import format_filename_from_pattern
        row = {"Enrollment number": "", "Name": None}
        fname = format_filename_from_pattern("[Enrollment number]_[Name].pdf", row, row_index=5)
        self.assertEqual(fname, "REC5_STUDENT_5.PDF")

    def test_custom_tokens_and_literals(self):
        from generation.pdf_generator import format_filename_from_pattern
        row = {"Class": "10-B", "Roll No": "45", "Name": "Rohan"}
        fname = format_filename_from_pattern("Result_[Class]_[Roll No]_[Name]", row, row_index=1)
        self.assertEqual(fname, "RESULT_10-B_45_ROHAN.PDF")

    def test_reserved_windows_names(self):
        from generation.pdf_generator import format_filename_from_pattern
        row = {"Name": "CON"}
        fname = format_filename_from_pattern("[Name].pdf", row, row_index=1)
        self.assertTrue(fname.startswith("RESULT_CON"))

    def test_unique_result_filename_with_pattern_collision(self):
        from generation.pdf_generator import get_unique_result_filename
        tmp = tempfile.mkdtemp()
        try:
            row = {"Enrollment number": "EN001", "Name": "Alice"}
            # Create first
            p1 = get_unique_result_filename(tmp, pattern="[Enrollment number]_[Name].pdf", row_data=row, row_index=1)
            self.assertEqual(os.path.basename(p1), "EN001_ALICE.PDF")
            with open(p1, "w") as f:
                f.write("test")

            # Create second (collision)
            p2 = get_unique_result_filename(tmp, pattern="[Enrollment number]_[Name].pdf", row_data=row, row_index=1)
            self.assertEqual(os.path.basename(p2), "EN001_ALICE_01.PDF")
        finally:
            shutil.rmtree(tmp)

    def test_preview_filenames_with_pattern(self):
        from generation.pdf_generator import preview_filenames
        tmp = tempfile.mkdtemp()
        try:
            rows = [
                {"Enrollment": "E1", "Student": "Alice"},
                {"Enrollment": "E2", "Student": "Bob"},
            ]
            prevs = preview_filenames(tmp, rows, pattern="[Enrollment]_[Student].pdf")
            self.assertEqual(len(prevs), 2)
            self.assertEqual(prevs[0], (1, "E1_ALICE.PDF"))
            self.assertEqual(prevs[1], (2, "E2_BOB.PDF"))
        finally:
            shutil.rmtree(tmp)


class TestZipPackaging(unittest.TestCase):
    def test_package_output_to_zip_creates_valid_archive(self):
        import zipfile
        from generation.pdf_generator import package_output_to_zip
        tmp = tempfile.mkdtemp()
        try:
            out_folder = os.path.join(tmp, "Class10_Results")
            os.makedirs(out_folder, exist_ok=True)
            bundle_dir = os.path.join(out_folder, "Print_Bundles")
            os.makedirs(bundle_dir, exist_ok=True)

            with open(os.path.join(out_folder, "101_ALICE.PDF"), "w") as f:
                f.write("Alice PDF content")
            with open(os.path.join(out_folder, "102_BOB.PDF"), "w") as f:
                f.write("Bob PDF content")
            with open(os.path.join(bundle_dir, "Class_10A_Master_Print.pdf"), "w") as f:
                f.write("Bundle content")

            zip_path = package_output_to_zip(out_folder)
            self.assertTrue(os.path.exists(zip_path))
            self.assertTrue(zip_path.endswith(".zip"))

            # Verify contents of zip
            with zipfile.ZipFile(zip_path, "r") as zf:
                namelist = zf.namelist()
                self.assertIn("101_ALICE.PDF", namelist)
                self.assertIn("102_BOB.PDF", namelist)
                self.assertTrue(any("Class_10A_Master_Print.pdf" in name for name in namelist))
        finally:
            shutil.rmtree(tmp)

    def test_package_output_to_zip_progress_callback(self):
        from generation.pdf_generator import package_output_to_zip
        tmp = tempfile.mkdtemp()
        try:
            out_folder = os.path.join(tmp, "Results")
            os.makedirs(out_folder, exist_ok=True)
            for i in range(3):
                with open(os.path.join(out_folder, f"result_{i}.pdf"), "w") as f:
                    f.write(f"content {i}")

            calls = []
            def on_prog(cur, tot, fn):
                calls.append((cur, tot, fn))

            zip_path = package_output_to_zip(out_folder, progress_callback=on_prog)
            self.assertEqual(len(calls), 3)
            self.assertEqual(calls[-1][0], 3)
            self.assertEqual(calls[-1][1], 3)
            self.assertTrue(os.path.exists(zip_path))
        finally:
            shutil.rmtree(tmp)


class TestAuditReport(unittest.TestCase):
    def test_write_generation_audit_report_clean(self):
        from generation.pdf_generator import write_generation_audit_report
        tmp = tempfile.mkdtemp()
        try:
            start = datetime.datetime(2026, 9, 18, 10, 0, 0)
            end = datetime.datetime(2026, 9, 18, 10, 0, 5)
            report_p = write_generation_audit_report(
                output_dir=tmp,
                template_name="Term 1 Report Card",
                template_id="uuid-12345",
                template_path="/path/to/template.bg.png",
                dataset_name="Class_10_Students.xlsx",
                total_processed=50,
                succeeded_count=50,
                skipped_count=0,
                failed_count=0,
                elapsed_seconds=5.25,
                start_time=start,
                end_time=end,
                created_bundles=["/path/to/Print_Bundles/Class_10A_Master_Print.pdf"],
                created_zip_path="/path/to/Class10_Results.zip",
            )
            self.assertTrue(os.path.exists(report_p))
            self.assertTrue(report_p.endswith("generation_report.txt"))

            with open(report_p, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("BATCH RESULT GENERATION AUDIT REPORT", content)
            self.assertIn("5.25 seconds", content)
            self.assertIn("Term 1 Report Card", content)
            self.assertIn("uuid-12345", content)
            self.assertIn("Class_10_Students.xlsx", content)
            self.assertIn("Total Records    : 50", content)
            self.assertIn("PDFs Succeeded   : 50", content)
            self.assertIn("Success Rate     : 100.0%", content)
            self.assertIn("Class_10A_Master_Print.pdf", content)
            self.assertIn("Class10_Results.zip", content)
            self.assertIn("Zero skipped or failed records", content)
        finally:
            shutil.rmtree(tmp)

    def test_write_generation_audit_report_with_failures_and_skips(self):
        from generation.pdf_generator import write_generation_audit_report
        tmp = tempfile.mkdtemp()
        try:
            report_p = write_generation_audit_report(
                output_dir=tmp,
                template_name="Term 1 Report Card",
                template_id="uuid-999",
                template_path="/template.png",
                dataset_name="Dataset.xlsx",
                total_processed=10,
                succeeded_count=7,
                skipped_count=2,
                failed_count=1,
                failed_records=[
                    {"row_index": 4, "student_name": "Charlie", "unique_val": "105", "error": "PyMuPDF render error"}
                ],
                skipped_records=[
                    {"row_num": 2, "student_name": "Alice", "unique_val": "102", "reason": "Empty cell in 'Math'"},
                    {"row_num": 3, "student_name": "Bob", "unique_val": "103", "reason": "Empty cell in 'Science'"},
                ],
                elapsed_seconds=2.40,
            )
            self.assertTrue(os.path.exists(report_p))
            with open(report_p, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("Total Records    : 10", content)
            self.assertIn("PDFs Succeeded   : 7", content)
            self.assertIn("Skipped Records  : 2", content)
            self.assertIn("Failed Records   : 1", content)
            self.assertIn("Success Rate     : 70.0%", content)
            self.assertIn("[SKIPPED RECORDS]", content)
            self.assertIn("Row 2 [102 - Alice]: Empty cell in 'Math'", content)
            self.assertIn("Row 3 [103 - Bob]: Empty cell in 'Science'", content)
            self.assertIn("[FAILED RECORDS]", content)
            self.assertIn("Row 5 [105 - Charlie]: PyMuPDF render error", content)
        finally:
            shutil.rmtree(tmp)

    def test_generator_worker_generates_audit_report(self):
        from generation.pdf_generator import GeneratorWorker
        tmp = tempfile.mkdtemp()
        try:
            tmpl = {
                "template_id": "rep-test-tmpl",
                "template_name": "Sample Report Card",
                "canvas_width": 400.0,
                "canvas_height": 600.0,
                "fields": [
                    {"label": "Name", "mapped_column": "Name", "x": 10, "y": 10, "width": 100, "height": 30}
                ]
            }
            rows = [
                {"ID": "101", "Name": "Alice"},
                {"ID": "102", "Name": "Bob"},
            ]
            worker = GeneratorWorker(
                template_state=tmpl,
                rows=rows,
                output_dir=tmp,
                unique_col="ID",
                name_col="Name",
                dataset_name="SampleStudents.xlsx",
            )
            worker.run()

            report_file = os.path.join(tmp, "generation_report.txt")
            self.assertTrue(os.path.exists(report_file))
            self.assertTrue(os.path.exists(worker.report_path))
            self.assertGreater(worker.elapsed_seconds, 0.0)

            with open(report_file, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("Sample Report Card", content)
            self.assertIn("SampleStudents.xlsx", content)
            self.assertIn("Total Records    : 2", content)
            self.assertIn("PDFs Succeeded   : 2", content)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main(verbosity=2)

