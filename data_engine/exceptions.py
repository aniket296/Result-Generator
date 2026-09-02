"""
Custom exceptions for data engine and generation.
"""


class FileLockedError(Exception):
    """Raised when an Excel file is locked by another process (e.g. MS Excel)."""


class EmptyCellError(Exception):
    """Raised when an Excel cell is empty or contains only whitespace."""

    def __init__(self, row_num: int, column_name: str, message: str = "") -> None:
        self.row_num = row_num
        self.column_name = column_name
        msg = message or f"Row {row_num}: Column '{column_name}' is empty."
        super().__init__(msg)


class DuplicateUniqueValueError(Exception):
    """Raised when a unique-designated field contains duplicate values in the dataset."""

    def __init__(self, column_name: str, duplicate_values: list[str]) -> None:
        self.column_name = column_name
        self.duplicate_values = duplicate_values
        msg = f"Duplicate values found in unique column '{column_name}': {', '.join(duplicate_values)}"
        super().__init__(msg)


class DatasetMismatchError(Exception):
    """Raised when the dataset structure does not match the active template."""
