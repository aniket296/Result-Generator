"""
Build & Packaging Script for Teacher Result Management System.
Packages the offline PyQt6 desktop app into a standalone Windows executable.

Usage:
    python build.py            # Standard onedir build (fast startup, recommended)
    python build.py --onefile  # Single .exe executable
"""
import os
import sys
import shutil
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_DIR, "dist")
BUILD_DIR = os.path.join(PROJECT_DIR, "build")
SPEC_FILE = os.path.join(PROJECT_DIR, "TeacherResultSoftware.spec")

def clean_build_artifacts():
    print("[1/3] Cleaning previous build artifacts...")
    for path in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
                print(f"      Removed {os.path.basename(path)}/")
            except Exception as e:
                print(f"      Warning: Could not remove {path}: {e}")

def check_pyinstaller():
    try:
        import PyInstaller
        print(f"[2/3] Found PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("[2/3] PyInstaller not found. Installing via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def run_build(onefile=False):
    print("[3/3] Building Windows Executable with PyInstaller...")
    
    if onefile:
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--noconsole",
            "--onefile",
            "--name=TeacherResultSoftware",
            "--hidden-import=pandas",
            "--hidden-import=openpyxl",
            "--hidden-import=openpyxl.cell._writer",
            "--hidden-import=pymupdf",
            "--hidden-import=PyQt6",
            "--hidden-import=PyQt6.QtCore",
            "--hidden-import=PyQt6.QtGui",
            "--hidden-import=PyQt6.QtWidgets",
            "--hidden-import=PyQt6.QtPrintSupport",
            "--hidden-import=matplotlib",
            "--hidden-import=matplotlib.pyplot",
            "--hidden-import=matplotlib.figure",
            "--hidden-import=matplotlib.backends.backend_agg",
            "--exclude-module=tkinter",
            "--exclude-module=scipy",
            "--exclude-module=IPython",
        ]
        ico_file = os.path.join(PROJECT_DIR, "installer", "assets", "app_icon.ico")
        if os.path.exists(ico_file):
            cmd.append(f"--icon={ico_file}")
        cmd.append("main.py")
    else:
        # Use spec file for onedir
        cmd = [sys.executable, "-m", "PyInstaller", SPEC_FILE]

    print(f"      Command: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=PROJECT_DIR)

    print("\n" + "=" * 65)
    print(" BUILD SUCCESSFUL!")
    print("=" * 65)
    if onefile:
        exe_path = os.path.join(DIST_DIR, "TeacherResultSoftware.exe")
        print(f"Single Executable: {exe_path}")
    else:
        out_folder = os.path.join(DIST_DIR, "TeacherResultSoftware")
        exe_path = os.path.join(out_folder, "TeacherResultSoftware.exe")
        print(f"Output Directory: {out_folder}")
        print(f"Main Executable : {exe_path}")
    print("=" * 65)

if __name__ == "__main__":
    is_onefile = "--onefile" in sys.argv
    clean_build_artifacts()
    check_pyinstaller()
    run_build(onefile=is_onefile)
