"""
Application-wide constants.
"""
import os

APP_NAME = "Teacher Result Management System"
APP_DATA_DIR = os.path.join(os.environ.get("APPDATA", ""), "TeacherResultSoftware")

# Ensure the app data directory exists on first import
os.makedirs(APP_DATA_DIR, exist_ok=True)
