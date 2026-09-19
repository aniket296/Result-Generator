"""
generation/pdf_generator.py
Comprehensive PDF Generation, Validation, Collision Handling & Recovery Engine.

Features:
- Windows-compliant filename sanitization, uppercase enforcement (UNIQUE_STUDENT.PDF).
- Collision resolution (_01.PDF, _02.PDF ... _100.PDF).
- Reserved Windows device name handling (CON, PRN, AUX, NUL, COM1-9, LPT1-9).
- High-fidelity PyMuPDF vector & image rendering with multiline word-wrapping.
- Template UUID metadata stamping.
- Pre-generation disk space check (+10% buffer) and write access verification.
- Non-blocking QThread worker with pause/resume/skip state machine.
- 3-retry per record cap.
- Crash recovery state tracking (.recovery.json).
- Session cancellation cleanup.
"""
from __future__ import annotations

import datetime
import io
import json
import math
import os
import re
import shutil
import uuid
import zipfile
from typing import Any, Callable

from PyQt6.QtCore import QMutex, QObject, QThread, QWaitCondition, pyqtSignal
import pymupdf

from data_engine.header_normalizer import find_matching_header
from utils.constants import RECOVERY_DIR

# ── Optional matplotlib (Agg backend) for chart rendering ────────────────────
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _MATPLOTLIB_AVAILABLE = True
except ImportError:
    _MATPLOTLIB_AVAILABLE = False

# ── Optional qrcode library for offline QR generation ────────────────────────
try:
    import qrcode
    from qrcode.image.pil import PilImage as _QrPilImage
    _QRCODE_AVAILABLE = True
except ImportError:
    _QRCODE_AVAILABLE = False


# ── Filename & Path Helpers ───────────────────────────────────────────────────

RESERVED_WINDOWS_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def sanitize_filename_part(text: str) -> str:
    """
    Sanitize a filename component:
    - Replace Windows-invalid characters with '_'
    - Collapse consecutive underscores to a single '_'
    - Remove path traversal dot segments
    - Strip leading/trailing underscores, spaces, and periods
    """
    if not text:
        return "UNNAMED"

    # Replace invalid chars: \ / : * ? " < > | and non-printables
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', str(text))
    # A filename component must never contain a parent-directory segment.
    cleaned = re.sub(r'\.{2,}', '_', cleaned)
    # Collapse multiple underscores/spaces
    cleaned = re.sub(r'[\s_]+', '_', cleaned)
    cleaned = cleaned.strip(" ._")

    return cleaned if cleaned else "UNNAMED"


def format_filename_from_pattern(
    pattern: str,
    row: dict[str, str],
    row_index: int = 1,
    default_pattern: str = "[Enrollment number]_[Name].pdf",
    ext: str = ".PDF",
) -> str:
    """
    Parse bracketed tokens like [Column_Name] in pattern and substitute with row values.
    - Matches tokens exact or normalized/case-insensitively against row keys.
    - Strips illegal Windows filename characters (\\ / : * ? " < > |).
    - Falls back safely to index naming (e.g. REC{row_index}) if a column value is missing or blank.
    - Enforces reserved Windows device name protection and uppercase extension.
    """
    raw_pattern = (pattern or default_pattern).strip()
    if raw_pattern.lower().endswith(".pdf"):
        raw_pattern = raw_pattern[:-4]

    if not raw_pattern:
        raw_pattern = "[Enrollment number]_[Name]"

    def replace_token(match: re.Match) -> str:
        token = match.group(1).strip()
        val = ""
        # 1. Exact match in row
        if token in row:
            val = str(row[token] or "").strip()
        else:
            # 2. Case-insensitive / fuzzy match
            matched_key = find_matching_header(token, list(row.keys()))
            if matched_key and matched_key in row:
                val = str(row[matched_key] or "").strip()

        # 3. Fallback safely to index naming if missing or blank
        if not val or val.lower() == "nan":
            lowered = token.lower()
            if any(k in lowered for k in ["roll", "enroll", "id", "num"]):
                val = f"REC{row_index}"
            elif any(k in lowered for k in ["name", "student"]):
                val = f"STUDENT_{row_index}"
            else:
                val = f"ROW{row_index}"

        return sanitize_filename_part(val)

    # Substitute [Tokens]
    result_base = re.sub(r'\[([^\]]+)\]', replace_token, raw_pattern)

    # Sanitize literal characters outside tokens
    result_base = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', result_base)
    result_base = re.sub(r'[\s_]+', '_', result_base)
    result_base = result_base.strip(" ._")

    if not result_base:
        result_base = f"RESULT_{row_index}"

    result_base = result_base.upper()

    # Reserved names check
    first_token = result_base.split("_")[0]
    if first_token in RESERVED_WINDOWS_NAMES:
        result_base = f"RESULT_{result_base}"

    ext_clean = ext.upper() if ext.startswith(".") else f".{ext.upper()}"
    return f"{result_base}{ext_clean}"


def get_unique_result_filename(
    output_dir: str,
    unique_val: str = "",
    student_name: str = "",
    ext: str = ".PDF",
    pattern: str = "",
    row_data: dict[str, str] | None = None,
    row_index: int = 1,
) -> str:
    """
    Constructs the exact uppercase filename with collision handling (_01, _02, ..., _100)
    and reserved name protection. Supports tokenized dynamic pattern when pattern and row_data are given.
    """
    if pattern and row_data is not None:
        filename = format_filename_from_pattern(pattern, row_data, row_index=row_index, ext=ext)
        base_name, file_ext = os.path.splitext(filename)
    else:
        u = sanitize_filename_part(unique_val)
        s = sanitize_filename_part(student_name)[:40].strip(" ._")
        if not s:
            s = "UNNAMED"

        base_name = f"{u}_{s}".upper()

        # Reserved names check
        first_token = base_name.split("_")[0]
        if first_token in RESERVED_WINDOWS_NAMES:
            base_name = f"RESULT_{base_name}"

        file_ext = ext.upper() if ext.startswith(".") else f".{ext.upper()}"

    candidate_path = os.path.join(output_dir, f"{base_name}{file_ext}")
    if not os.path.exists(candidate_path):
        return candidate_path

    # Collision loop with formatted padding (_01, _02, ... _100)
    counter = 1
    while True:
        suffix = f"_{counter:02d}" if counter < 100 else f"_{counter}"
        candidate_path = os.path.join(output_dir, f"{base_name}{suffix}{file_ext}")
        if not os.path.exists(candidate_path):
            return candidate_path
        counter += 1


def preview_filenames(
    output_dir: str,
    rows: list[dict[str, str]],
    unique_col: str = "",
    name_col: str = "",
    ext: str = ".PDF",
    pattern: str = "",
) -> list[tuple[int, str]]:
    """
    Generate accurate preview of final filenames.
    For < 5 records, previews all.
    For >= 5 records, previews the first 3 and last 2 records.
    Returns: list of (row_1_indexed, filename_only)
    """
    total = len(rows)
    if total == 0:
        return []

    if total < 5:
        target_indices = list(range(total))
    else:
        target_indices = [0, 1, 2, total - 2, total - 1]

    results: list[tuple[int, str]] = []
    simulated_used_paths: set[str] = set()

    for idx in target_indices:
        row = rows[idx]
        if pattern:
            filename = format_filename_from_pattern(pattern, row, row_index=idx + 1, ext=ext)
            base, ext_clean = os.path.splitext(filename)
        else:
            u = row.get(unique_col, f"REC{idx+1}")
            s = row.get(name_col, "")
            u_clean = sanitize_filename_part(u)
            s_clean = sanitize_filename_part(s)[:40].strip(" ._") or "UNNAMED"
            base = f"{u_clean}_{s_clean}".upper()
            if base.split("_")[0] in RESERVED_WINDOWS_NAMES:
                base = f"RESULT_{base}"
            ext_clean = ext.upper() if ext.startswith(".") else f".{ext.upper()}"

        candidate = os.path.join(output_dir, f"{base}{ext_clean}")

        if os.path.exists(candidate) or candidate in simulated_used_paths:
            cnt = 1
            while True:
                suffix = f"_{cnt:02d}" if cnt < 100 else f"_{cnt}"
                candidate = os.path.join(output_dir, f"{base}{suffix}{ext_clean}")
                if not os.path.exists(candidate) and candidate not in simulated_used_paths:
                    break
                cnt += 1

        simulated_used_paths.add(candidate)
        results.append((idx + 1, os.path.basename(candidate)))

    return results


# ── Pre-generation System Checks ─────────────────────────────────────────────

