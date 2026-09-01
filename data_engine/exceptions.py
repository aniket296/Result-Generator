"""
Custom exceptions for the data engine.
"""


class FileLockedError(Exception):
    """
    Raised when the target Excel file cannot be accessed because it is
    held open (write-locked) by another process such as Microsoft Excel.

    The UI layer catches this and shows a [Retry] / [Cancel] dialog.
    """


class EmptyCellError(Exception):
    """
    Raised when a required cell contains no value.

    Because this application is a strict raw-display renderer, an empty
    cell during result generation is always a critical error, never a
    blank placeholder.
    """
