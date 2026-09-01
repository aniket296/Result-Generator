"""
Excel ingestion module.

Public API
----------
load_excel(filepath)        -> dict  (headers, rows, total_rows)
validate_row(row, index)    -> list[str]   (empty = valid)
validate_all_rows(rows)     -> dict  (is_valid, error_count, errors_by_row)

Architecture note
-----------------
This module is a pure data layer.  It NEVER calculates, derives, or modifies
cell values.  Every cell is stored as the exact string from Excel.
Empty cells are stored as "" so the caller can detect and surface them as
critical errors.
"""
from __future__ import annotations

import os

import pandas as pd

from .exceptions import FileLockedError

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _check_file_locked(filepath: str) -> None:
    """
    Raise FileLockedError if the file is locked by another process.

    Two independent checks are performed so that both Excel-style shadow
    locks and generic OS write-locks are caught:

    Check 1 – Shadow file
        Microsoft Excel creates a hidden companion file named
        "~$<original_filename>" in the same directory while the workbook
        is open.  If that file exists, the workbook is locked by Excel.

    Check 2 – Exclusive write-open
        Attempt to open the file in read-write binary mode.  If another
        process holds an exclusive write-lock, this raises PermissionError.
    """
    abs_path  = os.path.abspath(filepath)
    directory = os.path.dirname(abs_path)
    basename  = os.path.basename(abs_path)

    # --- Check 1: Excel shadow lock file ------------------------------------
    shadow = os.path.join(directory, f"~${basename}")
    if os.path.exists(shadow):
        raise FileLockedError(
            f"Microsoft Excel has this file open.\n\n"
            f"Lock file detected:\n{shadow}\n\n"
            f"Please close the workbook in Excel and try again."
        )

    # --- Check 2: OS-level write-lock --------------------------------------
    try:
        with open(abs_path, "r+b"):
            pass
    except PermissionError:
        raise FileLockedError(
            f"The file is locked by another program:\n{abs_path}\n\n"
            f"Please close any application currently using this file."
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_excel(filepath: str) -> dict:
    """
    Load an .xlsx/.xls file and return a structured result dict.

    Parameters
    ----------
    filepath : str
        Absolute or relative path to the workbook.

    Returns
    -------
    dict with keys:
        filepath    : str
        headers     : list[str]            – column names from row 1
        rows        : list[dict[str, str]] – one dict per data row;
                                             empty cells stored as ""
        total_rows  : int

    Raises
    ------
    FileLockedError
        File is open in another program.
    ValueError
        File has no columns or is completely empty.
    Any pandas / openpyxl exception
        Propagated as-is for the UI to surface.
    """
    _check_file_locked(filepath)

    df = pd.read_excel(
        filepath,
        engine="openpyxl",
        dtype=str,              # treat every cell as a raw string
        keep_default_na=False,  # empty cells -> "" not NaN
    )

    if df.columns.empty:
        raise ValueError(f"No columns found in file:\n{filepath}")

    # Strip any accidental leading/trailing whitespace from header names
    df.columns = [str(col).strip() for col in df.columns]
    headers: list[str] = df.columns.tolist()

    # Build row dicts; strip whitespace from cell content
    rows: list[dict[str, str]] = []
    for _, pd_row in df.iterrows():
        row_dict: dict[str, str] = {col: str(pd_row[col]).strip() for col in headers}
        rows.append(row_dict)

    return {
        "filepath"  : filepath,
        "headers"   : headers,
        "rows"      : rows,
        "total_rows": len(rows),
    }


def validate_row(row: dict, row_index: int) -> list[str]:
    """
    Check a single data row for empty or blank cells.

    Parameters
    ----------
    row       : dict[str, str]  as returned inside load_excel()["rows"]
    row_index : int             0-based index within the dataset

    Returns
    -------
    List of human-readable error strings.
    An empty list means the row is fully populated (valid).
    """
    errors: list[str] = []
    human_row = row_index + 1  # convert to 1-based for display

    for column, value in row.items():
        if not value or not value.strip():
            errors.append(
                f"Row {human_row}, Column \"{column}\": "
                f"cell is empty. Empty cells are not allowed during generation."
            )

    return errors


def validate_all_rows(rows: list[dict], *, stop_on_first: bool = False) -> dict:
    """
    Validate every row in the dataset.

    Parameters
    ----------
    rows          : list[dict]  as returned by load_excel()["rows"]
    stop_on_first : bool        stop scanning after the first invalid row

    Returns
    -------
    dict with keys:
        is_valid      : bool
        error_count   : int   (total number of empty cells across all rows)
        errors_by_row : dict[int, list[str]]
                        maps 0-based row index to its list of error strings
    """
    errors_by_row: dict[int, list[str]] = {}

    for i, row in enumerate(rows):
        row_errors = validate_row(row, i)
        if row_errors:
            errors_by_row[i] = row_errors
            if stop_on_first:
                break

    return {
        "is_valid"     : len(errors_by_row) == 0,
        "error_count"  : sum(len(v) for v in errors_by_row.values()),
        "errors_by_row": errors_by_row,
    }