def check_pre_generation(
    output_dir: str,
    estimated_size_bytes: int = 10 * 1024 * 1024,
) -> tuple[bool, str]:
    """
    Validates:
    1. Output folder creation & accessibility.
    2. Write permissions.
    3. Disk space (+10% safety margin).
    4. Path length safety.
    """
    if len(os.path.abspath(output_dir)) > 240:
        return False, f"Target folder path is too long ({len(output_dir)} characters). Please select a shorter path."

    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as exc:
            return False, f"Could not create destination directory: {exc}"

    # Write access test
    test_file = os.path.join(output_dir, f".write_test_{uuid.uuid4().hex[:8]}.tmp")
    try:
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("write_test")
        os.remove(test_file)
    except Exception as exc:
        return False, f"Destination folder is not writable (Permission Denied): {exc}"

    # Disk space check with +10% safety margin
    try:
        _, _, free = shutil.disk_usage(output_dir)
        required_space = int(estimated_size_bytes * 1.1)
        if free < required_space:
            free_mb = free // (1024 * 1024)
            req_mb = required_space // (1024 * 1024)
            return False, (
                f"Insufficient disk space in target drive.\n"
                f"Available: {free_mb} MB\n"
                f"Required (with 10% safety buffer): {req_mb} MB"
            )
    except Exception as exc:
        return False, f"Failed to determine available disk space: {exc}"

    return True, ""


# ── Color & Drawing Helpers ───────────────────────────────────────────────────

def _hex_to_rgb_float(hex_str: str) -> tuple[float, float, float]:
    """Convert hex (#RRGGBB) to (r, g, b) float values [0.0, 1.0].
    Returns black (0, 0, 0) for any malformed or invalid hex string.
    """
    try:
        hex_str = hex_str.lstrip("#")
        if len(hex_str) == 6:
            r = int(hex_str[0:2], 16) / 255.0
            g = int(hex_str[2:4], 16) / 255.0
            b = int(hex_str[4:6], 16) / 255.0
            return (r, g, b)
    except (ValueError, AttributeError):
        pass
    return (0.0, 0.0, 0.0)


def _extract_field_value(f: dict[str, Any], row_data: dict[str, Any]) -> str:
    """Safely extracts and formats string value from row_data for a template field."""
    raw_val = None
    mapped_col = f.get("mapped_column")
    label = f.get("label")

    # 1. Direct match with mapped column name
    if mapped_col and mapped_col in row_data:
        raw_val = row_data[mapped_col]
    # 2. Direct match with label name
    elif label and label in row_data:
        raw_val = row_data[label]
    else:
        # 3. Dynamic alias & fuzzy matching
        candidates = [k for k in [mapped_col, label] if k]
        available_cols = list(row_data.keys())
        for cand in candidates:
            matched_col = find_matching_header(str(cand), available_cols)
            if matched_col and matched_col in row_data:
                raw_val = row_data[matched_col]
                break

        # Fallback: case-insensitive/trimmed iteration
        if raw_val is None:
            for cand in candidates:
                cand_clean = str(cand).strip().lower()
                for rk, rv in row_data.items():
                    if str(rk).strip().lower() == cand_clean:
                        raw_val = rv
                        break
                if raw_val is not None:
                    break

    # 4. Explicit type casting & graceful handling of None, NaN, etc.
    if raw_val is None:
        return ""
    if isinstance(raw_val, float):
        if math.isnan(raw_val) or math.isinf(raw_val):
            return ""
        if raw_val.is_integer():
            return str(int(raw_val))
        return str(raw_val)
    if isinstance(raw_val, (int, bool)):
        return str(raw_val)

    s_val = str(raw_val).strip()
    if s_val.lower() in ("nan", "none", "null", "<na>"):
        return ""
    return s_val


# ── Text Measurement & Auto-Shrink Font Helpers ───────────────────────────────

def measure_text_width(text: str, font_name: str, font_size: float) -> float:
    """
    Measure the pixel/point width of a text string using PyMuPDF font metrics.
    """
    if not text:
        return 0.0
    return float(pymupdf.get_text_length(text, fontname=font_name, fontsize=font_size))


def fit_single_line_font_size(
    text: str,
    font_name: str,
    initial_size: float,
    max_width: float,
    min_size: float = 4.0,
    step: float = 0.5,
    padding: float = 2.0,
) -> float:
    """
    Measure text pixel width against field box width and step down font size by 0.5pt increments
    until the text fits comfortably inside the bounding box.
    """
    if not text or max_width <= 0:
        return float(initial_size)

    target_w = max(1.0, float(max_width) - float(padding) * 2.0)
    cur_size = float(initial_size)

    while cur_size > min_size:
        w = measure_text_width(text, font_name, cur_size)
        if w <= target_w:
            return cur_size
        cur_size = max(min_size, round(cur_size - step, 2))

    return cur_size


def fit_multiline_font_size(
    rect: pymupdf.Rect,
    text: str,
    font_name: str,
    initial_size: float,
    min_size: float = 4.0,
    step: float = 0.5,
    align: int = 0,
) -> float:
    """
    For multiline blocks (e.g. addresses, long remarks), determine font size by stepping down
    by 0.5pt increments until the text fits comfortably inside the bounding box with word wrapping.
    """
    if not text or rect.width <= 0 or rect.height <= 0:
        return float(initial_size)

    cur_size = float(initial_size)
    scratch_doc = pymupdf.open()
    try:
        scratch_page = scratch_doc.new_page(
            width=max(rect.width + 100, 400),
            height=max(rect.height + 100, 400),
        )
        test_rect = pymupdf.Rect(0, 0, rect.width, rect.height)
        while cur_size > min_size:
            rc = scratch_page.insert_textbox(
                test_rect,
                text,
                fontsize=cur_size,
                fontname=font_name,
                align=align,
            )
            if rc >= 0:
                return cur_size
            cur_size = max(min_size, round(cur_size - step, 2))
    finally:
        scratch_doc.close()

    return cur_size


# ── Chart Image Renderer ──────────────────────────────────────────────────────

def _render_chart_to_image(
    chart_spec: dict[str, Any],
    row_data: dict[str, Any],
    width_px: int,
    height_px: int,
) -> bytes:
    """
    Render a per-student performance bar chart to PNG bytes using matplotlib.

    Returns empty bytes if matplotlib is unavailable or columns are missing.
    """
    if not _MATPLOTLIB_AVAILABLE:
        return b""

    columns    = chart_spec.get("chart_columns", [])
    chart_style = chart_spec.get("chart_style", "vertical")

    if not columns:
        return b""

    # ── Extract numeric values ────────────────────────────────────────────
    labels: list[str] = []
    values: list[float] = []
    for col in columns:
        raw = row_data.get(col, "") or ""
        try:
            str_raw = str(raw).strip().replace(",", "")
            if str_raw.lower() in ("", "nan", "none", "<na>", "n/a"):
                val = 0.0
            else:
                val = float(str_raw)
            if math.isnan(val) or math.isinf(val):
                val = 0.0
        except (ValueError, TypeError):
            val = 0.0
        labels.append(str(col))
        values.append(val)

    # ── Figure setup ──────────────────────────────────────────────────────
    dpi   = 96
    fig_w = max(1.0, width_px  / dpi)
    fig_h = max(1.0, height_px / dpi)

    _COLORS = [
        "#4f7ef8", "#10b981", "#f59e0b", "#ef4444",
        "#8b5cf6", "#06b6d4", "#ec4899", "#14b8a6",
    ]
    bar_colors = [_COLORS[i % len(_COLORS)] for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
    fig.patch.set_alpha(0.0)
    ax.set_facecolor("white")

    # ── Draw bars ─────────────────────────────────────────────────────────
    if chart_style == "horizontal":
        bars = ax.barh(labels, values, color=bar_colors, height=0.55, edgecolor="none")
        ax.set_xlabel("Score", fontsize=8)
        ax.set_xlim(left=0)
        ax.xaxis.set_tick_params(labelsize=7)
        ax.yaxis.set_tick_params(labelsize=7)
        for bar, val in zip(bars, values):
            if val > 0:
                ax.text(
                    bar.get_width() + max(0.5, ax.get_xlim()[1] * 0.01),
                    bar.get_y() + bar.get_height() / 2,
                    f"{val:.0f}",
                    va="center", ha="left", fontsize=7, color="#374151",
                )
    else:
        bars = ax.bar(labels, values, color=bar_colors, width=0.55, edgecolor="none")
        ax.set_ylabel("Score", fontsize=8)
        ax.set_ylim(bottom=0)
        ax.xaxis.set_tick_params(labelsize=7, rotation=20)
        ax.yaxis.set_tick_params(labelsize=7)
        for bar, val in zip(bars, values):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(0.5, ax.get_ylim()[1] * 0.01),
                    f"{val:.0f}",
                    ha="center", va="bottom", fontsize=7, color="#374151",
                )

    # ── Styling ───────────────────────────────────────────────────────────
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_alpha(0.3)
    ax.tick_params(colors="#374151")

    # ── Save to bytes and close ───────────────────────────────────────────
    buf = io.BytesIO()
    try:
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", transparent=True)
        buf.seek(0)
        return buf.getvalue()
    finally:
        plt.close("all")
        buf.close()


# ── Badge Rule Evaluator ──────────────────────────────────────────────────────

