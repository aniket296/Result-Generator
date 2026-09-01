"""
PDF Generation & Batch Processing Engine using PyMuPDF (fitz).

Handles:
- Coordinate mapping from Qt Canvas to PDF points.
- Background embedding (Image or PDF).
- Stamping text placeholders.
- Pre-generation disk space & write permission checks.
- Unique file naming (_1, _2 etc.).
- QThread worker with pause/resume/skip for missing data handling.
"""
from __future__ import annotations

import os
import shutil
from typing import Callable

import fitz  # PyMuPDF
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QMutex, QWaitCondition


def check_pre_generation(output_dir: str, estimated_size_bytes: int = 10 * 1024 * 1024) -> tuple[bool, str]:
    """
    Checks if output directory exists and is writable, and checks free disk space (+10% buffer).
    """
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            return False, f"Could not create output directory: {e}"

    # Check write permissions
    test_file = os.path.join(output_dir, ".write_test.tmp")
    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
    except Exception as e:
        return False, f"Output directory is not writable: {e}"

    # Check disk space
    try:
        total, used, free = shutil.disk_usage(output_dir)
        # Required size + 10% safety buffer
        required_space = int(estimated_size_bytes * 1.1)
        if free < required_space:
            return False, f"Insufficient disk space. Free: {free // (1024*1024)} MB, Required: {required_space // (1024*1024)} MB"
    except Exception as e:
        return False, f"Failed to check disk space: {e}"

    return True, ""


