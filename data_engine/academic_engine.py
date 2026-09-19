"""
data_engine/academic_engine.py
Academic Calculation Engine & Board-Compliant Grading / Metrics System.

Features:
- Board-compliant percentage-to-grade matrix (CBSE 9-point scale, custom scales).
- CBSE 10-Point CGPA scale converter (both 9.5 conversion multiplier and subject GP averages).
- Pass / Fail result status evaluator.
- Automatic score / percentage extraction from student records.
- In-memory DataFrame and dictionary dataset enrichment with calculated columns:
  - Calculated_Grade
  - Calculated_CGPA
  - Result_Status
"""
from __future__ import annotations

import re
from typing import Any, Sequence
import pandas as pd


# ── Board-Compliant Grade Matrix Presets ───────────────────────────────────────

# CBSE standard 9-point letter grade & grade point matrix
# Range format: (min_pct, max_pct, letter_grade, grade_point, status, description)
CBSE_GRADE_MATRIX: list[dict[str, Any]] = [
    {
        "min_pct": 91.0,
        "max_pct": 100.0,
        "grade": "A1",
        "grade_point": 10.0,
        "status": "PASSED",
        "description": "Outstanding",
    },
    {
        "min_pct": 81.0,
        "max_pct": 90.999,
        "grade": "A2",
        "grade_point": 9.0,
        "status": "PASSED",
        "description": "Excellent",
    },
    {
        "min_pct": 71.0,
        "max_pct": 80.999,
        "grade": "B1",
        "grade_point": 8.0,
        "status": "PASSED",
        "description": "Very Good",
    },
    {
        "min_pct": 61.0,
        "max_pct": 70.999,
        "grade": "B2",
        "grade_point": 7.0,
        "status": "PASSED",
        "description": "Good",
    },
    {
        "min_pct": 51.0,
        "max_pct": 60.999,
        "grade": "C1",
        "grade_point": 6.0,
        "status": "PASSED",
        "description": "Fair",
    },
    {
        "min_pct": 41.0,
        "max_pct": 50.999,
        "grade": "C2",
        "grade_point": 5.0,
        "status": "PASSED",
        "description": "Average",
    },
    {
        "min_pct": 33.0,
        "max_pct": 40.999,
        "grade": "D",
        "grade_point": 4.0,
        "status": "PASSED",
        "description": "Passing",
    },
    {
        "min_pct": 0.0,
        "max_pct": 32.999,
        "grade": "E",
        "grade_point": 0.0,
        "status": "FAILED",
        "description": "Needs Remedial Intervention",
    },
]

# Standard 5-letter grade matrix (A, B, C, D, F)
STANDARD_LETTER_MATRIX: list[dict[str, Any]] = [
    {"min_pct": 90.0, "max_pct": 100.0, "grade": "A", "grade_point": 4.0, "status": "PASSED", "description": "Excellent"},
    {"min_pct": 80.0, "max_pct": 89.999, "grade": "B", "grade_point": 3.0, "status": "PASSED", "description": "Good"},
    {"min_pct": 70.0, "max_pct": 79.999, "grade": "C", "grade_point": 2.0, "status": "PASSED", "description": "Satisfactory"},
    {"min_pct": 60.0, "max_pct": 69.999, "grade": "D", "grade_point": 1.0, "status": "PASSED", "description": "Pass"},
    {"min_pct": 0.0, "max_pct": 59.999, "grade": "F", "grade_point": 0.0, "status": "FAILED", "description": "Fail"},
]

GRADE_PRESETS: dict[str, list[dict[str, Any]]] = {
    "CBSE": CBSE_GRADE_MATRIX,
    "CBSE_9_POINT": CBSE_GRADE_MATRIX,
    "STANDARD": STANDARD_LETTER_MATRIX,
}

# Calculated column names
COL_CALCULATED_GRADE = "Calculated_Grade"
COL_CALCULATED_CGPA = "Calculated_CGPA"
COL_RESULT_STATUS = "Result_Status"
ACADEMIC_CALCULATED_COLUMNS = [COL_CALCULATED_GRADE, COL_CALCULATED_CGPA, COL_RESULT_STATUS]


# ── Core Calculators ─────────────────────────────────────────────────────────

