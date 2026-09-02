"""
data_engine/excel_loader.py
Loads, validates, exports, and backs up Excel datasets.

Key guarantees:
- Strict string loading (no float conversion, no formula evaluation).
- Dual-layer file-locking detection.
- Empty cell validation (empty cells are critical errors).
- Unique field constraint enforcement.
- Export of blank Excel template matching template fields.
- External `.dataset.backup` creation and recovery.
"""
from __future__ import annotations

import json
import os
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
import pandas as pd

from data_engine.exceptions import (
    DuplicateUniqueValueError,
    EmptyCellError,
    FileLockedError,
)


def _check_file_locked(file_path: str) -> None:
    """Check if the Excel file is currently open / locked by another process."""
    if not os.path.exists(file_path):
        return

    dir_name = os.path.dirname(os.path.abspath(file_path))
    base_name = os.path.basename(file_path)
    shadow_lock = os.path.join(dir_name, f"~${base_name}")

    if os.path.exists(shadow_lock):
        raise FileLockedError(
            f"The file '{base_name}' is currently open in Microsoft Excel or another program.\n"
            "Please close the file and try again."
        )

    try:
        with open(file_path, "a+b"):
            pass
    except (PermissionError, IOError) as exc:
        raise FileLockedError(
            f"The file '{base_name}' is locked by another process (Permission Denied).\n"
            "Please close any application using it and try again."
        ) from exc


def load_excel(file_path: str) -> tuple[list[str], list[dict[str, str]]]:
    """
    Load an Excel (.xlsx / .xls) file.

    Returns:
        tuple[list[str], list[dict[str, str]]]:
            (column_headers, rows_as_string_dicts)
    """
    _check_file_locked(file_path)

    try:
        df = pd.read_excel(
            file_path,
            dtype=str,
            keep_default_na=False,
            engine="openpyxl",
        )
    except Exception as exc:
        if isinstance(exc, FileLockedError):
            raise
        raise IOError(f"Failed to read Excel file: {exc}") from exc

    headers: list[str] = [str(col).strip() for col in df.columns]
    df.columns = headers

    # Convert all cell values strictly to string
    records: list[dict[str, str]] = []
    for _, row in df.iterrows():
        records.append({str(k): ("" if pd.isna(v) else str(v).strip()) for k, v in row.items()})

    return headers, records


def validate_row(row_dict: dict[str, str], row_num: int) -> None:
    """Validate that a row contains no empty or whitespace-only cells."""
    for col, val in row_dict.items():
        if val is None or str(val).strip() == "":
            raise EmptyCellError(row_num, col)


def validate_all_rows(rows: list[dict[str, str]]) -> list[tuple[int, str]]:
    """Scan all rows for empty cells. Returns list of (row_num_1_indexed, column_name)."""
    errors: list[tuple[int, str]] = []
    for idx, row in enumerate(rows, start=1):
        for col, val in row.items():
            if val is None or str(val).strip() == "":
                errors.append((idx, col))
    return errors


def validate_unique_column(rows: list[dict[str, str]], col_name: str) -> None:
    """
    Verify that all values in the designated unique column are distinct.
    Raises DuplicateUniqueValueError if any duplicate value is found.
    """
    seen: set[str] = set()
    duplicates: list[str] = []

    for row in rows:
        val = row.get(col_name, "").strip()
        if not val:
            continue
        if val in seen:
            if val not in duplicates:
                duplicates.append(val)
        else:
            seen.add(val)

    if duplicates:
        raise DuplicateUniqueValueError(col_name, duplicates)


def export_blank_excel_template(file_path: str, column_headers: list[str]) -> None:
    """
    Export a clean blank Microsoft Excel (.xlsx) dataset template.
    Column headers match the visual template fields exactly.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Student Data"

    # Header styling
    header_fill = PatternFill(start_color="1A1A2E", end_color="1A1A2E", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.row_dimensions[1].height = 28

    for col_idx, header in enumerate(column_headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
        # Set generous default column width
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max(len(header) + 6, 18)

    wb.save(file_path)


def export_dataset_backup(
    backup_path: str,
    rows: list[dict[str, str]],
    headers: list[str],
    template_metadata: dict[str, Any] | None = None,
) -> None:
    """
    Export dataset and associated template state to a `.dataset.backup` file.
    """
    data = {
        "format_version": "1.0",
        "headers": headers,
        "records": rows,
        "record_count": len(rows),
        "template_metadata": template_metadata or {},
    }
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def import_dataset_backup(backup_path: str) -> tuple[list[str], list[dict[str, str]], dict[str, Any]]:
    """
    Import and restore from a `.dataset.backup` file.
    Returns (headers, rows, template_metadata).
    """
    with open(backup_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    headers = data.get("headers", [])
    records = data.get("records", [])
    meta = data.get("template_metadata", {})
    return headers, records, meta
