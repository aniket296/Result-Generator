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

import io
import json
import math
import os
import re
import shutil
import uuid
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
    - Strip leading/trailing underscores, spaces, and periods
    """
    if not text:
        return "UNNAMED"

    # Replace invalid chars: \ / : * ? " < > | and non-printables
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', str(text))
    # Collapse multiple underscores/spaces
    cleaned = re.sub(r'[\s_]+', '_', cleaned)
    cleaned = cleaned.strip(" ._")

    return cleaned if cleaned else "UNNAMED"


def get_unique_result_filename(
    output_dir: str,
    unique_val: str,
    student_name: str,
    ext: str = ".PDF",
) -> str:
    """
    Constructs the exact uppercase filename: UNIQUEFIELD_STUDENTNAME.PDF
    with collision handling (_01, _02, ..., _100) and reserved name protection.
    """
    u = sanitize_filename_part(unique_val)
    s = sanitize_filename_part(student_name)[:40].strip(" ._")
    if not s:
        s = "UNNAMED"

    base_name = f"{u}_{s}".upper()

    # Reserved names check
    first_token = base_name.split("_")[0]
    if first_token in RESERVED_WINDOWS_NAMES:
        base_name = f"RESULT_{base_name}"

    ext = ext.upper() if ext.startswith(".") else f".{ext.upper()}"

    candidate_path = os.path.join(output_dir, f"{base_name}{ext}")
    if not os.path.exists(candidate_path):
        return candidate_path

    # Collision loop with formatted padding (_01, _02, ... _100)
    counter = 1
    while True:
        suffix = f"_{counter:02d}" if counter < 100 else f"_{counter}"
        candidate_path = os.path.join(output_dir, f"{base_name}{suffix}{ext}")
        if not os.path.exists(candidate_path):
            return candidate_path
        counter += 1


def preview_filenames(
    output_dir: str,
    rows: list[dict[str, str]],
    unique_col: str,
    name_col: str,
    ext: str = ".PDF",
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
        u = row.get(unique_col, f"REC{idx+1}")
        s = row.get(name_col, "")

        # Compute candidate
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
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", transparent=True)
    plt.close("all")
    buf.seek(0)
    return buf.getvalue()


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


# ── Single PDF Generator ─────────────────────────────────────────────────────

def generate_single_pdf(
    template_state: dict[str, Any],
    row_data: dict[str, str],
    output_path: str,
) -> None:
    """
    Renders one single student record onto the template background
    and saves the resulting flattened PDF.
    """
    bg_info = template_state.get("background", {})
    bg_path = bg_info.get("path", "")
    bg_type = bg_info.get("type", "image")

    canvas_w = float(template_state.get("canvas_width", 794.0))
    canvas_h = float(template_state.get("canvas_height", 1123.0))

    template_id = template_state.get("template_id", str(uuid.uuid4()))

    doc = pymupdf.open()

    if bg_path and os.path.exists(bg_path):
        if bg_type == "pdf":
            src_doc = pymupdf.open(bg_path)
            doc.insert_pdf(src_doc, from_page=0, to_page=0)
            src_doc.close()
            page = doc[0]
        else:
            # High-res image background
            page = doc.new_page(width=canvas_w, height=canvas_h)
            rect = pymupdf.Rect(0, 0, canvas_w, canvas_h)
            page.insert_image(rect, filename=bg_path)
    else:
        page = doc.new_page(width=canvas_w, height=canvas_h)

    page_rect = page.rect
    scale_x = page_rect.width / max(1.0, canvas_w)
    scale_y = page_rect.height / max(1.0, canvas_h)

    # Stamp fields
    fields = template_state.get("fields", [])
    for f in fields:
        col_key = f.get("mapped_column") or f.get("label", "")
        text_val = _extract_field_value(f, row_data)

        # Coordinates mapped to PDF points with top-edge protection
        x0 = max(0.0, float(f.get("x", 0.0)) * scale_x)
        y0 = max(0.0, float(f.get("y", 0.0)) * scale_y)
        w  = max(10.0, float(f.get("width", 100.0)) * scale_x)
        h  = max(10.0, float(f.get("height", 30.0)) * scale_y)

        # Ensure field is within bounds and not clipped off top/left
        x0 = min(x0, max(0.0, page_rect.width - 5.0))
        y0 = min(y0, max(0.0, page_rect.height - 5.0))

        font_size = max(4.0, float(f.get("font_size", 12)) * min(scale_x, scale_y))
        color = _hex_to_rgb_float(f.get("color", "#000000"))

        # Console Debugging: Right before the PyMuPDF insert loop
        print(f"[DEBUG PDF] Field: '{col_key}' | Pos: ({x0:.1f}, {y0:.1f}) | Dim: ({w:.1f}, {h:.1f}) | Value: '{text_val}'")

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

        # Vertical alignment calculation
        v_align = f.get("v_alignment", "Top")
        is_multiline = f.get("multiline", False)
        y_box_top = y0

        if not is_multiline:
            line_h = font_size * 1.15
            if v_align == "Middle":
                y_box_top = y0 + max(0.0, (h - line_h) / 2.0)
            elif v_align == "Bottom":
                y_box_top = y0 + max(0.0, h - line_h)
            effective_h = max(h - (y_box_top - y0), font_size * 1.5)
        else:
            effective_h = h

        box_rect = pymupdf.Rect(x0, y_box_top, x0 + w, y_box_top + effective_h)

        # Insert textbox with PyMuPDF
        rc = page.insert_textbox(
            box_rect,
            text_val,
            fontsize=font_size,
            fontname=font_name,
            color=color,
            align=align_code,
        )

        # Fallback if text overflowed the box (rc < 0): ensure it renders on the page
        if rc < 0:
            if not is_multiline:
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
                # Try with smaller font size until it fits
                for shrink in (0.85, 0.7, 0.55):
                    alt_rc = page.insert_textbox(
                        pymupdf.Rect(x0, y0, x0 + w, y0 + max(h, font_size * 2)),
                        text_val,
                        fontsize=font_size * shrink,
                        fontname=font_name,
                        color=color,
                        align=align_code,
                    )
                    if alt_rc >= 0:
                        break

    # ── Render chart placeholders ─────────────────────────────────────────────
    charts = template_state.get("charts", [])
    for chart_spec in charts:
        col_key     = chart_spec.get("label", "Performance Chart")
        cx0         = max(0.0, float(chart_spec.get("x",      0.0)) * scale_x)
        cy0         = max(0.0, float(chart_spec.get("y",      0.0)) * scale_y)
        cw          = max(10.0, float(chart_spec.get("width",  300.0)) * scale_x)
        ch          = max(10.0, float(chart_spec.get("height", 200.0)) * scale_y)

        chart_rect = pymupdf.Rect(cx0, cy0, cx0 + cw, cy0 + ch)

        print(
            f"[DEBUG CHART] '{col_key}' | Pos: ({cx0:.1f}, {cy0:.1f}) "
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

        bx0 = max(0.0, float(badge_spec.get("x",      0.0)) * scale_x)
        by0 = max(0.0, float(badge_spec.get("y",      0.0)) * scale_y)
        bw  = max(10.0, float(badge_spec.get("width",  100.0)) * scale_x)
        bh  = max(10.0, float(badge_spec.get("height", 100.0)) * scale_y)

        badge_rect = pymupdf.Rect(bx0, by0, bx0 + bw, by0 + bh)

        is_match = _evaluate_badge_rule(rule_col, rule_op, rule_val, row_data)
        print(
            f"[DEBUG BADGE] '{label}' | Rule: '{rule_col}' {rule_op} '{rule_val}' "
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

    # Stamp internal template identity in metadata
    doc.set_metadata({
        "keywords": f"TeacherResultSoftware:{template_id}",
        "producer": "TeacherResultSoftware Desktop Engine",
    })

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()


# ── Smart Class-Wise Print Bundling ──────────────────────────────────────────

def create_class_print_bundles(
    output_dir: str,
    student_mappings: list[tuple[dict[str, str], str]],
    group_col: str,
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
                try:
                    student_doc = pymupdf.open(pdf_path)
                    master_doc.insert_pdf(student_doc)
                    student_doc.close()
                except Exception as merge_err:
                    print(f"[DEBUG BUNDLE] Failed to merge {pdf_path} into {class_name}: {merge_err}")

            if master_doc.page_count > 0:
                safe_class = sanitize_filename_part(class_name)
                bundle_filename = f"Class_{safe_class}_Master_Print.pdf"
                bundle_path = os.path.join(bundle_dir, bundle_filename)
                master_doc.save(bundle_path, garbage=4, deflate=True)
                created_bundles.append(bundle_path)
                print(f"[DEBUG BUNDLE] Created bundle: '{bundle_path}' ({master_doc.page_count} pages)")
        finally:
            master_doc.close()

    return created_bundles


# ── Generator Worker (QThread) ───────────────────────────────────────────────

class GeneratorWorker(QThread):
    """
    Multithreaded generation worker with interactive error pause,
    per-record retry limit (max 3), recovery state saving, and cancellation cleanup.
    """

    # Signals
    progress = pyqtSignal(int, int, int, str, str)  # current, total, percent, filename, status
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

        self._cancelled = False
        self._mutex = QMutex()
        self._wait_condition = QWaitCondition()
        self._error_action = self.ACTION_SKIP

        self.retry_counts: dict[int, int] = {}
        self.generated_files: list[str] = []
        self.successful_records: list[tuple[dict[str, str], str]] = []
        self.created_bundles: list[str] = []
        self.failed_records: list[dict[str, Any]] = []

        self._cancelled = False
        self._mutex = QMutex()
        self._wait_condition = QWaitCondition()
        self._error_action = self.ACTION_SKIP

        self.retry_counts: dict[int, int] = {}
        self.generated_files: list[str] = []
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

    def run(self) -> None:
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
            u_val = row.get(self.unique_col, f"REC{row_num}")
            s_val = row.get(self.name_col, "")
            out_file = get_unique_result_filename(self.output_dir, u_val, s_val, ".PDF")
            filename_only = os.path.basename(out_file)

            # Update progress
            pct = int((generated_count / total) * 100) if total > 0 else 0
            self.progress.emit(
                row_num, total, pct, filename_only, f"Generating {row_num}/{total}..."
            )

            try:
                generate_single_pdf(self.template_state, row, out_file)
                self.generated_files.append(out_file)
                self.successful_records.append((row, out_file))
                generated_count += 1
                self.record_succeeded.emit(row_num, out_file)
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
                total, total, 99, "Print_Bundles", "Creating Class-Wise Print Bundles..."
            )
            try:
                self.created_bundles = create_class_print_bundles(
                    self.output_dir, self.successful_records, self.bundle_col
                )
            except Exception as bundle_err:
                print(f"[DEBUG BUNDLE] Bundling process error: {bundle_err}")

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