def get_unique_filename(output_dir: str, base_name: str, ext: str = ".pdf") -> str:
    """
    Intelligent naming: Returns non-conflicting filepath by appending _1, _2, etc.
    """
    # Sanitize base_name
    safe_base = "".join(c for c in base_name if c.isalnum() or c in (" ", "_", "-")).rstrip()
    if not safe_base:
        safe_base = "Result"

    candidate = os.path.join(output_dir, f"{safe_base}{ext}")
    if not os.path.exists(candidate):
        return candidate

    counter = 1
    while True:
        candidate = os.path.join(output_dir, f"{safe_base}_{counter}{ext}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def _hex_to_rgb_float(hex_str: str) -> tuple[float, float, float]:
    """Convert hex string (#RRGGBB) to (r, g, b) with values in 0.0 - 1.0."""
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 6:
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        return (r, g, b)
    return (0.0, 0.0, 0.0)


def generate_single_pdf(
    template_state: dict,
    row_data: dict[str, str],
    output_path: str,
) -> None:
    """
    Renders one single student record onto the template and saves the flattened PDF.
    """
    bg_info = template_state.get("background", {})
    bg_type = bg_info.get("type", "")
    bg_path = bg_info.get("path", "")
    canvas_info = template_state.get("canvas", {})
    canvas_w = float(canvas_info.get("width", 794))
    canvas_h = float(canvas_info.get("height", 1123))

    doc = fitz.open()

    if bg_type == "pdf" and os.path.exists(bg_path):
        bg_doc = fitz.open(bg_path)
        doc.insert_pdf(bg_doc, from_page=0, to_page=0)
        page = doc[0]
        page_rect = page.rect
        scale_x = page_rect.width / canvas_w
        scale_y = page_rect.height / canvas_h
    elif os.path.exists(bg_path):
        # Image background or default blank page
        page_rect = fitz.Rect(0, 0, canvas_w * 72.0 / 96.0, canvas_h * 72.0 / 96.0)
        page = doc.new_page(width=page_rect.width, height=page_rect.height)
        scale_x = page_rect.width / canvas_w
        scale_y = page_rect.height / canvas_h
        # Insert image
        page.insert_image(page_rect, filename=bg_path)
    else:
        # Blank canvas
        page_rect = fitz.Rect(0, 0, canvas_w * 72.0 / 96.0, canvas_h * 72.0 / 96.0)
        page = doc.new_page(width=page_rect.width, height=page_rect.height)
        scale_x = page_rect.width / canvas_w
        scale_y = page_rect.height / canvas_h

    # Stamp fields
    fields = template_state.get("fields", [])
    for field in fields:
        mapped_col = field.get("mapped_column") or field.get("label", "")
        # Raw display only - pull string directly
        val = row_data.get(mapped_col, "")
        if not val:
            # Check by label if mapped column was empty
            val = row_data.get(field.get("label", ""), "")

        fx = float(field.get("x", 0)) * scale_x
        fy = float(field.get("y", 0)) * scale_y
        fw = float(field.get("width", 100)) * scale_x
        fh = float(field.get("height", 30)) * scale_y

        target_rect = fitz.Rect(fx, fy, fx + fw, fy + fh)
        font_size = float(field.get("font_size", 12)) * scale_y
        color = _hex_to_rgb_float(field.get("color", "#000000"))
        align_str = field.get("alignment", "Left")
        
        # PyMuPDF alignment: 0=Left, 1=Center, 2=Right
        align_val = 0
        if align_str == "Center":
            align_val = 1
        elif align_str == "Right":
            align_val = 2

        # Insert textbox (fitz handles bounding & alignment)
        page.insert_textbox(
            target_rect,
            str(val),
            fontsize=font_size,
            color=color,
            align=align_val,
        )

    # Flatten / save
    doc.save(output_path, deflate=True)
    doc.close()


class GeneratorWorker(QThread):
    """
    Background worker thread to perform batch PDF generation.
    Supports pause/resume when empty cell error occurs.
    """
    progress_updated = pyqtSignal(int, int, str)  # current, total, current_filename
    error_occurred = pyqtSignal(int, str, dict)   # row_idx (1-based), column_name, row_dict
    generation_finished = pyqtSignal(int, int)     # success_count, skipped_count
    generation_aborted = pyqtSignal(str)          # reason

    # Actions user can choose on error
    ACTION_RETRY = 1
    ACTION_SKIP = 2
    ACTION_CANCEL = 3

    def __init__(
        self,
        template_state: dict,
        rows: list[dict[str, str]],
        output_dir: str,
        name_column: str = "",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.template_state = template_state
        self.rows = rows
        self.output_dir = output_dir
        self.name_column = name_column

        self._is_cancelled = False
        self._mutex = QMutex()
        self._wait_condition = QWaitCondition()
        self._user_action: int = self.ACTION_RETRY

    def cancel(self):
        self._mutex.lock()
        self._is_cancelled = True
        self._wait_condition.wakeAll()
        self._mutex.unlock()

    def resolve_error(self, action: int):
        """Called by UI thread to provide the action to resume generation."""
        self._mutex.lock()
        self._user_action = action
        self._wait_condition.wakeAll()
        self._mutex.unlock()

    def run(self):
        total = len(self.rows)
        success_count = 0
        skipped_count = 0

        # Get list of required mapped columns from template
        required_cols = []
        for field in self.template_state.get("fields", []):
            col = field.get("mapped_column") or field.get("label", "")
            if col and col not in required_cols:
                required_cols.append(col)

        row_idx = 0
        while row_idx < total:
            self._mutex.lock()
            if self._is_cancelled:
                self._mutex.unlock()
                self.generation_aborted.emit("Generation was cancelled by user.")
                return
            self._mutex.unlock()

            row = self.rows[row_idx]
            
            # Check for missing/empty values in required mapped columns
            missing_col = None
            for col in required_cols:
                val = row.get(col, "")
                if not val or not str(val).strip():
                    missing_col = col
                    break

            if missing_col:
                # Emit error and pause thread until UI responds
                self.error_occurred.emit(row_idx + 1, missing_col, row)
                
                self._mutex.lock()
                self._wait_condition.wait(self._mutex)
                action = self._user_action
                self._mutex.unlock()

                if action == self.ACTION_CANCEL or self._is_cancelled:
                    self.generation_aborted.emit("Generation stopped due to missing data.")
                    return
                elif action == self.ACTION_SKIP:
                    skipped_count += 1
                    row_idx += 1
                    continue
                elif action == self.ACTION_RETRY:
                    # Will retry this same row index
                    continue

            # Determine file base name
            base_name = ""
            if self.name_column and self.name_column in row:
                base_name = str(row[self.name_column]).strip()
            if not base_name:
                base_name = f"Result_Row_{row_idx + 1}"

            out_file = get_unique_filename(self.output_dir, base_name)
            filename = os.path.basename(out_file)

            self.progress_updated.emit(row_idx + 1, total, filename)

            try:
                generate_single_pdf(self.template_state, row, out_file)
                success_count += 1
            except Exception as e:
                self.generation_aborted.emit(f"Error writing PDF ({filename}): {e}")
                return

            row_idx += 1

        self.generation_finished.emit(success_count, skipped_count)