def calculate_grade(
    score: float | int | str,
    max_score: float = 100.0,
    preset: str = "CBSE",
    grade_matrix: list[dict[str, Any]] | None = None,
) -> tuple[str, float]:
    """
    Evaluate a raw score or percentage into a letter grade and grade point.

    Args:
        score: Raw score or percentage (can be numeric or numeric string).
        max_score: Maximum achievable score (default 100.0).
        preset: Preset matrix name ("CBSE", "CBSE_9_POINT", "STANDARD").
        grade_matrix: Optional custom grade matrix list.

    Returns:
        tuple[str, float]: (letter_grade, grade_point), e.g. ("A1", 10.0)
    """
    try:
        if isinstance(score, str):
            clean_str = re.sub(r'[^\d.]', '', score.strip())
            if not clean_str:
                return ("N/A", 0.0)
            val = float(clean_str)
        else:
            val = float(score)
    except (ValueError, TypeError):
        return ("N/A", 0.0)

    # Convert to percentage
    if max_score > 0 and max_score != 100.0:
        pct = (val / max_score) * 100.0
    else:
        pct = val

    # Clamp percentage to valid boundary
    pct = max(0.0, min(100.0, pct))

    matrix = grade_matrix or GRADE_PRESETS.get(preset.upper(), CBSE_GRADE_MATRIX)

    for bracket in matrix:
        min_p = float(bracket["min_pct"])
        max_p = float(bracket["max_pct"])
        # Support both floating point inclusive edge cases
        if min_p <= pct <= max_p or (pct >= min_p and bracket is matrix[0]):
            return (str(bracket["grade"]), float(bracket["grade_point"]))

    # Fallback to the lowest bracket if not matched
    lowest = matrix[-1]
    return (str(lowest["grade"]), float(lowest["grade_point"]))


def calculate_cgpa_from_percentage(
    percentage: float | int | str,
    method: str = "cbse_9_5",
) -> float:
    """
    Convert a percentage score into a 10-Point CGPA scale.

    Methods:
    - "cbse_9_5": Standard CBSE conversion formula (CGPA = Percentage / 9.5), capped at 10.0.
    - "grade_point": Direct 10-Point scale lookup based on the CBSE 9-point grade bracket.

    Returns:
        float: CGPA rounded to 2 decimal places (0.0 to 10.0).
    """
    try:
        if isinstance(percentage, str):
            clean_str = re.sub(r'[^\d.]', '', percentage.strip())
            pct = float(clean_str) if clean_str else 0.0
        else:
            pct = float(percentage)
    except (ValueError, TypeError):
        return 0.0

    pct = max(0.0, min(100.0, pct))

    if method == "grade_point":
        _, gp = calculate_grade(pct, max_score=100.0, preset="CBSE")
        return round(gp, 2)
    
    # Standard CBSE formula: Percentage / 9.5
    cgpa = pct / 9.5
    return round(min(10.0, max(0.0, cgpa)), 2)


def cgpa_to_percentage(cgpa: float | int | str) -> float:
    """
    Convert a 10-Point CGPA to its approximate percentage using standard CBSE formula (CGPA * 9.5).
    """
    try:
        val = float(cgpa)
    except (ValueError, TypeError):
        return 0.0
    return round(min(100.0, max(0.0, val * 9.5)), 2)


def evaluate_result_status(
    score: float | int | str,
    max_score: float = 100.0,
    passing_percentage: float = 33.0,
) -> str:
    """
    Evaluate student result status ("PASSED" or "FAILED").

    Args:
        score: Raw score or percentage.
        max_score: Maximum score.
        passing_percentage: Minimum percentage required to pass (default 33.0%).

    Returns:
        str: "PASSED" or "FAILED"
    """
    try:
        if isinstance(score, str):
            clean_str = re.sub(r'[^\d.]', '', score.strip())
            val = float(clean_str) if clean_str else 0.0
        else:
            val = float(score)
    except (ValueError, TypeError):
        return "FAILED"

    if max_score > 0 and max_score != 100.0:
        pct = (val / max_score) * 100.0
    else:
        pct = val

    return "PASSED" if pct >= passing_percentage else "FAILED"


# ── Record & Column Introspection ────────────────────────────────────────────

_COMMON_SCORE_NAMES = [
    "percentage", "percent", "pct", "%", "total percentage",
    "total marks", "total_marks", "total", "aggregate", "grand total",
    "obtained marks", "marks obtained", "score", "marks",
]


