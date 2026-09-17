"""
data_engine/preflight_sanitizer.py
Pre-Flight Data Sanitizer & Audit Engine for Student Result Datasets.

Key capabilities:
1. Whitespace sanitization (strips leading/trailing whitespace across all string columns).
2. Flaw detection:
   - Missing / empty / NaN cells in mapped template columns.
   - Duplicate identifiers in the designated Unique (Roll/ID) column.
3. Automated dataset sanitization (auto-filling empty mapped cells & de-duplicating ID suffixes).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Sequence


@dataclass
class AuditIssue:
    """Represents a single data flaw detected during pre-flight audit."""
    row_num: int            # 1-indexed spreadsheet row number
    column_name: str        # Column name where issue was found
    issue_type: str         # "Empty Cell" | "Duplicate Identifier"
    description: str        # Human-readable explanation
    original_value: str = ""


@dataclass
class AuditReport:
    """Summary of all issues found during pre-flight dataset audit."""
    total_rows: int = 0
    issues: list[AuditIssue] = field(default_factory=list)

    @property
    def has_flaws(self) -> bool:
        return len(self.issues) > 0

    @property
    def empty_count(self) -> int:
        return sum(1 for i in self.issues if i.issue_type == "Empty Cell")

    @property
    def duplicate_count(self) -> int:
        return sum(1 for i in self.issues if i.issue_type == "Duplicate Identifier")

    @property
    def affected_rows_count(self) -> int:
        return len({i.row_num for i in self.issues})


def is_empty_value(val: Any) -> bool:
    """Determine if a cell value is considered empty, whitespace-only, or NaN."""
    if val is None:
        return True
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return True
    s = str(val).strip()
    return s == "" or s.lower() in ("nan", "none", "null", "<na>", "n/a")


def clean_row_whitespace(row: dict[str, Any]) -> dict[str, str]:
    """Clean all string values in a single row by stripping extra leading/trailing whitespace."""
    cleaned: dict[str, str] = {}
    for k, v in row.items():
        if v is None:
            cleaned[str(k)] = ""
        elif isinstance(v, float):
            if math.isnan(v) or math.isinf(v):
                cleaned[str(k)] = ""
            elif v.is_integer():
                cleaned[str(k)] = str(int(v))
            else:
                cleaned[str(k)] = str(v)
        else:
            cleaned[str(k)] = str(v).strip()
    return cleaned


def audit_dataset(
    rows: Sequence[dict[str, Any]],
    mapped_columns: Sequence[str],
    unique_col: str = "",
) -> tuple[list[dict[str, str]], AuditReport]:
    """
    Run pre-flight validation on the dataset.

    Args:
        rows: Raw dataset row dictionaries.
        mapped_columns: Columns actively mapped to template placeholders/charts/badges.
        unique_col: Designated unique identifier column (e.g. Roll No, Enrollment).

    Returns:
        tuple[list[dict[str, str]], AuditReport]:
            (cleaned_rows, audit_report)
    """
    report = AuditReport(total_rows=len(rows))
    cleaned_rows: list[dict[str, str]] = []

    # Filter out empty/blank column names from mapped_columns
    valid_mapped_cols = [str(c).strip() for c in mapped_columns if str(c).strip()]

    seen_ids: dict[str, int] = {}  # {unique_val: first_seen_row_1_indexed}

    for idx, raw_row in enumerate(rows, start=1):
        clean_row = clean_row_whitespace(raw_row)
        cleaned_rows.append(clean_row)

        # 1. Check for empty cells in mapped columns
        for col in valid_mapped_cols:
            # Case-insensitive lookup if direct key not present
            val = clean_row.get(col)
            if val is None:
                for rk, rv in clean_row.items():
                    if rk.lower() == col.lower():
                        val = rv
                        break

            if is_empty_value(val):
                report.issues.append(
                    AuditIssue(
                        row_num=idx,
                        column_name=col,
                        issue_type="Empty Cell",
                        description=f"Missing or empty value for required mapped field '{col}'.",
                        original_value=str(val or ""),
                    )
                )

        # 2. Check for duplicate unique identifiers
        if unique_col:
            u_val = clean_row.get(unique_col)
            if u_val is None:
                for rk, rv in clean_row.items():
                    if rk.lower() == unique_col.lower():
                        u_val = rv
                        break

            u_clean = str(u_val or "").strip()
            if u_clean and not is_empty_value(u_clean):
                if u_clean in seen_ids:
                    first_row = seen_ids[u_clean]
                    report.issues.append(
                        AuditIssue(
                            row_num=idx,
                            column_name=unique_col,
                            issue_type="Duplicate Identifier",
                            description=f"Duplicate identifier '{u_clean}' (first seen at row {first_row}).",
                            original_value=u_clean,
                        )
                    )
                else:
                    seen_ids[u_clean] = idx

    return cleaned_rows, report


def auto_sanitize_dataset(
    rows: Sequence[dict[str, Any]],
    mapped_columns: Sequence[str],
    unique_col: str = "",
    default_empty_fill: str = "N/A",
) -> list[dict[str, str]]:
    """
    Sanitize dataset automatically so generation can proceed safely:
    - Strips all whitespace.
    - Replaces empty values in mapped columns with default_empty_fill.
    - Resolves duplicate unique IDs by appending a unique counter (_DUP1, _DUP2...).
    """
    sanitized: list[dict[str, str]] = []
    valid_mapped_cols = [str(c).strip() for c in mapped_columns if str(c).strip()]

    id_counts: dict[str, int] = {}

    for idx, raw_row in enumerate(rows, start=1):
        row = clean_row_whitespace(raw_row)

        # 1. Fill empty mapped columns
        for col in valid_mapped_cols:
            actual_key = col
            if col not in row:
                for rk in row:
                    if rk.lower() == col.lower():
                        actual_key = rk
                        break

            val = row.get(actual_key)
            if is_empty_value(val):
                row[actual_key] = default_empty_fill

        # 2. De-duplicate unique IDs
        if unique_col:
            u_key = unique_col
            if unique_col not in row:
                for rk in row:
                    if rk.lower() == unique_col.lower():
                        u_key = rk
                        break

            raw_id = row.get(u_key, f"REC_{idx}").strip()
            if not raw_id:
                raw_id = f"REC_{idx}"

            if raw_id in id_counts:
                id_counts[raw_id] += 1
                row[u_key] = f"{raw_id}_DUP{id_counts[raw_id]}"
            else:
                id_counts[raw_id] = 0
                row[u_key] = raw_id

        sanitized.append(row)

    return sanitized

