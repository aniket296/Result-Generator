"""
academic_engine.py
Root-level alias forwarding to data_engine.academic_engine.
"""
from data_engine.academic_engine import (
    ACADEMIC_CALCULATED_COLUMNS,
    CBSE_GRADE_MATRIX,
    COL_CALCULATED_CGPA,
    COL_CALCULATED_GRADE,
    COL_RESULT_STATUS,
    GRADE_PRESETS,
    STANDARD_LETTER_MATRIX,
    calculate_cgpa_from_percentage,
    calculate_grade,
    cgpa_to_percentage,
    enrich_dataset_with_academic_metrics,
    enrich_records,
    evaluate_result_status,
    extract_student_percentage,
)

__all__ = [
    "ACADEMIC_CALCULATED_COLUMNS",
    "CBSE_GRADE_MATRIX",
    "COL_CALCULATED_CGPA",
    "COL_CALCULATED_GRADE",
    "COL_RESULT_STATUS",
    "GRADE_PRESETS",
    "STANDARD_LETTER_MATRIX",
    "calculate_cgpa_from_percentage",
    "calculate_grade",
    "cgpa_to_percentage",
    "enrich_dataset_with_academic_metrics",
    "enrich_records",
    "evaluate_result_status",
    "extract_student_percentage",
]