def extract_student_percentage(
    record: dict[str, Any],
    score_column: str | None = None,
    max_score: float = 100.0,
) -> float | None:
    """
    Extract or calculate student aggregate percentage from a record dict.
    
    Resolution order:
    1. Explicit score_column if provided.
    2. Column named percentage/pct/percent.
    3. Column named total/aggregate with max_marks or default max.
    4. Average of numeric subject columns.
    """
    # 1. Explicit column
    if score_column and score_column in record:
        val_str = str(record[score_column]).strip()
        num = _parse_float(val_str)
        if num is not None:
            if max_score != 100.0 and max_score > 0:
                return (num / max_score) * 100.0
            return num

    # 2. Heuristic search for percentage / total marks column
    lowered_keys = {k.strip().lower(): k for k in record.keys()}

    # Look for percentage first
    for cand in ["percentage", "percent", "pct", "total percentage", "aggregate percentage"]:
        if cand in lowered_keys:
            val = _parse_float(record[lowered_keys[cand]])
            if val is not None:
                return val

    # Look for total marks
    for cand in ["total marks", "total_marks", "total", "aggregate", "grand total", "marks obtained"]:
        if cand in lowered_keys:
            total_val = _parse_float(record[lowered_keys[cand]])
            if total_val is not None:
                # Check for explicit max marks column
                for max_cand in ["max marks", "max_marks", "maximum marks", "total max", "out of"]:
                    if max_cand in lowered_keys:
                        m_val = _parse_float(record[lowered_keys[max_cand]])
                        if m_val and m_val > 0:
                            return (total_val / m_val) * 100.0
                if max_score > 0 and max_score != 100.0:
                    return (total_val / max_score) * 100.0
                return total_val

    # 3. Numeric subject columns aggregation
    numeric_scores: list[float] = []
    ignored_keywords = ["roll", "id", "enroll", "phone", "mobile", "contact", "pin", "year", "dob", "date", "age", "class", "rank", "sec"]
    for k, v in record.items():
        k_low = k.strip().lower()
        if any(ign in k_low for ign in ignored_keywords):
            continue
        val = _parse_float(v)
        if val is not None and 0.0 <= val <= 100.0:
            numeric_scores.append(val)

    if numeric_scores:
        return sum(numeric_scores) / len(numeric_scores)

    return None


def _parse_float(val: Any) -> float | None:
    """Helper to safely parse numeric float from string/number."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    clean = re.sub(r'[^\d.]', '', s)
    if not clean:
        return None
    try:
        return float(clean)
    except ValueError:
        return None


# ── Dataset Enrichment ───────────────────────────────────────────────────────

def enrich_records(
    headers: list[str],
    records: list[dict[str, str]],
    score_column: str | None = None,
    max_score: float = 100.0,
    preset: str = "CBSE",
    cgpa_method: str = "cbse_9_5",
    overwrite: bool = True,
) -> tuple[list[str], list[dict[str, str]]]:
    """
    Enrich raw student records and headers list with calculated academic columns:
    - Calculated_Grade
    - Calculated_CGPA
    - Result_Status

    Args:
        headers: List of existing column headers.
        records: List of student row dictionaries.
        score_column: Optional explicit column to compute from.
        max_score: Maximum achievable score.
        preset: Grading preset ("CBSE", "STANDARD").
        cgpa_method: CGPA calculation method ("cbse_9_5" or "grade_point").
        overwrite: Whether to overwrite existing calculated values.

    Returns:
        tuple[list[str], list[dict[str, str]]]: Updated (headers, records)
    """
    new_headers = list(headers)
    for col in ACADEMIC_CALCULATED_COLUMNS:
        if col not in new_headers:
            new_headers.append(col)

    enriched_records: list[dict[str, str]] = []

    for row in records:
        row_copy = dict(row)
        pct = extract_student_percentage(row_copy, score_column=score_column, max_score=max_score)

        if pct is not None:
            grade_letter, gp = calculate_grade(pct, max_score=100.0, preset=preset)
            cgpa = calculate_cgpa_from_percentage(pct, method=cgpa_method)
            status = evaluate_result_status(pct, max_score=100.0)

            if overwrite or not row_copy.get(COL_CALCULATED_GRADE):
                row_copy[COL_CALCULATED_GRADE] = grade_letter
            if overwrite or not row_copy.get(COL_CALCULATED_CGPA):
                row_copy[COL_CALCULATED_CGPA] = f"{cgpa:.2f}"
            if overwrite or not row_copy.get(COL_RESULT_STATUS):
                row_copy[COL_RESULT_STATUS] = status
        else:
            if overwrite or not row_copy.get(COL_CALCULATED_GRADE):
                row_copy[COL_CALCULATED_GRADE] = ""
            if overwrite or not row_copy.get(COL_CALCULATED_CGPA):
                row_copy[COL_CALCULATED_CGPA] = ""
            if overwrite or not row_copy.get(COL_RESULT_STATUS):
                row_copy[COL_RESULT_STATUS] = ""

        enriched_records.append(row_copy)

    return new_headers, enriched_records


def enrich_dataset_with_academic_metrics(
    df: pd.DataFrame,
    score_column: str | None = None,
    max_score: float = 100.0,
    preset: str = "CBSE",
    cgpa_method: str = "cbse_9_5",
) -> pd.DataFrame:
    """
    Enrich an active pandas DataFrame directly with calculated academic columns.
    
    Returns:
        pd.DataFrame with Calculated_Grade, Calculated_CGPA, and Result_Status columns.
    """
    records = df.to_dict(orient="records")
    headers = list(df.columns)
    _, enriched = enrich_records(
        headers=headers,
        records=records,
        score_column=score_column,
        max_score=max_score,
        preset=preset,
        cgpa_method=cgpa_method,
    )
    return pd.DataFrame(enriched)
