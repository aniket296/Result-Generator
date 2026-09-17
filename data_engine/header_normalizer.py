"""
data_engine/header_normalizer.py
Dynamic Header Aliasing Engine for standard student fields.

Supports dictionary-based normalization, fuzzy case-insensitive mapping,
and automatic alias resolution for common variations in Excel headers.
"""
from __future__ import annotations

import re
from typing import Sequence

# Canonical Concept -> Recognized Header Aliases
# All aliases are stored in normalized lowercase form (stripped, single spaces)
HEADER_ALIASES: dict[str, list[str]] = {
    "Name": [
        "name",
        "student name",
        "student_name",
        "full name",
        "full_name",
        "candidate name",
        "candidate_name",
        "student",
        "student's name",
        "students name",
        "pupil name",
        "learner name",
    ],
    "Roll No": [
        "roll no",
        "roll_no",
        "roll number",
        "roll_number",
        "roll",
        "rollno",
        "enrollment",
        "enrollment no",
        "enrollment_no",
        "enrollment number",
        "enrollment_number",
        "enroll no",
        "enroll_no",
        "reg no",
        "reg_no",
        "registration no",
        "registration_no",
        "registration number",
        "registration_number",
        "id",
        "student id",
        "student_id",
        "admission no",
        "admission_no",
    ],
    "Class": [
        "class",
        "grade",
        "standard",
        "std",
        "sec",
        "section",
        "class_section",
        "class/sec",
        "class-section",
        "class_sec",
    ],
}


def normalize_header(name: str) -> str:
    """
    Normalize header string for fuzzy comparison:
    - Lowercase
    - Replace underscores, hyphens, slashes with spaces
    - Collapse consecutive whitespace
    - Strip leading/trailing whitespace
    """
    if not name:
        return ""
    s = str(name).strip().lower()
    s = re.sub(r'[\_\-\/\\\:\.]+', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def get_canonical_concept(name: str) -> str | None:
    """
    Return the canonical concept name (e.g. 'Name', 'Roll No', 'Class')
    if the normalized name matches any known alias, else None.
    """
    norm = normalize_header(name)
    if not norm:
        return None

    for canonical, aliases in HEADER_ALIASES.items():
        norm_canonical = normalize_header(canonical)
        if norm == norm_canonical:
            return canonical
        for alias in aliases:
            if norm == normalize_header(alias):
                return canonical

    return None


def find_matching_header(
    field_name: str,
    available_headers: Sequence[str],
) -> str | None:
    """
    Find the best matching Excel header for a given template field name.

    Resolution hierarchy:
    1. Exact match (case-sensitive)
    2. Case-insensitive / whitespace-stripped match
    3. Normalized punctuation/space match
    4. Concept alias match via HEADER_ALIASES dictionary

    Returns:
        The exact string from available_headers, or None if no match is found.
    """
    if not field_name or not available_headers:
        return None

    clean_field = str(field_name).strip()

    # 1. Exact match
    for h in available_headers:
        if h == clean_field:
            return h

    # 2. Case-insensitive match
    field_lower = clean_field.lower()
    for h in available_headers:
        if str(h).strip().lower() == field_lower:
            return h

    # 3. Normalized string match
    norm_field = normalize_header(clean_field)
    for h in available_headers:
        if normalize_header(h) == norm_field:
            return h

    # 4. Dictionary-based alias matching
    field_concept = get_canonical_concept(clean_field)
    if field_concept:
        for h in available_headers:
            if get_canonical_concept(h) == field_concept:
                return h

    return None


def auto_map_fields(
    field_items: Sequence[Any],
    available_headers: Sequence[str],
) -> dict[str, str]:
    """
    Auto-map a collection of FieldItems against available Excel headers.
    Returns a dict of {field_label: matched_header}.
    """
    mappings: dict[str, str] = {}
    if not available_headers:
        return mappings

    used_headers: set[str] = set()

    for item in field_items:
        label = getattr(item, "label", str(item))
        current_mapped = getattr(item, "mapped_column", "")

        # If already mapped to an existing header, keep it
        if current_mapped and current_mapped in available_headers:
            mappings[label] = current_mapped
            used_headers.add(current_mapped)
            continue

        # Try auto-mapping
        matched = find_matching_header(label, available_headers)
        if matched and matched not in used_headers:
            mappings[label] = matched
            used_headers.add(matched)
        elif matched:
            mappings[label] = matched

    return mappings