def _evaluate_badge_rule(
    column: str,
    operator: str,
    threshold: str,
    row_data: dict[str, Any],
) -> bool:
    """
    Evaluate if a student record meets the condition for a badge to be displayed.
    Handles numeric values, percentages, and string equality comparisons.
    """
    if not column:
        return False

    raw_val = _extract_field_value({"mapped_column": column, "label": column}, row_data)
    if not raw_val:
        # Empty values: only match == "" or != "something"
        t_str = str(threshold).strip()
        if operator == "==":
            return t_str == ""
        elif operator == "!=":
            return t_str != ""
        return False

    s_clean = str(raw_val).strip().rstrip("%").strip().replace(",", "")
    t_clean = str(threshold).strip().rstrip("%").strip().replace(",", "")

    # Try numeric comparison first
    try:
        s_num = float(s_clean)
        t_num = float(t_clean)
        if operator == ">=":
            return s_num >= t_num
        elif operator == ">":
            return s_num > t_num
        elif operator == "<=":
            return s_num <= t_num
        elif operator == "<":
            return s_num < t_num
        elif operator == "==":
            return s_num == t_num
        elif operator == "!=":
            return s_num != t_num
    except (ValueError, TypeError):
        pass

    # Fallback: case-insensitive string comparison
    s_low = str(raw_val).strip().lower()
    t_low = str(threshold).strip().lower()
    if operator == "==":
        return s_low == t_low
    elif operator == "!=":
        return s_low != t_low
    elif operator == ">=":
        return s_low >= t_low
    elif operator == ">":
        return s_low > t_low
    elif operator == "<=":
        return s_low <= t_low
    elif operator == "<":
        return s_low < t_low

    return False


def find_student_photo_path(photo_dir: str, id_val: str) -> str | None:
    """
    Look for a student photo in photo_dir matching id_val with standard image extensions.
    Supports .jpg, .jpeg, .png, .bmp, .webp (case-insensitive).
    """
    if not photo_dir or not os.path.isdir(photo_dir) or not id_val:
        return None

    clean_id = str(id_val).strip()
    if not clean_id or clean_id.lower() in ("nan", "none", "<na>"):
        return None

    # 1. Direct match with common extensions
    for ext in (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".JPG", ".JPEG", ".PNG", ".BMP", ".WEBP"):
        candidate = os.path.join(photo_dir, f"{clean_id}{ext}")
        if os.path.isfile(candidate):
            return candidate

    # 2. Case-insensitive scan in photo_dir
    try:
        lower_id = clean_id.lower()
        for fname in os.listdir(photo_dir):
            stem, ext = os.path.splitext(fname)
            if stem.lower() == lower_id and ext.lower() in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
                full_path = os.path.join(photo_dir, fname)
                if os.path.isfile(full_path):
                    return full_path
    except Exception:
        pass

    return None


def _interpolate_qr_payload(template: str, row_data: dict[str, str]) -> str:
    """
    Replaces bracketed column tokens like [Name], [Roll No], [Total]
    with the student's corresponding value from row_data.
    Supports normalized/aliased header lookup.
    """
    if not template:
        return ""

    headers = list(row_data.keys())

    def replacer(match: re.Match) -> str:
        token = match.group(1).strip()
        # 1. Direct match
        if token in row_data:
            val = row_data[token]
            return "" if val is None else str(val)
        # 2. Aliased / fuzzy match
        matched = find_matching_header(token, headers)
        if matched and matched in row_data:
            val = row_data[matched]
            return "" if val is None else str(val)
        # Fallback: keep original token
        return match.group(0)

    return re.sub(r"\[(.*?)\]", replacer, template)


def _generate_qr_png_bytes(payload: str, box_size: int = 10, border: int = 1) -> bytes:
    """
    Generate monochrome PNG bytes for a QR code from payload string using offline qrcode library.
    """
    if not _QRCODE_AVAILABLE:
        raise RuntimeError("qrcode library is not installed or available.")

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=max(1, int(box_size)),
        border=max(0, int(border)),
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Dynamic Variable-Row Subject Table Helpers ───────────────────────────────

