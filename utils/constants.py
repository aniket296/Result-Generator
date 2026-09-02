"""
Application-wide constants, path helpers, and system utilities.
"""
from __future__ import annotations

import os
import sys

APP_NAME = "Teacher Result Management System"
APP_DATA_DIR = os.path.join(os.environ.get("APPDATA", ""), "TeacherResultSoftware")
TEMPLATES_DIR = os.path.join(APP_DATA_DIR, "templates")
DATASETS_DIR = os.path.join(APP_DATA_DIR, "datasets")
RECOVERY_DIR = os.path.join(APP_DATA_DIR, "recovery")

# Ensure required storage directories exist
os.makedirs(APP_DATA_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(DATASETS_DIR, exist_ok=True)
os.makedirs(RECOVERY_DIR, exist_ok=True)


def resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, compatible with development mode and PyInstaller frozen bundles.
    In PyInstaller bundles, sys._MEIPASS contains the runtime extraction/bundle directory path.
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)