def _extract_student_subjects(
    table_spec: dict[str, Any],
    row_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Extracts subject names and marks for a student from row_data based on table_spec configuration.
    Returns a list of dicts: [{'subject': str, 'marks': str, 'max_marks': str, 'grade': str}]
    """
    from data_engine.academic_engine import calculate_grade

    subject_columns = table_spec.get("subject_columns", [])
    max_marks = float(table_spec.get("max_marks", 100.0))
    show_grade = bool(table_spec.get("show_grade", True))
    show_max_marks = bool(table_spec.get("show_max_marks", True))

    subjects: list[dict[str, Any]] = []
    headers = list(row_data.keys())

    if subject_columns:
        for col in subject_columns:
            val = None
            if col in row_data:
                val = row_data[col]
            else:
                matched = find_matching_header(col, headers)
                if matched and matched in row_data:
                    val = row_data[matched]

            if val is not None:
                val_str = str(val).strip()
                if val_str and val_str.lower() not in ("nan", "none", "<na>", "-", "absent", "ab"):
                    grade_str = ""
                    if show_grade:
                        grade_str, _ = calculate_grade(val_str, max_score=max_marks)

                    max_m_str = f"{int(max_marks) if max_marks.is_integer() else max_marks}" if show_max_marks else ""
                    subjects.append({
                        "subject": col,
                        "marks": val_str,
                        "max_marks": max_m_str,
                        "grade": grade_str,
                    })
    else:
        # Auto-detect subject columns from row_data
        excluded_keywords = [
            "name", "student", "roll", "enroll", "admission", "id", "dob",
            "birth", "total", "percent", "cgpa", "grade", "rank", "result",
            "status", "remark", "photo", "qr", "signature", "gender",
            "class", "section", "division", "session", "year"
        ]
        for k, v in row_data.items():
            k_clean = str(k).strip()
            k_low = k_clean.lower()
            if any(kw in k_low for kw in excluded_keywords):
                continue
            if v is not None:
                v_str = str(v).strip()
                if v_str and v_str.lower() not in ("nan", "none", "<na>", "-", "absent"):
                    try:
                        clean_num = re.sub(r'[^\d.]', '', v_str)
                        if clean_num:
                            float(clean_num)
                            grade_str = ""
                            if show_grade:
                                grade_str, _ = calculate_grade(v_str, max_score=max_marks)
                            max_m_str = f"{int(max_marks) if max_marks.is_integer() else max_marks}" if show_max_marks else ""
                            subjects.append({
                                "subject": k_clean,
                                "marks": v_str,
                                "max_marks": max_m_str,
                                "grade": grade_str,
                            })
                    except (ValueError, TypeError):
                        pass

    return subjects


def _calculate_table_metrics(
    table_spec: dict[str, Any],
    subjects: list[dict[str, Any]],
    scale_x: float,
    scale_y: float,
) -> tuple[float, float, float, float, float, float, float]:
    """
    Computes table bounding rectangle (x0, y0, w, total_h), header_h, row_h, and delta_h.
    """
    x0 = max(0.0, float(table_spec.get("x", 0.0)) * scale_x)
    y0 = max(0.0, float(table_spec.get("y", 0.0)) * scale_y)
    w  = max(100.0, float(table_spec.get("width", 400.0)) * scale_x)
    initial_h = max(40.0, float(table_spec.get("height", 140.0)) * scale_y)

    row_h = max(12.0, float(table_spec.get("row_height", 22.0)) * scale_y)
    header_h = max(18.0 * scale_y, row_h * 1.1)

    row_count = max(1, len(subjects))
    total_h = header_h + (row_count * row_h)
    delta_h = max(0.0, total_h - initial_h)

    return x0, y0, w, total_h, header_h, row_h, delta_h


def _render_dynamic_subject_table(
    page: pymupdf.Page,
    table_spec: dict[str, Any],
    subjects: list[dict[str, Any]],
    scale_x: float,
    scale_y: float,
    y_offset: float = 0.0,
) -> float:
    """
    Renders the Dynamic Subject Table directly using PyMuPDF vector drawing primitives
    (draw_rect, insert_text).
    """
    x0, y0, w, total_h, header_h, row_h, _ = _calculate_table_metrics(
        table_spec, subjects, scale_x, scale_y
    )
    y0 += y_offset

    show_max = bool(table_spec.get("show_max_marks", True))
    show_grade = bool(table_spec.get("show_grade", True))
    font_size = max(5.0, float(table_spec.get("font_size", 9)) * min(scale_x, scale_y))

    header_bg = _hex_to_rgb_float(table_spec.get("header_bg", "#1e3a8a"))
    header_fg = _hex_to_rgb_float(table_spec.get("header_color", "#ffffff"))
    alt_row_bg = _hex_to_rgb_float(table_spec.get("alt_row_bg", "#f8fafc"))
    border_color = _hex_to_rgb_float(table_spec.get("border_color", "#cbd5e1"))
    text_color = (0.15, 0.2, 0.25)

    col_titles = ["Subject", "Marks Obtained"]
    col_keys = ["subject", "marks"]
    col_shares = [0.55, 0.45]

    if show_max and show_grade:
        col_titles = ["Subject", "Marks Obtained", "Max Marks", "Grade"]
        col_keys = ["subject", "marks", "max_marks", "grade"]
        col_shares = [0.42, 0.20, 0.18, 0.20]
    elif show_max:
        col_titles = ["Subject", "Marks Obtained", "Max Marks"]
        col_keys = ["subject", "marks", "max_marks"]
        col_shares = [0.50, 0.25, 0.25]
    elif show_grade:
        col_titles = ["Subject", "Marks Obtained", "Grade"]
        col_keys = ["subject", "marks", "grade"]
        col_shares = [0.50, 0.25, 0.25]

    # 1. Draw Header
    curr_x = x0
    for i, (title, share) in enumerate(zip(col_titles, col_shares)):
        col_w = w * share if i < len(col_titles) - 1 else (x0 + w - curr_x)
        cell_rect = pymupdf.Rect(curr_x, y0, curr_x + col_w, y0 + header_h)

        page.draw_rect(cell_rect, color=border_color, fill=header_bg, width=0.75)

        text_x = curr_x + 6.0 if i == 0 else max(curr_x + 2.0, curr_x + col_w / 2.0 - len(title) * font_size * 0.28)
        text_pt = pymupdf.Point(text_x, y0 + header_h * 0.68)
        page.insert_text(
            text_pt,
            title,
            fontsize=font_size,
            fontname="helv",
            color=header_fg,
        )
        curr_x += col_w

    # 2. Draw Subject Rows
    curr_y = y0 + header_h

    if not subjects:
        empty_rect = pymupdf.Rect(x0, curr_y, x0 + w, curr_y + row_h)
        page.draw_rect(empty_rect, color=border_color, fill=(1.0, 1.0, 1.0), width=0.5)
        page.insert_text(
            pymupdf.Point(x0 + 10.0, curr_y + row_h * 0.65),
            "No subjects recorded",
            fontsize=font_size,
            fontname="helv",
            color=(0.5, 0.5, 0.5),
        )
        return header_h + row_h

    for r_idx, subj in enumerate(subjects):
        row_fill = alt_row_bg if (r_idx % 2 == 1) else (1.0, 1.0, 1.0)
        curr_x = x0

        for c_idx, (k, share) in enumerate(zip(col_keys, col_shares)):
            col_w = w * share if c_idx < len(col_shares) - 1 else (x0 + w - curr_x)
            cell_rect = pymupdf.Rect(curr_x, curr_y, curr_x + col_w, curr_y + row_h)

            page.draw_rect(cell_rect, color=border_color, fill=row_fill, width=0.5)

            val = str(subj.get(k, "") or "")
            if c_idx == 0:
                text_pt = pymupdf.Point(curr_x + 6.0, curr_y + row_h * 0.65)
            else:
                text_len_approx = len(val) * font_size * 0.28
                text_pt = pymupdf.Point(max(curr_x + 2.0, curr_x + col_w / 2.0 - text_len_approx), curr_y + row_h * 0.65)

            page.insert_text(
                text_pt,
                val,
                fontsize=font_size,
                fontname="helv",
                color=text_color,
            )
            curr_x += col_w

        curr_y += row_h

    return total_h


# ── Single PDF Generator ─────────────────────────────────────────────────────

def generate_single_pdf(
    template_state: dict[str, Any],
    row_data: dict[str, str],
    output_path: str,
    photo_dir: str = "",
) -> None:
    """
    Renders one single student record onto the template background
    and saves the resulting flattened PDF.
    """
    num_pages = int(template_state.get("num_pages", 1))
    bg_info = template_state.get("background", {})
    bg_path = bg_info.get("path", "")
    bg_type = bg_info.get("type", "image")

    bg2_info = template_state.get("background_page2", {})
    bg2_path = bg2_info.get("path", "")
    bg2_type = bg2_info.get("type", "image")

    backgrounds = template_state.get("backgrounds", [])
    if len(backgrounds) > 1 and not bg2_path:
        bg2_path = backgrounds[1].get("path", "")
        bg2_type = backgrounds[1].get("type", "image")

    has_page_2 = any(
        int(item.get("page", 1)) == 2
        for cat in ("fields", "charts", "badges", "photos", "qr_codes", "tables")
        for item in template_state.get(cat, [])
    )

    is_multi_page_pdf = False
    if bg_path and os.path.exists(bg_path) and bg_type == "pdf":
        try:
            chk = pymupdf.open(bg_path)
            if chk.page_count >= 2:
                is_multi_page_pdf = True
                num_pages = max(num_pages, 2)
            chk.close()
        except Exception:
            pass

    if has_page_2 or (bg2_path and os.path.exists(bg2_path)):
        num_pages = max(num_pages, 2)

    canvas_w = float(template_state.get("canvas_width", 794.0))
    canvas_h = float(template_state.get("canvas_height", 1123.0))

    template_id = template_state.get("template_id", str(uuid.uuid4()))

    doc = pymupdf.open()

    # --- Page 1 (Front) ---
    if bg_path and os.path.exists(bg_path):
        if bg_type == "pdf":
            src_doc = pymupdf.open(bg_path)
            try:
                doc.insert_pdf(src_doc, from_page=0, to_page=0)
            finally:
                src_doc.close()
        else:
            page1 = doc.new_page(width=canvas_w, height=canvas_h)
            page1.insert_image(pymupdf.Rect(0, 0, canvas_w, canvas_h), filename=bg_path)
    else:
        doc.new_page(width=canvas_w, height=canvas_h)

    # --- Page 2 (Back) ---
    if num_pages >= 2:
        if is_multi_page_pdf:
            src_doc = pymupdf.open(bg_path)
            try:
                doc.insert_pdf(src_doc, from_page=1, to_page=1)
            finally:
                src_doc.close()
        elif bg2_path and os.path.exists(bg2_path):
            if bg2_type == "pdf":
                src_doc2 = pymupdf.open(bg2_path)
                try:
                    p_idx2 = int(bg2_info.get("page_index", 0))
                    p_idx2 = min(p_idx2, src_doc2.page_count - 1)
                    doc.insert_pdf(src_doc2, from_page=p_idx2, to_page=p_idx2)
                finally:
                    src_doc2.close()
            else:
                page2 = doc.new_page(width=canvas_w, height=canvas_h)
                page2.insert_image(pymupdf.Rect(0, 0, canvas_w, canvas_h), filename=bg2_path)
        else:
            doc.new_page(width=canvas_w, height=canvas_h)

    def _resolve_item_page(item_spec: dict[str, Any]) -> tuple[pymupdf.Page, float, float, int]:
        target_p = int(item_spec.get("page", 1))
        page_idx = min(max(0, target_p - 1), doc.page_count - 1)
        target_pg = doc[page_idx]
        sx = target_pg.rect.width / max(1.0, canvas_w)
        sy = target_pg.rect.height / max(1.0, canvas_h)
        return target_pg, sx, sy, page_idx

    # ── Compute Dynamic Subject Table metrics & push-down offsets ────────────
    tables = template_state.get("tables", [])
    table_render_data: list[tuple[int, float, float, float, list[dict[str, Any]]]] = []

    for t_spec in tables:
        subjs = _extract_student_subjects(t_spec, row_data)
        _, t_sx, t_sy, t_page_idx = _resolve_item_page(t_spec)
        tx0, ty0, tw, t_tot_h, t_head_h, t_row_h, t_delta_h = _calculate_table_metrics(
            t_spec, subjs, t_sx, t_sy
        )
        t_init_h = max(40.0, float(t_spec.get("height", 140.0)) * t_sy)
        table_render_data.append((t_page_idx, ty0, t_init_h, t_delta_h, subjs))

    def _get_table_push_down(elem_y: float, elem_page_idx: int) -> float:
        """Calculate downward shift for any element positioned below expanding tables on the same page."""
        total_shift = 0.0
        for (t_p_idx, t_y0, t_init_h, d_h, _) in table_render_data:
            if t_p_idx == elem_page_idx and elem_y >= (t_y0 + t_init_h - 5.0):
                total_shift += d_h
        return total_shift

    # Stamp fields
    fields = template_state.get("fields", [])
    for f in fields:
        col_key = f.get("mapped_column") or f.get("label", "")
        text_val = _extract_field_value(f, row_data)
        page, scale_x, scale_y, page_idx = _resolve_item_page(f)
        page_rect = page.rect

        # Coordinates mapped to PDF points with top-edge protection
        x0 = max(0.0, float(f.get("x", 0.0)) * scale_x)
        y0 = max(0.0, float(f.get("y", 0.0)) * scale_y)
        w  = max(10.0, float(f.get("width", 100.0)) * scale_x)
        h  = max(10.0, float(f.get("height", 30.0)) * scale_y)

        # Apply dynamic table expansion offset if below an expanding table on the same page
        y0 = min(y0 + _get_table_push_down(y0, page_idx), max(0.0, page_rect.height - h - 5.0))
        x0 = min(x0, max(0.0, page_rect.width - 5.0))

        # Ensure field is within bounds and not clipped off top/left
        x0 = min(x0, max(0.0, page_rect.width - 5.0))
        y0 = min(y0, max(0.0, page_rect.height - 5.0))

        font_size = max(4.0, float(f.get("font_size", 12)) * min(scale_x, scale_y))
        color = _hex_to_rgb_float(f.get("color", "#000000"))

        # Console Debugging: Right before the PyMuPDF insert loop
        print(f"[DEBUG PDF] Field: '{col_key}' (P{page_idx+1}) | Pos: ({x0:.1f}, {y0:.1f}) | Dim: ({w:.1f}, {h:.1f}) | Value: '{text_val}'")

        if not text_val:
            continue

        align_str = f.get("alignment", "Left")
        align_code = 0  # Left
        if align_str == "Center":
            align_code = 1
        elif align_str == "Right":
            align_code = 2

        font_family_lower = str(f.get("font_family", "")).lower()
        if "times" in font_family_lower or "serif" in font_family_lower:
            font_base = "ti"
        elif "courier" in font_family_lower or "mono" in font_family_lower:
            font_base = "co"
        else:
            font_base = "he"

        bold = f.get("bold", False)
        italic = f.get("italic", False)
        if font_base == "ti":
            font_name = "tibi" if (bold and italic) else ("tibo" if bold else ("tiit" if italic else "tiro"))
        elif font_base == "co":
            font_name = "cobi" if (bold and italic) else ("cobo" if bold else ("coit" if italic else "cour"))
        else:
            font_name = "hebi" if (bold and italic) else ("hebo" if bold else ("heit" if italic else "helv"))

        # Vertical alignment calculation & auto-shrink font fitting
        v_align = f.get("v_alignment", "Top")
        is_multiline = f.get("multiline", False)
        y_box_top = y0

        if not is_multiline:
            # Single-line auto-shrink: step down by 0.5pt increments until it fits bounding box width
            font_size = fit_single_line_font_size(
                text_val, font_name, font_size, w, min_size=4.0, step=0.5, padding=2.0
            )
            line_h = font_size * 1.15
            if v_align == "Middle":
                y_box_top = y0 + max(0.0, (h - line_h) / 2.0)
            elif v_align == "Bottom":
                y_box_top = y0 + max(0.0, h - line_h)
            effective_h = max(h - (y_box_top - y0), font_size * 1.5)
            box_rect = pymupdf.Rect(x0, y_box_top, x0 + w, y_box_top + effective_h)

            rc = page.insert_textbox(
                box_rect,
                text_val,
                fontsize=font_size,
                fontname=font_name,
                color=color,
                align=align_code,
            )

            # Fallback if text still overflowed the box (rc < 0): ensure it renders on the page
            if rc < 0:
                # Direct single-line text insertion fallback
                if align_code == 1:
                    tlen = pymupdf.get_text_length(text_val, fontname=font_name, fontsize=font_size)
                    pt_x = max(0.0, x0 + (w - tlen) / 2.0)
                elif align_code == 2:
                    tlen = pymupdf.get_text_length(text_val, fontname=font_name, fontsize=font_size)
                    pt_x = max(0.0, x0 + w - tlen)
                else:
                    pt_x = x0
                page.insert_text(
                    pymupdf.Point(pt_x, y_box_top + font_size * 0.85),
                    text_val,
                    fontsize=font_size,
                    fontname=font_name,
                    color=color,
                )
        else:
            effective_h = h
            box_rect = pymupdf.Rect(x0, y_box_top, x0 + w, y_box_top + effective_h)
            cur_sz = font_size
            rc = page.insert_textbox(
                box_rect,
                text_val,
                fontsize=cur_sz,
                fontname=font_name,
                color=color,
                align=align_code,
            )
            # Step down font size by 0.5pt increments until text fits inside bounding box
            while rc < 0 and cur_sz > 4.0:
                cur_sz = max(4.0, round(cur_sz - 0.5, 2))
                rc = page.insert_textbox(
                    box_rect,
                    text_val,
                    fontsize=cur_sz,
                    fontname=font_name,
                    color=color,
                    align=align_code,
                )
            if rc < 0:
                # Emergency fallback with min font size (4.0) with expanded boundary guard
                alt_rect = pymupdf.Rect(x0, y0, x0 + w, y0 + max(h, 4.0 * 2))
                page.insert_textbox(
                    alt_rect,
                    text_val,
                    fontsize=4.0,
                    fontname=font_name,
                    color=color,
                    align=align_code,
                )

    # ── Render chart placeholders ─────────────────────────────────────────────
    charts = template_state.get("charts", [])
    for chart_spec in charts:
        col_key     = chart_spec.get("label", "Performance Chart")
        page, scale_x, scale_y, page_idx = _resolve_item_page(chart_spec)
        page_rect   = page.rect
        cx0         = max(0.0, float(chart_spec.get("x",      0.0)) * scale_x)
        cy0         = max(0.0, float(chart_spec.get("y",      0.0)) * scale_y)
        cw          = max(10.0, float(chart_spec.get("width",  300.0)) * scale_x)
        ch          = max(10.0, float(chart_spec.get("height", 200.0)) * scale_y)

        cy0 = min(cy0 + _get_table_push_down(cy0, page_idx), max(0.0, page_rect.height - ch - 5.0))
        cx0 = min(cx0, max(0.0, page_rect.width - 5.0))
        chart_rect = pymupdf.Rect(cx0, cy0, cx0 + cw, cy0 + ch)

        print(
            f"[DEBUG CHART] '{col_key}' (P{page_idx+1}) | Pos: ({cx0:.1f}, {cy0:.1f}) "
            f"| Dim: ({cw:.1f}×{ch:.1f}) | Cols: {chart_spec.get('chart_columns', [])}"
        )

        try:
            png_bytes = _render_chart_to_image(chart_spec, row_data, int(cw), int(ch))
            if png_bytes:
                page.insert_image(chart_rect, stream=png_bytes)
        except Exception as chart_err:
            print(f"[DEBUG CHART] Render error for '{col_key}': {chart_err}")

    # ── Render conditional image badges ───────────────────────────────────────
    badges = template_state.get("badges", [])
    for badge_spec in badges:
        label      = badge_spec.get("label", "Badge")
        badge_path = badge_spec.get("badge_image_path", "")
        rule_col   = badge_spec.get("rule_column", "")
        rule_op    = badge_spec.get("rule_operator", ">=")
        rule_val   = badge_spec.get("rule_value", "0")

        page, scale_x, scale_y, page_idx = _resolve_item_page(badge_spec)
        page_rect  = page.rect
        bx0 = max(0.0, float(badge_spec.get("x",      0.0)) * scale_x)
        by0 = max(0.0, float(badge_spec.get("y",      0.0)) * scale_y)
        bw  = max(10.0, float(badge_spec.get("width",  100.0)) * scale_x)
        bh  = max(10.0, float(badge_spec.get("height", 100.0)) * scale_y)

        by0 = min(by0 + _get_table_push_down(by0, page_idx), max(0.0, page_rect.height - bh - 5.0))
        bx0 = min(bx0, max(0.0, page_rect.width - 5.0))
        badge_rect = pymupdf.Rect(bx0, by0, bx0 + bw, by0 + bh)

        is_match = _evaluate_badge_rule(rule_col, rule_op, rule_val, row_data)
        print(
            f"[DEBUG BADGE] '{label}' (P{page_idx+1}) | Rule: '{rule_col}' {rule_op} '{rule_val}' "
            f"| Match: {is_match} | Pos: ({bx0:.1f}, {by0:.1f}) | File: '{badge_path}'"
        )

        if is_match:
            if badge_path and os.path.exists(badge_path):
                try:
                    page.insert_image(badge_rect, filename=badge_path)
                except Exception as badge_err:
                    print(f"[DEBUG BADGE] Insert error for '{label}': {badge_err}")
            else:
                print(f"[DEBUG BADGE] Image not found or path empty: '{badge_path}'")

    # ── Render student photos ─────────────────────────────────────────────────
    photos = template_state.get("photos", [])
    if photos:
        effective_photo_dir = photo_dir or template_state.get("photo_dir", "")
        if not effective_photo_dir:
            try:
                from PyQt6.QtCore import QSettings
                effective_photo_dir = str(QSettings("TeacherResultSoftware", "ResultGenerator").value("photo_dir", "") or "")
            except Exception:
                effective_photo_dir = ""

        for photo_spec in photos:
            label = photo_spec.get("label", "Student Photo")
            id_col = photo_spec.get("photo_id_column", "").strip()
            id_val = ""

            if id_col:
                id_val = _extract_field_value({"mapped_column": id_col, "label": id_col}, row_data)
            else:
                # Auto-lookup in common ID columns
                for cand in ["Enrollment number", "Enrollment", "Roll No", "ID", "Student ID", "Admission No"]:
                    matched = find_matching_header(cand, list(row_data.keys()))
                    if matched and matched in row_data:
                        id_val = str(row_data[matched] or "").strip()
                        if id_val and id_val.lower() not in ("nan", "none", "<na>"):
                            break

            page, scale_x, scale_y, page_idx = _resolve_item_page(photo_spec)
            page_rect = page.rect
            px0 = max(0.0, float(photo_spec.get("x", 0.0)) * scale_x)
            py0 = max(0.0, float(photo_spec.get("y", 0.0)) * scale_y)
            pw  = max(10.0, float(photo_spec.get("width", 90.0)) * scale_x)
            ph  = max(10.0, float(photo_spec.get("height", 110.0)) * scale_y)

            py0 = min(py0 + _get_table_push_down(py0, page_idx), max(0.0, page_rect.height - ph - 5.0))
            px0 = min(px0, max(0.0, page_rect.width - 5.0))

            photo_rect = pymupdf.Rect(px0, py0, px0 + pw, py0 + ph)
            photo_file = find_student_photo_path(effective_photo_dir, id_val)

            border_w = max(0.0, float(photo_spec.get("border_width", 1.0)))
            border_c = _hex_to_rgb_float(photo_spec.get("border_color", "#6b7280"))

            print(
                f"[DEBUG PHOTO] '{label}' (P{page_idx+1}) | ID: '{id_val}' | File: '{photo_file}' "
                f"| Pos: ({px0:.1f}, {py0:.1f}) | Dim: ({pw:.1f}×{ph:.1f})"
            )

            if photo_file and os.path.exists(photo_file):
                try:
                    page.insert_image(photo_rect, filename=photo_file, keep_proportion=True)
                    if border_w > 0:
                        try:
                            page.draw_rect(photo_rect, color=border_c, width=border_w)
                        except Exception:
                            pass
                except Exception as p_err:
                    print(f"[DEBUG PHOTO] Insert error for '{label}' (File: {photo_file}): {p_err}")
            else:
                # Graceful missing photo handling: Draw a clean subtle neutral placeholder box
                try:
                    page.draw_rect(
                        photo_rect,
                        color=border_c if border_w > 0 else (0.8, 0.8, 0.8),
                        fill=(0.95, 0.95, 0.96),
                        width=max(1.0, border_w),
                    )
                    page.insert_text(
                        pymupdf.Point(px0 + pw * 0.15, py0 + ph * 0.55),
                        "No Photo",
                        fontsize=max(6.0, min(pw, ph) * 0.12),
                        fontname="helv",
                        color=(0.6, 0.6, 0.6),
                    )
                except Exception as p_err:
                    print(f"[DEBUG PHOTO] Placeholder drawing error for '{label}': {p_err}")

    # ── Render QR codes ───────────────────────────────────────────────────────
    qrs = template_state.get("qr_codes") or template_state.get("qrs") or []
    for qr_spec in qrs:
        label = qr_spec.get("label", "QR Code")
        payload_template = qr_spec.get("qr_payload_template") or qr_spec.get("qr_payload", "")
        border_cells = int(qr_spec.get("border_cells", 1))

        page, scale_x, scale_y, page_idx = _resolve_item_page(qr_spec)
        page_rect = page.rect
        qx0 = max(0.0, float(qr_spec.get("x", 0.0)) * scale_x)
        qy0 = max(0.0, float(qr_spec.get("y", 0.0)) * scale_y)
        qw  = max(10.0, float(qr_spec.get("width", 80.0)) * scale_x)
        qh  = max(10.0, float(qr_spec.get("height", 80.0)) * scale_y)

        qy0 = min(qy0 + _get_table_push_down(qy0, page_idx), max(0.0, page_rect.height - qh - 5.0))
        qx0 = min(qx0, max(0.0, page_rect.width - 5.0))

        qr_rect = pymupdf.Rect(qx0, qy0, qx0 + qw, qy0 + qh)
        interpolated_payload = _interpolate_qr_payload(payload_template, row_data)

        print(
            f"[DEBUG QR] '{label}' (P{page_idx+1}) | Payload: '{interpolated_payload}' "
            f"| Pos: ({qx0:.1f}, {qy0:.1f}) | Dim: ({qw:.1f}×{qh:.1f})"
        )

        if interpolated_payload and _QRCODE_AVAILABLE:
            try:
                png_bytes = _generate_qr_png_bytes(interpolated_payload, box_size=10, border=border_cells)
                page.insert_image(qr_rect, stream=png_bytes, keep_proportion=True)
            except Exception as qr_err:
                print(f"[DEBUG QR] Error generating/inserting QR code '{label}': {qr_err}")
        else:
            if not _QRCODE_AVAILABLE:
                print(f"[DEBUG QR] Cannot render '{label}': qrcode library not available")
            elif not interpolated_payload:
                print(f"[DEBUG QR] Empty payload for '{label}', skipping")

    # ── Render Dynamic Variable-Row Subject Tables ────────────────────────────
    for idx, t_spec in enumerate(tables):
        page, scale_x, scale_y, page_idx = _resolve_item_page(t_spec)
        if idx < len(table_render_data):
            _, ty0, _, _, subjs = table_render_data[idx]
        else:
            subjs = _extract_student_subjects(t_spec, row_data)
            ty0 = max(0.0, float(t_spec.get("y", 0.0)) * scale_y)

        t_shift = _get_table_push_down(ty0, page_idx)
        _render_dynamic_subject_table(page, t_spec, subjs, scale_x, scale_y, y_offset=t_shift)

    # Stamp internal template identity in metadata
    doc.set_metadata({
        "keywords": f"TeacherResultSoftware:{template_id}",
        "producer": "TeacherResultSoftware Desktop Engine",
    })

    try:
        doc.save(output_path, garbage=4, deflate=True)
    except PermissionError as exc:
        doc.close()
        raise PermissionError(
            f"Could not write PDF '{output_path}'. "
            "The file may be open in another application or the destination is not writable."
        ) from exc
    except Exception:
        doc.close()
        raise
    else:
        doc.close()


# ── Smart Class-Wise Print Bundling ──────────────────────────────────────────

def create_class_print_bundles(
    output_dir: str,
    student_mappings: list[tuple[dict[str, str], str]],
    group_col: str,
    errors: list[dict[str, Any]] | None = None,
) -> list[str]:
    """
    Groups generated individual student PDFs by class/section and merges them
    into master class-wise print bundles saved in output_dir/Print_Bundles.

    Returns a list of created master print bundle file paths.
    """
    if not student_mappings or not group_col:
        return []

    bundle_dir = os.path.join(output_dir, "Print_Bundles")
    os.makedirs(bundle_dir, exist_ok=True)

    # Group student PDF paths by class value
    groups: dict[str, list[str]] = {}
    for row, pdf_path in student_mappings:
        raw_group = str(row.get(group_col, "") or "").strip()
        class_key = raw_group if raw_group else "Unassigned"
        if class_key not in groups:
            groups[class_key] = []
        if os.path.exists(pdf_path):
            groups[class_key].append(pdf_path)

    created_bundles: list[str] = []
    for class_name, pdf_files in groups.items():
        if not pdf_files:
            continue

        master_doc = pymupdf.open()
        try:
            for pdf_path in pdf_files:
                student_doc = None
                try:
                    student_doc = pymupdf.open(pdf_path)
                    master_doc.insert_pdf(student_doc)
                except Exception as merge_err:
                    print(f"[DEBUG BUNDLE] Failed to merge {pdf_path} into {class_name}: {merge_err}")
                finally:
                    if student_doc is not None:
                        student_doc.close()

            if master_doc.page_count > 0:
                safe_class = sanitize_filename_part(class_name)
                bundle_filename = f"Class_{safe_class}_Master_Print.pdf"
                bundle_path = os.path.join(bundle_dir, bundle_filename)
                try:
                    master_doc.save(bundle_path, garbage=4, deflate=True)
                except PermissionError as exc:
                    error_message = (
                        f"Could not write class print bundle '{bundle_path}'. "
                        "The file may be open in another application or the destination is not writable."
                    )
                    if errors is not None:
                        errors.append({
                            "student_name": class_name,
                            "unique_val": "",
                            "error": error_message,
                            "row_data": {},
                            "row_index": -1,
                        })
                    if errors is None:
                        print(f"[DEBUG BUNDLE] {error_message}")
                else:
                    created_bundles.append(bundle_path)
                    print(f"[DEBUG BUNDLE] Created bundle: '{bundle_path}' ({master_doc.page_count} pages)")
        finally:
            master_doc.close()

    return created_bundles


# ── Automated ZIP Packaging ──────────────────────────────────────────────────

def package_output_to_zip(
    output_dir: str,
    zip_path: str = "",
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> str:
    """
    Compresses all generated files and subdirectories in output_dir into a single .zip archive.
    If zip_path is empty, creates [output_dir_name].zip alongside or within the output destination.
    Returns the absolute path to the created zip file.
    """
    if not os.path.exists(output_dir):
        raise FileNotFoundError(f"Output directory does not exist: {output_dir}")

    if not zip_path:
        base_name = os.path.basename(os.path.normpath(output_dir))
        parent_dir = os.path.dirname(os.path.normpath(output_dir))
        if base_name.lower() in ("desktop", "documents", "downloads", ""):
            ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
            zip_path = os.path.join(output_dir, f"Results_Archive_{ts}.zip")
        elif parent_dir and os.path.exists(parent_dir):
            zip_path = os.path.join(parent_dir, f"{base_name}.zip")
        else:
            zip_path = os.path.join(output_dir, f"{base_name}.zip")

    # Collect all files to compress
    all_files: list[tuple[str, str]] = []  # (abs_path, arcname)
    for root, _, files in os.walk(output_dir):
        for f in files:
            abs_p = os.path.join(root, f)
            # Avoid re-compressing the zip file if inside output_dir
            if os.path.abspath(abs_p) == os.path.abspath(zip_path):
                continue
            # Avoid recovery temporary files
            if f.startswith(".write_test_") or f.endswith(".recovery.json") or f.startswith("recovery_"):
                continue
            rel_p = os.path.relpath(abs_p, output_dir)
            all_files.append((abs_p, rel_p))

    total = len(all_files)
    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for i, (abs_p, rel_p) in enumerate(all_files, start=1):
                zf.write(abs_p, arcname=rel_p)
                if progress_callback:
                    progress_callback(i, total, os.path.basename(abs_p))
    except PermissionError as exc:
        raise PermissionError(
            f"Could not create ZIP archive '{zip_path}'. "
            "The file may be open in another application or the destination is not writable."
        ) from exc

    return zip_path



# ── Batch Audit & Execution Logging ──────────────────────────────────────────

def write_generation_audit_report(
    output_dir: str,
    template_name: str = "Result Template",
    template_id: str = "N/A",
    template_path: str = "N/A",
    dataset_name: str = "Dataset",
    total_processed: int = 0,
    succeeded_count: int = 0,
    skipped_count: int = 0,
    failed_count: int = 0,
    failed_records: list[dict[str, Any]] | None = None,
    skipped_records: list[dict[str, Any]] | list[tuple[int, str]] | None = None,
    elapsed_seconds: float = 0.0,
    start_time: datetime.datetime | None = None,
    end_time: datetime.datetime | None = None,
    created_bundles: list[str] | None = None,
    created_zip_path: str = "",
) -> str:
    """
    Generates a structured generation_report.txt in output_dir documenting:
    - Timestamps (Start & End)
    - Template details (Name, UUID, Path)
    - Dataset name / source
    - Total rows processed, succeeded, skipped, and failed
    - Detailed list of skipped/failed rows with reasons
    - Elapsed processing time in seconds
    - Print bundles & ZIP archive info (if applicable)

    Returns the absolute path to generation_report.txt.
    """
    os.makedirs(output_dir, exist_ok=True)
    report_file = os.path.join(output_dir, "generation_report.txt")

    if start_time is None:
        start_time = datetime.datetime.now()
    if end_time is None:
        end_time = datetime.datetime.now()

    start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

    success_pct = (succeeded_count / total_processed * 100.0) if total_processed > 0 else 0.0

    lines: list[str] = [
        "=" * 80,
        "BATCH RESULT GENERATION AUDIT REPORT",
        "=" * 80,
        f"Generated        : {end_str}",
        f"Execution Time   : {elapsed_seconds:.2f} seconds",
        f"Session Window   : {start_str}  -->  {end_str}",
        "",
        "-" * 80,
        "1. TEMPLATE CONFIGURATION",
        "-" * 80,
        f"Template Name    : {template_name or 'Result Template'}",
        f"Template UUID    : {template_id or 'N/A'}",
        f"Template Path    : {template_path or 'N/A'}",
        "",
        "-" * 80,
        "2. DATASET & DESTINATION",
        "-" * 80,
        f"Dataset Source   : {dataset_name or 'Student Dataset'}",
        f"Output Folder    : {output_dir}",
        "",
        "-" * 80,
        "3. EXECUTION SUMMARY",
        "-" * 80,
        f"Total Records    : {total_processed}",
        f"PDFs Succeeded   : {succeeded_count}",
        f"Skipped Records  : {skipped_count}",
        f"Failed Records   : {failed_count}",
        f"Success Rate     : {success_pct:.1f}%",
        "",
        "-" * 80,
        "4. PRINT BUNDLES & ARCHIVE",
        "-" * 80,
    ]

    if created_bundles:
        lines.append(f"Class Print Bundles : {len(created_bundles)} master bundles created:")
        for b in created_bundles:
            lines.append(f"  • {os.path.basename(b)} ({b})")
    else:
        lines.append("Class Print Bundles : None (disabled or not applicable)")

    if created_zip_path:
        lines.append(f"ZIP Archive         : {os.path.basename(created_zip_path)} ({created_zip_path})")
    else:
        lines.append("ZIP Archive         : None (disabled)")

    lines.extend([
        "",
        "-" * 80,
        "5. SKIPPED & FAILED RECORDS AUDIT LOG",
        "-" * 80,
    ])

    has_issues = False

    if skipped_records:
        has_issues = True
        lines.append("[SKIPPED RECORDS]")
        for item in skipped_records:
            if isinstance(item, dict):
                r_num = item.get("row_num", item.get("row_index", "?"))
                s_name = item.get("student_name", "Unknown")
                u_val = item.get("unique_val", "")
                reason = item.get("reason", item.get("error", "Skipped by user/validation"))
                lines.append(f"  • Row {r_num} [{u_val} - {s_name}]: {reason}")
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                lines.append(f"  • Row {item[0]}: {item[1]}")
            else:
                lines.append(f"  • {item}")
        lines.append("")

    if failed_records:
        has_issues = True
        lines.append("[FAILED RECORDS]")
        for rec in failed_records:
            if isinstance(rec, dict):
                r_idx = rec.get("row_index", -1)
                r_num = r_idx + 1 if r_idx >= 0 else rec.get("row_num", "?")
                s_name = rec.get("student_name", "Unknown")
                u_val = rec.get("unique_val", "")
                err = rec.get("error", "Unknown render error")
                lines.append(f"  • Row {r_num} [{u_val} - {s_name}]: {err}")
            else:
                lines.append(f"  • {rec}")
        lines.append("")

    if not has_issues:
        lines.append("Zero skipped or failed records. All records processed cleanly with 100% fidelity.")
        lines.append("")

    lines.extend([
        "=" * 80,
        "END OF REPORT",
        "=" * 80,
        "",
    ])

    report_content = "\n".join(lines)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    return report_file


# ── Generator Worker (QThread) ───────────────────────────────────────────────

class GeneratorWorker(QThread):
    """
    Multithreaded generation worker with interactive error pause,
    per-record retry limit (max 3), recovery state saving, and cancellation cleanup.
    """

    # Signals
    progress = pyqtSignal(int, int, int, str, str)  # current, total, percent, filename, status
    log_message = pyqtSignal(str)                   # worker log text for the UI
    record_succeeded = pyqtSignal(int, str)         # row_idx, file_path
    record_skipped = pyqtSignal(int, str)           # row_idx, reason
    error_occurred = pyqtSignal(int, str, dict, int) # row_idx, col_name, row_dict, retries_left
    generation_finished = pyqtSignal(int, int, int, str, list)  # gen, skip, fail, out_dir, failed_records
    generation_cancelled = pyqtSignal()

    ACTION_RETRY = 1
    ACTION_SKIP = 2
    ACTION_CANCEL = 3

    def __init__(
        self,
        template_state: dict[str, Any],
        rows: list[dict[str, str]],
        output_dir: str,
        unique_col: str,
        name_col: str,
        parent: QObject | None = None,
        operation_id: str | None = None,
        bundle_enabled: bool = False,
        bundle_col: str = "",
        filename_pattern: str = "",
        zip_package: bool = False,
        dataset_name: str = "",
        template_path: str = "",
        photo_dir: str = "",
    ) -> None:
        super().__init__(parent)
        self.template_state = template_state
        self.rows = rows
        self.output_dir = output_dir
        self.unique_col = unique_col
        self.name_col = name_col
        self.operation_id = operation_id or uuid.uuid4().hex[:12]
        self.bundle_enabled = bundle_enabled
        self.bundle_col = bundle_col
        self.filename_pattern = filename_pattern
        self.zip_package = zip_package
        self.dataset_name = dataset_name
        self.template_path = template_path
        self.photo_dir = photo_dir

        self._cancelled = False
        self._mutex = QMutex()
        self._wait_condition = QWaitCondition()
        self._error_action = self.ACTION_SKIP

        self.start_time: datetime.datetime | None = None
        self.end_time: datetime.datetime | None = None
        self.elapsed_seconds: float = 0.0
        self.skipped_records_log: list[dict[str, Any]] = []
        self.report_path: str = ""

        self.retry_counts: dict[int, int] = {}
        self.generated_files: list[str] = []
        self.successful_records: list[tuple[dict[str, str], str]] = []
        self.created_bundles: list[str] = []
        self.created_zip_path: str = ""
        self.failed_records: list[dict[str, Any]] = []

        self.recovery_file = os.path.join(
            RECOVERY_DIR, f"recovery_{self.operation_id}.json"
        )

    def cancel(self) -> None:
        """Signal thread to cancel and clean up."""
        self._mutex.lock()
        self._cancelled = True
        self._error_action = self.ACTION_CANCEL
        self._wait_condition.wakeAll()
        self._mutex.unlock()

    def resolve_error(self, action: int) -> None:
        """Called by UI to wake worker thread after user interaction."""
        self._mutex.lock()
        self._error_action = action
        self._wait_condition.wakeAll()
        self._mutex.unlock()

    def _save_recovery_state(self, current_idx: int, completed: int, skipped: int, failed: int) -> None:
        """Persist recovery state to disk."""
        state = {
            "operation_id": self.operation_id,
            "template_id": self.template_state.get("template_id", ""),
            "output_dir": self.output_dir,
            "current_index": current_idx,
            "completed_count": completed,
            "skipped_count": skipped,
            "failed_count": failed,
            "retry_counts": self.retry_counts,
            "generated_files": self.generated_files,
            "failed_records": self.failed_records,
        }
        try:
            with open(self.recovery_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

    def _log(self, message: str) -> None:
        """Emit worker diagnostics without writing to UI objects from this thread."""
        self.log_message.emit(message)

    def run(self) -> None:
        self.start_time = datetime.datetime.now()
        total = len(self.rows)
        generated_count = 0
        skipped_count = 0

        # Scan mapped columns to validate
        mapped_columns: list[str] = []
        for f in self.template_state.get("fields", []):
            c = f.get("mapped_column") or f.get("label", "")
            if c:
                mapped_columns.append(c)

        idx = 0
        while idx < total:
            if self._cancelled:
                self._cleanup_on_cancel()
                self.generation_cancelled.emit()
                return

            row = self.rows[idx]
            row_num = idx + 1
            retries_used = self.retry_counts.get(idx, 0)
            retries_left = max(0, 3 - retries_used)

            # Check for empty cells in mapped fields
            missing_col = ""
            for f in self.template_state.get("fields", []):
                val_str = _extract_field_value(f, row)
                if not val_str:
                    missing_col = f.get("mapped_column") or f.get("label", "Unknown")
                    break

            if missing_col:
                # Pause and notify UI
                self._mutex.lock()
                self.error_occurred.emit(row_num, missing_col, row, retries_left)
                self._wait_condition.wait(self._mutex)
                action = self._error_action
                self._mutex.unlock()

                if action == self.ACTION_CANCEL or self._cancelled:
                    self._cleanup_on_cancel()
                    self.generation_cancelled.emit()
                    return
                elif action == self.ACTION_SKIP:
                    skipped_count += 1
                    self.skipped_records_log.append({
                        "row_num": row_num,
                        "student_name": row.get(self.name_col, "Unknown"),
                        "unique_val": row.get(self.unique_col, f"Row {row_num}"),
                        "reason": f"Empty cell in '{missing_col}'",
                        "row_data": row,
                        "row_index": idx,
                    })
                    self.record_skipped.emit(row_num, f"Empty cell in '{missing_col}'")
                    idx += 1
                    continue
                elif action == self.ACTION_RETRY:
                    self.retry_counts[idx] = retries_used + 1
                    if self.retry_counts[idx] >= 3:
                        # Exceeded retry limit
                        self.failed_records.append({
                            "student_name": row.get(self.name_col, "Unknown"),
                            "unique_val": row.get(self.unique_col, f"Row {row_num}"),
                            "error": f"Missing value in '{missing_col}' (Max retries exceeded)",
                            "row_data": row,
                            "row_index": idx,
                        })
                        skipped_count += 1
                        idx += 1
                    continue

            # Construct safe filename
            if self.filename_pattern:
                out_file = get_unique_result_filename(
                    self.output_dir,
                    ext=".PDF",
                    pattern=self.filename_pattern,
                    row_data=row,
                    row_index=row_num,
                )
            else:
                u_val = row.get(self.unique_col, f"REC{row_num}")
                s_val = row.get(self.name_col, "")
                out_file = get_unique_result_filename(self.output_dir, u_val, s_val, ".PDF")
            filename_only = os.path.basename(out_file)

            # Update progress
            pct = int((generated_count / total) * 100) if total > 0 else 0
            self.progress.emit(
                row_num, total, pct, filename_only, f"Generating {row_num}/{total}..."
            )
            self._log(f"Generating row {row_num}/{total}: {filename_only}")

            try:
                generate_single_pdf(self.template_state, row, out_file, photo_dir=self.photo_dir)
                self.generated_files.append(out_file)
                self.successful_records.append((row, out_file))
                generated_count += 1
                self.record_succeeded.emit(row_num, out_file)
                self._log(f"Generated: {filename_only}")
                idx += 1
            except PermissionError as exc:
                error_message = str(exc)
                self.failed_records.append({
                    "student_name": row.get(self.name_col, "Unknown"),
                    "unique_val": row.get(self.unique_col, f"Row {row_num}"),
                    "error": error_message,
                    "row_data": row,
                    "row_index": idx,
                })
                skipped_count += 1
                self.record_skipped.emit(row_num, error_message)
                self._log(f"Skipped row {row_num}: {error_message}")
                idx += 1
            except Exception as exc:
                self._mutex.lock()
                self.error_occurred.emit(row_num, f"Render Error: {exc}", row, retries_left)
                self._wait_condition.wait(self._mutex)
                action = self._error_action
                self._mutex.unlock()

                if action == self.ACTION_CANCEL or self._cancelled:
                    self._cleanup_on_cancel()
                    self.generation_cancelled.emit()
                    return
                elif action == self.ACTION_SKIP:
                    skipped_count += 1
                    self.failed_records.append({
                        "student_name": row.get(self.name_col, "Unknown"),
                        "unique_val": row.get(self.unique_col, f"Row {row_num}"),
                        "error": str(exc),
                        "row_data": row,
                        "row_index": idx,
                    })
                    idx += 1
                elif action == self.ACTION_RETRY:
                    self.retry_counts[idx] = retries_used + 1
                    if self.retry_counts[idx] >= 3:
                        self.failed_records.append({
                            "student_name": row.get(self.name_col, "Unknown"),
                            "unique_val": row.get(self.unique_col, f"Row {row_num}"),
                            "error": f"{exc} (Max retries exceeded)",
                            "row_data": row,
                            "row_index": idx,
                        })
                        skipped_count += 1
                        idx += 1

            self._save_recovery_state(idx, generated_count, skipped_count, len(self.failed_records))

        # ── Post-Processing: Smart Class-Wise Print Bundling ──────────────────
        if self.bundle_enabled and self.bundle_col and self.successful_records and not self._cancelled:
            self.progress.emit(
                total, total, 97, "Print_Bundles", "Creating Class-Wise Print Bundles..."
            )
            try:
                self.created_bundles = create_class_print_bundles(
                    self.output_dir,
                    self.successful_records,
                    self.bundle_col,
                    errors=self.failed_records,
                )
            except Exception as bundle_err:
                print(f"[DEBUG BUNDLE] Bundling process error: {bundle_err}")

        # ── Post-Processing: Automated ZIP Packaging ────────────────────────
        if self.zip_package and self.generated_files and not self._cancelled:
            self.progress.emit(
                total, total, 98, "ZIP Packager", "Packaging output into ZIP archive..."
            )
            try:
                def _on_zip_prog(cur_f: int, tot_f: int, fn: str) -> None:
                    pct = 95 + int((cur_f / max(1, tot_f)) * 3)
                    self.progress.emit(
                        cur_f, tot_f, min(98, pct), fn, f"Archiving {cur_f}/{tot_f} files into ZIP..."
                    )

                self.created_zip_path = package_output_to_zip(
                    self.output_dir, progress_callback=_on_zip_prog
                )
                self._log(f"Created ZIP archive: {self.created_zip_path}")
            except PermissionError as zip_err:
                self.failed_records.append({
                    "student_name": "ZIP archive",
                    "unique_val": "",
                    "error": str(zip_err),
                    "row_data": {},
                    "row_index": -1,
                })
                self._log(f"ZIP archive failed: {zip_err}")
            except Exception as zip_err:
                self._log(f"ZIP packaging error: {zip_err}")

        # ── Post-Processing: Batch Audit & Execution Logging ────────────────
        self.end_time = datetime.datetime.now()
        self.elapsed_seconds = max(0.0, (self.end_time - self.start_time).total_seconds()) if self.start_time else 0.0
        template_name = self.template_state.get("template_name", "Result Template")
        template_id = self.template_state.get("template_id", "N/A")
        template_path = self.template_path or self.template_state.get("background", {}).get("path", "N/A")
        dataset_name = self.dataset_name or "Student Dataset"

        if not self._cancelled:
            self.progress.emit(
                total, total, 99, "Audit Log", "Writing generation audit report..."
            )
            try:
                self.report_path = write_generation_audit_report(
                    output_dir=self.output_dir,
                    template_name=template_name,
                    template_id=template_id,
                    template_path=template_path,
                    dataset_name=dataset_name,
                    total_processed=total,
                    succeeded_count=generated_count,
                    skipped_count=skipped_count,
                    failed_count=len(self.failed_records),
                    failed_records=self.failed_records,
                    skipped_records=self.skipped_records_log,
                    elapsed_seconds=self.elapsed_seconds,
                    start_time=self.start_time,
                    end_time=self.end_time,
                    created_bundles=self.created_bundles,
                    created_zip_path=self.created_zip_path,
                )
                self._log(f"Audit report written to: {self.report_path}")
            except Exception as rep_err:
                self._log(f"Failed to write audit report: {rep_err}")

        # Successful completion -> remove recovery file
        if os.path.exists(self.recovery_file):
            try:
                os.remove(self.recovery_file)
            except Exception:
                pass

        final_pct = 100 if generated_count == total else int((generated_count / total) * 100)
        self.progress.emit(
            total, total, final_pct, "Completed", "Generation Finished"
        )
        self.generation_finished.emit(
            generated_count,
            skipped_count,
            len(self.failed_records),
            self.output_dir,
            self.failed_records,
        )

    def _cleanup_on_cancel(self) -> None:
        """On confirmed cancellation, attempt to remove generated files for this session."""
        for path in self.generated_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
        if os.path.exists(self.recovery_file):
            try:
                os.remove(self.recovery_file)
            except Exception:
                pass
